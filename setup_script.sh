#!/bin/bash
script_name=$1
export $(PYTHONHASHSEED=0 ./check_state.py)
echo "$STATE_HASH $script_name" >> config
