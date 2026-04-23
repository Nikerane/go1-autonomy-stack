#!/bin/bash
# EMERGENCY: Release all motors (damping mode)
# Use when motors are overheating!
# Run on Xavier NX (192.168.123.14)

echo "!!! DAMPING MODE - Releasing all motors !!!"
cd ~/K1/build && ./sit_down 7
echo "Motors released. Robot will collapse if standing."
echo "Let motors cool before standing up again."
