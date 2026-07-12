/* 学习仪表盘页面 v2.4.2 — 去重版（热力图/趋势已移至进度页） */

import { api } from '../api.js';
import { renderTopbar, showEmpty } from '../components.js';
import { formatDate, escapeHtml } from '../utils.js';

export async function renderDashboardPage() {
  renderTopbar('dashboard');

  const mc = document.getElementById('mainContent');
  mc.className = 'main-content';
  mc.innerHTML = '<p class="text-center text-secondary mt-3"><span class="spinner"></span> 加载仪表盘...</p>';

  try {
    const overviewRes = await api.get('/dashboard/overview');
    const metrics = overviewRes.metrics || {};
    const weakPoints = overviewRes.weak_points || [];
    const recentDocs = overviewRes.docs || [];

    renderDashboard(mc, metrics, weakPoints, recentDocs);
  } catch (e) {
    mc.innerHTML = `<p class="text-error">仪表盘加载失败: ${e.message}</p>`;
    console.error(e);
  }
}

function renderDashboard(mc, metrics, weakPoints, recentDocs) {
  const parsingRate = metrics.doc_count > 0
    ? Math.round((metrics.parsed_count / metrics.doc_count) * 100) : 0;

  const weekHours = Math.floor(metrics.week_minutes / 60);
  const weekMins = metrics.week_minutes % 60;
  const weekTimeStr = metrics.week_minutes > 0
    ? `${weekHours}h ${weekMins}m` : '0m';

  mc.innerHTML = `
    <div class="dashboard-hero">
      <div>
        <h2 class="dashboard-title">学习仪表盘</h2>
        <p class="dashboard-subtitle">概览今日数据 · 薄弱点直达复习</p>
      </div>
      <div class="dashboard-quick-stats">
        <div class="qstat">
          <span class="qstat-num">${weekTimeStr}</span>
          <span class="qstat-label">本周</span>
        </div>
        <div class="qstat">
          <span class="qstat-num">${metrics.week_questions || 0}</span>
          <span class="qstat-label">提问</span>
        </div>
        <div class="qstat">
          <span class="qstat-num">${metrics.weak_points || 0}</span>
          <span class="qstat-label">薄弱点</span>
        </div>
      </div>
    </div>

    <div class="metrics-row">
      <div class="metric-card metric-card-doc">
        <div class="metric-icon">📚</div>
        <p class="metric-label">学习资料</p>
        <p class="metric-value">${metrics.doc_count || 0}</p>
        <div class="metric-bar"><div class="metric-bar-fill" style="width:${parsingRate}%"></div></div>
        <p class="metric-sub">${metrics.parsed_count || 0} 份已解析 · ${parsingRate}%</p>
      </div>
      <div class="metric-card metric-card-time">
        <div class="metric-icon">⏱</div>
        <p class="metric-label">本周学习</p>
        <p class="metric-value">${weekTimeStr}</p>
        <p class="metric-sub">${metrics.week_sessions || 0} 次会话</p>
      </div>
      <div class="metric-card metric-card-quiz">
        <div class="metric-icon">📝</div>
        <p class="metric-label">测评次数</p>
        <p class="metric-value">${metrics.assessment_count || 0}</p>
        <p class="metric-sub">累计完成测评</p>
      </div>
      <div class="metric-card metric-card-news">
        <div class="metric-icon">📰</div>
        <p class="metric-label">未读资讯</p>
        <p class="metric-value">${metrics.unread_news || 0}</p>
        <p class="metric-sub">AI 行业动态待阅读</p>
      </div>
    </div>

    <div class="dashboard-row">
      <div class="chart-card chart-card-weak">
        <div class="chart-card-head">
          <div>
            <h3>薄弱知识点</h3>
            <p class="chart-sub">最近测评中识别出的弱项，建议优先复习</p>
          </div>
          <a href="#/progress" class="btn btn-ghost btn-sm">查看全部 →</a>
        </div>
        ${renderWeakPoints(weakPoints)}
      </div>

      <div class="chart-card chart-card-recent">
        <div class="chart-card-head">
          <div>
            <h3>最近资料</h3>
            <p class="chart-sub">最近上传的 5 份文档</p>
          </div>
          <a href="#/library" class="btn btn-ghost btn-sm">资料库 →</a>
        </div>
        ${renderRecentDocs(recentDocs)}
      </div>
    </div>
  `;
}

function renderWeakPoints(weakPoints) {
  if (!weakPoints || weakPoints.length === 0) {
    return `<div class="empty-mini">🎯 暂无薄弱知识点，继续学习后系统会自动识别</div>`;
  }
  return `<ul class="weak-list">
    ${weakPoints.map(p => `
      <li>
        <span class="weak-name">${escapeHtml(p.topic || p.name || '未知')}</span>
        <span class="weak-level">${getMasteryLabel(p.mastery_level || p.mastery_rate)}</span>
        ${p.filename ? `<span class="weak-source">${escapeHtml(p.filename)}</span>` : ''}
      </li>`).join('')}
  </ul>`;
}

function renderRecentDocs(docs) {
  if (!docs || docs.length === 0) {
    return `<div class="empty-mini">📁 还未上传任何资料</div>`;
  }
  return `<ul class="recent-list">
    ${docs.slice(0, 5).map(d => `
      <li>
        <span class="recent-name">${escapeHtml(d.filename || '')}</span>
        <span class="recent-meta">${formatDate(d.created_at)}</span>
      </li>`).join('')}
  </ul>`;
}

function getMasteryLabel(level) {
  const labels = {
    '0': '未接触', '1': '入门', '2': '熟悉', '3': '精通', '4': '专家',
    'L0': '未接触', 'L1': '入门', 'L2': '熟悉', 'L3': '精通', 'L4': '专家',
    'weak': '薄弱', 'familiar': '一般', 'mastered': '已掌握',
    '0.0': '未接触', '0.25': '入门', '0.5': '熟悉', '0.75': '精通', '1.0': '专家'
  };
  return labels[String(level)] || level || '未知';
}
