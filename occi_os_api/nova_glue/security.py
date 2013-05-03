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
Security related 'glue'
"""

# L8R: Check exception handling of this routines!

from nova import compute
from nova import db
from nova.flags import FLAGS
from nova.openstack.common import importutils

from occi import exceptions

# connect to nova
COMPUTE_API = compute.API()

SEC_HANDLER = importutils.import_object(FLAGS.security_group_handler)


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
        #if db.security_group_in_use(context, group_id):
        #    raise AttributeError('Security group is still in use')

        db.security_group_destroy(context, group_id)
        SEC_HANDLER.trigger_security_group_destroy_refresh(
            context, group_id)

    except Exception as error:
        raise AttributeError(error)


def retrieve_group(mixin_term, context):
    """
    Retrieve the security group associated with the security mixin.

    mixin_term -- The term of the mixin representing the group.
    context -- The os context.
    """
    try:
        sec_group = db.security_group_get_by_name(context, context.project_id,
                                                  mixin_term)
    except Exception as err:
        msg = err.message
        raise AttributeError(msg)

    return sec_group


def create_rule(rule, context):
    """
    Create a security rule.

    rule -- The rule.
    context -- The os context.
    """
    try:
        db.security_group_rule_create(context, rule)
    except Exception as err:
        raise AttributeError('Unable to create rule: ' + str(err))


def remove_rule(rule, context):
    """
    Remove a security rule.

    rule -- The rule
    context -- The os context.
    """
    group_id = rule['parent_group_id']

    try:
        db.security_group_rule_destroy(context, rule['id'])
        SEC_HANDLER.trigger_security_group_rule_destroy_refresh(context,
            [rule['id']])
    except Exception as err:
        raise AttributeError('Unable to remove rule: ' + str(err))


def retrieve_rule(uid, context):
    """
    Retrieve a rule.

    uid -- Id of the rule (entity.attributes['occi.core.id'])
    context -- The os context.
    """
    try:
        return db.security_group_rule_get(context,
                                          int(uid))
    except Exception:
        raise exceptions.HTTPError(404, 'Rule not found!')
