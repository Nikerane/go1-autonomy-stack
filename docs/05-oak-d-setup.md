# 05 — OAK-D setup (from scratch)

This is the procedure for bringing the Luxonis OAK-D (BW1098OAK) up on a fresh Xavier NX (`.15`) under ROS Melodic. Needed only if `.15` was re-imaged, or if you're porting this to a new robot.

Target stack:
- **depthai-core** v2.24.0 installed to `/usr/local`
- **depthai-ros** 2.11.2 cloned into `~/catkin_ws/src/` and patched (see [06-depthai-ros-mods.md](06-depthai-ros-mods.md))
- udev rule so the OAK-D is accessible without `sudo`

Expected end state: `rostopic hz /oak/rgb/image_raw` shows ~10 Hz (USB 2.0-limited — see [07-troubleshooting.md](07-troubleshooting.md)).

## Prerequisites on .15

First, make sure the Xavier has internet. The on-board ethernet is the internal robot LAN — no internet there. You want `wlan0` (RTL8192CU USB dongle):

```bash
ssh unitree@192.168.123.15
cd ~/go1-autonomy-stack
./scripts/fix_net.sh
ping -c2 8.8.8.8      # must succeed
```

Install build deps:

```bash
sudo apt-get update
sudo apt-get install -y \
  cmake git build-essential libusb-1.0-0-dev \
  python3-pip python3-dev \
  libopencv-dev
```

## Step 1 — Build depthai-core v2.24.0

```bash
cd ~
git clone --recursive --branch v2.24.0 https://github.com/luxonis/depthai-core.git
cd depthai-core
mkdir build && cd build
cmake .. -D CMAKE_BUILD_TYPE=Release -D CMAKE_INSTALL_PREFIX=/usr/local -D BUILD_SHARED_LIBS=ON
make -j4
sudo make install
sudo ldconfig
```

Verify:

```bash
ls /usr/local/lib/libdepthai-*.so
# expect: libdepthai-core.so  libdepthai-opencv.so  libdepthai-resources.so
ls /usr/local/include/depthai/
# expect a tree with depthai.hpp, device/, pipeline/, ...
```

Cold build time on Xavier: **~25 min**. Don't build this on the Nano — `depthai-core` with submodules won't fit.

## Step 2 — Install the udev rule

Without this, the OAK-D only works as root:

```bash
sudo cp ~/go1-autonomy-stack/config/udev/80-movidius.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Unplug and replug the OAK-D, then:

```bash
lsusb | grep 03e7
# Bootloader mode:  03e7:2485 Intel Movidius MyriadX
# Runtime mode:     03e7:f63b Intel Movidius MyriadX
```

The VID flips from `2485` → `f63b` the first time you open a pipeline (the driver loads firmware onto the device). If you only ever see `2485`, the firmware push is failing — usually a cable or USB power issue.

## Step 3 — Sanity test (pure C++, no ROS)

```bash
cd ~/depthai-core/build
./examples/rgb_preview
```

You should see "Device booted" and a stream of frames scrolling. `Ctrl-C` to quit. If this works, depthai-core is healthy — any later issue is on the ROS side.

## Step 4 — Clone + patch depthai-ros

```bash
cd ~/catkin_ws/src
git clone --branch noetic https://github.com/luxonis/depthai-ros.git
cd depthai-ros
git checkout 2.11.2    # last tag that builds on Melodic with our patches
```

Apply the 6 patches documented in **[06-depthai-ros-mods.md](06-depthai-ros-mods.md)**. These are needed because:
- depthai-ros 2.11.2 targets Noetic / C++17, Melodic ships C++14
- two source files reference depthai-core APIs that don't exist in v2.24.0
- one default value (`i_nn_type: "spatial"`) tries to load a MobileNet blob we don't have

Drop in our pre-patched config:

```bash
cp ~/go1-autonomy-stack/config/camera.yaml \
   ~/catkin_ws/src/depthai-ros/depthai_ros_driver/config/camera.yaml
```

Key fields in that file:
- `camera_i_nn_type: none`
- `camera_i_pipeline_type: rgbd`

## Step 5 — Build

```bash
cd ~/catkin_ws
catkin_make -j4 --pkg depthai_ros_msgs
catkin_make -j4 --pkg depthai_bridge
catkin_make -j4 --pkg depthai_ros_driver
source devel/setup.bash
```

Full build from cold: **~12 min** on the Xavier.

If you see errors, they almost always match one of the 6 issues in [06](06-depthai-ros-mods.md) — apply the missing patch and re-run.

## Step 6 — First launch

```bash
roslaunch depthai_ros_driver camera.launch camera_model:=OAK-D
```

Expected log lines:
- `[INFO] Device booted`
- `[INFO] Camera set up`
- No `Cannot load blob` errors (if you see this, `i_nn_type` isn't `none` — check the yaml)

From a second shell:

```bash
rostopic list | grep oak
rostopic hz /oak/rgb/image_raw      # ~10 Hz
rostopic hz /oak/stereo/image_raw   # ~10 Hz
```

## Step 7 — Wire into the repo scripts

Once the above works by hand, day-to-day you just use:

```bash
# From .14:
./scripts/start_oak_camera.sh
```

That script SSHes into `.15`, kills any stale driver, and re-launches with our config. See [03-first-boot.md](03-first-boot.md) Step 5.

## Known quirks

- **USB 2.0 speed.** The OAK-D negotiates USB 2.0 on the Xavier's USB-C port, not USB 3.0. This caps framerate to ~10 Hz. Root cause unclear (cable? carrier board? kernel?). Tracked in [07-troubleshooting.md](07-troubleshooting.md). Not blocking for SLAM.
- **IMU firmware mismatch.** Device reports BNO086 firmware 3.2.13; depthai-core 2.24.0 expects 3.2.14. Driver prints a warning and continues. IMU topics publish correctly.
- **First launch after reboot is slow.** Firmware push takes ~8 s; that's why `start_oak_camera.sh` waits 12 s before listing topics.
