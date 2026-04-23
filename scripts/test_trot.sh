#!/bin/bash
source /opt/ros/melodic/setup.bash
source ~/catkin_ws/devel/setup.bash
export ROS_MASTER_URI=http://192.168.123.14:11311
export ROS_IP=192.168.123.14

echo "[1] Killing old publishers..."
pkill -f "rostopic pub.*high_cmd" 2>/dev/null
sleep 1

echo "[2] Sending idle (mode=0) at 50Hz for 2s..."
rostopic pub -r 50 /high_cmd unitree_legged_msgs/HighCmd "{head: [254, 239], levelFlag: 238, mode: 0}" &
PID=$!
sleep 2
kill $PID 2>/dev/null
wait $PID 2>/dev/null

echo "[3] Sending trot (mode=2, vx=0.2) at 50Hz for 10s..."
rostopic pub -r 50 /high_cmd unitree_legged_msgs/HighCmd "{head: [254, 239], levelFlag: 238, mode: 2, gaitType: 1, velocity: [0.2, 0.0], yawSpeed: 0.0, footRaiseHeight: 0.08}" &
PID=$!
sleep 10
kill $PID 2>/dev/null
wait $PID 2>/dev/null

echo "[4] Sending idle (mode=0) to stop..."
rostopic pub -r 50 /high_cmd unitree_legged_msgs/HighCmd "{head: [254, 239], levelFlag: 238, mode: 0}" &
PID=$!
sleep 2
kill $PID 2>/dev/null
wait $PID 2>/dev/null

echo "[DONE] Test complete"
