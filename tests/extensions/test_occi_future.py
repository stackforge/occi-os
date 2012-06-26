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

import gettext

try:
    from occi import core_model
except ImportError:
    pass

from nova import context
from nova import compute
from nova import db
from nova import flags
from nova import test
try:
    from api.extensions import occi_future
    from api import registry
except ImportError:
    pass
from tests import occi


FLAGS = flags.FLAGS


class TestOcciSecurityGroupBackend(test.TestCase):

    def setUp(self):
        super(TestOcciSecurityGroupBackend, self).setUp()

        gettext.install('nova-api-occi')

        # create sec context
        self.user_id = 'fake'
        self.project_id = 'fake'
        self.context = context.RequestContext(self.user_id,
                                              self.project_id,
                                              is_admin=True)

        # OCCI related setup
        if not occi.missing_pyssf():
            self.category = occi_future.UserSecurityGroupMixin(
                    term='my_grp',
                    scheme='http://www.mystuff.com/mygroup#',
                    related=[occi_future.SEC_GROUP],
                    attributes=None,
                    location='/security/my_grp/')

            self.extras = {'nova_ctx': self.context,
                           'registry': registry.OCCIRegistry()}

            self.class_under_test = occi_future.SecurityGroupBackend()

    @test.skip_if(occi.missing_pyssf(), "Test requires pyssf")
    def test_create_for_success(self):
        self.class_under_test.init_sec_group(self.category, self.extras)

    @test.skip_if(occi.missing_pyssf(), "Test requires pyssf")
    def test_delete_for_success(self):
        self.stubs.Set(db, 'security_group_get_by_name',
                       occi.fake_db_security_group_get_by_name)
        self.stubs.Set(db, 'security_group_in_use',
                       occi.fake_db_security_group_in_use)
        self.class_under_test.destroy(self.category, self.extras)

        self.stubs.UnsetAll()


class TestOcciSecurityRuleBackend(test.TestCase):

    def setUp(self):
        super(TestOcciSecurityRuleBackend, self).setUp()

        # create sec context
        self.user_id = 'fake'
        self.project_id = 'fake'
        self.context = context.RequestContext(self.user_id,
                                              self.project_id,
                                              is_admin=True)

        # OCCI related setup
        if not occi.missing_pyssf():
            self.category = occi_future.UserSecurityGroupMixin(
                    term='my_grp',
                    scheme='http://www.mystuff.com/mygroup#',
                    related=[occi_future.SEC_GROUP],
                    attributes=None,
                    location='/security/my_grp/')

            self.entity = core_model.Entity("123", 'A test entity', None,
                                 [self.category])
            self.entity.attributes['occi.core.id'] = '123123123'
            self.entity.attributes['occi.network.security.protocol'] = 'tcp'
            self.entity.attributes['occi.network.security.to'] = '22'
            self.entity.attributes['occi.network.security.from'] = '22'
            self.entity.attributes['occi.network.security.range'] = \
                                                                '0.0.0.0/24'
            self.entity.links = []
            self.extras = {'nova_ctx': self.context,
                           'registry': registry.OCCIRegistry()}

            self.class_under_test = occi_future.SecurityRuleBackend()

    @test.skip_if(occi.missing_pyssf(), "Test requires pyssf")
    def test_create_for_success(self):
        self.stubs.Set(db, 'security_group_get_by_name',
                       occi.fake_db_security_group_get_by_name)
        self.class_under_test.create(self.entity, self.extras)

    @test.skip_if(occi.missing_pyssf(), "Test requires pyssf")
    def test_delete_for_success(self):
        self.stubs.Set(db, 'security_group_rule_get',
                       occi.fake_db_security_group_rule_get)
        self.stubs.Set(db, 'security_group_get',
                       occi.fake_db_security_group_get)
        self.stubs.Set(db, 'security_group_rule_destroy',
                       occi.fake_db_security_group_rule_destroy)
        self.stubs.Set(compute.API, 'trigger_security_group_rules_refresh',
                       occi.fake_compute_trigger_security_group_rules_refresh)

        self.class_under_test.delete(self.entity, self.extras)
