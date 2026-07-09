/* 学习仪表盘页面 v2.4 */

import { api } from '../api.js';
import { renderTopbar, showEmpty } from '../components.js';
import { formatDate } from '../utils.js';

export async function renderDashboardPage() {
  renderTopbar('dashboard');

  const mc = document.getElementById('mainContent');
  mc.className = 'main-content';
  mc.innerHTML = '<p class="text-center text-secondary mt-3"><span class="spinner"></span> 加载仪表盘...</p>';

  try {
    const [overviewRes, heatmapRes, trendRes] = await Promise.all([
      api.get('/dashboard/overview'),
      api.get('/dashboard/heatmap'),
      api.get('/dashboard/trend')
    ]);

    const metrics = overviewRes.metrics || {};
    const weakPoints = overviewRes.weak_points || [];
    const heatmapData = heatmapRes.data || [];
    const trendData = trendRes.data || [];

    renderDashboard(mc, metrics, weakPoints, heatmapData, trendData);
    initCharts(heatmapData, trendData);

  } catch (e) {
    mc.innerHTML = `<p class="text-error">仪表盘加载失败: ${e.message}</p>`;
    console.error(e);
  }
}

function renderDashboard(mc, metrics, weakPoints, heatmapData, trendData) {
  const parsingRate = metrics.doc_count > 0
    ? Math.round((metrics.parsed_count / metrics.doc_count) * 100) : 0;

  // 周学习时长格式化
  const weekHours = Math.floor(metrics.week_minutes / 60);
  const weekMins = metrics.week_minutes % 60;
  const weekTimeStr = metrics.week_minutes > 0
    ? `${weekHours}h ${weekMins}m` : '暂无数据';

  mc.innerHTML = `
    <div class="welcome-banner">
      <h2>欢迎回来</h2>
      <p class="daily-tip">今天适合学习一个新概念。你目前有 <strong>${metrics.weak_points || 0}</strong> 个薄弱知识点需要复习，从 <strong>${metrics.parsed_count || 0}</strong> 份已解析的资料中挖掘新知识吧。</p>
    </div>

    <div class="metrics-row">
      <div class="metric-card">
        <div class="metric-icon">📚</div>
        <p class="metric-label">学习资料</p>
        <p class="metric-value">${metrics.doc_count || 0}</p>
        <p class="metric-sub">${metrics.parsed_count || 0} 份已解析（${parsingRate}%）</p>
      </div>
      <div class="metric-card">
        <div class="metric-icon">⏱</div>
        <p class="metric-label">本周学习</p>
        <p class="metric-value">${weekTimeStr}</p>
        <p class="metric-sub">${metrics.week_questions || 0} 次提问 · ${metrics.week_sessions || 0} 次会话</p>
      </div>
      <div class="metric-card">
        <div class="metric-icon">📝</div>
        <p class="metric-label">测评次数</p>
        <p class="metric-value">${metrics.assessment_count || 0}</p>
        <p class="metric-sub">累计完成测评</p>
      </div>
      <div class="metric-card">
        <div class="metric-icon">📰</div>
        <p class="metric-label">未读资讯</p>
        <p class="metric-value">${metrics.unread_news || 0}</p>
        <p class="metric-sub">AI 行业动态待阅读</p>
      </div>
    </div>

    <div class="dashboard-grid">
      <div class="chart-panel">
        <h3>90 天学习热力图</h3>
        <div id="heatmapChart" class="chart-container tall"></div>
      </div>
      <div class="chart-panel">
        <h3>学习趋势（近8周）</h3>
        <div id="trendChart" class="chart-container"></div>
      </div>
      <div class="chart-panel">
        <h3>薄弱知识点</h3>
        ${renderWeakPoints(weakPoints)}
      </div>
      <div class="chart-panel">
        <h3>最近活动</h3>
        ${renderActivityTimeline(heatmapData, trendData)}
      </div>
    </div>
  `;
}

function renderWeakPoints(weakPoints) {
  if (!weakPoints || weakPoints.length === 0) {
    return showEmpty('🎯', '暂无薄弱知识点，继续学习后系统会自动识别');
  }
  return weakPoints.map(p => `
    <div class="weak-alert">
      <strong>${p.topic || p.name || '未知'}</strong>
      — 掌握度：${getMasteryLabel(p.mastery_level || p.mastery_rate)}
      ${p.source ? `<br><small style="color:var(--text-tertiary)">来源：${p.source}</small>` : ''}
    </div>
  `).join('');
}

function renderActivityTimeline(heatmapData, trendData) {
  if (heatmapData.length === 0 && trendData.length === 0) {
    return showEmpty('📊', '暂无学习活动，开始学习后会出现在这里');
  }

  const items = [];
  // 取最近 5 天有学习记录
  const recent = heatmapData.slice(-5).reverse();
  for (const [day, minutes] of recent) {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    const timeStr = hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
    items.push(`
      <li>
        <span class="time-badge">${day.slice(5)}</span>
        <span>学习 ${timeStr}</span>
      </li>
    `);
  }

  if (items.length === 0) {
    items.push('<li><span class="time-badge">-</span><span>最近无学习记录</span></li>');
  }

  return `<ul class="activity-timeline">${items.join('')}</ul>`;
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

function initCharts(heatmapData, trendData) {
  // 热力图
  if (heatmapData.length > 0 && document.getElementById('heatmapChart')) {
    const heatEl = document.getElementById('heatmapChart');
    const chart = echarts.init(heatEl);

    const seriesData = heatmapData.map(([day, minutes]) => {
      const hours = Math.round(minutes / 60 * 10) / 10;
      return [day, hours];
    });

    const today = new Date();
    const startDate = new Date(today);
    startDate.setDate(startDate.getDate() - 90);
    const endDate = new Date(today);
    endDate.setDate(endDate.getDate() + 1);

    chart.setOption({
      tooltip: {
        position: 'top',
        formatter: function(p) {
          return p.data[0] + ': ' + p.data[1] + 'h';
        }
      },
      visualMap: {
        min: 0,
        max: Math.max(3, ...(seriesData.map(d => d[1]))),
        type: 'piecewise',
        orient: 'horizontal',
        left: 'center',
        bottom: 0,
        pieces: [
          { min: 3, color: '#993C1D' },
          { min: 2, max: 3, color: '#D85A30' },
          { min: 1, max: 2, color: '#F0997B' },
          { min: 0.1, max: 1, color: '#F5C4B3' },
          { value: 0, color: '#F1EFE8' }
        ]
      },
      calendar: {
        top: 10,
        left: 16,
        right: 16,
        cellSize: [14, 14],
        range: [startDate, endDate],
        itemStyle: { borderColor: '#fff', borderWidth: 2 },
        yearLabel: { show: false },
        dayLabel: { firstDay: 1, fontSize: 11, color: '#888780' },
        monthLabel: { fontSize: 11, color: '#888780' }
      },
      series: [{
        type: 'heatmap',
        coordinateSystem: 'calendar',
        data: seriesData,
        label: { show: false }
      }]
    });

    window.addEventListener('resize', () => chart.resize());
  }

  // 趋势折线图
  if (trendData.length > 0 && document.getElementById('trendChart')) {
    const trendEl = document.getElementById('trendChart');
    const chart = echarts.init(trendEl);

    chart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { top: 16, right: 16, bottom: 24, left: 40 },
      xAxis: {
        type: 'category',
        data: trendData.map(d => d.week),
        axisLine: { lineStyle: { color: '#D3D1C7' } },
        axisLabel: { fontSize: 10, color: '#888780' }
      },
      yAxis: {
        type: 'value',
        name: '分钟',
        splitLine: { lineStyle: { color: '#F1EFE8' } },
        axisLabel: { fontSize: 10, color: '#888780' }
      },
      series: [{
        data: trendData.map(d => d.minutes),
        type: 'line',
        smooth: true,
        lineStyle: { color: '#D85A30', width: 2 },
        itemStyle: { color: '#D85A30' },
        areaStyle: { color: 'rgba(216, 90, 48, 0.08)' },
        symbol: 'circle',
        symbolSize: 4
      }]
    });

    window.addEventListener('resize', () => chart.resize());
  }
}
