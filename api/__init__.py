# coding=utf-8

# vim: tabstop=4 shiftwidth=4 softtabstop=4

#
# Copyright (c) 2012, Intel Performance Learning Solutions Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
This it the entry point for paste.

Paste config file needs to point to egg:<package name>:<entrypoint name>:

    use = egg:occi-os#sample_app

sample_app entry point is defined in setup.py:

    entry_points='''
         [paste.app_factory]
         sample_app = api:main
    ''',

which point to this function call (<module name>:function).
"""

# W0613:unused args
# pylint: disable=W0613

from api import wsgi


def main(global_config, **settings):
    """
    This is the entry point for paste into the OCCI OS world.
    """
    return wsgi.OCCIApplication()
