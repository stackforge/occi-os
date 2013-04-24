# Note:
This documentation may not be current in places. There is also further documentation at the [openstack wiki](https://wiki.openstack.org/wiki/Occi)


# OCCI and OpenStack: What can I do?
This guide will explain what you can do with the current OCCI implementation for OpenStack

## First up, prerequisites:
### Get a running instance of OpenStack
Lots of ways to do this:

 * Install via apt-get
 * Install with puppet
 * Install with chef
 * Install with crowbar
 * Install with devstack
 
The easiest is devstack.
### Get the OCCI code

#### OCCI Library
On the machine(s) that you run the OCCI API, likely the same as the machine(s) as you run the OS-API, run the following:

>```pip install pyssf```

#### OCCI API Implementation
On the machine(s) that you want to run the OCCI API, likely the same as the machine(s) as you run the OS-API, run the following:

>```cd $YOUR_NOVA_INSTALL_LOCATION```

>```git add remote occi-upstream git://git@github.com/dizz/nova```

>```git fetch occi-upstream```

>```git merge occi-upstream/master```

### Configure devstack to run the volume service. Edit localrc and insert:
>```ENABLED_SERVICES=g-api,g-reg,key,n-api,n-crt,n-obj,n-cpu,n-net,n-sch,n-novnc,n-xvnc,n-cauth,horizon,mysql,rabbit,n-vol,openstackx```

### Run the OS-OCCI API
>```./bin/nova-api-occi --verbose --glance_api_servers=10.211.55.27:9292 --rabbit_host=10.211.55.27 --rabbit_password=admin --sql_connection=mysql://root:admin@10.211.55.27/nova```

### Get Authentication Credentials from Keystone
>```curl -d '{"auth":{"passwordCredentials":{"username": "admin", "password": "admin"}}}' -H "Content-type: application/json" http://10.211.55.27:35357/v2.0/tokens
```

>```export $KID=<<Token from Keystone>>```

## OCCI-ness

_Note:_ some confusion will happen if a content-type is not specified.

### See What Can be Provisioned
>```curl -v -H 'X-Auth-Token: '$KID -H -X GET 0.0.0.0:8787/-/
```

### Create a VM
>```curl -v -X POST localhost:8787/compute/ -H 'Category: compute; scheme="http://schemas.ogf.org/occi/infrastructure#"; class="kind"' -H 'Content-Type: text/occi' -H 'X-Auth-Token: '$KID -H 'X-Auth-Project-ID: 1' -H 'Category: m1.tiny; scheme="http://schemas.openstack.org/template/resource#"; class="mixin"' -H 'Category: cirros-0.3.0-x86_64-blank; scheme="http://schemas.openstack.org/template/os#"; class="mixin"'
```

### Get a Listing of VMs
>```curl -v -X GET localhost:8787/compute/ -H 'Content-Type: text/occi' -H 'X-Auth-Token: '$KID -H 'X-Auth-Project-ID: 1'
```

### Get an Individual VM's details
>```curl -v -X GET localhost:8787/compute/d54b4344-16be-486a-9871-2c566ef2263d -H 'Content-Type: text/occi' -H 'X-Auth-Token: '$KID -H 'X-Auth-Project-ID: 1'
```

### Execute a Stop Action Upon a VM
>```curl -v -X POST localhost:8787/compute/d54b4344-16be-486a-9871-2c566ef2263d?action=stop -H 'Content-Type: text/occi' -H 'X-Auth-Token: '$KID -H 'X-Auth-Project-ID: 1' -H 'Category: stop; scheme="http://schemas.ogf.org/occi/infrastructure/compute/action#"; class="action"'
```

### Execute a Start Action Upon a VM
_Note: this will probably result in an error state. Currently looking into the issue._

>```curl -v -X POST localhost:8787/compute/888fc64a-4500-4543-bed4-8ddf3938dcb5?action=start -H 'Content-Type: text/occi' -H 'X-Auth-Token: '$KID -H 'X-Auth-Project-ID: 1' -H 'Category: start; scheme="http://schemas.ogf.org/occi/infrastructure/compute/action#"; class="action"'
```

### Delete a VM
>```curl -v -X DELETE localhost:8787/compute/d54b4344-16be-486a-9871-2c566ef2263d -H 'Content-Type: text/occi' -H 'X-Auth-Token: '$KID -H 'X-Auth-Project-ID: 1' 
```

### Create some a block storage volume
>```curl -v -X POST localhost:8787/storage/ -H 'Category: storage; scheme="http://schemas.ogf.org/occi/infrastructure#"; class="kind"' -H 'Content-Type: text/occi' -H 'X-Auth-Token: '$KID -H 'X-Auth-Project-ID: 1' -H 'occi.storage.size = 1.0'
```

### Link and associate that volume to the new instance
>```curl -v -X POST localhost:8787/storage/link/ -H 'X-Auth-Token: '$KID -H 'X-Auth-Project-ID: 1' -H 'Category: storagelink; scheme="http://schemas.ogf.org/occi/infrastructure#"; class="kind"' -H 'X-OCCI-Attribute: occi.core.source="http://localhost:8787/compute/e7a34bc4-02e7-43e3-a543-8aec630b5364"' -H 'X-OCCI-Attribute: occi.core.target="http://localhost:8787/storage/1"' -H 'X-OCCI-Attribute: occi.storagelink.mountpoint="/dev/vdb"' -H 'Content-Type: text/occi'```

### Unlink and disassociate that volume with the new instance
>```curl -v -X DELETE localhost:8787/storage/link/6cb97f63-7d8a-4474-87cb-4d1c9c581de1 -H 'X-Auth-Token: '$KID -H 'X-Auth-Project-ID: 1' -H 'Content-Type: text/occi'```

## Upcoming
### Update a VM: Scale up!
Let's bump the current instance from tiny (512) to a custom flavour (768R, 1C).
_Notes:_ 

* This is a partial update with respect to OCCI.
* This only works with Xen currently
  * otherwise it fails silently

>```curl -v -X POST localhost:8787/compute/2ee26373-db62-4bbf-9325-ff68a81097e3 -H 'Content-Type: text/occi' -H 'X-Auth-Token: '$KID -H 'X-Auth-Project-ID: 1' -H 'Category: m1.medium; scheme="http://schemas.openstack.org/template/resource#"; class="mixin"'
```

### Update a VM: Change the OS!
Let's use SmartOS as the new OS
_Notes:_ 

* this is in effect a partial update.

>```curl -v -X POST localhost:8787/compute/d54b4344-16be-486a-9871-2c566ef2263d -H 'Content-Type: text/occi' -H 'X-Auth-Token: '$KID -H 'X-Auth-Project-ID: 1' -H 'Category: SmartOS; scheme="http://schemas.openstack.org/template/os#"; class="mixin"'
```
