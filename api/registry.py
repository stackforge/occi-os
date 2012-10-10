# vim: tabstop=4 shiftwidth=4 softtabstop=4

#
#    Copyright (c) 2012, Intel Performance Learning Solutions Ltd.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
OCCI registry
"""

#R0201:method could be func.E1002:old style obj
#pylint: disable=R0201,E1002

from occi import registry as occi_registry


class OCCIRegistry(occi_registry.NonePersistentRegistry):
    """
    Registry for OpenStack.
    """

    def __init__(self):
        super(OCCIRegistry, self).__init__()
