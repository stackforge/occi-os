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
Test network resource backend.
"""

#pylint: disable=W0102,C0103,R0904,R0801


import mox
import unittest

from occi import core_model, exceptions
from occi.extensions import infrastructure

from occi_os_api import nova_glue
from occi_os_api.backends import storage


class TestStorageBackend(unittest.TestCase):
    """
    Tests the storage backend!
    """

    def setUp(self):
        """
        Setup the tests.
        """
        self.backend = storage.StorageBackend()
        self.sec_obj = {'nova_ctx': None}
        self.mox = mox.Mox()

    def tearDown(self):
        """
        Cleanup mocks.
        """
        self.mox.UnsetStubs()

    # Test for failure

    def test_create_for_failure(self):
        """
        Test attachement.
        """
        # msg size attribute
        res = mox.MockObject(core_model.Resource)
        res.attributes = {}
        self.assertRaises(AttributeError, self.backend.create, res,
            self.sec_obj)

        # error in volume creation
        res.attributes = {'occi.storage.size': '1'}

        self.mox.StubOutWithMock(nova_glue.storage, 'create_storage')
        nova_glue.storage.create_storage(mox.IsA(object),
            mox.IsA(object)).AndReturn({'id': '1'})
        self.mox.StubOutWithMock(nova_glue.storage, 'get_storage')
        nova_glue.storage.get_storage(mox.IsA(object),
            mox.IsA(object)).AndReturn({'status': 'error'})

        self.mox.ReplayAll()

        self.assertRaises(exceptions.HTTPError, self.backend.create, res,
            self.sec_obj)

        self.mox.VerifyAll()

    def test_action_for_failure(self):
        """
        Test actions
        """
        res = mox.MockObject(core_model.Resource)
        res.actions = []

        # snapshot
        self.assertRaises(AttributeError, self.backend.action, res,
            infrastructure.SNAPSHOT, {}, self.sec_obj)

    # Test for sanity

    def test_create_for_sanity(self):
        """
        Test creation.
        """
        res = mox.MockObject(core_model.Resource)
        res.attributes = {'occi.storage.size': '1'}

        self.mox.StubOutWithMock(nova_glue.storage, 'create_storage')
        nova_glue.storage.create_storage(mox.IsA(object),
            mox.IsA(object)).AndReturn({'id': '1'})
        self.mox.StubOutWithMock(nova_glue.storage, 'get_storage')
        nova_glue.storage.get_storage(mox.IsA(object),
            mox.IsA(object)).AndReturn({'status': 'available'})

        self.mox.ReplayAll()

        self.backend.create(res, self.sec_obj)

        # verify all attrs.
        self.assertEqual(res.attributes['occi.storage.state'], 'active')
        self.assertListEqual([infrastructure.OFFLINE, infrastructure.BACKUP,
                              infrastructure.SNAPSHOT, infrastructure.RESIZE],
                             res.actions)

        self.mox.VerifyAll()

    def test_retrieve_for_sanity(self):
        """
        Test retrieval.
        """
        res = mox.MockObject(core_model.Resource)
        res.attributes = {'occi.core.id': '1'}

        self.mox.StubOutWithMock(nova_glue.storage, 'get_storage')
        nova_glue.storage.get_storage(mox.IsA(object),
            mox.IsA(object)).AndReturn({'status': 'available', 'size': '1'})

        self.mox.ReplayAll()

        self.backend.retrieve(res, self.sec_obj)

        # verify all attrs.
        self.assertEqual(res.attributes['occi.storage.state'], 'online')
        self.assertListEqual([infrastructure.OFFLINE, infrastructure.BACKUP,
                              infrastructure.SNAPSHOT, infrastructure.RESIZE],
            res.actions)

        self.mox.VerifyAll()

        self.mox.UnsetStubs()
        self.mox.StubOutWithMock(nova_glue.storage, 'get_storage')
        nova_glue.storage.get_storage(mox.IsA(object),
            mox.IsA(object)).AndReturn({'status': 'bla', 'size': '1'})

        self.mox.ReplayAll()

        self.backend.retrieve(res, self.sec_obj)

        # verify all attrs.
        self.assertEqual(res.attributes['occi.storage.state'], 'offline')
        self.assertTrue(len(res.actions) == 1)
        self.mox.VerifyAll()

    def test_update_for_sanity(self):
        """
        Test updating.
        """
        res1 = mox.MockObject(core_model.Resource)
        res1.attributes = {}
        res2 = mox.MockObject(core_model.Resource)
        res2.attributes = {'occi.core.title': 'foo', 'occi.core.summary':
            'bar'}

        self.mox.ReplayAll()

        self.backend.update(res1, res2, self.sec_obj)

        # verify all attrs.
        self.assertEqual(res1.attributes['occi.core.title'], 'foo')
        self.assertEqual(res1.attributes['occi.core.summary'], 'bar')

        self.mox.VerifyAll()

    def test_remove_for_sanity(self):
        """
        Test removal.
        """
        res = mox.MockObject(core_model.Resource)
        res.attributes = {'occi.core.id': '1'}

        self.mox.StubOutWithMock(nova_glue.storage, 'delete_storage_instance')
        nova_glue.storage.delete_storage_instance(mox.IsA(object),
            mox.IsA(object))

        self.mox.ReplayAll()

        self.backend.delete(res, self.sec_obj)

        self.mox.VerifyAll()

    def test_action_for_sanity(self):
        """
        Test actions
        """
        res = mox.MockObject(core_model.Resource)
        res.attributes = {'occi.core.id': '1',
                          'occi.core.summary': 'foo'}
        res.actions = [infrastructure.SNAPSHOT, infrastructure.BACKUP]

        # snapshot
        self.mox.StubOutWithMock(nova_glue.storage,
            'snapshot_storage_instance')
        nova_glue.storage.snapshot_storage_instance(mox.IsA(object),
            mox.IsA(object), mox.IsA(object), mox.IsA(object))
        self.mox.ReplayAll()
        self.backend.action(res, infrastructure.SNAPSHOT, {}, self.sec_obj)
        self.mox.VerifyAll()

        # some other action
        self.mox.ReplayAll()
        self.backend.action(res, infrastructure.BACKUP, {}, self.sec_obj)
        self.mox.VerifyAll()


class TestStorageLinkBackend(unittest.TestCase):
    """
    Tests storage linking.
    """

    def setUp(self):
        """
        Setup the tests.
        """
        self.backend = storage.StorageLinkBackend()
        self.sec_obj = {'nova_ctx': None}
        self.mox = mox.Mox()

    def tearDown(self):
        """
        Cleanup mocks.
        """
        self.mox.UnsetStubs()

    # Test for sanity

    def test_create_for_sanity(self):
        """
        Test attachement.
        """
        source = mox.MockObject(core_model.Resource)
        source.attributes = {'occi.core.id': 'foo'}
        target = mox.MockObject(core_model.Resource)
        target.attributes = {'occi.core.id': 'bar'}

        link = core_model.Link('foo', None, [], source, target)
        link.attributes = {'occi.storagelink.deviceid': '/dev/sda'}

        self.mox.StubOutWithMock(nova_glue.vm, 'attach_volume')
        nova_glue.vm.attach_volume(mox.IsA(object), mox.IsA(object),
            mox.IsA(object), mox.IsA(object)).AndReturn({})

        self.mox.ReplayAll()

        self.backend.create(link, self.sec_obj)

        # verify all attrs.
        self.assertEqual(link.attributes['occi.storagelink.deviceid'],
            '/dev/sda')
        self.assertIn('occi.storagelink.mountpoint', link.attributes)
        self.assertEqual(link.attributes['occi.storagelink.state'], 'active')

        self.mox.VerifyAll()

    def test_delete_for_sanity(self):
        """
        Test deattachement.
        """
        source = mox.MockObject(core_model.Resource)
        target = mox.MockObject(core_model.Resource)
        target.attributes = {'occi.core.id': 'bar'}

        link = core_model.Link('foo', None, [], source, target)

        self.mox.StubOutWithMock(nova_glue.vm, 'detach_volume')
        nova_glue.vm.detach_volume(mox.IsA(object), mox.IsA(object))

        self.mox.ReplayAll()

        self.backend.delete(link, self.sec_obj)

        self.mox.VerifyAll()
