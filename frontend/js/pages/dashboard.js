/* 学习仪表盘页面 v2.4.1 — 美化版 */

import { api } from '../api.js';
import { renderTopbar, showEmpty } from '../components.js';
import { formatDate } from '../utils.js';

let _heatmapChart = null;
let _trendChart = null;

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
    setTimeout(() => initCharts(heatmapData, trendData), 50);

  } catch (e) {
    mc.innerHTML = `<p class="text-error">仪表盘加载失败: ${e.message}</p>`;
    console.error(e);
  }
}

function renderDashboard(mc, metrics, weakPoints, heatmapData, trendData) {
  const parsingRate = metrics.doc_count > 0
    ? Math.round((metrics.parsed_count / metrics.doc_count) * 100) : 0;

  const weekHours = Math.floor(metrics.week_minutes / 60);
  const weekMins = metrics.week_minutes % 60;
  const weekTimeStr = metrics.week_minutes > 0
    ? `${weekHours}h ${weekMins}m` : '0m';

  // 学习趋势数字概要
  const totalTrendMinutes = trendData.reduce((s, d) => s + (d.minutes || 0), 0);
  const avgDailyMin = heatmapData.length > 0
    ? Math.round(metrics.week_minutes / 7) : 0;

  mc.innerHTML = `
    <div class="dashboard-hero">
      <div>
        <h2 class="dashboard-title">学习仪表盘</h2>
        <p class="dashboard-subtitle">实时追踪学习进度与掌握度</p>
      </div>
      <div class="dashboard-quick-stats">
        <div class="qstat">
          <span class="qstat-num">${heatmapData.length}</span>
          <span class="qstat-label">已记录</span>
        </div>
        <div class="qstat">
          <span class="qstat-num">${avgDailyMin}<small>m</small></span>
          <span class="qstat-label">日均</span>
        </div>
        <div class="qstat">
          <span class="qstat-num">${totalTrendMinutes}<small>m</small></span>
          <span class="qstat-label">8周总</span>
        </div>
      </div>
    </div>

    <div class="metrics-row">
      <div class="metric-card metric-card-doc">
        <div class="metric-icon">📚</div>
        <p class="metric-label">学习资料</p>
        <p class="metric-value">${metrics.doc_count || 0}</p>
        <div class="metric-bar">
          <div class="metric-bar-fill" style="width:${parsingRate}%"></div>
        </div>
        <p class="metric-sub">${metrics.parsed_count || 0} 份已解析 · ${parsingRate}%</p>
      </div>
      <div class="metric-card metric-card-time">
        <div class="metric-icon">⏱</div>
        <p class="metric-label">本周学习</p>
        <p class="metric-value">${weekTimeStr}</p>
        <p class="metric-sub">${metrics.week_questions || 0} 次提问 · ${metrics.week_sessions || 0} 次会话</p>
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

    <div class="chart-card chart-card-heatmap">
      <div class="chart-card-head">
        <div>
          <h3>90 天学习热力图</h3>
          <p class="chart-sub">每格代表一天，颜色越深学习时间越长</p>
        </div>
        <div class="chart-legend">
          <span class="legend-dot" style="background:#F1EFE8"></span>0
          <span class="legend-dot" style="background:#F5C4B3"></span>少
          <span class="legend-dot" style="background:#F0997B"></span>中
          <span class="legend-dot" style="background:#D85A30"></span>多
          <span class="legend-dot" style="background:#993C1D"></span>专注
        </div>
      </div>
      <div id="heatmapChart" class="chart-container"></div>
    </div>

    <div class="chart-card chart-card-trend">
      <div class="chart-card-head">
        <div>
          <h3>学习趋势（近 8 周）</h3>
          <p class="chart-sub">每周累计学习时长（分钟）</p>
        </div>
      </div>
      <div id="trendChart" class="chart-container"></div>
    </div>
  `;
}

function initCharts(heatmapData, trendData) {
  // 释放旧图
  if (_heatmapChart) { _heatmapChart.dispose(); _heatmapChart = null; }
  if (_trendChart) { _trendChart.dispose(); _trendChart = null; }

  // ── 热力图：堆叠式（每列 7 天，行=周） ──
  const heatEl = document.getElementById('heatmapChart');
  if (heatEl) {
    // 将 90 天数据按 7 天一列分组
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const seriesData = [];
    const minDate = new Date(today);
    minDate.setDate(minDate.getDate() - 89);

    for (let i = 0; i < 90; i++) {
      const d = new Date(minDate);
      d.setDate(d.getDate() + i);
      const dateStr = d.toISOString().slice(0, 10);
      const found = heatmapData.find(([day]) => day === dateStr);
      const minutes = found ? found[1] : 0;
      seriesData.push([dateStr, Math.round(minutes / 60 * 10) / 10]);
    }

    _heatmapChart = echarts.init(heatEl);
    _heatmapChart.setOption({
      tooltip: {
        formatter: function(p) {
          return `<b>${p.data[0]}</b><br/>学习 ${p.data[1]} 小时`;
        }
      },
      visualMap: {
        min: 0,
        max: Math.max(2, ...seriesData.map(d => d[1])),
        show: false,
        pieces: [
          { min: 3, color: '#993C1D' },
          { min: 2, max: 3, color: '#D85A30' },
          { min: 1, max: 2, color: '#F0997B' },
          { min: 0.1, max: 1, color: '#F5C4B3' },
          { value: 0, color: '#EDE8DC' }
        ]
      },
      calendar: {
        top: 14,
        left: 50,
        right: 16,
        cellSize: ['auto', 18],
        range: [minDate, today],
        itemStyle: { borderColor: '#FBF9F5', borderWidth: 3, borderRadius: 3 },
        yearLabel: { show: false },
        dayLabel: { firstDay: 1, fontSize: 11, color: '#888780', nameMap: ['日','一','二','三','四','五','六'] },
        monthLabel: { fontSize: 11, color: '#888780' },
        splitLine: { show: false }
      },
      series: [{
        type: 'heatmap',
        coordinateSystem: 'calendar',
        data: seriesData
      }]
    });
  }

  // ── 趋势图：横向柱状图，标签清晰可读 ──
  const trendEl = document.getElementById('trendChart');
  if (trendEl) {
    _trendChart = echarts.init(trendEl);
    const labels = trendData.map(d => d.week);
    const values = trendData.map(d => d.minutes);
    const maxVal = Math.max(60, ...values);

    _trendChart.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: function(p) {
          const d = p[0];
          return `<b>${d.name}</b><br/>学习 ${d.value} 分钟`;
        }
      },
      grid: { top: 16, right: 32, bottom: 30, left: 60 },
      xAxis: {
        type: 'category',
        data: labels,
        axisLine: { lineStyle: { color: '#D3D1C7' } },
        axisTick: { show: false },
        axisLabel: { fontSize: 11, color: '#888780' }
      },
      yAxis: {
        type: 'value',
        name: '分钟',
        nameTextStyle: { color: '#888780', fontSize: 11 },
        max: maxVal,
        splitLine: { lineStyle: { color: '#F1EFE8' } },
        axisLabel: { fontSize: 11, color: '#888780' }
      },
      series: [{
        type: 'bar',
        data: values,
        barMaxWidth: 32,
        itemStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: '#D85A30' },
              { offset: 1, color: '#F0997B' }
            ]
          },
          borderRadius: [4, 4, 0, 0]
        },
        label: {
          show: true, position: 'top', color: '#2C2C2A', fontSize: 11,
          formatter: ({ value }) => value > 0 ? value + 'm' : ''
        }
      }]
    });
  }

  // resize 处理
  if (!_dashboardResizeBound) {
    window.addEventListener('resize', () => {
      _heatmapChart && _heatmapChart.resize();
      _trendChart && _trendChart.resize();
    });
    _dashboardResizeBound = true;
  }
}

let _dashboardResizeBound = false;
