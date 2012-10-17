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

from occi import core_model
from occi.extensions import infrastructure
from occi_os_api import nova_glue

from occi_os_api.backends import compute
from occi_os_api.extensions import os_mixins

class TestComputeBackend(unittest.TestCase):
    """
    Tests the compute backend.
    """

    os_template = os_mixins.OsTemplate('', '')

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

    def test_create_for_failure(self):
        """
        Test for proper error handling
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

        # TODO check if all attrs are there!
        self.assertEqual(True, True)

        self.mox.VerifyAll()




