#!/bin/sh

rm -rf build/html
mkdir -p build/html

echo '\n PyLint report     \n****************************************\n'

pylint -d W0511,I0011,E1101,E0611,F0401 -i y --report no **/*.py

echo '\n Unittest coverage \n****************************************\n'

nc -z localhost 8787
if [ "$?" -ne 0 ]; then
  echo "Unable to connect to OCCI endpoint localhost 8787 - will not run
  system test."
  nosetests --with-coverage --cover-erase --cover-package=occi_os_api --exclude=system
else
  echo "Please make sure that the following line is available in nova.conf:"
  echo "allow_resize_to_same_host=True libvirt_inject_password=True enabled_apis=ec2,occiapi,osapi_compute,osapi_volume,metadata )"

  source ../devstack/openrc
  nova-manage flavor create --name=itsy --cpu=1 --memory=32 --flavor=98 --root_gb=1 --ephemeral_gb=1
  nova-manage flavor create --name=bitsy --cpu=1 --memory=64 --flavor=99 --root_gb=1 --ephemeral_gb=1
  nosetests --with-coverage --cover-erase --cover-package=occi_os_api
fi

echo '\n Code style        \n****************************************\n'

pep8 --repeat --statistics --count occi_os_api

echo '\n Issues report     \n****************************************\n'

pyflakes occi_os_api

echo '\n Pychecker report  \n****************************************\n'

pychecker -# 99 occi_os_api/*.py occi_os_api/backends/*.py
occi_os_api/nova_glue/*.py occi_os_api/extensions/*.py

# TODO: create project!
#epydoc epydoc.prj

# Fix:
#tmetsch@ubuntu:~/devstack$ cat /etc/tgt/targets.conf
#include /etc/tgt/conf.d/cinder.conf
#
# in devstack/files/horizon_settings:
#HORIZON_CONFIG = {
# #'dashboards': ('nova', 'syspanel', 'settings',),
# 'dashboards': ('project', 'admin', 'settings',),
# 'default_dashboard': 'project',
#}
