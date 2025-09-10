// 简单的设备管理和遥操作逻辑
const statusList = document.getElementById('status-list');
const armsList = document.getElementById('arms-list');
const camerasList = document.getElementById('cameras-list');
const configForm = document.getElementById('config-form');
const teleopLog = document.getElementById('teleop-log');

function fetchStatus() {
  ['vr', 'arm', 'camera'].forEach(type => {
    fetch(`/devices/${type}`)
      .then(res => res.json())
      .then(data => {
        const html = `<strong>${type.toUpperCase()}：</strong> ${data.devices.map(d => `<span style='color:green'>${d}</span>`).join(' ')}`;
        statusList.innerHTML += `<div>${html}</div>`;
      });
  });
}

function connectAll() {
  ['vr', 'arm', 'camera'].forEach(type => {
    fetch(`/connect/${type}`, {method: 'POST'})
      .then(res => res.json())
      .then(data => {
        teleopLog.innerHTML += `<div>${data.msg}</div>`;
        fetchStatus();
      });
  });
}

let armCount = 0;
function addArm() {
  if (armCount >= 2) return;
  armCount++;
  const div = document.createElement('div');
  div.innerHTML = `<input type='text' name='arm_ip_${armCount}' placeholder='机械臂IP' required> <input type='number' name='arm_port_${armCount}' placeholder='端口' required>`;
  armsList.appendChild(div);
}

let cameraCount = 0;
function addCamera() {
  cameraCount++;
  const div = document.createElement('div');
  div.innerHTML = `<input type='text' name='camera_type_${cameraCount}' placeholder='类型' required> <input type='text' name='camera_position_${cameraCount}' placeholder='位置'> <input type='text' name='camera_serial_${cameraCount}' placeholder='序列号'>`;
  camerasList.appendChild(div);
}

configForm.onsubmit = function(e) {
  e.preventDefault();
  const form = new FormData(configForm);
  const cfg = {
    vr_ip: form.get('vr_ip'),
    vr_port: Number(form.get('vr_port')),
    arms: [],
    cameras: []
  };
  for (let i = 1; i <= armCount; i++) {
    cfg.arms.push({ip: form.get(`arm_ip_${i}`), port: form.get(`arm_port_${i}`)});
  }
  for (let i = 1; i <= cameraCount; i++) {
    cfg.cameras.push({type: form.get(`camera_type_${i}`), position: form.get(`camera_position_${i}`), serial: form.get(`camera_serial_${i}`)});
  }
  fetch('/config', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(cfg)
  }).then(res => res.json()).then(data => {
    teleopLog.innerHTML += `<div>${data.msg}</div>`;
  });
};

function startTeleop() {
  fetch('/start_teleop', {method: 'POST'})
    .then(res => res.json())
    .then(data => {
      teleopLog.innerHTML += `<div>${data.msg}</div>`;
    });
}

window.onload = function() {
  fetchStatus();
  addArm(); // 默认添加一个机械臂
}
