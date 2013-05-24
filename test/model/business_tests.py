# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from google.appengine.api import memcache
from google.appengine.ext import ndb
from gaegraph import business
from gaegraph.business import UseCase
from gaegraph.business_base import NodeSearch, NeighborsSearch
from gaegraph.model import Node, Arc, neighbors_cache_key
from model.util import GAETestCase


class ModelMock(ndb.Model):
    ppt = ndb.StringProperty()


ERROR_KEY = "error_key"
ERROR_MSG = "TEST_ERROR"


class UseCaseMock(UseCase):
    def __init__(self, model_ppt, business_error=False):
        super(UseCaseMock, self).__init__()
        self.business_error = business_error
        self.set_up_executed = False
        self.commit_executed = False
        self._model_ppt = model_ppt
        self.model = None

    def set_up(self):
        if self.business_error:
            self.add_error(ERROR_KEY, ERROR_MSG)
        self.set_up_executed = True

    def do_business(self):
        self.model = ModelMock(ppt=self._model_ppt)

    def commit(self):
        return self.model


class BusinessTests(GAETestCase):
    def assert_usecase_executed(self, usecase, model_ppt):
        self.assertTrue(usecase.set_up_executed)
        self.assertEqual(model_ppt, usecase.model.ppt, "do_business not executed")
        self.assertIsNotNone(usecase.model.key, "model should be saved on db")

    def assert_usecase_not_executed(self, usecase):
        self.assertTrue(usecase.set_up_executed)
        self.assertIsNone(usecase.model)


    def test_execute_successful_business(self):
        MOCK_1 = "mock 1"
        MOCK_2 = "mock 2"
        usecases = [UseCaseMock(MOCK_1), UseCaseMock(MOCK_2)]
        errors = business.execute(usecases)
        self.assert_usecase_executed(usecases[0], MOCK_1)
        self.assert_usecase_executed(usecases[1], MOCK_2)
        self.assertDictEqual({}, errors)

    def test_execute_business_not_stopping_on_error(self):
        MOCK_1 = "mock 1"
        MOCK_2 = "mock 2"
        usecases = [UseCaseMock(MOCK_1, True), UseCaseMock(MOCK_2)]
        errors = business.execute(usecases)
        self.assert_usecase_not_executed(usecases[0])
        self.assert_usecase_executed(usecases[1], MOCK_2)
        self.assertDictEqual({ERROR_KEY: ERROR_MSG}, errors)

    def test_execute_business_stopping_on_error(self):
        MOCK_1 = "mock 1"
        MOCK_2 = "mock 2"
        usecases = [UseCaseMock(MOCK_1, True), UseCaseMock(MOCK_2)]
        errors = business.execute(usecases, True)
        self.assert_usecase_not_executed(usecases[0])
        self.assert_usecase_not_executed(usecases[0])
        self.assertDictEqual({ERROR_KEY: ERROR_MSG}, errors)


class NodeAccessTests(GAETestCase):
    def test_execution(self):
        node_search = NodeSearch("1")
        business.execute(node_search)
        self.assertIsNone(node_search.node)
        node_key = Node(id=1).put()
        business.execute(node_search)
        self.assertEqual(node_key, node_search.node.key)


class NeighborsTests(GAETestCase):
    def test_search(self):
        origin = Node()
        neighbors = [Node() for i in xrange(3)]
        ndb.put_multi([origin] + neighbors)
        arcs = [Arc(origin=origin.key, destination=d.key) for d in neighbors]
        ndb.put_multi(arcs)
        search = NeighborsSearch(Arc, origin)
        business.execute(search)
        expected_keys = [n.key for n in neighbors]
        actual_keys = [n.key for n in search.neighbors]
        self.assertItemsEqual(expected_keys, actual_keys)
        neighbors_in_cache = memcache.get(neighbors_cache_key(Arc, origin))
        cache_keys = [n.key for n in neighbors_in_cache]
        self.assertItemsEqual(expected_keys, cache_keys)

