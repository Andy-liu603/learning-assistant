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
          // 把引用 [1][2][3] 分散注入到回复中各段落的末尾（紧跟原文）
          injectInlineCitations(textEl, data.sources);
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

/**
 * 把 [1][2][3] 引用分散插入到回复文本各段落的末尾
 * 策略：对每条 source，从其 content 中提取 2-3 个关键词，
 *       在回复文本中找第一个包含这些关键词的段落，段末插入 [n]
 *       若未匹配到，则把该引用追加到回复末尾
 */
function injectInlineCitations(textEl, sources) {
  if (!textEl || !sources || !sources.length) return;
  // 拿到当前已渲染的 HTML（用 dataset.raw 备份）
  const raw = textEl.dataset.raw || textEl.textContent || '';
  if (!raw.trim()) return;

  // 把回复按段落（\n\n 或 <br><br>）拆分
  // 渲染后 \n 被转为 <br>，我们按 <br><br> 拆
  let html = textEl.innerHTML;
  // 把 br 拆为段落数组
  const blocks = html.split(/(?:<br>\s*){2,}/i);
  if (blocks.length <= 1) {
    // 没有段落分隔，按句号切分
    blocks.length = 0;
    const tmp = html.split(/(?<=[。！？!?\.])/);
    blocks.push(...tmp.filter(s => s.trim()));
  }

  // 对每条 source，尝试匹配一个段落
  const usedBlocks = new Set();
  const matchedSources = sources.map((s, i) => {
    const content = (s.content || '').trim();
    const fp = (s.fingerprint || content).slice(0, 30);
    // 提取 2-3 个关键词（每个至少 2 字）
    const keywords = [];
    if (fp) {
      // 按标点和空格切分
      const tokens = fp.split(/[，。！？,.!?\s\n]/).filter(t => t.length >= 2);
      keywords.push(...tokens.slice(0, 3));
    }
    // 找第一个含关键词的段落
    for (let j = 0; j < blocks.length; j++) {
      if (usedBlocks.has(j)) continue;
      const blockText = blocks[j].replace(/<[^>]+>/g, '').replace(/\s+/g, '');
      if (!blockText) continue;
      const hasKeyword = keywords.length === 0
        || keywords.some(k => k && blockText.includes(k.replace(/\s+/g, '')));
      if (hasKeyword) {
        usedBlocks.add(j);
        return { ...s, blockIndex: j, idx: i };
      }
    }
    return { ...s, blockIndex: -1, idx: i };
  });

  // 重新组装 HTML，把 [n] 插到匹配段落的末尾
  const newBlocks = blocks.map((b, j) => {
    const citesForBlock = matchedSources
      .filter(s => s.blockIndex === j)
      .map(s => {
        const docId = s.document_id || '';
        const filename = (s.filename || '资料片段').replace(/[<>"']/g, '');
        return `<sup class="cite-ref" data-doc-id="${docId}" data-idx="${s.idx}" data-filename="${escapeHtml(filename)}" title="查看引用：${escapeHtml(filename)}">[${s.idx + 1}]</sup>`;
      })
      .join('');
    return b + (citesForBlock || '');
  });

  // 未匹配到的 source 加到末尾
  const unmatched = matchedSources.filter(s => s.blockIndex === -1);
  if (unmatched.length) {
    const tail = unmatched.map(s => {
      const docId = s.document_id || '';
      const filename = (s.filename || '资料片段').replace(/[<>"']/g, '');
      return `<sup class="cite-ref" data-doc-id="${docId}" data-idx="${s.idx}" data-filename="${escapeHtml(filename)}" title="查看引用：${escapeHtml(filename)}">[${s.idx + 1}]</sup>`;
    }).join('');
    newBlocks.push(tail);
  }

  textEl.innerHTML = newBlocks.join('<br><br>');

  // 绑定点击跳转
  textEl.querySelectorAll('.cite-ref').forEach(ref => {
    if (ref.dataset.bound) return;
    ref.dataset.bound = '1';
    ref.addEventListener('click', (e) => {
      e.stopPropagation();
      const docId = ref.dataset.docId;
      if (docId) {
        window.location.hash = '#/library';
        setTimeout(() => {
          if (typeof window.viewDocumentById === 'function') {
            window.viewDocumentById(parseInt(docId));
          } else {
            showToast(`已跳转到资料库（${ref.dataset.filename}）`, 'info');
          }
        }, 300);
      } else {
        showToast('未关联具体文档', 'info');
      }
    });
  });
}
