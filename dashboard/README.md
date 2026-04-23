# Go1 Dashboard

Live camera feeds + full sensor telemetry for the Unitree Go1 quadruped robot.
Streams 3 stereo camera pairs, IMU, battery, 12 joint motors, foot force sensors,
and motion state over HTTP from the Xavier NX.

## Quick Start

```bash
# On Xavier NX (192.168.123.14):
# 1. Kill autostart camera processes
pkill -f point_cloud_node
pkill -f mqttControlNode

# 2. Kill camera hogs on Nano too
sshpass -p 123 ssh unitree@192.168.123.15 'pkill -f point_cloud_node'

# 3. Start dashboard
python3 ~/Desktop/go1-dashboard/tri_stream.py

# On your Mac (connected via ethernet to 192.168.123.x):
# 4. Create SSH tunnel
ssh -f -N -L 8080:localhost:8080 unitree@192.168.123.14

# 5. Open browser
open http://localhost:8080
```

## Robot Control (sit_down)

Build once:
```bash
cd ~/K1/build && cmake .. && make sit_down
```

Usage:
```bash
cd ~/K1/build

./sit_down 5    # Stand DOWN (lie down gently)
./sit_down 6    # Stand UP
./sit_down 7    # Damping (release all motors - use when motors are hot)
./sit_down 1    # Force stand
./sit_down 0    # Idle (default stand)
./sit_down 2    # Velocity walking mode
./sit_down 8    # Recovery stand
```

IMPORTANT: If motors get hot (>70C), immediately run `./sit_down 7` to release them.

## Architecture

```
Mac (browser)
  |  SSH tunnel :8080
  v
Xavier NX (.14) -- runs tri_stream.py
  |  /dev/video0 = Left stereo pair (928x400)
  |  /dev/video1 = Right stereo pair (928x400)
  |  UDP :5002 <-- belly camera from Nano
  |  UDP :8095 --> sport mode on Pi (sensor reading)
  |
  +-- Nano (.15) -- /dev/video0 = Belly/ground stereo (928x400)
  |     ffmpeg streams via UDP to Xavier :5002
  |
  +-- Raspberry Pi (.161) -- sport mode controller, no cameras
  |     Legged_sport binary on port 8082 (HighCmd/HighState UDP)
  |     Web UI on port 80 (nginx)
  |     SSH: pi@.161, password: 123
  |
  +-- Head Nano (.13) -- OFFLINE (needs cable check)
  |     Should have: /dev/video0 = chin camera, /dev/video1 = face camera
  |     SSH: unitree@.13, password: 123
  |
  +-- MCU (.10) -- motor controller, no SSH
```

## Camera Map

| Feed | Board | Device | Position | Resolution |
|------|-------|--------|----------|------------|
| 0 | Xavier .14 | /dev/video0 | Left body stereo | 928x400 |
| 1 | Xavier .14 | /dev/video1 | Right body stereo | 928x400 |
| 2 | Nano .15 | /dev/video0 | Belly (ground-facing) | 928x400 |
| -- | Head .13 | /dev/video1 | Face (front) | OFFLINE |
| -- | Head .13 | /dev/video0 | Chin (down) | OFFLINE |

All cameras are Sunplus USB2.0 stereo fisheye modules (vendor 1bcf:2cd1).

## Sensor Data (via HighState UDP)

The dashboard reads robot state from the sport mode controller at 192.168.123.161:8082.

| Sensor | Source | Update Rate |
|--------|--------|-------------|
| IMU (roll/pitch/yaw, gyro, accel) | MCU via HighState | ~20 Hz |
| Battery (SOC, current, cell voltages) | BMS via HighState | ~20 Hz |
| Motor states (12 joints: angle, velocity, torque, temp) | MCU via HighState | ~20 Hz |
| Foot force (4 feet) | MCU via HighState | ~20 Hz |
| Motion mode, gait type, velocity | Sport controller | ~20 Hz |

## Dashboard Features

- **Camera tab**: 3 live stereo MJPEG feeds
- **Sensors tab**: IMU orientation, battery with charge bar, motion state, velocity
- **Motors tab**: 12-DOF joint data (angle in rad, torque in Nm, temp in C)
- **Foot force**: 4 force sensors in Newtons
- **Network panel**: status of all 5 internal boards
- **Color-coded motor temps**: green <50C, yellow 50-70C, red >70C

## Files

- `tri_stream.py` - Main dashboard server (cameras + sensors + HTTP)
- `sit_down.cpp` - Robot mode control via Unitree Legged SDK
- `README.md` - This file

## SSH Credentials

| Board | IP | User | Password | Notes |
|-------|-----|------|----------|-------|
| Xavier NX | .14 | unitree | (SSH key) | Main compute, 2 cameras |
| Nano (body) | .15 | unitree | 123 | Belly camera |
| Nano (head) | .13 | unitree | 123 | OFFLINE - face/chin cameras |
| Raspberry Pi | .161 | pi | 123 | Sport mode, web UI |
| MCU | .10 | -- | -- | No SSH, UDP only |

## Troubleshooting

**Cameras show 503 (no frames)**:
Autostart processes hold the camera devices. Kill them first:
```bash
pkill -f point_cloud_node
pkill -f mqttControlNode
# On Nano:
sshpass -p 123 ssh unitree@192.168.123.15 'pkill -f point_cloud_node'
```

**Port 8080 in use**:
```bash
fuser -k 8080/tcp
```

**SSH tunnel dies**:
```bash
pkill -f "ssh.*-L 8080"
ssh -f -N -L 8080:localhost:8080 unitree@192.168.123.14
```

**Motors overheating**:
```bash
cd ~/K1/build && ./sit_down 7   # Damping mode - releases all motors
```

**Head Nano offline (.13)**:
Open the robot head shell and check the ethernet cable from the internal switch
to the Nano 2GB board. Also check the power connector.
