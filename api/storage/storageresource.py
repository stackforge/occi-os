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

import random

from occi import backend
from occi.extensions import infrastructure
from webob import exc

from nova import exception
from nova import log as logging
from nova import volume


#Hi I'm a logger, use me! :-)
LOG = logging.getLogger('nova.api.occi.backends.storage')


class StorageBackend(backend.KindBackend, backend.ActionBackend):
    """
    Backend to handle storage resources.
    """
    def __init__(self):
        super(StorageBackend, self).__init__()
        self.volume_api = volume.API()

    def create(self, resource, extras):
        """
        Creates a new volume.
        """

        if 'occi.storage.size' not in resource.attributes:
            exc.HTTPBadRequest()

        size = float(resource.attributes['occi.storage.size'])

        # TODO(dizz): A blueprint?
        # OpenStack deals with size in terms of integer.
        # Need to convert float to integer for now and only if the float
        # can be losslessly converted to integer
        # e.g. See nova/quota.py:allowed_volumes(...)
        if not size.is_integer:
            msg = _('Volume sizes cannot be specified as fractional floats.')
            LOG.error(msg)
            raise exc.HTTPBadRequest()

        size = str(int(size))

        msg = _("Creating volume of %s GB") % size
        LOG.info(msg)

        disp_name = ''
        try:
            disp_name = resource.attributes['occi.core.title']
        except KeyError:
            #Generate more suitable name as it's used for hostname
            #where no hostname is supplied.
            disp_name = resource.attributes['occi.core.title'] = \
                            str(random.randrange(0, 99999999)) + \
                                                        '-storage.occi-wg.org'
        if 'occi.core.summary' in resource.attributes:
            disp_descr = resource.attributes['occi.core.summary']
        else:
            disp_descr = disp_name

        snapshot = None
        # volume_type can be specified by mixin
        volume_type = None
        metadata = None
        avail_zone = None
        new_volume = self.volume_api.create(extras['nova_ctx'],
                                            size,
                                            disp_name,
                                            disp_descr,
                                            snapshot=snapshot,
                                            volume_type=volume_type,
                                            metadata=metadata,
                                            availability_zone=avail_zone)

        # Work around problem that instance is lazy-loaded...
        new_volume = self.volume_api.get(extras['nova_ctx'], new_volume['id'])

        if new_volume['status'] == 'error':
            msg = _('There was an error creating the volume')
            LOG.error(msg)
            raise exc.HTTPServerError(msg)

        resource.attributes['occi.core.id'] = str(new_volume['id'])

        if new_volume['status'] == 'available':
            resource.attributes['occi.storage.state'] = 'online'

        resource.actions = [infrastructure.OFFLINE, infrastructure.BACKUP,
                            infrastructure.SNAPSHOT, infrastructure.RESIZE]

    def retrieve(self, entity, extras):
        """
        Gets a representation of the storage volume and presents it ready for
        rendering by pyssf.
        """
        v_id = int(entity.attributes['occi.core.id'])

        try:
            vol = self.volume_api.get(extras['nova_ctx'], v_id)
        except exception.NotFound:
            raise exc.HTTPNotFound()

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
        msg = _('Removing storage device with id: %s') % entity.identifier
        LOG.info(msg)

        volume_id = int(entity.attributes['occi.core.id'])

        try:
            vol = self.volume_api.get(extras['nova_ctx'], volume_id)
            self.volume_api.delete(extras['nova_ctx'], vol)
        except exception.NotFound:
            raise exc.HTTPNotFound()

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

            msg = _('Online storage action requested resource with id: %s') % \
                                                            entity.identifier
            LOG.warn(msg)
            raise exc.HTTPBadRequest()

        elif action == infrastructure.OFFLINE:
            # OFFLINE, disconnected? disconnection supported in API otherwise
            # not. The following is not an approach to use:
            # self.volume_api.terminate_connection(context, volume, connector)

            # By default storage cannot be brought OFFLINE
            msg = _('Offline storage action requested for resource: %s') % \
                                                            entity.identifier
            LOG.warn(msg)
            raise exc.HTTPBadRequest()

        elif action == infrastructure.BACKUP:
            # BACKUP: create a complete copy of the volume.
            msg = _('Backup action for storage resource with id: %s') % \
                                                            entity.identifier
            LOG.warn(msg)
            raise exc.HTTPBadRequest()

        elif action == infrastructure.SNAPSHOT:
            # CDMI?!
            # SNAPSHOT: create a time-stamped copy of the volume? Supported in
            # OS volume API
            self._snapshot_storage(entity, extras)

        elif action == infrastructure.RESIZE:
            # TODO(dizz): not supported by API. A blueprint candidate?
            # RESIZE: increase, decrease size of volume. Not supported directly
            #         by the API

            msg = _('Resize storage actio requested resource with id: %s') % \
                                                            entity.identifier
            LOG.warn(msg)
            raise exc.HTTPNotImplemented()

    def _snapshot_storage(self, entity, extras, backup=False):
        """
        Takes a snapshot of the specified storage resource
        """
        msg = _('Snapshoting storage resource with id: %s') % entity.identifier
        LOG.info(msg)

        volume_id = int(entity.attributes['occi.core.id'])
        vol = self.volume_api.get(extras['nova_ctx'], volume_id)
        #TODO(dizz): these names/descriptions should be made better.
        if backup:
            name = 'backup name'
            description = 'backup description'
        else:
            # occi.core.title, occi.core.summary
            name = 'snapshot name'
            description = 'snapshot description'
        self.volume_api.create_snapshot(extras['nova_ctx'],
                                        vol, name, description)

    def update(self, old, new, extras):
        """
        Updates simple attributes of a storage resource:
        occi.core.title, occi.core.summary
        """
        # update attributes.
        if len(new.attributes) > 0:
            msg = _('Updating mutable attributes of volume instance')
            LOG.info(msg)
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
                msg = _('Cannot update the supplied attributes.')
                LOG.error()
                raise exc.HTTPBadRequest()
        else:
            raise exc.HTTPBadRequest()
