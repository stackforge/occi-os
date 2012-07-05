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
VM related 'glue' :-)
"""

#pylint: disable=R0914,W0142,R0912,R0915

from api.compute import templates
from api.extensions import occi_future
from api.extensions import openstack

from nova import compute, volume
from nova import exception
from nova import utils
from nova.compute import vm_states
from nova.compute import task_states
from nova.compute import instance_types
from nova.flags import FLAGS

from occi import exceptions
from occi.extensions import infrastructure

import logging

# Connection to the nova APIs

COMPUTE_API = compute.API()
VOLUME_API = volume.API()

LOG = logging.getLogger('nova.api.wsgi.occi.nova_glue.vm')


def create_vm(entity, context):
    """
    Create a VM for an given OCCI entity.

    entity -- the OCCI resource entity.
    context -- the os context.
    """
    if 'occi.compute.hostname' in entity.attributes:
        name = entity.attributes['occi.compute.hostname']
    else:
        name = 'None'
    key_name = key_data = None
    password = utils.generate_password(FLAGS.password_length)
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

    resource_template = None
    os_template = None
    for mixin in entity.mixins:
        if isinstance(mixin, templates.ResourceTemplate):
            resource_template = mixin
        elif isinstance(mixin, templates.OsTemplate):
            os_template = mixin
        elif mixin == openstack.OS_KEY_PAIR_EXT:
            attr = 'org.openstack.credentials.publickey.name'
            key_name = entity.attributes[attr]
            attr = 'org.openstack.credentials.publickey.data'
            key_data = entity.attributes[attr]
        elif mixin == openstack.OS_ADMIN_PWD_EXT:
            password = entity.attributes['org.openstack.credentials'\
                                         '.admin_pwd']
        elif mixin == openstack.OS_ACCESS_IP_EXT:
            attr = 'org.openstack.network.access.version'
            if entity.attributes[attr] == 'ipv4':
                access_ip_v4 = entity.attributes['org.openstack.network'\
                                                 '.access.ip']
            elif entity.attributes[attr] == 'ipv6':
                access_ip_v6 = entity.attributes['org.openstack.network'\
                                                 '.access.ip']
            else:
                raise AttributeError('No ip given within the attributes!')

        # Look for security group. If the group is non-existant, the
        # call to create will fail.
        if occi_future.SEC_GROUP in mixin.related:
            sg_names.append(mixin.term)

    if not os_template:
        raise AttributeError('Please provide a valid OS Template.')

    if resource_template:
        inst_type = compute.instance_types.get_instance_type_by_name\
            (resource_template.term)
    else:
        inst_type = compute.instance_types.get_default_instance_type()
        msg = ('No resource template was found in the request. '
               'Using the default: %s') % inst_type['name']
        LOG.warn(msg)
    # make the call
    try:
        (instances, _reservation_id) = COMPUTE_API.create(
            context=context,
            instance_type=inst_type,
            image_href=os_template.os_id,
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
        raise AttributeError(str(error))

    # return first instance
    return instances[0]


def rebuild_vm(uid, image_href, context):
    """
    Rebuilds the specified VM with the supplied OsTemplate mixin.

    uid -- id of the instance
    image_href -- image reference.
    context -- the os context
    """
    instance = get_vm(uid, context)

    admin_password = utils.generate_password(FLAGS.password_length)
    kwargs = {}
    try:
        COMPUTE_API.rebuild(context, instance, image_href, admin_password,
                            **kwargs)
    except exception.InstanceInvalidState:
        raise AttributeError('VM is in an invalid state.')
    except exception.ImageNotFound:
        raise AttributeError('Cannot find image for rebuild')


def resize_vm(uid, flavor_name, context):
    """
    Resizes a VM up or down

    Update: libvirt now supports resize see:
    http://wiki.openstack.org/HypervisorSupportMatrix

    uid -- id of the instance
    flavor_name -- image reference.
    context -- the os context
    """
    instance = get_vm(uid, context)
    kwargs = {}
    try:
        flavor = instance_types.get_instance_type_by_name(flavor_name)
        COMPUTE_API.resize(context, instance, flavor_id=flavor['flavorid'],
                           **kwargs)
    except exception.FlavorNotFound:
        raise AttributeError('Unable to locate requested flavor.')
    except exception.CannotResizeToSameSize:
        raise AttributeError('Resize requires a change in size.')
    except exception.InstanceInvalidState as error:
        raise error
        #raise AttributeError('VM is in an invalid state.')


def delete_vm(uid, context):
    """
    Destroy a VM.

    uid -- id of the instance
    context -- the os context
    """
    instance = get_vm(uid, context)

    if FLAGS.reclaim_instance_interval:
        COMPUTE_API.soft_delete(context, instance)
    else:
        COMPUTE_API.delete(context, instance)


def suspend_vm(uid, context):
    """
    Suspends a VM. Use the start action to unsuspend a VM.

    uid -- id of the instance
    context -- the os context
    """
    instance = get_vm(uid, context)

    try:
        COMPUTE_API.pause(context, instance)
    except Exception as error:
        raise exceptions.HTTPError(500, str(error))


def snapshot_vm(uid, image_name, context):
    """
    Snapshots a VM. Use the start action to unsuspend a VM.

    uid -- id of the instance
    image_name -- name of the new image
    context -- the os context
    """
    instance = get_vm(uid, context)
    try:
        COMPUTE_API.snapshot(context,
                             instance,
                             image_name)

    except exception.InstanceInvalidState:
        raise AttributeError('VM is not in an valid state.')


def start_vm(uid, context):
    """
    Starts a vm that is in the stopped state. Note, currently we do not
    use the nova start and stop, rather the resume/suspend methods. The
    start action also unpauses a paused VM.

    uid -- id of the instance
    state -- the state the VM is in (str)
    context -- the os context
    """
    instance = get_vm(uid, context)
    try:
        COMPUTE_API.resume(context, instance)
    except Exception as error:
        raise exceptions.HTTPError(500, 'Error while starting VM: ' + str
            (error))


def stop_vm(uid, context):
    """
    Stops a VM. Rather than use stop, suspend is used.
    OCCI -> graceful, acpioff, poweroff
    OS -> unclear

    uid -- id of the instance
    context -- the os context
    """
    instance = get_vm(uid, context)

    try:
        # TODO(dizz): There are issues with the stop and start methods of
        #             OS. For now we'll use suspend.
        # self.compute_api.stop(context, instance)
        COMPUTE_API.suspend(context, instance)
    except Exception as error:
        raise exceptions.HTTPError(500, 'Error while stopping VM: ' + str
            (error))


def restart_vm(uid, method, context):
    """
    Restarts a VM.
      OS types == SOFT, HARD
      OCCI -> graceful, warm and cold
      mapping:
      - SOFT -> graceful, warm
      - HARD -> cold

    uid -- id of the instance
    method -- how the machine should be restarted.
    context -- the os context
    """
    instance = get_vm(uid, context)

    if method in ('graceful', 'warm'):
        reboot_type = 'SOFT'
    elif method is 'cold':
        reboot_type = 'HARD'
    else:
        raise AttributeError('Unknown method.')
    try:
        COMPUTE_API.reboot(context, instance, reboot_type)
    except exception.InstanceInvalidState:
        raise exceptions.HTTPError(406, 'VM is in an invalid state.')
    except Exception as error:
        msg = ("Error in reboot %s") % error
        raise exceptions.HTTPError(500, msg)


def attach_volume(instance_id, volume_id, mount_point, context):
    """
    Attaches a storage volume.

    instance_id -- Id of the VM.
    volume_id -- Id of the storage volume.
    mount_point -- Where to mount.
    context -- The os security context.
    """
    # TODO: check exception handling!
    instance = get_vm(instance_id, context)
    try:
        vol_instance = VOLUME_API.get(context, volume_id)
    except exception.NotFound:
        raise exceptions.HTTPError(404, 'Volume not found!')
    volume_id = vol_instance['id']

    try:
        COMPUTE_API.attach_volume(
            context,
            instance,
            volume_id,
            mount_point)
    except Exception as error:
        LOG.error(str(error))
        raise error


def detach_volume(volume_id, context):
    """
    Detach a storage volume.

    volume_id -- Id of the volume.
    context -- the os context.
    """
    #try:
    #    instance = VOLUME_API.get(context, volume_id)
    #except exception.NotFound:
    #    raise exceptions.HTTPError(404, 'Volume not found!')
    #volume_id = instance['id']

    try:
        #TODO(dizz): see issue #15
        COMPUTE_API.detach_volume(context, volume_id)
    except Exception as error:
        LOG.error(str(error) + '; with id: ' + volume_id)
        raise error


def set_password_for_vm(uid, password, context):
    """
    Set new password for an VM.

    uid -- Id of the instance.
    password -- The new password.
    context -- The os context.
    """
    # TODO: check exception handling!
    instance = get_vm(uid, context)

    COMPUTE_API.set_admin_password(context, instance, password)


def get_vnc(uid, context):
    """
    Retrieve VNC console.

    uid -- id of the instance
    context -- the os context
    """
    instance = get_vm(uid, context)
    try:
        console = COMPUTE_API.get_vnc_console(context, instance, 'novnc')
    except Exception as error:
        LOG.warn('Console info is not available yet!')
        return None
    return console


def revert_resize_vm(uid, context):
    """
    Revert a resize.

    uid -- id of the instance
    context -- the os context
    """
    instance = get_vm(uid, context)
    try:
        COMPUTE_API.revert_resize(context, instance)
    except exception.MigrationNotFound:
        raise AttributeError('Instance has not been resized.')
    except exception.InstanceInvalidState:
        raise exceptions.HTTPError(406, 'VM is an invalid state.')
    except Exception:
        raise AttributeError('Error in revert-resize.')


def confirm_resize_vm(uid, context):
    """
    Confirm a resize.

    uid -- id of the instance
    context -- the os context
    """
    instance = get_vm(uid, context)
    try:
        COMPUTE_API.confirm_resize(context, instance)
    except exception.MigrationNotFound:
        raise AttributeError('Instance has not been resized.')
    except exception.InstanceInvalidState as error:
        raise exceptions.HTTPError(406, 'VM is an invalid state: ' +
                                        str(error))
    except Exception:
        raise AttributeError('Error in confirm-resize.')


def get_vm(uid, context):
    """
    Retrieve an VM instance from nova.

    uid -- id of the instance
    context -- the os context
    """
    try:
        instance = COMPUTE_API.get(context, uid)
    except exception.NotFound:
        raise exceptions.HTTPError(404, 'VM not found!')
    return instance


def get_occi_state(uid, context):
    """
    See nova/compute/vm_states.py nova/compute/task_states.py

    Mapping assumptions:
    - active == VM can service requests from network. These requests
            can be from users or VMs
    - inactive == the oppose! :-)
    - suspended == machine in a frozen state e.g. via suspend or pause

    uid -- Id of the VM.
    context -- the os context.
    """
    instance = get_vm(uid, context)
    state = 'inactive'
    actions = []

    if instance['vm_state'] in [vm_states.ACTIVE,
                                vm_states.RESIZING]:
        state = 'active'
        actions.append(infrastructure.STOP)
        actions.append(infrastructure.SUSPEND)
        actions.append(infrastructure.RESTART)
    elif instance['vm_state'] in [vm_states.BUILDING]:
        state = 'inactive'
    elif instance['vm_state'] in [vm_states.PAUSED, vm_states.SUSPENDED,
                                  vm_states.STOPPED]:
        state = 'inactive'
        actions.append(infrastructure.START)
    elif instance['vm_state'] in [vm_states.RESCUED,
                                  vm_states.ERROR, vm_states.SOFT_DELETE,
                                  vm_states.DELETED]:
        state = 'inactive'

    # Some task states require a state
    # TODO: check for others!
    if instance['vm_state'] in [task_states.IMAGE_SNAPSHOT]:
        state = 'inactive'
        actions = []

    return state, actions
