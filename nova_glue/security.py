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
Security related 'glue'
"""


from nova import compute
from nova import db
from nova import utils
from nova.flags import FLAGS

# connect to nova
from occi import exceptions

COMPUTE_API = compute.API()

SEC_HANDLER = utils.import_object(FLAGS.security_group_handler)
#SEC_HANDLER = importutils.import_object(FLAGS.security_group_handler)


def create_group(name, description, context):
    """
    Create a OS security group.

    name -- Name of the group.
    description -- Description.
    context -- The os context.
    """
    if db.security_group_exists(context, context.project_id, name):
        raise AttributeError('Security group already exists: ' + name)

    group = {'user_id': context.user_id,
             'project_id': context.project_id,
             'name': name,
             'description': description}
    db.security_group_create(context, group)
    SEC_HANDLER.trigger_security_group_create_refresh(context, group)


def remove_group(group_id, context):
    """
    Remove a security group.

    group_id -- the group.
    context -- The os context.
    """
    try:
        if db.security_group_in_use(context, group_id):
            raise AttributeError('Security group is still in use')

        db.security_group_destroy(context, group_id)
        SEC_HANDLER.trigger_security_group_destroy_refresh(
            context, group_id)

    except Exception as error:
        raise AttributeError(error)


def retrieve_group(mixin_term, project_id, context):
    """
    Retrieve the security group associated with the security mixin.

    mixin_term -- The term of the mixin representing the group.
    project_id -- The project id.
    context -- The os context.
    """
    try:
        sec_group = db.security_group_get_by_name(context,
                                                  project_id,
                                                  mixin_term)
    except Exception:
        # ensure that an OpenStack sec group matches the mixin
        # if not, create one.
        # This has to be done as pyssf has no way to associate
        # a handler for the creation of mixins at the query interface
        msg = 'Security group does not exist.'
        raise AttributeError(msg)

    return sec_group


def create_rule(rule, context):
    """
    Create a security rule.

    rule -- The rule.
    context -- The os context.
    """
    # TODO: check exception handling!
    db.security_group_rule_create(context, rule)


def remove_rule(rule, context):
    """
    Remove a security rule.

    rule -- The rule
    context -- The os context.
    """
    # TODO: check exception handling!
    group_id = rule['parent_group_id']
    # TODO(dizz): method seems to be gone!
    # self.compute_api.ensure_default_security_group(extras['nova_ctx'])
    security_group = db.security_group_get(context, group_id)

    db.security_group_rule_destroy(context, rule['id'])
    SEC_HANDLER.trigger_security_group_rule_destroy_refresh(context,
        [rule['id']])
    # TODO: method is one!
    COMPUTE_API.trigger_security_group_rules_refresh(context,
                                                     security_group['id'])


def get_rule(uid, context):
    """
    Retrieve a rule.

    uid -- Id of the rule (entity.attributes['occi.core.id'])
    context -- The os context.
    """
    try:
        rule = db.security_group_rule_get(context,
                                          int(uid))
    except Exception:
        raise exceptions.HTTPError(404, 'Rule not found!')
    return rule
