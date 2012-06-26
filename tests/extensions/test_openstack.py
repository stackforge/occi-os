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
from nova import flags
from nova import test
try:
    from api import registry
    from api.compute import templates
    from api.extensions import openstack
except ImportError:
    pass
from nova.network import api as net_api
import tests as occi


FLAGS = flags.FLAGS


class TestOcciOpenStackActionBackend(test.TestCase):

    def setUp(self):
        super(TestOcciOpenStackActionBackend, self).setUp()

        gettext.install('nova-api-occi')

        # create sec context
        self.user_id = 'fake'
        self.project_id = 'fake'
        self.context = context.RequestContext(self.user_id,
                                              self.project_id,
                                              is_admin=True)

        self.stubs.Set(compute.API, 'get', occi.fake_compute_get)
        self.stubs.Set(compute.API, 'delete', occi.fake_storage_delete)

        # OCCI related setup
        if not occi.missing_pyssf():
            self.stubs.Set(registry.OCCIRegistry, 'get_resource',
                       occi.fake_get_resource)
            self.os_template = templates.OsTemplate(
                                'http://schemas.openstack.org/template/os#',
                                'foo', '1')
            self.resource_template = templates.ResourceTemplate(
                            'http://schemas.openstack.org/template/resource#',
                            'm1.small')

            self.entity = core_model.Entity("123", 'A test entity', None,
                                 [self.os_template, self.resource_template])
            self.entity.attributes['occi.core.id'] = '123-123-123'
            self.entity.links = []
            self.extras = {'nova_ctx': self.context,
                           'registry': registry.OCCIRegistry()}

            self.class_under_test = openstack.OsComputeActionBackend()

    @test.skip_if(occi.missing_pyssf(), "Test requires pyssf")
    def test_action_for_success(self):
        self.stubs.Set(compute.API, 'set_admin_password',
                       occi.fake_compute_set_admin_password)
        self.stubs.Set(compute.API, 'revert_resize',
                       occi.fake_compute_revert_resize)
        self.stubs.Set(compute.API, 'confirm_resize',
                       occi.fake_compute_confirm_resize)
        self.stubs.Set(compute.API, 'snapshot',
                       occi.fake_compute_snapshot)
        self.stubs.Set(net_api.API, 'allocate_floating_ip',
                       occi.fake_network_allocate_floating_ip)
        self.stubs.Set(compute.API, 'associate_floating_ip',
                       occi.fake_compute_associate_floating_ip)
        self.stubs.Set(net_api.API, 'disassociate_floating_ip',
                       occi.fake_network_disassociate_floating_ip)
        self.stubs.Set(net_api.API, 'release_floating_ip',
                       occi.fake_network_release_floating_ip)

        self.entity.attributes['occi.compute.state'] = 'active'
        self.entity.actions = [openstack.OS_CHG_PWD]
        self.class_under_test.action(self.entity, openstack.OS_CHG_PWD,
                        {'org.openstack.credentials.admin_pwd': 'passwd_'},
                        self.extras)

        self.entity.attributes['occi.compute.state'] = 'active'
        self.entity.actions = [openstack.OS_REVERT_RESIZE]
        self.class_under_test.action(self.entity, openstack.OS_REVERT_RESIZE,
                                                            {}, self.extras)

        self.entity.attributes['occi.compute.state'] = 'active'
        self.entity.actions = [openstack.OS_CONFIRM_RESIZE]
        self.class_under_test.action(self.entity, openstack.OS_CONFIRM_RESIZE,
                                                            {}, self.extras)

        self.entity.attributes['occi.compute.state'] = 'active'
        self.entity.actions = [openstack.OS_CREATE_IMAGE]
        self.class_under_test.action(self.entity, openstack.OS_CREATE_IMAGE,
                            {'org.openstack.snapshot.image_name': 'img'},
                            self.extras)

        self.entity.attributes['occi.compute.state'] = 'active'
        self.entity.actions = [openstack.OS_ALLOC_FLOATING_IP]
        self.class_under_test.action(self.entity,
                            openstack.OS_ALLOC_FLOATING_IP,
                            {'org.openstack.network.floating.pool': 'test'},
                            self.extras)

        self.entity.attributes['occi.compute.state'] = 'active'
        self.entity.actions = [openstack.OS_DEALLOC_FLOATING_IP]
        self.class_under_test.action(self.entity,
                                     openstack.OS_DEALLOC_FLOATING_IP, {},
                                     self.extras)

        self.stubs.UnsetAll()
