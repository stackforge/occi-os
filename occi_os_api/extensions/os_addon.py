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
Set of extensions to get OCCI work with OpenStack.
"""

#pylint: disable=W0232,R0912,R0201,R0903

from occi import core_model

# Network security rule extension to specify firewall rules
_SEC_RULE_ATTRIBUTES = {
    'occi.network.security.protocol': '',
    'occi.network.security.to': '',
    'occi.network.security.from': '',
    'occi.network.security.range': '',
    }
SEC_RULE = core_model.Kind(
    'http://schemas.openstack.org/occi/infrastructure/network/security#',
    'rule',
    [core_model.Resource.kind],
    None,
    'Network security rule kind',
    _SEC_RULE_ATTRIBUTES,
    '/network/security/rule/')

# Network security rule group
SEC_GROUP = core_model.Mixin(
    'http://schemas.ogf.org/occi/infrastructure/security#',
    'group', attributes=None)

# OS change adminstrative password action
_OS_CHG_PWD_ATTRIBUTES = {'org.openstack.credentials.admin_pwd': '', }
OS_CHG_PWD = core_model.Action(
                'http://schemas.openstack.org/instance/action#',
                 'chg_pwd', 'Changes Admin password.',
                 _OS_CHG_PWD_ATTRIBUTES)

# OS create image from VM action
_OS_CREATE_IMAGE_ATTRIBUTES = {'org.openstack.snapshot.image_name': '', }
OS_CREATE_IMAGE = core_model.Action(
                'http://schemas.openstack.org/instance/action#',
                 'create_image', 'Creates a new image for the given server.',
                 _OS_CREATE_IMAGE_ATTRIBUTES)

# A Mixin for OpenStack VMs
_OS_VM_ATTRIBUTES = {'org.openstack.compute.console.vnc': 'immutable',
                     'org.openstack.compute.state': 'immutable'}
OS_VM = core_model.Mixin(
    'http://schemas.openstack.org/compute/instance#',
    'os_vms', actions=[OS_CHG_PWD, OS_CREATE_IMAGE],
    attributes=_OS_VM_ATTRIBUTES)

# OS Key pair extension
_OS_KEY_PAIR_ATTRIBUTES = {'org.openstack.credentials.publickey.name': '',
                       'org.openstack.credentials.publickey.data': '', }
OS_KEY_PAIR_EXT = core_model.Mixin(
    'http://schemas.openstack.org/instance/credentials#',
    'public_key', attributes=_OS_KEY_PAIR_ATTRIBUTES)

# A Mixin for OpenStack Network links
_OS_NET_LINK_ATTRIBUTES = {'org.openstack.network.floating.pool': 'required'}
OS_NET_LINK = core_model.Mixin(
    'http://schemas.openstack.org/network/instance#',
    'os_net_link', actions=[],
    attributes=_OS_NET_LINK_ATTRIBUTES)