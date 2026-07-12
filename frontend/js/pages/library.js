/* 资料库页面 v2.2 — 档案索引 */

import { api } from '../api.js';
import { renderTopbar, showConfirm, showEmpty } from '../components.js';
import { getStatusBadge, getProgressLabel, showToast, formatDate, escapeHtml } from '../utils.js';

export function renderLibraryPage() {
  renderTopbar('library');

  const content = document.getElementById('mainContent');
  content.innerHTML = `
    <div class="page-header">
      <h2>学习资料库</h2>
      <p>上传并管理学习文档，系统自动解析、分块、建立索引</p>
    </div>
    <div id="uploadZone" class="upload-zone">
      <div class="upload-icon">+</div>
      <p>点击或拖拽文件上传</p>
      <p class="text-xs text-secondary">支持 PDF、PPTX、DOCX、MD、TXT、JPG、PNG、WEBP、GIF</p>
      <input type="file" id="fileInput" hidden accept=".pdf,.pptx,.ppt,.docx,.doc,.md,.markdown,.txt,.jpg,.jpeg,.png,.webp,.bmp,.gif">
      <div id="uploadProgress" class="hidden mt-2">
        <span class="spinner"></span> <span id="uploadStatus" class="text-sm text-secondary">上传处理中...</span>
      </div>
    </div>
    <div class="divider"></div>
    <div id="docDetail" class="hidden"></div>
    <div id="docList" class="doc-list">
      <div class="loading-state"><span class="spinner"></span><p>加载中...</p></div>
    </div>
  `;

  const uploadZone = document.getElementById('uploadZone');
  const fileInput = document.getElementById('fileInput');
  uploadZone.addEventListener('click', () => fileInput.click());
  uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.classList.add('dragover'); });
  uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
  uploadZone.addEventListener('drop', e => {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) handleUpload(e.dataTransfer.files[0]);
  });
  fileInput.addEventListener('change', () => { if (fileInput.files.length) handleUpload(fileInput.files[0]); });

  loadDocuments();
}

async function handleUpload(file) {
  const progress = document.getElementById('uploadProgress');
  const status = document.getElementById('uploadStatus');
  progress.classList.remove('hidden');
  status.textContent = `正在上传: ${file.name}`;

  const formData = new FormData();
  formData.append('file', file);

  try {
    const result = await api.upload('/documents/upload', formData);
    progress.classList.add('hidden');
    if (result.error) {
      showToast(result.error, 'error');
    } else {
      showToast('上传成功，后台处理中...', 'success');
      setTimeout(loadDocuments, 2000);
    }
  } catch (e) {
    progress.classList.add('hidden');
    showToast(`上传失败: ${e.message}`, 'error');
  }
}

async function loadDocuments() {
  const docList = document.getElementById('docList');
  let data;
  try {
    data = await api.get('/documents');
    if (!data || !data.documents || !data.documents.length) {
      docList.innerHTML = showEmpty('', '还没有上传任何资料');
      return;
    }

    docList.innerHTML = data.documents.map(d => {
      let progressHtml = '';
      if (d.status === 'processing') {
        progressHtml = `
          <div class="doc-progress-bar" data-doc-id="${d.id}">
            <div class="doc-progress-fill" style="width:15%"></div>
          </div>
          <div class="doc-progress-label text-xs text-secondary">解析中...</div>
        `;
      }
      return `
      <div class="doc-item" data-id="${d.id}">
        <div class="doc-info">
          <div class="doc-name">${escapeHtml(d.filename)}</div>
          <div class="doc-meta">
            ${getStatusBadge(d.status)}${d.file_category === 'multimodal' ? ' <span class="badge badge-info">多模态</span>' : ''}
            <span>${d.chunk_count || 0} 片段</span>
            <span>${(d.file_size / 1024).toFixed(0)} KB</span>
            <span>${getProgressLabel(d.progress_status || 'not_started')}</span>
          </div>
          ${progressHtml}
        </div>
        <div class="doc-actions">
          ${d.status === 'parsed' ? `<button class="btn btn-sm btn-ghost" data-action="view" data-id="${d.id}">查看</button>` : ''}
          ${d.status === 'error' ? `<button class="btn btn-sm btn-ghost" data-action="reparse" data-id="${d.id}">重试</button>` : ''}
          <button class="btn btn-sm btn-danger" data-action="delete" data-id="${d.id}">删除</button>
        </div>
      </div>
    `}).join('');

    docList.querySelectorAll('.doc-item .doc-info').forEach(info => {
      info.addEventListener('click', () => {
        const docId = parseInt(info.parentElement.dataset.id);
        viewDocument(docId);
      });
    });

    docList.querySelectorAll('[data-action]').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const action = btn.dataset.action;
        const id = parseInt(btn.dataset.id);
        if (action === 'delete') {
          const ok = await showConfirm('删除后所有关联的对话、测评、学习记录将被永久移除。确定删除？');
          if (!ok) return;
          // 乐观移除 DOM 节点
          const docItem = btn.closest('.doc-item');
          if (docItem) docItem.style.opacity = '0.3';
          try {
            await api.delete(`/documents/${id}`);
            showToast('已删除', 'success');
            // 关闭详情面板（防止显示已删除文档的详情）
            const detail = document.getElementById('docDetail');
            if (detail) detail.classList.add('hidden');
            await loadDocuments();
          } catch (e) {
            if (docItem) docItem.style.opacity = '1';
            showToast('删除失败: ' + e.message, 'error');
          }
        } else if (action === 'reparse') {
          await api.post(`/documents/${id}/reparse`);
          showToast('重新解析已启动', 'info');
          setTimeout(loadDocuments, 2000);
        } else if (action === 'view') {
          viewDocument(id);
        }
      });
    });
  } catch (e) {
    if (docList) docList.innerHTML = `<p class="text-error">加载失败: ${e.message}</p>`;
  }

  const processingDocs = data.documents?.filter(d => d.status === 'processing') || [];
  processingDocs.forEach(d => pollDocProgress(d.id));
}

async function pollDocProgress(docId) {
  // 同一文档只允许一个轮询
  if (window._docPolls && window._docPolls[docId]) return;
  window._docPolls = window._docPolls || {};
  const maxPolls = 30;  // 30 次 * 1.5s = 45s 后强制停止
  let polls = 0;
  const interval = setInterval(async () => {
    polls++;
    try {
      const progress = await api.get(`/documents/${docId}/progress`);
      // 文档可能已被删除
      if (progress.error || progress.status === 'not_found') {
        clearInterval(interval);
        delete window._docPolls[docId];
        return;
      }
      const bar = document.querySelector(`.doc-progress-bar[data-doc-id="${docId}"]`);
      const label = bar?.nextElementSibling;
      if (bar) bar.querySelector('.doc-progress-fill').style.width = `${progress.progress_pct || 0}%`;
      if (label) label.textContent = progress.stage_label || '解析中...';
      if (progress.status === 'parsed' || progress.status === 'error' || polls >= maxPolls) {
        clearInterval(interval);
        delete window._docPolls[docId];
        if (progress.status === 'parsed') loadDocuments();
      }
    } catch (e) {
      clearInterval(interval);
      delete window._docPolls[docId];
    }
  }, 1500);
  window._docPolls[docId] = interval;
}

async function viewDocument(docId) {
  const panel = document.getElementById('docDetail');
  panel.classList.remove('hidden');
  panel.innerHTML = '<div class="loading-state"><span class="spinner"></span><p>加载文档详情...</p></div>';
  panel.scrollIntoView({ behavior: 'smooth' });

  try {
    const data = await api.get(`/documents/${docId}`);
    if (!data || !data.document) {
      panel.innerHTML = '<p class="text-error">文档不存在</p>';
      return;
    }
    const d = data.document || data;

    panel.innerHTML = `
      <div class="doc-detail-panel">
        <div style="display:flex;justify-content:space-between;align-items:flex-start">
          <h3>${escapeHtml(d.filename)}</h3>
          <button class="btn btn-sm btn-ghost" onclick="document.getElementById('docDetail').classList.add('hidden')">关闭</button>
        </div>
        <div class="doc-detail-meta">
          <div class="meta-item"><span class="meta-label">状态</span><span class="meta-value">${getStatusBadge(d.status)}</span></div>
          <div class="meta-item"><span class="meta-label">大小</span><span class="meta-value">${(d.file_size / 1024).toFixed(0)} KB</span></div>
          <div class="meta-item"><span class="meta-label">分块数</span><span class="meta-value">${d.chunk_count || 0}</span></div>
          <div class="meta-item"><span class="meta-label">学习进度</span><span class="meta-value">${getProgressLabel(d.progress_status || 'not_started')}</span></div>
          <div class="meta-item"><span class="meta-label">上传时间</span><span class="meta-value">${formatDate(d.created_at)}</span></div>
          ${d.page_count ? `<div class="meta-item"><span class="meta-label">页数</span><span class="meta-value">${d.page_count}</span></div>` : ''}
        </div>
        ${data.chunks && data.chunks.length ? `
          <div class="doc-chunks-list">
            <p class="text-xs text-secondary mb-2">内容片段（${data.chunks.length}）</p>
            ${data.chunks.map((c, i) => `
              <div class="doc-chunk-item">
                <div class="chunk-idx">片段 ${i + 1}</div>
                <div>${escapeHtml(c.content ? c.content.slice(0, 300) + (c.content.length > 300 ? '...' : '') : '(空)')}</div>
              </div>
            `).join('')}
          </div>
        ` : '<p class="text-sm text-secondary mt-3">暂无内容片段</p>'}
      </div>
    `;
  } catch (e) {
    panel.innerHTML = `<p class="text-error">加载失败: ${e.message}</p>`;
  }
}
