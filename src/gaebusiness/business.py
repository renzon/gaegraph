# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from google.appengine.ext import ndb


class UseCaseException(Exception):
    pass


class UseCase(object):
    def __init__(self):
        self.errors = {}
        self.result=None

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


def execute(use_cases, stop_on_error=False):
    '''
    :param use_cases: list of UseCase or a single one to be executed
    :param stop_on_error: boolean. Indicate if should stop running next use_cases if a error ocurs
    Executes a list of use_cases asynchronously,
    first the set_up, later the do_business if there are and last
    '''
    if isinstance(use_cases, UseCase):
        use_cases = [use_cases]

    for setting_up_uc in use_cases:
        setting_up_uc.set_up()

    for business_uc in use_cases:
        if business_uc.errors:
            if stop_on_error:
                return business_uc.errors
        else:
            business_uc.do_business()

    def to_model_list(models):
        return [models] if isinstance(models, ndb.Model) else models

    to_commit = []
    for committing_uc in use_cases:
        if not committing_uc.errors:
            to_commit.extend(to_model_list(committing_uc.commit()))
    if to_commit:
        ndb.put_multi(to_commit)

    errors = {}
    for uc in use_cases:
        errors.update(uc.errors)
    return errors

