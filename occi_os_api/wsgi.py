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
OCCI WSGI app :-)
"""

# W0613:unused args,R0903:too few pub methods
# pylint: disable=W0613,R0903

import logging

from nova import flags
from nova import wsgi
from nova import db
from nova.image import glance
from nova.compute import instance_types
from nova.openstack.common import cfg

from occi_os_api import registry
from occi_os_api.backends import compute
from occi_os_api.backends import openstack
from occi_os_api.backends import network
from occi_os_api.backends import storage
from occi_os_api.extensions import os_mixins
from occi_os_api.extensions import os_addon

from occi import backend
from occi import core_model
from occi import wsgi as occi_wsgi
from occi.extensions import infrastructure

LOG = logging.getLogger(__name__)

#Setup options
OCCI_OPTS = [
             cfg.IntOpt("occiapi_listen_port",
                        default=8787,
                        help="Port OCCI interface will listen on."),
             cfg.StrOpt("occi_custom_location_hostname",
                    default=None,
                    help="Override OCCI location hostname with custom value")
             ]

FLAGS = flags.FLAGS
FLAGS.register_opts(OCCI_OPTS)

MIXIN_BACKEND = backend.MixinBackend()


class OCCIApplication(occi_wsgi.Application, wsgi.Application):
    """
    Adapter which 'translates' represents a nova WSGI application into and OCCI
    WSGI application.
    """

    def __init__(self):
        """
        Initialize the WSGI OCCI application.
        """
        super(OCCIApplication, self).__init__(registry=registry.OCCIRegistry())
        self._register_backends()

    def _register_backends(self):
        """
        Registers the OCCI infrastructure resources to ensure compliance
        with GFD184
        """
        compute_backend = compute.ComputeBackend()
        network_backend = network.NetworkBackend()
        networkinterface_backend = network.NetworkInterfaceBackend()
        ipnetwork_backend = network.IpNetworkBackend()
        ipnetworking_backend = network.IpNetworkInterfaceBackend()

        storage_backend = storage.StorageBackend()
        storage_link_backend = storage.StorageLinkBackend()

        # register kinds with backends
        self.register_backend(infrastructure.COMPUTE, compute_backend)
        self.register_backend(infrastructure.START, compute_backend)
        self.register_backend(infrastructure.STOP, compute_backend)
        self.register_backend(infrastructure.RESTART, compute_backend)
        self.register_backend(infrastructure.SUSPEND, compute_backend)
        self.register_backend(infrastructure.OS_TEMPLATE, MIXIN_BACKEND)
        self.register_backend(infrastructure.RESOURCE_TEMPLATE, MIXIN_BACKEND)

        self.register_backend(infrastructure.NETWORK, network_backend)
        self.register_backend(infrastructure.UP, network_backend)
        self.register_backend(infrastructure.DOWN, network_backend)
        self.register_backend(infrastructure.NETWORKINTERFACE,
                                          networkinterface_backend)
        self.register_backend(infrastructure.IPNETWORK, ipnetwork_backend)
        self.register_backend(infrastructure.IPNETWORKINTERFACE,
                                          ipnetworking_backend)

        self.register_backend(infrastructure.STORAGE, storage_backend)
        self.register_backend(infrastructure.ONLINE, storage_backend)
        self.register_backend(infrastructure.OFFLINE, storage_backend)
        self.register_backend(infrastructure.BACKUP, storage_backend)
        self.register_backend(infrastructure.SNAPSHOT, storage_backend)
        self.register_backend(infrastructure.RESIZE, storage_backend)
        self.register_backend(infrastructure.STORAGELINK, storage_link_backend)

        # add extensions for occi.
        self.register_backend(os_addon.SEC_GROUP,
            openstack.SecurityGroupBackend())
        self.register_backend(os_addon.SEC_RULE,
            openstack.SecurityRuleBackend())
        self.register_backend(os_addon.OS_VM,
            openstack.OsComputeBackend())
        self.register_backend(os_addon.OS_CREATE_IMAGE,
            openstack.OsComputeBackend())
        self.register_backend(os_addon.OS_CHG_PWD,
            openstack.OsComputeBackend())

    def __call__(self, environ, response):
        """
        This will be called as defined by WSGI.
        Deals with incoming requests and outgoing responses

        Takes the incoming request, sends it on to the OCCI WSGI application,
        which finds the appropriate backend for it and then executes the
        request. The backend then is responsible for the return content.

        environ -- The environ.
        response -- The response.
        """
        extras = {'nova_ctx': environ['nova.context']}

        # register/refresh openstack images
        self._refresh_os_mixins(extras)
        # register/refresh openstack instance types (flavours)
        self._refresh_resource_mixins(extras)
        # register/refresh the openstack security groups as Mixins
        self._refresh_security_mixins(extras)

        return self._call_occi(environ, response, nova_ctx=extras['nova_ctx'],
                                                        registry=self.registry)

    def _refresh_os_mixins(self, extras):
        """
        Register images as OsTemplate mixins from
        information retrieved from glance (shared and user-specific).
        """
        template_schema = 'http://schemas.openstack.org/template/os#'
        image_service = glance.get_default_image_service()

        images = image_service.detail(extras['nova_ctx'])

        for img in images:
            # If the image is a kernel or ram one
            # and we're not to filter them out then register it.
            if (((img['container_format'] or img['disk_format']) in ('ari',
                                                                     'aki'))):
                msg = 'Not registering kernel/RAM image.'
                LOG.debug(msg)
                continue

            os_template = os_mixins.OsTemplate(
                                term=img['name'].strip().replace(' ', '_'),
                                scheme=template_schema,
                                os_id=img['id'],
                                related=[infrastructure.OS_TEMPLATE],
                                attributes=None,
                                title='This is an OS ' + img['name'] + \
                                                            ' VM image',
                                location='/' + img['name'] + '/')

            try:
                self.registry.get_backend(os_template, extras)
            except AttributeError:
                msg = 'Registering an OS image type as: %s' % str(os_template)
                LOG.debug(msg)
                self.register_backend(os_template, MIXIN_BACKEND)

    def _refresh_resource_mixins(self, extras):
        """
        Register the flavors as ResourceTemplates to which the user has access.
        """
        template_schema = 'http://schemas.openstack.org/template/resource#'
        os_flavours = instance_types.get_all_types()

        for itype in os_flavours:
            resource_template = os_mixins.ResourceTemplate(
                term=itype.strip().replace(' ', '_'),
                scheme=template_schema,
                related=[infrastructure.RESOURCE_TEMPLATE],
                title='This is an openstack ' + itype + ' flavor.',
                location='/' + itype + '/')

            try:
                self.registry.get_backend(resource_template, extras)
            except AttributeError:
                msg = 'Registering an OpenStack flavour/instance type: %s' % \
                      str(resource_template)
                LOG.debug(msg)
                self.register_backend(resource_template, MIXIN_BACKEND)

    def _refresh_security_mixins(self, extras):
        """
        Registers security groups as security mixins
        """
        # ensures that preexisting openstack security groups are
        # added and only once.
        # collect these and add them to an exclusion list so they're
        # not created again when listing non-user-defined sec. groups
        excld_grps = []
        for cat in self.registry.get_categories(extras):
            if (isinstance(cat, core_model.Mixin) and
                                    os_addon.SEC_GROUP in cat.related):
                excld_grps.append(cat.term)

        groups = db.security_group_get_by_project(extras['nova_ctx'],
                                                extras['nova_ctx'].project_id)
        sec_grp = 'http://schemas.openstack.org/infrastructure/security/group#'

        for group in groups:
            if group['name'] not in excld_grps:
                sec_mix = os_mixins.UserSecurityGroupMixin(
                term=group['name'].strip().replace(' ', '_'),
                scheme=sec_grp,
                related=[os_addon.SEC_GROUP],
                attributes=None,
                title=group['name'],
                location='/security/' + group['name'] + '/')
                try:
                    self.registry.get_backend(sec_mix, extras)
                except AttributeError:
                    self.register_backend(sec_mix, MIXIN_BACKEND)
