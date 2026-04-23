#!/bin/bash
# Make the Go1 lie down safely
# Run on Xavier NX (192.168.123.14)

echo "Sending STAND DOWN (mode 5)..."
cd ~/K1/build && ./sit_down 5
echo ""
echo "Robot should be lying down."
echo "Run ./damping.sh to fully release motors."
