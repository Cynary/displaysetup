#!/usr/bin/env python
import subprocess
import sys
import os
import argparse

SCRIPT_NAME=""
state_hash_to_script = None
edid_list = None
disconnected_monitors = None
connected_monitors = None
state_hash = None
prefix_exec = None
options = None

class ProcessReader:
    TERM_WAIT=150
    def __init__(self, exec_string):
        self.process = subprocess.Popen(exec_string.split(' '),
                                        stdout=subprocess.PIPE, bufsize=0)

    def __iter__(self):
        return self

    def __next__(self):
        line = self.process.stdout.readline()
        # When process dies, we read an empty line
        #
        if (line == b''):
            raise StopIteration
        return line.decode("utf-8")

    def __del__(self):
        self.process.terminate()
        try:
            outs, errs = self.process.communicate(timeout=self.TERM_WAIT)
        except TimeoutExpired:
            self.process.kill()
            outs, errs = self.process.communicate()

def parse_opt():
    global options, SCRIPT_NAME
    parser = argparse.ArgumentParser(description="Get current display state, and perform "
                                     "actions as instructed.")
    parser.add_argument('-c', '--config', type=str, default='config',
                        help="Config file location (default: config)")
    parser.add_argument('-f', '--fix-file', type=str, default=None,
                        help="Fix a script file, replacing monitor name occurrences with "
                        "MONITOR_N variables to allow for execution by %s" % SCRIPT_NAME)
    parser.add_argument("-e", "--execute", action='store_true', default=False,
                        help="If set, executes the script in the config file matching the "
                        "current state.")
    parser.add_argument("-o", "--old-state", type=int, default=None,
                        help="Previous state, does not execute anything if the state hasn't"
                        " changed, just outputs the state hash, and RESULT=REPEATED")
    parser.add_argument("-d", "--dry-run", action='store_true', default=False,
                        help="If set, it will not execute any commands, just print out what"
                        " commands it would execute.")
    options = parser.parse_args()

def syscall(exec_string):
    global options
    assert options is not None
    if options.dry_run:
        print(exec_string)
    else:
        os.system(exec_string)


#-------------------------------------------------------------------------------------------
# Function `process_config`
#
# Description:
#
#  Goes through the config file, and builds a map from state hashes (a state hash is built
#  from the collection of monitor edids to identify a specific monitor setup) to scripts to
#  run when those states are transitioned into.
#
#  A config file is expected to have one line per state hash->script mapping, and each line
#  contains the state hash followed by the script name, and they are separated by spaces.
#
# Parameters:
#
#  `config_file` - file name which contains the configuration.
#
def process_config(config_file):
    global state_hash_to_script, SCRIPT_NAME
    assert state_hash_to_script is None, "Can only process one config per %s run" % SCRIPT_NAME

    state_hash_to_script = {}
    with open(config_file) as f:
        for l in f:
            state,script = l.strip().split()
            state = int(state)
            if state in state_hash_to_script:
                print("Repeated state %s in config file, with scripts %s and %s. "
                      "Using more recent entry %s." % (state, state_hash_to_script[state],
                                                       script, script))
            state_hash_to_script[state] = script

#-------------------------------------------------------------------------------------------
# Function `get_monitors`
#
# Description:
#
#  Runs "xrandr --verbose" to figure out which monitors exist in the system, which are
#  disconnected, which are connected, and what their edids are.
#
#  It populates the global state `edid_list`, `disconnected_monitors`, and
#  `connected_monitors` with that information. `connected_monitors` is further intersected
#  with `bspc query -M --names`
#
def get_monitors():
    global edid_list, disconnected_monitors, connected_monitors, SCRIPT_NAME

    only_once = "Can only obtain display information once per %s run" % SCRIPT_NAME
    assert edid_list is None, only_once
    assert disconnected_monitors is None, only_once
    assert connected_monitors is None, only_once
    edid_list = []
    disconnected_monitors = []
    connected_monitors = []

    DISCONNECTED_STATE_STRING='disconnected'
    xrandr = ProcessReader("xrandr --verbose")
    for line in xrandr:
        if (line[0] != '\t' and line[0] != ' '):
            monitor_name, state = line.split(' ')[:2]
            if (state == DISCONNECTED_STATE_STRING):
                disconnected_monitors.append(monitor_name)
            else:
                connected_monitors.append(monitor_name)
        if (line.startswith('\tEDID:')):
            edid = ''
            line = next(xrandr)
            while (line.startswith('\t\t')):
                edid += line.strip()
                line = next(xrandr)
            edid_list.append((edid, monitor_name))

    bspc_monitors = set(m.strip() for m in ProcessReader("bspc query -M --names"))
    connected_monitors = [m for m in connected_monitors if m in bspc_monitors]
    assert len(connected_monitors) > 0, "WTF? This can only succeed if it has more than 1 monitor"

#-------------------------------------------------------------------------------------------
# Function `compute_current_state`
#
# Description:
#
#  Using the information obtained from `get_monitors` (specifically the `edid_list`) it
#  computes a unique repeatable hash for the current state (it assumes `PYTHONHASHSEED` is
#  kept constant by the caller)
#
#  It also creates the `prefix_exec` string which is used to identify monitors in a unique
#  repeatable order to the scripts this program runs.
#
def compute_current_state():
    global edid_list, state_hash, prefix_exec

    assert edid_list is not None, "Must call `get_monitors` first"
    assert state_hash is None, "Can only compute the state hash once per %s run" % SCRIPT_NAME
    assert prefix_exec is None, "Can only compute the state hash once per %s run" % SCRIPT_NAME

    edid_list.sort()
    state_hash = hash(tuple(i for i,_ in edid_list))

    prefix_exec = ""
    for i,(_,monitor) in enumerate(edid_list):
        prefix_exec += "MONITOR_%d=%s " % (i, monitor)

#-------------------------------------------------------------------------------------------
# Function `fix_script`
#
# Description:
#
#  Replaces occurrences of monitor names in the script with "$MONITOR_N" so that the script
#  can be run consistently regardless of which ports the monitors are connected to.
#
def fix_script(script_file):
    with open(script_file) as script:
        contents = script.read()
    id_monitor = [(i, monitor) for i,(_,monitor) in enumerate(sorted(edid_list))]
    # Backwards sort these by length so that longer words get replaced first. That way,
    # monitor names that are longer and contain shorter monitor names (e.g. eDP1 is longer
    # than and contains DP1 and are two plausible monitor names) get replaced first (if not,
    # and we replaced DP1 first, then eDP1 would be transformed into eMONITOR_N).
    #
    id_monitor.sort(key=lambda x: -len(x[1]))

    for i,monitor in id_monitor:
        contents = contents.replace(monitor, "$MONITOR_%d" % i)

    with open(sys.argv[2], 'w') as script:
        script.write(contents)

#-------------------------------------------------------------------------------------------
# Function `execute_script`
#
# Description:
#
#  Called to execute the script associated with the current `state_hash` value. If the
#  script does not exist, then it will output "RESULT=UNKNOWN" for the caller. If the script
#  exists, then it will output "RESULT=TRANSITION" for the caller, and:
#
#  - turn all disconnected monitors off via "xrandr"
#
#  - move all desktops in non-connected monitors to a connected monitor.
#
#  - remove all non-connected monitors from "bspwm"
#
#  - execute the script from `state_hash_to_script`
#
def execute_script():
    global state_hash, state_hash_to_script, disconnected_monitors, connected_monitors
    global prefix_exec
    assert state_hash is not None
    assert state_hash_to_script is not None
    assert state_hash != options.old_state
    if state_hash in state_hash_to_script:
        print("RESULT=TRANSITION")

        # Turn off all disconnected monitors via xrandr
        #
        if (len(disconnected_monitors) != 0):
            off_string = 'xrandr '
            for m in disconnected_monitors:
                off_string += "--output %s --off " % m
            syscall("%s &> /dev/null" % off_string)

        # Move all desktops in non-connected monitors to a connected monitor in bspwm
        #
        bspc_disconnected_monitors = [m.strip() for m in ProcessReader("bspc query -M --names") \
                                      if m.strip() not in connected_monitors]
        assert len(connected_monitors) > 0
        destination_monitor = connected_monitors[0]
        for m in bspc_disconnected_monitors:
            for d in ProcessReader("bspc query -D -m %s" % m):
                syscall("bspc desktop %s -m %s" % (d.strip(),destination_monitor))
            # Now that all its desktops have been safely moved, remove it.
            #
            syscall("bspc monitor %s -r" % m)

        # Finally, execute the script
        #
        syscall("%s ./%s &> /dev/null" % (prefix_exec, state_hash_to_script[state_hash]))
    else:
        print("RESULT=UNKNOWN")

def main(argv):
    global SCRIPT_NAME, options, state_hash, prefix_exec
    SCRIPT_NAME = argv[0]
    parse_opt()
    process_config(options.config)
    get_monitors()
    compute_current_state()

    # Always return these variables to the caller
    #
    assert state_hash is not None
    assert prefix_exec is not None
    print("STATE_HASH=%d" % state_hash)
    print(prefix_exec)

    if options.fix_file is not None:
        fix_script(options.fix_file)
    if options.execute and options.old_state != state_hash:
        execute_script()

    if options.old_state == state_hash:
        print("RESULT=REPEATED")

if __name__ == "__main__":
    main(sys.argv)
