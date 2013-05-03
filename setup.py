# coding=utf-8

# vim: tabstop=4 shiftwidth=4 softtabstop=4

#
# Copyright (c) 2012, Intel Performance Learning Solutions Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
Setupstools script which defines an entry point which can be used for OCCI
app later.
"""

from setuptools import setup


setup(
    name='occi-os-grizzly',
    version='1.0',
    description='OCCI interface for Openstack (stable/grizzly).',
    long_description='''
         This is a clone of https://github.com/dizz/nova - it provides a
         python egg which can be deployed in OpenStack and will thereby add the
         3rd party OCCI interface to OpenStack.
      ''',
    classifiers=[
        'Programming Language :: Python',
        'Development Status :: 5 - Production/Stable',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
        ],
    keywords='',
    author='Intel Performance Learning Solutions Ltd.',
    author_email='thijsx.metsch@intel.com',
    url='http://intel.com',
    license='Apache License, Version 2.0',
    include_package_data=True,
    packages=['occi_os_api','occi_os_api.backends','occi_os_api.extensions',
              'occi_os_api.nova_glue'],
    zip_safe=False,
    install_requires=[
        'setuptools',
        ],
    entry_points='''
      [paste.app_factory]
      occi_app = occi_os_api:main
      ''',
)
