// 天气面板
// 全屏玻璃拟态天气大屏：当前天气大字 + 3/7 天预报 + 城市切换 + 自动定位。
// 后端 /api/weather 返回 cardProps 形状：{ ok, city, mode, card, forecast[] }
const WX = (() => {
  const $ = (id) => document.getElementById(id);

  const REFRESH_MS = 30 * 60 * 1000; // 30 分钟
  const BOOT_DELAY_MS = 0;

  let panelEl = null;
  let open = false;
  let mode = 'compact'; // compact | week
  let city = '';         // 空 = 用后端自动定位城市
  let refreshTimer = null;
  let clockTimer = null;
  let bootTimer = null;
  let lastGeo = null; // 定位结果缓存，避免切模式时反复定位
  let lastManualCity = null; // 最近一次主动搜索的城市（用于失败友好提示/历史记录）

  const CONDITION_ICON = {
    '晴': '☀️', '局部多云': '🌤️', '多云': '⛅', '阴': '☁️', '阴云密布': '☁️',
    '薄雾': '🌫️', '雾': '🌫️', '冻雾': '🌫️', '小雨': '🌦️', '小阵雨': '🌦️',
    '中雨': '🌧️', '大雨': '🌧️', '暴雨': '⛈️', '雷雨': '⛈️', '雷暴': '⛈️',
    '小雪': '🌨️', '中雪': '🌨️', '大雪': '❄️', '暴风雪': '❄️', '雨夹雪': '🌨️',
    '毛毛雨': '🌦️', '细雨': '🌦️', '冻雨': '🌧️',
  };
  function condIcon(c) {
    return CONDITION_ICON[c] || '🌡️';
  }

  // 城市候选库：中文名 + 拼音/英文别名，用于输入联想与搜索补全
  const CITY_DB = [
    { n: '北京', a: ['beijing', 'bj'] }, { n: '上海', a: ['shanghai', 'sh'] },
    { n: '广州', a: ['guangzhou', 'gz'] }, { n: '深圳', a: ['shenzhen'] },
    { n: '杭州', a: ['hangzhou'] }, { n: '成都', a: ['chengdu'] },
    { n: '重庆', a: ['chongqing', 'cq'] }, { n: '武汉', a: ['wuhan'] },
    { n: '西安', a: ['xian', 'xi\'an'] }, { n: '南京', a: ['nanjing'] },
    { n: '天津', a: ['tianjin'] }, { n: '苏州', a: ['suzhou'] },
    { n: '长沙', a: ['changsha'] }, { n: '郑州', a: ['zhengzhou'] },
    { n: '青岛', a: ['qingdao'] }, { n: '厦门', a: ['xiamen', 'amoy'] },
    { n: '昆明', a: ['kunming'] }, { n: '大连', a: ['dalian'] },
    { n: '宁波', a: ['ningbo'] }, { n: '福州', a: ['fuzhou'] },
    { n: '济南', a: ['jinan'] }, { n: '合肥', a: ['hefei'] },
    { n: '哈尔滨', a: ['harbin'] }, { n: '沈阳', a: ['shenyang'] },
    { n: '长春', a: ['changchun'] }, { n: '石家庄', a: ['shijiazhuang'] },
    { n: '太原', a: ['taiyuan'] }, { n: '南昌', a: ['nanchang'] },
    { n: '贵阳', a: ['guiyang'] }, { n: '南宁', a: ['nanning'] },
    { n: '兰州', a: ['lanzhou'] }, { n: '海口', a: ['haikou'] },
    { n: '三亚', a: ['sanya'] }, { n: '拉萨', a: ['lhasa'] },
    { n: '乌鲁木齐', a: ['urumqi'] }, { n: '呼和浩特', a: ['hohhot'] },
    { n: '香港', a: ['hongkong', 'hong kong', 'xianggang'] },
    { n: '澳门', a: ['macau', 'macao', 'aomen'] }, { n: '台北', a: ['taipei'] },
    { n: '东京', a: ['tokyo'] }, { n: '大阪', a: ['osaka'] },
    { n: '名古屋', a: ['nagoya'] }, { n: '首尔', a: ['seoul'] },
    { n: '釜山', a: ['busan'] }, { n: '新加坡', a: ['singapore', 'sg'] },
    { n: '曼谷', a: ['bangkok'] }, { n: '吉隆坡', a: ['kualalumpur', 'kl'] },
    { n: '雅加达', a: ['jakarta'] }, { n: '马尼拉', a: ['manila'] },
    { n: '河内', a: ['hanoi'] }, { n: '新德里', a: ['newdelhi', 'delhi'] },
    { n: '孟买', a: ['mumbai'] }, { n: '迪拜', a: ['dubai'] },
    { n: '伊斯坦布尔', a: ['istanbul'] }, { n: '伦敦', a: ['london'] },
    { n: '巴黎', a: ['paris'] }, { n: '柏林', a: ['berlin'] },
    { n: '罗马', a: ['rome'] }, { n: '马德里', a: ['madrid'] },
    { n: '莫斯科', a: ['moscow'] }, { n: '纽约', a: ['newyork', 'nyc'] },
    { n: '洛杉矶', a: ['losangeles', 'la'] }, { n: '旧金山', a: ['sanfrancisco', 'sf'] },
    { n: '芝加哥', a: ['chicago'] }, { n: '西雅图', a: ['seattle'] },
    { n: '华盛顿', a: ['washington', 'dc'] }, { n: '多伦多', a: ['toronto'] },
    { n: '温哥华', a: ['vancouver'] }, { n: '悉尼', a: ['sydney'] },
    { n: '墨尔本', a: ['melbourne'] }, { n: '奥克兰', a: ['auckland'] },
    { n: '开普敦', a: ['capetown', 'cape town'] }, { n: '开罗', a: ['cairo'] },
    { n: '内罗毕', a: ['nairobi'] }, { n: '圣保罗', a: ['saopaulo', 'sao paulo'] },
    { n: '里约热内卢', a: ['rio'] },
  ];
  function matchCity(q) {
    q = (q || '').trim().toLowerCase();
    if (!q) return [];
    return CITY_DB.filter((c) =>
      c.n.toLowerCase().includes(q) || c.a.some((x) => x.includes(q))
    ).slice(0, 8).map((c) => c.n);
  }

  // 搜索历史（localStorage，最多 6 条）
  const HIST_KEY = 'xiao6_wx_history';
  function getHistory() {
    try { return JSON.parse(localStorage.getItem(HIST_KEY) || '[]'); } catch { return []; }
  }
  function pushHistory(cityName) {
    let h = getHistory().filter((x) => x !== cityName);
    h.unshift(cityName);
    h = h.slice(0, 6);
    try { localStorage.setItem(HIST_KEY, JSON.stringify(h)); } catch { /* 忽略 */ }
  }
  function escAttr(s) { return String(s).replace(/"/g, '&quot;'); }

  // 候选/历史下拉渲染与键盘交互
  let activeIdx = -1;
  function renderSuggest(items, isHist) {
    const box = $('wxSuggest');
    if (!box) return;
    if (!items.length) { box.hidden = true; return; }
    const head = isHist ? '<div class="wx-suggest-h">最近搜索</div>' : '';
    const rows = items.map((c, i) =>
      `<button type="button" class="wx-suggest-item" data-i="${i}" data-c="${escAttr(c)}">` +
      `<span class="wx-sug-ico">${isHist ? '<svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-clock"/></svg>' : '<svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-pin"/></svg>'}</span><span>${c}</span></button>`).join('');
    box.innerHTML = head + rows;
    box.hidden = false;
    activeIdx = -1;
    box.querySelectorAll('.wx-suggest-item').forEach((b) => {
      b.addEventListener('mousedown', (e) => {
        e.preventDefault();
        applyCity(b.getAttribute('data-c'));
      });
    });
  }
  function showSuggest() {
    const v = ($('wxCityInput').value || '').trim();
    renderSuggest(v ? matchCity(v) : getHistory(), !v);
  }
  function hideSuggest() {
    const box = $('wxSuggest');
    if (box) box.hidden = true;
  }
  function highlightSuggest(items) {
    items.forEach((it, i) => it.classList.toggle('active', i === activeIdx));
  }

  const PANEL_HTML = `
  <div id="weather-panel" class="weather-panel" aria-hidden="true">
    <div class="wx-boot"></div>
    <div class="wx-inner">
      <div class="wx-top">
        <div class="wx-title">
          <span class="wx-glyph">🌤️</span>
          <span>天气观测</span>
          <span class="wx-sub">WEATHER STATION</span>
        </div>
        <div class="wx-actions">
          <div class="wx-mode">
            <button class="wx-mode-btn active" data-mode="compact">近 3 天</button>
            <button class="wx-mode-btn" data-mode="week">未来 7 天</button>
          </div>
          <div class="wx-search">
            <div class="wx-search-wrap">
              <input id="wxCityInput" class="wx-city-input" type="text" placeholder="搜索城市，如 上海 / Tokyo" autocomplete="off" />
              <button id="wxCityGo" class="wx-city-go">查询</button>
              <div id="wxSuggest" class="wx-suggest" hidden></div>
            </div>
          </div>
          <div class="wx-fetch" id="wxFetchedAt">—</div>
          <button class="wx-exit-btn" id="wxExitBtn" title="关闭"><svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-close"/></svg></button>
        </div>
      </div>

      <div class="wx-body">
        <div class="wx-now" id="wxNow">
          <div class="wx-now-city" id="wxCity">定位中…</div>
          <div class="wx-now-main">
            <div class="wx-now-icon" id="wxIcon">🌡️</div>
            <div class="wx-now-temp" id="wxTemp">--<span class="wx-deg">°C</span></div>
            <div class="wx-now-cond" id="wxCond">—</div>
          </div>
          <div class="wx-now-range" id="wxRange">高 --° / 低 --°</div>
          <div class="wx-now-meta" id="wxMeta">
            <span>体感 --°</span><span>湿度 --%</span><span>风 --</span><span>能见度 -- km</span>
            <span id="wxAqi">空气 --</span>
          </div>
          <div class="wx-life" id="wxLife"></div>
        </div>

        <div class="wx-forecast" id="wxForecast">
          <div class="wx-forecast-empty">加载中…</div>
        </div>
      </div>

      <div class="wx-hourly" id="wxHourly">
        <div class="wx-hourly-h">未来 24 小时气温</div>
        <div class="wx-hourly-bars" id="wxHourlyBars"></div>
      </div>

      <div class="wx-foot">
        <span class="wx-foot-dot"></span>
        <span id="wxStatus">天气数据来自 wttr.in · open-meteo（免 key）</span>
      </div>
    </div>
  </div>`;

  function inject() {
    if (panelEl) return;
    const wrap = document.createElement('div');
    wrap.innerHTML = PANEL_HTML;
    document.body.appendChild(wrap.firstElementChild);
    panelEl = $('weather-panel');

    $('wxExitBtn').addEventListener('click', () => setWeatherMode(false));
    $('wxCityGo').addEventListener('click', () => applyCity());
    const cityInput = $('wxCityInput');
    cityInput.addEventListener('input', showSuggest);
    cityInput.addEventListener('focus', showSuggest);
    cityInput.addEventListener('blur', () => setTimeout(hideSuggest, 150));
    cityInput.addEventListener('keydown', (e) => {
      const box = $('wxSuggest');
      const items = box && !box.hidden ? box.querySelectorAll('.wx-suggest-item') : [];
      if (e.key === 'ArrowDown') {
        if (!items.length) return;
        e.preventDefault();
        activeIdx = (activeIdx + 1) % items.length;
        highlightSuggest(items);
      } else if (e.key === 'ArrowUp') {
        if (!items.length) return;
        e.preventDefault();
        activeIdx = (activeIdx - 1 + items.length) % items.length;
        highlightSuggest(items);
      } else if (e.key === 'Enter') {
        if (items.length && activeIdx >= 0) {
          e.preventDefault();
          applyCity(items[activeIdx].getAttribute('data-c'));
        } else {
          applyCity();
        }
      } else if (e.key === 'Escape') {
        hideSuggest();
      }
    });
    panelEl.querySelectorAll('.wx-mode-btn').forEach((b) => {
      b.addEventListener('click', () => {
        const m = b.getAttribute('data-mode');
        if (m === mode) return;
        mode = m;
        panelEl.querySelectorAll('.wx-mode-btn').forEach((x) =>
          x.classList.toggle('active', x.getAttribute('data-mode') === mode));
        refresh(true);
      });
    });
  }

  function applyCity(v) {
    if (v == null) v = ($('wxCityInput').value || '').trim();
    else { try { $('wxCityInput').value = v; } catch { /* 忽略 */ } }
    hideSuggest();
    if (!v) { lastManualCity = null; return; }
    city = v;
    lastManualCity = v; // 标记为主动搜索，便于失败时给出友好提示
    refresh(true);
  }

  function aqiInfo(aqi) {
    if (aqi == null) return { txt: '暂无', cls: '' };
    if (aqi <= 50) return { txt: `优 (AQI ${aqi})`, cls: 'aqi-good' };
    if (aqi <= 100) return { txt: `良 (AQI ${aqi})`, cls: 'aqi-mod' };
    if (aqi <= 150) return { txt: `轻度污染 (AQI ${aqi})`, cls: 'aqi-bad' };
    if (aqi <= 200) return { txt: `中度污染 (AQI ${aqi})`, cls: 'aqi-bad' };
    return { txt: `重度污染 (AQI ${aqi})`, cls: 'aqi-severe' };
  }

  function safeSet(id, val, attr = 'textContent') {
    const node = $(id);
    if (!node) return false;
    node[attr] = val;
    return true;
  }
  function safeHtml(id, html) {
    const node = $(id);
    if (!node) return false;
    node.innerHTML = html;
    return true;
  }

  function renderCard(card) {
    if (!card) return;
    safeSet('wxCity', card.city || '—');
    safeSet('wxIcon', condIcon(card.condition));
    safeHtml('wxTemp', `${card.temp ?? '--'}<span class="wx-deg">°C</span>`);
    safeSet('wxCond', card.condition || '—');
    safeSet('wxRange', `高 ${card.high ?? '--'}° / 低 ${card.low ?? '--'}°`);
    const meta = [];
    meta.push(`体感 ${card.feel ?? '--'}°`);
    meta.push(`湿度 ${card.humidity ?? '--'}%`);
    meta.push(`风 ${card.wind || '--'}`);
    if (card.visibility != null) meta.push(`能见度 ${card.visibility} km`);
    safeHtml('wxMeta', meta.map((m) => `<span>${m}</span>`).join(''));
    // 空气质量
    const a = aqiInfo(card.aqi);
    const aqiEl = $('wxAqi');
    if (aqiEl) {
      aqiEl.textContent = '空气 ' + a.txt;
      aqiEl.className = a.cls;
    }
    // 生活指数
    const life = (card.lifeIndex || []).map((x) =>
      `<span class="wx-life-tag">${x.name} · ${x.val}</span>`).join('');
    safeHtml('wxLife', life || '');
    // 24h 逐小时气温曲线
    renderHourly(card.hourly || []);
  }

  function renderHourly(hourly) {
    const box = $('wxHourlyBars');
    if (!box) return;
    if (!hourly.length) { box.innerHTML = '<div class="wx-hourly-empty">暂无逐小时数据</div>'; return; }
    const temps = hourly.map((h) => h.temp);
    const min = Math.min(...temps), max = Math.max(...temps);
    const span = Math.max(1, max - min);
    box.innerHTML = hourly.map((h) => {
      const hgt = 20 + ((h.temp - min) / span) * 70;
      return `<div class="wx-hb" title="${h.temp}°C">
        <div class="wx-hb-bar" style="height:${hgt}%"></div>
        <div class="wx-hb-t">${h.temp}°</div>
        <div class="wx-hb-time">${h.t}</div>
      </div>`;
    }).join('');
  }

  function renderForecast(list) {
    const box = $('wxForecast');
    if (!list || !list.length) {
      box.innerHTML = '<div class="wx-forecast-empty">暂无预报数据</div>';
      return;
    }
    box.innerHTML = list.map((d) => `
      <div class="wx-fc-card">
        <div class="wx-fc-day">${d.day}</div>
        <div class="wx-fc-icon">${condIcon(d.condition)}</div>
        <div class="wx-fc-cond">${d.condition || '—'}</div>
        <div class="wx-fc-temp"><b>${d.high ?? '--'}°</b> / ${d.low ?? '--'}°</div>
      </div>`).join('');
  }

  function setStatus(text, isErr) {
    const el = $('wxStatus');
    if (el) {
      el.textContent = text;
      el.classList.toggle('err', !!isErr);
    }
  }

  function fmtFetchedAt(ts) {
    if (!ts) return '—';
    return '更新于 ' + ts.replace('T', ' ');
  }

  function getDefaultCity() {
    try {
      const saved = JSON.parse(localStorage.getItem('xiao6_settings_v1') || '{}');
      return (saved.defaultCity || '').trim() || 'Beijing';
    } catch {
      return 'Beijing';
    }
  }

  function getSavedLocation() {
    try {
      const saved = JSON.parse(localStorage.getItem('xiao6_settings_v1') || '{}');
      return {
        city: (saved.defaultCity || '').trim(),
        display: (saved.locationDisplay || '').trim(),
        province: (saved.province || '').trim(),
        district: (saved.district || '').trim(),
      };
    } catch {
      return { city: '', display: '', province: '', district: '' };
    }
  }

  async function locate() {
    // 0) 用户已在设置中指定所在地，最优先使用（解决定位不精准问题）
    const saved = getSavedLocation();
    if (saved.city) {
      return { city: saved.city, display: saved.display || saved.city, source: 'settings' };
    }
    // 1) 浏览器定位
    if (navigator.geolocation) {
      try {
        const pos = await new Promise((resolve, reject) => {
          navigator.geolocation.getCurrentPosition(resolve, reject, {
            enableHighAccuracy: false, timeout: 8000, maximumAge: 10 * 60 * 1000
          });
        });
        return { lat: pos.coords.latitude, lon: pos.coords.longitude, source: 'browser' };
      } catch (_) {}
    }
    // 2) 回退到后端 IP 定位
    try {
      const r = await fetch('/api/geo', { cache: 'no-store' });
      const d = await r.json();
      const loc = d.location || {};
      if (loc.lat != null && loc.lon != null) {
        return { lat: loc.lat, lon: loc.lon, source: 'ip' };
      }
    } catch (_) {}
    // 3) 最终默认城市
    return { city: getDefaultCity(), source: 'default' };
  }

  async function refresh(force) {
    if (!panelEl) return;
    setStatus('正在定位并拉取天气…');
    // 切换模式时立即给出加载反馈，避免“点了没反应”的错觉
    if (mode === 'week') {
      safeHtml('wxForecast', '<div class="wx-forecast-empty">加载未来 7 天预报…</div>');
    } else {
      safeHtml('wxForecast', '<div class="wx-forecast-empty">加载中…</div>');
    }
    try {
      // 首次打开或强制刷新且未手动指定城市时，先定位（结果缓存复用，不重复定位）
      const needLocate = force || !city;
      let geo = null;
      if (needLocate && !city) {
        if (!lastGeo) lastGeo = await locate();
        geo = lastGeo;
        if (geo && geo.city) city = geo.city;
      } else {
        geo = lastGeo;
      }
      let url = '/api/weather?mode=' + encodeURIComponent(mode) +
        (city ? '&city=' + encodeURIComponent(city) : '') +
        (force ? '&refresh=1' : '');
      if (geo && geo.lat != null) {
        url += '&lat=' + encodeURIComponent(geo.lat) + '&lon=' + encodeURIComponent(geo.lon);
      }
      const res = await fetch(url, { cache: 'no-store' });
      const data = await res.json();
      if (!data.ok || !data.card) {
        renderCard(data.card);
        renderForecast(data.forecast || []);
        if (lastManualCity) {
          setStatus(`未找到「${lastManualCity}」的天气，可试试：北京 · 上海 · 广州 · 香港 · Tokyo · London`, true);
          lastManualCity = null;
        } else {
          setStatus(data.error ? ('天气获取失败：' + data.error) : '暂无天气数据', true);
        }
        return;
      }
      renderCard(data.card);
      renderForecast(data.forecast || []);
      if (lastManualCity) { pushHistory(lastManualCity); lastManualCity = null; }
      safeSet('wxFetchedAt', fmtFetchedAt(data.fetchedAt));
      let status = data.stale
        ? '使用缓存数据（实时获取失败）'
        : `天气数据来自 wttr.in · open-meteo（${data.refreshMinutes} 分钟刷新）`;
      if (data.weekLimited) {
        status += ' · 7 天预报源暂不可用，已显示可用天数';
      }
      setStatus(status);
    } catch (e) {
      setStatus('天气请求异常：' + e.message, true);
    }
  }

  function startClock() {
    stopClock();
    // fetchedAt 已在 refresh 后写入，这里仅保持面板活性的轻量占位
    clockTimer = setInterval(() => {}, 60 * 1000);
  }
  function stopClock() {
    if (clockTimer) { clearInterval(clockTimer); clockTimer = null; }
  }

  function setWeatherMode(on) {
    open = on;
    inject();
    if (on) {
      document.body.classList.add('weather-mode');
      panelEl.classList.add('wx-booting');
      panelEl.setAttribute('aria-hidden', 'false');
      // 触发启动故障闪动动画
      if (bootTimer) clearTimeout(bootTimer);
      bootTimer = setTimeout(() => panelEl.classList.remove('wx-booting'), 900);
      // 首次打开强制刷新：确保定位与中文城市名立即生效
      refresh(true);
      startClock();
      if (refreshTimer) clearInterval(refreshTimer);
      refreshTimer = setInterval(() => refresh(false), REFRESH_MS);
    } else {
      document.body.classList.remove('weather-mode');
      panelEl.setAttribute('aria-hidden', 'true');
      stopClock();
      if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null; }
    }
  }

  function initWeather() {
    inject();
    const btn = $('wxOpenBtn');
    if (btn) btn.addEventListener('click', () => setWeatherMode(!open));
    // 侧栏快捷能力：点击「现在几点了？」之类的无关，这里仅绑定按钮
  }

  // 自启动
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initWeather);
  } else {
    initWeather();
  }

  return { initWeather, setWeatherMode, toggle: () => setWeatherMode(!open) };
})();

if (typeof window !== 'undefined') window.WX = WX;
