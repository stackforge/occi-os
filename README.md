occi-os
=======

This is a clone of https://github.com/dizz/nova - it provides a python egg which can be deployed in OpenStack and will thereby add the 3rd party OCCI interface to OpenStack.

Usage
-----

1. Install this egg: python setup.py install (later maybe pip install occi-os)
2. Configure OpenStack - Add application to api-paste of nova and enable the API

Configuration
^^^^^^^^^^^^^

Make sure an application is configured in api-paste.ini (name can be picked yourself):

	[composite:testapp]
	use = egg:Paste#urlmap
	/: testapp11

	[app:testapp11]
	use = egg:occi-os#occi_app

Make sure the API (name from above) is enabled in nova.conf:

	[...]
	enabled_apis=ec2,occiapi,osapi_compute,osapi_volume,metadata,testapp
	[...]
	
For development
^^^^^^^^^^^^^^^

Make sure the nova compute api is in the path for Python and if you wanna test the app run:

	paster serve api-paste.ini --reload
