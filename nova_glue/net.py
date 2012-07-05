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
Network related 'glue' :-)
"""

import logging

from nova import network
from nova import exception
from nova import compute

from nova_glue import vm

# Connect to nova :-)

NETWORK_API = network.API()
COMPUTE_API = compute.API()

LOG = logging.getLogger('nova.api.wsgi.occi.nova_glue.net')


def get_adapter_info(uid, context):
    """
    Extracts the VMs network adapter information: interface name,
    IP address, gateway and mac address.

    uid -- Id of the VM.
    context -- The os context.
    """
    vm_instance = vm.get_vm(uid, context)

    # TODO(dizz): currently this assumes one adapter on the VM.
    # It's likely that this will not be the case when using Quantum

    vm_net_info = {'vm_iface': '', 'address': '', 'gateway': '', 'mac': '',
                   'allocation': ''}

    temp = NETWORK_API.get_instance_nw_info(context, vm_instance)

    # catches an odd error whereby no network info is returned back
    if len(temp) <= 0:
        LOG.warn('No network info was returned either live or cached.')
        return vm_net_info

    vm_net_info['vm_iface'] = temp[0]['network']['meta']['bridge_interface']

    # OS-specific if a VM is stopped it has no IP address
    if len(temp[0]['network']['subnets'][0]['ips']) > 0:
        adr = temp[0]['network']['subnets'][0]['ips'][0]['address']
        vm_net_info['address'] = adr
    else:
        vm_net_info['address'] = ''
    gateway = temp[0]['network']['subnets'][0]['gateway']['address']
    vm_net_info['gateway'] = gateway
    vm_net_info['mac'] = temp[0]['address']
    if temp[0]['network']['subnets'][0]['ips'][0]['type'] == 'fixed':
        vm_net_info['allocation'] = 'static'
    else:
        vm_net_info['allocation'] = 'dynamic'
    return vm_net_info


def add_flaoting_ip_to_vm(uid, attributes, context):
    """
    Adds an ip to an VM instance.

    uid -- id of the VM.
    attributes -- the call attributes (dict)
    context -- The os context.
    """
    vm_instance = vm.get_vm(uid, context)

    #cached_nwinfo = compute_utils.get_nw_info_for_instance(vm_instance)
    #if not cached_nwinfo:
    #    raise AttributeError('No nw_info cache associated with instance')

    #fixed_ips = cached_nwinfo.fixed_ips()
    #if not fixed_ips:
    #    raise AttributeError('No fixed ips associated to instance')

    if 'org.openstack.network.floating.pool' not in attributes:
        pool = None
    else:
        pool = attributes['org.openstack.network.floating.pool']

    float_address = NETWORK_API.allocate_floating_ip(context, pool)

    #if len(fixed_ips) > 1:
    #    LOG.warn('multiple fixed_ips exist, using the first')

    try:
        # address = fixed_ips[0]['address']
        COMPUTE_API.associate_floating_ip(context, vm_instance,
                                          float_address)
    except exception.FloatingIpAssociated:
        msg = 'floating ip is already associated'
        raise AttributeError(msg)
    except exception.NoFloatingIpInterface:
        msg = 'l3driver call to add floating ip failed'
        raise AttributeError(msg)
    except Exception as error:
        msg = 'Error. Unable to associate floating ip: ' + str(error)
        raise AttributeError(msg)
    return float_address


def remove_floating_ip(address, context):
    """
    Remove a given address from an VM instance.

    uid -- Id of the VM.
    address -- The ip address.
    context -- The os context.
    """
    # TODO: check exception handling!

    NETWORK_API.disassociate_floating_ip(context, address)
    NETWORK_API.release_floating_ip(context, address)
