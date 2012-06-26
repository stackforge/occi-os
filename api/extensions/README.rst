Copyright (c) 2012, Intel Performance Learning Solutions Ltd.

============================
Creating OCCI Extensions
============================

To create OCCI extensions:

1. Define the method to retreive all extension information. This method
**must** have the following signature:

  ``def get_extensions()``

  It **must** return a list. That list **must** contain at least one dict.
  The dict **must** contain a pyssf backend handler. The dict **must** also
  contain a list of OCCI Categories that are handled by the pyssf backend
  handler. The OCCI Categories and pyssf backend handler **should** be
  defined in the same python file.

2. Define the extension categories. Depending on your needs you can define
Kind, Mixin, Link or Action extensions.

3. Define the extension handler(s).

Examples of OCCI extensions can be found in the same directory as this README
file.

* ``fiware.py`` - this includes a very basic extension.

* ``occi_future.py`` - this includes extensions that are considered as
  future OCCI-WG extensions.

* ``openstack.py`` - this includes various OpenStack specific extensions.

All extensions are enumerated via ``__init__.py`` and loaded via ``wsgi.py``.
