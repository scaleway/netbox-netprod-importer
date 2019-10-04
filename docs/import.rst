.. _import:

===================
Import devices data
===================


The importer goal is to import the state and data of a network device. It is
not meant to create a device or magically rack it, but to populate it as it is
currently configured. It is based on `Napalm <https://napalm.readthedocs.io>`_
to be platform agnostic, when possible, but uses some custom specific parsers
when needed.


.. contents:: Table of Contents
   :depth: 3


Create a device in Netbox
-------------------------

Before importing the data of a device, it should be created in Netbox.
netbox-netprod-importer will not create a device for the user, as it is
difficult to do so by staying infrastructure agnostic. It just needs a
hostname and all fields required by Netbox, the rest being part of the listed
features will be populated by netbox-netprod-importer.


Usage
-----

An import can be started through the subcommand ``import``::

    usage: netbox-netprod-importer import [-h] [-u user] [-p] [-t THREADS] [--overwrite] [-v LEVEL] [ -f DEVICES | -F FILTER ]

    arguments:
      -f devices, --file devices
                            Yaml file containing a definition of devices to poll
      or
      -F FILTER, --filter FILTER
                            Yaml file containing the device definition filter for polling from NetBox

    optional arguments:
      -h, --help            show this help message and exit
      --overwrite           overwrite devices already pushed
      -u user, --user user  user to use for connections to the devices
      -p, --password        ask for credentials for connections to the devices
      -P PASSWORD, --Password PASSWORD
                            credentials for connections to the devices
      -t THREADS, --threads THREADS
                            number of threads to run
      -v LEVEL, --verbose LEVEL
                            verbose output debug, info, warning, error and
                            critical, default: error

By default, connecting to the devices will use the default authentication
mechanism of the napalm driver, which is normally the current user and no
password/authentication by key. To change this behavior, the ``-u/--user`` and
``-p/--password|-P/--Password`` options can be used to specify the user to use, and tells the
importer to ask|set for the password to use.

The import is multithreaded, and split by device. The default number of threads
is 10, but can be changed with the ``-t/--threads`` option.

Importing a device will replace the current data in Netbox, but not clean (by
default) what has not been found by fetching the device state. If a device is
already populated in Netbox, network interfaces already added but not found
during the import will not be cleaned, same as the IP addresses that do not
seem to be configured anymore. This behavior can be changed by enabling the
``--overwrite`` option, which will clean all interfaces and IP that have not been
found during the import.

Toggle the verbose mode with the ``-v/--verbose  LEVEL`` option to get a more
verbose output. Default error.

The ``devices`` parameter is a yaml file, representing the devices list to
import, as detailed :ref:`here <quickstart_device_list>`.


Example
~~~~~~~

Considering a yaml file ``~/importer/devices.yml`` containing these devices::

    switch-1.foo.tld:
      driver: "nxos_ssh"

    switch-2.bar.tld:
      driver: "junos"
      target: "192.0.2.3"

To simply apply the import on these devices, do::

    $ netbox-netprod-importer import -f ~/importer/devices.yml

Considering that the current user is named ``foo``, if a password is needed for
this user to connect to these devices, do::

    $ netbox-netprod-importer import -p -f ~/importer/devices.yml

To use a different user, for example `bar` do::

    $ netbox-netprod-importer import -u bar -p -f ~/importer/devices.yml

And to use more threads and enable the overwrite mode to get a clean clone of a
device state::

    $ netbox-netprod-importer import -u bar -p -t 30 --overwrite -f ~/importer/devices.yml

Considering a yaml file ``~/importer/filter.yml`` containing this filter::

    discovery_protocol:
        ios: cdp
        nxos: multiple
        nxos_ssh: multiple
        junos: lldp

    filter:
        q:
        region:
            - england
        site:
            - london
            - birmingham
        rack:
        status: 1
        role:
        tenant_group:
        tenant:
            - it
        manufacturer:
            - cisco
        device_type:
        mac_address:
        has_primary_ip: True
        platform:
        virtual_chassis_member:
        console_ports:
        console_server_ports:
        power_ports:
        power_outlets:
        interfaces:
        pass_through_ports:

Full online documentation on filter keys is available on a running NetBox instance
in /api/docs/, section GET /dcim/devices/

We will choose London and birmingham sites in England, the equipment is active,
the owner is it, the manufacturer is cisco and has a primary ip::

    $ netbox-netprod-importer import -u bar -p -t 30 --overwrite -F ~/importer/filter.yml

Configuration
-------------

For the import part, the only configuration needed in your
:ref:`config file <quickstart_configuration>` is the following one::

    netbox:
      # Netbox API URL
      url: "https://netbox.tld/api"
      # username: "user"
      # password: "password"
      # or to use a token instead
      token: "CHANGEME"


It is used to get and push the fetched data from and to Netbox. This block
is self documented, and is used to get the Netbox API URL and credentials.


Data imported
-------------

.. _import_data_imported:

The importer fetch the following type of data:

  - Network interfaces (physical & virtual):

    * Try to guess the interface form factor
    * MTU
    * MAC Address
    * Description
    * Parent LAG
    * Enabled/Disabled
    * IPv4/IPv6
    * Vlan (only cisco equipment)
    * 802.1Q Mode (only cisco equipment)

  - Serial number
  - Main IPv4/IPv6


Interface form factor
~~~~~~~~~~~~~~~~~~~~~

netbox-netprod-importer can find the form factor by fetching it from the device
and by selecting the matching type on Netbox. A form factor can be for example
1000Base-T, SFP, SFP+, etc.

To correctly detect the interface type, the platform of the targetted device
needs to be fully supported by the importer. Some parsers are written to get
more info than what napalm allows (read :ref:`the documentation about specific
parsers <specific_parsers>` for more details), and are used by the importer.

When an interface type can be fetched from a device, it has then to be
translated as a type expected by Netbox. To do so, a list of regexp
are written to help for the mapping. This list is certainly incomplete, so
someone seeing an unhandled case is welcomed to open an issue about it.


IP addresses and VRF
~~~~~~~~~~~~~~~~~~~~

IP addresses configured on an interface are imported and attached to this
interface in Netbox. If an IP already exists in Netbox, it is used it
and assigned it to the correct interface. If an IP does not already exist,
it is created and assigned to the interface.

.. warning::
  This behavior can be an issue with anycasted ip addresses.

When an IP is part of a VRF, the VRF cannot be guessed from Netbox. As multiple
VRF can be declared with the same name but a different route distinguisher, it
is not easier to get the correct one and staying infrastructure agnostic. That
is the reason why created IP are not assigned to any VRF. Scripts can be use to
move them after the import, but the import will let the responsability on the
user to do it.

.. warning::
  Be aware that some Napalm drivers do not handle well the notion of VRF.
  Getting the IP addresses of an interface will sometimes be limited to the
  default VRF.

  Pull requests are opened on Napalm to fix it:
    - https://github.com/napalm-automation/napalm/pull/815
    - https://github.com/napalm-automation/napalm/pull/819
