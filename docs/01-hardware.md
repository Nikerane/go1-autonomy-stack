# 01 — Hardware

The Go1 Edu Plus ships with 3 Jetsons, a Pi, and an MCU on an internal gigabit network. One Jetson (the head) is currently offline.

## Board inventory

### `.14` — Jetson Nano 4GB (body/belly area)

- **Hostname:** `unitree-desktop`
- **SoC:** NVIDIA Tegra (Jetson Nano 4GB)
- **RAM:** 4 GB
- **Storage:** 14 GB eMMC (at ~65 % full — be careful with large builds here)
- **Kernel:** `4.9.201-tegra` (Ubuntu 18.04 ARM64)
- **Role:** **ROS master**, runs the go1-dashboard, commands the robot via `/high_cmd`
- **Cameras attached:** `/dev/video0` (left body stereo), `/dev/video1` (right body stereo) — Sunplus USB2.0 fisheye pairs at 928 × 400
- **Network:**
  - `eth0` → internal `192.168.123.14` (gigabit, links to other boards + Pi)
  - No WiFi chip. Internet can only reach this board via IPv6 hand-off from the Pi.
- **Auth:** `unitree` user, passwordless SSH (`ed25519` key from the lab laptop), `sudo` password `123`.

Relevant install locations:
- `~/catkin_ws/` — ROS workspace
- `~/K1/` — Unitree Legged SDK + Sagittarius arm SDK (do not move)
- `~/Desktop/go1-dashboard/` — the dashboard (now mirrored into `dashboard/` in this repo)

### `.15` — Jetson Xavier NX (main compute)

- **Hostname:** `nx`
- **SoC:** NVIDIA Xavier NX (from `/proc/device-tree/model`: "NVIDIA Jetson Xavier NX Developer Kit")
- **RAM:** 8 GB
- **Storage:** 110 GB NVMe SSD (~20 % full — this is where all big builds go)
- **Kernel:** `4.9.201-tegra`
- **Role:** OAK-D camera node, depthai-core/-ros host, UnitreeSLAM (lidar path), belly camera
- **Cameras attached:** `/dev/video0` (belly/ground-facing stereo pair). OAK-D over USB when connected.
- **Network:**
  - `eth0` → `192.168.123.15`
  - `wlan0` → TP-LINK USB dongle on SSID `Otto51 1` (used for internet only; see `scripts/fix_net.sh` for recovery).
- **Auth:** `unitree` / password `123`, `sudo` password `123`.

Relevant install locations:
- `~/catkin_ws/` — ROS workspace (slightly different from .14: contains `depthai-ros` and the extra `go1_bridge` package)
- `/usr/local/{lib,include}/depthai/` — depthai-core v2.24.0 headers + `.so`'s
- `~/UnitreeSLAM/` — 2D SLAM (RPLidar-based, Slamtec SDK). Not lifted into this repo due to ~240 MB of proprietary binary `.a` files; reference it in-place.

### `.161` — Raspberry Pi 3B+ (sport-mode relay)

- **Role:** Runs `Legged_sport` on UDP :8082, bridges `/high_cmd` from the ROS side to the MCU. Also hosts the factory web UI (`nginx` on :80).
- **Auth:** `pi` / password `123`.
- Reach from laptop via `ssh -J unitree@192.168.123.14 pi@192.168.123.161`.

### `.10` — MCU (motor controller)

- No SSH, no direct access. UDP-only on port 8007.
- Reached exclusively via the Pi's `Legged_sport`.

### `.13` — Jetson Nano 2GB (head) — OFFLINE

- Factory config hosts the face + chin fisheye cameras on `/dev/video0,1`.
- Currently not pingable from any other board. Suspected cable issue inside the head shell (ethernet or power). Not blocking our work — body and belly cameras + OAK-D cover forward FOV.

## Peripherals

- **OAK-D (Luxonis BW1098OAK):** RGB + active stereo depth over USB-C. Currently mounted on the body, pointing down (needs retilt before SLAM). Vendor `03e7:2485` (bootloader) → `03e7:f63b` (runtime). Udev rule in `config/udev/80-movidius.rules`.
- **Sagittarius arm (Z1 variant):** serial over `/dev/ttyACM0` at 1M baud. Not currently connected.
- **Unitree remote controller:** pairs over the Go1's internal 2.4 GHz link; talks to `Legged_sport` directly, no ROS involvement.

## Power

- 24 V DC via XT60. Factory batteries last ~25 min under active walking. Swap frequently during tuning.
- Bench supply for long sessions: 24 V, 15–20 A, XT60 pigtail.
- If motors climb over 70 °C during tests, run `./scripts/go1_ros.sh damp` — overheating is by far the most common way to damage this robot.

## Thermal behavior

- Xavier NX hits ~60 °C under heavy depthai load; has an active fan. No throttling observed.
- Nano 4GB runs hotter (~70 °C) under dashboard + ROS master load. The factory case has adequate ventilation — do not cover.
- Leg motors (especially rear hips) overheat fastest. Check `./scripts/go1_ros.sh status` between trot runs.
