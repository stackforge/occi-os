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

from occi import backend
from occi import core_model
from webob import exc

from nova import compute
from nova import db
from nova import flags
from nova import log as logging
from nova import utils


# TODO(dizz): Remove SSH Console and VNC Console once URI support is added to
#             pyssf

#Hi I'm a logger, use me! :-)
LOG = logging.getLogger('nova.api.occi.backends.securityrule')

FLAGS = flags.FLAGS


####################### OCCI Candidate Spec Additions ########################
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

    def __init__(self):
        super(SecurityGroupBackend, self).__init__()
        self.compute_api = compute.API()
        self.sgh = utils.import_object(FLAGS.security_group_handler)

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

        self.compute_api.ensure_default_security_group(context)
        if db.security_group_exists(context, context.project_id, group_name):
            raise exc.HTTPBadRequest(
                explanation=_('Security group %s already exists') % group_name)

        group = {'user_id': context.user_id,
                 'project_id': context.project_id,
                 'name': group_name,
                 'description': group_description}
        db.security_group_create(context, group)
        self.sgh.trigger_security_group_create_refresh(context, group)

    def destroy(self, category, extras):
        """
        Deletes the specified security group.
        """
        context = extras['nova_ctx']
        security_group = self._get_sec_group(extras, category)
        if db.security_group_in_use(context, security_group['id']):
            raise exc.HTTPBadRequest(
                            explanation=_("Security group is still in use"))

        db.security_group_destroy(context, security_group['id'])
        self.sgh.trigger_security_group_destroy_refresh(
            context, security_group['id'])

    def _get_sec_group(self, extras, sec_mixin):
        """
        Retreive the security group by name associated with the security mixin.
        """
        try:
            sec_group = db.security_group_get_by_name(extras['nova_ctx'],
                                 extras['nova_ctx'].project_id, sec_mixin.term)
        except Exception:
            msg = _('Security group does not exist.')
            LOG.error(msg)
            raise exc.HTTPBadRequest()

        return sec_group


class SecurityRuleBackend(backend.KindBackend):

    def __init__(self):
        super(SecurityRuleBackend, self).__init__()
        self.compute_api = compute.API()
        self.sgh = utils.import_object(FLAGS.security_group_handler)

    def create(self, entity, extras):
        """
        Creates a security rule.
        The group to add the rule to must exist.
        In OCCI-speak this means the mixin must be supplied with the request
        """
        msg = _('Creating a network security rule')
        LOG.info(msg)

        sec_mixin = self._get_sec_mixin(entity)
        security_group = self._get_sec_group(extras, sec_mixin)
        sg_rule = self._make_sec_rule(entity, security_group['id'])

        if self._security_group_rule_exists(security_group, sg_rule):
            #This rule already exists in group
            msg = _('This rule already exists in group. %s') % \
                                                        str(security_group)
            LOG.error(msg)
            raise exc.HTTPBadRequest()

        db.security_group_rule_create(extras['nova_ctx'], sg_rule)

    def _make_sec_rule(self, entity, sec_grp_id):
        """
        Create and validate the security rule.
        """
        sg_rule = {}
        sg_rule['id'] = random.randrange(0, 99999999)
        entity.attributes['occi.core.id'] = str(sg_rule['id'])
        sg_rule['parent_group_id'] = sec_grp_id
        prot = \
            entity.attributes['occi.network.security.protocol'].lower().strip()
        if prot in ('tcp', 'udp', 'icmp'):
            sg_rule['protocol'] = prot
        else:
            raise exc.HTTPBadRequest()
        from_p = entity.attributes['occi.network.security.to'].strip()
        from_p = int(from_p)
        if (type(from_p) is int) and from_p > 0 and from_p <= 65535:
            sg_rule['from_port'] = from_p
        else:
            raise exc.HTTPBadRequest()
        to_p = entity.attributes['occi.network.security.to'].strip()
        to_p = int(to_p)
        if (type(to_p) is int) and to_p > 0 and to_p <= 65535:
            sg_rule['to_port'] = to_p
        else:
            raise exc.HTTPBadRequest()
        if from_p > to_p:
            raise exc.HTTPBadRequest()
        cidr = entity.attributes['occi.network.security.range'].strip()
        if len(cidr) <= 0:
            cidr = '0.0.0.0/0'
        if utils.is_valid_cidr(cidr):
            sg_rule['cidr'] = cidr
        else:
            raise exc.HTTPBadRequest()
        sg_rule['group'] = {}
        return sg_rule

    def _get_sec_group(self, extras, sec_mixin):
        """
        Retreive the security group associated with the security mixin.
        """
        try:
            sec_group = db.security_group_get_by_name(extras['nova_ctx'],
                                 extras['nova_ctx'].project_id, sec_mixin.term)
        except Exception:
            # ensure that an OpenStack sec group matches the mixin
            # if not, create one.
            # This has to be done as pyssf has no way to associate
            # a handler for the creation of mixins at the query interface
            msg = _('Security group does not exist.')
            LOG.error(msg)
            raise exc.HTTPBadRequest()

        return sec_group

    def _get_sec_mixin(self, entity):
        """
        Get the security mixin of the supplied entity.
        """
        sec_mixin_present = 0
        sec_mixin = None
        for mixin in entity.mixins:
            if SEC_GROUP in mixin.related:
                sec_mixin = mixin
                sec_mixin_present = sec_mixin_present + 1

        if not sec_mixin_present:
            # no mixin of the type security group was found
            msg = _('No security group mixin was found')
            LOG.error(msg)
            raise exc.HTTPBadRequest()
        if sec_mixin_present > 1:
            msg = _('More than one security group mixin was found')
            LOG.error(msg)
            raise exc.HTTPBadRequest()

        return sec_mixin

    def _security_group_rule_exists(self, security_group, values):
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

    def delete(self, entity, extras):
        """
        Deletes the security rule.
        """
        msg = _('Deleting a network security rule')
        LOG.info(msg)
        self.compute_api.ensure_default_security_group(extras['nova_ctx'])
        try:
            rule = db.security_group_rule_get(extras['nova_ctx'],
                                        int(entity.attributes['occi.core.id']))
        except Exception:
            raise exc.HTTPNotFound()

        group_id = rule['parent_group_id']
        self.compute_api.ensure_default_security_group(extras['nova_ctx'])
        security_group = db.security_group_get(extras['nova_ctx'], group_id)

        db.security_group_rule_destroy(extras['nova_ctx'], rule['id'])
        self.sgh.trigger_security_group_rule_destroy_refresh(
                                            extras['nova_ctx'], [rule['id']])
        self.compute_api.trigger_security_group_rules_refresh(
                                                        extras['nova_ctx'],
                                                        security_group['id'])
