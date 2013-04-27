# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals


class UseCaseException(Exception):
    pass


class UseCase(object):
    def __init__(self):
        self.errors = {}

    def validate_inputs(self, *args, **kwargs):
        raise NotImplementedError()

    def do_logic(self, *args, **kwargs):
        raise NotImplementedError()

    def do_business(self, *args, **kwargs):
        errors = self.validate_inputs()
        if errors:
            self.errors = errors
            raise UseCaseException()
        return self.do_logic(*args, **kwargs)