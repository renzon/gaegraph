# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import urllib
from google.appengine.api import urlfetch, taskqueue
from google.appengine.api.labs.taskqueue.taskqueue import Task
from google.appengine.api.taskqueue.taskqueue import Queue
from gaebusiness.business import Command


class UrlFecthCommand(Command):
    def __init__(self, url, params={}, method=urlfetch.GET, headers={}, validate_certificate=True):
        super(UrlFecthCommand, self).__init__()
        self._method = method
        self._headers = headers
        self._validate_certificate = validate_certificate
        self._url = url
        self._params = None
        if params:
            encoded_params = urllib.urlencode(params)
            if method in (urlfetch.POST, urlfetch.PUT, urlfetch.PATCH):
                self._params = encoded_params
            else:
                self._url = "%s?%s" % (url, encoded_params)

    def set_up(self):
        self._rpc = urlfetch.create_rpc()
        urlfetch.make_fetch_call(self._rpc, self._url, self._params, method=self._method,
                                 validate_certificate=self._validate_certificate, headers=self._headers)

    def do_business(self, stop_on_error=False):
        self.result = self._rpc.get_result()


class TaskQueueCommand(Command):
    def __init__(self, queue_name, url, **kwargs):
        '''
        kwargs are the same used on Task class
        (https://developers.google.com/appengine/docs/python/taskqueue/tasks#Task)
        '''
        super(TaskQueueCommand, self).__init__()
        self._task = Task(url=url, **kwargs)
        self._queue_name = queue_name


    def set_up(self):
        self._rpc = taskqueue.create_rpc()
        q=Queue(self._queue_name)
        q.add_async(self._task, rpc=self._rpc)

    def do_business(self, stop_on_error=False):
        self._rpc.get_result()


