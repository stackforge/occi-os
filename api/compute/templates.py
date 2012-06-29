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
Set of templates.
"""

#pylint: disable=R0913,E1002,R0903,W0232

from occi import core_model


class OsTemplate(core_model.Mixin):
    """
    Represents the OS Template mechanism as per OCCI specification.
    An OS template is equivalent to an image in OpenStack
    """
    def __init__(self, scheme, term, os_id=None, related=None, actions=None,
                 title='', attributes=None, location=None):
        super(OsTemplate, self).__init__(scheme, term, related, actions,
                                         title, attributes, location)
        self.os_id = os_id


OS_TEMPLATE = OsTemplate('http://schemas.ogf.org/occi/infrastructure#',
                                                                    'os_tpl')


class ResourceTemplate(core_model.Mixin):
    """
    Represents the Resource Template mechanism as per OCCI specification.
    An Resource template is equivocal to a flavor in OpenStack. Implemented
    as such for consistency with OsTemplate.
    """
    pass


RES_TEMPLATE = ResourceTemplate('http://schemas.ogf.org/occi/infrastructure#',
                                                                'resource_tpl')
