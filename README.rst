==================================
Netbox network production importer
==================================

.. image:: https://travis-ci.org/Anthony25/netbox-netprod-importer.svg?branch=master
    :target: https://travis-ci.org/Anthony25/netbox-netprod-importer

netbox-netprod-importer in a tool dedicated to help moving your current
knowledge base to `Netbox <https://netbox.readthedocs.io/en/latest/>`_ as an
IPAM/DCIM, independently of your the current information system. It connects to
a given list of network devices and parse their status and configuration to
import them into Netbox like they are currently configured.

It is thought to be generic and infrastructure agnostic. It means that imported
data will probably need to be adapted by some custom scripts, like the
specification of roles, tennant and other properties on objects.


Used by `Online.net <https://www.online.net>`_ on more than 5000 network
devices.


Documentation
-------------

Documentation is available `here  <https://netboxnetimporter.readthedocs.io/>`_.


Features
--------

Device's data:
  - Fetch interfaces (physical & virtual):

    * Try to guess the interface form factor (more info in the documentation)
    * MTU
    * MAC Address
    * Description
    * Parent LAG
    * Enabled/Disabled
    * IPv4/IPv6

  - Serial number
  - Main IPv4/IPv6


Devices interconnections:
  - Build an interconnection graph by using LLDP to add (and optionally clean)
    interconnections between devices in Netbox


Compatibility
-------------

Tested on:

  - Cisco IOS (catalyst, 2960)
  - Cisco Nexus 9000
  - Cisco ASR (but no specific parser written, some features are not available)
  - Juniper


Installation
------------

Run::

  pip3 install netbox-netprod-importer

netbox-netprod-importer is tested under python 3.4 to 3.7


Contributors
------------

Tool initially developed by `Online.net  <https://www.online.net>`_ .

* Anthony Ruhier <anthony.ruhier@gmail.com>


License
-------

Tool under the GPLv3 license. Do not hesitate to report bugs, ask me some
questions or do some pull request if you want to!
