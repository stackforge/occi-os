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
Will test the OS api against a local running instance.
"""

import logging
import unittest


HEADS = {'Content-Type':'text/occi',
         'Accept':'text/occi'
}

KEYSTONE_HOST='127.0.0.1:5000'
OCCI_HOST='127.0.0.1:8787'

# Init a simple logger...
logging.basicConfig(level=logging.DEBUG)
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
LOG = logging.getLogger()
LOG.addHandler(console)


def do_request(verb, url, headers):
    '''
    Do an HTTP request defined by a HTTP verb, an URN and a dict of headers.
    '''
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
        if item[0] in ['category', 'link', 'x-occi-attribute', 'x-occi-location', 'location']:
            tmp = []
            for val in item[1].split(','):
                tmp.append(val.strip())
            result[item[0]] = tmp

    conn.close()
    return result


def get_os_token(username, password):
    '''
    Get a security token from Keystone.
    '''
    body = '{"auth": {"tenantName": "'+username+'", "passwordCredentials":{"username": "'+username+'", "password": "'+password+'"}}}'

    heads = {'Content-Type': 'application/json'}
    conn = httplib.HTTPConnection(KEYSTONE_HOST)
    conn.request("POST", "/v2.0/tokens", body, heads)
    response = conn.getresponse()
    data = response.read()
    tokens = json.loads(data)
    token = tokens['access']['token']['id']
    return token


def get_qi_listing(token):
    heads = HEADS.copy()
    heads['X-Auth-Token'] = token
    result = do_request('GET', '/-/', heads)
    LOG.debug(result['category'])


def create_node(token, category_list):
    '''
    Create a VM.
    '''
    heads = HEADS.copy()
    heads['X-Auth-Token'] = token

    heads['Category'] = 'compute; scheme="http://schemas.ogf.org/occi/infrastructure#"'
    for cat in category_list:
        heads['Category'] += ', ' + cat

    heads = do_request('POST', '/compute/', heads)
    loc = heads['location'][0]
    loc = loc[len('http://' + OCCI_HOST):]
    LOG.debug('VM location is: ' + loc)
    return loc


def create_storage_node(token, attributes):
    heads = HEADS.copy()
    heads['X-Auth-Token'] = token

    heads['Category'] = 'storage; scheme="http://schemas.ogf.org/occi/infrastructure#"'
    heads['X-OCCI-Attribute'] = attributes

    heads = do_request('POST', '/storage/', heads)
    loc = heads['location'][0]
    loc = loc[len('http://' + OCCI_HOST):]
    LOG.debug('Storage location is: ' + loc)
    return loc


def list_nodes(token):
    heads = HEADS.copy()
    heads['X-Auth-Token'] = token
    heads = do_request('GET', '/compute/', heads)
    return heads['x-occi-location']


def get_node(token, location):
    heads = HEADS.copy()
    heads['X-Auth-Token'] = token
    heads = do_request('GET', location, heads)
    return heads


def destroy_node(token, location):
    heads = HEADS.copy()
    heads['X-Auth-Token'] = token
    heads = do_request('DELETE', location, heads)
    return heads


def trigger_action(token, url, action_cat, action_param =None):
    '''
    Trigger an OCCI action.
    '''
    heads = HEADS.copy()
    heads['X-Auth-Token'] = token
    heads['Category'] = action_cat
    if action_param is not None:
        heads['X-OCCI-Attribute'] = action_param

    do_request('POST', url, heads)


def attach_storage_vol(token, vm_location, vol_location):
    heads = HEADS.copy()
    heads['X-Auth-Token'] = token
    heads['Category'] = 'storagelink; scheme="http://schemas.ogf.org/occi/infrastructure#"'
    heads['X-OCCI-Attribute'] = 'occi.core.source=http://"' +\
                                OCCI_HOST + vm_location +  '"'\
                                                           ', occi.core.target=http://"' + OCCI_HOST +\
                                vol_location +\
                                '", occi.storagelink.deviceid="/dev/vdc"'
    heads = do_request('POST', '/storage/link/', heads)
    loc = heads['location'][0]
    loc = loc[len('http://' + OCCI_HOST):]
    LOG.debug('Storage link location is: ' + loc)
    return loc

class MyTestCase(unittest.TestCase):

    def test_something(self):
        # Get a security token:
        token = get_os_token('admin', 'os4all')
        LOG.info('security token is: ' + token)

        # QI listing
        get_qi_listing(token)

        # create VM
        vm_location = create_node(token,['m1.tiny; scheme="http://schemas'
                                         '.openstack.org/template/resource#"',
                                         'cirros-0.3.0-x86_64-uec; '
                                         'scheme="http://schemas.openstack.org/template/os#"'])
        # list computes
        if 'http://' + OCCI_HOST + vm_location not in list_nodes(token):
            LOG.error('VM should be listed!')

        # wait
        time.sleep(15)

        # get individual node.
        LOG.debug(get_node(token, vm_location)['x-occi-attribute'])

        # trigger stop
        trigger_action(token, vm_location + '?action=stop',
            'stop; scheme="http://schemas.ogf.org/occi/infrastructure/compute/action#"')

        # wait
        time.sleep(15)
        LOG.debug(get_node(token, vm_location)['x-occi-attribute'])

        # trigger start
        trigger_action(token, vm_location + '?action=start',
            'start; scheme="http://schemas.ogf'
            '.org/occi/infrastructure/compute/action#"')

        # create volume
        #vol_location = create_storage_node(token, 'occi.storage.size = 1.0')

        # get individual node.
        #LOG.debug(get_node(token, vol_location)['x-occi-attribute'])

        time.sleep(15)

        # link volume and copute
        #link_location = attach_storage_vol(token, vm_location, vol_location)

        #LOG.debug(get_node(token, link_location)['x-occi-attribute'])

        # deassociate storage vol - see #15
        # destroy_node(token, link_location)
        # destroy_node(token, vol_location) # untested because of last command

        # scale up VM - see #17
        #heads = HEADS.copy()
        #heads['X-Auth-Token'] = token
        #heads['Category'] = 'm1.large; scheme="http://schemas.openstack.org/template/resource#"'
        #print do_request('POST', vm_location, heads)

        # confirm scale up
        #trigger_action(token, vm_location + '?action=confirm_resize', 'confirm_resize; scheme="http://schemas.openstack.org/instance/action#"')

        # create sec group
        heads = HEADS.copy()
        heads['X-Auth-Token'] = token
        heads['Category'] = 'my_grp; scheme="http://www.mystuff.org/sec#"; class="mixin"; rel="http://schemas.ogf.org/occi/infrastructure/security#group"; location="/mygroups/"'
        print do_request('POST', '/-/', heads)

        print do_request('GET', '/-/', heads)

        # create sec rule
        heads = HEADS.copy()
        heads['X-Auth-Token'] = token
        heads['Category'] = 'my_grp; scheme="http://www.mystuff.org/sec#", rule; scheme="http://schemas.openstack.org/occi/infrastructure/network/security#"'
        heads['X-OCCI-Attribute'] = 'occi.network.security.protocol = "TCP", occi.network.security.to ="22",  occi.network.security.from ="22", occi.network.security.range = "0.0.0.0/0"'
        heads = do_request('POST', '/network/security/rule/', heads)
        loc = heads['location'][0]
        sec_rule_loc = loc[len('http://' + OCCI_HOST):]
        LOG.debug('Security Rule location is: ' + sec_rule_loc)

        heads = HEADS.copy()
        heads['X-Auth-Token'] = token
        print do_request('GET', '/mygroups/', heads)

        print do_request('GET', sec_rule_loc, heads)

        # add VM to sec group - see #22
        #heads['X-OCCI-Location'] = vm_location
        #print do_request('POST', '/mygroups/', heads)

        # create new VM
        destroy_node(token, vm_location)
        vm_location = create_node(token,['m1.tiny; scheme="http://schemas'
                                         '.openstack.org/template/resource#"',
                                         'cirros-0.3.0-x86_64-uec; '
                                         'scheme="http://schemas.openstack.org/template/os#"','my_grp; scheme="http://www.mystuff.org/sec#"'])

        time.sleep(15)

        # allocate floating IP
        print trigger_action(token, vm_location + '?action=alloc_float_ip', 'alloc_float_ip; scheme="http://schemas.openstack.org/instance/action#"', 'org.openstack.network.floating.pool="nova"')

        time.sleep(15)

        #Deallocate Floating IP to VM
        print trigger_action(token, vm_location + '?action=dealloc_float_ip', 'dealloc_float_ip; scheme="http://schemas.openstack.org/instance/action#"')

        # delte rule
        print do_request('DELETE', sec_rule_loc, heads)

        # delete sec group - see #18
        heads['Category'] = 'my_grp; scheme="http://www.mystuff.org/sec#"'
        print do_request('DELETE', '/-/', heads)


        # change pw
        print trigger_action(token, vm_location + '?action=chg_pwd', 'chg_pwd; scheme="http://schemas.openstack.org/instance/action#"', 'org.openstack.credentials.admin_pwd="new_pass"')

        # Create a Image from an Active VM
        print trigger_action(token, vm_location + '?action=create_image', 'create_image; scheme="http://schemas.openstack.org/instance/action#"', 'org.openstack.snapshot.image_name="awesome_ware"')

        # clean VM
        destroy_node(token, vm_location)


