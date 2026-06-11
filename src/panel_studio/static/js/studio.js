/**
 * studio.js — 演播厅逻辑：SSE连接、实时渲染、状态管理
 */

// ============================================================
// 全局状态
// ============================================================

const state = {
    discussionId: null,
    discussion: null,
    panelists: [],
    speeches: [],
    findings: { consensus: [], disagreement: [] },
    eventSource: null,
    isRunning: false,
};

// ============================================================
// 初始化
// ============================================================

document.addEventListener('DOMContentLoaded', async () => {
    // 从 URL 提取 discussion_id
    const path = window.location.pathname;
    const match = path.match(/\/studio\/(.+)/);
    if (!match) {
        alert('无效的讨论ID');
        window.location.href = '/';
        return;
    }

    state.discussionId = match[1];
    await loadDiscussion();
});

async function loadDiscussion() {
    try {
        const data = await api(`/api/discussions/${state.discussionId}`);
        state.discussion = data.discussion;
        state.panelists = data.panelists || [];
        state.speeches = data.speeches || [];

        // 解析 findings
        const findings = data.findings || [];
        state.findings.consensus = findings.filter(f => f.type === 'consensus').map(f => f.content);
        state.findings.disagreement = findings.filter(f => f.type === 'disagreement').map(f => f.content);

        renderHeader();
        renderPanelists();
        renderTranscript();
        renderFindings();

        // 根据状态决定显示什么
        if (state.discussion.status === 'configuring') {
            showConfigPanel();
        } else if (state.discussion.status === 'active') {
            connectSSE();
            showRunningState();
        } else if (state.discussion.status === 'concluded') {
            showConcludedState();
        }
    } catch (err) {
        console.error('加载讨论失败:', err);
        alert('加载讨论失败: ' + err.message);
    }
}

// ============================================================
// 渲染函数
// ============================================================

function renderHeader() {
    document.getElementById('topic-title').textContent = state.discussion.topic;
    document.title = `${state.discussion.topic} — AI Panel Studio`;
}

function renderPanelists() {
    const container = document.getElementById('panelist-list');
    container.innerHTML = state.panelists.map((p, i) => `
        <div class="panelist-card" id="panelist-${p.id}" style="--guest-color:${p.color}">
            <div class="panelist-header">
                <div class="panelist-avatar" style="background:${p.color}">
                    ${getInitial(p.name)}
                    <span class="status-dot ${p.status}"></span>
                </div>
                <div class="panelist-info">
                    <div class="panelist-name">${escapeHtml(p.name)}</div>
                    <div class="panelist-title">${escapeHtml(p.title)}</div>
                </div>
            </div>
            <div class="panelist-stance">${escapeHtml(p.stance)}</div>
            <div class="panelist-focus" id="focus-${p.id}" style="display:none"></div>
        </div>
    `).join('');
}

function renderTranscript() {
    const container = document.getElementById('transcript-list');
    const waiting = document.getElementById('waiting-state');

    if (state.speeches.length === 0) {
        if (waiting) waiting.style.display = 'flex';
        return;
    }

    if (waiting) waiting.style.display = 'none';

    container.innerHTML = state.speeches.map(s => {
        const panelist = state.panelists.find(p => p.id === s.panelist_id) || {};
        const isHost = s.panelist_role === 'host';
        return `
            <div class="speech-item ${isHost ? 'host' : ''}" style="--guest-color:${s.panelist_color || panelist.color || '#3b82f6'}">
                <div class="speech-avatar" style="background:${s.panelist_color || panelist.color || '#3b82f6'}">
                    ${getInitial(s.panelist_name)}
                </div>
                <div class="speech-body">
                    <div class="speech-meta">
                        <span class="speech-name">${escapeHtml(s.panelist_name)}</span>
                        <span class="speech-title">${escapeHtml(s.panelist_title || '')}</span>
                        <span class="speech-type-badge">${getSpeechTypeLabel(s.speech_type)}</span>
                    </div>
                    <div class="speech-content">${escapeHtml(s.content)}</div>
                </div>
            </div>
        `;
    }).join('');

    document.getElementById('speech-count').textContent = `${state.speeches.length} 条发言`;
    scrollToBottom(container);
}

function renderFindings() {
    // 主侧边栏
    renderFindingList('consensus-list', state.findings.consensus);
    renderFindingList('disagreement-list', state.findings.disagreement);
    // 窄屏底栏
    renderFindingList('consensus-list-bar', state.findings.consensus);
    renderFindingList('disagreement-list-bar', state.findings.disagreement);
}

function renderFindingList(containerId, items) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (items.length === 0) {
        container.innerHTML = '<div class="finding-empty">讨论开始后自动提炼...</div>';
        return;
    }

    container.innerHTML = items.map(item => `
        <div class="finding-item">${escapeHtml(item)}</div>
    `).join('');
}

// ============================================================
// 嘉宾配置流程
// ============================================================

async function showConfigPanel() {
    const overlay = document.getElementById('config-overlay');
    overlay.style.display = 'flex';

    // 如果没有嘉宾，先生成
    if (state.panelists.length === 0) {
        await generatePanelists();
    } else {
        renderPanelistPreview();
    }
}

async function generatePanelists() {
    const grid = document.getElementById('panelist-preview-grid');
    grid.innerHTML = '<div class="loading-spinner"><div class="spinner"></div> AI 正在生成嘉宾阵容...</div>';

    try {
        const data = await api(`/api/discussions/${state.discussionId}/panelists/generate`, {
            method: 'POST',
        });
        state.panelists = data.panelists || [];
        renderPanelists();
        renderPanelistPreview();
    } catch (err) {
        grid.innerHTML = `<div style="color:var(--accent-red)">生成失败: ${err.message}</div>`;
    }
}

function renderPanelistPreview() {
    const grid = document.getElementById('panelist-preview-grid');
    grid.innerHTML = state.panelists.map(p => `
        <div class="panelist-preview-card" style="--guest-color:${p.color}">
            ${p.role === 'host' ? '<span class="preview-role-badge">主持人</span>' : ''}
            <div class="preview-name">${escapeHtml(p.name)}</div>
            <div class="preview-title">${escapeHtml(p.title)}</div>
            <div class="preview-stance">${escapeHtml(p.stance)}</div>
        </div>
    `).join('');
}

async function regeneratePanelists() {
    await generatePanelists();
}

async function confirmPanelists() {
    try {
        await api(`/api/discussions/${state.discussionId}/confirm`, { method: 'POST' });
        document.getElementById('config-overlay').style.display = 'none';
        showRunningState();
        connectSSE();
    } catch (err) {
        alert('确认失败: ' + err.message);
    }
}

// ============================================================
// 讨论控制
// ============================================================

function showRunningState() {
    document.getElementById('btn-start').style.display = 'inline-flex';
    document.getElementById('btn-stop').style.display = 'none';
    document.getElementById('live-badge').style.display = 'none';
}

function showActiveState() {
    document.getElementById('btn-start').style.display = 'none';
    document.getElementById('btn-stop').style.display = 'inline-flex';
    document.getElementById('live-badge').style.display = 'inline-flex';
    state.isRunning = true;
}

function showConcludedState() {
    document.getElementById('btn-start').style.display = 'none';
    document.getElementById('btn-stop').style.display = 'none';
    document.getElementById('live-badge').style.display = 'none';
    state.isRunning = false;

    if (state.discussion.conclusion) {
        document.getElementById('conclusion-text').textContent = state.discussion.conclusion;
        document.getElementById('conclusion-overlay').style.display = 'flex';
    }
}

async function startDiscussion() {
    try {
        await api(`/api/discussions/${state.discussionId}/start`, { method: 'POST' });
        showActiveState();
    } catch (err) {
        alert('启动失败: ' + err.message);
    }
}

async function stopDiscussion() {
    if (!confirm('确定要结束讨论吗？')) return;

    try {
        await api(`/api/discussions/${state.discussionId}/stop`, { method: 'POST' });
        state.isRunning = false;
    } catch (err) {
        alert('结束失败: ' + err.message);
    }
}

function goHome() {
    window.location.href = '/';
}

// ============================================================
// SSE 连接
// ============================================================

function connectSSE() {
    if (state.eventSource) {
        state.eventSource.close();
    }

    const url = `/api/discussions/${state.discussionId}/events`;
    state.eventSource = new EventSource(url);

    state.eventSource.addEventListener('init', (e) => {
        const data = JSON.parse(e.data);
        console.log('SSE init:', data);
        // 初始化数据已在 loadDiscussion 中处理
    });

    state.eventSource.addEventListener('panelists_generated', (e) => {
        const data = JSON.parse(e.data);
        state.panelists = data.panelists || [];
        renderPanelists();
    });

    state.eventSource.addEventListener('status_changed', (e) => {
        const data = JSON.parse(e.data);
        state.discussion.status = data.status;
        if (data.status === 'active') {
            showActiveState();
        }
    });

    state.eventSource.addEventListener('panelist_update', (e) => {
        const data = JSON.parse(e.data);
        updatePanelistStatus(data.panelist_id, data.status, data.focus);
    });

    state.eventSource.addEventListener('speech', (e) => {
        const data = JSON.parse(e.data);
        appendSpeech(data);
    });

    state.eventSource.addEventListener('finding', (e) => {
        const data = JSON.parse(e.data);
        appendFinding(data);
    });

    state.eventSource.addEventListener('concluded', (e) => {
        const data = JSON.parse(e.data);
        state.discussion.status = 'concluded';
        state.discussion.conclusion = data.conclusion;
        showConcludedState();
    });

    state.eventSource.addEventListener('error', (e) => {
        const data = JSON.parse(e.data || '{}');
        console.error('SSE error:', data);
    });

    state.eventSource.onerror = (e) => {
        console.warn('SSE 连接断开，正在重连...');
    };
}

// ============================================================
// 实时更新
// ============================================================

function updatePanelistStatus(panelistId, status, focus) {
    const card = document.getElementById(`panelist-${panelistId}`);
    if (!card) return;

    // 更新状态点
    const dot = card.querySelector('.status-dot');
    if (dot) {
        dot.className = `status-dot ${status}`;
    }

    // 更新卡片样式
    card.className = `panelist-card ${status === 'speaking' ? 'speaking' : ''}`;

    // 更新关注点
    const focusEl = document.getElementById(`focus-${panelistId}`);
    if (focusEl) {
        if (focus) {
            focusEl.textContent = focus;
            focusEl.style.display = 'block';
        } else {
            focusEl.style.display = 'none';
        }
    }
}

function appendSpeech(speech) {
    state.speeches.push(speech);

    const container = document.getElementById('transcript-list');
    const waiting = document.getElementById('waiting-state');
    if (waiting) waiting.style.display = 'none';

    const panelist = state.panelists.find(p => p.id === speech.panelist_id) || {};
    const isHost = speech.panelist_role === 'host';

    const html = `
        <div class="speech-item ${isHost ? 'host' : ''}" style="--guest-color:${speech.panelist_color || panelist.color || '#3b82f6'}">
            <div class="speech-avatar" style="background:${speech.panelist_color || panelist.color || '#3b82f6'}">
                ${getInitial(speech.panelist_name)}
            </div>
            <div class="speech-body">
                <div class="speech-meta">
                    <span class="speech-name">${escapeHtml(speech.panelist_name)}</span>
                    <span class="speech-title">${escapeHtml(speech.panelist_title || '')}</span>
                    <span class="speech-type-badge">${getSpeechTypeLabel(speech.speech_type)}</span>
                </div>
                <div class="speech-content">${escapeHtml(speech.content)}</div>
            </div>
        </div>
    `;

    container.insertAdjacentHTML('beforeend', html);
    document.getElementById('speech-count').textContent = `${state.speeches.length} 条发言`;
    scrollToBottom(container);
}

function appendFinding(finding) {
    if (finding.type === 'consensus') {
        state.findings.consensus.push(finding.content);
    } else {
        state.findings.disagreement.push(finding.content);
    }
    renderFindings();
}

// ============================================================
// 页面卸载
// ============================================================

window.addEventListener('beforeunload', () => {
    if (state.eventSource) {
        state.eventSource.close();
    }
});
