// map.js —— 全屏「地图服务」面板
// 合规要求：不绘制任何地图图像 / 瓦片 / 国界省界轮廓，仅以文字 + 坐标卡片呈现。
// 由 app.js handleToolEvent 收到 { xiao6_event:'panel', panel:'map', data } 时调用 window.ZZMap.open(data)
// data 形状：
//   { type:'distance'|'location'|'citylist'|'empty', text,
//     from?:{name,lat,lon}, to?:{name,lat,lon},
//     km?, point?:{name,lat,lon}, cities?:[{name,lat,lon}] }

const MAP = { panel: null, open: false };

// 本地转义：避免依赖其它模块作用域内的 escapeHtml
function escapeHtml(str) {
  return String(str == null ? '' : str).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

function mapBuild() {
  if (MAP.panel) return;
  const html = `
  <div class="map-panel" id="map-panel" role="dialog" aria-label="地图服务">
    <div class="map-backdrop" data-close="1"></div>
    <div class="map-stage glass">
      <div class="map-bar">
        <div class="map-title"><span class="map-dot"></span>地图服务</div>
        <button class="map-close" id="map-close" title="关闭（Esc）" aria-label="关闭"><svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-close"/></svg></button>
      </div>
      <div class="map-body" id="map-body"></div>
    </div>
  </div>`;
  document.body.insertAdjacentHTML('beforeend', html);
  MAP.panel = document.getElementById('map-panel');
  document.getElementById('map-close').addEventListener('click', mapClose);
  MAP.panel.querySelector('[data-close]').addEventListener('click', mapClose);
}

// 把坐标格式化为固定精度字符串
function mapFmtCoord(lat, lon) {
  const f = (v) => (v == null ? '—' : Number(v).toFixed(5));
  return `${f(lat)}, ${f(lon)}`;
}

function mapPointCard(label, p) {
  if (!p) return '';
  const name = p.name != null ? escapeHtml(String(p.name)) : '未命名地点';
  const coord = p.lat != null && p.lon != null
    ? `<div class="map-coord"><span class="map-coord-ico">⌖</span>${mapFmtCoord(p.lat, p.lon)}</div>`
    : `<div class="map-coord map-coord-muted">无坐标信息</div>`;
  return `
    <div class="map-card">
      <div class="map-card-label">${escapeHtml(label)}</div>
      <div class="map-card-name">${name}</div>
      ${coord}
    </div>`;
}

function mapRender(data) {
  const body = document.getElementById('map-body');
  if (!body) return;
  if (!data || !data.type || data.type === 'empty') {
    const txt = (data && data.text) ? escapeHtml(String(data.text)) : '暂无地图信息';
    body.innerHTML = `<div class="map-empty">${txt}</div>`;
    return;
  }

  if (data.type === 'distance') {
    const km = (data.km != null) ? `${Number(data.km).toFixed(1)} km` : '未知距离';
    body.innerHTML = `
      <div class="map-hero">
        <div class="map-hero-route">${escapeHtml(data.from && data.from.name ? String(data.from.name) : '起点')}
          <span class="map-arrow">→</span>
          ${escapeHtml(data.to && data.to.name ? String(data.to.name) : '终点')}</div>
        <div class="map-hero-km">约 <b>${km}</b></div>
      </div>
      <div class="map-card-row">
        ${mapPointCard('起点', data.from)}
        ${mapPointCard('终点', data.to)}
      </div>`;
    return;
  }

  if (data.type === 'location') {
    const p = data.point || data.from || null;
    const city = (data.text) ? `<div class="map-empty map-loc-text">${escapeHtml(String(data.text))}</div>` : '';
    body.innerHTML = `
      ${city}
      <div class="map-card-row">
        ${mapPointCard('当前位置', p)}
      </div>`;
    return;
  }

  if (data.type === 'citylist') {
    const cities = Array.isArray(data.cities) ? data.cities : [];
    const chips = cities.length
      ? cities.map((c) => `
          <div class="map-chip">
            <div class="map-chip-name">${escapeHtml(c.name != null ? String(c.name) : '未命名')}</div>
            <div class="map-chip-coord">${mapFmtCoord(c.lat, c.lon)}</div>
          </div>`).join('')
      : `<div class="map-empty">暂无城市数据</div>`;
    body.innerHTML = `
      <div class="map-section-title">城市列表（${cities.length}）</div>
      <div class="map-chip-grid">${chips}</div>`;
    return;
  }

  // 兜底：未知 type，展示原始文本
  const txt = (data.text) ? escapeHtml(String(data.text)) : '未知地图请求';
  body.innerHTML = `<div class="map-empty">${txt}</div>`;
}

function mapOpen(data) {
  mapBuild();
  mapRender(data);
  requestAnimationFrame(() => document.body.classList.add('map-mode'));
  MAP.open = true;
  window.dispatchEvent(new CustomEvent('xiao6:map-mode', { detail: { active: true } }));
  // Sprint 1/2：登记到 OverlayManager（统一 ESC / 焦点 / 栈）
  if (window.OverlayManager) window.OverlayManager.track('map', { el: MAP.panel, onClose: mapCloseImpl, type: window.OverlayManager.OverlayType.PANEL, trap: false });
}

function mapCloseImpl() {
  document.body.classList.remove('map-mode');
  MAP.open = false;
  window.dispatchEvent(new CustomEvent('xiao6:map-mode', { detail: { active: false } }));
}

function mapClose() {
  if (window.OverlayManager && window.OverlayManager.isOpen('map')) window.OverlayManager.close('map');
  else mapCloseImpl();
}

window.ZZMap = { open: mapOpen, close: mapClose };
