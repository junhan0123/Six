// memory-center.js —— 记忆中心（Phase 36.1 · Task 1）
// 产品化既有记忆能力：让用户理解「小6记住了什么 / 怎么来的 / 可信度如何」。
// 纪律：只读展示 + archive 软删 + 叠加式纠正（/api/notes）；绝不改写 Memory V2 核心 / Runtime / Planner / Executor / EventBus。
// 复用 OverlayManager 统一浮层栈；body.memc-mode 表现类；window.ZZMemoryCenter 暴露入口。

const MEMC = { panel: null, open: false, memories: [], truth: null, corrections: [], keyword: '' };

function memcEscapeHtml(str) {
  return String(str == null ? '' : str).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

function memcFmtTime(ts) {
  if (!ts) return '—';
  const n = Number(ts);
  if (!isNaN(n) && String(ts).length <= 12) {
    const d = new Date(String(ts).length <= 10 ? n * 1000 : n);
    if (!isNaN(d.getTime())) return memcFmt(d);
  }
  const d = new Date(String(ts).replace(' ', 'T'));
  if (!isNaN(d.getTime())) return memcFmt(d);
  return String(ts);
}
function memcFmt(d) {
  const p = (x) => String(x).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

// 容错解析 tags：可能是 JSON 数组串 / JSON 对象串 / 逗号串 / 数组
function memcParseTags(raw) {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw.map(String).filter(Boolean);
  if (typeof raw === 'string') {
    const s = raw.trim();
    if (!s) return [];
    if (s[0] === '[') { try { const a = JSON.parse(s); if (Array.isArray(a)) return a.map(String); } catch (_) {} }
    if (s[0] === '{') { try { const o = JSON.parse(s); if (o && typeof o === 'object') return Object.keys(o).concat(Object.values(o).map(String)); } catch (_) {} }
    return s.split(',').map((x) => x.trim()).filter(Boolean);
  }
  return [];
}

// 三态可信度：⚪系统（权威来源）/ 🟢已确认（有叠加纠正）/ 🟡推断（默认）
function memcBadge(mem) {
  const sysTypes = ['user_input', 'important_date', 'important_dates', 'canonical', 'identity', 'profile'];
  if (sysTypes.indexOf(mem.event_type) >= 0) return { cls: 'sys', label: '系统' };
  if (mem.mem_id && MEMC.corrections.some((n) =>
    (n.aliases && String(n.aliases).indexOf(mem.mem_id) >= 0) ||
    (n.tags && String(n.tags).indexOf(mem.mem_id) >= 0) ||
    (n.markdown && String(n.markdown).indexOf(mem.mem_id) >= 0))) {
    return { cls: 'ok', label: '已确认' };
  }
  return { cls: 'inf', label: '推断' };
}

function memcBuild() {
  if (MEMC.panel) return;
  const html = `
  <div class="memc-panel" id="memc-panel" role="dialog" aria-label="记忆中心">
    <div class="memc-backdrop" data-close="1"></div>
    <div class="memc-stage glass">
      <div class="memc-bar">
        <div class="memc-title"><span class="memc-dot"></span>记忆中心</div>
        <div class="memc-meta" id="memc-meta"></div>
        <button class="memc-refresh" id="memc-refresh" title="刷新">↻</button>
        <button class="memc-close" id="memc-close" title="关闭（Esc）" aria-label="关闭"><svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-close"/></svg></button>
      </div>
      <div class="memc-search-wrap">
        <input class="memc-search" id="memc-search" type="search" placeholder="筛选记忆（标题 / 内容 / 标签 / 来源）…" />
      </div>
      <div class="memc-body" id="memc-body"></div>
    </div>
  </div>`;
  document.body.insertAdjacentHTML('beforeend', html);
  MEMC.panel = document.getElementById('memc-panel');
  document.getElementById('memc-close').addEventListener('click', memcClose);
  MEMC.panel.querySelector('[data-close]').addEventListener('click', memcClose);
  document.getElementById('memc-refresh').addEventListener('click', () => memcLoad());
  const search = document.getElementById('memc-search');
  search.addEventListener('input', () => { MEMC.keyword = search.value.trim().toLowerCase(); memcRender(); });
}

async function memcLoad() {
  const body = document.getElementById('memc-body');
  if (body) body.innerHTML = `<div class="memc-loading">正在读取记忆与真实态…</div>`;
  try {
    const [mr, tr, nr] = await Promise.all([
      fetch('/api/memories', { cache: 'no-store' }).then((r) => r.json()).catch(() => []),
      fetch('/api/memory/truth', { cache: 'no-store' }).then((r) => r.json()).catch(() => null),
      fetch('/api/notes?folder=' + encodeURIComponent('智能反馈'), { cache: 'no-store' }).then((r) => r.json()).catch(() => []),
    ]);
    MEMC.memories = Array.isArray(mr) ? mr : (mr && Array.isArray(mr.memories) ? mr.memories : []);
    MEMC.truth = tr;
    MEMC.corrections = Array.isArray(nr) ? nr : [];
    memcRender();
  } catch (e) {
    if (body) body.innerHTML = `<div class="memc-empty">记忆加载失败：${memcEscapeHtml(String(e && e.message || e))}</div>`;
  }
}

function memcRender() {
  const body = document.getElementById('memc-body');
  if (!body) return;
  const kw = MEMC.keyword;
  const mems = MEMC.memories.filter((m) => {
    if (!kw) return true;
    const tags = memcParseTags(m.tags).join(' ');
    const hay = ((m.title || '') + ' ' + (m.content || '') + ' ' + (m.event_type || '') + ' ' + (m.source_ref || '') + ' ' + tags).toLowerCase();
    return hay.indexOf(kw) >= 0;
  });

  const t = MEMC.truth || {};
  const stats = t.stats || {};
  const bySource = t.by_source || {};
  const meta = document.getElementById('memc-meta');
  if (meta) {
    const parts = [];
    if (stats.scanned != null) parts.push('扫描 ' + stats.scanned);
    if (bySource.inference != null) parts.push('推断 ' + bySource.inference);
    if (bySource.system != null) parts.push('系统 ' + bySource.system);
    if (stats.deprecated != null) parts.push('已弃用 ' + stats.deprecated);
    if (t.feature_memory_truth) parts.push('真实态已开启');
    meta.textContent = parts.join(' · ');
  }

  if (!mems.length) {
    body.innerHTML = `<div class="memc-empty">${kw ? '没有匹配「' + memcEscapeHtml(kw) + '」的记忆' : '暂无记忆数据'}</div>`;
    return;
  }

  const groups = {};
  mems.forEach((m) => { const g = m.event_type || '未分类'; (groups[g] = groups[g] || []).push(m); });
  const groupKeys = Object.keys(groups).sort((a, b) => groups[b].length - groups[a].length);

  let html = `<div class="memc-list-head">${mems.length} 条记忆 · ${groupKeys.length} 类</div>`;
  groupKeys.forEach((g) => {
    html += `<section class="memc-group"><div class="memc-group-title">${memcEscapeHtml(g)} <span class="memc-group-count">${groups[g].length}</span></div>`;
    html += `<div class="memc-grid">${groups[g].map(memcCard).join('')}</div></section>`;
  });
  body.innerHTML = html;
  memcBind(body);
}

function memcCard(m) {
  const b = memcBadge(m);
  const tags = memcParseTags(m.tags);
  const tagHtml = tags.length ? `<div class="memc-tags">${tags.map((t) => `<span class="memc-chip">${memcEscapeHtml(t)}</span>`).join('')}</div>` : '';
  const content = m.content || m.title || '';
  const sal = (m.salience != null) ? `<span class="memc-kv">显著度 <b>${memcEscapeHtml(String(m.salience))}</b></span>` : '';
  const src = m.source_ref ? `<span class="memc-kv">来源 <b>${memcEscapeHtml(String(m.source_ref))}</b></span>` : '';
  const canArchive = !!m.mem_id;
  return `
  <div class="memc-row" data-mem="${memcEscapeHtml(m.mem_id || '')}">
    <div class="memc-row-top">
      <div class="memc-row-title">${memcEscapeHtml(m.title || '(未命名)')}</div>
      <span class="memc-badge ${b.cls}"><span class="dot"></span>${memcEscapeHtml(b.label)}</span>
    </div>
    <div class="memc-content">${memcEscapeHtml(content)}</div>
    ${tagHtml}
    <div class="memc-kvs">${sal}${src}<span class="memc-kv">类型 <b>${memcEscapeHtml(m.event_type || '—')}</b></span></div>
    <div class="memc-actions">
      <button class="memc-archive" data-mem="${memcEscapeHtml(m.mem_id || '')}" ${canArchive ? '' : 'disabled title="该记忆缺少 mem_id，无法归档"'} ${canArchive ? 'title="软删到冷存储（可恢复）"' : ''}>归档</button>
      <button class="memc-correct" data-mem="${memcEscapeHtml(m.mem_id || '')}">纠正</button>
    </div>
    <div class="memc-edit" hidden></div>
  </div>`;
}

function memcBind(root) {
  root.querySelectorAll('.memc-archive').forEach((btn) => {
    btn.addEventListener('click', () => {
      const memId = btn.getAttribute('data-mem');
      if (!memId) return;
      memcArchive(memId, btn);
    });
  });
  root.querySelectorAll('.memc-correct').forEach((btn) => {
    btn.addEventListener('click', () => {
      const memId = btn.getAttribute('data-mem');
      const mem = MEMC.memories.find((x) => x.mem_id === memId) || { mem_id: memId, title: memId };
      memcOpenEdit(btn, mem);
    });
  });
}

function memcOpenEdit(btn, mem) {
  const row = btn.closest('.memc-row');
  if (!row) return;
  const edit = row.querySelector('.memc-edit');
  if (!edit) return;
  if (!edit.hidden) { edit.hidden = true; edit.innerHTML = ''; return; }
  edit.hidden = false;
  edit.innerHTML = `
    <div class="memc-edit-box">
      <textarea class="memc-edit-ta" placeholder="告诉小6这条记忆哪里不对 / 应该是什么（叠加纠正，不修改原记忆）…"></textarea>
      <div class="memc-edit-actions">
        <button class="memc-edit-cancel">取消</button>
        <button class="memc-edit-save">提交纠正</button>
      </div>
    </div>`;
  const ta = edit.querySelector('.memc-edit-ta');
  ta.focus();
  edit.querySelector('.memc-edit-cancel').addEventListener('click', () => { edit.hidden = true; edit.innerHTML = ''; });
  edit.querySelector('.memc-edit-save').addEventListener('click', async () => {
    const text = ta.value.trim();
    if (!text) { ta.focus(); return; }
    const save = edit.querySelector('.memc-edit-save');
    save.disabled = true; save.textContent = '提交中…';
    await memcCorrect(mem, text, save);
  });
}

async function memcArchive(memId, btn) {
  btn.disabled = true; btn.textContent = '归档中…';
  try {
    const r = await fetch('/api/memories/archive', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mem_id: memId, archived: 1 }),
    });
    if (r.status === 404) { btn.textContent = '已不可归档'; memcToast('该记忆不在活跃库中（可能已归档）'); return; }
    const d = await r.json().catch(() => ({}));
    if (d && d.ok) {
      const row = btn.closest('.memc-row'); if (row) row.remove();
      memcToast('已归档（冷存储，可随时恢复）');
    } else {
      btn.disabled = false; btn.textContent = '归档';
      memcToast('归档失败：' + memcEscapeHtml(String(d.error || '未知')));
    }
  } catch (e) {
    btn.disabled = false; btn.textContent = '归档';
    memcToast('请求失败：' + memcEscapeHtml(String(e && e.message || e)));
  }
}

async function memcCorrect(mem, text, saveBtn) {
  const md = '纠正记忆（mem_id=' + (mem.mem_id || '未知') + '，标题：' + (mem.title || '—') + '）：\n\n' + text +
    '\n\n> 由用户在「记忆中心」提交，作为叠加式纠正，不修改原始记忆。';
  try {
    const r = await fetch('/api/notes', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: '记忆纠正 · ' + (mem.title || mem.mem_id || '未知'),
        markdown: md,
        tags: 'mem:' + (mem.mem_id || 'unknown'),
        folder: '智能反馈',
        aliases: mem.mem_id || '',
      }),
    });
    const d = await r.json().catch(() => ({}));
    const edit = saveBtn ? saveBtn.closest('.memc-edit') : null;
    if (d && d.ok) {
      MEMC.corrections.push({ aliases: mem.mem_id || '', tags: 'mem:' + (mem.mem_id || 'unknown'), markdown: md });
      if (edit) { edit.hidden = true; edit.innerHTML = ''; }
      memcToast('已记录纠正（叠加生效，原记忆不变）');
      memcRender();
    } else {
      if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = '提交纠正'; }
      memcToast('纠正提交失败：' + memcEscapeHtml(String(d.error || '未知')));
    }
  } catch (e) {
    if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = '提交纠正'; }
    memcToast('请求失败：' + memcEscapeHtml(String(e && e.message || e)));
  }
}

function memcToast(msg) {
  let el = document.getElementById('memc-toast');
  if (!el) {
    el = document.createElement('div');
    el.id = 'memc-toast';
    el.className = 'memc-toast';
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove('show'), 2600);
}

function memcOpen() {
  memcBuild();
  memcLoad();
  requestAnimationFrame(() => document.body.classList.add('memc-mode'));
  MEMC.open = true;
  window.dispatchEvent(new CustomEvent('xiao6:memc-mode', { detail: { active: true } }));
  if (window.OverlayManager) {
    const type = (window.OverlayManager.OverlayType) ? window.OverlayManager.OverlayType.PANEL : 'panel';
    window.OverlayManager.track('memory-center', { el: MEMC.panel, onClose: memcCloseImpl, type: type, trap: false });
  }
}
function memcCloseImpl() {
  document.body.classList.remove('memc-mode');
  MEMC.open = false;
  window.dispatchEvent(new CustomEvent('xiao6:memc-mode', { detail: { active: false } }));
}
function memcClose() {
  if (window.OverlayManager && window.OverlayManager.isOpen && window.OverlayManager.isOpen('memory-center')) window.OverlayManager.close('memory-center');
  else memcCloseImpl();
}

window.ZZMemoryCenter = { open: memcOpen, close: memcClose };
