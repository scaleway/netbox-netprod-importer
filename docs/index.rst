Welcome to Netbox netprod importer's documentation!
===================================================

netbox-netprod-importer is a tool dedicated to help reflecting your production
in `Netbox <https://netbox.readthedocs.io/en/latest/>`_ as an IPAM/DCIM,
independently of your information system. It connects to a given list of
network devices and parse their status and configuration to import them into
Netbox like they are currently configured.

It is thought to be generic and infrastructure agnostic. It means that imported
data will probably need to be adapted by some custom scripts, like the
specification of roles, tennant and other properties on objects.

To be the most platform agnostic as possible, data are fetched through
`Napalm <https://napalm.readthedocs.io/en/latest/>`_, with some custom parsers
when more info are needed.

Used by `Online.net <https://www.online.net>`_ on more than 5000 network
devices.


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   quickstart
   import
   interconnect
   specific_parsers

Indices and tables
==================
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
