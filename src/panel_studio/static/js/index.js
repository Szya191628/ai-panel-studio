/**
 * index.js — 首页逻辑：讨论列表、新建讨论
 */

// ============================================================
// 初始化
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    loadDiscussions();
    // 每 5 秒刷新列表
    setInterval(loadDiscussions, 5000);
});

// ============================================================
// 讨论列表
// ============================================================

async function loadDiscussions() {
    try {
        const data = await api('/api/discussions');
        renderDiscussions(data.discussions || []);
    } catch (err) {
        console.error('加载讨论列表失败:', err);
    }
}

function renderDiscussions(discussions) {
    const grid = document.getElementById('discussion-list');
    const empty = document.getElementById('empty-state');

    if (discussions.length === 0) {
        grid.style.display = 'none';
        empty.style.display = 'flex';
        return;
    }

    grid.style.display = 'grid';
    empty.style.display = 'none';

    grid.innerHTML = discussions.map(d => `
        <div class="discussion-card" onclick="openDiscussion('${d.id}', '${d.status}')">
            <div class="card-header">
                <div class="card-topic">${escapeHtml(d.topic)}</div>
                <span class="card-status ${getStatusClass(d.status)}">${getStatusLabel(d.status)}</span>
            </div>
            <div class="card-meta">
                <span class="card-meta-item">👥 ${d.expert_count}位专家</span>
                <span class="card-meta-item">🕐 ${formatTime(d.created_at)}</span>
            </div>
        </div>
    `).join('');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================================
// 打开讨论
// ============================================================

function openDiscussion(id, status) {
    window.location.href = `/studio/${id}`;
}

// ============================================================
// 新建讨论
// ============================================================

function openCreateModal() {
    document.getElementById('create-modal').classList.add('active');
    document.getElementById('topic-input').focus();
}

function closeCreateModal() {
    document.getElementById('create-modal').classList.remove('active');
    document.getElementById('topic-input').value = '';
}

async function createDiscussion() {
    const topic = document.getElementById('topic-input').value.trim();
    const expertCount = parseInt(document.getElementById('expert-count').value);

    if (!topic) {
        alert('请输入讨论话题');
        return;
    }

    try {
        const data = await api('/api/discussions', {
            method: 'POST',
            body: { topic, expert_count: expertCount },
        });

        closeCreateModal();

        // 跳转到演播厅
        window.location.href = `/studio/${data.discussion.id}`;
    } catch (err) {
        alert('创建失败: ' + err.message);
    }
}

// 回车提交
document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && document.getElementById('create-modal').classList.contains('active')) {
        createDiscussion();
    }
    if (e.key === 'Escape') {
        closeCreateModal();
    }
});
