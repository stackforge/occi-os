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

from occi import backend
from webob import exc

from nova import log as logging


# With Quantum:
#     TODO(dizz): implement create - note: this must handle either
#                 nova-network or quantum APIs - detect via flags and
#                 secondarily via import exceptions
#                 implement delete
#                 implement update
# Also see nova/api/openstack/compute/contrib/multinic.py


#Hi I'm a logger, use me! :-)
LOG = logging.getLogger('nova.api.occi.backends.network.link')


class NetworkInterfaceBackend(backend.KindBackend):
    """
    A backend for network links.
    """

    def create(self, link, extras):
        """
        As nova does not support creation of L2 networks we don't.
        """
        # implement with Quantum
        raise exc.HTTPBadRequest()

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

        raise exc.HTTPBadRequest()

    def delete(self, link, extras):
        """
        no-op
        """
        pass


class IpNetworkInterfaceBackend(backend.MixinBackend):
    """
    A mixin backend for the IpNetworkingInterface.
    """
    def create(self, link, extras):
        """
        Can't create in nova so we don't either.
        """
        raise exc.HTTPBadRequest()

    def delete(self, entity, extras):
        """
        no-op
        """
        pass

    def action(self):
        """
        no-op
        """
        pass
