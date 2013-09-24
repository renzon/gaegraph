# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from google.appengine.api import memcache
from google.appengine.ext import ndb
from gaebusiness.business import Command
from gaegraph.model import Node, destinations_cache_key, origins_cache_key

LONG_ERROR = "LONG_ERROR"


class NodeSearch(Command):
    '''
    Usecase for search a result by its id
    '''

    def __init__(self, id, **kwargs):
        super(NodeSearch, self).__init__(id=id, **kwargs)


    def set_up(self):
        try:
            id = long(self.id)
            self._future = Node._get_by_id_async(id)
        except ValueError:
            self.add_error("id", LONG_ERROR)

    def do_business(self, stop_on_error=False):
        self.result = self._future.get_result()


class ArcSearchBase(Command):
    def __init__(self, arc_cls, node, cache_key_fcn, arc_property, error_key, query, **kwargs):
        super(ArcSearchBase, self).__init__(node=node, arc_cls=arc_cls, **kwargs)
        self._cache_key = cache_key_fcn(arc_cls, node)
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


class OriginsSearch(ArcSearchBase):
    def __init__(self, arc_cls, destination, **kwargs):
        super(OriginsSearch, self).__init__(arc_cls, destination, origins_cache_key, 'origin', 'destination',
                                            arc_cls.find_origins, **kwargs)

