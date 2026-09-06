/* ============================================================
   全球洞察 GFE Dashboard — 前端逻辑
   Xiao6 v1.0.0
   ============================================================ */
(function () {
  "use strict";

  /* =========================================================
     数据获取
     ========================================================= */
  async function fetchDashboard() {
    try {
      return await window.__api_getJSON("/api/gfe/dashboard");
    } catch (e) {
      console.warn("[GFE] Dashboard fetch failed:", e);
      return null;
    }
  }

  /* =========================================================
     渲染组件
     ========================================================= */

  function renderRiskOverview(data) {
    const rs = data.risk_summary || {};
    const events = data.events || [];
    const warnings = data.warnings || [];

    const highRiskCountries = warnings
      .filter(w => (w.severity || 0) >= 0.7)
      .map(w => w.country_code || "?");

    let totalRisk = rs.total_risk_index || 0;
    let activeCount = rs.active_events_count || 0;
    let highSeverityCount = rs.high_severity_count || 0;

    const html = `
      <div class="gfe-section gfe-risk-overview">
        <div class="gfe-section-header">
          <span class="gfe-section-title">🌍 全球风险概览</span>
          <span class="gfe-section-badge">${new Date().toLocaleDateString()}</span>
        </div>
        <div class="gfe-risk-hero">
          <div class="gfe-risk-index">
            <div class="gfe-risk-index-value">${totalRisk.toFixed(2)}</div>
            <div class="gfe-risk-index-label">综合风险指数</div>
          </div>
          <div class="gfe-risk-stats">
            <div class="gfe-risk-stat">
              <div class="gfe-risk-stat-value" style="color:${activeCount > 5 ? 'var(--brand)' : 'var(--ink-1)'}">${activeCount}</div>
              <div class="gfe-risk-stat-label">活跃事件</div>
            </div>
            <div class="gfe-risk-stat">
              <div class="gfe-risk-stat-value" style="color:${highSeverityCount > 0 ? 'var(--brand)' : 'var(--ok)'}">${highSeverityCount}</div>
              <div class="gfe-risk-stat-label">高风险</div>
            </div>
            <div class="gfe-risk-stat">
              <div class="gfe-risk-stat-value">${warnings.filter(w=>w.status==='active').length}</div>
              <div class="gfe-risk-stat-label">活跃预警</div>
            </div>
          </div>
        </div>
        ${highRiskCountries.length > 0 ? `
          <div class="gfe-risk-high-list">
            ${highRiskCountries.map(c => `<span class="gfe-country-tag">🔴 ${c}</span>`).join("")}
          </div>
        ` : ""}
      </div>
    `;
    return html;
  }

  function renderEventPanel(events) {
    if (!events || events.length === 0) {
      return `
        <div class="gfe-section">
          <div class="gfe-section-header">
            <span class="gfe-section-title">📡 事件情报</span>
            <span class="gfe-section-badge">无事件</span>
          </div>
          <div class="gfe-empty">暂无活跃事件</div>
        </div>
      `;
    }

    const sorted = [...events].sort((a, b) => (b.severity || 0) - (a.severity || 0)).slice(0, 5);
    const items = sorted.map(e => {
      const sev = (e.severity || 0) >= 0.7 ? 'high' : ((e.severity || 0) >= 0.4 ? 'medium' : 'low');
      return `
        <div class="gfe-event-item severity-${sev}">
          <div class="gfe-event-severity ${sev}">${(e.severity || 0).toFixed(1)}</div>
          <div class="gfe-event-content">
            <div class="gfe-event-title" title="${e.title || e.event_type || '未知事件'}">${e.title || e.event_type || '未命名事件'}</div>
            <div class="gfe-event-meta">
              <span>${e.category || '—'}</span>
              <span>•</span>
              <span>${e.country_code || '—'}</span>
              <span>•</span>
              <span>${e.impacted_dims || '—'}</span>
            </div>
          </div>
        </div>
      `;
    }).join("");

    return `
      <div class="gfe-section">
        <div class="gfe-section-header">
          <span class="gfe-section-title">📡 事件情报</span>
          <span class="gfe-section-badge">${events.length} 个</span>
        </div>
        <div class="gfe-event-list">${items}</div>
      </div>
    `;
  }

  function renderForecastPanel(forecasts) {
    if (!forecasts || forecasts.length === 0) {
      return `
        <div class="gfe-section">
          <div class="gfe-section-header">
            <span class="gfe-section-title">🔮 预测面板</span>
            <span class="gfe-section-badge">无预测</span>
          </div>
          <div class="gfe-empty">暂无活跃预测</div>
        </div>
      `;
    }

    const items = forecasts.slice(0, 5).map(f => {
      const prob = (f.probability || 0).toFixed(0) + "%";
      const conf = (f.confidence || 0).toFixed(2);
      const horizon = f.horizon_months || "?";
      return `
        <div class="gfe-forecast-item">
          <div class="gfe-forecast-title">${f.forecast_type || f.description || '未命名预测'}</div>
          <div class="gfe-forecast-stats">
            <span>概率 <span class="gfe-forecast-stat-value">${prob}</span></span>
            <span>置信度 <span class="gfe-forecast-stat-value">${conf}</span></span>
            <span>周期 <span class="gfe-forecast-stat-value">${horizon}月</span></span>
          </div>
        </div>
      `;
    }).join("");

    return `
      <div class="gfe-section">
        <div class="gfe-section-header">
          <span class="gfe-section-title">🔮 预测面板</span>
          <span class="gfe-section-badge">${forecasts.length} 个</span>
        </div>
        <div class="gfe-forecast-list">${items}</div>
      </div>
    `;
  }

  function renderCalibrationPanel(data) {
    const cal = data.calibration || {};
    const analysts = cal.analyst_metrics || [];

    const avgBrier = cal.overall_brier_score || 0;
    const calScore = cal.overall_calibration_score || 0;
    const sampleCount = cal.total_records || 0;

    let analystRows = "";
    if (analysts.length > 0) {
      analystRows = analysts.slice(0, 5).map(a => `
        <div class="gfe-analyst-item">
          <span class="gfe-analyst-name">${a.analyst_id}</span>
          <span class="gfe-analyst-brier">Brier <strong>${(a.average_brier_score || 0).toFixed(3)}</strong></span>
          <span class="gfe-analyst-brier">校准 <strong>${(a.calibration_score || 0).toFixed(2)}</strong></span>
        </div>
      `).join("");
    }

    return `
      <div class="gfe-section">
        <div class="gfe-section-header">
          <span class="gfe-section-title">📊 校准面板</span>
          <span class="gfe-section-badge">${sampleCount} 条记录</span>
        </div>
        <div class="gfe-calibration-grid">
          <div class="gfe-calc-item">
            <div class="gfe-calc-value" style="color:${avgBrier > 0.3 ? 'var(--brand)' : 'var(--ok)'}">${avgBrier.toFixed(3)}</div>
            <div class="gfe-calc-label">平均 Brier Score</div>
          </div>
          <div class="gfe-calc-item">
            <div class="gfe-calc-value" style="color:${calScore < 0.5 ? 'var(--brand)' : 'var(--ok)'}">${calScore.toFixed(2)}</div>
            <div class="gfe-calc-label">校准度</div>
          </div>
          <div class="gfe-calc-item">
            <div class="gfe-calc-value">${analysts.length}</div>
            <div class="gfe-calc-label">分析师</div>
          </div>
        </div>
        ${analystRows ? `<div class="gfe-analyst-list" style="margin-top:12px">${analystRows}</div>` : ""}
      </div>
    `;
  }

  function renderWarningPanel(warnings) {
    if (!warnings || warnings.length === 0) {
      return `
        <div class="gfe-section">
          <div class="gfe-section-header">
            <span class="gfe-section-title">⚠️ 预警面板</span>
            <span class="gfe-section-badge">无预警</span>
          </div>
          <div class="gfe-empty">当前无活跃预警</div>
        </div>
      `;
    }

    const items = warnings.slice(0, 5).map(w => {
      const sev = (w.severity || 0) >= 0.7 ? 'high' : ((w.severity || 0) >= 0.4 ? 'medium' : 'low');
      const statusClass = w.status === 'acknowledged' ? 'status-acknowledged' : (w.status === 'resolved' ? 'status-resolved' : '');
      return `
        <div class="gfe-warning-item ${statusClass}">
          <div class="gfe-warning-title">${w.title || '未命名预警'} <span class="gfe-section-badge" style="margin-left:6px">${w.status || 'active'}</span></div>
          <div class="gfe-warning-meta">
            <span>国家: ${w.country_code || '—'}</span>
            <span>风险: ${(w.severity || 0).toFixed(2)}</span>
            <span>概率: ${(w.probability || 0).toFixed(0)}%</span>
            <span>置信: ${(w.confidence || 0).toFixed(2)}</span>
          </div>
          <div class="gfe-warning-evidence">${w.description || ''}</div>
        </div>
      `;
    }).join("");

    return `
      <div class="gfe-section">
        <div class="gfe-section-header">
          <span class="gfe-section-title">⚠️ 预警面板</span>
          <span class="gfe-section-badge">${warnings.filter(w=>w.status==='active').length} 活跃</span>
        </div>
        <div class="gfe-warning-list">${items}</div>
      </div>
    `;
  }

  /* =========================================================
     主渲染函数
     ========================================================= */
  function renderDashboard(data) {
    const el = document.getElementById("gfeDashboard");
    if (!el) return;

    if (!data) {
      el.innerHTML = '<div class="gfe-empty">无法加载数据，请检查服务连接</div>';
      return;
    }

    const parts = [
      renderRiskOverview(data),
      renderEventPanel(data.events),
      renderForecastPanel(data.forecasts),
      renderCalibrationPanel(data),
      renderWarningPanel(data.warnings),
    ];

    el.innerHTML = `<div class="gfe-dashboard">${parts.join("")}</div>`;
  }

  /* =========================================================
     公开接口
     ========================================================= */
  window.loadGfeDashboard = async function () {
    const el = document.getElementById("gfeDashboard");
    if (!el) return;
    el.innerHTML = '<div class="gfe-loading"><span class="spinner"></span>加载中…</div>';
    try {
      const data = await fetchDashboard();
      renderDashboard(data);
    } catch (e) {
      el.innerHTML = `<div class="gfe-empty">加载失败: ${e.message}</div>`;
    }
  };

  /* =========================================================
     绑定刷新按钮
     ========================================================= */
  function bindRefresh() {
    const btn = document.querySelector('[data-act="refresh-gfe"]');
    if (btn) {
      btn.addEventListener("click", () => {
        window.loadGfeDashboard();
      });
    }
  }

  /* =========================================================
     初始化
     ========================================================= */
  document.addEventListener("DOMContentLoaded", () => {
    bindRefresh();
  });

})();
