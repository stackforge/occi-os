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

from occi import registry

from nova.api.occi.extensions import occi_future


class OCCIRegistry(registry.NonePersistentRegistry):
    """
    Registry for OpenStack.
    """

    def get_extras(self, extras):
        sec_extras = None
        if extras != None:
            sec_extras = {}
            sec_extras['user_id'] = extras['nova_ctx'].user_id
            sec_extras['project_id'] = extras['nova_ctx'].project_id
        return sec_extras

    def add_resource(self, key, resource, extras):
        """
        Ensures OpenStack keys are used as resource identifiers and sets
        user id and tenant id
        """
        key = resource.kind.location + resource.attributes['occi.core.id']
        resource.identifier = key

        super(OCCIRegistry, self).add_resource(key, resource, extras)

    def delete_mixin(self, mixin, extras):
        """
        Allows for the deletion of user defined mixins.
        If the mixin is a security group mixin then that mixin's
        backend is called.
        """
        if (hasattr(mixin, 'related') and
                                    occi_future.SEC_GROUP in mixin.related):
            be = self.get_backend(mixin, extras)
            be.destroy(mixin, extras)

        super(OCCIRegistry, self).delete_mixin(mixin, extras)

    def set_backend(self, category, backend, extras):
        """
        Assigns user id and tenant id to user defined mixins
        """
        if (hasattr(category, 'related') and
                                    occi_future.SEC_GROUP in category.related):
            be = occi_future.SecurityGroupBackend()
            backend = be
            be.init_sec_group(category, extras)

        super(OCCIRegistry, self).set_backend(category, backend, extras)
