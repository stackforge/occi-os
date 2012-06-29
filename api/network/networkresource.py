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
Network resource backend.
"""

#W0613:unused arguments,R0201:mth could be func,R0903:too few pub mthd.
#W0232:no init
#pylint: disable=W0613,R0201,R0903,W0232

# TODO(dizz): implement create
#             implement delete
#             implement retreive
#             implement actions
#             implement updates

# Also see nova/api/openstack/compute/contrib/networks.py

from occi import backend


class NetworkBackend(backend.KindBackend, backend.ActionBackend):
    """
    Backend to handle network resources.
    """

    def create(self, entity, extras):
        """
        Currently unsupported.
        """
        raise AttributeError('Currently not supported.')

    def action(self, entity, action, attributes, extras):
        """
        Currently unsupported.
        """
        raise AttributeError('Currently not supported.')


class IpNetworkBackend(backend.MixinBackend):
    """
    A mixin backend for the IPnetworking.
    """

    def create(self, entity, extras):
        """
        Currently unsupported.
        """
        raise AttributeError('Currently not supported.')
