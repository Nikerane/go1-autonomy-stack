#!/bin/bash
# Make the Go1 stand up
# Run on Xavier NX (192.168.123.14)

echo "Sending STAND UP (mode 6)..."
cd ~/K1/build && ./sit_down 6
echo "Robot should be standing up."
