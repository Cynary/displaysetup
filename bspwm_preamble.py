#!/usr/bin/python

# This script is used to cleanup the bspwm state before any of the display scripts start
# getting executed (it is supposed to be called from display scripts on bspwm).
#
# Separated it from `check_state.py` because that script was always intended to be
# independent of window manager.
#

import os
import argparse
from check_state import ProcessReader

options = None

def syscall(exec_string):
    global options
    assert options is not None
    if options.dry_run:
        print(exec_string)
    else:
        os.system(exec_string)

class RangeStopWhen:
    def __init__(self, condition):
        self.condition = condition
        self.i = -1

    def __iter__(self):
        return self

    def __next__(self):
        self.i = self.i+1
        if (self.condition(self.i)):
            raise StopIteration
        else:
            return self.i

#-------------------------------------------------------------------------------------------
# Function `get_connected_monitors`
#
# Description:
#
#  Returns a list of all the connected monitors based on an analysis of the calling
#  environment. Note: when `check_state.py` calls the state assigned scripts it will set
#  MONITOR_N variables, where N=0,1,... for every monitor. Thus, that is used to determine
#  which monitors are connected.
#
# Parameters:
#
#  `env` - dictionary describing the environment this script was called in.
#
# Returns a list of all the connected monitors
#
def get_connected_monitors(env):
    return [env["MONITOR_%d" % i] for i in RangeStopWhen(lambda i: "MONITOR_%d" % i not in env)]

#-------------------------------------------------------------------------------------------
# Function `parse_opt`
#
# Description:
#
#  Parses command line options using argparse. Possible options are:
#
#  - dry_run: runs a dry run in which no side effecting commands are executed, but instead
#    are printed out (defaults to `False`).
#
#  - help: prints a helpful guide message and quits.
#
# Returns an object with each option as a member, set to the passed in command line option.
#
def parse_opt():
    parser = argparse.ArgumentParser(description="Cleanup the state of bspwm by moving "
                                     "desktops to connected monitors, and removing "
                                     "disconnected monitors.")
    parser.add_argument("-d", "--dry-run", action='store_true', default=False,
                        help="If set, it will not execute any commands, just print out what"
                        " commands it would execute.")
    return parser.parse_args()

def cleanup_bspwm():
    connected_monitors = get_connected_monitors(os.environ)
    assert len(connected_monitors) > 0, "Can't do much without at least one active monitor"
    disconnected_monitors = [m.strip() for m in ProcessReader("bspc query -M --names") \
                             if m.strip() not in connected_monitors]
    destination_monitor=connected_monitors[0]
    for m in disconnected_monitors:
        for d in ProcessReader("bspc query -D -m %s" % m):
            syscall("bspc desktop %s -m %s" % (d.strip(),destination_monitor))
        # Now that all its desktops have been safely moved, remove it.
        #
        syscall("bspc monitor %s -r" % m)

def main():
    global options
    options = parse_opt()
    cleanup_bspwm()

if __name__ == "__main__":
    main()
