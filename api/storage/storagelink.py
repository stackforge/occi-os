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

from api import nova_glue


class StorageLinkBackend(backend.KindBackend):
    """
    A backend for the storage links.
    """

    def create(self, link, extras):
        """
        Creates a link from a compute instance to a storage volume.
        The user must specify what the device id is to be.
        """
        context = extras['nova_ctx']
        inst_to_attach = get_inst_to_attach(link, context)
        vol_to_attach = get_vol_to_attach(link, context)

        uid = link.attributes['occi.storagelink.deviceid']
        nova_glue.attach_volume(inst_to_attach, vol_to_attach['id'], uid,
                                context)

        link.attributes['occi.core.id'] = str(uuid.uuid4())
        link.attributes['occi.storagelink.deviceid'] = \
                                link.attributes['occi.storagelink.deviceid']
        link.attributes['occi.storagelink.mountpoint'] = ''
        link.attributes['occi.storagelink.state'] = 'active'


    def delete(self, link, extras):
        """
        Unlinks the the compute from the storage resource.
        """
        try:
            vol_to_detach = get_vol_to_attach(extras['nova_ctx'], link)
            nova_glue.detach_volume(vol_to_detach['id'], extras['nova_ctx'])
        except Exception:
            msg = 'Error in detaching storage volume.'
            raise AttributeError(msg)

# HELPERS

def get_inst_to_attach(link, context):
    """
    Gets the compute instance that is to have the storage attached.
    """
    if link.target.kind == infrastructure.COMPUTE:
        instance = nova_glue.get_vm_instance(link.target.attributes['occi' \
                                                                    '.core' \
                                                                    '.id'],
                                             context)
    elif link.source.kind == infrastructure.COMPUTE:
        instance = nova_glue.get_vm_instance(link.source.attributes['occi' \
                                                                    '.core' \
                                                                    '.id'],
                                             context)
    else:
        raise exc.HTTPBadRequest()
    return instance


def get_vol_to_attach(link, context):
    """
    Gets the storage instance that is to have the compute attached.
    """
    if link.target.kind == infrastructure.STORAGE:
        vol_to_attach = nova_glue.get_storage_instance(link.target
                                                       .attributes['occi' \
                                                                   '.core' \
                                                                   '.id'],
                                                       context)
    elif link.source.kind == infrastructure.STORAGE:
        vol_to_attach = nova_glue.get_storage_instance(link.source
                                                       .attributes['occi'\
                                                                   '.core'\
                                                                   '.id'],
                                                       context)
    else:
        raise exc.HTTPBadRequest()
    return vol_to_attach