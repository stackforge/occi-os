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
from api.compute import openstack

from api.extensions import occi_future


class OCCIRegistry(occi_registry.NonePersistentRegistry):
    """
    Registry for OpenStack.
    """

    def __init__(self):
        super(OCCIRegistry, self).__init__()
        self.transient = {}

    def get_extras(self, extras):
        """
        Get data which is encapsulated in the extras.
        """
        sec_extras = None
        if extras is not None:
            sec_extras = {'user_id': extras['nova_ctx'].user_id,
                          'project_id': extras['nova_ctx'].project_id}
        return sec_extras

    def add_resource(self, key, resource, extras):
        """
        Ensures OpenStack keys are used as resource identifiers and sets
        user id and tenant id
        """
        key = resource.kind.location + resource.attributes['occi.core.id']
        resource.identifier = key

        super(OCCIRegistry, self).add_resource(key, resource, extras)

    def add_transient_resource(self, parent, key, resource, extras):
        """
        Add a resource which is transient - meaning when the parent which
        links to this resource gets deleted the transient resource gets
        deleted as well.
        """
        self.add_resource(key, resource, extras)
        if parent in self.transient:
            self.transient[parent].append(resource)
        else:
            self.transient[parent] = [resource]

    def delete_resource(self, key, extras):
        """
        Deletes a resource. When resource has associate resources those
        will be deleted as well.
        """
        parent = self.get_resource(key, extras)
        if parent in self.transient:
            for item in self.transient[parent]:
                tmp = item.identifier
                super(OCCIRegistry, self).delete_resource(tmp, extras)

        super(OCCIRegistry, self).delete_resource(key, extras)

    def get_resource(self, key, extras):
        """
        Ensure that the default network is visible to all!
        """
        # TODO: move to pyssf!
        if self.resources[key].extras is not None and self.resources[key]\
                                                   .extras != self.get_extras(extras):
            raise KeyError
        return self.resources[key]

    def delete_mixin(self, mixin, extras):
        """
        Allows for the deletion of user defined mixins.
        If the mixin is a security group mixin then that mixin's
        backend is called.
        """
        if (hasattr(mixin, 'related') and
                                    occi_future.SEC_GROUP in mixin.related):
            backend = self.get_backend(mixin, extras)
            backend.destroy(mixin, extras)

        super(OCCIRegistry, self).delete_mixin(mixin, extras)

    def set_backend(self, category, backend, extras):
        """
        Assigns user id and tenant id to user defined mixins
        """
        if (hasattr(category, 'related') and
                                    occi_future.SEC_GROUP in category.related):
            backend = openstack.SecurityGroupBackend()
            backend.init_sec_group(category, extras)

        super(OCCIRegistry, self).set_backend(category, backend, extras)
