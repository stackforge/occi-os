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


import uuid

from occi import backend
from occi.extensions import infrastructure
from webob import exc

from nova import compute
from nova import log as logging
from nova import volume


#Hi I'm a logger, use me! :-)
LOG = logging.getLogger('nova.api.occi.backends.storage.link')


class StorageLinkBackend(backend.KindBackend):
    """
    A backend for the storage links.
    """

    def __init__(self):
        super(StorageLinkBackend, self).__init__()
        self.volume_api = volume.API()
        self.compute_api = compute.API()

    def create(self, link, extras):
        """
        Creates a link from a compute instance to a storage volume.
        The user must specify what the device id is to be.
        """
        msg = _('Linking compute to storage via StorageLink.')
        LOG.info(msg)

        inst_to_attach = self._get_inst_to_attach(extras['nova_ctx'], link)
        vol_to_attach = self._get_vol_to_attach(extras['nova_ctx'], link)

        self.compute_api.attach_volume(
                                extras['nova_ctx'],
                                inst_to_attach,
                                vol_to_attach['id'],
                                link.attributes['occi.storagelink.deviceid'])

        link.attributes['occi.core.id'] = str(uuid.uuid4())
        link.attributes['occi.storagelink.deviceid'] = \
                                link.attributes['occi.storagelink.deviceid']
        link.attributes['occi.storagelink.mountpoint'] = ''
        link.attributes['occi.storagelink.state'] = 'active'

    def _get_inst_to_attach(self, context, link):
        """
        Gets the compute instance that is to have the storage attached.
        """
        if link.target.kind == infrastructure.COMPUTE:
            instance = self.compute_api.get(context,
                                        link.target.attributes['occi.core.id'])
        elif link.source.kind == infrastructure.COMPUTE:
            instance = self.compute_api.get(context,
                                        link.source.attributes['occi.core.id'])
        else:
            raise exc.HTTPBadRequest()
        return instance

    def _get_vol_to_attach(self, context, link):
        """
        Gets the storage instance that is to have the compute attached.
        """
        if link.target.kind == infrastructure.STORAGE:
            vol_to_attach = self.volume_api.get(context,
                                        link.target.attributes['occi.core.id'])
        elif link.source.kind == infrastructure.STORAGE:
            vol_to_attach = self.volume_api.get(context,
                                        link.source.attributes['occi.core.id'])
        else:
            raise exc.HTTPBadRequest()

        return vol_to_attach

    def delete(self, link, extras):
        """
        Unlinks the the compute from the storage resource.
        """
        msg = _('Unlinking entity from storage via StorageLink.')
        LOG.info(msg)

        try:
            vol_to_detach = self._get_vol_to_attach(extras['nova_ctx'], link)
            self.compute_api.detach_volume(extras['nova_ctx'],
                                                        vol_to_detach['id'])
        except Exception, e:
            msg = _('Error in detaching storage volume.')
            LOG.error(msg)
            raise e
