#!/bin/bash
# Stop all Go1 custom processes
# Run on Xavier NX (192.168.123.14)

echo "Stopping dashboard..."
pkill -f "python3.*tri_stream" 2>/dev/null || true
pkill -f "ffmpeg.*video" 2>/dev/null || true

echo "Stopping Nano ffmpeg relay..."
sshpass -p 123 ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no unitree@192.168.123.15 \
    'pkill -f ffmpeg 2>/dev/null' 2>/dev/null || true

echo "All custom processes stopped."
echo "Note: autostart processes (camerarosnode, sportMode) are NOT affected."
