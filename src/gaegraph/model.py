# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from google.appengine.ext import ndb
from google.appengine.ext.ndb.polymodel import PolyModel


class Node(PolyModel):
    creation = ndb.DateTimeProperty(auto_now_add=True)


def to_node_key(arg):
    if isinstance(arg, ndb.Key):
        return arg
    elif isinstance(arg, ndb.Model):
        return arg.key
    return ndb.Key(Node, long(arg))


class Arc(PolyModel):
    creation = ndb.DateTimeProperty(auto_now_add=True)
    origin = ndb.KeyProperty(Node, required=True)
    destination = ndb.KeyProperty(Node, required=True)

    @classmethod
    def default_order(cls):
        return cls.creation

    @classmethod
    def neighbors(cls, node):
        node = to_node_key(node)
        return cls.query(cls.origin == node).order(cls.default_order())


def neighbors_cache_key(arc_cls, origin):
    return arc_cls.__name__ + str(to_node_key(origin).id())
