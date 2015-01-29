# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from itertools import chain, izip

from google.appengine.api import memcache
from google.appengine.ext import ndb

from gaebusiness.business import Command, CommandSequential, CommandExecutionException, CommandParallel
from gaebusiness.gaeutil import UpdateCommand, DeleteCommand, ModelSearchCommand
from gaegraph.model import destinations_cache_key, origins_cache_key, to_node_key, Node

LONG_ERROR = "LONG_ERROR"


class _NodeSearch(Command):
    """
    Command for search node by its id
    """
    _model_class = None  # attribute to enforce node class


    def __init__(self, node_or_key_or_id):
        super(_NodeSearch, self).__init__()
        self.node_key = to_node_key(node_or_key_or_id)
        self._future = None


    def set_up(self):
        self._future = self.node_key.get_async()


    def do_business(self):
        self.result = self._future.get_result()
        node = self.result
        if self._model_class is not None and node and not isinstance(node, self._model_class):
            self.add_error('node_error', '%s should be %s instance' % (node.key, self._model_class.__name__))


class RelationFiller(CommandParallel):
    def __init__(self, node_or_key_or_id, relation_factory, relations):
        node_key = to_node_key(node_or_key_or_id)
        relations = relations or []
        self._relations_commands = {k: relation_factory[k](node_key)
                                    for k in relations}

        super(RelationFiller, self).__init__(*self._relations_commands.itervalues())

    def fill(self, obj):
        for k, cmd in self._relations_commands.iteritems():
            setattr(obj, k, cmd.result)


class NodeSearch(CommandParallel):
    _model_class = None  # attribute to enforce node class
    _relations = {}

    def __init__(self, node_or_key_or_id, relations=None):
        node_search = _NodeSearch(node_or_key_or_id)
        node_search._model_class = self._model_class
        if relations:
            self._relation_filler = RelationFiller(node_or_key_or_id, self._relations, relations)
            super(NodeSearch, self).__init__(self._relation_filler, node_search)
        else:
            self._relation_filler = None
            super(NodeSearch, self).__init__(node_search)

    def do_business(self):
        super(NodeSearch, self).do_business()
        if self._relation_filler:
            self._relation_filler.fill(self.result)


class ModelSearchWithRelations(ModelSearchCommand):
    _relations = {}

    def __init__(self, query, page_size=100, start_cursor=None, offset=0, use_cache=True, cache_begin=True,
                 relations=None, **kwargs):
        super(ModelSearchWithRelations, self).__init__(query, page_size, start_cursor, offset, use_cache, cache_begin,
                                                       **kwargs)
        self._required_relations = relations

    def do_business(self, stop_on_error=True):
        super(ModelSearchWithRelations, self).do_business(stop_on_error)
        if self._required_relations and self.result:
            cmds = CommandParallel(*(RelationFiller(r, self._relations, self._required_relations) for r in self.result))
            cmds()
            for r, filler in izip(self.result, cmds):
                filler.fill(r)


class CreateArc(CommandSequential):
    """
    Command to create arc between origin and destination.

    Useful to create many to many relations between origins and destination.

    See CreateSingleArc for one to many connections or CreateUniqueArc for one to one connections
    """
    arc_class = None

    def __init__(self, origin=None, destination=None):

        # this values will be set latter on _extract_and_validate or handle_previous
        self.origin = None
        self.destination = None

        self._command_parallel = CommandParallel(self._to_command(origin), self._to_command(destination))
        super(CreateArc, self).__init__(self._command_parallel)

    def _extract_and_validate_nodes(self):
        if self.origin is None:
            self.origin = self._command_parallel[0].result
        if self.destination is None:
            self.destination = self._command_parallel[1].result
        if self.origin is None or self.destination is None:
            self.add_error('node_error', 'origin and destination must not be None')

    def do_business(self):
        super(CreateArc, self).do_business()
        self._extract_and_validate_nodes()
        self._validate()
        if self.errors:
            raise CommandExecutionException(unicode(self.errors))
        else:
            self._to_commit = self.arc_class(self.origin, self.destination)
            self.result = self._to_commit


    def _validate(self):
        pass

    def _to_command(self, node_or_command):
        if isinstance(node_or_command, Command):
            return node_or_command
        cmd = Command()
        try:
            node_key = to_node_key(node_or_command)
            cmd.result = node_key
        except:
            pass
        return cmd


class CreateUniqueArc(Command):
    """
    Command to create Arc between origin and destination only if both nodes don't have any arc of type informed on
    __init__.

    Useful for create one to one associations between origin and destination
    or one destination has many origins

    See CreateArc for many to many connections or CreateSingleArc for one to many connections
    """
    arc_class = None

    def __init__(self, origin=None, destination=None):
        super(CreateUniqueArc, self).__init__()
        self.destination = None
        self._destination_cmd = destination
        self.origin = None
        self._origin_cmd = origin
        self._origin_validation_cmd = None
        self._destination_validation_cmd = None

    def _extract_command(self, node, cmd_class):
        key = None
        try:
            key = to_node_key(node)
        except:
            return None
        cmd = cmd_class(key)
        cmd.arc_class = self.arc_class
        return cmd

    def set_up(self):
        self._origin_validation_cmd = self._extract_command(self._origin_cmd, _OriginHasDestinationRaiseError)
        self._destination_validation_cmd = self._extract_command(self._destination_cmd, _DestinationHasOriginRaiseError)

        # execution origin
        if self._origin_validation_cmd:
            self._origin_validation_cmd.set_up()
        else:
            self._origin_cmd.set_up()
        # execution destination
        if self._destination_validation_cmd:
            self._destination_validation_cmd.set_up()
        else:
            self._destination_cmd.set_up()

    def do_business(self):
        # execution origin
        if not self._origin_validation_cmd:
            self._origin_cmd.do_business()
            result = self._origin_cmd.result
            if result and result.key:
                self._origin_validation_cmd = self._extract_command(to_node_key(result),
                                                                    _OriginHasDestinationRaiseError)
                self._origin_validation_cmd.set_up()
        if self._origin_validation_cmd:
            self._origin_validation_cmd.do_business()
            self.errors.update(self._origin_validation_cmd.errors)
            self.origin = self._origin_validation_cmd.result

        if not self._destination_validation_cmd:
            self._destination_cmd.do_business()
            result = self._destination_cmd.result
            if result and result.key:
                self._destination_validation_cmd = self._extract_command(to_node_key(result),
                                                                         _DestinationHasOriginRaiseError)
                self._destination_validation_cmd.set_up()
        if self._destination_validation_cmd:
            self._destination_validation_cmd.do_business()
            self.errors.update(self._destination_validation_cmd.errors)
            self.destination = self._destination_validation_cmd.result


    def commit(self):
        if not self.errors:
            if self.origin is None and self.destination is None:
                ndb.put_multi([self._origin_cmd.commit(), self._destination_cmd.commit()])
                self.origin = self._origin_cmd.result
                self.destination = self._destination_cmd.result

            elif self.origin is None:
                ndb.put_multi([self._origin_cmd.commit()])
                self.origin = self._origin_cmd.result

            elif self.destination is None:
                ndb.put_multi([self._destination_cmd.commit()])
                self.destination = self._destination_cmd.result

            cmd = CreateArc(self.origin, self.destination)
            cmd.arc_class = self.arc_class
            cmd.set_up()
            cmd.do_business()
            return cmd.commit()


class CreateSingleArc(CreateArc):
    """
    Command to create Arc between origin and destination only if there is not one connecting them.

    Useful for create one to many associations where one origins node has many destination
    or one destination has many origins.

    See CreateArc for many to many connections or CreateUniqueArc for one to one connections
    """

    def _validate(self):
        has_arc = HasArcCommand(self.origin, self.destination)
        has_arc.arc_class = self.arc_class
        self.result = has_arc()
        if self.result:
            self.add_error('nodes_error', 'There is already an Arc %s for those nodes' % self.result)


class CreateSingleOriginArc(CreateArc):
    """
    Command to create Arc between origin and destination only destination has not already an arc.

    Useful for create one to many associations where one origin node has many destinations but destinations has only one origin.

    See CreateArc or CreateSingleArc for many to many connections or CreateUniqueArc for one to one connections
    """

    def _validate(self):
        has_arc_cmd = HasArcCommand(destination=self.destination)
        has_arc_cmd.arc_class = self.arc_class
        self.result = has_arc_cmd()
        if self.result:
            self.add_error('nodes_error',
                           'There is already an Arc %s for destination %s. It is not possible creating another connection to origin %s' % (
                               self.result, self.destination, self.origin))


class CreateSingleDestinationArc(CreateArc):
    """
    Command to create Arc between origin and destination only destination has not already an arc.

    Useful for create one to many associations where one origin node has many destinations but destinations has only one origin.

    See CreateArc or CreateSingleArc for many to many connections or CreateUniqueArc for one to one connections
    """

    def _validate(self):
        has_arc_cmd = HasArcCommand(self.origin)
        has_arc_cmd.arc_class = self.arc_class
        self.result = has_arc_cmd()
        if self.result:
            self.add_error('nodes_error',
                           'There is already an Arc %s for origin %s. It is not possible creating another connection to destination %s' % (
                               self.result, self.origin, self.destination ))


class PaginatedArcSearch(ModelSearchCommand):
    def __init__(self, query, page_size=100, start_cursor=None, offset=0, use_cache=True, cache_begin=True, **kwargs):
        super(PaginatedArcSearch, self).__init__(query, page_size, start_cursor, offset, use_cache, cache_begin,
                                                 **kwargs)


class ArcSearch(Command):
    arc_class = None

    def __init__(self, origin=None, destination=None, keys_only=True):
        super(ArcSearch, self).__init__()
        self.destination = destination
        self.origin = origin
        self._keys_only = keys_only
        self._query = None
        self._future = None

    def _validate(self):
        origin = self.origin
        destination = self.destination
        if not (origin or destination):
            raise Exception('at least one of origin and destination must be not None')
        if origin and destination:
            self._query = self.arc_class.query_by_origin_and_destination(origin, destination)
        elif origin:
            self._query = self.arc_class.find_destinations(origin)
        else:
            self._query = self.arc_class.find_origins(destination)
        self._future = None

    def set_up(self):
        self._validate()
        self._future = self._query.fetch_async(keys_only=self._keys_only)

    def do_business(self):
        self.result = self._future.get_result()


class HasArcCommand(ArcSearch):
    """
    Class used to know if there is an Arc connecting origin and destination
    If origin or destination is None, it is going to search for any Arc
    origin and destination can not be none at same time
    """

    def __init__(self, origin=None, destination=None):
        super(HasArcCommand, self).__init__(origin, destination, True)

    def set_up(self):
        self._validate()
        self._future = self._query.get_async(keys_only=True)


class _OriginHasDestinationRaiseError(HasArcCommand):
    def __init__(self, origin):
        super(_OriginHasDestinationRaiseError, self).__init__(origin, None)
        self.origin = origin

    def do_business(self):
        super(_OriginHasDestinationRaiseError, self).do_business()
        if self.result:
            self.add_error('origin', 'Origin %s already has an Arc %s' % (self.origin, self.result))
        else:
            self.result = self.origin

    def handle_previous(self, command):
        self.origin = command.result


class _DestinationHasOriginRaiseError(HasArcCommand):
    def __init__(self, destination):
        super(_DestinationHasOriginRaiseError, self).__init__(None, destination)
        self.destination = destination

    def do_business(self):
        super(_DestinationHasOriginRaiseError, self).do_business()
        if self.result:
            self.add_error('destination', 'Destination %s already has an Arc %s' % (self.destination, self.result))
        else:
            self.result = self.destination

    def handle_previous(self, command):
        self.destination = command.result


class ArcNodeSearchBase(ArcSearch):
    arc_class = None

    def __init__(self, origin=None, destination=None):
        super(ArcNodeSearchBase, self).__init__(origin, destination, False)
        if origin and destination:
            raise Exception('only one of origin or destination can be not None')
        elif origin:
            self._cache_key = destinations_cache_key(self.arc_class, self.origin)
            self._arc_property = 'destination'
        else:
            self._arc_property = 'origin'
            self._cache_key = origins_cache_key(self.arc_class, destination)
        self._node_cached_keys = None

    def set_up(self):
        try:
            self._node_cached_keys = memcache.get(self._cache_key)
        except:
            pass  # If memcache fails, do nothing
        if not self._node_cached_keys:
            super(ArcNodeSearchBase, self).set_up()

    def do_business(self):
        cached_keys = self._node_cached_keys
        if not cached_keys:
            super(ArcNodeSearchBase, self).do_business()
            cached_keys = [getattr(arc, self._arc_property) for arc in self.result]
            self.result = []
            if cached_keys:
                try:
                    memcache.set(self._cache_key, cached_keys)
                except:
                    pass  # If memcache fails, do nothing
        if cached_keys:
            self.result = ndb.get_multi(cached_keys)
        self.result = [e for e in self.result if e]


class DestinationsSearch(ArcNodeSearchBase):
    def __init__(self, origin):
        super(DestinationsSearch, self).__init__(origin)


class SingleDestinationSearch(DestinationsSearch):
    def do_business(self):
        DestinationsSearch.do_business(self)
        self.result = self.result[0] if self.result else None


class OriginsSearch(ArcNodeSearchBase):
    def __init__(self, destination):
        super(OriginsSearch, self).__init__(destination=destination)


class SingleOriginSearch(OriginsSearch):
    def do_business(self):
        OriginsSearch.do_business(self)
        self.result = self.result[0] if self.result else None


class UpdateNode(UpdateCommand):
    def __init__(self, model_key, **form_parameters):
        model_or_key = model_key if isinstance(model_key, ndb.Model) else to_node_key(model_key)
        super(UpdateNode, self).__init__(model_or_key, **form_parameters)


class DeleteNode(CommandParallel):
    _model_class = None

    def __init__(self, *model_keys):
        class _NodeSearch(NodeSearch):
            _model_class = self._model_class

        self.model_keys = [to_node_key(m) for m in model_keys]
        super(DeleteNode, self).__init__(*[_NodeSearch(m) for m in self.model_keys])

    def do_business(self):
        super(DeleteNode, self).do_business()


    def commit(self):
        ndb.delete_multi(self.model_keys)


class DeleteArcs(ArcSearch):
    def __init__(self, origin=None, destination=None):
        super(DeleteArcs, self).__init__(origin, destination, False)
        self.__destination = destination
        self.__origin = origin
        self._arc_delete_future = None

    def do_business(self):
        super(DeleteArcs, self).do_business()

        if self.result:
            futures = ndb.delete_multi_async([arc.key for arc in self.result])
            cache_keys = []
            if self.__origin:
                cache_keys.append(destinations_cache_key(self.arc_class, self.__origin))
            else:
                for arc in self.result:
                    cache_keys.append(destinations_cache_key(self.arc_class, arc.origin))

            if self.__destination:
                cache_keys.append(origins_cache_key(self.arc_class, self.__destination))
            else:
                for arc in self.result:
                    cache_keys.append(origins_cache_key(self.arc_class, arc.destination))
            memcache.delete_multi(cache_keys)
            [f.get_result() for f in futures]







