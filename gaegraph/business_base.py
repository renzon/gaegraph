# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from google.appengine.api import memcache
from google.appengine.ext import ndb
from gaebusiness.business import Command
from gaebusiness.gaeutil import UpdateCommand, DeleteCommand
from gaegraph.model import Node, destinations_cache_key, origins_cache_key, to_node_key

LONG_ERROR = "LONG_ERROR"


class NodeSearch(Command):
    '''
    Usecase for search a result by its id
    '''

    def __init__(self, node_or_key_or_id):
        super(NodeSearch, self).__init__()
        self.node_key = to_node_key(node_or_key_or_id)
        self._future = None


    def set_up(self):
        self._future = self.node_key.get_async()

    def do_business(self, stop_on_error=False):
        self.result = self._future.get_result()


class ArcSearchBase(Command):
    def __init__(self, arc_cls, node, cache_key_fcn, arc_property, error_key, query):
        super(ArcSearchBase, self).__init__()
        self._cache_key = cache_key_fcn(arc_cls, node)
        self.node = node
        self.arc_cls = arc_cls
        self._nodes_cached_keys = None
        self._arc_property = arc_property
        self.result = []
        self._error_key = error_key
        self._query = query

    def set_up(self):
        try:
            self._nodes_cached_keys = memcache.get(self._cache_key)
        except Exception:
            # If memcache fails, do nothing
            pass
        try:
            if not self._nodes_cached_keys:
                query = self._query(self.node)
                self._future = query.fetch_async()
        except ValueError:
            self.add_error(self._error_key, LONG_ERROR)

    def do_business(self, stop_on_error=False):
        cached_keys = self._nodes_cached_keys
        if not cached_keys:
            cached_keys = [getattr(arc, self._arc_property) for arc in self._future.get_result()]
            if cached_keys:
                memcache.set(self._cache_key, cached_keys)
        if cached_keys:
            self.result = ndb.get_multi(cached_keys)


class DestinationsSearch(ArcSearchBase):
    def __init__(self, arc_cls, origin, **kwargs):
        super(DestinationsSearch, self).__init__(arc_cls, origin, destinations_cache_key, 'destination', 'origin',
                                                 arc_cls.find_destinations, **kwargs)


class SingleDestinationSearh(DestinationsSearch):
    def do_business(self, stop_on_error=False):
        DestinationsSearch.do_business(self, stop_on_error)
        self.result = self.result[0] if self.result else None


class OriginsSearch(ArcSearchBase):
    def __init__(self, arc_cls, destination, **kwargs):
        super(OriginsSearch, self).__init__(arc_cls, destination, origins_cache_key, 'origin', 'destination',
                                            arc_cls.find_origins, **kwargs)


class SingleOriginSearh(OriginsSearch):
    def do_business(self, stop_on_error=False):
        OriginsSearch.do_business(self, stop_on_error)
        self.result = self.result[0] if self.result else None


class UpdateNode(UpdateCommand):
    def __init__(self, model_key, **form_parameters):
        super(UpdateNode, self).__init__(to_node_key(model_key), **form_parameters)


class DeleteNode(DeleteCommand):
    def __init__(self, *model_keys):
        super(DeleteNode, self).__init__(*[to_node_key(m) for m in model_keys])