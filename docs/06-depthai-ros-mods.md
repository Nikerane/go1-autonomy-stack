# 06 — depthai-ros modifications

Reference for the 6 patches we made to `depthai-ros` 2.11.2 to get it building on ROS Melodic against `depthai-core` v2.24.0. Apply these by hand after cloning (see [05-oak-d-setup.md](05-oak-d-setup.md) Step 4).

Target tree: `~/catkin_ws/src/depthai-ros/` on `.15`.

---

## Patch 1 — CMake minimum version

depthai-ros 2.11.2 requires CMake ≥ 3.10.2 in several `CMakeLists.txt` files. Our Ubuntu 18.04 ships 3.10.2 exactly, which sometimes triggers a spurious policy warning. Bump it.

**Files:**
- `depthai-ros/depthai_ros_driver/CMakeLists.txt`
- `depthai-ros/depthai_bridge/CMakeLists.txt`
- `depthai-ros/depthai_ros_msgs/CMakeLists.txt`

```diff
-cmake_minimum_required(VERSION 3.10.2)
+cmake_minimum_required(VERSION 3.10.2 FATAL_ERROR)
+if(POLICY CMP0057)
+  cmake_policy(SET CMP0057 NEW)
+endif()
```

---

## Patch 2 — Remove tof.cpp sensor node

`depthai_ros_driver/src/dai_nodes/sensors/tof.cpp` calls `dai::node::ToF` APIs that don't exist in depthai-core v2.24.0 (ToF was reworked in 2.25+). We don't have a ToF sensor on the OAK-D, so drop the file from the build.

**File:** `depthai-ros/depthai_ros_driver/CMakeLists.txt`

```diff
 set(SENSOR_SOURCES
   src/dai_nodes/sensors/sensor_wrapper.cpp
   src/dai_nodes/sensors/rgb.cpp
   src/dai_nodes/sensors/mono.cpp
-  src/dai_nodes/sensors/tof.cpp
   src/dai_nodes/sensors/imu.cpp
 )
```

Also remove the `#include "depthai_ros_driver/dai_nodes/sensors/tof.hpp"` line from `src/pipeline/pipeline_generator.cpp` and the two branches referencing `NodeNameEnum::ToF`.

---

## Patch 3 — TFPublisher.cpp API drift

`depthai_bridge/src/TFPublisher.cpp` uses `dai::CalibrationHandler::getCameraExtrinsics(...)` with a 4-arg signature that was collapsed to 3 args in v2.24.0 (the `useSpecTranslation` default moved).

**File:** `depthai-ros/depthai_bridge/src/TFPublisher.cpp`

```diff
-auto extrinsics = calHandler.getCameraExtrinsics(
-    srcCamera, dstCamera, useSpecTranslation, false);
+auto extrinsics = calHandler.getCameraExtrinsics(
+    srcCamera, dstCamera, useSpecTranslation);
```

Two call sites in the same file — patch both.

---

## Patch 4 — PresetMode enum mapping

`depthai_ros_driver/src/param_handlers/stereo_param_handler.cpp` maps string → `dai::node::StereoDepth::PresetMode`. In v2.24.0 the enum values were renamed (`HIGH_DENSITY` → `HIGH_ACCURACY`/`HIGH_DENSITY` split). Update the map:

**File:** `depthai-ros/depthai_ros_driver/src/param_handlers/stereo_param_handler.cpp`

```diff
 const std::unordered_map<std::string, dai::node::StereoDepth::PresetMode> presetModeMap = {
-    {"HIGH_ACCURACY", dai::node::StereoDepth::PresetMode::HIGH_ACCURACY},
-    {"HIGH_DENSITY", dai::node::StereoDepth::PresetMode::HIGH_DENSITY},
+    {"HIGH_ACCURACY", dai::node::StereoDepth::PresetMode::HIGH_ACCURACY},
+    {"HIGH_DENSITY",  dai::node::StereoDepth::PresetMode::HIGH_DENSITY},
+    {"DEFAULT",       dai::node::StereoDepth::PresetMode::HIGH_DENSITY},
 };
```

If you leave this with a missing `DEFAULT`, the driver aborts on launch with `std::out_of_range`.

---

## Patch 5 — Skip RawToFConfig

`depthai_bridge/include/depthai_bridge/ImageConverter.hpp` references `dai::RawToFConfig` which doesn't exist in v2.24.0. Guard it out:

**File:** `depthai-ros/depthai_bridge/include/depthai_bridge/ImageConverter.hpp`

```diff
 #include <depthai/pipeline/datatype/ImgFrame.hpp>
-#include <depthai/pipeline/datatype/RawToFConfig.hpp>
+// RawToFConfig not available in depthai-core v2.24.0; skipping (no ToF sensor in use).
+// #include <depthai/pipeline/datatype/RawToFConfig.hpp>
```

Any downstream `RawToFConfig` usage is inside `#ifdef HAS_TOF` blocks — leave `HAS_TOF` undefined.

---

## Patch 6 — nn_type default → none

**This is the patch that matters most day-to-day.** Stock depthai-ros defaults `camera_i_nn_type` to `"spatial"`, which tries to load a MobileNet blob from a hardcoded path. We don't ship that blob, so the driver crashes at startup with `Cannot load blob, file doesn't exist`.

**File:** `depthai-ros/depthai_ros_driver/src/param_handlers/camera_param_handler.cpp`

```diff
-declareAndLogParam<std::string>("i_nn_type", "spatial");
+declareAndLogParam<std::string>("i_nn_type", "none");
```

And in the shipped config:

**File:** `depthai-ros/depthai_ros_driver/config/camera.yaml`

```diff
-camera_i_nn_type: spatial
+camera_i_nn_type: none
```

The repo keeps a known-good copy at `config/camera.yaml` — just `cp` it over after cloning depthai-ros (see [05](05-oak-d-setup.md) Step 4).

---

## Verifying patches are applied

```bash
cd ~/catkin_ws/src/depthai-ros
grep -n 'i_nn_type' depthai_ros_driver/src/param_handlers/camera_param_handler.cpp
# expect: "none"
grep -n 'tof.cpp' depthai_ros_driver/CMakeLists.txt
# expect: no match
grep -c 'getCameraExtrinsics.*useSpecTranslation, false' depthai_bridge/src/TFPublisher.cpp
# expect: 0
```

If any of these don't match, re-apply the relevant patch.

## If you re-clone depthai-ros and need a fresh patch session

The 6 files above, in order:

1. `depthai_ros_driver/CMakeLists.txt` (+ siblings)
2. `depthai_ros_driver/CMakeLists.txt` — remove tof.cpp
3. `depthai_bridge/src/TFPublisher.cpp`
4. `depthai_ros_driver/src/param_handlers/stereo_param_handler.cpp`
5. `depthai_bridge/include/depthai_bridge/ImageConverter.hpp`
6. `depthai_ros_driver/src/param_handlers/camera_param_handler.cpp`

After the last patch, `catkin_make` should complete cleanly. If upstream later tags a Melodic-compatible release, ditch this whole patch set and pin to that tag instead.
