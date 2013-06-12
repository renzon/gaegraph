# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from google.appengine.api import memcache
from google.appengine.ext import ndb
from gaebusiness.business import UseCase
from gaegraph.model import Node, neighbors_cache_key

LONG_ERROR = "LONG_ERROR"


class NodeSearch(UseCase):
    '''
    Usecase for search a result by its id
    '''

    def __init__(self, id):
        super(NodeSearch, self).__init__()
        self.id = id

    def set_up(self):
        try:
            id = long(self.id)
            self._future = Node._get_by_id_async(id)
        except ValueError:
            self.add_error("id", LONG_ERROR)

    def do_business(self):
        self.result = self._future.get_result()


class NeighborsSearch(UseCase):
    def __init__(self, arc_cls, origin):
        super(NeighborsSearch, self).__init__()
        self.origin = origin
        self.arc_cls = arc_cls
        self._cache_key = neighbors_cache_key(arc_cls, origin)
        self._neighbors_cached_keys = None
        self.result=[]

    def set_up(self):
        try:
            self._neighbors_cached_keys = memcache.get(self._cache_key)
        except Exception:
            # If memcache fails, do nothing
            pass
        try:
            if self._neighbors_cached_keys is None:
                query = self.arc_cls.neighbors(self.origin)
                self._future = query.fetch_async()
        except ValueError:
            self.add_error("origin", LONG_ERROR)

    def do_business(self):
        neighbor_keys= self._neighbors_cached_keys
        if neighbor_keys is None:
            neighbor_keys = [arc.destination for arc in self._future.get_result()]
            memcache.set(self._cache_key, neighbor_keys)
        if neighbor_keys:
            self.result = ndb.get_multi(neighbor_keys)




