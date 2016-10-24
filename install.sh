# This is where the fifo is stored
mkdir /etc/event_fifos
# FIFO
mkfifo /etc/event_fifos/monitor.fifo
# Event handler
cp 99-monitor.rules /etc/udev/rules.d/
# Script run by the handler
cp monitor.sh /etc/event_fifos/
chmod +x /etc/event_fifos/monitor.sh
# Reload udev
udevadm control -R

# Put sleep script so that if you go from a closed docking
# position to single-monitor, it will detect the switch
cp notify_monitors.sh /usr/lib/systemd/systemd-sleep/
chmod +x /usr/lib/systemd/systemd-sleep/notify_monitors.sh
