#!/usr/bin/env python3
"""Go1 Dashboard - cameras + sensor data + real-time graphs over HTTP."""
import sys, subprocess, threading, http.server, time, json, struct, socket, math

frames = {0: b'', 1: b'', 2: b''}
lock = threading.Lock()

# --- Sensor state (from HighState UDP) ---
sensor_data = {
    'imu': {'rpy': [0,0,0], 'gyro': [0,0,0], 'accel': [0,0,0], 'temp': 0, 'quat': [1,0,0,0]},
    'battery': {'soc': 0, 'current': 0, 'cell_voltages': [], 'temp_bq': [0,0], 'temp_mcu': [0,0]},
    'motors': [{'q':0,'dq':0,'tau':0,'temp':0} for _ in range(12)],
    'foot_force': [0,0,0,0],
    'mode': 0, 'gait': 0,
    'velocity': [0,0,0], 'yaw_speed': 0,
    'body_height': 0.28, 'foot_raise': 0.08,
    'position': [0,0,0],
    'connected': False, 'last_update': 0,
}
sensor_lock = threading.Lock()

MOTOR_FMT = '<Bfffffffb2I'
MOTOR_SIZE = struct.calcsize(MOTOR_FMT)
BMS_FMT = '<BBBBiH2b2b10H'
BMS_SIZE = struct.calcsize(BMS_FMT)

def parse_high_state(data):
    if len(data) < 1087:
        return None
    off = 0
    head = struct.unpack_from('<2BBBIIIH', data, off); off += 22
    quat = struct.unpack_from('<4f', data, off); off += 16
    gyro = struct.unpack_from('<3f', data, off); off += 12
    accel = struct.unpack_from('<3f', data, off); off += 12
    rpy = struct.unpack_from('<3f', data, off); off += 12
    imu_temp = struct.unpack_from('<b', data, off)[0]; off += 1
    motors = []
    for i in range(20):
        m = struct.unpack_from(MOTOR_FMT, data, off); off += MOTOR_SIZE
        motors.append({'mode': m[0], 'q': m[1], 'dq': m[2], 'ddq': m[3], 'tau': m[4], 'temp': m[8]})
    bms = struct.unpack_from(BMS_FMT, data, off); off += BMS_SIZE
    foot_force = struct.unpack_from('<4h', data, off); off += 8
    foot_force_est = struct.unpack_from('<4h', data, off); off += 8
    mode = struct.unpack_from('<B', data, off)[0]; off += 1
    progress = struct.unpack_from('<f', data, off)[0]; off += 4
    gait = struct.unpack_from('<B', data, off)[0]; off += 1
    foot_raise = struct.unpack_from('<f', data, off)[0]; off += 4
    position = struct.unpack_from('<3f', data, off); off += 12
    body_height = struct.unpack_from('<f', data, off)[0]; off += 4
    velocity = struct.unpack_from('<3f', data, off); off += 12
    yaw_speed = struct.unpack_from('<f', data, off)[0]; off += 4
    return {
        'imu': {'quat': list(quat), 'gyro': [round(g,3) for g in gyro],
                'accel': [round(a,3) for a in accel],
                'rpy': [round(math.degrees(r),2) for r in rpy], 'temp': imu_temp},
        'battery': {'soc': bms[3], 'current': bms[4],
                    'cell_voltages': list(bms[8:18]),
                    'temp_bq': [bms[6], bms[7]], 'temp_mcu': [bms[8], bms[9]]},
        'motors': [{'q': round(motors[i]['q'],3), 'dq': round(motors[i]['dq'],2),
                     'tau': round(motors[i]['tau'],2), 'temp': motors[i]['temp']} for i in range(12)],
        'foot_force': list(foot_force),
        'mode': mode, 'gait': gait,
        'velocity': [round(v,3) for v in velocity],
        'yaw_speed': round(yaw_speed, 3),
        'body_height': round(body_height, 3),
        'foot_raise': round(foot_raise, 3),
        'position': [round(p, 3) for p in position],
        'connected': True, 'last_update': time.time()
    }

def sensor_reader():
    HIGHCMD_SIZE = 129
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1.0)
    sock.bind(('0.0.0.0', 8095))
    target = ('192.168.123.161', 8082)
    idle_cmd = bytearray(HIGHCMD_SIZE)
    idle_cmd[0] = 0xFE; idle_cmd[1] = 0xEF; idle_cmd[2] = 0xEE
    while True:
        try:
            sock.sendto(bytes(idle_cmd), target)
            data, addr = sock.recvfrom(2048)
            parsed = parse_high_state(data)
            if parsed:
                with sensor_lock:
                    sensor_data.update(parsed)
        except socket.timeout:
            with sensor_lock:
                sensor_data['connected'] = False
        except Exception as e:
            print('sensor_reader error:', e)
        time.sleep(0.05)

# --- HTML Dashboard with Graphs ---
HTML = b'''<!DOCTYPE html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Go1 Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0a0a;color:#fff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif}
.hdr{padding:16px 28px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #1a1a1a}
.logo{display:flex;align-items:center;gap:8px;font-size:18px;font-weight:700}
.dot{width:8px;height:8px;background:#22c55e;border-radius:50%;animation:p 2s infinite}
@keyframes p{0%,100%{opacity:1}50%{opacity:.4}}
.tabs{display:flex;gap:3px;background:#111;padding:3px;border-radius:10px}
.tab{padding:6px 16px;border-radius:7px;font-size:12px;color:#555;cursor:pointer;border:none;background:none}
.tab.on{background:#222;color:#fff}
.badge{padding:5px 14px;border-radius:16px;font-size:12px;font-weight:500}
.bg{background:#162312;color:#22c55e}.br{background:#290f0f;color:#ef4444}
.main{padding:20px 28px;display:flex;flex-direction:column;gap:16px}
.row{display:grid;gap:12px}
.r2{grid-template-columns:1fr 1fr}
.r3{grid-template-columns:1fr 1fr 1fr}
.r4{grid-template-columns:1fr 1fr 1fr 1fr}
.r5{grid-template-columns:1fr 1fr 1fr 1fr 1fr}
.card{background:linear-gradient(145deg,#131313,#181818);border:1px solid #1e1e1e;border-radius:12px;overflow:hidden}
.card:hover{border-color:#2a2a2a}
.ch{padding:10px 14px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #1a1a1a}
.ct{font-size:12px;font-weight:600}.cs{font-size:10px;color:#444;margin-top:1px}
.cb{font-size:10px;padding:2px 7px;border-radius:5px;font-weight:600}
.cb-g{background:#162312;color:#22c55e}.cb-b{background:#0c1929;color:#3b82f6}
.cb-p{background:#1a0f29;color:#a855f7}.cb-r{background:#290f0f;color:#ef4444}
.ci{padding:5px}.ci img{width:100%;height:auto;display:block;border-radius:6px;background:#000;min-height:80px}
.sec{font-size:11px;color:#444;text-transform:uppercase;letter-spacing:1px;font-weight:600;padding:4px 0}
.pnl{background:linear-gradient(145deg,#131313,#181818);border:1px solid #1e1e1e;border-radius:12px;padding:14px}
.pnl h4{font-size:11px;color:#444;margin-bottom:10px;font-weight:600;text-transform:uppercase;letter-spacing:.5px}
.m{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #111;font-size:11px}
.m:last-child{border:none}
.ml{color:#444}.mv{color:#fff;font-weight:500;font-variant-numeric:tabular-nums}
.grn{color:#22c55e}.red{color:#ef4444}.blu{color:#3b82f6}.ylw{color:#eab308}.prp{color:#a855f7}.cyn{color:#06b6d4}
canvas{width:100%;height:120px;border-radius:6px;background:#0c0c0c;display:block;margin-top:6px}
.graph-card{padding:14px}
.graph-card h4{font-size:11px;color:#444;margin-bottom:2px;font-weight:600;text-transform:uppercase;letter-spacing:.5px}
.graph-legend{display:flex;gap:12px;font-size:10px;color:#555;margin-top:4px}
.graph-legend span{display:flex;align-items:center;gap:4px}
.graph-legend i{width:8px;height:3px;border-radius:1px;display:inline-block}
.bbar{height:5px;background:#1a1a1a;border-radius:3px;margin-top:6px;overflow:hidden}
.bfill{height:100%;border-radius:3px;transition:width .5s}
.motor-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
.mc{background:#111;border:1px solid #1a1a1a;border-radius:8px;padding:10px}
.mc h5{font-size:10px;color:#666;margin-bottom:6px;font-weight:600}
.mc .sub{font-size:8px;color:#333;margin-bottom:4px}
.mr{display:flex;justify-content:space-between;font-size:10px;padding:2px 0}
.mr span:first-child{color:#444}.mr span:last-child{color:#ccc;font-variant-numeric:tabular-nums}
.foot-g{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:6px}
.fb{background:#111;border-radius:4px;padding:6px 8px;display:flex;justify-content:space-between;font-size:10px}
.fb .fl{color:#444}.fb .fv{font-weight:600;font-variant-numeric:tabular-nums}
.sbar{display:flex;gap:20px;padding:10px 28px;border-top:1px solid #1a1a1a;font-size:11px;color:#444;position:fixed;bottom:0;left:0;right:0;background:#0a0a0a;z-index:10}
.sbar span{font-variant-numeric:tabular-nums}
</style></head><body>

<div class="hdr">
  <div class="logo"><div class="dot"></div>Go1 Dashboard</div>
  <div class="tabs">
    <button class="tab" onclick="stab('all',this)">All</button>
    <button class="tab on" onclick="stab('cam',this)">Cameras</button>
    <button class="tab" onclick="stab('tel',this)">Telemetry</button>
    <button class="tab" onclick="stab('mot',this)">Motors</button>
  </div>
  <div class="badge bg" id="connB">System Online</div>
</div>

<div class="main">

<!-- CAMERAS -->
<div id="s-cam">
<div class="sec">Camera Feeds</div>
<div class="row r3">
  <div class="card"><div class="ch"><div><div class="ct">Left Stereo</div><div class="cs">Xavier /dev/video0</div></div><div class="cb cb-g">LIVE</div></div><div class="ci"><img id="c0"></div></div>
  <div class="card"><div class="ch"><div><div class="ct">Right Stereo</div><div class="cs">Xavier /dev/video1</div></div><div class="cb cb-b">LIVE</div></div><div class="ci"><img id="c1"></div></div>
  <div class="card"><div class="ch"><div><div class="ct">Belly (Ground)</div><div class="cs">Nano /dev/video0 via UDP</div></div><div class="cb cb-p">LIVE</div></div><div class="ci"><img id="c2"></div></div>
</div>
</div>

<!-- TELEMETRY GRAPHS -->
<div id="s-tel">
<div class="sec">Telemetry Graphs</div>
<div class="row r2">
  <div class="card graph-card">
    <h4>IMU Orientation</h4>
    <div class="graph-legend"><span><i style="background:#3b82f6"></i>Roll (deg)</span><span><i style="background:#22c55e"></i>Pitch (deg)</span><span><i style="background:#eab308"></i>Yaw (deg)</span></div>
    <canvas id="g-imu"></canvas>
  </div>
  <div class="card graph-card">
    <h4>Gyroscope</h4>
    <div class="graph-legend"><span><i style="background:#3b82f6"></i>X (rad/s)</span><span><i style="background:#22c55e"></i>Y (rad/s)</span><span><i style="background:#eab308"></i>Z (rad/s)</span></div>
    <canvas id="g-gyro"></canvas>
  </div>
</div>
<div class="row r2">
  <div class="card graph-card">
    <h4>Motor Temperatures</h4>
    <div class="graph-legend"><span><i style="background:#3b82f6"></i>FR (deg C)</span><span><i style="background:#22c55e"></i>FL (deg C)</span><span><i style="background:#eab308"></i>RR (deg C)</span><span><i style="background:#a855f7"></i>RL (deg C)</span></div>
    <canvas id="g-mtemp"></canvas>
  </div>
  <div class="card graph-card">
    <h4>Foot Force</h4>
    <div class="graph-legend"><span><i style="background:#3b82f6"></i>FR (N)</span><span><i style="background:#22c55e"></i>FL (N)</span><span><i style="background:#eab308"></i>RR (N)</span><span><i style="background:#a855f7"></i>RL (N)</span></div>
    <canvas id="g-foot"></canvas>
  </div>
</div>
<div class="row r2">
  <div class="card graph-card">
    <h4>Velocity</h4>
    <div class="graph-legend"><span><i style="background:#3b82f6"></i>Forward (m/s)</span><span><i style="background:#22c55e"></i>Lateral (m/s)</span><span><i style="background:#eab308"></i>Yaw (rad/s)</span></div>
    <canvas id="g-vel"></canvas>
  </div>
  <div class="card graph-card">
    <h4>Accelerometer</h4>
    <div class="graph-legend"><span><i style="background:#3b82f6"></i>X (m/s2)</span><span><i style="background:#22c55e"></i>Y (m/s2)</span><span><i style="background:#eab308"></i>Z (m/s2)</span></div>
    <canvas id="g-accel"></canvas>
  </div>
</div>

<!-- Numeric panels -->
<div class="row r4">
  <div class="pnl">
    <h4>Battery</h4>
    <div class="m"><span class="ml">Charge</span><span class="mv grn" id="batt-soc">--%</span></div>
    <div class="m"><span class="ml">Current</span><span class="mv" id="batt-cur">-- mA</span></div>
    <div class="m"><span class="ml">Avg Cell</span><span class="mv" id="batt-v">-- V</span></div>
    <div class="bbar"><div class="bfill" id="bbar" style="width:0%;background:#22c55e"></div></div>
  </div>
  <div class="pnl">
    <h4>Motion</h4>
    <div class="m"><span class="ml">Mode</span><span class="mv ylw" id="s-mode">--</span></div>
    <div class="m"><span class="ml">Gait</span><span class="mv ylw" id="s-gait">--</span></div>
    <div class="m"><span class="ml">Body Height</span><span class="mv" id="s-bh">-- m</span></div>
    <div class="m"><span class="ml">Foot Raise</span><span class="mv" id="s-fr">-- m</span></div>
  </div>
  <div class="pnl">
    <h4>IMU Numeric</h4>
    <div class="m"><span class="ml">Roll</span><span class="mv blu" id="n-roll">--</span></div>
    <div class="m"><span class="ml">Pitch</span><span class="mv blu" id="n-pitch">--</span></div>
    <div class="m"><span class="ml">Yaw</span><span class="mv blu" id="n-yaw">--</span></div>
    <div class="m"><span class="ml">IMU Temp</span><span class="mv" id="n-itemp">--</span></div>
  </div>
  <div class="pnl">
    <h4>Foot Force</h4>
    <div class="foot-g">
      <div class="fb"><span class="fl">FR</span><span class="fv grn" id="ff0">-- N</span></div>
      <div class="fb"><span class="fl">FL</span><span class="fv grn" id="ff1">-- N</span></div>
      <div class="fb"><span class="fl">RR</span><span class="fv blu" id="ff2">-- N</span></div>
      <div class="fb"><span class="fl">RL</span><span class="fv blu" id="ff3">-- N</span></div>
    </div>
  </div>
</div>
</div>

<!-- MOTORS -->
<div id="s-mot">
<div class="sec">Joint Motors (12 DOF)</div>
<div class="motor-grid">
  <div class="mc"><h5>FR Leg</h5><div class="sub">angle (rad) | torque (Nm) | temp</div>
    <div class="mr"><span>Hip</span><span id="m0">--</span></div>
    <div class="mr"><span>Thigh</span><span id="m1">--</span></div>
    <div class="mr"><span>Calf</span><span id="m2">--</span></div>
  </div>
  <div class="mc"><h5>FL Leg</h5><div class="sub">angle (rad) | torque (Nm) | temp</div>
    <div class="mr"><span>Hip</span><span id="m3">--</span></div>
    <div class="mr"><span>Thigh</span><span id="m4">--</span></div>
    <div class="mr"><span>Calf</span><span id="m5">--</span></div>
  </div>
  <div class="mc"><h5>RR Leg</h5><div class="sub">angle (rad) | torque (Nm) | temp</div>
    <div class="mr"><span>Hip</span><span id="m6">--</span></div>
    <div class="mr"><span>Thigh</span><span id="m7">--</span></div>
    <div class="mr"><span>Calf</span><span id="m8">--</span></div>
  </div>
  <div class="mc"><h5>RL Leg</h5><div class="sub">angle (rad) | torque (Nm) | temp</div>
    <div class="mr"><span>Hip</span><span id="m9">--</span></div>
    <div class="mr"><span>Thigh</span><span id="m10">--</span></div>
    <div class="mr"><span>Calf</span><span id="m11">--</span></div>
  </div>
</div>
</div>

<!-- NETWORK -->
<div class="sec" style="margin-top:4px">Network</div>
<div class="row r5" style="margin-bottom:50px">
  <div class="pnl"><h4>Xavier NX</h4><div class="m"><span class="ml">192.168.123.14</span><span class="mv grn">Online</span></div><div class="m"><span class="ml">Cameras</span><span class="mv">2</span></div></div>
  <div class="pnl"><h4>Nano Body</h4><div class="m"><span class="ml">192.168.123.15</span><span class="mv grn">Online</span></div><div class="m"><span class="ml">Cameras</span><span class="mv">1</span></div></div>
  <div class="pnl"><h4>Nano Head</h4><div class="m"><span class="ml">192.168.123.13</span><span class="mv red">Offline</span></div><div class="m"><span class="ml">Cameras</span><span class="mv">0/2</span></div></div>
  <div class="pnl"><h4>Raspberry Pi</h4><div class="m"><span class="ml">192.168.123.161</span><span class="mv grn">Online</span></div><div class="m"><span class="ml">Role</span><span class="mv">Sport Mode</span></div></div>
  <div class="pnl"><h4>MCU</h4><div class="m"><span class="ml">192.168.123.10</span><span class="mv grn">Online</span></div><div class="m"><span class="ml">Role</span><span class="mv">Motor Ctrl</span></div></div>
</div>

</div>

<div class="sbar">
  <span>Frames: <span id="fps">0</span></span>
  <span>Uptime: <span id="upt">0s</span></span>
  <span>Sensor: <span id="ss">connecting...</span></span>
</div>

<script>
var total=0,start=Date.now(),N=200;
var modes={0:'idle',1:'force stand',2:'vel walk',3:'pos walk',5:'stand down',6:'stand up',7:'damping',8:'recovery',9:'backflip',10:'jump yaw',12:'dance1',13:'dance2'};
var gaits={0:'idle',1:'trot',2:'trot run',3:'climb stair',4:'obstacle'};

/* ---- Graph engine ---- */
function makeHistory(count){var h=[];for(var i=0;i<count;i++){h.push(new Float32Array(N))}return h}
var H={
  imu:makeHistory(3), gyro:makeHistory(3), mtemp:makeHistory(4),
  foot:makeHistory(4), vel:makeHistory(3), accel:makeHistory(3)
};
function pushH(buf,vals){
  for(var i=0;i<vals.length;i++){
    buf[i].copyWithin(0,1);
    buf[i][N-1]=vals[i];
  }
}
function drawGraph(canvasId,buf,colors,yMin,yMax,unit){
  var c=document.getElementById(canvasId);
  if(!c)return;
  var ctx=c.getContext('2d');
  var W=c.width=c.offsetWidth*2;
  var Hh=c.height=c.offsetHeight*2;
  ctx.clearRect(0,0,W,Hh);

  // grid
  ctx.strokeStyle='#1a1a1a';ctx.lineWidth=1;
  var steps=4;
  for(var i=0;i<=steps;i++){
    var y=Hh*i/steps;
    ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke();
    var val=yMax-(yMax-yMin)*i/steps;
    ctx.fillStyle='#333';ctx.font='18px -apple-system,sans-serif';
    ctx.fillText(val.toFixed(1)+' '+unit,4,y-4);
  }
  // zero line
  if(yMin<0&&yMax>0){
    var zy=Hh*(yMax/(yMax-yMin));
    ctx.strokeStyle='#2a2a2a';ctx.lineWidth=1;
    ctx.beginPath();ctx.moveTo(0,zy);ctx.lineTo(W,zy);ctx.stroke();
  }
  // lines
  for(var s=0;s<buf.length;s++){
    ctx.strokeStyle=colors[s];ctx.lineWidth=2;ctx.beginPath();
    for(var i=0;i<N;i++){
      var x=i*W/(N-1);
      var v=buf[s][i];
      var y=Hh*(1-(v-yMin)/(yMax-yMin));
      y=Math.max(0,Math.min(Hh,y));
      if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);
    }
    ctx.stroke();
  }
  // latest values
  ctx.font='bold 20px -apple-system,sans-serif';
  for(var s=0;s<buf.length;s++){
    var lv=buf[s][N-1];
    ctx.fillStyle=colors[s];
    ctx.fillText(lv.toFixed(2)+' '+unit, W-140, 24+s*22);
  }
}
var graphColors3=['#3b82f6','#22c55e','#eab308'];
var graphColors4=['#3b82f6','#22c55e','#eab308','#a855f7'];

/* ---- Tabs ---- */
function stab(t,el){
  document.querySelectorAll('.tab').forEach(function(b){b.classList.remove('on')});
  el.classList.add('on');
  var sc=document.getElementById('s-cam').style;
  var st=document.getElementById('s-tel').style;
  var sm=document.getElementById('s-mot').style;
  sc.display=st.display=sm.display='';
  if(t==='cam'){st.display='none';sm.display='none'}
  if(t==='tel'){sc.display='none';sm.display='none'}
  if(t==='mot'){sc.display='none';st.display='none'}
}

/* ---- Camera polling ---- */
function poll(id,cam){
  var img=document.getElementById(id);
  var f=function(){img.src='/frame/'+cam+'?t='+Date.now()};
  img.onload=function(){total++;document.getElementById('fps').textContent=total;setTimeout(f,80)};
  img.onerror=function(){setTimeout(f,500)};
  f();
}
poll('c0',0);poll('c1',1);poll('c2',2);
/* Default to cameras tab */
document.getElementById('s-tel').style.display='none';
document.getElementById('s-mot').style.display='none';

/* ---- Sensor update ---- */
function updateSensors(){
  var x=new XMLHttpRequest();
  x.open('GET','/sensors?t='+Date.now());
  x.onload=function(){
    try{
      var d=JSON.parse(x.responseText);
      var c=d.connected;
      document.getElementById('ss').textContent=c?'live':'disconnected';
      document.getElementById('ss').style.color=c?'#22c55e':'#ef4444';
      if(!c)return;

      // Push to graph histories
      pushH(H.imu, d.imu.rpy);
      pushH(H.gyro, d.imu.gyro);
      pushH(H.accel, d.imu.accel);
      // Motor temps: max of each leg's 3 joints
      var mt=[Math.max(d.motors[0].temp,d.motors[1].temp,d.motors[2].temp),
              Math.max(d.motors[3].temp,d.motors[4].temp,d.motors[5].temp),
              Math.max(d.motors[6].temp,d.motors[7].temp,d.motors[8].temp),
              Math.max(d.motors[9].temp,d.motors[10].temp,d.motors[11].temp)];
      pushH(H.mtemp, mt);
      pushH(H.foot, d.foot_force);
      pushH(H.vel, [d.velocity[0],d.velocity[1],d.yaw_speed]);

      // Numeric updates
      var el=document.getElementById;
      document.getElementById('n-roll').textContent=d.imu.rpy[0].toFixed(1)+'\\u00b0';
      document.getElementById('n-pitch').textContent=d.imu.rpy[1].toFixed(1)+'\\u00b0';
      document.getElementById('n-yaw').textContent=d.imu.rpy[2].toFixed(1)+'\\u00b0';
      document.getElementById('n-itemp').textContent=d.imu.temp+'\\u00b0C';

      var soc=d.battery.soc;
      document.getElementById('batt-soc').textContent=soc+'%';
      document.getElementById('batt-soc').style.color=soc>20?'#22c55e':'#ef4444';
      document.getElementById('batt-cur').textContent=d.battery.current+' mA';
      var cells=d.battery.cell_voltages||[];
      if(cells.length>0){
        var avg=cells.reduce(function(a,b){return a+b},0)/cells.length;
        document.getElementById('batt-v').textContent=(avg/1000).toFixed(2)+' V';
      }
      document.getElementById('bbar').style.width=soc+'%';
      document.getElementById('bbar').style.background=soc>20?'#22c55e':'#ef4444';

      document.getElementById('s-mode').textContent=modes[d.mode]||('mode '+d.mode);
      document.getElementById('s-gait').textContent=gaits[d.gait]||('gait '+d.gait);
      document.getElementById('s-bh').textContent=d.body_height.toFixed(3)+' m';
      document.getElementById('s-fr').textContent=d.foot_raise.toFixed(3)+' m';

      document.getElementById('ff0').textContent=d.foot_force[0]+' N';
      document.getElementById('ff1').textContent=d.foot_force[1]+' N';
      document.getElementById('ff2').textContent=d.foot_force[2]+' N';
      document.getElementById('ff3').textContent=d.foot_force[3]+' N';

      for(var i=0;i<12;i++){
        var m=d.motors[i];
        var el2=document.getElementById('m'+i);
        var tc=m.temp>=70?'color:#ef4444':m.temp>=50?'color:#eab308':'color:#ccc';
        if(el2)el2.innerHTML=m.q.toFixed(2)+' rad | '+m.tau.toFixed(1)+' Nm | <span style=\"'+tc+'\">'+m.temp+'\\u00b0C</span>';
      }
    }catch(e){}
  };
  x.send();
}
setInterval(updateSensors,200);

/* ---- Draw graphs at 10fps ---- */
setInterval(function(){
  drawGraph('g-imu',H.imu,graphColors3,-90,90,'deg');
  drawGraph('g-gyro',H.gyro,graphColors3,-3,3,'rad/s');
  drawGraph('g-mtemp',H.mtemp,graphColors4,20,90,'C');
  drawGraph('g-foot',H.foot,graphColors4,-50,500,'N');
  drawGraph('g-vel',H.vel,graphColors3,-1.5,1.5,'m/s');
  drawGraph('g-accel',H.accel,graphColors3,-15,15,'m/s2');
},100);

/* ---- Uptime ---- */
setInterval(function(){
  var s=Math.floor((Date.now()-start)/1000);
  var m=Math.floor(s/60);s=s%60;
  var h=Math.floor(m/60);m=m%60;
  document.getElementById('upt').textContent=(h?h+'h ':'')+(m?m+'m ':'')+s+'s';
},1000);
</script></body></html>'''

# --- Camera capture ---
def capture_local(dev_index, device, width, height):
    while True:
        try:
            proc = subprocess.Popen(
                ['ffmpeg','-f','v4l2','-video_size','%dx%d'%(width,height),
                 '-framerate','15','-i',device,
                 '-f','image2pipe','-vcodec','mjpeg','-q:v','5','-'],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            parse_mjpeg(proc.stdout, dev_index)
        except Exception as e:
            print('capture_local error:', e)
        time.sleep(2)

def capture_remote(dev_index, host, port):
    import socket as _socket
    sock = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', port)); sock.settimeout(5)
    buf = b''
    while True:
        try:
            data, addr = sock.recvfrom(65536); buf += data
            while True:
                soi = buf.find(b'\xff\xd8')
                if soi < 0: buf = b''; break
                eoi = buf.find(b'\xff\xd9', soi+2)
                if eoi < 0: buf = buf[soi:]; break
                with lock: frames[dev_index] = buf[soi:eoi+2]
                buf = buf[eoi+2:]
        except _socket.timeout: continue
        except Exception as e: print('capture_remote error:', e); time.sleep(1)

def parse_mjpeg(pipe, dev_index):
    buf = b''
    while True:
        chunk = pipe.read(4096)
        if not chunk: break
        buf += chunk
        while True:
            soi = buf.find(b'\xff\xd8')
            if soi < 0: buf = b''; break
            eoi = buf.find(b'\xff\xd9', soi+2)
            if eoi < 0: buf = buf[soi:]; break
            with lock: frames[dev_index] = buf[soi:eoi+2]
            buf = buf[eoi+2:]

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200); self.send_header('Content-Type','text/html'); self.end_headers()
            self.wfile.write(HTML)
        elif self.path.startswith('/frame/'):
            try: cam = int(self.path.split('/')[2].split('?')[0])
            except: cam = 0
            with lock: f = frames.get(cam, b'')
            if f:
                self.send_response(200)
                self.send_header('Content-Type','image/jpeg')
                self.send_header('Content-Length',str(len(f)))
                self.send_header('Cache-Control','no-cache, no-store')
                self.end_headers(); self.wfile.write(f)
            else:
                self.send_response(503); self.end_headers()
        elif self.path.startswith('/sensors'):
            with sensor_lock: data = json.dumps(sensor_data)
            self.send_response(200); self.send_header('Content-Type','application/json')
            self.send_header('Cache-Control','no-cache'); self.end_headers()
            self.wfile.write(data.encode())
        else:
            self.send_response(404); self.end_headers()
    def log_message(self, *a): pass

if __name__ == '__main__':
    threading.Thread(target=capture_local, args=(0, '/dev/video0', 928, 400), daemon=True).start()
    threading.Thread(target=capture_local, args=(1, '/dev/video1', 928, 400), daemon=True).start()
    threading.Thread(target=capture_remote, args=(2, '0.0.0.0', 5002), daemon=True).start()
    subprocess.Popen(
        ['ssh', 'unitree@192.168.123.15',
         'ffmpeg -f v4l2 -video_size 928x400 -framerate 15 -i /dev/video0 '
         '-f mjpeg -q:v 5 udp://192.168.123.14:5002'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    threading.Thread(target=sensor_reader, daemon=True).start()
    print('Go1 Dashboard at http://0.0.0.0:8080')
    srv = http.server.HTTPServer(('0.0.0.0', 8080), Handler)
    srv.serve_forever()
