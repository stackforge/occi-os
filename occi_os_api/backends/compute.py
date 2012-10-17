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
The compute resource backend for OpenStack.
"""

#pylint: disable=W0232,R0201

import logging

from occi_os_api.extensions import os_mixins
from occi_os_api.extensions import os_addon
from occi_os_api.nova_glue import vm
from occi_os_api.nova_glue import storage

from occi.backend import KindBackend, ActionBackend
from occi.extensions import infrastructure

LOG = logging.getLogger(__name__)


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
        entity.identifier = '/compute/' + uid

        # set some attributes
        entity.attributes['occi.compute.hostname'] = instance['hostname']
        entity.attributes['occi.compute.architecture'] = \
            storage.get_image_architecture(uid, extras['nova_ctx'])
        entity.attributes['occi.compute.cores'] = str(instance['vcpus'])
        entity.attributes['occi.compute.speed'] = str(0.0)  # N/A in instance
        value = str(float(instance['memory_mb']) / 1024)
        entity.attributes['occi.compute.memory'] = value
        entity.attributes['occi.compute.state'] = 'inactive'

        # set valid actions
        entity.actions = [infrastructure.STOP,
                         infrastructure.SUSPEND,
                         infrastructure.RESTART]

        entity.mixins.append(os_addon.OS_VM)

    def retrieve(self, entity, extras):
        """
        Retrieve a VM.
        """
        uid = entity.attributes['occi.core.id']
        context = extras['nova_ctx']
        instance = vm.get_vm(uid, context)

        LOG.debug('Retrieving an Virtual machine: ' + repr(uid))

        # set state and applicable actions!
        state, actions = vm.get_occi_state(uid, context)
        entity.attributes['occi.compute.state'] = state
        entity.actions = actions

        # set up to date attributes
        entity.attributes['occi.compute.hostname'] = instance['hostname']
        entity.attributes['occi.compute.architecture'] =\
        storage.get_image_architecture(uid, extras['nova_ctx'])
        entity.attributes['occi.compute.cores'] = str(instance['vcpus'])
        entity.attributes['occi.compute.speed'] = str(0.0)  # N/A in instance
        value = str(float(instance['memory_mb']) / 1024)
        entity.attributes['occi.compute.memory'] = value

    def update(self, old, new, extras):
        """
        Update an VM.
        """
        context = extras['nova_ctx']
        uid = old.attributes['occi.core.id']

        LOG.debug('Updating an Virtual machine: ' + repr(uid))

        # for now we will only handle one mixin change per request
        mixin = new.mixins[0]
        if isinstance(mixin, os_mixins.ResourceTemplate):
            flavor_name = mixin.term
            vm.resize_vm(uid, flavor_name, context)
            old.attributes['occi.compute.state'] = 'inactive'
            # now update the mixin info
            old.mixins.append(mixin)
        elif isinstance(mixin, os_mixins.OsTemplate):
            image_href = mixin.os_id
            vm.rebuild_vm(uid, image_href, context)
            old.attributes['occi.compute.state'] = 'inactive'
            # now update the mixin info
            old.mixins.append(mixin)
        else:
            msg = 'Unrecognized mixin. %s' % str(mixin)
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
        msg = 'Removing representation of virtual machine with id: %s' %\
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
