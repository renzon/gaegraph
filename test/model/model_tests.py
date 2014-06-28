# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import unittest
from google.appengine.ext import ndb

from gaegraph import model
from gaegraph.model import Node, Arc, destinations_cache_key
from model.util import GAETestCase
from mommygae import mommy


class ModelTests(GAETestCase):
    def test_to_node_key(self):
        node = Node(id=1)
        self.assertEqual(node.key, model.to_node_key(1))
        self.assertEqual(node.key, model.to_node_key("1"))
        self.assertEqual(node.key, model.to_node_key(node.key))
        self.assertEqual(node.key, model.to_node_key(node))

    def test_query_by_creation(self):
        nodes = [mommy.save_one(Node) for i in range(4)]
        self.assertListEqual(nodes, Node.query_by_creation().fetch())

    def test_to_dict(self):
        class NodeMock(Node):
            attr = ndb.StringProperty()

        node = NodeMock(id=1, attr='foo')
        node.put()
        # to_dict without arguments
        dct = node.to_dict()
        self.assertEqual(4, len(dct))
        self.assertEqual('1', dct['id'])
        self.assertEqual('foo', dct['attr'])
        self.assertIsNotNone(dct['creation'])

        # with exclude arguments
        dct = node.to_dict(exclude=('creation', 'class_'))
        self.assertDictEqual({'id': '1', 'attr': 'foo'}, dct)
        dct = node.to_dict(exclude=('creation', 'class_', 'id'))
        self.assertDictEqual({'attr': 'foo'}, dct)

        # with exclude arguments
        dct = node.to_dict(include=('id', 'attr'))
        self.assertDictEqual({'id': '1', 'attr': 'foo'}, dct)
        dct = node.to_dict(include=('attr',))
        self.assertDictEqual({'attr': 'foo'}, dct)


class ArcTests(GAETestCase):
    def assert_keys_assignment(self, n, n2, origin_key, destination_key):
        a = Arc(n, n2)
        self.assertEqual(a.origin, origin_key)
        self.assertEqual(a.destination, destination_key)

    def test_init(self):
        n = Node(id=1)
        n.put()
        n2 = Node(id=2)
        n2.put()
        self.assert_keys_assignment(n, n2, n.key, n2.key)
        self.assert_keys_assignment(n.key, n2.key, n.key, n2.key)
        self.assert_keys_assignment(1, 2, n.key, n2.key)
        self.assert_keys_assignment('1', '2', n.key, n2.key)


    def test_neighbors(self):
        root = Node(id=1)
        neighbors = [Node(id=i) for i in xrange(2, 5)]
        arcs = [Arc(origin=root.key, destination=n.key) for n in neighbors]
        ndb.put_multi(arcs + neighbors + [root])
        searched_arcs = Arc.find_destinations(root).fetch(10)
        searched_neighbors_keys = [a.destination for a in searched_arcs]
        neighbors_keys = [n.key for n in neighbors]
        self.assertListEqual(neighbors_keys, searched_neighbors_keys)

    def test_neighbors_cache_key(self):
        node = Node(id=1)
        self.assertEqual("Arc1", destinations_cache_key(Arc, node))

        class SubArc(Arc):
            pass

        self.assertEqual("SubArc1", destinations_cache_key(SubArc, node))

