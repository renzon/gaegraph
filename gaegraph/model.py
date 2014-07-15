# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.ext.ndb.polymodel import PolyModel


class Node(PolyModel):
    creation = ndb.DateTimeProperty(auto_now_add=True)

    @classmethod
    def query_by_creation(cls):
        return cls.query().order(cls.creation)

    @classmethod
    def query_by_creation_desc(cls):
        return cls.query().order(-cls.creation)

    def to_dict(self, include=None, exclude=None):
        if include is None or 'class_' not in include:
            exclude = exclude or []
            exclude.append('class_')

        dct = super(Node, self).to_dict(include=include, exclude=exclude)
        if include:
            if 'id' in include and self.key:
                dct['id'] = str(self.key.id())
        elif (exclude is None or 'id' not in exclude) and self.key:
            dct['id'] = str(self.key.id())
        return dct


def to_node_key(arg):
    if isinstance(arg, ndb.Key):
        return arg
    elif isinstance(arg, ndb.Model):
        return arg.key
    return ndb.Key(Node, long(arg))


class Arc(PolyModel):
    def __init__(self, origin=None, destination=None, **kwargs):
        if origin:
            origin = to_node_key(origin)
        if destination:
            destination = to_node_key(destination)
        PolyModel.__init__(self, origin=origin, destination=destination, **kwargs)

    creation = ndb.DateTimeProperty(auto_now_add=True)
    origin = ndb.KeyProperty(Node, required=True)
    destination = ndb.KeyProperty(Node, required=True)

    @classmethod
    def default_order(cls):
        return cls.creation

    @classmethod
    def find_destinations(cls, node):
        node = to_node_key(node)
        return cls.query(cls.origin == node).order(cls.default_order())

    @classmethod
    def query_by_origin_and_destination(cls, origin, destination):
        origin = to_node_key(origin)
        destination = to_node_key(destination)
        return cls.query(cls.origin == origin, cls.destination == destination).order(cls.default_order())

    @classmethod
    def find_origins(cls, node):
        node = to_node_key(node)
        return cls.query(cls.destination == node).order(cls.default_order())

    def _pre_put_hook(self):
        if hasattr(self, 'key'):
            origins_key = origins_cache_key(self.__class__, self.destination)
            destinations_key = destinations_cache_key(self.__class__, self.origin)
            memcache.delete_multi([origins_key, destinations_key])


def destinations_cache_key(arc_cls, origin):
    return arc_cls.__name__ + str(to_node_key(origin).id())


def origins_cache_key(arc_cls, destination):
    return 'o' + destinations_cache_key(arc_cls, destination)

