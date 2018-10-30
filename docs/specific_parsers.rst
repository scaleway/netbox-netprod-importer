.. _specific_parsers:

=========================================
Compatibility and specific custom parsers
=========================================

Compatibility
-------------

The platforms of the targeted network devices have to be compatible with
Napalm. A list of drivers can be found
`here <https://napalm.readthedocs.io/en/latest/support/index.html>`_.

Napalm, however, does not support all features needed by
netbox-netprod-importer. Because of that, some specific parsers have been
written to either get more data or enhanced some features to improve the
import.

netbox-netprod-importer has been tested on:
  - Cisco IOS (catalyst, 2960)
  - Cisco Nexus 9000
  - Cisco ASR
  - JunOS devices


List of specific parsers
------------------------

They can be found in ``netbox_netprod_importer/vendors/``. Fully supported
devices are:

  - Cisco IOS (catalyst, 2960)
  - Cisco Nexus 9000
  - JunOS devices


Napalm only features
--------------------

When targetting a device which does not have a specific parser, the import is
based on Napalm only. In that situation, here is a list of supported features:


Data import
~~~~~~~~~~~

+-----------------+-----------+
| Feature         | Supported |
+=================+===========+
| Serial number   | True      |
+-----------------+-----------+
| Main IPv4/IPv6  | True      |
+-----------------+-----------+

Network interfaces
^^^^^^^^^^^^^^^^^^

+-----------------------------------------+-----------+
| Feature                                 | Supported |
+=========================================+===========+
| Guess the interface form factor:        | False     |
+-----------------------------------------+-----------+
| MTU                                     | True      |
+-----------------------------------------+-----------+
| MAC Address                             | True      |
+-----------------------------------------+-----------+
| Description                             | True      |
+-----------------------------------------+-----------+
| Parent LAG                              | False     |
+-----------------------------------------+-----------+
| Enabled/Disabled                        | True      |
+-----------------------------------------+-----------+
| IPv4/IPv6                               | True      |
+-----------------------------------------+-----------+


Interconnect
~~~~~~~~~~~~

Specific parsers will fetch the MAC address of each interface, to maximize
the finding when the interface name or hostname cannot be found on Netbox.
They also yield a list of alternative names for an interface, allowing to
deal with aggregated names.
