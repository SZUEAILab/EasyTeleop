// Dashboard.js - 仪表盘组件
export class Dashboard {
    constructor() {
        this.init();
    }

    init() {
        // 监听设备和遥操作组列表变化
        window.addEventListener('deviceListChanged', () => this.updateStats());
        window.addEventListener('teleopGroupListChanged', () => this.updateStats());
        
        // 初始化统计数据
        this.updateStats();
    }

    async updateStats() {
        try {
            const [nodesData, devicesData, teleopData] = await Promise.all([
                this.fetchNodes(),
                this.fetchDevices(),
                this.fetchTeleopGroups()
            ]);
            
            this.updateDashboardUI({
                nodes: nodesData.length,
                devices: this.calculateTotalDevices(devicesData),
                teleopGroups: teleopData.length
            });
        } catch (error) {
            console.error('获取仪表盘数据失败:', error);
        }
    }

    async fetchNodes() {
        const response = await fetch('/api/nodes');
        return await response.json();
    }

    async fetchDevices() {
        const response = await fetch('/api/devices');
        return await response.json();
    }

    async fetchTeleopGroups() {
        const response = await fetch('/api/teleop-groups');
        return await response.json();
    }

    calculateTotalDevices(devicesData) {
        if (Array.isArray(devicesData)) {
            return devicesData.length;
        }
        return Object.values(devicesData).reduce((total, devices) => total + devices.length, 0);
    }

    updateDashboardUI({ nodes, devices, teleopGroups }) {
        document.getElementById('online-nodes').textContent = nodes;
        document.getElementById('total-devices').textContent = devices;
        document.getElementById('total-teleop-groups').textContent = teleopGroups;
    }
}

// 导出单例实例
export const dashboard = new Dashboard();