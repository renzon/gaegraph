# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import unittest
from google.appengine.ext import ndb

from gaegraph import model
from gaegraph.model import Node, Arc, neighbors_cache_key
from model.util import GAETestCase


class modelTests(unittest.TestCase):
    def test_to_node_key(self):
        node = Node(id=1)
        self.assertEqual(node.key, model.to_node_key(1))
        self.assertEqual(node.key, model.to_node_key("1"))
        self.assertEqual(node.key, model.to_node_key(node.key))
        self.assertEqual(node.key, model.to_node_key(node))


class ArcTests(GAETestCase):
    def test_neighbors(self):
        root = Node(id=1)
        neighbors = [Node(id=i) for i in xrange(2, 5)]
        arcs = [Arc(origin=root.key, destination=n.key) for n in neighbors]
        ndb.put_multi(arcs + neighbors + [root])
        searched_arcs = Arc.neighbors(root).fetch(10)
        searched_neighbors_keys = [a.destination for a in searched_arcs]
        neighbors_keys = [n.key for n in neighbors]
        self.assertListEqual(neighbors_keys, searched_neighbors_keys)

    def test_neighbors_cache_key(self):
        node = Node(id=1)
        self.assertEqual("Arc1", neighbors_cache_key(Arc, node))

        class SubArc(Arc):
            pass

        self.assertEqual("SubArc1", neighbors_cache_key(SubArc, node))

