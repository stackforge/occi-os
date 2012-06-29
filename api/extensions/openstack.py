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
from nova_glue import vm, net


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

    def action(self, entity, action, attributes, extras):
        """
        This is called by pyssf when an action request is issued.
        """
        context = extras['nova_ctx']
        uid = entity.attributes['occi.core.id']

        if action == OS_CHG_PWD:
            if 'org.openstack.credentials.admin_pwd' not in attributes:
                msg = 'org.openstack.credentials.admin_pwd was not supplied' \
                      ' in the request.'
                raise AttributeError(msg)

            new_password = attributes['org.openstack.credentials.admin_pwd']
            vm.set_password_for_vm(uid, new_password, context)
        elif action == OS_REVERT_RESIZE:
            vm.revert_resize_vm(uid, context)
            entity.attributes['occi.compute.state'] = 'inactive'
        elif action == OS_CONFIRM_RESIZE:
            vm.confirm_resize_vm(uid, context)
            entity.attributes['occi.compute.state'] = 'active'
        elif action == OS_CREATE_IMAGE:
            if 'org.openstack.snapshot.image_name' not in attributes:
                raise AttributeError('Missing image name')

            image_name = attributes['org.openstack.snapshot.image_name']
            vm.snapshot_vm(uid, image_name, context)
        elif action == OS_ALLOC_FLOATING_IP:
            for mixin in entity.mixins:
                if (mixin.scheme + mixin.term) == OS_FLOATING_IP_EXT.scheme +\
                                                  OS_FLOATING_IP_EXT.term:
                    #TODO(dizz): implement support for multiple floating ips
                    #            needs support in pyssf for URI in link
                    raise AttributeError('There is already a floating IP '
                                         'assigned to the VM')

            address = net.add_flaoting_ip_to_vm(uid, attributes, context)

            # once the address is allocated we need to reflect that fact
            # on the resource holding it.
            entity.mixins.append(OS_FLOATING_IP_EXT)
            entity.attributes['org.openstack.network.floating.ip'] = address
        elif action == OS_DEALLOC_FLOATING_IP:
            address = entity.attributes['org.openstack.network.floating.ip']
            net.remove_floating_ip(uid, address, context)

            # remove the mixin
            for mixin in entity.mixins:
                if (mixin.scheme + mixin.term) == OS_FLOATING_IP_EXT.scheme +\
                                                  OS_FLOATING_IP_EXT.term:
                    entity.mixins.remove(mixin)
                    entity.attributes.pop('org.openstack.network.floating.ip')
        else:
            raise AttributeError('Not an applicable action.')
