# 07 — Troubleshooting

Issues we've hit and how to recover. Organised by symptom.

---

## Network

### Laptop can't reach `.14` from macOS

Symptom: `ping 192.168.123.14` times out; `ping 192.168.123.100` says "sendto: Host is down".

Cause: macOS assigned `192.168.123.100` to multiple interfaces (WiFi, Thunderbolt-bridge, USB-ethernet) and picked the wrong one.

Fix:

```bash
ifconfig | grep -B5 "192.168.123.100"
sudo ifconfig en0 -alias 192.168.123.100     # WiFi
sudo ifconfig en3 -alias 192.168.123.100     # Thunderbolt bridge
sudo route add -net 192.168.123.0/24 -interface en6   # your real ethernet
route -n get 192.168.123.14                  # confirms interface
```

Reboot wipes this. See [02-network.md](02-network.md).

### `.15` loses internet after running for an hour

Symptom: `apt update` hangs, `pip install` times out. `ping 8.8.8.8` fails. `ping 192.168.123.14` still works.

Cause: RTL8192CU WiFi dongle driver silently drops unicast packets after some time.

Fix:

```bash
ssh unitree@192.168.123.15
cd ~/go1-autonomy-stack
./scripts/fix_net.sh
```

### Port 8090 conflict

Symptom: `Legged_sport` on the Pi won't start, or `ros_udp` prints `bind: Address already in use`.

Cause: `ros_udp`, `base_ctrl`, and a few factory SDK binaries all want UDP :8090 on the Pi.

Fix:

```bash
ssh -J unitree@192.168.123.14 pi@192.168.123.161
sudo netstat -tulnp | grep 8090
# kill whichever PID is squatting; restart Legged_sport
sudo systemctl restart legged_sport    # or the factory init script
```

---

## Walking / motors

### `./scripts/go1_ros.sh stand` — nothing happens

Check in order:

1. `ping 192.168.123.161` — is the Pi up?
2. `./scripts/go1_ros.sh status` — does HighState print at all? If not, Pi's `Legged_sport` is down.
3. `ls ~/K1/build/sit_down` on `.14` — binary missing? rebuild K1.
4. Remote controller — if someone has the remote in "soft emergency stop," the MCU ignores `/high_cmd`. Release it.

### Motors overheat during tuning

Symptom: `go1_ros.sh status` shows motor temps ≥ 70 °C; trot feels sluggish.

Fix: `./scripts/go1_ros.sh damp` and wait 5–10 min. Rear hips take the longest to cool. Don't power-cycle — the damping state is the safest cooling position.

Prevention: keep sessions short (< 2 min active walking), batteries ≥ 50 %, bench supply at 24 V / 20 A if doing back-to-back tests.

### Loud click on shutdown

You pulled the battery while motors were still energised. The FETs handle it but you're stressing them. Always `./scripts/go1_ros.sh damp` first, then power off.

---

## OAK-D camera

### `Cannot load blob, file doesn't exist`

`i_nn_type` is still `"spatial"` somewhere. Check:

```bash
ssh unitree@192.168.123.15
grep nn_type ~/catkin_ws/src/depthai-ros/depthai_ros_driver/config/camera.yaml
```

Must say `none`. If it says `spatial`, re-apply patch 6 in [06-depthai-ros-mods.md](06-depthai-ros-mods.md) and redeploy `config/camera.yaml`.

### `Cannot find any device`

```bash
ssh unitree@192.168.123.15
lsusb | grep 03e7
```

If nothing: cable unplugged or dead. Reseat USB-C.
If `03e7:2485` only (never flips to `f63b`): firmware push failing — try a different USB port / cable. USB-C → USB-A cables are especially flaky.

### Camera stuck at 10 Hz

Known issue. OAK-D negotiates USB 2.0 on the Xavier's USB-C port; we expect USB 3.0 (~30 Hz). Diagnosis so far:

```bash
lsusb -t   # shows Movidius at 480M (USB 2.0), not 5000M (USB 3.0)
```

Swapping cables and ports on the Xavier hasn't helped. Candidate causes: carrier-board USB 3 lane not wired, kernel driver on Xavier NX devkit, or the OAK-D's USB-C cable is 2.0-only. Not blocking M3 (SLAM works fine at 10 Hz). Leave it for the next student to investigate.

### IMU firmware warning at startup

```
[WARN] BNO086 firmware 3.2.13, expected 3.2.14
```

Safe to ignore. IMU still publishes `/oak/imu/data` correctly. Updating the firmware requires the Luxonis flashing tool on a Linux x86 host — deferred.

---

## Build / ROS

### `unitree_legged_msgs/HighCmd.h: No such file or directory`

Message package wasn't built first. From `~/catkin_ws`:

```bash
catkin_make --pkg unitree_legged_msgs
source devel/setup.bash
catkin_make
```

### `c++: internal compiler error: Killed (program cc1plus)` on Nano

OOM during catkin_make. Drop to `-j1` and add swap:

```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
catkin_make -j1
```

### `rostopic hz` on laptop shows "no new messages"

Your laptop doesn't know about `.15`'s hostname. Either:

```bash
export ROS_MASTER_URI=http://192.168.123.14:11311
export ROS_IP=192.168.123.100
```

…or add to `/etc/hosts`:

```
192.168.123.14  unitree-desktop
192.168.123.15  nx
```

ROS multi-master uses hostnames in the TCP handshake; without resolution, topics list but data doesn't flow.

---

## Dashboard

### `http://localhost:8080` → "Connection refused"

SSH tunnel died or was never opened:

```bash
ssh -f -N -L 8080:localhost:8080 unitree@192.168.123.14
```

If the dashboard process died on `.14`:

```bash
ssh unitree@192.168.123.14
cd ~/go1-autonomy-stack
./scripts/start_dashboard.sh
```

### Belly camera feed is black

UDP stream from `.15` → `.14:5002` stopped. On `.15`:

```bash
pgrep -a ffmpeg
# if nothing, restart the belly-cam streamer (it's part of start_dashboard.sh's remote section)
```

---

## General "I've tried everything"

Escalation ladder:
1. `./scripts/go1_ros.sh damp` — always safe, always first.
2. Power-cycle the robot (battery out → in, wait 30 s).
3. Power-cycle your laptop's ethernet adapter (unplug, replug, re-run the macOS routing fix).
4. If after all this `rostopic list` is still empty: `ssh .14 && pgrep -a rosmaster` — is the master even running? `roscore &` it manually and retry.
5. Check `dmesg | tail -50` on the affected Jetson — USB drops, thermal throttle events, kernel oopses all show up here.

If you hit something not in this doc, add it.
