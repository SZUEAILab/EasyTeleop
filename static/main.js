// 获取设备列表（同步）
async function getDeviceOptions() {
  const res = await fetch('/api/devices');
  const data = await res.json();
  return data;
}

// 遥操作组弹窗
let teleopModal = null;
window.showTeleopModal = async function (group = null) {
  if (teleopModal) teleopModal.remove();
  const devices = await getDeviceOptions();
  // 组配置
  const config = group ? group.config : {};
  teleopModal = document.createElement('div');
  teleopModal.className = 'fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50';
  teleopModal.innerHTML = `
      <form id="teleop-form" class="bg-white p-6 rounded-lg shadow-lg w-full max-w-md flex flex-col gap-4">
        <h3 class="text-lg font-bold mb-2">${group ? '编辑' : '新建'}遥操作组</h3>
        <label>左臂:
          <select name="left_arm" class="border rounded px-2 py-1">
            <option value="">无</option>
            ${(devices.robot || []).map(dev => `<option value="${dev.id}" ${config.left_arm == dev.id ? 'selected' : ''}>${dev.type}#${dev.id}</option>`).join('')}
          </select>
        </label>
        <label>右臂:
          <select name="right_arm" class="border rounded px-2 py-1">
            <option value="">无</option>
            ${(devices.robot || []).map(dev => `<option value="${dev.id}" ${config.right_arm == dev.id ? 'selected' : ''}>${dev.type}#${dev.id}</option>`).join('')}
          </select>
        </label>
        <label>头显:
          <select name="vr" class="border rounded px-2 py-1">
            <option value="">无</option>
            ${(devices.vr || []).map(dev => `<option value="${dev.id}" ${config.vr == dev.id ? 'selected' : ''}>${dev.type}#${dev.id}</option>`).join('')}
          </select>
        </label>
        <label>头部摄像头:
          <select name="head_camera" class="border rounded px-2 py-1">
            <option value="">无</option>
            ${(devices.camera || []).map(dev => `<option value="${dev.id}" ${config.head_camera == dev.id ? 'selected' : ''}>${dev.type}#${dev.id}</option>`).join('')}
          </select>
        </label>
        <label>左腕摄像头:
          <select name="left_camera" class="border rounded px-2 py-1">
            <option value="">无</option>
            ${(devices.camera || []).map(dev => `<option value="${dev.id}" ${config.left_camera == dev.id ? 'selected' : ''}>${dev.type}#${dev.id}</option>`).join('')}
          </select>
        </label>
        <label>右腕摄像头:
          <select name="right_camera" class="border rounded px-2 py-1">
            <option value="">无</option>
            ${(devices.camera || []).map(dev => `<option value="${dev.id}" ${config.right_camera == dev.id ? 'selected' : ''}>${dev.type}#${dev.id}</option>`).join('')}
          </select>
        </label>
        <div class="flex gap-2 justify-end">
          <button type="submit" class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">${group ? '保存' : '创建'}</button>
          <button type="button" id="cancelTeleop" class="px-4 py-2 bg-gray-300 rounded hover:bg-gray-400">取消</button>
        </div>
      </form>
    `;
  document.body.appendChild(teleopModal);
  document.getElementById('cancelTeleop').onclick = () => teleopModal.remove();
  document.getElementById('teleop-form').onsubmit = function (e) {
    e.preventDefault();
    const form = new FormData(e.target);
    const config = {};
    for (const [key, value] of form.entries()) {
      config[key] = value || null;
    }
    if (group) {
      fetch(`/api/teleop-groups/${group.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config })
      }).then(() => {
        teleopModal.remove();
        renderTeleopGroups();
      });
    } else {
      const newId = 'group_' + Date.now();
      fetch(`/api/teleop-groups/${newId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config })
      }).then(() => {
        teleopModal.remove();
        renderTeleopGroups();
      });
    }
  };
};

// 渲染遥操作组列表（示例）
async function renderTeleopGroups() {
  const containerId = 'teleop-groups';
  let container = document.getElementById(containerId);
  // 获取所有遥操作组
  let groups = [];
  try {
    const res = await fetch('/api/teleop-groups');
    groups = await res.json();
  } catch { }
  container.innerHTML = `<div class="grid grid-cols-1 md:grid-cols-2 gap-4">${groups.map(group => `
    <div class="p-4 bg-white rounded shadow flex flex-col gap-2 border border-gray-200">
      <div class="font-bold text-blue-600">组ID: ${group.id}</div>
      <div>左臂: ${group.config.left_arm || '无'} | 右臂: ${group.config.right_arm || '无'} | 头显: ${group.config.vr || '无'}</div>
      <div>摄像头: ${group.config.head_camera || '无'} / ${group.config.left_camera || '无'} / ${group.config.right_camera || '无'}</div>
      <div class="flex gap-2 mt-2">
        <button class="px-2 py-1 bg-yellow-400 text-white rounded hover:bg-yellow-500" onclick='showTeleopModal(${JSON.stringify(group)})'>配置</button>
        <button class="px-2 py-1 bg-gray-500 text-white rounded hover:bg-gray-700" onclick='deleteTeleopGroup("${group.id}")'>删除</button>
        <button class="px-2 py-1 ${group.running ? 'bg-red-500 hover:bg-red-600' : 'bg-green-500 hover:bg-green-600'} text-white rounded" onclick='${group.running ? `stopTeleopGroup("${group.id}")` : `startTeleopGroup("${group.id}")`}'>${group.running ? '停止' : '启动'}</button>
      </div>
    </div>
    
  `).join('')}</div>
  <div class="flex justify-start mt-4"><button id="addTeleopBtn" class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600" onclick='showTeleopModal()'>新建遥操作组</button></div>
  `;
}
// Tailwind UI重构入口
document.addEventListener('DOMContentLoaded', () => {
  // 主容器
  const app = document.getElementById('app');
  app.innerHTML = `
    <div class="min-h-screen bg-gray-100 flex flex-col items-center justify-center">
      <div class="w-full max-w-3xl p-8 bg-white rounded-lg shadow-lg flex flex-col gap-8">
        <h1 class="text-3xl font-bold text-center text-blue-600">遥操作管理平台</h1>
        <section id="device-status">
          <h2 class="text-xl font-semibold mb-2">设备管理</h2>
          <div id="device-cards" class="grid grid-cols-1 md:grid-cols-2 gap-4"></div>
          <button id="addDeviceBtn" class="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition">添加设备</button>
        </section>
        <div id="add-device-modal" class="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50 hidden">
          <form id="add-device-form" class="bg-white p-6 rounded-lg shadow-lg w-full max-w-md flex flex-col gap-4">
            <h3 class="text-lg font-bold mb-2">添加设备</h3>
            <input type="text" name="name" placeholder="设备名称" required class="border rounded px-2 py-1">
            <input type="text" name="describe" placeholder="设备描述" required class="border rounded px-2 py-1">
            <select name="category" class="border rounded px-2 py-1">
              <!-- 选项将从API动态加载 -->
            </select>
            <input type="text" name="type" placeholder="类型" required class="border rounded px-2 py-1">
            <div class="flex gap-2 justify-end">
              <button type="submit" class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">添加</button>
              <button type="button" id="cancelAddDevice" class="px-4 py-2 bg-gray-300 rounded hover:bg-gray-400">取消</button>
            </div>
          </form>
        </div>
        <section id="teleop">
          <h2 class="text-xl font-semibold mb-2">遥操作组</h2>
          <div id = "teleop-groups">

        </div>
        </section>
        
        <footer class="text-center text-gray-400 mt-8">
          <small>© 2025 SZUEAILab</small>
        </footer>
      </div>
    </div>
  `;

  // 设备卡片渲染
  const deviceCards = document.getElementById('device-cards');
  function renderDeviceCards() {
    fetch('/api/devices')
      .then(res => res.json())
      .then(data => {
        deviceCards.innerHTML = '';
        const allDevices = [];
        ['vr', 'robot', 'camera'].forEach(category => {
          (data[category] || []).forEach(dev => {
            allDevices.push({ category, dev });
          });
        });
        // 并发获取所有设备状态
        Promise.all(allDevices.map(({ category, dev }) =>
          fetch(`/api/devices/${category}/${dev.id}/status`)
            .then(res => res.json())
            .then(statusData => ({ category, dev, connStatus: statusData.conn_status }))
            .catch(() => ({ category, dev, connStatus: 0 }))
        )).then(devicesWithStatus => {
          deviceCards.innerHTML = '';
          devicesWithStatus.forEach(({ category, dev, connStatus }) => {
            console.log(connStatus)
            // 根据连接状态设置颜色和文本
            let statusColor = 'gray';
            let statusText = '未连接';
            let statusBgColor = 'bg-gray-500';
            if (connStatus == 1) { 
              statusColor = 'green'; 
              statusText = '已连接'; 
              statusBgColor = 'bg-green-500';
            }
            if (connStatus == 2) { 
              statusColor = 'red'; 
              statusText = '断开'; 
              statusBgColor = 'bg-red-500';
            }
            
            let actionBtn = '';
            if (connStatus == 0) {
              actionBtn = `<button class="px-2 py-1 bg-green-500 text-white rounded hover:bg-green-600" onclick="startDevice('${category}',${dev.id})">启动</button>`;
            } else {
              actionBtn = `<button class="px-2 py-1 bg-red-500 text-white rounded hover:bg-red-600" onclick="stopDevice('${category}',${dev.id})">停止</button>`;
            }
            
            // 转义特殊字符的函数
            function escapeHtml(unsafe) {
              return unsafe
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
            }
            
            // 转义JSON字符串中的引号，以便在HTML属性中使用
            function escapeJsonForHtml(jsonString) {
              return jsonString
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
            }
            
            deviceCards.innerHTML += `
              <div class="p-4 bg-gray-50 rounded shadow flex flex-col gap-2 border border-gray-200">
                <div class="font-bold text-blue-500">${category.toUpperCase()}</div>
                <div>类型: <span class="font-mono">${dev.type}</span></div>
                <div>配置: <span class="text-xs">${escapeHtml(JSON.stringify(dev.config))}</span></div>
                <!-- 连接状态单独一行显示，按照"连接状态：xxx"格式 -->
                <div class="flex items-center">
                  <span>连接状态：</span>
                  <span class="px-2 py-1 rounded text-white ${statusBgColor} rounded-full">${statusText}</span>
                </div>
                <div class="flex items-center gap-2 mt-2">
                  <button class="px-2 py-1 bg-yellow-400 text-white rounded hover:bg-yellow-500" onclick="showConfigModal('${category}',${dev.id},'${dev.type}','${escapeJsonForHtml(JSON.stringify(dev.config))}','${escapeHtml(dev.name)}','${escapeHtml(dev.describe)}')">配置</button>
                  ${actionBtn}
                  <button class="px-2 py-1 bg-gray-500 text-white rounded hover:bg-gray-700" onclick="deleteDevice('${category}',${dev.id})">删除</button>
                </div>
              </div>
            `;
          });
        });
      });
  }

  // 添加设备弹窗逻辑
  const addDeviceModal = document.getElementById('add-device-modal');
  const addDeviceForm = document.getElementById('add-device-form');
  // 动态渲染type和config字段
  let adaptedTypes = {};
  const categorySelect = addDeviceForm.querySelector('select[name="category"]');
  let typeSelect = addDeviceForm.querySelector('input[name="type"]');
  // 移除config输入框（配置(JSON)）
  const configInput = addDeviceForm.querySelector('input[name="config"]');
  if (configInput) configInput.remove();

  // 获取设备分类并填充下拉框
  function loadCategories() {
    fetch('/api/device-categories')
      .then(res => res.json())
      .then(data => {
        categorySelect.innerHTML = '';
        data.categories.forEach(category => {
          const option = document.createElement('option');
          option.value = category;
          option.textContent = getCategoryDisplayName(category);
          categorySelect.appendChild(option);
        });
        // 触发类别change事件以加载类型
        categorySelect.dispatchEvent(new Event('change'));
      });
  }

  // 获取分类显示名称
  function getCategoryDisplayName(category) {
    const displayNameMap = {
      'vr': 'VR头显',
      'robot': '机械臂',
      'camera': '摄像头'
    };
    return displayNameMap[category] || category;
  }

  // 替换type输入框为下拉框
  function renderTypeSelect(types) {
    if (typeSelect && typeSelect.tagName === 'INPUT') {
      const select = document.createElement('select');
      select.name = 'type';
      select.className = 'border rounded px-2 py-1';
      typeSelect.replaceWith(select);
      typeSelect = select;
    }
    typeSelect.innerHTML = '';
    Object.keys(types).forEach(type => {
      typeSelect.innerHTML += `<option value="${type}">${type}</option>`;
    });
  }

  // 渲染config字段输入框
  function renderConfigFields(fields) {
    // 移除旧字段
    Array.from(addDeviceForm.querySelectorAll('.config-field')).forEach(e => e.remove());
    // 添加新字段
    fields.forEach(field => {
      const input = document.createElement('input');
      input.className = 'config-field border rounded px-2 py-1';
      input.name = field;
      input.placeholder = field;
      input.required = true;
      addDeviceForm.insertBefore(input, addDeviceForm.querySelector('.flex'));
    });
  }

  // 监听类别变化
  categorySelect.onchange = function (e) {
    fetch(`/api/device-types/${e.target.value}`)
      .then(res => res.json())
      .then(types => {
        adaptedTypes = types;
        renderTypeSelect(types);
        // 默认渲染第一个type的config字段
        const firstType = Object.keys(types)[0];
        // 获取配置字段的键名（而不是整个对象）
        const configFields = Object.keys(types[firstType] || {});
        renderConfigFields(configFields);
      });
  };

  // 监听type变化
  addDeviceForm.addEventListener('change', function (e) {
    if (e.target.name === 'type') {
      // 获取配置字段的键名（而不是整个对象）
      const fields = Object.keys(adaptedTypes[e.target.value] || {});
      renderConfigFields(fields);
    }
  });

  // 打开弹窗时自动触发类别change
  document.getElementById('addDeviceBtn').onclick = () => {
    addDeviceModal.classList.remove('hidden');
    loadCategories(); // 从API加载分类
  };
  document.getElementById('cancelAddDevice').onclick = () => {
    addDeviceModal.classList.add('hidden');
  };

  // 提交时收集所有config字段
  addDeviceForm.onsubmit = function (e) {
    e.preventDefault();
    const form = new FormData(addDeviceForm);
    const category = form.get('category');
    const type = form.get('type');
    const name = form.get('name');
    const describe = form.get('describe');
    let config = {};
    // 修复：adaptedTypes[type] 是一个对象，不是数组
    const configFields = adaptedTypes[type] || {};
    Object.keys(configFields).forEach(field => {
      config[field] = form.get(field);
    });
    fetch(`/api/devices/${category}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, describe, type, config })
    }).then(response => {
      if (response.ok) {
        addDeviceModal.classList.add('hidden');
        renderDeviceCards();
      } else {
        console.error('添加设备失败:', response.status);
        alert('添加设备失败，请检查控制台错误信息');
      }
    }).catch(error => {
      console.error('添加设备出错:', error);
      alert('添加设备出错，请检查控制台错误信息');
    });
  };

  // 设备操作API
  // 配置弹窗
  let configModal = null;
  window.showConfigModal = function (category, id, type, configStr, name, describe) {
    // 解析传递过来的JSON字符串
    let config = {};
    try {
      config = JSON.parse(configStr);
    } catch (e) {
      console.error('解析配置失败:', e);
      alert('配置解析失败');
      return;
    }
    
    if (configModal) configModal.remove();
    configModal = document.createElement('div');
    configModal.className = 'fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50';
    configModal.innerHTML = `
      <form id="edit-config-form" class="bg-white p-6 rounded-lg shadow-lg w-full max-w-md flex flex-col gap-4">
        <h3 class="text-lg font-bold mb-2">配置设备</h3>
        <input class="border rounded px-2 py-1" name="name" value="${name}" placeholder="设备名称" required>
        <input class="border rounded px-2 py-1" name="describe" value="${describe}" placeholder="设备描述" required>
        ${Object.entries(config).map(([key, value]) => `<input class="border rounded px-2 py-1" name="${key}" value="${value}" placeholder="${key}" required>`).join('')}
        <div class="flex gap-2 justify-end">
          <button type="submit" class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">保存</button>
          <button type="button" id="cancelEditConfig" class="px-4 py-2 bg-gray-300 rounded hover:bg-gray-400">取消</button>
        </div>
      </form>
    `;
    document.body.appendChild(configModal);
    document.getElementById('cancelEditConfig').onclick = () => configModal.remove();
    document.getElementById('edit-config-form').onsubmit = function (e) {
      e.preventDefault();
      const form = new FormData(e.target);
      const newConfig = {};
      let newName = form.get('name');
      let newDescribe = form.get('describe');
      for (const [key, value] of form.entries()) {
        if (key !== 'name' && key !== 'describe') {
          newConfig[key] = value;
        }
      }
      fetch(`/api/devices/${category}/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName, describe: newDescribe, config: newConfig })
      }).then(response => {
        if (response.ok) {
          configModal.remove();
          renderDeviceCards();
        } else {
          console.error('更新设备配置失败:', response.status);
          alert('更新设备配置失败，请检查控制台错误信息');
        }
      }).catch(error => {
        console.error('更新设备配置出错:', error);
        alert('更新设备配置出错，请检查控制台错误信息');
      });
    };
  };
  window.deleteDevice = function (category, id) {
    if (!confirm('确定要删除该设备吗？')) return;
    fetch(`/api/devices/${category}/${id}`, { method: 'DELETE' })
      .then(() => renderDeviceCards());
  };
  window.startDevice = function (category, id) {
    fetch(`/api/devices/${category}/${id}/start`, { method: 'POST' })
      .then(() => renderDeviceCards());
  };
  window.stopDevice = function (category, id) {
    fetch(`/api/devices/${category}/${id}/stop`, { method: 'POST' })
      .then(() => renderDeviceCards());
  };
  async function renderTeleopGroups() {
    const containerId = 'teleop-groups';
    let container = document.getElementById(containerId);
    // 获取所有遥操作组
    let groups = [];
    try {
      const res = await fetch('/api/teleop-groups');
      groups = await res.json();
    } catch { }
    container.innerHTML = `<div class="grid grid-cols-1 md:grid-cols-2 gap-4">${groups.map(group => `
      <div class="p-4 bg-white rounded shadow flex flex-col gap-2 border border-gray-200">
        <div class="font-bold text-blue-600">组ID: ${group.id}</div>
        <div>左臂: ${group.config.left_arm || '无'} | 右臂: ${group.config.right_arm || '无'} | 头显: ${group.config.vr || '无'}</div>
        <div>摄像头: ${group.config.head_camera || '无'} / ${group.config.left_camera || '无'} / ${group.config.right_camera || '无'}</div>
        <div class="flex gap-2 mt-2">
          <button class="px-2 py-1 bg-yellow-400 text-white rounded hover:bg-yellow-500" onclick='showTeleopModal(${JSON.stringify(group)})'>配置</button>
          <button class="px-2 py-1 bg-gray-500 text-white rounded hover:bg-gray-700" onclick='deleteTeleopGroup("${group.id}")'>删除</button>
          <button class="px-2 py-1 ${group.running ? 'bg-red-500 hover:bg-red-600' : 'bg-green-500 hover:bg-green-600'} text-white rounded" onclick='${group.running ? `stopTeleopGroup("${group.id}")` : `startTeleopGroup("${group.id}")`}'>${group.running ? '停止' : '启动'}</button>
        </div>
      </div>
      
    `).join('')}</div>
    <div class="flex justify-start mt-4"><button id="addTeleopBtn" class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600" onclick='showTeleopModal()'>新建遥操作组</button></div>
    `;
  }

  // 启动/停止/删除遥操作组API
  window.startTeleopGroup = function (id) {
    fetch(`/api/teleop-groups/${id}/start`, { method: 'POST' }).then(() => renderTeleopGroups());
  };
  window.stopTeleopGroup = function (id) {
    fetch(`/api/teleop-groups/${id}/stop`, { method: 'POST' }).then(() => renderTeleopGroups());
  };
  window.deleteTeleopGroup = function (id) {
    if (!confirm('确定要删除该遥操作组吗？')) return;
    fetch(`/api/teleop-groups/${id}`, { method: 'DELETE' }).then(() => renderTeleopGroups());
  };
  // 初始化渲染和轮询刷新
  renderDeviceCards();
  renderTeleopGroups();
  // setInterval(renderDeviceCards, 2000);
});