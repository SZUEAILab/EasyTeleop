// 主入口文件
import { deviceManager } from './components/DeviceManager.js';
import { teleopManager } from './components/TeleopManager.js';
import { dashboard } from './components/Dashboard.js';
import { navigation } from './components/Navigation.js';

// 使组件实例在全局可用（为了支持现有的事件处理）
window.deviceManager = deviceManager;
window.teleopManager = teleopManager;

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    try {
        console.log('初始化应用...');
        
        // 组件已经在各自的构造函数中初始化
        
        console.log('应用初始化完成');
    } catch (error) {
        console.error('应用初始化失败:', error);
        showToast('页面初始化失败，请刷新页面重试');
    }
});

// 全局工具函数
function showToast(message, type = 'error') {
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

window.showToast = showToast;