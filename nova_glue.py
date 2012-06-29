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

# TODO(tmetsch): unify exception handling
# TODO(tmetsch): sanitize the interface - make sure call parameters and
# return values are consistent.
import random

from nova import compute, db
from nova import exception
from nova import image
from nova import network
from nova import utils
from nova import volume
from nova.compute import vm_states, task_states, instance_types
from nova.compute import utils as compute_utils
from nova.flags import FLAGS

from api.compute import templates
from api.extensions import occi_future
from api.extensions import openstack
from nova.openstack.common import importutils

from occi.extensions import infrastructure

from webob import exc

# Connection to the nova APIs

compute_api = compute.API()
network_api = network.API()
volume_api = volume.API()

image_api = image.get_default_image_service()
sec_handler = importutils.import_object(FLAGS.security_group_handler)
