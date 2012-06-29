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
Storage related glue :-)
"""

import random

from nova import image, exception
from nova import volume

from occi import exceptions

# Connection to the nova APIs
from nova_glue import vm

VOLUME_API = volume.API()

IMAGE_API = image.get_default_image_service()


def create_storage(size, context, name=None, description=None):
    """
    Create a storage instance.

    size -- Size of the storage. ('occi.storage.size')
    context -- The os context.
    name -- defaults to a random number if needed.
    description -- defaults to the name
    """
    # TODO: exception handling!
    # TODO(dizz): A blueprint?
    # OpenStack deals with size in terms of integer.
    # Need to convert float to integer for now and only if the float
    # can be losslessly converted to integer
    # e.g. See nova/quota.py:allowed_volumes(...)
    if not float(size).is_integer:
        raise AttributeError('Volume sizes cannot be specified as fractional'
                             ' floats.')
    #size = str(int(float(size)))
    size = int(float(size))

    disp_name = ''
    if name is not None:
        disp_name = name
    else:
        disp_name = str(random.randrange(0, 99999999)) + '-storage.occi-wg.org'
    if description is not None:
        disp_descr = description
    else:
        disp_descr = disp_name

    new_volume = VOLUME_API.create(context,
                                   size,
                                   disp_name,
                                   disp_descr)
    return new_volume


def delete_storage_instance(uid, context):
    """
    Delete a storage instance.

    uid -- Id of the volume.
    context -- The os context.
    """
    # TODO: exception handling!
    instance = get_storage(uid, context)
    VOLUME_API.delete(context, instance)


def snapshot_storage_instance(uid, name, description, context):
    """
    Snapshots an storage instance.

    uid -- Id of the volume.
    context -- The os context.
    """
    # TODO: exception handling!
    instance = get_storage(uid, context)
    VOLUME_API.create_snapshot(context, instance, name, description)


def get_image_architecture(uid, context):
    """
    Extract architecture from either:
    - image name, title or metadata. The architecture is sometimes
      encoded in the image's name
    - db::glance::image_properties could be used reliably so long as the
      information is supplied when registering an image with glance.
    - else return a default of x86

    uid -- id of the instance!
    context -- The os context.
    """
    instance = vm.get_vm(uid, context)

    arch = ''
    uid = instance['image_ref']
    img = IMAGE_API.show(context, uid)
    img_properties = img['properties']
    if 'arch' in img_properties:
        arch = img['properties']['arch']
    elif 'architecture' in img_properties:
        arch = img['properties']['architecture']

    if arch == '':
        # if all attempts fail set it to a default value
        arch = 'x86'
    return arch


def get_storage(uid, context):
    """
    Retrieve an Volume instance from nova.

    uid -- id of the instance
    context -- the os context
    """
    try:
        instance = VOLUME_API.get(context, uid)
    except exception.NotFound:
        raise exceptions.HTTPError(404, 'Volume not found!')
    return instance
