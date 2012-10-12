#!/usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4

#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""
Will test the OS occi_os_api against a local running instance.
"""

#pylint: disable=W0102,C0103,R0904

import json
import sys
import time
import httplib
import logging
import unittest
import random


HEADS = {'Content-Type':'text/occi',
         'Accept':'text/occi'
}

KEYSTONE_HOST = '127.0.0.1:5000'
OCCI_HOST = '127.0.0.1:8787'

# Init a simple logger...
logging.basicConfig(level=logging.DEBUG)
CONSOLE = logging.StreamHandler()
CONSOLE.setLevel(logging.DEBUG)
LOG = logging.getLogger()
LOG.addHandler(CONSOLE)


def do_request(verb, url, headers):
    """
    Do an HTTP request defined by a HTTP verb, an URN and a dict of headers.
    """
    conn = httplib.HTTPConnection(OCCI_HOST)
    conn.request(verb, url, None, headers)
    response = conn.getresponse()
    if response.status not in [200, 201]:
        LOG.error(response.reason)
        LOG.warn(response.read())
        sys.exit(1)

    heads = response.getheaders()
    result = {}
    for item in heads:
        if item[0] in ['category', 'link', 'x-occi-attribute',
                       'x-occi-location', 'location']:
            tmp = []
            for val in item[1].split(','):
                tmp.append(val.strip())
            result[item[0]] = tmp

    conn.close()
    return result


def get_os_token(username, password):
    """
    Get a security token from Keystone.
    """
    body = '{"auth": {"tenantName": "'+username+'", ' \
           '"passwordCredentials":{"username": "'+username+'", ' \
           '"password": "'+password+'"}}}'

    heads = {'Content-Type': 'application/json'}
    conn = httplib.HTTPConnection(KEYSTONE_HOST)
    conn.request("POST", "/v2.0/tokens", body, heads)
    response = conn.getresponse()
    data = response.read()
    tokens = json.loads(data)
    token = tokens['access']['token']['id']
    return token


def get_qi_listing(token):
    """
    Retrieve categories from QI.
    """
    heads = HEADS.copy()
    heads['X-Auth-Token'] = token
    result = do_request('GET', '/-/', heads)
    LOG.debug(result['category'])


def create_node(token, category_list, attributes=[]):
    """
    Create a VM.
    """
    heads = HEADS.copy()
    heads['X-Auth-Token'] = token

    for cat in category_list:
        if 'Category' in heads:
            heads['Category'] += ', ' + cat
        else:
            heads['Category'] = cat

    for attr in attributes:
        if 'X-OCCI-Attribute' in heads:
            heads['X-OCCI-Attribute'] += ', ' + attr
        else:
            heads['X-OCCI-Attribute'] = attr

    heads = do_request('POST', '/compute/', heads)
    loc = heads['location'][0]
    loc = loc[len('http://' + OCCI_HOST):]
    LOG.debug('Location is: ' + loc)
    return loc


def list_nodes(token, url):
    """
    List a bunch of resource.
    """
    heads = HEADS.copy()
    heads['X-Auth-Token'] = token
    heads = do_request('GET', url, heads)
    return heads['x-occi-location']


def get_node(token, location):
    """
    Retrieve a single resource.
    """
    heads = HEADS.copy()
    heads['X-Auth-Token'] = token
    heads = do_request('GET', location, heads)
    return heads


def destroy_node(token, location):
    """
    Destroy a single node.
    """
    heads = HEADS.copy()
    heads['X-Auth-Token'] = token
    heads = do_request('DELETE', location, heads)
    return heads


def trigger_action(token, url, action_cat, action_param =None):
    """
    Trigger an OCCI action.
    """
    heads = HEADS.copy()
    heads['X-Auth-Token'] = token
    heads['Category'] = action_cat
    if action_param is not None:
        heads['X-OCCI-Attribute'] = action_param

    do_request('POST', url, heads)


class SystemTest(unittest.TestCase):
    """
    Do a simple set of test.
    """


    def setUp(self):
        """
        Setup the test.
        """
        # Get a security token:
        self.token = get_os_token('admin', 'os4all')
        LOG.info('security token is: ' + self.token)


    def tesat_compute_node(self):
        """
        Test ops on a compute node!
        """
        # QI listing
        get_qi_listing(self.token)

        # create VM
        cats = ['m1.tiny; scheme="http://schemas.openstack'
                '.org/template/resource#"',
                'cirros-0.3.0-x86_64-uec; scheme="http://schemas.openstack'
                '.org/template/os#"',
                'compute; scheme="http://schemas.ogf'
                '.org/occi/infrastructure#"']
        vm_location = create_node(self.token, cats)
        # list computes
        if 'http://' + OCCI_HOST + vm_location not in list_nodes(self.token,
            '/compute/'):
            LOG.error('VM should be listed!')

        # wait
        cont = False
        while not cont:
            if 'occi.compute.state="active"' in get_node(self.token,
                vm_location)['x-occi-attribute']:
                cont = True
            else:
                time.sleep(5)

        # trigger stop
        trigger_action(self.token, vm_location + '?action=stop',
            'stop; scheme="http://schemas.ogf'
            '.org/occi/infrastructure/compute/action#"')

        # wait
        cont = False
        while not cont:
            if 'occi.compute.state="inactive"' in get_node(self.token,
                vm_location)['x-occi-attribute']:
                cont = True
            else:
                time.sleep(5)

        # trigger start
        trigger_action(self.token, vm_location + '?action=start',
            'start; scheme="http://schemas.ogf'
            '.org/occi/infrastructure/compute/action#"')

        # wait
        cont = False
        while not cont:
            if 'occi.compute.state="active"' in get_node(self.token,
                vm_location)['x-occi-attribute']:
                cont = True
            else:
                time.sleep(5)

        # delete
        destroy_node(self.token, vm_location)


    def test_security_grouping(self):
        """
        Test some security and accessibility stuff!
        """
        # create sec group
        heads = HEADS.copy()
        heads['X-Auth-Token'] = self.token
        name = 'my_grp' + str(random.randint(1, 999999))
        heads['Category'] = name + '; scheme="http://www.mystuff.org/sec#";' \
        ' rel="http://schemas.ogf.org/occi/infrastructure/security#group"; ' \
        'location="/mygroups/"'
        do_request('POST', '/-/', heads)

        # create sec rule
        cats = [name + '; scheme="http://www.mystuff.org/sec#"',
                'rule; scheme="http://schemas.openstack'
                '.org/occi/infrastructure/network/security#"']
        attrs = ['occi.network.security.protocol="tcp"',
                 'occi.network.security.to="22"',
                 'occi.network.security.from="22"',
                 'occi.network.security.range="0.0.0.0/0"']
        sec_rule_loc = create_node(self.token, cats, attrs)

        # list
        LOG.debug(list_nodes(self.token, '/mygroups/'))
        LOG.debug(do_request('GET', sec_rule_loc, heads))

        # FIXME: add VM to sec group - see #22
        #heads['X-OCCI-Location'] = vm_location
        #print do_request('POST', '/mygroups/', heads)

        # create new VM
        cats = ['m1.tiny; scheme="http://schemas.openstack'
                '.org/template/resource#"',
                'cirros-0.3.0-x86_64-uec; scheme="http://schemas.openstack'
                '.org/template/os#"',
                name + '; scheme="http://www.mystuff.org/sec#"',
                'compute; scheme="http://schemas.ogf'
                '.org/occi/infrastructure#"']
        vm_location = create_node(self.token, cats)

        # wait
        cont = False
        while not cont:
            if 'occi.compute.state="active"' in get_node(self.token,
                vm_location)['x-occi-attribute']:
                cont = True
            else:
                time.sleep(5)

#        # allocate floating IP
#        LOG.debug(trigger_action(self.token, vm_location +
#                                             '?action=alloc_float_ip',
#            'alloc_float_ip; scheme="http://schemas.openstack'
#            '.org/instance/action#"',
#            'org.openstack.network.floating.pool="nova"'))
#
#        #time.sleep(15)
#
#        # Deallocate Floating IP to VM
#        LOG.debug(trigger_action(self.token, vm_location +
#                                             '?action=dealloc_float_ip',
#            'dealloc_float_ip; scheme="http://schemas.openstack'
#            '.org/instance/action#"'))

        # change pw
        LOG.debug(trigger_action(self.token, vm_location + '?action=chg_pwd',
            'chg_pwd; scheme="http://schemas.openstack.org/instance/action#"',
            'org.openstack.credentials.admin_pwd="new_pass"'))

        # clean VM
        destroy_node(self.token, vm_location)

        # delete rule
        destroy_node(self.token, sec_rule_loc)

        time.sleep(5)

        # FIXME: delete sec group - see #18
        heads = HEADS.copy()
        heads['X-Auth-Token'] = self.token
        heads['Category'] = name + '; scheme="http://www.mystuff.org/sec#"'
        do_request('DELETE', '/-/', heads)


    def tesat_storage_stuff(self):
        """
        Test attaching and detaching storage volumes + snapshotting etc.
        """
        # create new VM
        cats = ['m1.tiny; scheme="http://schemas.openstack'
                '.org/template/resource#"',
                'cirros-0.3.0-x86_64-uec; scheme="http://schemas.openstack'
                '.org/template/os#"',
                'compute; scheme="http://schemas.ogf.org/occi/infrastructure#"']
        vm_location = create_node(self.token, cats)

        # create volume
        cats = ['storage; scheme="http://schemas.ogf.org/occi/infrastructure#"']
        attrs = ['occi.storage.size = 1.0']
        vol_location = create_node(self.token, cats, attrs)

        # get individual node.
        LOG.debug(get_node(self.token, vol_location)['x-occi-attribute'])

        time.sleep(15)

        # link volume and compute
        cats = ['storagelink; scheme="http://schemas.ogf'
                '.org/occi/infrastructure#"']
        attrs = ['occi.core.source=http://"' + OCCI_HOST + vm_location +  '"',
                 'occi.core.target=http://"' + OCCI_HOST + vol_location + '"',
                 'occi.storagelink.deviceid="/dev/vdc"']
        link_location = create_node(self.token, cats, attrs)

        # retrieve link
        LOG.debug(get_node(self.token, link_location)['x-occi-attribute'])

        time.sleep(30)

        # deassociate storage vol - see #15
        destroy_node(self.token, link_location)

        time.sleep(15)

        destroy_node(self.token, vol_location)

        # wait
        cont = False
        while not cont:
            if 'occi.compute.state="active"' in get_node(self.token,
                vm_location)['x-occi-attribute']:
                cont = True
            else:
                time.sleep(5)

        # Create a Image from an Active VM
        LOG.debug(trigger_action(self.token, vm_location +
                                             '?action=create_image',
            'create_image; scheme="http://schemas.openstack'
            '.org/instance/action#"',
            'org.openstack.snapshot.image_name="awesome_ware"'))

        destroy_node(self.token, vm_location)


    def tesat_scaling(self):
        """
        Test the scaling operations
        """
        # create new VM
        cats = ['itsy; scheme="http://schemas.openstack'
                '.org/template/resource#"',
                'cirros-0.3.0-x86_64-uec; scheme="http://schemas.openstack'
                '.org/template/os#"',
                'compute; scheme="http://schemas.ogf.org/occi/infrastructure#"']
        vm_location = create_node(self.token, cats)

        # wait
        cont = False
        while not cont:
            if 'occi.compute.state="active"' in get_node(self.token,
                                vm_location)['x-occi-attribute']:
                cont = True
            else:
                time.sleep(5)

        # scale up VM - see #17
        heads = HEADS.copy()
        heads['X-Auth-Token'] = self.token
        heads['Category'] = 'bitsy; scheme="http://schemas.openstack' \
                            '.org/template/resource#"'
        do_request('POST', vm_location, heads)

        # wait
        cont = False
        while not cont:
            if 'occi.compute.state="active"' in get_node(self.token,
                vm_location)['x-occi-attribute']:
                cont = True
            else:
                time.sleep(5)

        destroy_node(self.token, vm_location)

