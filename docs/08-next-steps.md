# 08 — Next steps (M3 → M5)

M1 (platform + command path) and M2 (OAK-D camera integration) are done. Below is what remains.

---

## M3 — 2D SLAM

**Goal:** real-time 2D occupancy map of a flat indoor environment while the robot walks under teleop.

**Approach:** OAK-D stereo depth → virtual LaserScan via `pcl2scan` → `gmapping`.

### What's needed

1. **Forward-facing OAK-D.** Currently mounted pointing down. Re-angle before SLAM makes sense.
2. **`base_link` TF.** Publish a static transform from `base_link` → `oak-d_frame` with the measured mounting offset.
3. **Odometry.** Wrap HighState body velocity into `nav_msgs/Odometry` on `/odom`.
4. **pcl2scan config.** `packages/ros_unitree/pcl2scan/` already exists. Subscribe to `/oak/stereo/points` (set `i_publish_pointcloud: true` in `config/camera.yaml`), tune height limits to cut out floor and ceiling.
5. **gmapping.** Standard `slam_gmapping`, subscribe `/scan`, publish `/map`. Benchmark against `hector_slam` (hector doesn't need odometry — good sanity check).

---

## M4 — Point-to-point navigation

**Goal:** click a goal in rviz, robot walks there avoiding obstacles.

**Approach:** `move_base` + `AMCL` on the M3 map.

### What's needed

- **`/cmd_vel` → `/high_cmd` translator.** `move_base` outputs `geometry_msgs/Twist`; write a small ROS node (new package under `packages/`) to convert it to `/high_cmd` at 50 Hz with `mode=2, gaitType=1`.
- **Costmap config.** Go1 footprint ~0.60 × 0.35 m. Inflation radius ~0.35 m. Disable `rotate_recovery` (gait switching is janky); use `clear_costmap_recovery` only.
- **Velocity cap.** Start with `max_vel_x: 0.3 m/s`; odometry drift gets bad above that.

---

## M5 — Evaluation

**What to measure:**

- SLAM accuracy: drive a known loop (tape a 2×2 m square), compare map closure error.
- Localisation drift: AMCL covariance growth over 5 min stationary.
- Navigation success rate: 20 goals, fixed environment, report success / partial / fail.
- Compute load: `tegrastats` during SLAM and navigation.
