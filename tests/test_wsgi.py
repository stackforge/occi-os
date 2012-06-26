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
    from occi.extensions import infrastructure
except ImportError:
    pass

from nova import context
from nova import db
from nova import image
from nova import test
from nova import wsgi
try:
    from api.extensions import occi_future
    from api.extensions import openstack
    from api import wsgi as occi_wsgi
except ImportError:
    pass
from nova.network import api as net_api
import tests as occi


class TestOcciWsgiApp(test.TestCase):

    def setUp(self):
        super(TestOcciWsgiApp, self).setUp()

        gettext.install('nova-api-occi')

        # setup img service...
        self.stubs.Set(image, 'get_default_image_service',
                       occi.fake_get_default_image_service)
        self.stubs.Set(net_api.API, 'get_floating_ip_pools',
                       occi.fake_get_floating_ip_pools)
        self.stubs.Set(db, 'security_group_get_by_project',
                       occi.fake_security_group_get_by_project)

        self.user_id = 'fake'
        self.project_id = 'fake'
        self.context = context.RequestContext(self.user_id,
                                              self.project_id,
                                              is_admin=True)

    @test.skip_if(occi.missing_pyssf(), "Test requires pyssf")
    def test_occi_app_for_success(self):
        '''
        test constructor...
        '''
        occi_wsgi.OCCIApplication()

    @test.skip_if(occi.missing_pyssf(), "Test requires pyssf")
    def test_occi_app_for_sanity(self):
        '''
        test for sanity...
        '''
        app = occi_wsgi.OCCIApplication()
        occi_wsgi.FLAGS.set_default('show_default_net_config', True, None)

        self.assertTrue(isinstance(app, wsgi.Application),
                        'OCCI WSGI app needs to be derived frrom wsgi.App')

        # check if all core occi infrastructure kinds and mixins are present
        cats = app.registry.get_categories(None)

        self.assertTrue(infrastructure.COMPUTE in cats)
        self.assertTrue(infrastructure.STORAGE in cats)
        self.assertTrue(infrastructure.STORAGELINK in cats)
        self.assertTrue(infrastructure.NETWORK in cats)
        self.assertTrue(infrastructure.NETWORKINTERFACE in cats)
        self.assertTrue(infrastructure.IPNETWORK in cats)
        self.assertTrue(infrastructure.IPNETWORKINTERFACE in cats)
        self.assertTrue(infrastructure.OS_TEMPLATE in cats)
        self.assertTrue(infrastructure.RESOURCE_TEMPLATE in cats)

        # check if all core occi actions are present
        self.assertTrue(infrastructure.START in cats)
        self.assertTrue(infrastructure.STOP in cats)
        self.assertTrue(infrastructure.RESTART in cats)
        self.assertTrue(infrastructure.SUSPEND in cats)

        self.assertTrue(infrastructure.UP in cats)
        self.assertTrue(infrastructure.DOWN in cats)

        self.assertTrue(infrastructure.ONLINE in cats)
        self.assertTrue(infrastructure.OFFLINE in cats)
        self.assertTrue(infrastructure.BACKUP in cats)
        self.assertTrue(infrastructure.RESIZE in cats)

        # check if all necessary OpenStack Extensions are present
        self.assertTrue(openstack.OS_KEY_PAIR_EXT in cats)
        self.assertTrue(openstack.OS_ADMIN_PWD_EXT in cats)
        self.assertTrue(openstack.OS_ACCESS_IP_EXT in cats)

        # check if all necessary OpenStack action Extensions are present
        self.assertTrue(openstack.OS_CHG_PWD in cats)
        self.assertTrue(openstack.OS_REVERT_RESIZE in cats)
        self.assertTrue(openstack.OS_CONFIRM_RESIZE in cats)
        self.assertTrue(openstack.OS_CREATE_IMAGE in cats)
        self.assertTrue(openstack.OS_ALLOC_FLOATING_IP in cats)
        self.assertTrue(openstack.OS_DEALLOC_FLOATING_IP in cats)

        # check if all necessary occi_future extensions are present
        self.assertTrue(occi_future.CONSOLE_LINK in cats)
        self.assertTrue(occi_future.SSH_CONSOLE in cats)
        self.assertTrue(occi_future.VNC_CONSOLE in cats)
        self.assertTrue(occi_future.SEC_RULE in cats)
        self.assertTrue(occi_future.SEC_GROUP in cats)

        # make a call so OS templates get filled
        environ = {'SERVER_NAME': 'localhost',
                   'SERVER_PORT': '8080',
                   'PATH_INFO': '/',
                   'REQUEST_METHOD': 'GET',
                   'nova.context': self.context}

        app(environ, occi.fake_response)

        # now test for os, resource templates and sec groups
        i = 0
        types = ['m1.xlarge', 'm1.medium', 'm1.tiny', 'm1.small', 'm1.large']
        for cat in app.registry.get_categories(None):
            if hasattr(cat, 'related') and \
                            infrastructure.RESOURCE_TEMPLATE in cat.related:
                self.assertTrue(cat.term in types)
                scheme = 'http://schemas.openstack.org/template/resource#'
                self.assertEquals(scheme, cat.scheme)
                i += 1
        self.assertTrue(i, len(types))

        i = 0
        images = ['fakeimage7', 'fakeimage6', 'fakeimage123456']
        for cat in app.registry.get_categories(None):
            if hasattr(cat, 'related') and \
                                    infrastructure.OS_TEMPLATE in cat.related:
                self.assertTrue(cat.term in images)
                scheme = 'http://schemas.openstack.org/template/os#'
                self.assertEquals(scheme, cat.scheme)
                i += 1
        self.assertTrue(i, len(images))

        i = 0
        pools = ['test1', 'test2']
        scheme = 'http://schemas.openstack.org/instance/network/pool/floating#'
        for cat in app.registry.get_categories(None):
            if cat.scheme == scheme:
                self.assertTrue(cat.term in pools)
                i += 1
        self.assertTrue(i, len(pools))

        i = 0
        grps = ['grp1', 'grp2']
        scheme = 'http://schemas.openstack.org/infrastructure/security/group#'
        for cat in app.registry.get_categories(None):
            if cat.scheme == scheme:
                self.assertTrue(cat.term in grps)
                i += 1
        self.assertTrue(i, len(grps))
