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
Network link backend!
"""

#W0613:unused arguments,R0201:mth could be func,R0903:too few pub mthd.
#W0232:no init
#pylint: disable=W0613,R0201,R0903,W0232

from occi import backend

# With Quantum:
#     TODO(dizz): implement create - note: this must handle either
#                 nova-network or quantum APIs - detect via flags and
#                 secondarily via import exceptions
#                 implement delete
#                 implement update
# Also see nova/api/openstack/compute/contrib/multinic.py


class NetworkInterfaceBackend(backend.KindBackend):
    """
    A backend for network links.
    """

    def create(self, link, extras):
        """
        As nova does not support creation of L2 networks we don't.
        """
        # implement with Quantum
        raise AttributeError('Currenlty not supported.')

    def update(self, old, new, extras):
        """
        Allows for the update of network links.
        """
        #L8R: here we associate a security group
        #L8R: here we could possibly assign a static (floating) ip - request
        #     must include a ipnetworkinterface mixin
        # make sure the link has an IP mixin
        # get a reference to the compute instance
        # get the security group
        # associate the security group with the compute instance

        raise AttributeError('Currently not supported.')


class IpNetworkInterfaceBackend(backend.MixinBackend):
    """
    A mixin backend for the IpNetworkingInterface.
    """

    def create(self, link, extras):
        """
        Can't create in nova so we don't either.
        """
        raise AttributeError('Currently not supported.')
