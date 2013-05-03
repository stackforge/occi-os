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
Network resource backend.
"""

#W0613:unused arguments,R0201:mth could be func,R0903:too few pub mthd.
#W0232:no init
#pylint: disable=W0613,R0201,R0903,W0232


from occi import backend
from occi_os_api.extensions import os_addon
from occi_os_api.nova_glue import net


class NetworkBackend(backend.KindBackend, backend.ActionBackend):
    """
    Backend to handle network resources.
    """

    def create(self, entity, extras):
        """
        Currently unsupported.
        """
        raise AttributeError('Currently not supported.')

    def action(self, entity, action, attributes, extras):
        """
        Currently unsupported.
        """
        raise AttributeError('Currently not supported.')


class IpNetworkBackend(backend.MixinBackend):
    """
    A mixin backend for the IPnetworking.
    """

    def create(self, entity, extras):
        """
        Currently unsupported.
        """
        raise AttributeError('Currently not supported.')


class IpNetworkInterfaceBackend(backend.MixinBackend):
    """
    A mixin backend for the IpNetworkingInterface (covered by
    NetworkInterfaceBackend).
    """

    pass


class NetworkInterfaceBackend(backend.KindBackend):
    """
    A backend for network links.
    """

    def create(self, link, extras):
        """
        As nova does not support creation of L2 networks we don't.
        """
        if link.target.identifier == '/network/public':
            # public means floating IP in OS!
            # if the os_net_link mixin is avail. a pool must be provided:
            if not 'org.openstack.network.floating.pool' in link.attributes\
                    and os_addon.OS_NET_LINK in link.mixins:
                raise AttributeError('Please specify the pool name when using'
                                     ' this mixin!')
            elif os_addon.OS_NET_LINK in link.mixins:
                pool = link.attributes['org.openstack.network.floating.pool']
            else:
                pool = None
            address = net.add_floating_ip(link.source.attributes['occi.'
                                                                 'core.id'],
                                          pool,
                                          extras['nova_ctx'])
            link.attributes['occi.networkinterface.interface'] = 'eth0'
            link.attributes['occi.networkinterface.mac'] = 'aa:bb:cc:dd:ee:ff'
            link.attributes['occi.networkinterface.state'] = 'active'
            link.attributes['occi.networkinterface.address'] = address
            link.attributes['occi.networkinterface.gateway'] = '0.0.0.0'
            link.attributes['occi.networkinterface.allocation'] = 'static'
        else:
            raise AttributeError('Currently not supported.')

    def update(self, old, new, extras):
        """
        Allows for the update of network links.
        """
        raise AttributeError('Currently not supported.')

    def delete(self, link, extras):
        """
        Remove a floating ip!
        """
        if link.target.identifier == '/network/public':
            # public means floating IP in OS!
            net.remove_floating_ip(link.source.attributes['occi.core.id'],
                                   link.attributes['occi.networkinterface.'
                                                   'address'],
                                   extras['nova_ctx'])
