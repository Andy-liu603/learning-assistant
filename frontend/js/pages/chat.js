/* 智能对话页面 v3.1 — 对话历史侧边栏 + 文档关联 + 后端持久化 */

import { api } from '../api.js';
import { createEl, renderTopbar, showEmpty } from '../components.js';
import { renderMarkdown, escapeHtml, showToast } from '../utils.js';

export async function renderChatPage() {
  renderTopbar('chat');

  const content = document.getElementById('mainContent');
  content.innerHTML = `
    <div class="chat-page">
      <div class="page-header">
        <h2>智能对话</h2>
      </div>

      <!-- 历史对话侧边栏 -->
      <div id="convSidebar" class="conv-sidebar">
        <div class="conv-sidebar-header">
          <span>历史对话</span>
          <button id="newChatBtn" class="btn btn-primary btn-sm">+ 新对话</button>
        </div>
        <div id="convList" class="conv-list">
          <p class="text-muted" style="text-align:center;padding:16px;">加载中...</p>
        </div>
      </div>

      <!-- 主对话区 -->
      <div class="chat-main">
        <div class="chat-context-bar">
          <div class="context-item">
            <label for="docSelect">关联文档</label>
            <select id="docSelect">
              <option value="">通用问答</option>
            </select>
          </div>
          <div class="context-item">
            <label>模型</label>
            <span id="modelDisplay" class="context-value">加载中...</span>
          </div>
        </div>
        <div id="chatHistory" class="chat-history">
          ${showEmpty('', '选择文档或直接提问开始对话')}
        </div>
        <div class="chat-input-area">
          <textarea id="chatInput" placeholder="输入问题，Enter 发送，Shift+Enter 换行" rows="1"></textarea>
          <button id="sendBtn" class="btn btn-primary">发送</button>
        </div>
      </div>
    </div>
  `;

  let convId = null;
  let isFirstMsg = true;
  const chatHistory = document.getElementById('chatHistory');
  const chatInput = document.getElementById('chatInput');

  loadConversationList();
  loadDocOptions();
  loadModelDisplay();

  document.getElementById('newChatBtn').addEventListener('click', startNewChat);

  async function sendMessage() {
    const message = chatInput.value.trim();
    if (!message) return;

    const docSelect = document.getElementById('docSelect');
    const docId = docSelect ? (docSelect.value || null) : null;

    if (isFirstMsg) { chatHistory.innerHTML = ''; isFirstMsg = false; }

    addMessageDOM('user', message);
    chatInput.value = '';
    chatInput.style.height = 'auto';

    if (!convId) {
      const r = await api.post('/conversations', {
        title: message.slice(0, 30),
        document_id: docId ? parseInt(docId) : null
      });
      if (r && r.id) {
        convId = r.id;
        loadConversationList();
      }
    }

    const aiMsg = addMessageDOM('assistant', '', true);
    const textEl = aiMsg.querySelector('.msg-text');

    api.stream(
      `/conversations/${convId}/messages`,
      { message, document_id: docId ? parseInt(docId) : null, stream: true },
      chunk => {
        textEl.innerHTML = renderMarkdown(textEl.textContent + chunk);
        chatHistory.scrollTop = chatHistory.scrollHeight;
      },
      data => {
        aiMsg.querySelector('.typing-dots')?.remove();
        if (data.sources && data.sources.length) {
          const srcDiv = document.createElement('div');
          srcDiv.className = 'chat-sources';
          srcDiv.textContent = `引用 ${data.sources.length} 个资料片段`;
          aiMsg.appendChild(srcDiv);
        }
        loadConversationList();
      },
      err => {
        aiMsg.querySelector('.typing-dots')?.remove();
        textEl.textContent += `\n[错误: ${err.message}]`;
      }
    );
  }

  document.getElementById('sendBtn').addEventListener('click', sendMessage);
  chatInput.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });
  chatInput.addEventListener('input', () => {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
  });

  // ── 对话列表 ──
  async function loadConversationList() {
    try {
      const data = await api.get('/conversations');
      const list = document.getElementById('convList');
      if (!data || !data.conversations || data.conversations.length === 0) {
        list.innerHTML = '<p class="text-muted" style="text-align:center;padding:16px;">暂无历史对话</p>';
        return;
      }
      list.innerHTML = data.conversations.map(c => {
        const date = c.updated_at ? new Date(c.updated_at).toLocaleDateString('zh-CN') : '';
        const isActive = c.id === convId;
        return `
          <div class="conv-item ${isActive ? 'conv-item-active' : ''}" data-id="${c.id}">
            <div class="conv-item-title">${escapeHtml(c.title || '未命名对话')}</div>
            <div class="conv-item-meta">${date} · ${c.message_count || 0} 条</div>
            <button class="conv-item-delete" data-id="${c.id}" title="删除">×</button>
          </div>
        `;
      }).join('');
      list.querySelectorAll('.conv-item').forEach(item => {
        item.addEventListener('click', e => {
          if (e.target.classList.contains('conv-item-delete')) return;
          loadConversation(parseInt(item.dataset.id));
        });
      });
      list.querySelectorAll('.conv-item-delete').forEach(btn => {
        btn.addEventListener('click', async e => {
          e.stopPropagation();
          const id = parseInt(btn.dataset.id);
          if (!confirm('确定删除这条对话？')) return;
          await api.delete(`/conversations/${id}`);
          if (convId === id) startNewChat();
          loadConversationList();
          showToast('对话已删除');
        });
      });
    } catch (e) {
      console.warn('Load conversations failed:', e);
    }
  }

  async function loadConversation(id) {
    try {
      const data = await api.get(`/conversations/${id}`);
      convId = id;
      isFirstMsg = false;
      chatHistory.innerHTML = '';
      if (data && data.messages) {
        data.messages.forEach(m => {
          addMessageDOM(m.role === 'user' ? 'user' : 'assistant', m.content);
        });
      }
      loadConversationList();
    } catch (e) {
      showToast('加载对话失败: ' + e.message);
    }
  }

  function startNewChat() {
    convId = null;
    isFirstMsg = true;
    chatHistory.innerHTML = showEmpty('', '开始新的对话');
    loadConversationList();
  }
}

function addMessageDOM(role, content, isStreaming = false) {
  const chatHistory = document.getElementById('chatHistory');
  const cls = role === 'user' ? 'chat-user' : 'chat-assistant';
  const div = createEl('div', { className: `chat-message ${cls}` });
  if (isStreaming) {
    div.innerHTML = '<span class="msg-text" style="white-space:pre-wrap"></span><div class="typing-dots"><span></span><span></span><span></span></div>';
  } else {
    div.innerHTML = `<span class="msg-text" style="white-space:pre-wrap">${escapeHtml(content)}</span>`;
  }
  chatHistory.appendChild(div);
  chatHistory.scrollTop = chatHistory.scrollHeight;
  return div;
}

async function loadDocOptions() {
  try {
    const data = await api.get('/documents');
    if (data && data.documents) {
      const sel = document.getElementById('docSelect');
      if (!sel) return;
      data.documents.filter(d => d.status === 'parsed').forEach(d => {
        const opt = document.createElement('option');
        opt.value = d.id;
        opt.textContent = d.filename;
        sel.appendChild(opt);
      });
    }
  } catch (e) { /* ignore */ }
}

async function loadModelDisplay() {
  try {
    const data = await api.get('/models');
    const el = document.getElementById('modelDisplay');
    if (data && data.current && el) el.textContent = data.current;
  } catch (e) {
    const el = document.getElementById('modelDisplay');
    if (el) el.textContent = 'DeepSeek Chat';
  }
}
