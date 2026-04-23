#!/usr/bin/env bash
# start_oak_camera.sh — launch the OAK-D ROS driver on the Xavier NX (.15).
#
# Run from the Nano (.14, ROS master) or from your laptop if it can SSH to .15.
# The camera node runs on .15 and publishes topics back to the master at .14:11311.
#
# Verify from .14 after launch:
#   rostopic hz /oak/rgb/image_raw
#   rostopic hz /oak/stereo/image_raw
#
# To stop: pkill -f roslaunch  (on .15)

set -e

NX_HOST="${NX_HOST:-unitree@192.168.123.15}"
NX_PASS="${NX_PASS:-123}"
MASTER_URI="${MASTER_URI:-http://192.168.123.14:11311}"

echo "[oak] Launching camera node on $NX_HOST (master: $MASTER_URI)"

sshpass -p "$NX_PASS" ssh -o StrictHostKeyChecking=no "$NX_HOST" bash -c "'
  export ROS_MASTER_URI=$MASTER_URI
  export ROS_IP=192.168.123.15
  source /opt/ros/melodic/setup.bash
  source ~/catkin_ws/devel/setup.bash

  # Kill any previous camera node so we do not fight over the USB device
  pkill -f depthai_ros_driver 2>/dev/null || true
  sleep 1

  # Check the camera is physically present
  if ! lsusb | grep -q 03e7; then
    echo \"[oak] ERROR: OAK-D not detected on USB (vendor 03e7). Plug it in.\"
    exit 2
  fi

  nohup roslaunch depthai_ros_driver camera.launch camera_model:=OAK-D \
      > /tmp/oak_camera.log 2>&1 &

  echo \"[oak] roslaunch started, PID=\$!\"
  echo \"[oak] Log: /tmp/oak_camera.log on .15\"
'"

echo "[oak] Waiting 12 s for pipeline to come up…"
sleep 12

echo "[oak] Topic list (filtered to /oak/*):"
rostopic list 2>/dev/null | grep '^/oak/' || echo "  (no /oak topics yet — check /tmp/oak_camera.log on .15)"
