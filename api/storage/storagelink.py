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
Storage link backends.
"""

#pylint: disable=R0201,W0232

import uuid

from nova_glue import vm

from occi import backend
from occi.extensions import infrastructure


class StorageLinkBackend(backend.KindBackend):
    """
    A backend for the storage links.
    """

    # TODO: need to implement retrieve so states get updated!!!!

    def create(self, link, extras):
        """
        Creates a link from a compute instance to a storage volume.
        The user must specify what the device id is to be.
        """
        context = extras['nova_ctx']
        instance_id = get_inst_to_attach(link)
        volume_id = get_vol_to_attach(link)
        mount_point = link.attributes['occi.storagelink.deviceid']

        vm.attach_volume(instance_id, volume_id, mount_point, context)

        link.attributes['occi.core.id'] = str(uuid.uuid4())
        link.attributes['occi.storagelink.deviceid'] = \
                                link.attributes['occi.storagelink.deviceid']
        link.attributes['occi.storagelink.mountpoint'] = ''
        link.attributes['occi.storagelink.state'] = 'active'

    def delete(self, link, extras):
        """
        Unlinks the the compute from the storage resource.
        """
        volume_id = get_vol_to_attach(link)
        vm.detach_volume(volume_id, extras['nova_ctx'])

# HELPERS


def get_inst_to_attach(link):
    """
    Gets the compute instance that is to have the storage attached.
    """
    if link.target.kind == infrastructure.COMPUTE:
        uid = link.target.attributes['occi.core.id']
    elif link.source.kind == infrastructure.COMPUTE:
        uid = link.source.attributes['occi.core.id']
    else:
        raise AttributeError('Id of the VM not found!')
    return uid


def get_vol_to_attach(link):
    """
    Gets the storage instance that is to have the compute attached.
    """
    if link.target.kind == infrastructure.STORAGE:
        uid = link.target.attributes['occi.core.id']
    elif link.source.kind == infrastructure.STORAGE:
        uid = link.source.attributes['occi.core.id']
    else:
        raise AttributeError('Id of the Volume not found!')
    return uid
