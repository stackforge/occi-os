# coding=utf-8
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
from occi import core_model
from occi.extensions import infrastructure

from nova_glue import vm, storage

class OCCIRegistry(occi_registry.NonePersistentRegistry):
    """
    Registry for OpenStack.
    """

    def __init__(self):
        super(OCCIRegistry, self).__init__()
        self.cache = {}
        self._setup_network()

    def add_resource(self, key, resource, extras):
        """
        Just here to prevent the super class from filling up an unused dict.
        """
        pass

    def delete_resource(self, key, extras):
        """
        Just here to prevent the super class from messing up.
        """
        pass

    def get_resource(self, key, extras):
        """
        Retrieve a single resource.
        """
        if extras is not None:
            context = extras['nova_ctx']
            iden = key[key.rfind('/') + 1:]
            vm_desc = vm.get_vm(iden, context)

            if (key, context.user_id) in self.cache:
                entity = self._update_occi_compute(key, extras)
            else:
                entity = self._construct_occi_compute(iden, [vm_desc], extras)
        else:
            # shared resources - look in cache!
            entity = self.cache[(key, None)]

        return entity

    def get_resource_keys(self, extras):
        """
        Retrieve the keys of all resources.
        """
        keys = []
        # TODO: implement this!

        return keys

    def get_resources(self, extras):
        """
        Retrieve a set of resources.
        """
        context = extras['nova_ctx']
        result = [self.pub_net, self.adm_net]

        vms = vm.get_vms(context)
        res_ids = [item['uuid'] for item in vms]

        for item in res_ids:
            if (infrastructure.COMPUTE.location + item,
                context.user_id) in self.cache:
                entity = self._update_occi_compute(infrastructure.COMPUTE
                .location + item, extras)
                result.append(entity)
                result.extend(entity.links)
            else:
                entity = self._construct_occi_compute(item, vms, extras)
                result.append(entity)
                result.extend(entity.links)

        return result

    # Not part of parent

    def _update_occi_compute(self, identifier, extras):
        context = extras['nova_ctx']
        return self.cache[identifier, context.user_id]

    def _construct_occi_compute(self, identifier, vms, extras):
        """
        Construct a OCCI compute instance.

        Adds it to the cache too!
        """
        context = extras['nova_ctx']

        # 1. get identifier
        iden = infrastructure.COMPUTE.location + identifier
        entity = core_model.Resource(iden, infrastructure.COMPUTE, [])

        # 2. os and res templates
        flavor_name = vm.get_vm(identifier, context)['instance_type'].name
        res_tmp = self.get_category('/' + flavor_name + '/', extras)
        entity.mixins.append(res_tmp)

        os_id = vm.get_vm(identifier, context)['image_ref']
        image_name = storage.get_image(os_id, context)['name']
        os_tmp = self.get_category('/' + image_name + '/', extras)
        entity.mixins.append(os_tmp)

        # 3. network links & get links from cache!

        # 4. storage links & get links from cache!

        # core.id and cache it!
        entity.attributes['occi.core.id'] = identifier
        entity.extras = extras
        self.cache[(entity.identifier, context.user_id)] = entity

        return entity

    def _setup_network(self):
        """
        Add a public and an admin network interface.
        """
        # TODO: read from openstack!
        self.pub_net = core_model.Resource('/network/public',
            infrastructure.NETWORK, [infrastructure.IPNETWORK])
        self.pub_net.attributes = {'occi.network.vlan': 'external',
                                   'occi.network.label': 'default',
                                   'occi.network.state': 'active',
                                   'occi.networkinterface.address': '192'
                                                                    '.168'
                                                                    '.0.0/24',
                                   'occi.networkinterface.gateway': '192.168'
                                                                    '.0.1',
                                   'occi.networkinterface.allocation': 'dynamic'}
        self.adm_net = core_model.Resource('/network/admin',
            infrastructure.NETWORK, [infrastructure.IPNETWORK])
        self.adm_net.attributes = {'occi.network.vlan': 'admin',
                                   'occi.network.label': 'default',
                                   'occi.network.state': 'active',
                                   'occi.networkinterface.address': '10.0.0.0/24',
                                   'occi.networkinterface.gateway': '10.0.0'
                                                                    '.1',
                                   'occi.networkinterface.allocation': 'dynamic'}
        self.cache[(self.adm_net.identifier, None)] = self.adm_net
        self.cache[(self.pub_net.identifier, None)] = self.pub_net
