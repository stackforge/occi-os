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
from webob import exc

from nova import context
from nova import test
try:
    from api import registry
    from api.storage import storageresource
except ImportError:
    pass
import tests as occi


class TestOcciStorageResource(test.TestCase):

    def setUp(self):
        super(TestOcciStorageResource, self).setUp()

        gettext.install('nova-api-occi')

        # create sec context
        self.user_id = 'fake'
        self.project_id = 'fake'
        self.context = context.RequestContext(self.user_id,
                                              self.project_id,
                                              is_admin=True)
        if not occi.missing_pyssf():
            self.stubs.Set(registry.OCCIRegistry, 'get_resource',
                           occi.fake_get_resource)
            from nova import volume
            self.stubs.Set(volume.API, 'get', occi.fake_storage_get)
            self.stubs.Set(volume.API, 'delete', occi.fake_storage_delete)

            # OCCI related setup
            self.entity = core_model.Entity("123", 'A test entity', None, [])
            self.entity.attributes['occi.storage.size'] = '1.0'
            self.entity.attributes['occi.storage.state'] = 'offline'
            self.entity.attributes['occi.core.id'] = '321'
            self.reg = registry.OCCIRegistry()
            self.extras = {'nova_ctx': self.context,
                           'registry': self.reg}

            self.class_under_test = storageresource.StorageBackend()

    @test.skip_if(occi.missing_pyssf(), "Test requires pyssf")
    def test_create_for_success(self):
        '''
        Try to create an OCCI entity.
        '''
        self.assertTrue((self.entity.attributes['occi.storage.state'] ==
                                                                    'offline'))
        self.class_under_test.create(self.entity, self.extras)
        self.assertTrue((self.entity.attributes['occi.storage.state'] ==
                                                                    'online'))

    @test.skip_if(occi.missing_pyssf(), "Test requires pyssf")
    def test_retrieve_for_success(self):
        self.assertTrue(len(self.entity.actions) == 0)
        self.class_under_test.retrieve(self.entity, self.extras)
        self.assertTrue(len(self.entity.actions) > 0)

    @test.skip_if(occi.missing_pyssf(), "Test requires pyssf")
    def test_delete_for_success(self):
        try:
            self.class_under_test.delete(self.entity, self.extras)
        except exc.HTTPNotFound:
            self.fail('Could not find entity to delete')
