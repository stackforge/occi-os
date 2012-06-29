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

import logging

from nova import network, exception
from nova.compute import utils as compute_utils

from nova_glue import vm

# Connect to nova :-)

network_api = network.API()

LOG = logging.getLogger()


def get_adapter_info(uid, context):
    """
    Extracts the VMs network adapter information: interface name,
    IP address, gateway and mac address.

    uid -- Id of the VM.
    context -- The os context.
    """
    vm_instance = vm._get_vm(uid, context)

    # TODO(dizz): currently this assumes one adapter on the VM.
    # It's likely that this will not be the case when using Quantum

    vm_net_info = {'vm_iface': '', 'address': '', 'gateway': '', 'mac': '',
                   'allocation': ''}

    sj = network_api.get_instance_nw_info(context, vm_instance)

    # catches an odd error whereby no network info is returned back
    if len(sj) <= 0:
        LOG.warn('No network info was returned either live or cached.')
        return vm_net_info

    vm_net_info['vm_iface'] = sj[0]['network']['meta']['bridge_interface']

    # OS-specific if a VM is stopped it has no IP address
    if len(sj[0]['network']['subnets'][0]['ips']) > 0:
        adr = sj[0]['network']['subnets'][0]['ips'][0]['address']
        vm_net_info['address'] = adr
    else:
        vm_net_info['address'] = ''
    gw = sj[0]['network']['subnets'][0]['gateway']['address']
    vm_net_info['gateway'] = gw
    vm_net_info['mac'] = sj[0]['address']
    if sj[0]['network']['subnets'][0]['ips'][0]['type'] == 'fixed':
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
    vm_instance = vm._get_vm(uid, context)

    cached_nwinfo = compute_utils.get_nw_info_for_instance(vm_instance)
    if not cached_nwinfo:
        raise AttributeError('No nw_info cache associated with instance')

    fixed_ips = cached_nwinfo.fixed_ips()
    if not fixed_ips:
        raise AttributeError('No fixed ips associated to instance')

    if 'org.openstack.network.floating.pool' not in attributes:
        pool = None
    else:
        pool = attributes['org.openstack.network.floating.pool']

    address = network_api.allocate_floating_ip(context, pool)

    if len(fixed_ips) > 1:
        LOG.warn('multiple fixed_ips exist, using the first')

    try:
        address = fixed_ips[0]['address']
        network_api.associate_floating_ip(context, vm_instance,
                                          floating_address=address,
                                          fixed_address=address)
    except exception.FloatingIpAssociated:
        msg = 'floating ip is already associated'
        raise AttributeError(msg)
    except exception.NoFloatingIpInterface:
        msg = 'l3driver call to add floating ip failed'
        raise AttributeError(msg)
    except Exception:
        msg = 'Error. Unable to associate floating ip'
        raise AttributeError(msg)
    return address


def remove_floating_ip(uid, address, context):
    """
    Remove a given address from an VM instance.

    uid -- Id of the VM.
    address -- The ip address.
    context -- The os context.
    """
    # TODO: check exception handling!
    vm_instance = vm._get_vm(uid, context)

    network_api.disassociate_floating_ip(context, vm_instance, address)
    network_api.release_floating_ip(context, address)
