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

#pylint: disable=W0232,R0201

import logging
import uuid

from api.extensions import openstack, occi_future
from api.compute import templates

from nova_glue import net
from nova_glue import vm
from nova_glue import vol

from occi import core_model
from occi.backend import KindBackend, ActionBackend
from occi.extensions import infrastructure

LOG = logging.getLogger('nova.api.wsgi.occi.compute.compute_resource')


class ComputeBackend(KindBackend, ActionBackend):
    """
    The compute backend.
    """

    def create(self, entity, extras):
        """
        Create a VM.
        """
        LOG.debug('Creating an Virtual machine')

        # ignore some attributes - done via templating
        if 'occi.compute.cores' in entity.attributes or \
           'occi.compute.speed' in entity.attributes or \
           'occi.compute.memory' in entity.attributes or \
           'occi.compute.architecture' in entity.attributes:
            raise AttributeError('There are unsupported attributes in the '
                                 'request.')

        # create the VM
        context = extras['nova_ctx']
        instance = vm.create_vm(entity, context)
        uid = instance['uuid']

        # deal with some networking stuff
        net_info = net.get_adapter_info(uid, context)
        attach_to_default_network(net_info, entity, extras)

        # add consoles and storage links
        set_console_info(entity, uid, extras)

        # set some attributes
        entity.attributes['occi.core.id'] = instance['uuid']
        entity.attributes['occi.compute.hostname'] = instance['hostname']
        entity.attributes['occi.compute.architecture'] = \
            vol.get_image_architecture(uid, extras['nova_ctx'])
        entity.attributes['occi.compute.cores'] = str(instance['vcpus'])
        entity.attributes['occi.compute.speed'] = str(0.0)  # N/A in instance
        value = str(float(instance['memory_mb']) / 1024)
        entity.attributes['occi.compute.memory'] = value
        entity.attributes['occi.compute.state'] = 'inactive'

        # set valid actions
        entity.actions = [infrastructure.STOP,
                         infrastructure.SUSPEND,
                         infrastructure.RESTART,
                         openstack.OS_REVERT_RESIZE,
                         openstack.OS_CONFIRM_RESIZE,
                         openstack.OS_CREATE_IMAGE]

    def retrieve(self, entity, extras):
        """
        Retrieve a VM.
        """
        uid = entity.attributes['occi.core.id']
        context = extras['nova_ctx']
        instance = vm.get_vm(uid, context)

        LOG.debug('Retrieving an Virtual machine: ', uid)

        # set state and applicable actions!
        state, actions = vm.get_occi_state(uid, context)
        entity.attributes['occi.compute.state'] = state
        entity.actions = actions

        # set up to date attributes
        entity.attributes['occi.compute.cores'] = str(instance['vcpus'])
        value = str(float(instance['memory_mb']) / 1024)
        entity.attributes['occi.compute.memory'] = value

        #Now we have the instance state, get its updated network info
        net_info = net.get_adapter_info(uid, context)
        attach_to_default_network(net_info, entity, extras)

        # add consoles and storage links
        set_console_info(entity, uid, extras)

    def update(self, old, new, extras):
        """
        Update an VM.
        """
        context = extras['nova_ctx']
        uid = old.attributes['occi.core.id']

        LOG.debug('Updating an Virtual machine: ', uid)

        # update title, summary etc.
        if 'occi.core.title' in new.attributes:
            old.attributes['occi.core.title'] = \
            new.attributes['occi.core.title']
        if 'occi.core.summary' in new.attributes:
            old.attributes['occi.core.summary'] = \
            new.attributes['occi.core.summary']

        # for now we will only handle one mixin change per request
        mixin = new.mixins[0]
        if isinstance(mixin, templates.ResourceTemplate):
            flavor_name = mixin.term
            vm.resize_vm(uid, flavor_name, context)
            old.attributes['occi.compute.state'] = 'inactive'
            # now update the mixin info
            # TODO(tmetsch): remove old mixin!!!
            old.mixins.append(mixin)
        elif isinstance(mixin, templates.OsTemplate):
            image_href = mixin.os_id
            vm.rebuild_vm(uid, image_href, context)
            old.attributes['occi.compute.state'] = 'inactive'
            #now update the mixin info
            # TODO(tmetsch): remove old mixin!!!
            old.mixins.append(mixin)
        else:
            msg = ('Unrecognized mixin. %s') % str(mixin)
            LOG.error(msg)
            raise AttributeError(msg)

    def replace(self, old, new, extras):
        """
        XXX:not doing anything - full updates are hard :-)
        """
        pass

    def delete(self, entity, extras):
        """
        Remove a VM.
        """
        msg = ('Removing representation of virtual machine with id: %s') %\
              entity.identifier
        LOG.info(msg)

        context = extras['nova_ctx']
        uid = entity.attributes['occi.core.id']

        vm.delete_vm(uid, context)

    def action(self, entity, action, attributes, extras):
        """
        Perform an action.
        """
        # As there is no callback mechanism to update the state
        # of computes known by occi, a call to get the latest representation
        # must be made.
        context = extras['nova_ctx']
        uid = entity.attributes['occi.core.id']

        # set state and applicable actions - so even if the user hasn't done
        # a GET het can still the most applicable action now...
        state, actions = vm.get_occi_state(uid, context)
        entity.attributes['occi.compute.state'] = state
        entity.actions = actions

        if action not in entity.actions:
            raise AttributeError("This action is currently not applicable.")
        elif action == infrastructure.START:
            vm.start_vm(uid, context)
        elif action == infrastructure.STOP:
            vm.stop_vm(uid, context)
        elif action == infrastructure.RESTART:
            if not 'method' in attributes:
                raise AttributeError('Please provide a method!')
            method = attributes['method']
            vm.restart_vm(uid, method, context)
        elif action == infrastructure.SUSPEND:
            vm.suspend_vm(uid, context)

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
                link.attributes['occi.networkinterface.interface'] = \
                vm_net_info['vm_iface']
                link.attributes['occi.networkinterface.address'] = \
                vm_net_info['address']
                link.attributes['occi.networkinterface.gateway'] = \
                vm_net_info['gateway']
                link.attributes['occi.networkinterface.mac'] = \
                vm_net_info['mac']
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
    link.attributes['occi.networkinterface.address'] = \
    vm_net_info['address']
    link.attributes['occi.networkinterface.gateway'] = \
    vm_net_info['gateway']
    link.attributes['occi.networkinterface.allocation'] = \
    vm_net_info['allocation']

    entity.links.append(link)
    registry.add_resource(identifier, link, extras)


def set_console_info(entity, uid, extras):
    """
    Adds console access information to the resource.
    """

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
    address = entity.links[0].attributes['occi.networkinterface.address']
    if not ssh_console_present and len(address) > 7:
        identifier = str(uuid.uuid4())
        ssh_console = core_model.Resource(
            identifier, occi_future.SSH_CONSOLE, [],
            links=None, summary='',
            title='')
        ssh_console.attributes['occi.core.id'] = identifier
        ssh_console.attributes['org.openstack.compute.console.ssh'] = \
        'ssh://' + address + ':22'
        registry.add_transient_resource(entity, identifier, ssh_console,
            extras)

        identifier = str(uuid.uuid4())
        ssh_console_link = core_model.Link(
            identifier,
            occi_future.CONSOLE_LINK,
            [], entity, ssh_console)
        ssh_console_link.attributes['occi.core.id'] = identifier
        registry.add_resource(identifier, ssh_console_link, extras)

        entity.links.append(ssh_console_link)

    if not vnc_console_present:
        console = vm.get_vnc(uid, extras['nova_ctx'])
        if console is None:
            return

        identifier = str(uuid.uuid4())
        vnc_console = core_model.Resource(
            identifier, occi_future.VNC_CONSOLE, [],
            links=None, summary='',
            title='')
        vnc_console.attributes['occi.core.id'] = identifier
        vnc_console.attributes['org.openstack.compute.console.vnc'] = \
        console['url']

        registry.add_transient_resource(entity, identifier, vnc_console,
            extras)

        identifier = str(uuid.uuid4())
        vnc_console_link = core_model.Link(
            identifier,
            occi_future.CONSOLE_LINK,
            [], entity, vnc_console)
        vnc_console_link.attributes['occi.core.id'] = identifier
        registry.add_resource(identifier, vnc_console_link, extras)

        entity.links.append(vnc_console_link)
