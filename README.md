Automatic Display Docking Setup
===============================

Description
-----------

This collection of scripts allows you to associate a certain
configuration of displays with a script that sets them up
whichever way you like them best.

Install
-------

First, you need to install the scripts that will fire+handle
events. Run `install.sh` as root to install the `udev` rules
that will monitor displays getting added/removed. Read through
it to understand what it does, and also try using `udevadm monitor -p`
to make sure that the subsystem drm fires a CHANGE
event when a monitor is added/removed.

After the `udev` rule is installed, make sure the `run.sh`
script is started when your Window Manager is started (in my
case I am using `bspwm`, so I just put it in the `bspwmrc`
file).

Add a Display COnfiguration
---------------------------

* Create a script that correctly sets up the current
configuration. Store that script in the file `$SCRIPT_FILE`.
* Run `./setup_script.sh $SCRIPT_FILE` to register that script
with this configuration (note that the script can do more than
just setup the displays).
* Use `./fix_script.sh $SCRIPT_FILE` to generalize the script,
in case you decide to use different ports.

An example `$SCRIPT_FILE` is included for reference, called
`default.sh`
