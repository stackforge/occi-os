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
This module will connect the backends with nova code. This is the *ONLY*
place where nova API calls should be made!
"""

# TODO(tmetsch): consistency checks - make sure OCCI entities are passed in
# and out, an nothing else.
# TODO(tmetsch): unify exception handling

from nova import compute, exception
from nova import image
from nova import network
from nova.compute import vm_states, task_states, instance_types
from nova.flags import FLAGS

from api.compute import templates
from api.extensions import occi_future
from api.extensions import openstack

from occi.extensions import infrastructure

from webob import exc

# Connection to the nova APIs

compute_api = compute.API()
network_api = network.API()
image_api = image.get_default_image_service()

# COMPUTE


def create_vm(entity, context):
    """
    Create a VM for an given OCCI entity.
    """
    if 'occi.compute.hostname' in entity.attributes:
        name = entity.attributes['occi.compute.hostname']
    else:
        name = 'None'
    key_name = key_data = None
    password = compute.utils.generate_password(FLAGS.password_length)
    access_ip_v4 = None
    access_ip_v6 = None
    user_data = None
    metadata = {}
    injected_files = []
    min_count = max_count = 1
    requested_networks = None
    sg_names = []
    availability_zone = None
    config_drive = None
    block_device_mapping = None
    kernel_id = ramdisk_id = None
    auto_disk_config = None
    scheduler_hints = None

    rc = oc = 0
    for mixin in entity.mixins:
        if isinstance(mixin, templates.ResourceTemplate):
            resource_template = mixin
            rc += 1
        elif isinstance(mixin, templates.OsTemplate):
            os_template = mixin
            oc += 1
        elif mixin == openstack.OS_KEY_PAIR_EXT:
            attr = 'org.openstack.credentials.publickey.name'
            key_name = entity.attributes[attr]
            attr = 'org.openstack.credentials.publickey.data'
            key_data = entity.attributes[attr]
        elif mixin == openstack.OS_ADMIN_PWD_EXT:
            password = entity.attributes['org.openstack.credentials' \
                                         '.admin_pwd']
        elif mixin == openstack.OS_ACCESS_IP_EXT:
            attr = 'org.openstack.network.access.version'
            if entity.attributes[attr] == 'ipv4':
                access_ip_v4 = entity.attributes['org.openstack.network' \
                                                 '.access.ip']
            elif entity.attributes[attr] == 'ipv6':
                access_ip_v6 = entity.attributes['org.openstack.network' \
                                                 '.access.ip']
            else:
                raise exc.HTTPBadRequest()

        # Look for security group. If the group is non-existant, the
        # call to create will fail.
        if occi_future.SEC_GROUP in mixin.related:
            sg_names.append(mixin.term)

    flavor_name = resource_template.term
    image_id = os_template.os_id

    if flavor_name:
        inst_type = compute.instance_types.get_instance_type_by_name\
            (flavor_name)
    else:
        inst_type = compute.instance_types.get_default_instance_type()
        msg = ('No resource template was found in the request. '
                'Using the default: %s') % inst_type['name']
        LOG.warn(msg)

    # make the call
    try:
        (instances, _reservation_id) = compute_api.create(
            context=context,
            instance_type=inst_type,
            image_href=image_id,
            kernel_id=kernel_id,
            ramdisk_id=ramdisk_id,
            min_count=min_count,
            max_count=max_count,
            display_name=name,
            display_description=name,
            key_name=key_name,
            key_data=key_data,
            security_group=sg_names,
            availability_zone=availability_zone,
            user_data=user_data,
            metadata=metadata,
            injected_files=injected_files,
            admin_password=password,
            block_device_mapping=block_device_mapping,
            access_ip_v4=access_ip_v4,
            access_ip_v6=access_ip_v6,
            requested_networks=requested_networks,
            config_drive=config_drive,
            auto_disk_config=auto_disk_config,
            scheduler_hints=scheduler_hints)
    except Exception as error:
        raise exc.HTTPBadRequest(explanation=unicode(error))

    return instances[0]


def delete_vm(uid, context):
    """
    Destroy a VM.
    """
    try:
        instance = compute_api.get(context, uid)
    except exception.NotFound:
        raise exc.HTTPNotFound()

    if FLAGS.reclaim_instance_interval:
        compute_api.soft_delete(context, instance)
    else:
        compute_api.delete(context, instance)


def resize_vm(entity, mixin, context):
    """
    Resizes up or down a VM
    Update: libvirt now supports resize see:
    http://wiki.openstack.org/HypervisorSupportMatrix
    """
    instance = get_vm_instance(entity.attributes['occi.core.id'], context)
    flavor = instance_types.get_instance_type_by_name(mixin.term)
    kwargs = {}
    try:
        compute_api.resize(context, instance, flavor_id=flavor['flavorid'],
                           **kwargs)
    except exception.FlavorNotFound:
        msg = 'Unable to locate requested flavor.'
        raise exc.HTTPBadRequest(explanation=msg)
    except exception.CannotResizeToSameSize:
        msg = 'Resize requires a change in size.'
        raise exc.HTTPBadRequest(explanation=msg)
    except exception.InstanceInvalidState:
        exc.HTTPConflict()
    entity.attributes['occi.compute.state'] = 'inactive'
    # now update the mixin info
    # TODO(tmetsch): remove old mixin!!!
    entity.mixins.append(mixin)


def rebuild_vm(entity, mixin, context):
    """
    Rebuilds the specified VM with the supplied OsTemplate mixin.
    """
    # TODO(dizz): Use the admin_password extension?
    instance = get_vm_instance(entity.attributes['occi.core.id'], context)
    image_href = mixin.os_id
    admin_password = compute.utils.generate_password(FLAGS.password_length)
    kwargs = {}
    try:
        compute_api.rebuild(context, instance, image_href, admin_password,
                            **kwargs)
    except exception.InstanceInvalidState:
        exc.HTTPConflict()
    except exception.InstanceNotFound:
        msg = 'Instance could not be found"'
        raise exc.HTTPNotFound(explanation=msg)
    except exception.ImageNotFound:
        msg = 'Cannot find image for rebuild'
        raise exc.HTTPBadRequest(explanation=msg)
    entity.attributes['occi.compute.state'] = 'inactive'
    #now update the mixin info
    # TODO(tmetsch): remove old mixin!!!
    entity.mixins.append(mixin)


def start_vm(self, entity, context):
    """
    Starts a vm that is in the stopped state. Note, currently we do not
    use the nova start and stop, rather the resume/suspend methods. The
    start action also unpauses a paused VM.
    """
    instance = get_vm_instance(entity.attributes['occi.core.id'], context)

    try:
        if entity.attributes['occi.compute.state'] == 'suspended':
            compute_api.unpause(context, instance)
        else:
            compute_api.resume(context, instance)
    except Exception:
        raise exc.HTTPServerError('Error in starting VM')
    entity.attributes['occi.compute.state'] = 'active'
    entity.actions = [infrastructure.STOP,
                      infrastructure.SUSPEND,
                      infrastructure.RESTART,
                      openstack.OS_REVERT_RESIZE,
                      openstack.OS_CONFIRM_RESIZE,
                      openstack.OS_CREATE_IMAGE]


def stop_vm(entity, attributes, context):
    """
    Stops a VM. Rather than use stop, suspend is used.
    OCCI -> graceful, acpioff, poweroff
    OS -> unclear
    """
    instance = get_vm_instance(entity.attributes['occi.core.id'], context)

    if 'method' in attributes:
        msg = 'OS only allows one type of stop. What is specified in the ' \
              'request will be ignored.'
        # TODO(tmetsch): log...
    try:
        # TODO(dizz): There are issues with the stop and start methods of
        #             OS. For now we'll use suspend.
        # self.compute_api.stop(context, instance)
        compute_api.suspend(context, instance)
    except Exception:
        msg = 'Error in stopping VM'
        raise exc.HTTPServerError(msg)
    entity.attributes['occi.compute.state'] = 'inactive'
    entity.actions = [infrastructure.START]


def restart_vm(entity, attributes, context):
    """
    Restarts a VM.
      OS types == SOFT, HARD
      OCCI -> graceful, warm and cold
      mapping:
      - SOFT -> graceful, warm
      - HARD -> cold
    """
    instance = get_vm_instance(entity.attributes['occi.core.id'], context)

    if not 'method' in attributes:
        raise exc.HTTPBadRequest('Please provide a method!')
    if attributes['method'] in ('graceful', 'warm'):
        reboot_type = 'SOFT'
    elif attributes['method'] is 'cold':
        reboot_type = 'HARD'
    else:
        raise exc.HTTPBadRequest('Unknown method.')
    try:
        compute_api.reboot(context, instance, reboot_type)
    except exception.InstanceInvalidState:
        exc.HTTPConflict()
    except Exception as e:
        msg = ("Error in reboot %s") % e
        raise exc.HTTPUnprocessableEntity(msg)
    entity.attributes['occi.compute.state'] = 'inactive'
    entity.actions = []


def suspend_vm(self, entity, attributes, context):
    """
    Suspends a VM. Use the start action to unsuspend a VM.
    """
    instance = get_vm_instance(entity.attributes['occi.core.id'], context)

    if 'method' in attributes:
        msg = _('OS only allows one type of suspend. '
                'What is specified in the request will be ignored.')
        # TODO(tmetsch): log...
    try:
        compute_api.pause(context, instance)
    except Exception:
        msg = 'Error in stopping VM.'
        raise exc.HTTPServerError(msg)
    entity.attributes['occi.compute.state'] = 'suspended'
    entity.actions = [infrastructure.START]


def get_vm_instance(uid, context):
    """
    Retrieve an VM instance from nova.
    """
    try:
        instance = compute_api.get(context, uid)
    except exception.NotFound:
        raise exc.HTTPNotFound()
    return instance


def set_vm_occistate(entity, context):
    """
    See nova/compute/vm_states.py nova/compute/task_states.py

    Mapping assumptions:
    - active == VM can service requests from network. These requests
            can be from users or VMs
    - inactive == the oppose! :-)
    - suspended == machine in a frozen state e.g. via suspend or pause
    """
    uid = entity.attributes['occi.core.id']
    instance = get_vm_instance(uid, context)

    if instance['vm_state'] in (vm_states.ACTIVE,
                                task_states.UPDATING_PASSWORD,
                                task_states.RESIZE_CONFIRMING):
        entity.attributes['occi.compute.state'] = 'active'
        entity.actions = [infrastructure.STOP,
                          infrastructure.SUSPEND,
                          infrastructure.RESTART,
                          openstack.OS_CONFIRM_RESIZE,
                          openstack.OS_REVERT_RESIZE,
                          openstack.OS_CHG_PWD,
                          openstack.OS_CREATE_IMAGE]

        # reboot server - OS, OCCI
        # start server - OCCI
    elif instance['vm_state'] in (task_states.STARTING,
                                  task_states.POWERING_ON,
                                  task_states.REBOOTING,
                                  task_states.REBOOTING_HARD):
        entity.attributes['occi.compute.state'] = 'inactive'
        entity.actions = []

        # pause server - OCCI, suspend server - OCCI, stop server - OCCI
    elif instance['vm_state'] in (task_states.STOPPING,
                                  task_states.POWERING_OFF):
        entity.attributes['occi.compute.state'] = 'inactive'
        entity.actions = [infrastructure.START]

        # resume server - OCCI
    elif instance['vm_state'] in (task_states.RESUMING,
                                  task_states.PAUSING,
                                  task_states.SUSPENDING):
        entity.attributes['occi.compute.state'] = 'suspended'
        if instance['vm_state'] in (vm_states.PAUSED,
                                    vm_states.SUSPENDED):
            entity.actions = [infrastructure.START]
        else:
            entity.actions = []

        # rebuild server - OS
        # resize server confirm rebuild
        # revert resized server - OS (indirectly OCCI)
    elif instance['vm_state'] in (
        vm_states.RESIZED,
        vm_states.BUILDING,
        task_states.RESIZE_CONFIRMING,
        task_states.RESIZE_FINISH,
        task_states.RESIZE_MIGRATED,
        task_states.RESIZE_MIGRATING,
        task_states.RESIZE_PREP,
        task_states.RESIZE_REVERTING):
        entity.attributes['occi.compute.state'] = 'inactive'
        entity.actions = []

# NETWORK


def get_adapter_info(instance, context):
    """
    Extracts the VMs network adapter information: interface name,
    IP address, gateway and mac address.
    """
    # TODO(dizz): currently this assumes one adapter on the VM.
    # It's likely that this will not be the case when using Quantum

    vm_net_info = {'vm_iface': '', 'address': '', 'gateway': '', 'mac': '',
                   'allocation': ''}

    sj = network_api.get_instance_nw_info(context, instance)
    # catches an odd error whereby no network info is returned back
    if len(sj) <= 0:
        msg = 'No network info was returned either live or cached.'
        LOG.warn(msg)
        return vm_net_info

    vm_net_info['vm_iface'] = sj[0]['network']['meta']['bridge_interface']

    # OS-specific if a VM is stopped it has no IP address
    if len(sj[0]['network']['subnets'][0]['ips']) > 0:
        vm_net_info['address'] = sj[0]['network']['subnets'][0]['ips'][0]['address']
    else:
        vm_net_info['address'] = ''
    vm_net_info['gateway'] = sj[0]['network']['subnets'][0]['gateway']['address']
    vm_net_info['mac'] = sj[0]['address']
    if sj[0]['network']['subnets'][0]['ips'][0]['type'] == 'fixed':
        vm_net_info['allocation'] = 'static'
    else:
        vm_net_info['allocation'] = 'dynamic'
    return vm_net_info

# STORAGE


def get_image_architecture(instance, context):
    """
    Extract architecture from either:
    - image name, title or metadata. The architecture is sometimes
      encoded in the image's name
    - db::glance::image_properties could be used reliably so long as the
      information is supplied when registering an image with glance.
    - else return a default of x86
    """
    arch = ''
    print 'BOOJA - might be prob here:', dir(instance)
    id = instance['image_href']
    img = image_api.show(context, id)
    img_properties = img['properties']
    if 'arch' in img_properties:
        arch = img['properties']['arch']
    elif 'architecture' in img_properties:
        arch = img['properties']['architecture']

    if arch == '':
        # if all attempts fail set it to a default value
        arch = 'x86'
    return arch