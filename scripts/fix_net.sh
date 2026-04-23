#!/bin/bash
echo 123 | sudo -S nmcli connection modify "Otto51 1" ipv4.dns "8.8.8.8 8.8.4.4" ipv4.ignore-auto-dns yes
echo 123 | sudo -S nmcli connection modify "Otto51 1" ipv4.route-metric 100
echo 123 | sudo -S nmcli connection down "Otto51 1"
sleep 2
echo 123 | sudo -S nmcli connection up "Otto51 1"
sleep 4
echo 123 | sudo -S ip neigh replace 192.168.178.1 lladdr e0:08:55:eb:6b:6d dev wlan0 nud permanent
echo 123 | sudo -S ip route del default via 192.168.123.161 dev eth0 2>/dev/null || true
ping -c2 8.8.8.8 && echo "Internet OK"
