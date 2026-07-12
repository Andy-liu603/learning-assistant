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
            <label for="modelSelect">模型</label>
            <select id="modelSelect">
              <option value="">加载中...</option>
            </select>
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
  loadModelSelect();

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
        // 流式累加后整体渲染 markdown
        const raw = textEl.dataset.raw || '';
        textEl.dataset.raw = raw + chunk;
        textEl.innerHTML = renderMarkdown(textEl.dataset.raw);
        chatHistory.scrollTop = chatHistory.scrollHeight;
      },
      data => {
        aiMsg.querySelector('.typing-dots')?.remove();
        if (data.sources && data.sources.length) {
          // 行内引用：把 [1][2][3] 插入文本末尾，并绑定点击
          const inlineSup = data.sources.map((s, i) => {
            const docId = s.document_id || s.doc_id || (s.metadata && s.metadata.document_id) || '';
            const filename = (s.filename || (s.metadata && s.metadata.filename) || '资料片段').replace(/[<>]/g, '');
            return `<sup class="cite-ref" data-doc-id="${docId}" data-idx="${i}" data-filename="${escapeHtml(filename)}" title="查看引用：${escapeHtml(filename)}">[${i + 1}]</sup>`;
          }).join('');
          if (inlineSup) {
            const tail = document.createElement('span');
            tail.className = 'msg-cites';
            tail.innerHTML = inlineSup;
            textEl.appendChild(tail);
            // 绑定点击跳转
            tail.querySelectorAll('.cite-ref').forEach(ref => {
              ref.addEventListener('click', (e) => {
                e.stopPropagation();
                const docId = ref.dataset.docId;
                if (docId) {
                  window.location.hash = '#/library';
                  setTimeout(() => {
                    if (typeof window.viewDocumentById === 'function') {
                      window.viewDocumentById(parseInt(docId));
                    }
                  }, 300);
                } else {
                  showToast('未关联具体文档', 'info');
                }
              });
            });
          }
        }
        loadConversationList();
      },
      err => {
        aiMsg.querySelector('.typing-dots')?.remove();
        const raw = textEl.dataset.raw || '';
        textEl.dataset.raw = raw + '\n[错误: ' + err.message + ']';
        textEl.innerHTML = renderMarkdown(textEl.dataset.raw);
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
          // 乐观更新：先从 DOM 移除并结束
          const item = btn.closest('.conv-item');
          if (item) item.style.display = 'none';
          if (convId === id) {
            // 当前打开的对话被删除，关闭它
            convId = null;
            isFirstMsg = true;
            chatHistory.innerHTML = showEmpty('', '对话已删除，开始新的对话吧');
          }
          try {
            await api.delete(`/conversations/${id}`);
            showToast('对话已删除', 'success');
          } catch (err) {
            // 失败时恢复显示
            if (item) item.style.display = '';
            showToast('删除失败: ' + err.message, 'error');
          }
          await loadConversationList();
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
    div.innerHTML = '<div class="msg-text markdown-body"></div><div class="typing-dots"><span></span><span></span><span></span></div>';
    div.querySelector('.msg-text').textContent = '';
  } else {
    div.innerHTML = `<div class="msg-text markdown-body">${renderMarkdown(content)}</div>`;
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

async function loadModelSelect() {
  try {
    const data = await api.get('/models');
    const sel = document.getElementById('modelSelect');
    if (!sel) return;
    if (data && data.models && data.models.length) {
      sel.innerHTML = data.models.map(m =>
        `<option value="${m.id}" ${m.is_current ? 'selected' : ''}>${m.name}${m.type === 'multimodal' ? ' · 多模态' : ''}</option>`
      ).join('');
      sel.addEventListener('change', async (e) => {
        const model = e.target.value;
        try {
          const r = await api.post('/models/switch', { model });
          if (r.status === 'switched') {
            showToast(`已切换至 ${model}`, 'success');
          }
        } catch (err) {
          showToast('切换失败: ' + err.message, 'error');
        }
      });
    } else {
      sel.innerHTML = '<option>DeepSeek V4 Flash</option>';
    }
  } catch (e) {
    const sel = document.getElementById('modelSelect');
    if (sel) sel.innerHTML = '<option>DeepSeek V4 Flash</option>';
  }
}
