# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from google.appengine.api import memcache
from google.appengine.ext import ndb
from gaegraph.business_base import NodeSearch, DestinationsSearch, OriginsSearch, SingleDestinationSearh, SingleOriginSearh
from gaegraph.model import Node, Arc, destinations_cache_key, origins_cache_key
from model.util import GAETestCase


class NodeAccessTests(GAETestCase):
    def test_execution(self):
        node_search = NodeSearch("1")
        node_search.execute()
        self.assertIsNone(node_search.result)
        node_key = Node(id=1).put()
        node_search.execute()
        self.assertEqual(node_key, node_search.result.key)


class ArcSearchTests(GAETestCase):
    def test_destinations_search(self):
        origin = Node()
        destinations = [Node() for i in xrange(3)]
        ndb.put_multi([origin] + destinations)
        arcs = [Arc(origin=origin.key, destination=d.key) for d in destinations]
        ndb.put_multi(arcs)
        search = DestinationsSearch(Arc, origin)
        search.execute()
        expected_keys = [n.key for n in destinations]
        actual_keys = [n.key for n in search.result]
        self.assertItemsEqual(expected_keys, actual_keys)
        cache_keys = memcache.get(destinations_cache_key(Arc, origin))
        self.assertItemsEqual(expected_keys, cache_keys)

        # Assert Arcs are removed from cache
        Arc(origin=origin.key, destination=destinations[0].key).put()
        self.assertIsNone(memcache.get(destinations_cache_key(Arc, origin)))

    def test_origins_search(self):
        destination = Node()
        origins = [Node() for i in xrange(3)]
        ndb.put_multi([destination] + origins)
        arcs = [Arc(origin=ori.key, destination=destination.key) for ori in origins]
        ndb.put_multi(arcs)
        search = OriginsSearch(Arc, destination)
        search.execute()
        expected_keys = [n.key for n in origins]
        actual_keys = [n.key for n in search.result]
        self.assertItemsEqual(expected_keys, actual_keys)
        cache_keys = memcache.get(origins_cache_key(Arc, destination))
        self.assertItemsEqual(expected_keys, cache_keys)

        # Assert Arcs are removed from cache
        Arc(origin=origins[0].key, destination=destination.key).put()
        self.assertIsNone(memcache.get(origins_cache_key(Arc, destination)))

    def test_single_destination_search(self):
        destination = Node()
        origin = Node()
        ndb.put_multi([destination, origin])
        search = SingleDestinationSearh(Arc, origin).execute()
        self.assertIsNone(search.result)
        Arc(origin=origin, destination=destination).put()
        search = SingleDestinationSearh(Arc, origin).execute()
        self.assertEqual(destination.key, search.result.key)

    def test_single_origin_search(self):
        destination = Node()
        origin = Node()
        ndb.put_multi([destination, origin])
        search = SingleOriginSearh(Arc, destination).execute()
        self.assertIsNone(search.result)
        Arc(origin=origin, destination=destination).put()
        search = SingleOriginSearh(Arc, destination).execute()
        self.assertEqual(origin.key, search.result.key)
