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
Features some extensions which later might make it into OCCI.
"""

#pylint: disable=W0232,R0903,R0201

from occi import core_model


# Console Link Extension
CONSOLE_LINK = core_model.Kind(
                        'http://schemas.ogf.org/infrastructure/compute#',
                        'console',
                        [core_model.Link.kind],
                        None,
                        'This is a link to the VMs console',
                        None,
                        '/compute/consolelink/')


# SSH Console Kind Extension
_SSH_CONSOLE_ATTRIBUTES = {'org.openstack.compute.console.ssh': '', }
SSH_CONSOLE = core_model.Kind(
                'http://schemas.openstack.org/occi/infrastructure/compute#',
                'ssh_console',
                None,
                None,
                'SSH console kind',
                _SSH_CONSOLE_ATTRIBUTES,
                '/compute/console/ssh/')


# VNC Console Kind Extension
_VNC_CONSOLE_ATTRIBUTES = {'org.openstack.compute.console.vnc': '', }
VNC_CONSOLE = core_model.Kind(
                'http://schemas.openstack.org/occi/infrastructure/compute#',
                'vnc_console',
                None,
                None,
                'VNC console kind',
                _VNC_CONSOLE_ATTRIBUTES,
                '/compute/console/vnc/')


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


# An extended Mixin, an extension
class UserSecurityGroupMixin(core_model.Mixin):
    """
    Empty Mixin.
    """
    pass
