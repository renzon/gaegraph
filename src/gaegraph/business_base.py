# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from gaegraph.business import UseCase
from gaegraph.model import Node

LONG_ERROR="LONG_ERROR"


class NodeSearch(UseCase):
    def __init__(self, id):
        super(NodeSearch,self).__init__()
        self.id = id

    def set_up(self):
        try:
            id=long(self.id)
            self._future = Node._get_by_id_async(id)
        except ValueError:
            self.add_error("id",LONG_ERROR)

    def do_business(self):
        self.node=self._future.get_result()
