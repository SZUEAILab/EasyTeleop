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
            <select name="category" class="border rounded px-2 py-1">
              <option value="vr">VR头显</option>
              <option value="arm">机械臂</option>
              <option value="camera">摄像头</option>
            </select>
            <input type="text" name="type" placeholder="类型" required class="border rounded px-2 py-1">
            <div class="flex gap-2 justify-end">
              <button type="submit" class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">添加</button>
              <button type="button" id="cancelAddDevice" class="px-4 py-2 bg-gray-300 rounded hover:bg-gray-400">取消</button>
            </div>
          </form>
        </div>
        <section id="teleop">
          <h2 class="text-xl font-semibold mb-2">遥操作启动</h2>
          <button id="startTeleopBtn" class="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600">启动遥操作</button>
          <div id="teleop-log" class="mt-2 text-gray-700"></div>
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
    fetch('/devices')
      .then(res => res.json())
      .then(data => {
        deviceCards.innerHTML = '';
        ['vr', 'arm', 'camera'].forEach(category => {
          data[category].forEach(dev => {
            deviceCards.innerHTML += `
              <div class="p-4 bg-gray-50 rounded shadow flex flex-col gap-2 border border-gray-200">
                <div class="font-bold text-blue-500">${category.toUpperCase()}</div>
                <div>类型: <span class="font-mono">${dev.type}</span></div>
                <div>配置: <span class="text-xs">${JSON.stringify(dev.config)}</span></div>
                <div class="flex gap-2 mt-2">
                  <button class="px-2 py-1 bg-yellow-400 text-white rounded hover:bg-yellow-500" onclick="showConfigModal('${category}',${dev.id})">配置</button>
                  <button class="px-2 py-1 bg-green-500 text-white rounded hover:bg-green-600" onclick="startDevice('${category}',${dev.id})">启动</button>
                  <button class="px-2 py-1 bg-red-500 text-white rounded hover:bg-red-600" onclick="stopDevice('${category}',${dev.id})">停止</button>
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
  categorySelect.onchange = function(e) {
    fetch(`/device/${e.target.value}/adapted_types`)
      .then(res => res.json())
      .then(types => {
        adaptedTypes = types;
        renderTypeSelect(types);
        // 默认渲染第一个type的config字段
        const firstType = Object.keys(types)[0];
        renderConfigFields(types[firstType] || []);
      });
  };

  // 监听type变化
  addDeviceForm.addEventListener('change', function(e) {
    if (e.target.name === 'type') {
      const fields = adaptedTypes[e.target.value] || [];
      renderConfigFields(fields);
    }
  });

  // 打开弹窗时自动触发类别change
  document.getElementById('addDeviceBtn').onclick = () => {
    addDeviceModal.classList.remove('hidden');
    categorySelect.dispatchEvent(new Event('change'));
  };
  document.getElementById('cancelAddDevice').onclick = () => {
    addDeviceModal.classList.add('hidden');
  };

  // 提交时收集所有config字段
  addDeviceForm.onsubmit = function(e) {
    e.preventDefault();
    const form = new FormData(addDeviceForm);
    const category = form.get('category');
    const type = form.get('type');
    let config = {};
    (adaptedTypes[type] || []).forEach(field => {
      config[field] = form.get(field);
    });
    fetch(`/device/${category}/add`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({type, config})
    }).then(() => {
      addDeviceModal.classList.add('hidden');
      renderDeviceCards();
    });
  };

  // 设备操作API
  window.showConfigModal = function(category, id) {
    alert('请在后端或数据库修改配置，或补充前端弹窗逻辑');
  };
  window.startDevice = function(category, id) {
    fetch(`/device/${category}/${id}/start`, {method: 'POST'})
      .then(() => renderDeviceCards());
  };
  window.stopDevice = function(category, id) {
    fetch(`/device/${category}/${id}/stop`, {method: 'POST'})
      .then(() => renderDeviceCards());
  };

  // 遥操作启动
  document.getElementById('startTeleopBtn').onclick = () => {
    fetch('/teleop/start', {method: 'POST'})
      .then(res => res.json())
      .then(data => {
        document.getElementById('teleop-log').textContent = data.message || '已启动';
      });
  };

  // 初始化渲染
  renderDeviceCards();
});
