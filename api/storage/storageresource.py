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

from occi import backend
from occi.extensions import infrastructure
from webob import exc

from api import nova_glue


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
            exc.HTTPBadRequest()

        new_volume = nova_glue.create_storage(entity, context)

        # Work around problem that instance is lazy-loaded...
        new_volume = nova_glue.get_storage_instance(new_volume['id'], context)

        if new_volume['status'] == 'error':
            msg = 'There was an error creating the volume'
            raise exc.HTTPServerError(msg)

        entity.attributes['occi.core.id'] = str(new_volume['id'])

        if new_volume['status'] == 'available':
            entity.attributes['occi.storage.state'] = 'online'

        entity.actions = [infrastructure.OFFLINE, infrastructure.BACKUP,
                            infrastructure.SNAPSHOT, infrastructure.RESIZE]

    def retrieve(self, entity, extras):
        """
        Gets a representation of the storage volume and presents it ready for
        rendering by pyssf.
        """
        v_id = int(entity.attributes['occi.core.id'])

        vol = nova_glue.get_storage_instance(v_id, extras['nova_ctx'])

        entity.attributes['occi.storage.size'] = str(float(vol['size']))

        # OS volume states:
        #       available, creating, deleting, in-use, error, error_deleting
        if vol['status'] == 'available' or vol['status'] == 'in-use':
            entity.attributes['occi.storage.state'] = 'online'
            entity.actions = [infrastructure.OFFLINE, infrastructure.BACKUP,
                              infrastructure.SNAPSHOT, infrastructure.RESIZE]

    def delete(self, entity, extras):
        """
        Deletes the storage resource
        """
        context = extras['nova_ctx']
        volume_id = int(entity.attributes['occi.core.id'])

        vol = nova_glue.get_storage_instance(volume_id, context)
        nova_glue.delete_storage_instance(vol, context)

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

            msg = ('Online storage action requested resource with id: %s') % \
                                                            entity.identifier
            raise exc.HTTPBadRequest(msg)

        elif action == infrastructure.OFFLINE:
            # OFFLINE, disconnected? disconnection supported in API otherwise
            # not. The following is not an approach to use:
            # self.volume_api.terminate_connection(context, volume, connector)

            # By default storage cannot be brought OFFLINE
            msg = ('Offline storage action requested for resource: %s') % \
                                                            entity.identifier
            raise exc.HTTPBadRequest(msg)

        elif action == infrastructure.BACKUP:
            # BACKUP: create a complete copy of the volume.
            msg = ('Backup action for storage resource with id: %s') % \
                                                            entity.identifier
            raise exc.HTTPBadRequest(msg)

        elif action == infrastructure.SNAPSHOT:
            # CDMI?!
            # SNAPSHOT: create a time-stamped copy of the volume? Supported in
            # OS volume API
            self._snapshot_storage(entity, extras)

        elif action == infrastructure.RESIZE:
            # TODO(dizz): not supported by API. A blueprint candidate?
            # RESIZE: increase, decrease size of volume. Not supported directly
            #         by the API

            msg = ('Resize storage actio requested resource with id: %s') % \
                                                            entity.identifier
            raise exc.HTTPNotImplemented(msg)

    def _snapshot_storage(self, entity, extras, backup=False):
        """
        Takes a snapshot of the specified storage resource
        """
        context = extras['nova_ctx']

        volume_id = int(entity.attributes['occi.core.id'])
        vol = nova_glue.get_storage_instance(volume_id, context)
        #TODO(dizz): these names/descriptions should be made better.
        if backup:
            name = 'backup name'
            description = 'backup description'
        else:
            # occi.core.title, occi.core.summary
            name = 'snapshot name'
            description = 'snapshot description'
        nova_glue.snapshot_storage_instance(vol, name, description, context)

    def update(self, old, new, extras):
        """
        Updates simple attributes of a storage resource:
        occi.core.title, occi.core.summary
        """
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
                msg = 'Cannot update the supplied attributes.'
                raise exc.HTTPBadRequest(explanation=msg)
        else:
            raise exc.HTTPBadRequest()

    def replace(self, old, new, extras):
        pass