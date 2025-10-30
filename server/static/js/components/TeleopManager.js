// TeleopManager.js - 遥操作组管理组件
export class TeleopManager {
    constructor() {
        this.container = document.getElementById('teleop-groups');
        this.modal = null;
        this.init();
    }

    init() {
        this.renderTeleopGroups();
    }

    async renderTeleopGroups() {
        if (!this.container) return;
        
        this.showLoading();
        
        try {
            const [nodesRes, devicesRes] = await Promise.all([
                fetch('/api/nodes'),
                fetch('/api/devices')
            ]);
            
            const nodes = await nodesRes.json();
            const devicesData = await devicesRes.json();
            
            if (nodes.length === 0) {
                this.renderEmptyState();
                return;
            }
            
            // 重组设备数据结构
            const devices = this.organizeDevices(devicesData);
            
            await this.renderNodeGroups(nodes, devices);
            
        } catch (error) {
            console.error('获取遥操作组列表失败:', error);
            this.showError();
        }
    }

    showLoading() {
        this.container.innerHTML = `
            <div class="col-span-full text-center py-12">
                <div class="loading mx-auto"></div>
                <p class="mt-2 text-gray-500">加载中...</p>
            </div>
        `;
    }

    renderEmptyState() {
        this.container.innerHTML = `
            <div class="col-span-full empty-state">
                <i class="fas fa-network-wired"></i>
                <p>暂无节点</p>
                <p class="text-gray-500 text-sm mt-2">请先连接节点再创建遥操作组</p>
            </div>
        `;
    }

    showError() {
        this.container.innerHTML = `
            <div class="col-span-full text-center py-12 text-red-500">
                获取遥操作组数据失败
            </div>
        `;
    }

    organizeDevices(devicesData) {
        const devices = {};
        devicesData.forEach(device => {
            devices[device.id] = device;
        });
        return devices;
    }

    async renderNodeGroups(nodes, devices) {
        this.container.innerHTML = '';
        
        const nodeGroups = await Promise.all(nodes.map(node => this.fetchNodeGroups(node)));
        
        nodeGroups.forEach(({ node, groups }) => {
            const nodeSection = this.createNodeSection(node, groups, devices);
            this.container.appendChild(nodeSection);
        });
        
        this.attachEventListeners();
    }

    async fetchNodeGroups(node) {
        try {
            const res = await fetch(`/api/teleop-groups?node_id=${node.id}`);
            const groups = await res.json();
            return { node, groups };
        } catch (error) {
            console.error(`获取节点 ${node.id} 的遥操作组失败:`, error);
            return { node, groups: [] };
        }
    }

    createNodeSection(node, groups, devices) {
        const section = document.createElement('div');
        section.className = 'node-section mb-8';
        
        section.innerHTML = `
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-semibold">节点 #${node.id} - ${node.uuid}</h3>
                <button class="add-teleop-btn px-3 py-1 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition flex items-center gap-1 text-sm" 
                        data-node-id="${node.id}">
                    <i class="fas fa-plus"></i>
                    <span>新建遥操作组</span>
                </button>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4" id="node-${node.id}-teleop-groups">
                ${groups.length === 0 ? this.renderEmptyNodeState() : ''}
            </div>
        `;

        if (groups.length > 0) {
            const groupsContainer = section.querySelector(`#node-${node.id}-teleop-groups`);
            groups.forEach(group => {
                const card = this.createTeleopCard(group, devices);
                groupsContainer.appendChild(card);
            });
        }

        return section;
    }

    renderEmptyNodeState() {
        return `
            <div class="col-span-full empty-state py-8">
                <i class="fas fa-gamepad text-gray-300 text-2xl"></i>
                <p class="text-gray-500 mt-2">该节点暂无遥操作组</p>
            </div>
        `;
    }

    createTeleopCard(group, devices) {
        const card = document.createElement('div');
        card.className = 'bg-white rounded-lg shadow p-4 flex flex-col';
        card.innerHTML = `
            <div class="flex justify-between items-start mb-3">
                <div>
                    <h4 class="text-lg font-medium">${group.name}</h4>
                    <p class="text-sm text-gray-500">${group.description || '无描述'}</p>
                </div>
                <span class="status-badge ${group.status}">${group.status}</span>
            </div>
            <div class="text-sm text-gray-600 mb-4">
                <p>类型: ${group.type}</p>
                <p class="mt-1">设备配置:</p>
                <ul class="list-disc list-inside ml-2">
                    ${this.renderDevicesList(group.config, devices)}
                </ul>
            </div>
            <div class="flex justify-end gap-2 mt-auto">
                ${this.renderTeleopActions(group)}
            </div>
        `;
        return card;
    }

    renderDevicesList(config, devices) {
        return Object.entries(config)
            .filter(([_, deviceId]) => devices[deviceId])
            .map(([role, deviceId]) => `
                <li>${role}: ${devices[deviceId]?.name || '未知设备'}</li>
            `).join('');
    }

    renderTeleopActions(group) {
        const actions = [];
        if (group.status === 'stopped') {
            actions.push(`
                <button onclick="teleopManager.startTeleopGroup('${group.id}')"
                        class="px-3 py-1 bg-green-500 text-white rounded hover:bg-green-600 text-sm">
                    启动
                </button>
            `);
        } else {
            actions.push(`
                <button onclick="teleopManager.stopTeleopGroup('${group.id}')"
                        class="px-3 py-1 bg-yellow-500 text-white rounded hover:bg-yellow-600 text-sm">
                    停止
                </button>
            `);
        }
        actions.push(`
            <button onclick="teleopManager.editTeleopGroup('${group.id}')"
                    class="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm">
                编辑
            </button>
            <button onclick="teleopManager.deleteTeleopGroup('${group.id}')"
                    class="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600 text-sm">
                删除
            </button>
        `);
        return actions.join('');
    }

    attachEventListeners() {
        document.querySelectorAll('.add-teleop-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                const nodeId = e.target.closest('.add-teleop-btn').dataset.nodeId;
                this.showTeleopModal(null, nodeId);
            });
        });
    }

    async startTeleopGroup(id) {
        try {
            const response = await fetch(`/api/teleop-groups/${id}/start`, { method: 'POST' });
            if (response.ok) {
                this.renderTeleopGroups();
                this.showToast('遥操作组启动成功', 'success');
            } else {
                this.showToast('启动遥操作组失败');
            }
        } catch (error) {
            console.error('启动遥操作组出错:', error);
            this.showToast('启动遥操作组出错');
        }
    }

    async stopTeleopGroup(id) {
        try {
            const response = await fetch(`/api/teleop-groups/${id}/stop`, { method: 'POST' });
            if (response.ok) {
                this.renderTeleopGroups();
                this.showToast('遥操作组停止成功', 'success');
            } else {
                this.showToast('停止遥操作组失败');
            }
        } catch (error) {
            console.error('停止遥操作组出错:', error);
            this.showToast('停止遥操作组出错');
        }
    }

    async deleteTeleopGroup(id) {
        if (!confirm('确定要删除该遥操作组吗？')) return;
        
        try {
            const response = await fetch(`/api/teleop-groups/${id}`, { method: 'DELETE' });
            if (response.ok) {
                this.renderTeleopGroups();
                window.dispatchEvent(new Event('teleopGroupListChanged'));
                this.showToast('遥操作组删除成功', 'success');
            } else {
                this.showToast('删除遥操作组失败');
            }
        } catch (error) {
            console.error('删除遥操作组出错:', error);
            this.showToast('删除遥操作组出错');
        }
    }

    showToast(message, type = 'error') {
        const toast = document.createElement('div');
        toast.className = `fixed bottom-4 right-4 px-4 py-2 rounded-lg text-white ${
            type === 'success' ? 'bg-green-500' : 'bg-red-500'
        }`;
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }

    async showTeleopModal(groupId = null, defaultNodeId = null) {
        // 移除现有模态框
        if (this.modal) this.modal.remove();
        
        const [nodes, group] = await Promise.all([
            this.fetchNodes(),
            groupId ? this.fetchGroup(groupId) : null
        ]);
        
        if (nodes.length === 0) {
            alert('请先连接节点再创建遥操作组');
            return;
        }
        
        const selectedNodeId = defaultNodeId || group?.node_id || nodes[0].id;
        const teleopGroupTypes = await this.fetchTeleopGroupTypes(selectedNodeId);
        
        this.createModal(nodes, group, selectedNodeId, teleopGroupTypes);
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

    async fetchGroup(groupId) {
        try {
            const response = await fetch(`/api/teleop-groups/${groupId}`);
            return await response.json();
        } catch (error) {
            console.error('获取遥操组信息失败:', error);
            return null;
        }
    }

    async fetchTeleopGroupTypes(nodeId) {
        try {
            const response = await fetch(`/api/teleop-groups/types?node_id=${nodeId}`);
            return await response.json();
        } catch (error) {
            console.error('获取遥操组类型失败:', error);
            throw error;
        }
    }

    createModal(nodes, group, selectedNodeId, teleopGroupTypes) {
        this.modal = document.createElement('div');
        this.modal.className = 'fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50';
        this.modal.innerHTML = this.getModalHTML(nodes, group, selectedNodeId, teleopGroupTypes);
        
        document.body.appendChild(this.modal);
        
        this.setupModalEventListeners(teleopGroupTypes);
    }

    getModalHTML(nodes, group, selectedNodeId, teleopGroupTypes) {
        return `
            <form id="teleop-form" class="bg-white p-6 rounded-lg shadow-lg w-full max-w-md flex flex-col gap-4">
                <h3 class="text-lg font-bold mb-2">${group ? '编辑' : '新建'}遥操作组</h3>
                <input type="hidden" name="group_id" value="${group ? group.id : ''}">
                ${this.getFormFields(nodes, group, selectedNodeId, teleopGroupTypes)}
                <div class="flex gap-2 justify-end pt-2">
                    <button type="button" id="cancelTeleop" 
                            class="px-4 py-2 bg-gray-300 rounded-lg hover:bg-gray-400">
                        取消
                    </button>
                    <button type="submit" 
                            class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">
                        ${group ? '保存' : '创建'}
                    </button>
                </div>
            </form>
        `;
    }

    getFormFields(nodes, group, selectedNodeId, teleopGroupTypes) {
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
                <span class="font-medium mb-1">组名称</span>
                <input type="text" name="name" value="${group ? group.name : ''}" 
                       placeholder="遥操作组名称" required class="border rounded px-3 py-2">
            </label>
            <label class="flex flex-col">
                <span class="font-medium mb-1">描述</span>
                <input type="text" name="description" value="${group ? group.description : ''}" 
                       placeholder="遥操作组描述" class="border rounded px-3 py-2">
            </label>
            <label class="flex flex-col">
                <span class="font-medium mb-1">类型</span>
                <select name="type" class="border rounded px-3 py-2 teleop-type-selector">
                    ${Object.keys(teleopGroupTypes).map(type => `
                        <option value="${type}" ${group && group.type == type ? 'selected' : ''}>
                            ${type}
                        </option>
                    `).join('')}
                </select>
            </label>
            <div id="teleop-config-fields">
                <!-- 动态配置字段将在这里插入 -->
            </div>
        `;
    }

    setupModalEventListeners(initialTypes) {
        const form = document.getElementById('teleop-form');
        const nodeSelector = form.querySelector('.node-selector');
        const typeSelector = form.querySelector('.teleop-type-selector');
        
        nodeSelector.addEventListener('change', () => this.handleNodeChange(nodeSelector, typeSelector));
        typeSelector.addEventListener('change', () => this.handleTypeChange(nodeSelector, typeSelector));
        
        document.getElementById('cancelTeleop').onclick = () => this.modal.remove();
        form.onsubmit = (e) => this.handleFormSubmit(e);
        
        // 触发初始类型选择变化事件以渲染配置字段
        if (Object.keys(initialTypes).length > 0) {
            typeSelector.dispatchEvent(new Event('change'));
        }
    }

    async handleNodeChange(nodeSelector, typeSelector) {
        try {
            const types = await this.fetchTeleopGroupTypes(nodeSelector.value);
            typeSelector.innerHTML = Object.keys(types)
                .map(type => `<option value="${type}">${type}</option>`)
                .join('');
            typeSelector.dispatchEvent(new Event('change'));
        } catch (error) {
            console.error('获取遥操组类型失败:', error);
            this.showToast('获取遥操组类型失败');
        }
    }

    async handleTypeChange(nodeSelector, typeSelector) {
        try {
            const types = await this.fetchTeleopGroupTypes(nodeSelector.value);
            const selectedType = typeSelector.value;
            const typeConfig = types[selectedType]?.need_config || [];
            
            this.renderConfigFields(typeConfig);
        } catch (error) {
            console.error('获取遥操组类型配置失败:', error);
            this.showToast('获取遥操组类型配置失败');
        }
    }

    renderConfigFields(configFields) {
        const container = document.getElementById('teleop-config-fields');
        container.innerHTML = '';
        
        if (configFields.length === 0) {
            container.innerHTML = '<p class="text-gray-500 text-sm">该类型无需额外配置</p>';
            return;
        }
        
        configFields.forEach(field => {
            container.innerHTML += `
                <div class="mb-4">
                    <label class="flex flex-col">
                        <span class="font-medium mb-1">${field.name}</span>
                        <select name="config_${field.name}" class="border rounded px-3 py-2" required>
                            ${this.getDeviceOptions(field.device_type)}
                        </select>
                    </label>
                    ${field.description ? `
                        <p class="text-xs text-gray-500 mt-1">${field.description}</p>
                    ` : ''}
                </div>
            `;
        });
    }

    async getDeviceOptions(deviceType) {
        try {
            const response = await fetch('/api/devices');
            const devices = await response.json();
            return devices
                .filter(device => device.type === deviceType)
                .map(device => `
                    <option value="${device.id}">${device.name}</option>
                `)
                .join('');
        } catch (error) {
            console.error('获取设备列表失败:', error);
            return '<option value="">获取设备失败</option>';
        }
    }

    async handleFormSubmit(e) {
        e.preventDefault();
        const form = e.target;
        const formData = new FormData(form);
        const groupId = formData.get('group_id');
        
        const groupData = {
            node_id: parseInt(formData.get('node_id')),
            name: formData.get('name'),
            description: formData.get('description') || '',
            type: formData.get('type'),
            config: this.collectConfigData(formData)
        };
        
        try {
            const url = groupId ? 
                `/api/teleop-groups/${groupId}` : 
                '/api/teleop-groups';
            
            const response = await fetch(url, {
                method: groupId ? 'PUT' : 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(groupData)
            });
            
            if (response.ok) {
                this.modal.remove();
                this.renderTeleopGroups();
                this.showToast(
                    `遥操作组${groupId ? '更新' : '创建'}成功`, 
                    'success'
                );
                window.dispatchEvent(new Event('teleopGroupListChanged'));
            } else {
                const error = await response.json();
                this.showToast(error.message || `${groupId ? '更新' : '创建'}遥操作组失败`);
            }
        } catch (error) {
            console.error(`${groupId ? '更新' : '创建'}遥操作组出错:`, error);
            this.showToast(`${groupId ? '更新' : '创建'}遥操作组出错`);
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
}

// 导出单例实例
export const teleopManager = new TeleopManager();