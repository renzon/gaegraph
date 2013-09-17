# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from google.appengine.ext import ndb


def to_model_list(models):
    if models is None:
        return []
    return [models] if isinstance(models, ndb.Model) else models


class Command(object):
    def __init__(self, **kwargs):
        self.errors = {}
        self.result = None
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

    def add_error(self, key, msg):
        self.errors[key] = msg

    def set_up(self):
        '''
        Must set_up data for business.
        It should fetch data asyncrounously if needed
        '''
        pass

    def do_business(self, stop_on_error=False):
        '''
        Must do the main business of use case
        '''
        raise NotImplementedError()

    def commit(self):
        '''
        Must return a Model, or a list of it to be commited on DB
        '''
        return []

    def execute(self, stop_on_error=False):
        self.set_up()
        self.do_business(stop_on_error)
        ndb.put_multi(to_model_list(self.commit()))
        return self.errors


class CommandList(Command):
    def __init__(self, commands, **kwargs):
        super(CommandList, self).__init__(**kwargs)
        self.commands = commands


    def set_up(self):
        for cmd in self.commands:
            cmd.set_up()

    def do_business(self, stop_on_error=False):
        for cmd in self.commands:
            if not cmd.errors:
                cmd.do_business(stop_on_error)
            self.errors.update(cmd.errors)
            if stop_on_error and self.errors:
                return self.errors
        return self.errors

    def commit(self):
        to_commit = []
        for cmd in self.commands:
            to_commit.extend(to_model_list(cmd.commit()))
        return to_commit
