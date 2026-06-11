/**
 * utils.js — 通用工具函数
 */

// API 基础路径
const API_BASE = '';

// 嘉宾色板（与后端 schema.py 对齐）
const GUEST_COLORS = [
    '#3b82f6', '#ef4444', '#10b981', '#f59e0b',
    '#8b5cf6', '#ec4899', '#06b6d4', '#f97316',
];

/**
 * 发起 API 请求
 */
async function api(path, options = {}) {
    const url = `${API_BASE}${path}`;
    const config = {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    };
    if (config.body && typeof config.body === 'object') {
        config.body = JSON.stringify(config.body);
    }

    const resp = await fetch(url, config);
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(err.detail || '请求失败');
    }
    return resp.json();
}

/**
 * 获取状态中文标签
 */
function getStatusLabel(status) {
    const map = {
        'configuring': '配置中',
        'active': '进行中',
        'concluded': '已结束',
    };
    return map[status] || status;
}

/**
 * 获取状态 CSS 类
 */
function getStatusClass(status) {
    return `status-${status}`;
}

/**
 * 格式化时间戳
 */
function formatTime(ts) {
    if (!ts) return '';
    const date = new Date(ts * 1000);
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;

    return date.toLocaleDateString('zh-CN', {
        month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit',
    });
}

/**
 * 获取嘉宾首字（用于头像）
 */
function getInitial(name) {
    return name ? name.charAt(0) : '?';
}

/**
 * 获取发言类型中文标签
 */
function getSpeechTypeLabel(type) {
    const map = {
        'open': '开场',
        'comment': '观点',
        'rebut': '反驳',
        'question': '提问',
        'summary': '总结',
    };
    return map[type] || type;
}

/**
 * 获取角色中文标签
 */
function getRoleLabel(role) {
    return role === 'host' ? '主持人' : '专家';
}

/**
 * 获取状态中文标签（嘉宾）
 */
function getPanelistStatusLabel(status) {
    const map = {
        'idle': '待机',
        'preparing': '准备发言',
        'speaking': '发言中',
    };
    return map[status] || status;
}

/**
 * 防抖函数
 */
function debounce(fn, delay) {
    let timer = null;
    return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}

/**
 * 滚动到底部
 */
function scrollToBottom(el) {
    if (el) {
        requestAnimationFrame(() => {
            el.scrollTop = el.scrollHeight;
        });
    }
}
