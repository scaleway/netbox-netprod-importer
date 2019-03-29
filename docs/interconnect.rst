.. _interconnect:

====================
Interconnect devices
====================


Once all network interfaces are created, the interconnection feature allows
to build a graph of some devices neighbours, and create an interconnection
between each other in Netbox. It is based on LLDP, CDP and napalm, plus some custom
parsers to get more informations that what is fetched by the napalm drivers.

The classic workflow is to start the interconnection after importing the
current states of the devices, so all network interfaces exist in Netbox.

.. contents:: Table of Contents
   :depth: 3


Usage
-----

The interconnections feature can be started through the subcommand
``interconnect``::

    usage: netbox-netprod-importer interconnect [-h] [-u USER] [-p] [-t THREADS] [-v LEVEL] DEVICES

    positional arguments:
      DEVICES               Yaml file containing a definition of devices to poll

    optional arguments:
      -h, --help            show this help message and exit
      -u USER, --user USER  user to use for connections to the devices
      -p, --password        ask for credentials for connections to the devices
      -t THREADS, --threads THREADS
                            number of threads to run
      --overwrite           overwrite data already pushed
      -v LEVEL, --verbose LEVEL
                            verbose output debug, info, warning, error and
                            critical, default: error

By default, connecting to the devices will use the default authentication
mechanism of the napalm driver, which is normally the current user and no
password/authentication by key. To change this behavior, the ``-u/--user`` and
``-p/--password`` options can be used to specify the user to use, and tells
netbox-netprod-importer to ask for the password to use.

The process is multithreaded, and split by device. The default number of
threads is 10, but can be changed with the ``-t/--threads`` option.

Interconnecting devices will not clean old connections in Netbox: if 2
interfaces are marked as connected in Netbox but are not detected as such
during the neighbour search, it will be kept as it is. This behavior can be
changed by enabling the ``--overwrite`` option, which will, on each scanned
device, clean all connections that have not been found.

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

    switch-3.foo.tld:
      driver: "nxos"
      discovery_protocol: "cdp"

    switch-4.foo.tld:
      driver: "nxos"
      discovery_protocol: "multiple"

To simply apply the import on these devices, do::

    $ netbox-netprod-importer interco ~/importer/devices.yml

Considering that the current user is named ``foo``, if a password is needed for
this user to connect to these devices, do::

    $ netbox-netprod-importer interco -p ~/importer/devices.yml

To use a different user, for example `bar` do::

    $ netbox-netprod-importer interco -u bar -p ~/importer/devices.yml

And to use more threads::

    $ netbox-netprod-importer interco -u bar -p -t 30 ~/importer/devices.yml


Configuration
-------------

For the import part, the configuration needed in your
:ref:`config file <quickstart_configuration>` is the following one::

    netbox:
      # Netbox API URL
      url: "https://netbox.tld/api"
      # username: "user"
      # password: "password"
      # or to use a token instead
      token: "CHANGEME"

    # On some devices, LLDP will expose the host FQDN. If devices are stored on
    # Netbox only by their hostname, the interconnection process will not be able
    # to find them. Fill this list to strip the domain name from exposed names.
    remove_domains:
      - "foo.tld"
      - "bar.tld"

The ``netbox`` section is used to get and push the fetched data from and to
Netbox. This block is self documented, and is used to get the Netbox API URL
and credentials.

As explained in the :ref:`LLDP section <interconnect_lldp>`, some tweaks
are done to maximize the neighbours finding. On some platform, the host
property inside LLDP is the fqdn when usually it contains only the hostname.
The ``remove_domains`` option is a list of domain names to workaround it, as
the interconnection algorithm will try to find the device in Netbox with and
without the domain name, if the host contains it.


Neighbours finding
------------------

.. _interconnect_lldp:

To discover neighbours connected to a device, LLDP is used. LLDP is a standard
protocol, but is quite permissive, and manufacturers do not all expose the same
information in each field. To maximize the information fetched about each
neighbour, some custom parsers are done :ref:`for fully supported platforms
<specific_parsers>`.

.. note::
  To maximize the neighbours finding, use the import on all devices. This
  way, if a neighbour cannot be find through a device, there is some chances
  that the discover from the neighbour will find this same device.

To find a neighbour on Netbox, the interconnect functions will connect to the
listed devices, then use LLDP to get the hostname exposed by the neighbour, its
network interface name and MAC address. Some platforms will try to interpret
the received values: for example, Cisco NXOS will add the domain name setup
inside the router to the hostname received by LLDP. So if your device expose
its fqdn, for example ``switch.bar.tld``, NXOS will transform it as
``switch.bar.tld.bar.tld`` if ``bar.tld`` is its domain name. This is why the
``remove_domains`` option has been written, in the
:ref:`config file <quickstart_configuration>`: if one domain listed in this
option is found in the neighbour hostname, it will try to search it in Netbox
without this domain name.

On some platforms, the network interface can be exposed via LLDP as aggregated.
For example, Cisco can show an interface named ``GigabitEthernet0/1`` as
``Ge0/1``, what can be an issue because netbox-netprod-importer actually
imports the full interface name (``GigabitEthernet0/1``). To help finding them
in Netbox, all possible form of interface names are written inside the custom
parsers, and are tested in case nothing is found.

When no interface name is exposed nor found, the interface can be searched
through the exposed MAC address. It can work in most cases, but be aware that
some devices can share the same MAC address on multiple interfaces: Cisco N9000
for example will have the same MAC address for all interfaces configured as
layer 2 only. If multiple interfaces are found on Netbox by trying to match on
their MAC address, the interconnection will fail, as the correct neighbour
interface cannot be determined. This feature is permitted by the specific
parsers, and platforms relying only on Napalm will not be able to do that.

Also, if you want to connect switches to servers (linux), and on bond servers
or team and in netbox you enter them with MAC addresses, the search will
return more than one value, and which is not known. Of course, you can check
the type of interface, but why if you can configure a normal return port_id.

Ansible task to configure::

  - name: configure lldpd
    lineinfile:
      dest: /etc/lldpd.conf
      line: "configure ports {{ item }} lldp portidsubtype local {{ item }}"
      state: present
      backup: yes
      create: yes
    when: hostvars[inventory_hostname]['ansible_%s' | format(item)]['module'] is defined
    loop: "{{ansible_interfaces }}"
    tags:
      - config_lldp
    notify: restart lldpd

Tested on RedHat 6 and 7, lldpd from EPEL repository.