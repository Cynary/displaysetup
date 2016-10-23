#!/bin/bash

# Assuming we'll never get a hash of 0
# Do not put an empty string here, otherwise this won't work
#
results=$(mktemp)
STATE_HASH=0
DISPLAYS_CONFIG_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DISPLAYS_CONFIG_DIR
echo $DISPLAYS_CONFIG_DIR
PATH=$PATH:"$DISPLAYS_CONFIG_DIR"

while true
do
    for ((i = 0; i < 30; i++))
    do
        PYTHONHASHSEED=0 check_state.py $STATE_HASH > $results
        source $results
        echo $RESULT $STATE_HASH
        if [ "$RESULT" != "REPEATED" ]
        then
            break
        fi
        sleep 1
    done
    if [ "$RESULT" = "TRANSITION" ]
    then
        echo "Just transitioned state, and applied script"
    elif [ "$RESULT" = "UNKNOWN" ]
    then
        echo "Just got into an unknown state"
    elif [ "$RESULT" = "REPEATED" ]
    then
        echo "Just got into the same state as before, no changes"
    fi

    dd if=/etc/event_fifos/monitor.fifo iflag=nonblock of=/dev/null &> /dev/null
    cat /etc/event_fifos/monitor.fifo &> /dev/null
done
