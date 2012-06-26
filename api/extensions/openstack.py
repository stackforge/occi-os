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
from occi import core_model
from webob import exc

from nova import compute
from nova import exception
from nova import logging
from nova.network import api as net_api


# Hi I'm a logger, use me! :-)
LOG = logging.getLogger('nova.api.occi.backends.compute.os')


######################## OpenStack Specific Addtitions #######################
######### 1. define the method to retreive all extension information #########
def get_extensions():

    return  [
             {
              'categories': [OS_CHG_PWD, OS_REVERT_RESIZE,
                            OS_CONFIRM_RESIZE, OS_CREATE_IMAGE,
                            OS_ALLOC_FLOATING_IP, OS_DEALLOC_FLOATING_IP, ],
              'handler': OsComputeActionBackend(),
             },
             {
              'categories': [OS_KEY_PAIR_EXT, OS_ADMIN_PWD_EXT,
                            OS_ACCESS_IP_EXT, OS_FLOATING_IP_EXT, ],
              'handler': backend.MixinBackend(),
             },
            ]


##### 2. define the extension categories - OpenStack Specific Additions ######
# OS change adminstrative password action
_OS_CHG_PWD_ATTRIBUTES = {'org.openstack.credentials.admin_pwd': '', }
OS_CHG_PWD = core_model.Action(
                'http://schemas.openstack.org/instance/action#',
                 'chg_pwd', 'Removes all data on the server and replaces'
                                    'it with the specified image (via Mixin).',
                 _OS_CHG_PWD_ATTRIBUTES)


# OS revert a resized VM action
OS_REVERT_RESIZE = core_model.Action(
                'http://schemas.openstack.org/instance/action#',
                 'revert_resize', 'Revert the compute resize and roll back.')


# OS confirm a resized VM action
OS_CONFIRM_RESIZE = core_model.Action(
                'http://schemas.openstack.org/instance/action#',
                 'confirm_resize', 'Confirms the resize action.')


# OS create image from VM action
_OS_CREATE_IMAGE_ATTRIBUTES = {'org.openstack.snapshot.image_name': '', }
OS_CREATE_IMAGE = core_model.Action(
                'http://schemas.openstack.org/instance/action#',
                 'create_image', 'Creates a new image for the given server.',
                 _OS_CREATE_IMAGE_ATTRIBUTES)


# OS Key pair extension
_OS_KEY_PAIR_ATTRIBUTES = {'org.openstack.credentials.publickey.name': '',
                       'org.openstack.credentials.publickey.data': '', }
OS_KEY_PAIR_EXT = core_model.Mixin(
    'http://schemas.openstack.org/instance/credentials#',
    'public_key', attributes=_OS_KEY_PAIR_ATTRIBUTES)


# OS VM Administrative password extension
_OS_ADMIN_PWD_ATTRIBUTES = {'org.openstack.credentials.admin_pwd': '', }
OS_ADMIN_PWD_EXT = core_model.Mixin(
    'http://schemas.openstack.org/instance/credentials#',
    'admin_pwd', attributes=_OS_ADMIN_PWD_ATTRIBUTES)


# OS access IP extension
_OS_ACCESS_IP_ATTRIBUTES = {'org.openstack.network.access.ip': '',
                           'org.openstack.network.access.version': ''}
OS_ACCESS_IP_EXT = core_model.Mixin(
    'http://schemas.openstack.org/instance/network#',
    'access_ip', attributes=_OS_ACCESS_IP_ATTRIBUTES)


# OS floating IP allocation action
# expected parameter is the floating IP pool to take the IP from
OS_ALLOC_FLOATING_IP = core_model.Action(
                'http://schemas.openstack.org/instance/action#',
                 'alloc_float_ip', 'Allocate a floating IP to the '
                                                        'compute resource.')


# OS floating IP deallocation action
OS_DEALLOC_FLOATING_IP = core_model.Action(
                'http://schemas.openstack.org/instance/action#',
                 'dealloc_float_ip', 'Deallocate a floating IP from the '
                                                        'compute resource.')


# OS floating IP extension
_OS_FLOATING_IP_ATTRIBUTES = {'org.openstack.network.floating.ip': '', }
OS_FLOATING_IP_EXT = core_model.Mixin(
    'http://schemas.openstack.org/instance/network#',
    'floating_ip', attributes=_OS_FLOATING_IP_ATTRIBUTES)


##################### 3. define the extension handler(s) #####################
class OsComputeActionBackend(backend.ActionBackend):

    def __init__(self):
        super(OsComputeActionBackend, self).__init__()
        self.compute_api = compute.API()
        self.network_api = net_api.API()

    def action(self, entity, action, attributes, extras):
        """
        This is called by pyssf when an action request is issued.
        """
        context = extras['nova_ctx']

        try:
            instance = self.compute_api.get(context,
                                            entity.attributes['occi.core.id'])
        except exception.NotFound:
            raise exc.HTTPNotFound()

        if action == OS_CHG_PWD:
            self._os_chg_passwd_vm(entity, attributes, instance, context)
        elif action == OS_REVERT_RESIZE:
            self._os_revert_resize_vm(entity, instance, context)
        elif action == OS_CONFIRM_RESIZE:
            self._os_confirm_resize_vm(entity, instance, context)
        elif action == OS_CREATE_IMAGE:
            self._os_create_image(entity, attributes, instance, context)
        elif action == OS_ALLOC_FLOATING_IP:
            self._os_allocate_floating_ip(entity, attributes, instance,
                                                                    context)
        elif action == OS_DEALLOC_FLOATING_IP:
            self._os_deallocate_floating_ip(entity, context)
        else:
            raise exc.HTTPBadRequest()

    def _os_chg_passwd_vm(self, entity, attributes, instance, context):
        """
        Implements changing of a vm's admin password
        """
        # Use the password extension?
        msg = _('Changing admin password of virtual machine with id %s') % \
                                                            entity.identifier
        LOG.info(msg)
        if 'org.openstack.credentials.admin_pwd' not in attributes:
            msg = _("'org.openstack.credentials.admin_pwd' "
                                        "was not supplied in the request.")
            LOG.error(msg)
            exc.HTTPBadRequest()

        new_password = attributes['org.openstack.credentials.admin_pwd']
        self.compute_api.set_admin_password(context, instance, new_password)

        # No need to update attributes - state remains the same.

    def _os_revert_resize_vm(self, entity, instance, context):
        """
        Implements reverting of a resized vm
        """
        msg = _('Reverting resized virtual machine with id %s') % \
                                                            entity.identifier
        LOG.info(msg)
        try:
            self.compute_api.revert_resize(context, instance)
        except exception.MigrationNotFound:
            msg = _("Instance has not been resized.")
            raise exc.HTTPBadRequest(explanation=msg)
        except exception.InstanceInvalidState:
            exc.HTTPConflict()
        except Exception:
            msg = _('Error in revert-resize.')
            LOG.error(msg)
            raise exc.HTTPBadRequest()
        entity.attributes['occi.compute.state'] = 'inactive'

    def _os_confirm_resize_vm(self, entity, instance, context):
        """
        Implements the confirmation of a resized vm.
        """
        msg = _('Confirming resize of virtual machine with id %s') % \
                                                            entity.identifier
        LOG.info(msg)
        try:
            self.compute_api.confirm_resize(context, instance)
        except exception.MigrationNotFound:
            msg = _("Instance has not been resized.")
            raise exc.HTTPBadRequest(explanation=msg)
        except exception.InstanceInvalidState:
            exc.HTTPConflict()
        except Exception:
            msg = _('Error in confirm-resize.')
            LOG.error(msg)
            raise exc.HTTPBadRequest()
        entity.attributes['occi.compute.state'] = 'active'

    def _os_create_image(self, entity, attributes, instance, context):
        """
        implements the creation of an image of the specified vm
        """
        msg = _('Creating image from virtual machine with id %s') % \
                                                            entity.identifier
        LOG.info(msg)
        if 'org.openstack.snapshot.image_name' not in attributes:
            exc.HTTPBadRequest()

        image_name = attributes['org.openstack.snapshot.image_name']
        props = {}

        try:
            self.compute_api.snapshot(context,
                                      instance,
                                      image_name,
                                      extra_properties=props)

        except exception.InstanceInvalidState:
            exc.HTTPConflict()

    def _os_allocate_floating_ip(self, entity, attributes, instance, context):
        """
        This allocates a floating ip from the supplied floating ip pool. The
        pool is specified as an optional parameter in the action request.
        Currently, this only supports the assignment of 1 floating IP.
        """
        for mixin in entity.mixins:
            if (mixin.scheme + mixin.term) == OS_FLOATING_IP_EXT.scheme + \
                                                    OS_FLOATING_IP_EXT.term:
                #TODO(dizz): implement support for multiple floating ips
                #            needs support in pyssf for URI in link
                msg = _('There is already a floating IP assigned to the VM')
                LOG.error(msg)
                exc.HTTPBadRequest(explanation=msg)

        if 'org.openstack.network.floating.pool' not in attributes:
            pool = None
        else:
            pool = attributes['org.openstack.network.floating.pool']

        address = self.network_api.allocate_floating_ip(context, pool)

        self.compute_api.associate_floating_ip(context, instance, address)

        # once the address is allocated we need to reflect that fact
        # on the resource holding it.
        entity.mixins.append(OS_FLOATING_IP_EXT)
        entity.attributes['org.openstack.network.floating.ip'] = address

    def _os_deallocate_floating_ip(self, entity, context):
        """
        This deallocates a floating ip from the compute resource.
        This returns the deallocated IP address to the pool.
        """
        address = entity.attributes['org.openstack.network.floating.ip']
        self.network_api.disassociate_floating_ip(context, address)
        self.network_api.release_floating_ip(context, address)

        # remove the mixin
        for mixin in entity.mixins:
            if (mixin.scheme + mixin.term) == OS_FLOATING_IP_EXT.scheme + \
                                                    OS_FLOATING_IP_EXT.term:
                entity.mixins.remove(mixin)
                entity.attributes.pop('org.openstack.network.floating.ip')
