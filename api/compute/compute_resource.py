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
The compute resource backend for OpenStack.
"""
import logging
import uuid

from occi import core_model
from occi.backend import KindBackend, ActionBackend
from occi.extensions import infrastructure

from api import nova_glue
from api.extensions import openstack, occi_future
from api.compute import templates

LOG = logging.getLogger('api.compute.compute_resource')

class ComputeBackend(KindBackend, ActionBackend):

    def create(self, entity, extras):
        LOG.debug('Creating an Virtual machine')

        # ignore some attributes - done via templating
        if 'occi.compute.cores' in entity.attributes or \
           'occi.compute.speed' in entity.attributes or \
           'occi.compute.memory' in entity.attributes or \
           'occi.compute.architecture' in entity.attributes:
            msg = 'There are unsupported attributes in the request.'
            LOG.error(msg)
            raise AttributeError(msg)

        # create the VM
        instance = nova_glue.create_vm(entity, extras['nova_ctx'])

        # deal with some networking stuff
        net_info = nova_glue.get_adapter_info(instance, extras['nova_ctx'])
        attach_to_default_network(net_info, entity, extras)

        # add consoles and storage links
        set_console_info(entity, instance, extras)

        # set some attributes
        entity.attributes['occi.core.id'] = instance['uuid']
        entity.attributes['occi.compute.hostname'] = instance['hostname']
        entity.attributes['occi.compute.architecture'] = nova_glue.get_image_architecture\
            (instance, extras['nova_ctx'])
        entity.attributes['occi.compute.cores'] = str(instance['vcpus'])
        entity.attributes['occi.compute.speed'] = str(0.0) # N/A in instance
        entity.attributes['occi.compute.memory'] = str(float
                                                           (instance['memory_mb']) / 1024)
        entity.attributes['occi.compute.state'] = 'inactive'

        # set valid actions
        entity.actions = [infrastructure.STOP,
                         infrastructure.SUSPEND,
                         infrastructure.RESTART,
                         openstack.OS_REVERT_RESIZE,
                         openstack.OS_CONFIRM_RESIZE,
                         openstack.OS_CREATE_IMAGE]


    def retrieve(self, entity, extras):
        uid = entity.attributes['occi.core.id']
        instance = nova_glue.get_vm_instance(uid, extras['nova_ctx'])

        LOG.debug('Retrieving an Virtual machine: ', uid)

        # set state and applicable actions!
        nova_glue.set_vm_occistate(entity, extras['nova_ctx'])

        # set up to date attributes
        entity.attributes['occi.compute.cores'] = str(instance['vcpus'])
        entity.attributes['occi.compute.memory'] = str(float
                                                           (instance['memory_mb']) / 1024)

        #Now we have the instance state, get its updated network info
        net_info = nova_glue.get_adapter_info(instance, extras['nova_ctx'])
        attach_to_default_network(net_info, entity, extras)

        # add consoles and storage links
        set_console_info(entity, instance, extras)

    def update(self, old, new, extras):
        uid = old.attributes['occi.core.id']

        LOG.debug('Updating an Virtual machine: ', uid)

        # update title, summary etc.
        if len(new.attributes['occi.core.title']) > 0:
            old.attributes['occi.core.title'] =\
            new.attributes['occi.core.title']
        if len(new.attributes['occi.core.summary']) > 0:
            old.attributes['occi.core.summary'] =\
            new.attributes['occi.core.summary']

        # for now we will only handle one mixin change per request
        mixin = new.mixins[0]
        if isinstance(mixin, templates.ResourceTemplate):
            nova_glue.resize_vm(old, mixin, extras['nova_ctx'])
        elif isinstance(mixin, templates.OsTemplate):
            # do we need to check for new os rebuild in new?
            nova_glue.rebuild_vm(old, mixin, extras['nova_ctx'])
        else:
            msg = ('Unrecognised mixin. %s') % str(mixin)
            LOG.error(msg)
            raise AttributeError(msg)

    def replace(self, old, new, extras):
        # XXX:not doing anything - full updates are hard :-)
        pass

    def delete(self, entity, extras):
        msg = ('Removing representation of virtual machine with id: %s') %\
              entity.identifier
        LOG.info(msg)

        context = extras['nova_ctx']
        uid = entity.attributes['occi.core.id']

        nova_glue.delete_vm(uid, context)

    def action(self, entity, action, attributes, extras):
        # As there is no callback mechanism to update the state
        # of computes known by occi, a call to get the latest representation
        # must be made.
        context = extras['nova_ctx']

        if action not in entity.actions:
            raise AttributeError("This action is not currently applicable.")
        elif action == infrastructure.START:
            nova_glue.start_vm(entity, context)
        elif action == infrastructure.STOP:
            nova_glue.stop_vm(entity, attributes, context)
        elif action == infrastructure.RESTART:
            nova_glue.restart_vm(entity, attributes, context)
        elif action == infrastructure.SUSPEND:
            nova_glue.suspend_vm(entity, attributes, context)

# SOME HELPER FUNCTIONS


def attach_to_default_network(vm_net_info, entity, extras):
    """
    Associates a network adapter with the relevant network resource.
    """
    # check that existing network does not exist
    if len(entity.links) > 0:
        for link in entity.links:
            if link.kind.term == infrastructure.NETWORKINTERFACE.term and \
               link.kind.scheme == infrastructure.NETWORK.scheme:
                msg = 'A link to the network already exists. Will update ' \
                      'the links attributes.'
                LOG.debug(msg)
                link.attributes['occi.networkinterface.interface'] = vm_net_info['vm_iface']
                link.attributes['occi.networkinterface.address'] = vm_net_info['address']
                link.attributes['occi.networkinterface.gateway'] = vm_net_info['gateway']
                link.attributes['occi.networkinterface.mac'] = vm_net_info['mac']
                return

    # If the network association does not exist...
    # Get a handle to the default network
    registry = extras['registry']
    default_network = registry.get_resource('/network/DEFAULT_NETWORK', None)
    source = entity
    target = default_network

    # Create the link to the default network
    identifier = str(uuid.uuid4())
    link = core_model.Link(identifier, infrastructure.NETWORKINTERFACE,
        [infrastructure.IPNETWORKINTERFACE], source, target)
    link.attributes['occi.core.id'] = identifier
    link.attributes['occi.networkinterface.interface'] = \
    vm_net_info['vm_iface']
    link.attributes['occi.networkinterface.mac'] = vm_net_info['mac']
    link.attributes['occi.networkinterface.state'] = 'active'
    link.attributes['occi.networkinterface.address'] =\
    vm_net_info['address']
    link.attributes['occi.networkinterface.gateway'] =\
    vm_net_info['gateway']
    link.attributes['occi.networkinterface.allocation'] =\
    vm_net_info['allocation']

    entity.links.append(link)
    registry.add_resource(identifier, link, extras)


def set_console_info(entity, instance, extras):
    """
    Adds console access information to the resource.
    """
    address = entity.links[0].attributes['occi.networkinterface.address']

    ssh_console_present = False
    vnc_console_present = False
    comp_sch = 'http://schemas.openstack.org/occi/infrastructure/compute#'

    for link in entity.links:
        if link.target.kind.term == "ssh_console" and link.target.kind\
                                                      .scheme == comp_sch:
            ssh_console_present = True
        elif link.target.kind.term == "vnc_console" and  link.target.kind\
                                                         .scheme == comp_sch:
            vnc_console_present = True

    registry = extras['registry']
    if not ssh_console_present:
        identifier = str(uuid.uuid4())
        ssh_console = core_model.Resource(
            identifier, occi_future.SSH_CONSOLE, [],
            links=None, summary='',
            title='')
        ssh_console.attributes['occi.core.id'] = identifier
        ssh_console.attributes['org.openstack.compute.console.ssh'] =\
        'ssh://' + address + ':22'
        registry.add_resource(identifier, ssh_console, extras)

        identifier = str(uuid.uuid4())
        ssh_console_link = core_model.Link(
            identifier,
            occi_future.CONSOLE_LINK,
            [], entity, ssh_console)
        ssh_console_link.attributes['occi.core.id'] = identifier
        registry.add_resource(identifier, ssh_console_link, extras)

        entity.links.append(ssh_console_link)

    if not vnc_console_present:
        console = nova_glue.get_vnc_for_vm(instance, extras['nova_ctx'])

        identifier = str(uuid.uuid4())
        vnc_console = core_model.Resource(
            identifier, occi_future.VNC_CONSOLE, [],
            links=None, summary='',
            title='')
        vnc_console.attributes['occi.core.id'] = identifier
        vnc_console.attributes['org.openstack.compute.console.vnc'] =\
        console['url']

        registry.add_resource(identifier, vnc_console, extras)

        identifier = str(uuid.uuid4())
        vnc_console_link = core_model.Link(
            identifier,
            occi_future.CONSOLE_LINK,
            [], entity, vnc_console)
        vnc_console_link.attributes['occi.core.id'] = identifier
        registry.add_resource(identifier, vnc_console_link, extras)

        entity.links.append(vnc_console_link)