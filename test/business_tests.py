# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from google.appengine.ext import ndb
from gaebusiness import business
from gaebusiness.business import Command, CommandList
from util import GAETestCase


class ModelMock(ndb.Model):
    ppt = ndb.StringProperty()


ERROR_KEY = "error_key"
ERROR_MSG = "TEST_ERROR"


class CommandMock(Command):
    def __init__(self, model_ppt, business_error=False):
        super(CommandMock, self).__init__()
        self.business_error = business_error
        self.set_up_executed = False
        self.commit_executed = False
        self._model_ppt = model_ppt
        self.result = None

    def set_up(self):
        if self.business_error:
            self.add_error(ERROR_KEY, ERROR_MSG)
        self.set_up_executed = True

    def do_business(self):
        self.result = ModelMock(ppt=self._model_ppt)

    def commit(self):
        return self.result


class BusinessTests(GAETestCase):
    def assert_usecase_executed(self, usecase, model_ppt):
        self.assertTrue(usecase.set_up_executed)
        self.assertEqual(model_ppt, usecase.result.ppt, "do_business not executed")
        self.assertIsNotNone(usecase.result.key, "result should be saved on db")

    def assert_usecase_not_executed(self, usecase):
        self.assertTrue(usecase.set_up_executed)
        self.assertIsNone(usecase.result)


    def test_execute_successful_business(self):
        MOCK_1 = "mock 1"
        MOCK_2 = "mock 2"
        commands=[CommandMock(MOCK_1), CommandMock(MOCK_2)]
        command_list = CommandList(commands)
        errors = command_list.execute()
        self.assert_usecase_executed(commands[0], MOCK_1)
        self.assert_usecase_executed(commands[1], MOCK_2)
        self.assertDictEqual({}, errors)

    def test_execute_business_not_stopping_on_error(self):
        MOCK_1 = "mock 1"
        MOCK_2 = "mock 2"
        commands = [CommandMock(MOCK_1, True), CommandMock(MOCK_2)]
        command_list = CommandList(commands)
        errors = command_list.execute()
        self.assert_usecase_not_executed(commands[0])
        self.assert_usecase_executed(commands[1], MOCK_2)
        self.assertDictEqual({ERROR_KEY: ERROR_MSG}, errors)

    def test_execute_business_stopping_on_error(self):
        MOCK_1 = "mock 1"
        MOCK_2 = "mock 2"
        commands = [CommandMock(MOCK_1, True), CommandMock(MOCK_2)]
        command_list = CommandList(commands)
        errors = command_list.execute(True)
        self.assert_usecase_not_executed(commands[0])
        self.assert_usecase_not_executed(commands[0])
        self.assertDictEqual({ERROR_KEY: ERROR_MSG}, errors)


