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
Set of extensions to get OCCI work with OpenStack.
"""

#pylint: disable=W0232,R0912,R0201,R0903

from occi import core_model


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
