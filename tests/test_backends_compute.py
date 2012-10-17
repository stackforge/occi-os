# coding=utf-8
# vim: tabstop=4 shiftwidth=4 softtabstop=4

#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""
Unittest for the Compute Backend.
"""

#pylint: disable=W0102,C0103,R0904

import unittest

# depenency from nova :-)
import mox
from nova.compute import vm_states

from occi import core_model
from occi.extensions import infrastructure

from occi_os_api import nova_glue
from occi_os_api.backends import compute
from occi_os_api.extensions import os_mixins


class TestComputeBackend(unittest.TestCase):
    """
    Tests the compute backend.
    """

    os_template = os_mixins.OsTemplate('http://example.com', 'unix')
    os_template2 = os_mixins.OsTemplate('http://example.com', 'windows')

    res_template = os_mixins.ResourceTemplate('http://example.com', 'itsy')
    res_template2 = os_mixins.ResourceTemplate('http://example.com', 'bitsy')

    def setUp(self):
        """
        Setup tests.
        """
        self.backend = compute.ComputeBackend()
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
        Test for proper error handling.
        """
        # msg OS template
        res = core_model.Resource('/foo/bar', infrastructure.COMPUTE, [])

        self.assertRaises(AttributeError, self.backend.create, res,
            self.sec_obj)

        # provide immutable attr
        res = core_model.Resource('/foo/bar', infrastructure.COMPUTE,
            [self.os_template])
        res.attributes = {'occi.compute.cores': 2}

        self.assertRaises(AttributeError, self.backend.create, res,
            self.sec_obj)

    def test_update_for_failure(self):
        """
        Test if correct errors are thrown.
        """
        # msg mixin
        res1 = core_model.Resource('/foo/bar', infrastructure.COMPUTE, [])
        res1.attributes = {'occi.core.id': 'bar'}
        res2 = core_model.Resource('/foo/bar', infrastructure.COMPUTE, [])

        self.assertRaises(AttributeError, self.backend.update, res1, res2,
            self.sec_obj)

        res2 = core_model.Resource('/foo/bar', infrastructure.COMPUTE,
            [core_model.Category('http://foo.com', 'bar', '', '', '')])

        self.assertRaises(AttributeError, self.backend.update, res1, res2,
            self.sec_obj)

    def test_action_for_failure(self):
        """
        Test if correct errors are thrown.
        """
        # wrong action
        res1 = core_model.Resource('/foo/bar', infrastructure.COMPUTE, [])
        res1.attributes = {'occi.core.id': 'bar'}
        self.mox.StubOutWithMock(nova_glue.vm, 'get_vm')
        nova_glue.vm.get_vm(mox.IsA(object), mox.IsA(object)).AndReturn(
            {
                'vm_state': vm_states.STOPPED
            })
        self.mox.ReplayAll()
        self.assertRaises(AttributeError, self.backend.action, res1,
            infrastructure.STOP, {}, self.sec_obj)
        self.mox.VerifyAll()

        # missing method!
        self.mox.UnsetStubs()
        self.mox.StubOutWithMock(nova_glue.vm, 'get_vm')
        nova_glue.vm.get_vm(mox.IsA(object), mox.IsA(object)).AndReturn(
            {
                'vm_state': vm_states.ACTIVE
            })
        self.mox.ReplayAll()
        self.assertRaises(AttributeError, self.backend.action, res1,
                            infrastructure.RESTART, {}, self.sec_obj)
        self.mox.VerifyAll()

    # Test for Sanity

    def test_create_for_sanity(self):
        """
        Simulate a create call!
        """
        res = core_model.Resource('/foo/bar', infrastructure.COMPUTE,
            [self.os_template])

        self.mox.StubOutWithMock(nova_glue.vm, 'create_vm')
        nova_glue.vm.create_vm(mox.IsA(object), mox.IsA(object)).AndReturn(
            {
                'uuid': 'foo',
                'hostname': 'Server foo',
                'vcpus': 1,
                'memory_mb': 256
            })
        self.mox.StubOutWithMock(nova_glue.storage, 'get_image_architecture')
        nova_glue.storage.get_image_architecture(mox.IsA(object),
            mox.IsA(object)).AndReturn(
            'foo')

        self.mox.ReplayAll()

        self.backend.create(res, self.sec_obj)

        # check if all attrs are there!
        self.assertIn('occi.compute.hostname', res.attributes)
        self.assertIn('occi.compute.architecture', res.attributes)
        self.assertIn('occi.compute.cores', res.attributes)
        self.assertIn('occi.compute.speed', res.attributes)
        self.assertIn('occi.compute.memory', res.attributes)
        self.assertIn('occi.compute.state', res.attributes)

        self.assertEqual('inactive', res.attributes['occi.compute.state'])

        self.assertListEqual([infrastructure.STOP, infrastructure.SUSPEND,
                              infrastructure.RESTART], res.actions)

        self.mox.VerifyAll()

    def test_retrieve_for_sanity(self):
        """
        Simulate a retrieve call!
        """
        res = core_model.Resource('/foo/bar', infrastructure.COMPUTE,
            [self.os_template])
        res.attributes = {'occi.core.id': 'bar'}

        self.mox.StubOutWithMock(nova_glue.vm, 'get_occi_state')
        nova_glue.vm.get_occi_state(mox.IsA(object),
            mox.IsA(object)).AndReturn(('active', [infrastructure.STOP,
                                                   infrastructure.SUSPEND,
                                                   infrastructure.RESTART]))
        self.mox.StubOutWithMock(nova_glue.vm, 'get_vm')
        nova_glue.vm.get_vm(mox.IsA(object), mox.IsA(object)).AndReturn(
            {
                'hostname': 'bar',
                'vcpus': 1,
                'memory_mb': 256
            })
        self.mox.StubOutWithMock(nova_glue.storage, 'get_image_architecture')
        nova_glue.storage.get_image_architecture(mox.IsA(object),
            mox.IsA(object)).AndReturn(
            'foo')
        self.mox.ReplayAll()

        self.backend.retrieve(res, self.sec_obj)

        # check if all attrs are there!
        self.assertIn('occi.compute.hostname', res.attributes)
        self.assertIn('occi.compute.architecture', res.attributes)
        self.assertIn('occi.compute.cores', res.attributes)
        self.assertIn('occi.compute.speed', res.attributes)
        self.assertIn('occi.compute.memory', res.attributes)
        self.assertIn('occi.compute.state', res.attributes)

        self.assertIn('occi.core.id', res.attributes)

        self.assertEqual('active', res.attributes['occi.compute.state'])

        self.assertListEqual([infrastructure.STOP, infrastructure.SUSPEND,
                              infrastructure.RESTART], res.actions)

        self.mox.VerifyAll()

    def test_update_for_sanity(self):
        """
        Simulate a update call!
        """
        res1 = core_model.Resource('/foo/bar', infrastructure.COMPUTE,
            [self.os_template])
        res1.attributes = {'occi.core.id': 'bar'}

        # case 1 - rebuild VM with different OS
        res2 = core_model.Resource('/foo/bar', infrastructure.COMPUTE,
            [self.os_template2])

        self.mox.StubOutWithMock(nova_glue.vm, 'rebuild_vm')
        nova_glue.vm.rebuild_vm(mox.IsA(object), mox.IsA(object),
            mox.IsA(object))
        self.mox.ReplayAll()
        self.backend.update(res1, res2, self.sec_obj)

        self.assertIn(self.os_template2, res1.mixins)

        self.mox.VerifyAll()

        # case 2 - resize the VM
        res2 = core_model.Resource('/foo/bar', infrastructure.COMPUTE,
            [self.res_template2])

        self.mox.StubOutWithMock(nova_glue.vm, 'resize_vm')
        nova_glue.vm.resize_vm(mox.IsA(object), mox.IsA(object),
            mox.IsA(object))
        self.mox.ReplayAll()
        self.backend.update(res1, res2, self.sec_obj)

        self.assertIn(self.res_template2, res1.mixins)

        self.mox.VerifyAll()

    def test_replace_for_sanity(self):
        """
        Simulate a replace call - does nothing atm.
        """
        self.backend.replace(None, None, self.sec_obj)

    def test_delete_for_sanity(self):
        """
        Simulate a delete call.
        """
        res = core_model.Resource('/foo/bar', infrastructure.COMPUTE,
            [self.os_template])
        res.attributes = {'occi.core.id': 'bar'}

        self.mox.StubOutWithMock(nova_glue.vm, 'delete_vm')
        nova_glue.vm.delete_vm(mox.IsA(object), mox.IsA(object))
        self.mox.ReplayAll()
        self.backend.delete(res, self.sec_obj)

        self.mox.VerifyAll()

    def test_action_for_sanity(self):
        """
        Test actions
        """
        res1 = core_model.Resource('/foo/bar', infrastructure.COMPUTE, [])
        res1.attributes = {'occi.core.id': 'bar'}

        # start
        self.mox.StubOutWithMock(nova_glue.vm, 'start_vm')
        nova_glue.vm.start_vm(mox.IsA(object), mox.IsA(object))
        self.mox.StubOutWithMock(nova_glue.vm, 'get_vm')
        nova_glue.vm.get_vm(mox.IsA(object), mox.IsA(object)).AndReturn(
            {
                'vm_state': vm_states.STOPPED
            })
        self.mox.ReplayAll()
        self.backend.action(res1, infrastructure.START, {}, self.sec_obj)
        self.mox.VerifyAll()

        # stop
        self.mox.UnsetStubs()
        self.mox.StubOutWithMock(nova_glue.vm, 'stop_vm')
        nova_glue.vm.stop_vm(mox.IsA(object), mox.IsA(object))
        self.mox.StubOutWithMock(nova_glue.vm, 'get_vm')
        nova_glue.vm.get_vm(mox.IsA(object), mox.IsA(object)).AndReturn(
            {
                'vm_state': vm_states.ACTIVE
            })
        self.mox.ReplayAll()
        self.backend.action(res1, infrastructure.STOP, {}, self.sec_obj)
        self.mox.VerifyAll()

        # reboot
        self.mox.UnsetStubs()
        self.mox.StubOutWithMock(nova_glue.vm, 'restart_vm')
        nova_glue.vm.restart_vm(mox.IsA(object), mox.IsA(str),
            mox.IsA(object))
        self.mox.StubOutWithMock(nova_glue.vm, 'get_vm')
        nova_glue.vm.get_vm(mox.IsA(object), mox.IsA(object)).AndReturn(
            {
                'vm_state': vm_states.ACTIVE
            })
        self.mox.ReplayAll()
        self.backend.action(res1, infrastructure.RESTART,
            {'method': 'graceful'},
            self.sec_obj)
        self.mox.VerifyAll()

        # suspend
        self.mox.UnsetStubs()
        self.mox.StubOutWithMock(nova_glue.vm, 'suspend_vm')
        nova_glue.vm.suspend_vm(mox.IsA(object), mox.IsA(object))
        self.mox.StubOutWithMock(nova_glue.vm, 'get_vm')
        nova_glue.vm.get_vm(mox.IsA(object), mox.IsA(object)).AndReturn(
            {
                'vm_state': vm_states.ACTIVE
            })
        self.mox.ReplayAll()
        self.backend.action(res1, infrastructure.SUSPEND, {}, self.sec_obj)
        self.mox.VerifyAll()
