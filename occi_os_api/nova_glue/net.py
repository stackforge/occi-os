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
Network related 'glue' :-)
"""

import logging

from nova import network
from nova import exception
from nova import compute
from nova.compute import utils

from occi_os_api.nova_glue import vm

# Connect to nova :-)

NETWORK_API = network.API()
COMPUTE_API = compute.API()

LOG = logging.getLogger('nova.occiosapi.wsgi.occi.nova_glue.net')


def get_adapter_info(uid, context):
    """
    Extracts the VMs network adapter information.

    uid -- Id of the VM.
    context -- The os context.
    """
    vm_instance = vm.get_vm(uid, context)

    result = {'public':[], 'admin':[]}
    try:
        net_info = NETWORK_API.get_instance_nw_info(context, vm_instance)[0]
    except IndexError:
        LOG.warn('Unable to retrieve network information - this is because '
                 'of OpenStack!!')
        return result
    gw = net_info['network']['subnets'][0]['gateway']['address']
    mac = net_info['address']

    tmp = net_info['network']['subnets'][0]['ips'][0]
    for item in tmp['floating_ips']:
        result['public'].append({'interface':'eth0',
                                 'mac':'aa:bb:cc:dd:ee:ff',
                                 'state': 'active',
                                 'address': item['address'],
                                 'gateway': '0.0.0.0',
                                 'allocation': 'static'})
    result['admin'].append({'interface':'eth0',
                            'mac': mac,
                            'state': 'active',
                            'address': tmp['address'],
                            'gateway': gw,
                            'allocation': 'static'})

    return result


def add_floating_ip_to_vm(uid, context):
    """
    Adds an ip to an VM instance.

    uid -- id of the VM.
    attributes -- the call attributes (dict)
    context -- The os context.
    """
    vm_instance = vm.get_vm(uid, context)

    cached_nwinfo = utils.get_nw_info_for_instance(vm_instance)
    if not cached_nwinfo:
        raise AttributeError('No nw_info cache associated with instance')

    fixed_ips = cached_nwinfo.fixed_ips()
    if not fixed_ips:
        raise AttributeError('No fixed ips associated to instance')

    float_address = NETWORK_API.allocate_floating_ip(context, None)

    try:
        address = fixed_ips[0]['address']
        NETWORK_API.associate_floating_ip(context, vm_instance,
                                          float_address, address)
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


def remove_floating_ip(uid, address, context):
    """
    Remove a given address from an VM instance.

    uid -- Id of the VM.
    address -- The ip address.
    context -- The os context.
    """
    vm_instance = vm.get_vm(uid, context)

    # TODO: check exception handling!

    NETWORK_API.disassociate_floating_ip(context, vm_instance, address)
    NETWORK_API.release_floating_ip(context, address)
