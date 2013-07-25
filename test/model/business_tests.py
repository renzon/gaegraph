# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from google.appengine.api import memcache
from google.appengine.ext import ndb
from gaebusiness import business
from gaegraph.business_base import NodeSearch, NeighborsSearch
from gaegraph.model import Node, Arc, neighbors_cache_key
from model.util import GAETestCase




class NodeAccessTests(GAETestCase):
    def test_execution(self):
        node_search = NodeSearch("1")
        node_search.execute()
        self.assertIsNone(node_search.result)
        node_key = Node(id=1).put()
        node_search.execute()
        self.assertEqual(node_key, node_search.result.key)


class NeighborsTests(GAETestCase):
    def test_search(self):
        origin = Node()
        neighbors = [Node() for i in xrange(3)]
        ndb.put_multi([origin] + neighbors)
        arcs = [Arc(origin=origin.key, destination=d.key) for d in neighbors]
        ndb.put_multi(arcs)
        search = NeighborsSearch(Arc, origin)
        search.execute()
        expected_keys = [n.key for n in neighbors]
        actual_keys = [n.key for n in search.result]
        self.assertItemsEqual(expected_keys, actual_keys)
        cache_keys = memcache.get(neighbors_cache_key(Arc, origin))
        self.assertItemsEqual(expected_keys, cache_keys)

