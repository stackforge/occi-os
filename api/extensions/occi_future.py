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

import random

from nova_glue import security

from occi import backend
from occi import core_model


# TODO(dizz): Remove SSH Console and VNC Console once URI support is added to
#             pyssf


def get_extensions():
    return [
            {
             'categories': [CONSOLE_LINK, SSH_CONSOLE, VNC_CONSOLE, ],
             'handler': backend.KindBackend(),
            },
            {
             'categories': [SEC_RULE, ],
             'handler': SecurityRuleBackend(),
            },
            {
              'categories': [SEC_GROUP, ],
              'handler': SecurityGroupBackend(),
            },
           ]


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
    pass


# The same approach can be used to create and delete VM images.
class SecurityGroupBackend(backend.UserDefinedMixinBackend):

    def init_sec_group(self, category, extras):
        """
        Creates the security group as specified in the request.
        """
        #do not recreate default openstack security groups
        if (category.scheme ==
                'http://schemas.openstack.org/infrastructure/security/group#'):
            return

        context = extras['nova_ctx']

        group_name = category.term.strip()
        group_description = (category.title.strip()
                                            if category.title else group_name)

        security.create_group(group_name, group_description, context)

    def destroy(self, category, extras):
        """
        Deletes the specified security group.
        """
        context = extras['nova_ctx']
        security_group = security.retrieve_group(category.term,
                                                 extras['nova_ctx'].project_id,
                                                 extras)
        security.remove_group(security_group, context)


class SecurityRuleBackend(backend.KindBackend):

    def create(self, entity, extras):
        """
        Creates a security rule.
        The group to add the rule to must exist.
        In OCCI-speak this means the mixin must be supplied with the request
        """
        sec_mixin = get_sec_mixin(entity)
        context = extras['nova_ctx']
        security_group = security.retrieve_group(sec_mixin.term,
                                                 extras['nova_ctx']
                                                 .project_id, context)
        sg_rule = make_sec_rule(entity, security_group['id'])

        if security_group_rule_exists(security_group, sg_rule):
            #This rule already exists in group
            msg = ('This rule already exists in group. %s') % \
                                                        str(security_group)
            raise AttributeError(msg)

        security.create_rule(sg_rule, context)

    def delete(self, entity, extras):
        """
        Deletes the security rule.
        """
        context = extras['nova_ctx']
        rule = security.get_rule(entity.attributes['occi.core.id'], context)

        security.remove_rule(rule, context)


def make_sec_rule(entity, sec_grp_id):
    """
    Create and validate the security rule.
    """
    nm = random.randrange(0, 99999999)
    sg_rule = {'id': nm}
    entity.attributes['occi.core.id'] = str(sg_rule['id'])
    sg_rule['parent_group_id'] = sec_grp_id
    prot =\
    entity.attributes['occi.network.security.protocol'].lower().strip()
    if prot in ('tcp', 'udp', 'icmp'):
        sg_rule['protocol'] = prot
    else:
        raise AttributeError('Invalid protocol defined.')
    from_p = entity.attributes['occi.network.security.to'].strip()
    from_p = int(from_p)
    if (type(from_p) is int) and 0 < from_p <= 65535:
        sg_rule['from_port'] = from_p
    else:
        raise AttributeError('No valid from port defined.')
    to_p = entity.attributes['occi.network.security.to'].strip()
    to_p = int(to_p)
    if (type(to_p) is int) and 0 < to_p <= 65535:
        sg_rule['to_port'] = to_p
    else:
        raise AttributeError('No valid to port defined.')
    if from_p > to_p:
        raise AttributeError('From port is bigger than to port defined.')
    cidr = entity.attributes['occi.network.security.range'].strip()
    if len(cidr) <= 0:
        cidr = '0.0.0.0/0'
        # TODO(dizz): find corresponding call in master!
    #if utils.is_valid_cidr(cidr):
    if True:
        sg_rule['cidr'] = cidr
    else:
        raise AttributeError('No valid CIDR defined.')
    sg_rule['group'] = {}
    return sg_rule


def get_sec_mixin(entity):
    """
    Get the security mixin of the supplied entity.
    """
    sec_mixin_present = 0
    sec_mixin = None
    for mixin in entity.mixins:
        if SEC_GROUP in mixin.related:
            sec_mixin = mixin
            sec_mixin_present += 1

    if not sec_mixin_present:
        # no mixin of the type security group was found
        msg = 'No security group mixin was found'
        raise AttributeError(msg)
    if sec_mixin_present > 1:
        msg = 'More than one security group mixin was found'
        raise AttributeError(msg)

    return sec_mixin


def security_group_rule_exists(security_group, values):
    """
    Indicates whether the specified rule values are already
    defined in the given security group.
    """
    # Taken directly from security_groups.py as that method is not
    # directly import-able.
    for rule in security_group['rules']:
        is_duplicate = True
        keys = ('group_id', 'cidr', 'from_port', 'to_port', 'protocol')
        for key in keys:
            if rule.get(key) != values.get(key):
                is_duplicate = False
                break
        if is_duplicate:
            return True
    return False