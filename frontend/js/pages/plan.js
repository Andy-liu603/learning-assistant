/* 学习计划页面 v2.4 */

import { api } from '../api.js';
import { renderTopbar, showEmpty } from '../components.js';
import { formatDate, formatDateTime, showToast } from '../utils.js';

let currentPlanId = null;

export async function renderPlanPage() {
  renderTopbar('plan');
  const mc = document.getElementById('mainContent');
  mc.className = 'main-content';
  mc.innerHTML = '<p class="text-center text-secondary mt-3"><span class="spinner"></span> 加载中...</p>';

  try {
    const data = await api.get('/plans/list');
    const plans = data.plans || [];

    if (plans.length === 0) {
      mc.innerHTML = `
        <div class="plan-page">
          <h2>学习计划</h2>
          ${renderCreateForm()}
        </div>
      `;
    } else {
      mc.innerHTML = `
        <div class="plan-page">
          <h2>学习计划</h2>
          ${renderCreateForm()}
          <div class="plan-list" style="margin-top:24px;">
            ${plans.map(p => `
              <div class="plan-card card" style="margin-bottom:12px;cursor:pointer;"
                   onclick="window._viewPlan(${p.id})">
                <div class="plan-card-header">
                  <strong>${p.topic}</strong>
                  <span class="badge ${p.status === 'active' ? 'badge-success' : 'badge-info'}">${p.status === 'active' ? '进行中' : '已完成'}</span>
                </div>
                <p class="text-sm text-secondary" style="margin:4px 0 0">
                  ${p.duration_days}天 · 每日${p.daily_hours}h · ${p.current_level === 'beginner' ? '入门' : p.current_level === 'intermediate' ? '中级' : '高级'}
                  · ${formatDate(p.created_at)}
                </p>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }

    // 全局回调
    window._viewPlan = viewPlan;
    window._generatePlan = generatePlan;
    window._toggleDay = toggleDay;
    window._goBackToList = () => renderPlanPage();

  } catch (e) {
    mc.innerHTML = `<p class="text-error">加载失败: ${e.message}</p>`;
    console.error(e);
  }
}

function renderCreateForm() {
  return `
    <div class="card" style="margin-bottom:20px;">
      <h3 style="font-size:15px;font-weight:500;margin:0 0 16px;">创建新计划</h3>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
        <div class="form-group">
          <label class="form-label">学习主题</label>
          <input id="planTopic" class="form-input" placeholder="例如：机器学习基础">
        </div>
        <div class="form-group">
          <label class="form-label">当前水平</label>
          <select id="planLevel" class="form-select">
            <option value="beginner">入门</option>
            <option value="intermediate">中级</option>
            <option value="advanced">高级</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">计划天数</label>
          <select id="planDays" class="form-select">
            <option value="3">3天</option>
            <option value="7" selected>7天</option>
            <option value="14">14天</option>
            <option value="30">30天</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">每日学习时长</label>
          <select id="planHours" class="form-select">
            <option value="0.5">0.5小时</option>
            <option value="1" selected>1小时</option>
            <option value="2">2小时</option>
            <option value="3">3小时</option>
          </select>
        </div>
      </div>
      <button id="generatePlanBtn" class="btn btn-primary" style="margin-top:16px;width:100%;" onclick="window._generatePlan()">
        生成学习计划
      </button>
    </div>
  `;
}

async function generatePlan() {
  const topic = document.getElementById('planTopic').value.trim();
  const level = document.getElementById('planLevel').value;
  const days = parseInt(document.getElementById('planDays').value);
  const hours = parseFloat(document.getElementById('planHours').value);

  if (!topic) {
    showToast('请输入学习主题', 'error');
    return;
  }

  const btn = document.getElementById('generatePlanBtn');
  btn.textContent = 'AI 正在生成...';
  btn.disabled = true;

  try {
    const data = await api.post('/plans/generate', {
      topic, duration_days: days, current_level: level, daily_hours: hours
    });
    if (data.error) {
      showToast(data.error, 'error');
    } else {
      showToast('计划已生成！', 'success');
      renderPlanPage();
    }
  } catch (e) {
    showToast(e.message, 'error');
  } finally {
    btn.textContent = '生成学习计划';
    btn.disabled = false;
  }
}

async function viewPlan(planId) {
  currentPlanId = planId;
  const mc = document.getElementById('mainContent');

  try {
    const data = await api.get(`/plans/${planId}`);
    const plan = data.plan || {};
    const content = plan.content || {};
    const progress = plan.progress || {};

    const days = content.days || [];
    const totalDays = days.length;
    const completedDays = Object.values(progress).filter(v => v === true).length;
    const progressPct = totalDays > 0 ? Math.round(completedDays / totalDays * 100) : 0;

    mc.innerHTML = `
      <div class="plan-page">
        <div style="display:flex;align-items:center;gap:16px;margin-bottom:20px;">
          <button class="btn btn-ghost btn-sm" onclick="window._goBackToList()">← 返回</button>
          <h2 style="margin:0;">${plan.topic || '学习计划'}</h2>
        </div>

        <div class="card" style="margin-bottom:20px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
            <span style="font-weight:500;">学习进度</span>
            <span class="text-sm text-secondary">${completedDays}/${totalDays} 天完成（${progressPct}%）</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill" style="width:${progressPct}%;"></div>
          </div>
          ${content.overview ? `<p style="margin:8px 0 0;font-size:13px;color:var(--text-secondary);">${content.overview}</p>` : ''}
        </div>

        <div class="plan-timeline">
          ${days.map(d => `
            <div class="plan-day card" style="margin-bottom:12px;border-left:3px solid var(${progress[d.day] ? '--success' : '--border'});">
              <div style="display:flex;align-items:center;gap:12px;">
                <div style="min-width:48px;text-align:center;">
                  <div style="font-family:var(--font-display);font-size:24px;font-weight:500;color:var(--rust);">${d.day}</div>
                  <div style="font-size:11px;color:var(--text-tertiary);">天</div>
                </div>
                <div style="flex:1;">
                  <div style="display:flex;justify-content:space-between;align-items:center;">
                    <strong style="font-size:15px;">${d.title || 'Day ' + d.day}</strong>
                    <label style="display:flex;align-items:center;gap:6px;cursor:pointer;font-size:13px;" onclick="event.stopPropagation();">
                      <input type="checkbox" ${progress[d.day] ? 'checked' : ''}
                             onchange="window._toggleDay(${planId}, ${d.day}, this.checked)"
                             style="width:16px;height:16px;accent-color:var(--rust);">
                      已完成
                    </label>
                  </div>
                  <p style="margin:4px 0 0;font-size:13px;color:var(--text-secondary);">目标：${d.goal || ''}</p>
                  ${d.tasks ? `<div style="margin-top:8px;">${d.tasks.map(t => `<div style="font-size:13px;color:var(--text-secondary);padding:3px 0;">• ${t}</div>`).join('')}</div>` : ''}
                </div>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;

  } catch (e) {
    mc.innerHTML = `<p class="text-error">加载计划失败: ${e.message}</p>`;
    console.error(e);
  }
}

async function toggleDay(planId, day, completed) {
  try {
    await api.put(`/plans/${planId}/progress`, { day: String(day), completed });
    // 刷新当前视图
    viewPlan(planId);
  } catch (e) {
    showToast('更新失败', 'error');
  }
}

// 全局绑定
window._viewPlan = viewPlan;
window._generatePlan = generatePlan;
window._toggleDay = toggleDay;
window._goBackToList = () => renderPlanPage();
