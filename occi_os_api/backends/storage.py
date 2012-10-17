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
Backends for the storage resource.
"""

#pylint: disable=R0201,W0232,W0613
import uuid

from occi import backend
from occi import exceptions
from occi.extensions import infrastructure

from occi_os_api.nova_glue import storage
from occi_os_api.nova_glue import vm


class StorageBackend(backend.KindBackend, backend.ActionBackend):
    """
    Backend to handle storage resources.
    """

    def create(self, entity, extras):
        """
        Creates a new volume.
        """
        context = extras['nova_ctx']
        if 'occi.storage.size' not in entity.attributes:
            raise AttributeError('size attribute not found!')

        new_volume = storage.create_storage(entity.attributes['occi.storage' \
                                                          '.size'], context)
        vol_id = new_volume['id']

        # Work around problem that instance is lazy-loaded...
        new_volume = storage.get_storage(vol_id, context)

        if new_volume['status'] == 'error':
            raise exceptions.HTTPError(500, 'There was an error creating the '
                                       'volume')
        entity.attributes['occi.core.id'] = str(vol_id)
        entity.identifier = infrastructure.STORAGE.location + vol_id

        if new_volume['status'] == 'available':
            entity.attributes['occi.storage.state'] = 'online'

        entity.actions = [infrastructure.OFFLINE, infrastructure.BACKUP,
                            infrastructure.SNAPSHOT, infrastructure.RESIZE]

    def retrieve(self, entity, extras):
        """
        Gets a representation of the storage volume and presents it ready for
        rendering by pyssf.
        """
        v_id = entity.attributes['occi.core.id']

        volume = storage.get_storage(v_id, extras['nova_ctx'])

        entity.attributes['occi.storage.size'] = str(float(volume['size']))

        # OS volume states:
        #       available, creating, deleting, in-use, error, error_deleting
        if volume['status'] == 'available' or volume['status'] == 'in-use':
            entity.attributes['occi.storage.state'] = 'online'
            entity.actions = [infrastructure.OFFLINE, infrastructure.BACKUP,
                              infrastructure.SNAPSHOT, infrastructure.RESIZE]
        else:
            entity.attributes['occi.storage.state'] = 'offline'

    def update(self, old, new, extras):
        """
        Updates simple attributes of a storage resource:
        occi.core.title, occi.core.summary
        """
        # TODO: proper set the state of an storage instance!

        # update attributes.
        if len(new.attributes) > 0:
            # support only title and summary changes now.
            if (('occi.core.title' in new.attributes)
                or ('occi.core.title' in new.attributes)):
                if len(new.attributes['occi.core.title']) > 0:
                    old.attributes['occi.core.title'] = \
                    new.attributes['occi.core.title']

                if len(new.attributes['occi.core.summary']) > 0:
                    old.attributes['occi.core.summary'] = \
                    new.attributes['occi.core.summary']
            else:
                raise AttributeError('Cannot update the supplied attributes.')

    def replace(self, old, new, extras):
        """
        Ignored.
        """
        pass

    def delete(self, entity, extras):
        """
        Deletes the storage resource
        """
        context = extras['nova_ctx']
        volume_id = entity.attributes['occi.core.id']

        storage.delete_storage_instance(volume_id, context)

    def action(self, entity, action, attributes, extras):
        """
        Executes actions against the target storage resource.
        """
        if action not in entity.actions:
            raise AttributeError("This action is currently no applicable.")

        elif action == infrastructure.ONLINE:
            # ONLINE, ready for service, default state of a created volume.
            # could this cover the attach functionality in storage link?
            # The following is not an approach to use:
            # self.volume_api.initialize_connection(context, volume, connector)

            # By default storage is ONLINE and can not be brought OFFLINE

            msg = 'Online storage action requested resource with id: %s' % \
                                                            entity.identifier
            raise AttributeError(msg)

        elif action == infrastructure.OFFLINE:
            # OFFLINE, disconnected? disconnection supported in API otherwise
            # not. The following is not an approach to use:
            # self.volume_api.terminate_connection(context, volume, connector)

            # By default storage cannot be brought OFFLINE
            msg = 'Offline storage action requested for resource: %s' % \
                                                            entity.identifier
            raise AttributeError(msg)

        elif action == infrastructure.BACKUP:
            # BACKUP: create a complete copy of the volume.
            msg = 'Backup action for storage resource with id: %s' % \
                                                            entity.identifier
            raise AttributeError(msg)

        elif action == infrastructure.SNAPSHOT:
            # CDMI?!
            # SNAPSHOT: create a time-stamped copy of the volume? Supported in
            # OS volume API
            volume_id = int(entity.attributes['occi.core.id'])
            # occi.core.title, occi.core.summary
            name = 'snapshot name'
            description = 'snapshot description'
            storage.snapshot_storage_instance(volume_id, name, description,
                                          extras['nova_ctx'])

        elif action == infrastructure.RESIZE:
            # TODO(dizz): not supported by API. A blueprint candidate?
            # RESIZE: increase, decrease size of volume. Not supported directly
            #         by the API

            msg = 'Resize storage actio requested resource with id: %s' % \
                                                            entity.identifier
            raise AttributeError(msg)


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

    def retrieve(self, entity, extras):
        """
        Get most up to date attribute informations.
        """
        # occi.storagelink.deviceid
        # occi.storagelink.mountpoint
        # occi.storagelink.state
        pass

    def delete(self, link, extras):
        """
        Unlinks the the compute from the storage resource.
        """
        volume_id = get_vol_to_attach(link)
        vm.detach_volume(volume_id, extras['nova_ctx'])
