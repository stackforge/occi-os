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

import os

from nova import log as logging


LOG = logging.getLogger('nova.api.occi.extensions')
EXTENSIONS = []


def load_extensions():
    """
    Loads compliant extensions found within the extensions module.
    See README.rst for details on extensions.
    """
    pth = __file__.rpartition(os.sep)
    pth = pth[0] + pth[1]

    # Walkthrough the extensions directory
    msg = _('Loading the following extensions...')
    LOG.info(msg)
    for _dirpath, _dirnames, filenames in os.walk(pth):
        for filename in filenames:
            if (filename.endswith('.py') and
                                        not filename.startswith('__init__')):
                mod = filename.split('.py')[0]
                exec('from %s import %s' % (__package__, mod))
                extn = eval(mod).get_extensions()
                EXTENSIONS.append(extn)
                msg = _('Loading occi extension: %s') % extn
                LOG.info(msg)


load_extensions()
