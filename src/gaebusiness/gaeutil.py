# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import urllib
from google.appengine.api import urlfetch
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

