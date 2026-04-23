#!/bin/bash
# Start the Go1 Dashboard (cameras + sensors + graphs)
# Run this on Nano 4GB (192.168.123.14)
set -e

echo "=== Go1 Dashboard Launcher ==="

# Kill old instances
echo "[1/4] Killing old processes..."
pkill -f "python3.*tri_stream" 2>/dev/null || true
pkill -f "ffmpeg.*video" 2>/dev/null || true
sleep 2

# Free cameras from autostart
echo "[2/4] Freeing camera devices..."
pkill -f point_cloud_node 2>/dev/null || true
pkill -f mqttControlNode 2>/dev/null || true

# Free Nano camera too
echo "[3/4] Freeing Nano camera..."
sshpass -p 123 ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no unitree@192.168.123.15 \
    'pkill -f point_cloud_node 2>/dev/null; pkill -f ffmpeg 2>/dev/null' 2>/dev/null || true
sleep 2

# Start dashboard
echo "[4/4] Starting dashboard..."
nohup python3 ~/go1-autonomy-stack/dashboard/tri_stream.py > /tmp/tri_stream.log 2>&1 &
sleep 3

if pgrep -f "python3.*tri_stream" > /dev/null; then
    echo ""
    echo "Dashboard running at http://0.0.0.0:8080"
    echo ""
    echo "From your Mac, run:"
    echo "  ssh -f -N -L 8080:localhost:8080 unitree@192.168.123.14"
    echo "  open http://localhost:8080"
else
    echo "ERROR: Dashboard failed to start. Check /tmp/tri_stream.log"
    cat /tmp/tri_stream.log
fi
