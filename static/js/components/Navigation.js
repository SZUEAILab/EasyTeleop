// Navigation.js - 导航组件
export class Navigation {
    constructor() {
        this.navLinks = null;
        this.pages = null;
        this.pageTitle = null;
        this.init();
    }

    init() {
        // 等待 DOM 完全加载
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupNavigation());
        } else {
            this.setupNavigation();
        }
    }

    setupNavigation() {
        // 获取必要的 DOM 元素
        this.navLinks = document.querySelectorAll('.nav-link');
        this.pages = document.querySelectorAll('.page');
        this.pageTitle = document.getElementById('page-title');

        // 检查必要元素是否存在
        if (!this.navLinks.length || !this.pages.length) {
            console.error('Navigation: 找不到必要的导航元素');
            return;
        }

        // 设置导航点击事件
        this.navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const targetPage = link.getAttribute('data-target');
                if (targetPage) {
                    this.navigateToPage(targetPage);
                }
            });
        });

        // 从 URL 获取当前页面或默认到仪表盘
        const currentPage = window.location.hash.substring(1) || 'dashboard';
        this.navigateToPage(currentPage);
    }

    navigateToPage(pageId) {
        if (!pageId) return;

        // 更新导航链接状态
        this.navLinks.forEach(link => {
            const isActive = link.getAttribute('data-target') === pageId;
            // 移除所有链接的活动状态
            link.classList.remove('active', 'bg-blue-50', 'text-blue-600');
            
            // 为活动链接添加样式
            if (isActive) {
                link.classList.add('active', 'bg-blue-50', 'text-blue-600');
                // 仅在找到活动链接且页面标题元素存在时更新标题
                if (this.pageTitle) {
                    this.pageTitle.textContent = link.querySelector('span')?.textContent || '';
                }
            } else {
                link.classList.add('hover:bg-gray-100');
            }
        });

        // 显示目标页面
        this.pages.forEach(page => {
            if (page) {
                // 如果是目标页面则移除hidden类并添加active类，否则相反
                if (page.id === pageId) {
                    page.classList.remove('hidden');
                    page.classList.add('active');
                } else {
                    page.classList.add('hidden');
                    page.classList.remove('active');
                }
            }
        });

        // 更新 URL，但不触发新的导航
        if (window.location.hash !== `#${pageId}`) {
            window.history.pushState(null, '', `#${pageId}`);
        }
    }
}

// 导出单例实例
export const navigation = new Navigation();