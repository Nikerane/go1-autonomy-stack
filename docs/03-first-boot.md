# 03 — First boot (cold robot → walking + camera in under 1 hour)

This is the "day 1" checklist. Assumes the repo is already cloned on your laptop and both Jetsons are already set up (i.e., they build). If the Jetsons are fresh and catkin_ws is empty, see [04-build-catkin.md](04-build-catkin.md) first.

## Before you touch the robot

- [ ] Battery is ≥ 80 %. Swap if below.
- [ ] Floor is flat and clear within ~2 m radius.
- [ ] You know where the **main power switch** is (under the belly near the battery).
- [ ] Laptop has `sshpass` and `rsync` installed.

## Step 1 — Power up

1. Press the power button on the battery. LEDs cycle.
2. Wait ~30 s for all boards to boot.
3. The robot starts in **damping** (legs loose, body on the ground). This is normal.

## Step 2 — Confirm the network is healthy

On your laptop:

```bash
# Join the robot LAN first — see docs/02-network.md if this is a fresh macOS session
ping -c1 192.168.123.14 && ping -c1 192.168.123.15 && ping -c1 192.168.123.161
```

All three should reply in < 2 ms. If .14 times out, the routing fix in [02-network.md](02-network.md) didn't stick — re-apply.

## Step 3 — Deploy this repo to both boards

```bash
cd ~/go1-autonomy-stack     # wherever you cloned it
./scripts/deploy.sh
```

This rsyncs the repo to `~/go1-autonomy-stack/` on both `.14` and `.15`. Takes ~20 s on a warm cache, ~2 min cold.

## Step 4 — Stand the robot up

```bash
ssh unitree@192.168.123.14
cd ~/go1-autonomy-stack
./scripts/go1_ros.sh damp      # confirm in damping
./scripts/go1_ros.sh stand     # legs extend, robot stands
./scripts/go1_ros.sh status    # battery + motor temps
```

If the robot wobbles but doesn't rise:
- Hip motors may be wedged against the ground. Lift the belly ~5 cm by hand and re-run `stand`.
- If one leg stays folded, `damp` and inspect the motor hall sensor — see [07-troubleshooting.md](07-troubleshooting.md).

## Step 5 — Start the OAK-D camera

Still on `.14`:

```bash
./scripts/start_oak_camera.sh
```

The script SSHs into `.15`, kills any previous driver, checks the USB device, launches the ROS driver with our patched `camera.yaml`, and waits 12 s before listing topics.

Verify from `.14`:

```bash
source /opt/ros/melodic/setup.bash
export ROS_MASTER_URI=http://192.168.123.14:11311

rostopic list | grep oak
rostopic hz /oak/rgb/image_raw      # ~10 Hz (USB 2.0-limited)
rostopic hz /oak/stereo/image_raw   # ~10 Hz
```

If no topics appear:
- SSH to `.15` and check `tail /tmp/oak_camera.log`. Common error: "Cannot find any device" → OAK-D unplugged. Less common: "Cannot load blob…" → `camera_i_nn_type` isn't `none`; see [06-depthai-ros-mods.md](06-depthai-ros-mods.md).

## Step 6 — Walking test

**With the robot on flat ground and clear space ahead:**

```bash
./scripts/go1_ros.sh trot
```

The robot idles for 2 s, trots forward at 0.2 m/s for 10 s, then idles again. Keep your hand near the main power switch the first time.

If the robot doesn't move:
- Motor temps too high → `./scripts/go1_ros.sh damp`, let cool.
- Not in the right mode — `go1_ros.sh trot` sets `mode=2, gaitType=2` at 50 Hz. If the Pi isn't listening, no motion. Check `.161` is pingable.

## Step 7 — Live dashboard (optional but useful)

```bash
# On .14:
./scripts/start_dashboard.sh

# On your laptop:
ssh -f -N -L 8080:localhost:8080 unitree@192.168.123.14
open http://localhost:8080
```

You'll see 3 camera feeds + IMU + battery + motor temps in the browser.

## Step 8 — Safe shutdown

```bash
./scripts/go1_ros.sh damp        # on .14
```

Then press the power button on the battery. Do **not** pull the battery with motors still energised — you'll hear a loud click and it's bad for the FETs.

---

## If you're here and the robot hasn't moved

Diagnostic order (5 min):

1. **Pings OK?** If .14/.15/.161 don't reply, it's network. See [02-network.md](02-network.md).
2. **`./scripts/go1_ros.sh status` prints something?** If no HighState, the Pi (`.161:8082`) is down. `ssh pi@.161` and check `Legged_sport` is running.
3. **`./scripts/go1_ros.sh damp` makes the motors click?** If not, the SDK binary isn't talking to the Pi. Check `~/K1/build/sit_down` exists on `.14`.
4. **`/oak/rgb/image_raw` publishing?** If not, `tail /tmp/oak_camera.log` on `.15` — see step 5 above.

If all four of those are green and the robot still won't move, it's likely a motor or MCU issue — escalate.
