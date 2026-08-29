// aboutme-panel.js —— 关于我（Phase 36.1 · Task 2）
// 融合 /api/user_model + /api/personal_context，呈现小6对你的「画像」：身份 / 项目 / 偏好 / 工作风格 / 沟通风格。
// 每条显示来源 + 更新时间 + 可信度；提供叠加式「反馈」入口（/api/notes，folder=智能反馈）。
// 纪律：只读用户模型 + 个性化上下文；纠正走 append-only notes；绝不读取 / 修改 Memory V2 核心。
// 复用 OverlayManager 统一浮层栈；body.aboutme-mode 表现类；window.ZZAboutMe 暴露入口。

const ABT = { panel: null, open: false, model: null, pctx: null, corrections: [] };

function abtEscapeHtml(str) {
  return String(str == null ? '' : str).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}
function abtFmtTime(ts) {
  if (!ts) return '—';
  const n = Number(ts);
  if (!isNaN(n) && String(ts).length <= 12) {
    const d = new Date(String(ts).length <= 10 ? n * 1000 : n);
    if (!isNaN(d.getTime())) return abtFmt(d);
  }
  const d = new Date(String(ts).replace(' ', 'T'));
  if (!isNaN(d.getTime())) return abtFmt(d);
  return String(ts);
}
function abtFmt(d) {
  const p = (x) => String(x).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

// 三态可信度：⚪系统（权威来源）/ 🟢已确认（有叠加反馈）/ 🟡推断（默认）
function abtBadge(field) {
  const sysSources = ['canonical', 'project_state', 'identity', 'system', 'user_input'];
  if (field.source && sysSources.indexOf(field.source) >= 0) return { cls: 'sys', label: '系统' };
  if (ABT.corrections.some((n) =>
    (n.tags && String(n.tags).indexOf('about:' + field._key) >= 0) ||
    (n.aliases && String(n.aliases).indexOf(field._key) >= 0) ||
    (n.markdown && String(n.markdown).indexOf(field._key) >= 0))) {
    return { cls: 'ok', label: '已确认' };
  }
  return { cls: 'inf', label: '推断' };
}

function abtBuild() {
  if (ABT.panel) return;
  const html = `
  <div class="about-panel" id="about-panel" role="dialog" aria-label="关于我">
    <div class="about-backdrop" data-close="1"></div>
    <div class="about-stage glass">
      <div class="about-bar">
        <div class="about-title"><span class="about-dot"></span>关于我</div>
        <div class="about-meta" id="about-meta"></div>
        <button class="about-refresh" id="about-refresh" title="刷新">↻</button>
        <button class="about-close" id="about-close" title="关闭（Esc）" aria-label="关闭"><svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-close"/></svg></button>
      </div>
      <div class="about-banner">这些画像由对话推断生成。你随时可以「反馈 / 纠正」某一条，或要求小6遗忘；小6不会把你的偏好用于任何超出本会话的用途。</div>
      <div class="about-body" id="about-body"></div>
    </div>
  </div>`;
  document.body.insertAdjacentHTML('beforeend', html);
  ABT.panel = document.getElementById('about-panel');
  document.getElementById('about-close').addEventListener('click', abtClose);
  ABT.panel.querySelector('[data-close]').addEventListener('click', abtClose);
  document.getElementById('about-refresh').addEventListener('click', () => abtLoad());
}

async function abtLoad() {
  const body = document.getElementById('about-body');
  if (body) body.innerHTML = `<div class="about-loading">正在读取用户画像…</div>`;
  try {
    const [ur, pr, nr] = await Promise.all([
      fetch('/api/user_model', { cache: 'no-store' }).then((r) => r.json()).catch(() => null),
      fetch('/api/personal_context', { cache: 'no-store' }).then((r) => r.json()).catch(() => null),
      fetch('/api/notes?folder=' + encodeURIComponent('智能反馈'), { cache: 'no-store' }).then((r) => r.json()).catch(() => []),
    ]);
    ABT.model = (ur && ur.model) ? ur.model : {};
    ABT.pctx = pr || {};
    ABT.corrections = Array.isArray(nr) ? nr : [];
    abtRender();
  } catch (e) {
    if (body) body.innerHTML = `<div class="about-empty">画像加载失败：${abtEscapeHtml(String(e && e.message || e))}</div>`;
  }
}

function abtRow(key, label, value, source, updated, confidence) {
  const field = { _key: key, source: source };
  const b = abtBadge(field);
  const conf = (confidence != null && confidence !== '') ? `<span class="abt-kv">可信度 <b>${abtEscapeHtml(String(confidence))}</b></span>` : '';
  const upd = updated ? `<span class="abt-kv">更新 <b>${abtEscapeHtml(abtFmtTime(updated))}</b></span>` : '';
  const src = source ? `<span class="abt-kv">来源 <b>${abtEscapeHtml(String(source))}</b></span>` : '';
  const val = (value == null || value === '') ? '（未设定）' : String(value);
  return `
  <div class="abt-row" data-key="${abtEscapeHtml(key)}">
    <div class="abt-row-top">
      <div class="abt-row-label">${abtEscapeHtml(label)}</div>
      <span class="memc-badge ${b.cls}"><span class="dot"></span>${abtEscapeHtml(b.label)}</span>
    </div>
    <div class="abt-row-val">${abtEscapeHtml(val)}</div>
    <div class="abt-kvs">${src}${upd}${conf}</div>
    <div class="abt-actions"><button class="abt-fb" data-key="${abtEscapeHtml(key)}">反馈 / 纠正</button></div>
    <div class="abt-edit" hidden></div>
  </div>`;
}

function abtObjRows(prefix, obj, source, labelMap) {
  if (!obj || typeof obj !== 'object') return [];
  return Object.keys(obj).filter((k) => obj[k] != null && obj[k] !== '').map((k) => {
    let v = obj[k];
    if (typeof v === 'object') v = JSON.stringify(v);
    const label = (labelMap && labelMap[k]) ? labelMap[k] : k;
    return abtRow(prefix + '.' + k, label, String(v), source, null, null);
  });
}

function abtRender() {
  const body = document.getElementById('about-body');
  if (!body) return;
  const um = ABT.model || {};
  const pctx = ABT.pctx || {};
  const id = um.identity || {};
  const pId = pctx.identity || {};

  const meta = document.getElementById('about-meta');
  if (meta) {
    const parts = [];
    if (um.canonical_project) parts.push('主项目 ' + um.canonical_project);
    if (um.canonical_confidence != null) parts.push('置信 ' + um.canonical_confidence);
    if (pctx.identity && pctx.identity.name) parts.push('称呼 ' + pctx.identity.name);
    meta.textContent = parts.join(' · ') || '画像';
  }

  let html = '';

  // —— 身份 ——
  html += `<div class="about-section-title">身份</div><div class="about-grid">`;
  const idRows = [];
  if (id.name) idRows.push(abtRow('identity.name', '称呼', id.name, 'canonical'));
  if (id.role || pId.role) idRows.push(abtRow('identity.role', '角色', id.role || pId.role, 'canonical'));
  if (id.org) idRows.push(abtRow('identity.org', '组织', id.org, 'canonical'));
  if (pId.prefs && pId.prefs.length) {
    pId.prefs.forEach((p, i) => idRows.push(abtRow('prefs.' + i, '偏好 · 个性化', p, 'inference')));
  }
  html += (idRows.length ? idRows.join('') : abtRow('identity.empty', '身份', '（暂未建模）', 'inference')) + `</div>`;

  // —— 项目 ——
  const projects = Array.isArray(um.projects) ? um.projects : [];
  html += `<div class="about-section-title">项目（${projects.length}）</div><div class="about-grid">`;
  if (projects.length) {
    html += projects.map((p, i) => abtRow('projects.' + i, p.name || ('项目 ' + (i + 1)),
      '正在推进的项目', p.source, p.updated, p.confidence)).join('');
  } else {
    html += abtRow('projects.empty', '项目', '（暂未记录）', 'inference');
  }
  html += `</div>`;

  // —— 偏好 ——
  const prefs = um.preferences || {};
  const prefRows = abtObjRows('preferences', prefs, 'inference', { theme: '主题偏好', tone: '语气', notify: '通知' });
  html += `<div class="about-section-title">偏好</div><div class="about-grid">`;
  html += (prefRows.length ? prefRows.join('') : abtRow('preferences.empty', '偏好', '（暂未显式设定）', 'inference')) + `</div>`;

  // —— 工作风格 ——
  const ws = um.working_style || {};
  const wsRows = abtObjRows('working_style', ws, 'inference');
  html += `<div class="about-section-title">工作风格</div><div class="about-grid">`;
  html += (wsRows.length ? wsRows.join('') : abtRow('working_style.empty', '工作风格', '（暂未建模）', 'inference')) + `</div>`;

  // —— 沟通风格 ——
  const cs = um.communication_style || {};
  const csLabel = { verbosity: '详尽度', formality: '正式度', humor: '幽默感' };
  const csRows = abtObjRows('communication_style', cs, 'inference', csLabel);
  html += `<div class="about-section-title">沟通风格</div><div class="about-grid">`;
  html += (csRows.length ? csRows.join('') : abtRow('communication_style.empty', '沟通风格', '（暂未建模）', 'inference')) + `</div>`;

  // —— 其它（专家领域 / 价值观 / 反馈）—— 仅在有数据时展示
  const extra = [];
  if (Array.isArray(um.expertise) && um.expertise.length) extra.push(abtRow('expertise', '专家领域', um.expertise.join('、'), 'inference'));
  if (Array.isArray(um.values) && um.values.length) extra.push(abtRow('values', '价值观', um.values.join('、'), 'inference'));
  if (Array.isArray(um.feedback) && um.feedback.length) extra.push(abtRow('feedback', '反馈记录', um.feedback.length + ' 条', 'inference'));
  if (extra.length) {
    html += `<div class="about-section-title">其它画像</div><div class="about-grid">${extra.join('')}</div>`;
  }

  body.innerHTML = html;
  abtBind(body);
}

function abtBind(root) {
  root.querySelectorAll('.abt-fb').forEach((btn) => {
    btn.addEventListener('click', () => {
      const key = btn.getAttribute('data-key');
      const label = (btn.closest('.abt-row') || {}).querySelector ? btn.closest('.abt-row').querySelector('.abt-row-label').textContent : key;
      abtOpenEdit(btn, key, label);
    });
  });
}

function abtOpenEdit(btn, key, label) {
  const row = btn.closest('.abt-row');
  if (!row) return;
  const edit = row.querySelector('.abt-edit');
  if (!edit) return;
  if (!edit.hidden) { edit.hidden = true; edit.innerHTML = ''; return; }
  edit.hidden = false;
  edit.innerHTML = `
    <div class="abt-edit-box">
      <textarea class="abt-edit-ta" placeholder="关于「${abtEscapeHtml(label || key)}」，小6理解错了 / 应该是…（叠加反馈，不修改原画像）"></textarea>
      <div class="abt-edit-actions">
        <button class="abt-edit-cancel">取消</button>
        <button class="abt-edit-save">提交反馈</button>
      </div>
    </div>`;
  const ta = edit.querySelector('.abt-edit-ta');
  ta.focus();
  edit.querySelector('.abt-edit-cancel').addEventListener('click', () => { edit.hidden = true; edit.innerHTML = ''; });
  edit.querySelector('.abt-edit-save').addEventListener('click', async () => {
    const text = ta.value.trim();
    if (!text) { ta.focus(); return; }
    const save = edit.querySelector('.abt-edit-save');
    save.disabled = true; save.textContent = '提交中…';
    await abtFeedback(key, label, text, save);
  });
}

async function abtFeedback(key, label, text, saveBtn) {
  const md = '关于「' + (label || key) + '」(' + key + ') 的反馈：\n\n' + text +
    '\n\n> 由用户在「关于我」面板提交，作为叠加式纠正，不修改原始用户模型。';
  try {
    const r = await fetch('/api/notes', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: '用户反馈 · ' + (label || key),
        markdown: md,
        tags: 'about:' + key,
        folder: '智能反馈',
        aliases: key,
      }),
    });
    const d = await r.json().catch(() => ({}));
    const edit = saveBtn ? saveBtn.closest('.abt-edit') : null;
    if (d && d.ok) {
      ABT.corrections.push({ tags: 'about:' + key, aliases: key, markdown: md });
      if (edit) { edit.hidden = true; edit.innerHTML = ''; }
      abtToast('已记录反馈（叠加生效，原画像不变）');
      abtRender();
    } else {
      if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = '提交反馈'; }
      abtToast('反馈提交失败：' + abtEscapeHtml(String(d.error || '未知')));
    }
  } catch (e) {
    if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = '提交反馈'; }
    abtToast('请求失败：' + abtEscapeHtml(String(e && e.message || e)));
  }
}

function abtToast(msg) {
  let el = document.getElementById('about-toast');
  if (!el) {
    el = document.createElement('div');
    el.id = 'about-toast';
    el.className = 'memc-toast';
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove('show'), 2600);
}

function abtOpen() {
  abtBuild();
  abtLoad();
  requestAnimationFrame(() => document.body.classList.add('aboutme-mode'));
  ABT.open = true;
  window.dispatchEvent(new CustomEvent('xiao6:aboutme-mode', { detail: { active: true } }));
  if (window.OverlayManager) {
    const type = (window.OverlayManager.OverlayType) ? window.OverlayManager.OverlayType.PANEL : 'panel';
    window.OverlayManager.track('aboutme', { el: ABT.panel, onClose: abtCloseImpl, type: type, trap: false });
  }
}
function abtCloseImpl() {
  document.body.classList.remove('aboutme-mode');
  ABT.open = false;
  window.dispatchEvent(new CustomEvent('xiao6:aboutme-mode', { detail: { active: false } }));
}
function abtClose() {
  if (window.OverlayManager && window.OverlayManager.isOpen && window.OverlayManager.isOpen('aboutme')) window.OverlayManager.close('aboutme');
  else abtCloseImpl();
}

window.ZZAboutMe = { open: abtOpen, close: abtClose };
