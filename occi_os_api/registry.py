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
import uuid

from occi import registry as occi_registry
from occi import core_model
from occi.extensions import infrastructure
from occi_os_api.backends import openstack
from occi_os_api.extensions import os_addon

from occi_os_api.nova_glue import vm, storage, net

class OCCIRegistry(occi_registry.NonePersistentRegistry):
    """
    Registry for OpenStack.

    Idea is the following: Create the OCCI entities (Resource and their
    links) here and let the backends handle actions, attributes etc.
    """

    def __init__(self):
        super(OCCIRegistry, self).__init__()
        self.cache = {}
        self._setup_network()

    def get_extras(self, extras):
        """
        Get data which is encapsulated in the extras.
        """
        sec_extras = None
        if extras is not None:
            sec_extras = {'user_id': extras['nova_ctx'].user_id,
                          'project_id': extras['nova_ctx'].project_id}
        return sec_extras

    # The following two are here to deal with the security group mixins

    def delete_mixin(self, mixin, extras):
        """
        Allows for the deletion of user defined mixins.
        If the mixin is a security group mixin then that mixin's
        backend is called.
        """
        if (hasattr(mixin, 'related') and
            os_addon.SEC_GROUP in mixin.related):
            backend = self.get_backend(mixin, extras)
            backend.destroy(mixin, extras)

        super(OCCIRegistry, self).delete_mixin(mixin, extras)

    def set_backend(self, category, backend, extras):
        """
        Assigns user id and tenant id to user defined mixins
        """
        if (hasattr(category, 'related') and
            os_addon.SEC_GROUP in category.related):
            backend = openstack.SecurityGroupBackend()
            backend.init_sec_group(category, extras)

        super(OCCIRegistry, self).set_backend(category, backend, extras)

    # The following two deal with the creation and deletion os links.

    def add_resource(self, key, resource, extras):
        """
        Just here to prevent the super class from filling up an unused dict.
        """
        if (key, extras['nova_ctx'].user_id) not in self.cache and \
           core_model.Link.kind in resource.kind.related:
            # don't need to cache twice, only adding links :-)
            self.cache[(key, extras['nova_ctx'].user_id)] = resource
        elif (key, extras['nova_ctx'].user_id) not in self.cache and \
             resource.kind == os_addon.SEC_RULE:
            # don't need to cache twice, only adding links :-)
            self.cache[(key, extras['nova_ctx'].user_id)] = resource

    def delete_resource(self, key, extras):
        """
        Just here to prevent the super class from messing up.
        """
        if (key, extras['nova_ctx'].user_id) in self.cache:
            self.cache.pop((key, extras['nova_ctx'].user_id))

    # the following routines actually retrieve the info form OpenStack. Note
    # that a cache is used. The cache is stable - so delete resources
    # eventually also get deleted form the cache.

    def get_resource(self, key, extras):
        """
        Retrieve a single resource.
        """
        context = extras['nova_ctx']
        iden = key[key.rfind('/') + 1:]

        vms = vm.get_vms(context)
        vm_res_ids = [item['uuid'] for item in vms]
        stors = storage.get_storages(context)
        stor_res_ids = [item['id'] for item in stors]

        if (key, context.user_id) in self.cache:
            # I have seen it - need to update or delete if gone in OS!
            # I have already seen it
            cached_item = self.cache[(key, context.user_id)]
            if not iden in vm_res_ids and cached_item.kind ==\
               infrastructure.COMPUTE:
                # it was delete in OS -> remove links, cache + KeyError!
                # can delete it because it was my item!
                for link in cached_item.links:
                    self.cache.pop((link.identifier, repr(extras)))
                self.cache.pop((key, repr(extras)))
                raise KeyError
            if not iden in stor_res_ids and cached_item.kind ==\
               infrastructure.STORAGE:
                # it was delete in OS -> remove from cache + KeyError!
                # can delete it because it was my item!
                self.cache.pop((key, repr(extras)))
                raise KeyError
            elif iden in vm_res_ids:
                # it also exists in OS -> update it (take links, mixins
                # from cached one)
                result = self._update_occi_compute(cached_item, extras)
            elif iden in stor_res_ids:
                # it also exists in OS -> update it!
                result = self._update_occi_storage(cached_item, extras)
            else:
                # return cached item (links)
                return cached_item
        elif (key, None) in self.cache:
            # return shared entities from cache!
            return self.cache[(key, None)]
        else:
            # construct it.
            if iden in vm_res_ids:
                # create new & add to cache!
                result = self._construct_occi_compute(iden, vms, extras)[0]
            elif iden in stor_res_ids:
                result = self._construct_occi_storage(iden, stors, extras)[0]
            else:
                # doesn't exist!
                raise KeyError

        if result.identifier != key:
            raise AttributeError('Key/identifier mismatch! Requested: ' +
                                 key + ' Got: ' + result.identifier)
        return result

    def get_resource_keys(self, extras):
        """
        Retrieve the keys of all resources.
        """
        keys = []
        for item in self.cache.values():
            if item.extras is not None and item.extras != extras:
                # filter out items not belonging to this user!
                continue
            else:
                # add identifier
                keys.append(item.identifier)

        return keys

    def get_resources(self, extras):
        """
        Retrieve a set of resources.
        """

        # TODO: add security rules!

        context = extras['nova_ctx']
        result = []

        vms = vm.get_vms(context)
        vm_res_ids = [item['uuid'] for item in vms]

        stors = storage.get_storages(context)
        stor_res_ids = [item['id'] for item in stors]

        for item in self.cache.values():
            if item.extras is not None and item.extras['user_id'] != context\
            .user_id:
                # filter out items not belonging to this user!
                continue
            item_id = item.identifier[item.identifier.rfind('/') + 1:]
            if item.extras is None:
                # add to result set
                result.append(item)
            elif item_id in vm_res_ids and item.kind == infrastructure.COMPUTE:
                # check & update (take links, mixins from cache)
                # add compute and it's links to result
                self._update_occi_compute(item, extras)
                result.append(item)
                result.extend(item.links)
            elif item_id in stor_res_ids and item.kind == infrastructure.STORAGE:
                # check & update (take links, mixins from cache)
                # add compute and it's links to result
                self._update_occi_storage(item, extras)
                result.append(item)
            elif item_id not in vm_res_ids and item.kind == infrastructure.COMPUTE:
                # remove item and it's links from cache!
                for link in item.links:
                    self.cache.pop((link.identifier, item.extras['user_id']))
                self.cache.pop((item.identifier, item.extras['user_id']))
            elif item_id not in stor_res_ids and item.kind == infrastructure.STORAGE:
                # remove item
                self.cache.pop((item.identifier, item.extras['user_id']))
        for item in vms:
            if (infrastructure.COMPUTE.location + item['uuid'],
                context.user_id) in self.cache:
                continue
            else:
                # construct (with links and mixins and add to cache!
                # add compute and it's linke to result
                ent_list = self._construct_occi_compute(item['uuid'], vms,
                    extras)
                result.extend(ent_list)
        for item in stors:
            if (infrastructure.STORAGE.location + item['id'],
                context.user_id) in self.cache:
                continue
            else:
                # construct (with links and mixins and add to cache!
                # add compute and it's linke to result
                ent_list = self._construct_occi_storage(item['id'], stors,
                    extras)
                result.extend(ent_list)

        return result

    # Not part of parent

    def _update_occi_compute(self, entity, extras):
        # TODO: implement update of mixins and links (remove old mixins and
        # links)!
        return entity

    def _construct_occi_compute(self, identifier, vms, extras):
        """
        Construct a OCCI compute instance.

        First item in result list is entity self!

        Adds it to the cache too!
        """
        result = []
        context = extras['nova_ctx']

        instance = vm.get_vm(identifier, context)

        # 1. get identifier
        iden = infrastructure.COMPUTE.location + identifier
        entity = core_model.Resource(iden, infrastructure.COMPUTE,
            [os_addon.OS_VM])
        result.append(entity)

        # 2. os and res templates
        flavor_name = instance['instance_type'].name
        res_tmp = self.get_category('/' + flavor_name + '/', extras)
        entity.mixins.append(res_tmp)

        os_id = instance['image_ref']
        image_name = storage.get_image(os_id, context)['name']
        os_tmp = self.get_category('/' + image_name + '/', extras)
        entity.mixins.append(os_tmp)

        # 3. network links & get links from cache!
        net_links = net.get_adapter_info(identifier, context)
        for item in net_links['public']:
            link = self._construct_network_link(item, entity, self.pub_net,
                extras)
            result.append(link)
        for item in net_links['admin']:
            link = self._construct_network_link(item, entity, self.adm_net,
                extras)
            result.append(link)

        # core.id and cache it!
        entity.attributes['occi.core.id'] = identifier
        entity.extras = self.get_extras(extras)
        self.cache[(entity.identifier, context.user_id)] = entity

        return result

    def _update_occi_storage(self, entity, extras):
        # TODO: is there sth to do here??
        return entity

    def _construct_occi_storage(self, identifier, stors, extras):
        """
        Construct a OCCI storage instance.

        First item in result list is entity self!

        Adds it to the cache too!
        """
        result = []
        context = extras['nova_ctx']
        stor = storage.get_storage(identifier, context)

        # id, display_name, size, status
        iden = infrastructure.STORAGE.location + identifier
        entity = core_model.Resource(iden, infrastructure.STORAGE, [])
        result.append(entity)

        # create links on VM resources
        if stor['status'] == 'in-use':
            source = self.get_resource(infrastructure.COMPUTE.location +
                                       str(stor['instance_uuid']), extras)
            link = core_model.Link(infrastructure.STORAGELINK.location +
                                   str(uuid.uuid4()),
                infrastructure.STORAGELINK, [], source, entity)
            link.extras = self.get_extras(extras)
            source.links.append(link)
            result.append(link)
            self.cache[(link.identifier, context.user_id)] = link

        # core.id and cache it!
        entity.attributes['occi.core.id'] = identifier
        entity.extras = self.get_extras(extras)
        self.cache[(entity.identifier, context.user_id)] = entity

        return result

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
                                   'occi.networkinterface.allocation':
                                       'static'}
        self.adm_net = core_model.Resource('/network/admin',
            infrastructure.NETWORK, [infrastructure.IPNETWORK])
        self.adm_net.attributes = {'occi.network.vlan': 'admin',
                                   'occi.network.label': 'default',
                                   'occi.network.state': 'active',
                                   'occi.networkinterface.address': '10.0.0.0/24',
                                   'occi.networkinterface.gateway': '10.0.0'
                                                                    '.1',
                                   'occi.networkinterface.allocation':
                                       'static'}
        self.cache[(self.adm_net.identifier, None)] = self.adm_net
        self.cache[(self.pub_net.identifier, None)] = self.pub_net

    def _construct_network_link(self, net_desc, source, target, extras):
        """
        Construct a network link and add to cache!
        """
        link = core_model.Link(infrastructure.NETWORKINTERFACE.location +
                               str(uuid.uuid4()),
            infrastructure.NETWORKINTERFACE,
            [infrastructure.IPNETWORKINTERFACE], source, target)
        link.attributes = {
            'occi.networkinterface.interface': net_desc['interface'],
            'occi.networkinterface.mac': net_desc['mac'],
            'occi.networkinterface.state': net_desc['state'],
            'occi.networkinterface.address': net_desc['address'],
            'occi.networkinterface.gateway': net_desc['gateway'],
            'occi.networkinterface.allocation': net_desc['allocation']
        }
        link.extras = self.get_extras(extras)
        source.links.append(link)
        self.cache[(link.identifier, extras['nova_ctx'].user_id)] = link
        return link
