# 04 — Rebuilding the catkin workspace

## Day-to-day development workflow

All code lives in `~/go1-autonomy-stack/packages/`. You edit there, then build in `catkin_ws/`:

```bash
# Edit source
nano ~/go1-autonomy-stack/packages/ros_unitree/pcl2scan/src/something.cpp

# Build
cd ~/catkin_ws && catkin_make -j2

# Test
source ~/catkin_ws/devel/setup.bash && rosrun ...
```

`catkin_ws/src/ros_unitree` is a symlink to `~/go1-autonomy-stack/packages/ros_unitree`, so catkin picks up your edits automatically. Git push/pull from `~/go1-autonomy-stack/` as normal.

---

You only need the rest of this doc if the Jetsons were re-imaged, `~/catkin_ws/` was wiped, or you've added a new ROS package and want to verify the build from scratch.

Both boards run ROS Melodic on Ubuntu 18.04 ARM64. The workspace layout is the same on both but the *set of packages* differs (see table at the end).

## Prerequisites (per board, one-time)

```bash
sudo apt-get update
sudo apt-get install -y \
  ros-melodic-desktop \
  ros-melodic-cv-bridge \
  ros-melodic-image-transport \
  ros-melodic-tf2-ros \
  ros-melodic-pcl-ros \
  ros-melodic-image-view \
  python-catkin-tools python-rosdep \
  build-essential cmake git
```

If this is a brand-new image:

```bash
sudo rosdep init || true
rosdep update
```

## Step 1 — Create the workspace

```bash
mkdir -p ~/catkin_ws/src
cd ~/catkin_ws
catkin_make      # produces an empty devel/ and build/
source devel/setup.bash
```

Add to `~/.bashrc` so every new shell picks up ROS + the workspace:

```bash
echo 'source /opt/ros/melodic/setup.bash' >> ~/.bashrc
echo 'source ~/catkin_ws/devel/setup.bash' >> ~/.bashrc
echo 'export ROS_MASTER_URI=http://192.168.123.14:11311' >> ~/.bashrc
echo 'export ROS_IP=$(hostname -I | awk "{print \$1}")' >> ~/.bashrc
```

On `.14` (ROS master) set `ROS_IP=192.168.123.14`. On `.15` set `ROS_IP=192.168.123.15`.

## Step 2 — Drop in the repo's packages

From your laptop:

```bash
./scripts/deploy.sh
```

Then, on each board:

```bash
cd ~/catkin_ws/src
ln -sfn ~/go1-autonomy-stack/packages/ros_unitree  ros_unitree
```

We symlink rather than copy so that `./scripts/deploy.sh` updates the source tree in place.

## Step 3 — Resolve dependencies

```bash
cd ~/catkin_ws
rosdep install --from-paths src --ignore-src -y -r
```

Expected "skipped" packages (these are pulled in by name but are ROS-internal and already installed): `unitree_legged_msgs`, `unitree_legged_real`. That's fine.

## Step 4 — Build order

`ros_unitree` contains message packages that everything else depends on. catkin figures out the order, but if you hit `unitree_legged_msgs/HighCmd.h: No such file`, it means messages weren't generated first. Force the order:

```bash
cd ~/catkin_ws
catkin_make --pkg unitree_legged_msgs
source devel/setup.bash
catkin_make -j2             # -j2 on the Nano; -j4 is fine on the Xavier
```

On the Nano, a full cold build takes **~18 min** and briefly peaks at ~3.2 GB RAM. If you see the OOM killer hit `cc1plus`, drop to `-j1` and add a swap file:

```bash
sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
```

On the Xavier a full build is **~6 min**.

## Step 5 — Verify

```bash
source ~/catkin_ws/devel/setup.bash
rospack list | grep -E 'unitree|go1'
```

Expected on both boards:

```
unitree_legged_msgs   /home/unitree/catkin_ws/src/ros_unitree/unitree_legged_msgs
unitree_legged_real   /home/unitree/catkin_ws/src/ros_unitree/unitree_legged_real
unitree_guide         /home/unitree/catkin_ws/src/ros_unitree/unitree_guide
pcl2scan              /home/unitree/catkin_ws/src/ros_unitree/pcl2scan
```

Additionally on `.15`:

```
depthai_ros_driver    /home/unitree/catkin_ws/src/depthai-ros/depthai_ros_driver
depthai_bridge        /home/unitree/catkin_ws/src/depthai-ros/depthai_bridge
depthai_ros_msgs      /home/unitree/catkin_ws/src/depthai-ros/depthai_ros_msgs
```

`depthai-ros` is **not** in this repo — see [05-oak-d-setup.md](05-oak-d-setup.md) for how to clone and patch it on `.15`.

## Packages per board

| Package | .14 (Nano) | .15 (Xavier) | Source |
|---|---|---|---|
| `unitree_legged_msgs` | ✅ | ✅ | `packages/ros_unitree/` |
| `unitree_legged_real` | ✅ | ✅ | `packages/ros_unitree/` |
| `unitree_guide` | ✅ | ✅ | `packages/ros_unitree/` |
| `pcl2scan` | ✅ | ✅ | `packages/ros_unitree/` |
| `depthai_ros_driver` | — | ✅ | upstream + patches ([06](06-depthai-ros-mods.md)) |

## Common build errors

- **`Could NOT find catkin`** — you forgot `source /opt/ros/melodic/setup.bash`.
- **`unitree_legged_msgs/HighCmd.h: No such file`** — build messages first (Step 4).
- **`c++: internal compiler error: Killed (program cc1plus)`** on Nano — OOM, add swap + use `-j1`.
- **depthai_ros_driver errors about `PresetMode` or `RawToFConfig`** — you're on a stock depthai-ros; apply the 6 patches in [06-depthai-ros-mods.md](06-depthai-ros-mods.md).

## Clean rebuild

```bash
cd ~/catkin_ws
rm -rf build devel
catkin_make --pkg unitree_legged_msgs
catkin_make -j2
```

Do this if you've pulled upstream message changes, or if linker errors smell stale.
