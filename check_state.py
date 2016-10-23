#!/usr/bin/env python
import subprocess
import sys
import os

state_hash_to_script = {}
with open('config') as f:
    for l in f:
        state,script = l.strip().split()
        state = int(state)
        if state in state_hash_to_script:
            print("Repeated state %s in config file, with scripts %s and %s. "
                  "Using more recent entry %s." % (state, state_hash_to_script[state],
                  script, script))
        state_hash_to_script[state] = script

xrandr = subprocess.Popen(["xrandr", "--verbose"],
                          stdout=subprocess.PIPE, bufsize=0)
monitor_name = ''
edid = ''
edid_list = []
disconnected_monitors = []
DISCONNECTED_STATE_STRING='disconnected'
while True:
    try:
        line = xrandr.stdout.readline()
        # When process dies, we read an empty line
        #
        if (line == b''):
            break
        line = line.decode("utf-8")
        if (line[0] != '\t' and line[0] != ' '):
            monitor_name, state = line.split(' ')[:2]
            if (state == DISCONNECTED_STATE_STRING):
                disconnected_monitors.append(monitor_name)
        if (line.startswith('\tEDID:')):
            edid = ''
            line = xrandr.stdout.readline()
            line = line.decode("utf-8")
            while (line.startswith('\t\t')):
                edid += line.strip()
                line = xrandr.stdout.readline()
                line = line.decode("utf-8")
            edid_list.append((edid, monitor_name))
    except:
        # Ignore all exceptions, just throw some error
        #
        print("HERE?")
        sys.exit(1)

edid_list.sort()
state_hash = hash(tuple(i for i,_ in edid_list))
exec_string = ''
for i,(_,monitor) in enumerate(edid_list):
    exec_string += "MONITOR_%d=\"%s\" " % (i, monitor)

if (len(sys.argv) == 1):
    print("STATE_HASH=%d" % state_hash)
    print(exec_string)
elif sys.argv[1] == "fix_script":
    assert(len(sys.argv) == 3)
    with open(sys.argv[2]) as script:
        contents = script.read()
    for i,(_,monitor) in enumerate(edid_list):
        contents = contents.replace(monitor, "$MONITOR_%d" % i)
    with open(sys.argv[2], 'w') as script:
        script.write(contents)
elif state_hash in state_hash_to_script:
    print("STATE_HASH=%d" % state_hash)

    old_state = int(sys.argv[1])
    if (old_state != state_hash):

        print("RESULT=TRANSITION")
        os.system("%s ./%s" % (exec_string, state_hash_to_script[state_hash]))
        # Turn off all unplugged monitors
        #
        if (len(disconnected_monitors) != 0):
            off_string = 'xrandr '
            for m in disconnected_monitors:
                off_string += "--output %s --off " % m
            os.system(off_string)
    else:
        print("RESULT=REPEATED")
else:
    old_state = int(sys.argv[1])
    if (old_state == 0):
        print("STATE_HASH=%d" % state_hash)
    if (old_state == state_hash):
        print("RESULT=REPEATED")
    else:
        print("RESULT=UNKNOWN")
