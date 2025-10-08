// DeviceManager.js - 设备管理组件
export class DeviceManager {
    constructor() {
        this.deviceCards = document.getElementById('device-cards');
        this.modal = null;
        this.deviceTypesInfo = {};
        this.init();
    }

    init() {
        // 等待 DOM 完全加载
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.initAfterDOMLoad();
            });
        } else {
            this.initAfterDOMLoad();
        }
    }

    initAfterDOMLoad() {
        this.initEventListeners();
        this.renderDeviceCards();
    }

    initEventListeners() {
        // 添加设备按钮事件
        document.getElementById('addDeviceBtn')?.addEventListener('click', () => this.handleAddDeviceClick());
    }

    async handleAddDeviceClick() {
        try {
            const response = await fetch('/api/nodes');
            const nodes = await response.json();
            
            if (nodes.length === 0) {
                alert('请先连接节点再添加设备');
                return;
            }
            
            // 显示添加设备模态框
            await this.showAddDeviceModal();
        } catch (error) {
            console.error('获取节点列表失败:', error);
            alert('获取节点列表失败');
        }
    }

    async showAddDeviceModal(defaultNodeId = null) {
        // 移除现有模态框
        if (this.modal) this.modal.remove();
        
        const nodes = await this.fetchNodes();
        
        if (nodes.length === 0) {
            alert('请先连接节点再创建设备');
            return;
        }
        
        const selectedNodeId = defaultNodeId || nodes[0].id;
        const deviceTypes = await this.fetchDeviceTypes(selectedNodeId);
        
        this.createModal(nodes, selectedNodeId, deviceTypes);
    }

    async fetchNodes() {
        try {
            const response = await fetch('/api/nodes');
            return await response.json();
        } catch (error) {
            console.error('获取节点列表失败:', error);
            throw error;
        }
    }

    async fetchDeviceTypes(nodeId) {
        try {
            const response = await fetch(`/api/device/types?node_id=${nodeId}`);
            return await response.json();
        } catch (error) {
            console.error('获取设备类型失败:', error);
            throw error;
        }
    }

    createModal(nodes, selectedNodeId, deviceTypes) {
        this.modal = document.createElement('div');
        this.modal.className = 'modal active';
        this.modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>新建设备</h3>
                </div>
                <div class="modal-body">
                    <form id="device-form">
                        ${this.getFormFields(nodes, selectedNodeId, deviceTypes)}
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" id="cancelDevice" class="btn btn-secondary">
                        取消
                    </button>
                    <button type="submit" form="device-form" class="btn btn-primary">
                        创建
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(this.modal);
        
        this.setupModalEventListeners(deviceTypes);
    }

    getFormFields(nodes, selectedNodeId, deviceTypes) {
        return `
            <div class="form-group">
                <label for="node-selector">节点</label>
                <select id="node-selector" name="node_id" class="node-selector">
                    ${nodes.map(node => `
                        <option value="${node.id}" ${selectedNodeId == node.id ? 'selected' : ''}>
                            Node #${node.id} - ${node.uuid}
                        </option>
                    `).join('')}
                </select>
            </div>
            
            <div class="form-group">
                <label for="device-name">设备名称</label>
                <input type="text" id="device-name" name="name" placeholder="设备名称" required>
            </div>
            
            <div class="form-group">
                <label for="device-description">描述</label>
                <textarea id="device-description" name="description" placeholder="设备描述" rows="2"></textarea>
            </div>
            
            <div class="form-group">
                <label for="device-category">分类</label>
                <select id="device-category" name="category" class="device-category-selector">
                    <option value="">请选择设备分类</option>
                    ${Object.keys(deviceTypes).map(category => `
                        <option value="${category}">${this.getCategoryDisplayName(category)}</option>
                    `).join('')}
                </select>
            </div>
            
            <div class="form-group">
                <label for="device-type">类型</label>
                <select id="device-type" name="type" class="device-type-selector" disabled>
                    <option value="">请先选择分类</option>
                </select>
            </div>
            
            <div id="device-config-fields">
                <!-- 动态配置字段将在这里插入 -->
            </div>
        `;
    }

    getFormFields(nodes, selectedNodeId, deviceTypes) {
        return `
            <label class="flex flex-col">
                <span class="font-medium mb-1">节点</span>
                <select name="node_id" class="border rounded px-3 py-2 node-selector">
                    ${nodes.map(node => `
                        <option value="${node.id}" ${selectedNodeId == node.id ? 'selected' : ''}>
                            Node #${node.id} - ${node.uuid}
                        </option>
                    `).join('')}
                </select>
            </label>
            <label class="flex flex-col">
                <span class="font-medium mb-1">设备名称</span>
                <input type="text" name="name" placeholder="设备名称" required class="border rounded px-3 py-2">
            </label>
            <label class="flex flex-col">
                <span class="font-medium mb-1">描述</span>
                <input type="text" name="description" placeholder="设备描述" class="border rounded px-3 py-2">
            </label>
            <label class="flex flex-col">
                <span class="font-medium mb-1">分类</span>
                <select name="category" class="border rounded px-3 py-2 device-category-selector">
                    <option value="">请选择设备分类</option>
                    ${Object.keys(deviceTypes).map(category => `
                        <option value="${category}">${this.getCategoryDisplayName(category)}</option>
                    `).join('')}
                </select>
            </label>
            <label class="flex flex-col">
                <span class="font-medium mb-1">类型</span>
                <select name="type" class="border rounded px-3 py-2 device-type-selector" disabled>
                    <option value="">请先选择分类</option>
                </select>
            </label>
            <div id="device-config-fields">
                <!-- 动态配置字段将在这里插入 -->
            </div>
        `;
    }

    setupModalEventListeners(initialTypes) {
        const form = document.getElementById('device-form');
        const nodeSelector = form.querySelector('.node-selector');
        const categorySelector = form.querySelector('.device-category-selector');
        const typeSelector = form.querySelector('.device-type-selector');
        
        nodeSelector.addEventListener('change', () => this.handleNodeChange(nodeSelector, categorySelector, typeSelector));
        categorySelector.addEventListener('change', () => this.handleCategoryChange(categorySelector, typeSelector, initialTypes));
        typeSelector.addEventListener('change', () => this.handleTypeChange(categorySelector, typeSelector, initialTypes));
        
        document.getElementById('cancelDevice').onclick = () => this.modal.remove();
        form.onsubmit = (e) => this.handleFormSubmit(e);
    }

    async handleNodeChange(nodeSelector, categorySelector, typeSelector) {
        try {
            const types = await this.fetchDeviceTypes(nodeSelector.value);
            categorySelector.innerHTML = `
                <option value="">请选择设备分类</option>
                ${Object.keys(types).map(category => `
                    <option value="${category}">${this.getCategoryDisplayName(category)}</option>
                `).join('')}
            `;
            typeSelector.innerHTML = '<option value="">请先选择分类</option>';
            typeSelector.disabled = true;
            document.getElementById('device-config-fields').innerHTML = '';
        } catch (error) {
            console.error('获取设备类型失败:', error);
            alert('获取设备类型失败');
        }
    }

    handleCategoryChange(categorySelector, typeSelector, deviceTypes) {
        const selectedCategory = categorySelector.value;
        if (selectedCategory && deviceTypes[selectedCategory]) {
            typeSelector.innerHTML = `
                <option value="">请选择设备类型</option>
                ${Object.entries(deviceTypes[selectedCategory]).map(([type, info]) => `
                    <option value="${type}">${info.name}</option>
                `).join('')}
            `;
            typeSelector.disabled = false;
        } else {
            typeSelector.innerHTML = '<option value="">请先选择分类</option>';
            typeSelector.disabled = true;
        }
        document.getElementById('device-config-fields').innerHTML = '';
    }

    handleTypeChange(categorySelector, typeSelector, deviceTypes) {
        const selectedCategory = categorySelector.value;
        const selectedType = typeSelector.value;
        
        if (selectedCategory && selectedType && deviceTypes[selectedCategory]?.[selectedType]?.need_config) {
            const configFields = deviceTypes[selectedCategory][selectedType].need_config;
            this.renderConfigFields(configFields);
        } else {
            document.getElementById('device-config-fields').innerHTML = '<p class="text-gray-500 text-sm">该类型无需额外配置</p>';
        }
    }

    renderConfigFields(configFields) {
        const container = document.getElementById('device-config-fields');
        container.innerHTML = '';
        
        if (Object.keys(configFields).length === 0) {
            container.innerHTML = '<p class="text-gray-500 text-sm">该类型无需额外配置</p>';
            return;
        }
        
        Object.entries(configFields).forEach(([key, field]) => {
            container.innerHTML += `
                <div class="mb-4">
                    <label class="flex flex-col">
                        <span class="font-medium mb-1">${field.description}</span>
                        <input type="${this.getInputType(field.type)}" 
                               name="config_${key}" 
                               class="border rounded px-3 py-2"
                               ${field.default !== undefined ? `value="${field.default}"` : ''}
                               ${field.required ? 'required' : ''}
                               placeholder="请输入${field.description}">
                    </label>
                    ${field.description ? `
                        <p class="text-xs text-gray-500 mt-1">${field.description}</p>
                    ` : ''}
                </div>
            `;
        });
    }

    getInputType(paramType) {
        const typeMap = {
            'integer': 'number',
            'number': 'number',
            'string': 'text',
            'boolean': 'checkbox'
        };
        return typeMap[paramType] || 'text';
    }

    async handleFormSubmit(e) {
        e.preventDefault();
        const form = e.target;
        const formData = new FormData(form);
        
        const deviceData = {
            node_id: parseInt(formData.get('node_id')),
            name: formData.get('name'),
            description: formData.get('description') || '',
            category: formData.get('category'),
            type: formData.get('type'),
            config: this.collectConfigData(formData)
        };
        
        try {
            const response = await fetch('/api/devices', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(deviceData)
            });
            
            if (response.ok) {
                this.modal.remove();
                this.renderDeviceCards();
                window.dispatchEvent(new Event('deviceListChanged'));
                this.showToast('设备创建成功', 'success');
            } else {
                const error = await response.json();
                this.showToast(error.message || '创建设备失败');
            }
        } catch (error) {
            console.error('创建设备出错:', error);
            this.showToast('创建设备出错');
        }
    }

    collectConfigData(formData) {
        const config = {};
        for (const [key, value] of formData.entries()) {
            if (key.startsWith('config_')) {
                config[key.replace('config_', '')] = value;
            }
        }
        return config;
    }

    showToast(message, type = 'error') {
        // 检查是否已存在toast
        const existingToast = document.querySelector('.toast-notification');
        if (existingToast) {
            existingToast.remove();
        }
        
        const toast = document.createElement('div');
        toast.className = `toast-notification fixed bottom-4 right-4 px-4 py-2 rounded-lg text-white z-50 ${
            type === 'success' ? 'bg-green-500' : 'bg-red-500'
        }`;
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.3s';
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 3000);
    }

    getCategoryDisplayName(category) {
        const displayNameMap = {
            'Camera': '摄像头',
            'Robot': '机械臂',
            'VR': 'VR设备',
            'Hand': '机械手'
        };
        return displayNameMap[category] || category;
    }

    async renderDeviceCards() {
        if (!this.deviceCards) return;

        this.deviceCards.innerHTML = '<div class="loading">加载中...</div>';

        try {
            const [nodesResponse, devicesResponse] = await Promise.all([
                fetch('/api/nodes'),
                fetch('/api/devices')
            ]);

            const [nodes, devices] = await Promise.all([
                nodesResponse.json(),
                devicesResponse.json()
            ]);

            if (nodes.length === 0) {
                this.renderEmptyState('暂无节点', '请先连接节点再添加设备');
                return;
            }

            this.renderDevices(nodes, devices);
        } catch (error) {
            console.error('获取设备数据失败:', error);
            this.deviceCards.innerHTML = '<div class="error">获取设备数据失败</div>';
        }
    }

    renderEmptyState(title, message) {
        this.deviceCards.innerHTML = `
            <div class="empty-state">
                <div class="icon">📱</div>
                <h3>${title}</h3>
                <p>${message}</p>
            </div>
        `;
    }

    renderDevices(nodes, devices) {
        // 按节点组织设备
        const devicesByNode = this.groupDevicesByNode(devices);

        this.deviceCards.innerHTML = nodes.map(node => this.renderNodeSection(node, devicesByNode[node.id] || [])).join('');
        
        // 添加事件监听
        this.attachDeviceCardEvents();
    }

    groupDevicesByNode(devices) {
        return devices.reduce((acc, device) => {
            if (!acc[device.node_id]) {
                acc[device.node_id] = [];
            }
            acc[device.node_id].push(device);
            return acc;
        }, {});
    }

    renderNodeSection(node, devices) {
        return `
            <div class="node-section">
                <h3>Node #${node.id} - ${node.uuid}</h3>
                <div class="flex justify-between items-center mb-4">
                    <button class="add-device-btn" data-node-id="${node.id}">
                        <i class="fas fa-plus"></i>
                        添加设备
                    </button>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    ${devices.length > 0 
                        ? devices.map(device => this.renderDeviceCard(device)).join('') 
                        : '<div class="col-span-full text-center py-8 text-gray-500">该节点暂无设备</div>'}
                </div>
            </div>
        `;
    }

    renderDeviceCard(device) {
        return `
            <div class="device-card" data-id="${device.id}">
                <div class="card-header">
                    <h4>${device.name}</h4>
                    <span class="status ${device.status}">${device.status === 'running' ? '运行中' : '已停止'}</span>
                </div>
                <div class="card-body">
                    <p>${device.description || '无描述'}</p>
                    <div class="details">
                        <span>类型: ${device.type}</span>
                        <span>类别: ${this.getCategoryDisplayName(device.category)}</span>
                    </div>
                </div>
                <div class="card-actions">
                    ${this.renderDeviceActions(device)}
                </div>
            </div>
        `;
    }

    renderDeviceActions(device) {
        const actions = [];
        if (device.status === 'stopped') {
            actions.push(`<button onclick="deviceManager.startDevice('${device.id}')" class="start">启动</button>`);
        } else {
            actions.push(`<button onclick="deviceManager.stopDevice('${device.id}')" class="stop">停止</button>`);
        }
        actions.push(`<button onclick="deviceManager.editDevice('${device.id}')" class="edit">编辑</button>`);
        actions.push(`<button onclick="deviceManager.deleteDevice('${device.id}')" class="delete">删除</button>`);

        return actions.join('');
    }

    attachDeviceCardEvents() {
        // 添加设备按钮事件
        this.deviceCards.querySelectorAll('.add-device-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const nodeId = parseInt(e.target.closest('.add-device-btn').dataset.nodeId);
                this.showAddDeviceModal(nodeId);
            });
        });
    }

    async startDevice(id) {
        try {
            const response = await fetch(`/api/devices/${id}/start`, { method: 'POST' });
            if (response.ok) {
                this.renderDeviceCards();
            } else {
                alert('启动设备失败');
            }
        } catch (error) {
            console.error('启动设备出错:', error);
            alert('启动设备出错');
        }
    }

    async stopDevice(id) {
        try {
            const response = await fetch(`/api/devices/${id}/stop`, { method: 'POST' });
            if (response.ok) {
                this.renderDeviceCards();
            } else {
                alert('停止设备失败');
            }
        } catch (error) {
            console.error('停止设备出错:', error);
            alert('停止设备出错');
        }
    }

    async deleteDevice(id) {
        if (!confirm('确定要删除该设备吗？')) return;
        
        try {
            const response = await fetch(`/api/devices/${id}`, { method: 'DELETE' });
            if (response.ok) {
                this.renderDeviceCards();
                // 触发仪表盘更新
                window.dispatchEvent(new Event('deviceListChanged'));
            } else {
                alert('删除设备失败');
            }
        } catch (error) {
            console.error('删除设备出错:', error);
            alert('删除设备出错');
        }
    }
}

// 导出单例实例
export const deviceManager = new DeviceManager();