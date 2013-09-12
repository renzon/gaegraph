# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import unittest
import urllib
from google.appengine.api import urlfetch
from gaebusiness import gaeutil
from gaebusiness.gaeutil import UrlFecthCommand, TaskQueueCommand
from mock import Mock


class UrlfecthTests(unittest.TestCase):
    def test_https_post(self):
        params = {'id': 'foo', 'token': 'bar'}
        url = 'https://foo.bar.com/rest'
        rpc = Mock()
        result = Mock()
        result.status_code = 200
        result.content = '{"ticket":"123456"}'
        rpc.get_result = Mock(return_value=result)
        gaeutil.urlfetch.create_rpc = Mock(return_value=rpc)
        fetch = Mock()
        gaeutil.urlfetch.make_fetch_call = fetch
        command = UrlFecthCommand(url, params, urlfetch.POST)
        command.execute()
        self.assertEqual(result, command.result)
        fetch.assert_called_once_with(rpc, url, urllib.urlencode(params), method=urlfetch.POST,
                                      validate_certificate=True, headers={})

    def test_http_get(self):
        params = {'id': 'foo', 'token': 'bar'}
        url = 'http://foo.bar.com/rest'
        rpc = Mock()
        result = Mock()
        result.status_code = 200
        result.content = '{"ticket":"123456"}'
        rpc.get_result = Mock(return_value=result)
        gaeutil.urlfetch.create_rpc = Mock(return_value=rpc)
        fetch = Mock()
        gaeutil.urlfetch.make_fetch_call = fetch
        command = UrlFecthCommand(url, params, validate_certificate=False)
        command.execute()
        self.assertEqual(result, command.result)
        fetch.assert_called_once_with(rpc, '%s?%s' % (url, urllib.urlencode(params)), None, method=urlfetch.GET,
                                      validate_certificate=False, headers={})


class TaskQueueTests(unittest.TestCase):
    def test_queue_creation(self):
        task_mock = Mock()
        rpc_mock = Mock()
        queue_mock = Mock()
        gaeutil.Queue = queue_mock
        gaeutil.taskqueue.create_rpc = Mock(return_value=rpc_mock)
        gaeutil.Task = task_mock
        queue_name = 'foo'
        params = {'param1': 'bar'}
        url = '/mytask'
        cmd = TaskQueueCommand(queue_name, url, params=params)
        cmd.execute()
        task_mock.assert_called_once_with(url=url, params=params)
        queue_mock.add_async.assert_called_once_with(queue_name, rpc=rpc_mock)
        rpc_mock.get_result.assert_called_once_with()
