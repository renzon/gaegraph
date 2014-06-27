# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import os

SRC_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.join(SRC_DIR, '..')
SRC_DIR = os.path.normpath(SRC_DIR)


def _create_dir_if_not_existing(package_path):
    if not os.path.exists(package_path):
        os.mkdir(package_path)


def _create_file_if_not_existing(file_path, content=''):
    if not os.path.isfile(file_path):
        with open(file_path, 'w') as f:
            f.write(content.encode('utf8'))


PY_HEADER = '''# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals'''


def _create_package(package_path):
    _create_dir_if_not_existing(package_path)
    _create_file_if_not_existing(os.path.join(package_path, '__init__.py'))
    _create_file_if_not_existing(os.path.join(package_path, 'model.py'), PY_HEADER)
    _create_file_if_not_existing(os.path.join(package_path, 'commands.py'), PY_HEADER)
    _create_file_if_not_existing(os.path.join(package_path, 'facade.py'), PY_HEADER)


def create_app(name):
    package_path = os.path.join(SRC_DIR, name)
    _create_package(package_path)


if __name__ == '__main__':
    print create_app('user')