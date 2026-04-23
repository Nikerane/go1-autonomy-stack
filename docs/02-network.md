# 02 — Network

The Go1 has a private `192.168.123.0/24` network on its internal gigabit switch. Everything meaningful — ROS traffic, `/high_cmd` UDP, camera streams — flows inside this subnet. Your laptop joins via one ethernet port and does not need internet for anything on the robot.

## Address map

| IP | Host | MAC owner | Purpose |
|---|---|---|---|
| `.10` | MCU | Unitree | Motor controller (UDP :8007) |
| `.13` | Head Nano 2GB | NVIDIA | Face/chin cameras — **OFFLINE** |
| `.14` | Body Nano 4GB | NVIDIA | ROS master (:11311), body cams, dashboard |
| `.15` | Xavier NX | NVIDIA | OAK-D driver, UnitreeSLAM, belly cam |
| `.100` | Your laptop | (any) | SSH / rviz client |
| `.161` | Raspberry Pi | Raspberry Pi | Sport-mode relay (:8082), web UI (:80) |

## Who talks to whom

```
laptop (.100) ──ssh──▶  .14 (ROS master)
                         │
                         │  /high_cmd  (UDP ROS)
                         ▼
                   unitree_legged_real ─── ros_udp ───▶ Pi (.161:8082)
                                                             │
                                                             │ SDK UDP
                                                             ▼
                                                        MCU (.10:8007)

.15 (OAK-D node) ───ROS topics──▶ .14 (subscribers, rviz, etc.)
.15 (belly cam)  ── ffmpeg UDP ──▶ .14:5002 (dashboard)
```

## Ports you should know

| Port | Proto | Where | What |
|---|---|---|---|
| 22 | TCP | all Jetsons, Pi | SSH |
| 80 | TCP | Pi | factory web UI (nginx) |
| 5002 | UDP | Nano (.14) | belly cam stream in (from .15) |
| 8007 | UDP | MCU (.10) | motor control (don't poke) |
| 8080 | TCP | Nano (.14) | go1-dashboard |
| 8082 | UDP | Pi (.161) | `Legged_sport` HighCmd / HighState |
| 8090 | UDP | Pi (.161) | conflict-prone — `ros_udp`, `base_ctrl`, SDK binaries all want it. See [07-troubleshooting.md](07-troubleshooting.md). |
| 11311 | TCP | Nano (.14) | ROS master |

## Laptop → robot connectivity (the painful bit)

Plug your laptop's ethernet adapter into any open port on the Go1's internal switch. The adapter should get `192.168.123.100` via DHCP or static config.

### macOS routing fix

macOS tends to assign `192.168.123.100` to multiple interfaces (WiFi, Thunderbolt-bridge, USB ethernet) simultaneously, and then picks the wrong one. Fix:

```bash
# See where .100 lives right now
ifconfig | grep -B5 "192.168.123.100"

# Remove it from anything that isn't your physical ethernet adapter
sudo ifconfig en0 -alias 192.168.123.100   # WiFi
sudo ifconfig en3 -alias 192.168.123.100   # Thunderbolt bridge

# Force the subnet route through the right interface (replace en6 as needed)
sudo route add -net 192.168.123.0/24 -interface en6

# Verify
route -n get 192.168.123.14   # should show "interface: en6"
ping -c3 192.168.123.14
```

This resets on every reboot. For a persistent fix write a launchd plist; day-to-day we just re-run the three `sudo` lines.

### Verify all boards

```bash
for ip in 10 13 14 15 161; do
  printf "192.168.123.%-3s  " "$ip"
  if ping -c1 -W1 192.168.123.$ip >/dev/null 2>&1; then
    echo "UP"
  else
    echo "down"
  fi
done
```

Expected: .10, .14, .15, .161 **UP**; .13 **down** (head Nano hardware issue).

## Internet on the Jetsons

The body Nano (.14) has no WiFi. The Xavier NX (.15) has a USB WiFi dongle (RTL8192CU on SSID `Otto51 1`). The Pi has its own WiFi + LTE but we don't route through it.

The RTL8192CU driver on .15 drops unicast packets after a while, which kills apt, pip, and git pulls. When that happens, run:

```bash
ssh unitree@192.168.123.15
cd ~/go1-autonomy-stack
./scripts/fix_net.sh
```

The script does:
1. Sets DNS to Google (8.8.8.8, 8.8.4.4), ignore DHCP-assigned DNS.
2. Lowers the WiFi route metric (so it wins over the internal eth0).
3. Cycles the connection `down` → `up`.
4. Inserts a permanent ARP entry for the home router (works around the kernel driver bug).
5. Pings 8.8.8.8 to confirm.

## SSH shortcuts

In `~/.ssh/config` on your laptop, something like:

```
Host go1-nano
  HostName 192.168.123.14
  User unitree
  IdentityFile ~/.ssh/id_ed25519

Host go1-xavier
  HostName 192.168.123.15
  User unitree
  ProxyJump go1-nano   # optional, if your subnet route is flaky
```

Then: `ssh go1-nano` and `ssh go1-xavier`.
