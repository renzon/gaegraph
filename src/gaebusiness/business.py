# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from google.appengine.ext import ndb


def to_model_list(models):
    if models is None:
        return []
    return [models] if isinstance(models, ndb.Model) else models

class Command(object):
    def __init__(self):
        self.errors = {}
        self.result = None

    def add_error(self, key, msg):
        self.errors[key] = msg

    def set_up(self):
        '''
        Must set_up data for business.
        It should fetch data asyncrounously if need
        '''
        pass

    def do_business(self):
        '''
        Must do the main business of use case
        '''
        raise NotImplementedError()

    def commit(self):
        '''
        Must return a Model, or a list of it to be commited on DB
        '''
        return []

    def execute(self,stop_on_error=False):
        self.set_up()
        self.do_business()
        if not self.errors:
            ndb.put_multi(to_model_list(self.commit()))

class CommandList(Command):
    def __init__(self,commands):
        super(CommandList,self).__init__()
        self.commands=commands

    def execute(self,stop_on_error=False):
        '''
        :param stop_on_error: boolean. Indicate if should stop running next commands if a error ocurs
        Executes a list of commands asynchronously,
        first the set_up, second the do_business and last the commit
        '''
        for setting_up_command in self.commands:
            setting_up_command.set_up()

        for business_command in self.commands:
            if business_command.errors:
                if stop_on_error:
                    return business_command.errors
            else:
                business_command.do_business()

        to_commit = []
        for committing_command in self.commands:
            to_commit.extend(to_model_list(committing_command.commit()))
        if to_commit:
            ndb.put_multi(to_commit)

        for command in self.commands:
            self.errors.update(command.errors)
        return self.errors
