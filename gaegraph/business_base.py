# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from google.appengine.api import memcache
from google.appengine.ext import ndb

from gaebusiness.business import Command
from gaebusiness.gaeutil import UpdateCommand, DeleteCommand
from gaegraph.model import destinations_cache_key, origins_cache_key, to_node_key

LONG_ERROR = "LONG_ERROR"


class NodeSearch(Command):
    """
    Command for search node by its id
    """

    def __init__(self, node_or_key_or_id):
        super(NodeSearch, self).__init__()
        self.node_key = to_node_key(node_or_key_or_id)
        self._future = None


    def set_up(self):
        self._future = self.node_key.get_async()

    def do_business(self):
        self.result = self._future.get_result()


class ArcSearch(Command):
    def __init__(self, arc_class, origin=None, destination=None, keys_only=True):
        if not (origin or destination):
            raise Exception('at least one of origin and destination must be not None')
        super(ArcSearch, self).__init__()
        self._keys_only = keys_only
        if origin and destination:
            self._query = arc_class.query_by_origin_and_destination(origin, destination)
        elif origin:
            self._query = arc_class.find_destinations(origin)
        else:
            self._query = arc_class.find_origins(destination)
        self._future = None

    def set_up(self):
        self._future = self._query.fetch_async(keys_only=self._keys_only)

    def do_business(self):
        self.result = self._future.get_result()


class ArcNodeSearchBase(ArcSearch):
    def __init__(self, arc_class, origin=None, destination=None):
        super(ArcNodeSearchBase, self).__init__(arc_class, origin, destination, False)
        if origin and destination:
            raise Exception('only one of origin or destination can be not None')
        elif origin:
            self._cache_key = destinations_cache_key(arc_class, origin)
            self._arc_property = 'destination'
        else:
            self._arc_property = 'origin'
            self._cache_key = origins_cache_key(arc_class, destination)
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


class DestinationsSearch(ArcNodeSearchBase):
    def __init__(self, arc_class, origin):
        super(DestinationsSearch, self).__init__(arc_class, origin)


class SingleDestinationSearch(DestinationsSearch):
    def do_business(self):
        DestinationsSearch.do_business(self)
        self.result = self.result[0] if self.result else None


class OriginsSearch(ArcNodeSearchBase):
    def __init__(self, arc_class, destination):
        super(OriginsSearch, self).__init__(arc_class, destination=destination)


class SingleOriginSearch(OriginsSearch):
    def do_business(self):
        OriginsSearch.do_business(self)
        self.result = self.result[0] if self.result else None


class UpdateNode(UpdateCommand):
    def __init__(self, model_key, **form_parameters):
        super(UpdateNode, self).__init__(to_node_key(model_key), **form_parameters)


class DeleteNode(DeleteCommand):
    def __init__(self, *model_keys):
        super(DeleteNode, self).__init__(*[to_node_key(m) for m in model_keys])


class DeleteArcs(ArcSearch):
    def __init__(self, arc_class, origin=None, destination=None):
        super(DeleteArcs, self).__init__(arc_class, origin, destination, True)
        self._arc_delete_future = None
        self._cache_keys = []
        if origin:
            self._cache_keys.append(destinations_cache_key(arc_class, origin))
        if destination:
            self._cache_keys.append(origins_cache_key(arc_class, destination))

    def do_business(self):
        super(DeleteArcs, self).do_business()
        if self.result:
            ndb.delete_multi(self.result)
            memcache.delete_multi(self._cache_keys)







