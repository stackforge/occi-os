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


# TODO(dizz): implement create
#             implement delete
#             implement retreive
#             implement actions
#             implement updates

# Also see nova/api/openstack/compute/contrib/networks.py

from occi import backend
from webob import exc

from nova import flags
from nova import log as logging


#Hi I'm a logger, use me! :-)
LOG = logging.getLogger('nova.api.occi.backends.network')

FLAGS = flags.FLAGS


class NetworkBackend(backend.KindBackend, backend.ActionBackend):
    """
    Backend to handle network resources.
    """
    def create(self, entity, extras):
        raise exc.HTTPBadRequest()

    def delete(self, entity, extras):
        pass

    def action(self, entity, action, extras):
        raise exc.HTTPBadRequest()


class IpNetworkBackend(backend.MixinBackend):
    """
    A mixin backend for the IPnetworking.
    """
    def create(self, entity, extras):
        raise exc.HTTPBadRequest()

    def delete(self, entity, extras):
        pass
