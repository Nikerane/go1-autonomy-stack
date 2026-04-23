#!/bin/bash
# Go1 Hardware Health Check
# Tests all boards, cameras, network, and sensors
# Run on Xavier NX (192.168.123.14)

RED='\033[0;31m'
GRN='\033[0;32m'
YLW='\033[1;33m'
CYN='\033[0;36m'
NC='\033[0m'

ok() { echo -e "  ${GRN}[OK]${NC} $1"; }
fail() { echo -e "  ${RED}[FAIL]${NC} $1"; }
warn() { echo -e "  ${YLW}[WARN]${NC} $1"; }
info() { echo -e "  ${CYN}[INFO]${NC} $1"; }

echo "============================================"
echo "  Go1 Hardware Health Check"
echo "  $(date)"
echo "============================================"
echo ""

# --- Network ---
echo "--- NETWORK ---"

ping -c 1 -W 2 192.168.123.10 > /dev/null 2>&1 && ok "MCU (.10) reachable" || fail "MCU (.10) unreachable"
ping -c 1 -W 2 192.168.123.14 > /dev/null 2>&1 && ok "Xavier NX (.14) reachable (this board)" || fail "Xavier NX (.14)"
ping -c 1 -W 2 192.168.123.15 > /dev/null 2>&1 && ok "Nano body (.15) reachable" || fail "Nano body (.15) unreachable"
ping -c 1 -W 2 192.168.123.13 > /dev/null 2>&1 && ok "Nano head (.13) reachable" || fail "Nano head (.13) unreachable - check cable inside head"
ping -c 1 -W 2 192.168.123.161 > /dev/null 2>&1 && ok "Raspberry Pi (.161) reachable" || fail "Raspberry Pi (.161) unreachable"

echo ""

# --- SSH ---
echo "--- SSH ACCESS ---"

ssh -o ConnectTimeout=3 -o BatchMode=yes unitree@192.168.123.14 'echo ok' > /dev/null 2>&1 && ok "SSH to Xavier (.14) - key auth" || warn "SSH to Xavier (.14) failed"
sshpass -p 123 ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no unitree@192.168.123.15 'echo ok' > /dev/null 2>&1 && ok "SSH to Nano body (.15) - pw:123" || fail "SSH to Nano body (.15)"
sshpass -p 123 ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no unitree@192.168.123.13 'echo ok' > /dev/null 2>&1 && ok "SSH to Nano head (.13) - pw:123" || fail "SSH to Nano head (.13) - board offline"
sshpass -p 123 ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no pi@192.168.123.161 'echo ok' > /dev/null 2>&1 && ok "SSH to Pi (.161) - pw:123" || fail "SSH to Pi (.161)"

echo ""

# --- Cameras ---
echo "--- CAMERAS (Xavier NX) ---"

if [ -e /dev/video0 ]; then
    ok "/dev/video0 exists"
    fuser /dev/video0 > /dev/null 2>&1 && warn "/dev/video0 in use by PID $(fuser /dev/video0 2>&1 | awk '{print $1}')" || ok "/dev/video0 is free"
else
    fail "/dev/video0 not found"
fi

if [ -e /dev/video1 ]; then
    ok "/dev/video1 exists"
    fuser /dev/video1 > /dev/null 2>&1 && warn "/dev/video1 in use by PID $(fuser /dev/video1 2>&1 | awk '{print $1}')" || ok "/dev/video1 is free"
else
    fail "/dev/video1 not found"
fi

echo ""
echo "--- CAMERAS (Nano body .15) ---"
NANO_CAM=$(sshpass -p 123 ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no unitree@192.168.123.15 'ls /dev/video0 2>/dev/null && echo yes || echo no' 2>/dev/null)
if [ "$NANO_CAM" = "yes" ]; then
    ok "Nano /dev/video0 exists (belly camera)"
else
    fail "Nano /dev/video0 not found"
fi

echo ""
echo "--- CAMERAS (Nano head .13) ---"
HEAD_CAM=$(sshpass -p 123 ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no unitree@192.168.123.13 'ls /dev/video0 /dev/video1 2>/dev/null | wc -l' 2>/dev/null)
if [ -n "$HEAD_CAM" ] && [ "$HEAD_CAM" -ge 1 ]; then
    ok "Head cameras found: $HEAD_CAM devices"
else
    fail "Head cameras unreachable (board offline)"
fi

echo ""

# --- Sport Mode ---
echo "--- SPORT MODE (Pi .161) ---"
SPORT=$(sshpass -p 123 ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no pi@192.168.123.161 'pgrep -f Legged_sport > /dev/null && echo running || echo stopped' 2>/dev/null)
if [ "$SPORT" = "running" ]; then
    ok "Legged_sport is running"
else
    fail "Legged_sport not running"
fi

echo ""

# --- Motor Temps ---
echo "--- MOTOR TEMPERATURES ---"
python3 -c "
import socket, struct, time
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(2)
try:
    sock.bind(('0.0.0.0', 8091))
except:
    sock.bind(('0.0.0.0', 8092))
cmd = bytearray(129)
cmd[0]=0xFE;cmd[1]=0xEF;cmd[2]=0xEE
sock.sendto(bytes(cmd), ('192.168.123.161', 8082))
time.sleep(0.1)
for _ in range(5):
    sock.sendto(bytes(cmd), ('192.168.123.161', 8082))
    time.sleep(0.05)
try:
    data,_ = sock.recvfrom(2048)
    if len(data)>=1087:
        off=22+53  # skip header+IMU
        names=['FR_hip','FR_thigh','FR_calf','FL_hip','FL_thigh','FL_calf',
               'RR_hip','RR_thigh','RR_calf','RL_hip','RL_thigh','RL_calf']
        hot=False
        for i in range(12):
            m=struct.unpack_from('<Bfffffffb2I',data,off)
            off+=38
            temp=m[8]
            status='OK' if temp<50 else ('WARM' if temp<70 else 'HOT!')
            color='\033[0;32m' if temp<50 else ('\033[1;33m' if temp<70 else '\033[0;31m')
            print(f'  {color}[{status}]\033[0m {names[i]}: {temp}C')
            if temp>=70: hot=True
        # Battery
        off_bms=22+53+20*38
        bms=struct.unpack_from('<BBBBiH',data,off_bms)
        print(f'  \033[0;36m[INFO]\033[0m Battery: {bms[3]}%  Current: {bms[4]} mA')
        if hot:
            print(f'  \033[0;31m[WARN] Motors are HOT! Run: cd ~/K1/build && ./sit_down 7\033[0m')
except socket.timeout:
    print('  \033[0;31m[FAIL]\033[0m Could not read motor state (UDP timeout)')
sock.close()
" 2>&1

echo ""

# --- Dashboard ---
echo "--- DASHBOARD ---"
if pgrep -f "python3.*tri_stream" > /dev/null; then
    ok "Dashboard is running"
    info "Access at http://0.0.0.0:8080"
else
    warn "Dashboard is not running. Start with: ./start_dashboard.sh"
fi

echo ""
echo "============================================"
echo "  Health check complete"
echo "============================================"
