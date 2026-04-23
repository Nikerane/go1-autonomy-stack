# go1-autonomy-stack

Onboard perception + autonomy stack for the **Unitree Go1 Edu Plus** under ROS Melodic. Runs on the robot's internal compute (Jetson Nano 4GB + Jetson Xavier NX), talks to the factory locomotion controller, and publishes live camera topics for downstream SLAM and navigation.

**Status (2026-04-23):** Robot walks from ROS. OAK-D RGB + stereo-depth topics live at ~10 Hz. SLAM (M3) is the next milestone.

---

## Current status

- [x] **M1** — Platform & command path. Stand / sit / damp / trot / walk commanded from ROS, with reproducible boot scripts.
- [x] **M2** — Camera integration. OAK-D mounted, depthai-core v2.24.0 + depthai-ros patched for Melodic, `/oak/rgb/image_raw` and `/oak/stereo/image_raw` publishing.
- [ ] **M3** — 2D SLAM. pcl2scan + gmapping, benchmark vs hector.
- [ ] **M4** — Point-to-point navigation. AMCL + move_base.
- [ ] **M5** — Evaluation: map accuracy, nav success rate, compute load benchmarks.

See [docs/08-next-steps.md](docs/08-next-steps.md) for the full roadmap.

---

## Hardware & network (short version)

| Board | IP | Hardware | Hostname | User | Pass | Role |
|---|---|---|---|---|---|---|
| Nano 4GB | `192.168.123.14` | Jetson Nano (4 GB RAM, 14 GB eMMC) | `unitree-desktop` | `unitree` | SSH key | **ROS master**, body cameras, dashboard |
| Xavier NX | `192.168.123.15` | Jetson Xavier NX (8 GB RAM, 110 GB NVMe) | `nx` | `unitree` | `123` | OAK-D camera node, UnitreeSLAM, belly camera |
| Raspberry Pi | `192.168.123.161` | Pi 3B+ | — | `pi` | `123` | Sport-mode relay, web UI |
| MCU | `192.168.123.10` | STM32 | — | — | — | Motor controller (UDP-only) |

Your laptop sits at `192.168.123.100` on whatever ethernet adapter reaches the robot LAN. Full details: [docs/01-hardware.md](docs/01-hardware.md), [docs/02-network.md](docs/02-network.md).

---

## Quickstart — 5 minutes from cold robot

```bash
# 1. Power the robot on. It boots into damping. Wait 30 s for all boards to come up.
ping -c1 192.168.123.14 && ping -c1 192.168.123.15

# 2. The repo is already on the robot at ~/go1-autonomy-stack/.
#    If starting fresh on a re-imaged board, clone it:
#    ssh unitree@192.168.123.14
#    git clone <this-repo-url> go1-autonomy-stack

# 3. Stand the robot up.
ssh unitree@192.168.123.14
cd ~/go1-autonomy-stack
./scripts/go1_ros.sh stand

# 4. Launch the OAK-D camera (still on .14).
./scripts/start_oak_camera.sh

# 5. Verify topics are alive.
source /opt/ros/melodic/setup.bash
export ROS_MASTER_URI=http://192.168.123.14:11311
rostopic hz /oak/rgb/image_raw          # expect ~10 Hz

# 6. Trot test (10 s forward at 0.2 m/s). Keep a hand near the power switch.
./scripts/go1_ros.sh trot

# 7. Back to safe state.
./scripts/go1_ros.sh damp
```

First-time setup (cold boards, empty catkin_ws, or re-imaged Jetsons): see [docs/03-first-boot.md](docs/03-first-boot.md).

---

## Architecture

```
                Your laptop (192.168.123.100)
                         │  ssh / rosmaster client
                         ▼
  ┌──────────────────────────────────────────────────────────┐
  │  Jetson Nano 4GB (.14)  ← ROS master, port 11311         │
  │  - roscore                                               │
  │  - go1-dashboard (tri_stream.py → http://localhost:8080) │
  │  - /high_cmd publisher → Pi → MCU                        │
  │  - body stereo /dev/video0,1                             │
  └────────────┬───────────────────┬────────────────────────┘
               │ ROS topics        │ UDP /high_cmd → .161:8082
               ▼                   ▼
  ┌─────────────────────────┐  ┌──────────────────────────┐
  │  Jetson Xavier NX (.15) │  │  Raspberry Pi (.161)     │
  │  - depthai_ros_driver   │  │  - Legged_sport relay    │
  │  - /oak/rgb/image_raw   │  │  - nginx web UI          │
  │  - /oak/stereo/image_raw│  │  - UDP ↔ MCU (.10:8007)  │
  │  - UnitreeSLAM (lidar)  │  └────────────┬─────────────┘
  │  - belly /dev/video0    │               │
  └─────────────────────────┘               ▼
                                 ┌──────────────────────┐
                                 │  MCU (.10)           │
                                 │  Motor control 8007  │
                                 └──────────────────────┘
```

---

## Repo layout

| Folder | What it is |
|---|---|
| [`docs/`](docs/) | Numbered onboarding guides (hardware, network, first-boot, build, OAK-D, troubleshooting, next steps). |
| [`packages/`](packages/) | ROS packages — drop into `~/catkin_ws/src/` and `catkin_make`. Contains `ros_unitree` (Go1 ROS core). |
| [`scripts/`](scripts/) | Automation: `go1_ros.sh` (unified control), `start_oak_camera.sh`, `fix_net.sh`, `deploy.sh`, etc. |
| [`dashboard/`](dashboard/) | Live web dashboard (`tri_stream.py`) — cameras + sensors in a browser. Runs on `.14`. |
| [`config/`](config/) | Drop-in configs we tweaked: OAK-D `camera.yaml` (nn_type=none), USB udev rule for vendor `03e7`. |

---

## Building & running

- **Catkin workspace rebuild:** [docs/04-build-catkin.md](docs/04-build-catkin.md)
- **OAK-D from scratch** (depthai-core v2.24.0 + patched depthai-ros): [docs/05-oak-d-setup.md](docs/05-oak-d-setup.md)
- **depthai-ros modifications** (6 patches for Melodic + v2.24.0 compatibility): [docs/06-depthai-ros-mods.md](docs/06-depthai-ros-mods.md)
- **Troubleshooting:** [docs/07-troubleshooting.md](docs/07-troubleshooting.md)
