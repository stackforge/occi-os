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
import random
from occi import backend
from occi import exceptions

from occi_os_api.extensions import os_addon
from occi_os_api.nova_glue import vm
from occi_os_api.nova_glue import security


class OsComputeBackend(backend.MixinBackend, backend.ActionBackend):
    """
    The OpenStackCompute backend.
    """

    def retrieve(self, entity, extras):
        """
        Add OpenStack related actions.
        """
        if 'occi.compute.state' in entity.attributes and  entity.attributes[
                  'occi.compute.state'] == 'active':
            entity.actions.append(os_addon.OS_CREATE_IMAGE)
            entity.actions.append(os_addon.OS_CHG_PWD)

    def action(self, entity, action, attributes, extras):
        """
        This is called by pyssf when an action request is issued.
        """
        context = extras['nova_ctx']
        uid = entity.attributes['occi.core.id']

        if action == os_addon.OS_CHG_PWD:
            if 'org.openstack.credentials.admin_pwd' not in attributes:
                msg = 'org.openstack.credentials.admin_pwd was not supplied'\
                      ' in the request.'
                raise AttributeError(msg)

            new_password = attributes['org.openstack.credentials.admin_pwd']
            vm.set_password_for_vm(uid, new_password, context)
        elif action == os_addon.OS_CREATE_IMAGE:
            if 'org.openstack.snapshot.image_name' not in attributes:
                raise AttributeError('Missing image name')

            image_name = attributes['org.openstack.snapshot.image_name']
            vm.snapshot_vm(uid, image_name, context)
        else:
            raise AttributeError('Not an applicable action.')


class SecurityGroupBackend(backend.UserDefinedMixinBackend):
    """
    Security Group backend.
    """

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
                                                 extras['nova_ctx'])
        security.remove_group(security_group.id, context)


class SecurityRuleBackend(backend.KindBackend):
    """
    Security rule backend.
    """

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
            msg = 'This rule already exists in group. %s' %\
                  str(security_group)
            raise AttributeError(msg)

        security.create_rule(sg_rule, context)

    def delete(self, entity, extras):
        """
        Deletes the security rule.
        """
        try:
            context = extras['nova_ctx']
            rule = security.get_rule(entity.attributes['occi.core.id'],
                                     context)

            security.remove_rule(rule, context)
        except Exception as error:
            raise exceptions.HTTPError(500, str(error))


def make_sec_rule(entity, sec_grp_id):
    """
    Create and validate the security rule.
    """
    # TODO: add some checks for missing attributes!

    name = random.randrange(0, 99999999)
    sg_rule = {'id': name,
               'parent_group_id': sec_grp_id}
    entity.attributes['occi.core.id'] = str(sg_rule['id'])
    prot = \
    entity.attributes['occi.network.security.protocol'].lower().strip()
    if prot in ('tcp', 'udp', 'icmp'):
        sg_rule['protocol'] = prot
    else:
        raise AttributeError('Invalid protocol defined:' + prot)
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
        if os_addon.SEC_GROUP in mixin.related:
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
