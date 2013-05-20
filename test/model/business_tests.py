# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from google.appengine.ext import ndb
from gaegraph import business
from gaegraph.business import UseCase
from model.util import GAETestCase


class ModelMock(ndb.Model):
    ppt=ndb.StringProperty()

ERROR_KEY="error_key"
ERROR_MSG="TEST_ERROR"

class UseCaseMock(UseCase):
    def __init__(self,model_ppt,business_error=False):
        super(UseCaseMock,self).__init__()
        self.business_error=business_error
        self.set_up_executed=False
        self.commit_executed=False
        self._model_ppt=model_ppt
        self.model=None

    def set_up(self):
        if self.business_error:
            self.add_error(ERROR_KEY,ERROR_MSG)
        self.set_up_executed=True

    def do_business(self):
        self.model=ModelMock(ppt=self._model_ppt)

    def commit(self):
        return self.model

class BusinessTests(GAETestCase):
    def self_assert_usecase_executed(self,usecase,model_ppt):
        self.assertTrue(usecase.set_up_executed)
        self.assertEqual(model_ppt,usecase.model.ppt,"do_business not executed")
        self.assertIsNotNone(usecase.model.key,"model should be saved on db")

    def self_assert_usecase_not_executed(self,usecase):
        self.assertTrue(usecase.set_up_executed)
        self.assertIsNone(usecase.model)


    def test_execute_successful_business(self):
        MOCK_1="mock 1"
        MOCK_2="mock 2"
        usecases=[UseCaseMock(MOCK_1),UseCaseMock(MOCK_2)]
        errors=business.execute(usecases)
        self.self_assert_usecase_executed(usecases[0],MOCK_1)
        self.self_assert_usecase_executed(usecases[1],MOCK_2)
        self.assertDictEqual({},errors)

    def test_execute_business_not_stopping_on_error(self):
        MOCK_1="mock 1"
        MOCK_2="mock 2"
        usecases=[UseCaseMock(MOCK_1,True),UseCaseMock(MOCK_2)]
        errors=business.execute(usecases)
        self.self_assert_usecase_not_executed(usecases[0])
        self.self_assert_usecase_executed(usecases[1],MOCK_2)
        self.assertDictEqual({ERROR_KEY,ERROR_MSG},errors)

    def test_execute_business_stopping_on_error(self):
        MOCK_1="mock 1"
        MOCK_2="mock 2"
        usecases=[UseCaseMock(MOCK_1,True),UseCaseMock(MOCK_2)]
        errors=business.execute(usecases,True)
        self.self_assert_usecase_not_executed(usecases[0])
        self.self_assert_usecase_not_executed(usecases[0])
        self.assertDictEqual({ERROR_KEY,ERROR_MSG},errors)





