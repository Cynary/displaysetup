#!/bin/bash

# Assuming we'll never get a hash of 0
# Do not put an empty string here, otherwise this won't work
#
results=$(mktemp)
STATE_HASH=0
DISPLAYS_CONFIG_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DISPLAYS_CONFIG_DIR
PATH=$PATH:"$DISPLAYS_CONFIG_DIR"

if [ $(pgrep -cx run.sh) -gt 0 ] ; then
    printf "%s\n" "The display script is already running, terminating old one." >&2
    for pid in $(pgrep run.sh)
    do
        if [ "$pid" != "$$" ]
        then
            kill $pid
        fi
    done
fi

new_state=$(mktemp)
echo false > $new_state
(while cat /etc/event_fifos/monitor.fifo; do echo true > $new_state; done) &

while true
do
    for ((i = 0; i < 30; i++))
    do
        PYTHONHASHSEED=0 check_state.py --old-state=$STATE_HASH -e > $results
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

    echo false > $new_state
    while ! $(cat $new_state); do sleep 1; done
done
