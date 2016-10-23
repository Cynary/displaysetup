#!/bin/bash
xrandr --output $MONITOR_0 --auto --primary
for i in {1..9} 0
do
    bspc desktop $i -m $MONITOR_0
done
bspc desktop -f 1
~/.fehbg
killall panel_bar.py 2> /dev/null
~/.local/panel/panel
sudo systemctl start wpa_supplicant@wlp3s0

# For the keyboard/mouse bt
#
sudo iw dev wlp3s0 set power_save on
xset s 300
