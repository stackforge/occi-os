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

#pylint: disable=W0102,C0103,R0904

import mox
import unittest
from occi import core_model

from occi_os_api import nova_glue
from occi_os_api.backends import network
from occi_os_api.extensions import os_addon


class TestNetworkInterfaceBackend(unittest.TestCase):
    """
    Tests the network interface backend!
    """

    def setUp(self):
        """
        Setup the tests.
        """
        self.backend = network.NetworkInterfaceBackend()
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
        Test create for failure!
        """
        source = mox.MockObject(core_model.Resource)
        source.attributes = {'occi.core.id': 'bar'}
        target = mox.MockObject(core_model.Resource)
        target.identifier = '/network/admin'

        link = core_model.Link('foo', None, [], source, target)

        self.mox.ReplayAll()

        self.assertRaises(AttributeError, self.backend.create, link,
                          self.sec_obj)

        self.mox.VerifyAll()

        # should have pool name in attribute...
        target.identifier = '/network/public'
        link = core_model.Link('foo', None, [os_addon.OS_NET_LINK], source,
                               target)

        self.mox.ReplayAll()
        self.assertRaises(AttributeError, self.backend.create, link,
                          self.sec_obj)

        self.mox.VerifyAll()

    def test_update_for_failure(self):
        """
        No updates allowed!
        """
        self.assertRaises(AttributeError, self.backend.update, None, None,
                          None)

    # Test for sanity!

    def test_create_for_sanity(self):
        """
        Test create for sanity!
        """
        source = mox.MockObject(core_model.Resource)
        source.attributes = {'occi.core.id': 'bar'}
        target = mox.MockObject(core_model.Resource)
        target.identifier = '/network/public'

        link = core_model.Link('foo', None, [os_addon.OS_NET_LINK], source,
                               target)
        link.attributes = {'org.openstack.network.floating.pool': 'nova'}

        self.mox.StubOutWithMock(nova_glue.net, 'add_floating_ip')
        nova_glue.net.add_floating_ip(mox.IsA(str), mox.IsA(str),
                                      mox.IsA(object)).AndReturn('10.0.0.1')

        self.mox.ReplayAll()
        self.backend.create(link, self.sec_obj)

        # verify all attrs and mixins!
        self.assertIn('occi.networkinterface.interface', link.attributes)
        self.assertIn('occi.networkinterface.mac', link.attributes)
        self.assertIn('occi.networkinterface.state', link.attributes)
        self.assertIn('occi.networkinterface.address', link.attributes)
        self.assertIn('occi.networkinterface.gateway', link.attributes)
        self.assertIn('occi.networkinterface.allocation', link.attributes)

        # self.assertIn(infrastructure.IPNETWORKINTERFACE, link.mixins)
        # self.assertIn(infrastructure.NETWORKINTERFACE, link.mixins)

        # test without pool name...
        self.mox.UnsetStubs()
        link = core_model.Link('foo', None, [], source, target)

        self.mox.StubOutWithMock(nova_glue.net, 'add_floating_ip')

        nova_glue.net.add_floating_ip(mox.IsA(str), mox.IsA(None),
                                      mox.IsA(object)).AndReturn('10.0.0.2')

        self.mox.ReplayAll()
        self.backend.create(link, self.sec_obj)
        self.mox.VerifyAll()

    def test_delete_for_sanity(self):
        """
        Test create for sanity!
        """
        source = mox.MockObject(core_model.Resource)
        source.attributes = {'occi.core.id': 'bar'}
        target = mox.MockObject(core_model.Resource)
        target.identifier = '/network/public'

        link = core_model.Link('foo', None, [], source, target)
        link.attributes = {'occi.networkinterface.address': '10.0.0.1'}

        self.mox.StubOutWithMock(nova_glue.net, 'remove_floating_ip')
        nova_glue.net.remove_floating_ip(mox.IsA(object), mox.IsA(object),
                                         mox.IsA(object))

        self.mox.ReplayAll()

        self.backend.delete(link, self.sec_obj)

        self.mox.VerifyAll()


class TestNetworkBackend(unittest.TestCase):
    """
    Some tests for network resources.
    """

    def setUp(self):
        """
        Initialize test.
        """
        self.backend = network.NetworkBackend()

    def test_create_for_failure(self):
        """
        Expecting an error!
        """
        self.assertRaises(AttributeError, self.backend.create, None, None)

    def test_action_for_failure(self):
        """
        Expecting an error!
        """
        self.assertRaises(AttributeError, self.backend.action, None,
                          None, None, None)


class TestIpNetworkBackend(unittest.TestCase):
    """
    Some tests for network resources.
    """

    def setUp(self):
        """
        Initialize test.
        """
        self.backend = network.IpNetworkBackend()

    def test_create_for_failure(self):
        """
        Expecting an error!
        """
        self.assertRaises(AttributeError, self.backend.create, None, None)
