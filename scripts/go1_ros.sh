#!/usr/bin/env bash
# go1_ros.sh — unified control entry point for the Unitree Go1 (ROS Melodic)
#
# Runs on the ROS master (Jetson Nano 4GB, 192.168.123.14).
# Replaces: stand_up.sh, sit_down.sh, damping.sh, test_trot.sh.
#
# Usage:
#   ./go1_ros.sh <subcommand>
#
# Subcommands:
#   damp     — release all motors (mode 7). Use when motors are hot or before shutdown.
#   sit      — stand down gently (mode 5).
#   stand    — force stand (mode 6).
#   idle     — idle stand (mode 0).
#   walk     — walk forward 10 s at vx=0.2 m/s, gaitType=1.
#   trot     — trot forward 10 s at vx=0.2 m/s, gaitType=2.
#   stop     — return to idle (mode 0) and kill any rostopic publishers.
#   status   — print battery %, mode, motor temps (hottest 3).
#
# Safety:
#   - Always prefer `damp` over a hard power-off when motors are warm (>70 °C).
#   - The robot must be on flat ground before `stand`.
#   - Keep a hand near the main power switch during first trot/walk tests.

set -e

source /opt/ros/melodic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
export ROS_MASTER_URI=http://192.168.123.14:11311
export ROS_IP=192.168.123.14

SDK_BIN="$HOME/K1/build/sit_down"

die() { echo "[go1_ros] $*" >&2; exit 1; }

[[ -x "$SDK_BIN" ]] || die "Missing $SDK_BIN — build with: cd ~/K1/build && cmake .. && make sit_down"

kill_pub() {
  pkill -f "rostopic pub.*high_cmd" 2>/dev/null || true
}

publish_highcmd() {
  # $1 = duration in seconds, rest = yaml for HighCmd
  local duration="$1"; shift
  kill_pub
  rostopic pub -r 50 /high_cmd unitree_legged_msgs/HighCmd "$*" &
  local pid=$!
  sleep "$duration"
  kill "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
}

case "${1:-}" in
  damp)
    echo "[go1_ros] Damping — motors released."
    "$SDK_BIN" 7
    ;;
  sit)
    echo "[go1_ros] Standing down (mode 5)."
    "$SDK_BIN" 5
    ;;
  stand)
    echo "[go1_ros] Force stand (mode 6)."
    "$SDK_BIN" 6
    ;;
  idle)
    echo "[go1_ros] Idle (mode 0)."
    "$SDK_BIN" 0
    ;;
  walk)
    echo "[go1_ros] Walk forward 10 s @ vx=0.2, gaitType=1"
    publish_highcmd 2  "{head: [254, 239], levelFlag: 238, mode: 0}"
    publish_highcmd 10 "{head: [254, 239], levelFlag: 238, mode: 2, gaitType: 1, velocity: [0.2, 0.0], yawSpeed: 0.0, footRaiseHeight: 0.08}"
    publish_highcmd 2  "{head: [254, 239], levelFlag: 238, mode: 0}"
    ;;
  trot)
    echo "[go1_ros] Trot forward 10 s @ vx=0.2, gaitType=2"
    publish_highcmd 2  "{head: [254, 239], levelFlag: 238, mode: 0}"
    publish_highcmd 10 "{head: [254, 239], levelFlag: 238, mode: 2, gaitType: 2, velocity: [0.2, 0.0], yawSpeed: 0.0, footRaiseHeight: 0.08}"
    publish_highcmd 2  "{head: [254, 239], levelFlag: 238, mode: 0}"
    ;;
  stop)
    kill_pub
    publish_highcmd 2  "{head: [254, 239], levelFlag: 238, mode: 0}"
    echo "[go1_ros] Stopped — idle."
    ;;
  status)
    echo "[go1_ros] Listening on /high_state for 2 s…"
    timeout 2 rostopic echo -n1 /high_state 2>/dev/null | \
      awk '/^bms:/{bms=1} bms && /SOC:/{print "Battery SOC: "$2"%"; bms=0}
           /^motorState:/{ms=1; idx=0} ms && /temperature:/{t[idx]=$2; idx++}
           END{
             if(idx>0){
               n=asort(t); print "Hottest motors: "t[n]"°C, "t[n-1]"°C, "t[n-2]"°C";
             }
           }' || echo "(no HighState — is the Pi + MCU online?)"
    ;;
  ""|help|-h|--help)
    grep '^#' "$0" | head -30
    ;;
  *)
    die "Unknown subcommand: $1 (try: damp, sit, stand, walk, trot, stop, status)"
    ;;
esac
