:orphan:

sphinx-build manual page
========================

Synopsis
--------

**ilorest** [*GLOBAL OPTIONS*] [*COMMAND*] [*COMMAND OPTIONS*] [*COMMAND ARGUMENTS*]

Warning
-------

Improper use of this tool can result in the loss of critical data.
Only experienced users should attempt to use this tool.  Because
of the potential risk of data loss, take all necessary precautions
to ensure that mission-critical systems remain online if a
failure occurs.

Description
-----------

:program:`ilorest` is a command line tool which simplifies the process of
applying firmware for your HPE ProLiant server.   :program:`ilorest`
is designed for administrators looking to script and automate firmware
deployment.

:program:`ilorest` looks for firmware in the ``/usr/lib/<triplet>`` directory
where <triplet> is the multiarch triplet (http://wiki.debian.org/Multiarch)

When firmware is found :program:`ilorest` will guide you through the process
of applying it to your system.

In order to populate the ``/usr/lib/<triplet>`` directory you must
download and install HPE firmware packages from the
ProLiant Software Delivery Repository http://downloads.linux.hpe.com/SDR/ 

:program:`ilorest` includes integrated online help.  To access it run the
:program:`ilorest` command without any arguments.

Commands
--------

:program:`ilorest` utilizes a number of sub-commands to simplify usage.
Each sub-command accepts the its own set of options and arguments.
The sub-command specific options and arguments must must be specified
after the sub-command name.

help
^^^^

Display online help.  The help command without any argument displays
a list of commands.  help <command> displays help on the command provided.




