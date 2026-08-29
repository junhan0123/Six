// memory.js — 小6记忆 Vault（Obsidian 风格）
// 参考 Obsidian：Markdown 笔记 + [[双向链接]] + #标签 + 文件夹 + 图谱视图
// 后端：/api/notes（SQLite + Markdown 混合）

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

const panel = $('#memPanel');
const treeEl = $('#memTree');
const tagsEl = $('#memTags');
const mainEl = $('#memMain');
const viewportEl = $('#memViewport');
const tabsEl = $('#memTabs');
const outlineEl = $('#memOutline');
const tocEl = $('#memToc');
const backlinksPanelEl = $('#memBacklinksPanel');
const searchEl = $('#memSearch');
const graphWrap = $('#memGraphWrap');
const graphCanvas = $('#memGraph');
const memMemGraphWrap = $('#memMemGraphWrap');
const memMemGraph = $('#memMemGraph');

function freshState() {
  return {
    folder: null, tag: null, q: '',
    tabs: [], activeId: null, treeOpen: {},
    sideCollapsed: false, outlineCollapsed: false,
    allNotes: null, dirty: {},
    graph: null, archiveView: false
  };
}
let state = freshState();

/* ---------------- API ---------------- */
async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error(path + ' -> ' + r.status);
  return r.json();
}
const esc = (s) => String(s == null ? '' : s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

/* ---------------- 记忆归档（Hermes 冷存储生命周期） ---------------- */
// 归档：仅切换 mem_id 对应记忆的 archived 状态，数据不删，可随时恢复。
async function archiveMemory(mem_id) {
  try {
    return await api('/api/memories/archive', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mem_id, archived: 1 })
    });
  } catch (e) { toast('归档失败：' + e.message); return null; }
}
async function restoreMemory(mem_id) {
  try {
    return await api('/api/memories/archive', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mem_id, archived: 0 })
    });
  } catch (e) { toast('恢复失败：' + e.message); return null; }
}

/* ---------------- Markdown 轻量渲染 ---------------- */
function renderMarkdown(md) {
  const lines = (md || '').split('\n');
  let html = '', inList = false, inQuote = false;
  const closeList = () => { if (inList) { html += '</ul>'; inList = false; } };
  const closeQuote = () => { if (inQuote) { html += '</blockquote>'; inQuote = false; } };

  const inline = (t) => esc(t)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\[\[([^\]|]+)(?:\|[^\]]+)?\]\]/g,
      (m, name) => `<span class="mem-link" data-title="${esc(name.trim())}">${esc(name.trim())}</span>`)
    .replace(/(^|[\s(])(#[\u4e00-\u9fa5A-Za-z0-9_\-]+)/g,
      (m, pre, tag) => `${pre}<span class="mem-tag" data-tag="${esc(tag.slice(1))}">${esc(tag)}</span>`);

  for (const raw of lines) {
    const line = raw.trimEnd();
    if (!line.trim()) { closeList(); closeQuote(); continue; }
    let m;
    if ((m = line.match(/^(#{1,4})\s+(.*)$/))) {
      closeList(); closeQuote();
      const lv = m[1].length;
      html += `<h${lv} class="md-h">${inline(m[2])}</h${lv}>`;
    } else if (line.startsWith('>')) {
      closeList();
      if (!inQuote) { html += '<blockquote class="md-quote">'; inQuote = true; }
      html += inline(line.slice(1).trim()) + '<br>';
    } else if ((m = line.match(/^[-*]\s+(.*)$/))) {
      closeQuote();
      if (!inList) { html += '<ul class="md-ul">'; inList = true; }
      html += `<li>${inline(m[1])}</li>`;
    } else {
      closeList(); closeQuote();
      html += `<p class="md-p">${inline(line)}</p>`;
    }
  }
  closeList(); closeQuote();
  return html;
}

/* ---------------- 列表 / 导航（Obsidian 式文件树） ---------------- */
function buildTree(notes) {
  const root = { name: '', folders: {}, notes: [] };
  for (const n of notes) {
    const parts = (n.folder || '收件箱').split('/').map(s => s.trim()).filter(Boolean);
    let node = root;
    for (const p of parts) {
      if (!node.folders[p]) node.folders[p] = { name: p, folders: {}, notes: [] };
      node = node.folders[p];
    }
    node.notes.push(n);
  }
  return root;
}
function countNotes(node) {
  let c = node.notes.length;
  for (const k in node.folders) c += countNotes(node.folders[k]);
  return c;
}
function renderTreeNode(node, depth, path) {
  let html = '';
  const names = Object.keys(node.folders).sort();
  for (const fname of names) {
    const f = node.folders[fname];
    const fpath = path ? path + '/' + fname : fname;
    const open = state.treeOpen[fpath] !== false; // 默认展开
    const cnt = countNotes(f);
    html += '<div class="mem-tree-node">'
      + '<div class="mem-tree-row folder" data-folder="' + esc(fpath) + '">'
      + '<span class="mem-tree-twist ' + (open ? 'open' : '') + '"><svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-play"/></svg></span>'
      + '<span class="mem-tree-ico"><svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-folder"/></svg></span>'
      + '<span class="mem-tree-name">' + esc(fname) + '</span>'
      + '<span class="mem-tree-count">' + cnt + '</span>'
      + '</div>'
      + '<div class="mem-tree-children" ' + (open ? '' : 'style="display:none"') + '>'
      + renderTreeNode(f, depth + 1, fpath)
      + '</div></div>';
  }
  for (const n of node.notes) {
    const on = n.id === state.activeId;
    html += '<div class="mem-tree-row note ' + (on ? 'on' : '') + '" data-id="' + n.id + '">'
      + '<span class="mem-tree-twist"></span>'
      + '<span class="mem-tree-ico"><svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-file"/></svg></span>'
      + '<span class="mem-tree-name">' + esc(n.title || '未命名') + '</span>'
      + '</div>';
  }
  return html;
}
function renderTree() {
  const notes = state.allNotes || [];
  treeEl.innerHTML = notes.length
    ? renderTreeNode(buildTree(notes), 0, '')
    : '<div class="mem-sub">暂无笔记，点击「＋ 新建」记录第一条。</div>';
  $$('.mem-tree-row.folder', treeEl).forEach(el => el.onclick = () => {
    const fp = el.dataset.folder;
    state.treeOpen[fp] = (state.treeOpen[fp] !== false) ? false : true; // 切换
    renderTree();
  });
  $$('.mem-tree-row.note', treeEl).forEach(el => el.onclick = () => openNote(+el.dataset.id));
  if (state.activeId) $$('.mem-tree-row.note', treeEl).forEach(el => el.classList.toggle('on', +el.dataset.id === state.activeId));
}
function renderTags(tags) {
  tagsEl.innerHTML = tags.length
    ? tags.map(t => '<span class="mem-chip ' + (state.tag === t.tag ? 'on' : '') + '" data-tag="' + esc(t.tag) + '">#' + esc(t.tag) + '<i>' + t.count + '</i></span>').join('')
    : '<div class="mem-sub">暂无标签，在笔记中使用 #标签 即可自动生成。</div>';
  $$('.mem-chip', tagsEl).forEach(el => el.onclick = () => {
    state.tag = (state.tag === el.dataset.tag) ? null : el.dataset.tag;
    state.folder = null; refresh();
  });
}

async function loadNav() {
  let notes = [], err = '';
  try { notes = await api('/api/notes?limit=500'); }
  catch (e) { err = e.message; }
  state.allNotes = notes;
  renderTree();
  // 标签云
  let tags = [];
  try { tags = await api('/api/notes/tags'); } catch (_) {}
  renderTags(tags);
  if (err) treeEl.innerHTML = '<div class="mem-sub">加载失败：' + esc(err) + '</div>';
}

async function refresh() {
  let notes;
  try {
    if (state.q) notes = await api('/api/notes/search?q=' + encodeURIComponent(state.q));
    else notes = await api('/api/notes' + (state.folder ? '?folder=' + encodeURIComponent(state.folder) : '') + (state.tag ? (state.folder ? '&' : '?') + 'tag=' + encodeURIComponent(state.tag) : ''));
    state.allNotes = notes;
    renderTree();
  } catch (e) {
    treeEl.innerHTML = '<div class="mem-sub">笔记加载失败：' + esc(e.message) + '</div>';
  }
  // 标签
  try { const tags = await api('/api/notes/tags'); renderTags(tags); } catch (_) {}
}

/* ---------------- 多标签 / 双模式 / 大纲反链 ---------------- */
function bindLinks(root) {
  $$('.mem-link', root).forEach(el => el.onclick = () => jumpToTitle(el.dataset.title));
  $$('.mem-tag', root).forEach(el => el.onclick = () => { state.tag = el.dataset.tag; state.folder = null; refresh(); });
}
function renderTabs() {
  tabsEl.innerHTML = state.tabs.map(id => {
    const n = (state.allNotes || []).find(x => x.id === id);
    const title = n ? (n.title || '未命名') : ('#' + id);
    return '<div class="mem-tab ' + (id === state.activeId ? 'on' : '') + '" data-id="' + id + '">'
      + '<span class="mem-tab-name">' + esc(title) + '</span>'
      + (state.dirty[id] ? '<span class="mem-tab-unsaved"></span>' : '')
      + '<span class="mem-tab-close" data-id="' + id + '" title="关闭">×</span>'
      + '</div>';
  }).join('');
  $$('.mem-tab', tabsEl).forEach(el => el.onclick = (e) => {
    if (e.target.classList.contains('mem-tab-close')) { closeTab(+el.dataset.id); return; }
    switchTab(+el.dataset.id);
  });
}
function switchTab(id) {
  if (id === state.activeId) return;
  state.activeId = id;
  renderTabs();
  openNote(id);
}
async function closeTab(id) {
  state.tabs = state.tabs.filter(t => t !== id);
  state.dirty[id] = false;
  if (state.activeId === id) state.activeId = state.tabs[state.tabs.length - 1] || null;
  renderTabs();
  if (state.activeId) openNote(state.activeId);
  else viewportEl.innerHTML = '<div class="mem-empty">从左侧文件树选择一条笔记，或点击「＋ 新建」。</div>';
}

async function openNote(id) {
  state.activeId = id;
  if (!state.tabs.includes(id)) state.tabs.push(id);
  state.dirty[id] = false;
  const n = await api('/api/notes/' + id);
  if (!n) { viewportEl.innerHTML = '<div class="mem-empty">笔记不存在或已删除。</div>'; renderTabs(); return; }
  renderTabs();
  renderNote(n);
  $$('.mem-tree-row.note', treeEl).forEach(el => el.classList.toggle('on', +el.dataset.id === id));
  renderOutline(n);
}
function renderNote(n) {
  viewportEl.innerHTML =
    '<div class="mem-note-head">'
      + '<input class="mem-note-title" id="memNoteTitle" value="' + esc(n.title || '') + '" />'
      + '<input class="mem-note-folder" id="memNoteFolder" value="' + esc(n.folder || '收件箱') + '" placeholder="文件夹" />'
      + '<div class="mem-btn-group">'
        + '<button class="mem-btn" id="memModeBtn">编辑</button>'
        + '<button class="mem-btn mem-danger" id="memDel">删除</button>'
      + '</div>'
    + '</div>'
    + '<div class="mem-note-body" id="memView">' + renderMarkdown(n.markdown) + '</div>'
    + '<textarea class="mem-note-edit" id="memEdit" hidden>' + esc(n.markdown || '') + '</textarea>'
    + '<div class="mem-note-meta" id="memMeta">更新于 ' + esc(n.ts || '') + '　·　文件夹 ' + esc(n.folder || '收件箱') + '</div>';
  bindLinks(viewportEl);
  $('#memModeBtn').onclick = () => toggleMode(n);
  $('#memNoteTitle').oninput = () => markDirty(n);
  $('#memNoteFolder').oninput = () => markDirty(n);
  $('#memEdit').oninput = () => markDirty(n);
  $('#memDel').onclick = async () => {
    if (!confirm('确定删除这条笔记？')) return;
    await api('/api/notes/delete', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id }) });
    state.tabs = state.tabs.filter(t => t !== id);
    state.dirty[id] = false;
    state.activeId = state.tabs[state.tabs.length - 1] || null;
    renderTabs();
    refresh();
    if (state.activeId) openNote(state.activeId);
    else viewportEl.innerHTML = '<div class="mem-empty">已删除。</div>';
  };
}
function toggleMode(n) {
  const ed = $('#memEdit'), view = $('#memView'), btn = $('#memModeBtn');
  if (ed.hidden) { ed.value = n.markdown || ''; ed.hidden = false; view.hidden = true; btn.textContent = '预览'; }
  else {
    n.markdown = ed.value;
    view.hidden = false; view.innerHTML = renderMarkdown(ed.value); ed.hidden = true; btn.textContent = '编辑';
    bindLinks(view);
    saveNote(n, false);
  }
}
function markDirty(n) {
  state.dirty[n.id] = true; renderTabs();
  clearTimeout(n._saveT);
  n._saveT = setTimeout(() => saveNote(n, true), 800);
}
async function saveNote(n, toastIt) {
  const titleEl = $('#memNoteTitle'), folderEl = $('#memNoteFolder'), ed = $('#memEdit');
  if (!titleEl) return;
  const payload = { id: n.id, title: titleEl.value, folder: folderEl.value, markdown: ed.hidden ? n.markdown : ed.value };
  try {
    await api('/api/notes/update', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    state.dirty[n.id] = false; renderTabs();
    if (toastIt) toast('已保存');
    refresh();
  } catch (e) { toast('保存失败：' + e.message); }
}
async function renderOutline(n) {
  const lines = (n.markdown || '').split('\n');
  const toc = [];
  for (const raw of lines) {
    const m = raw.trim().match(/^(#{1,4})\s+(.*)$/);
    if (m) toc.push({ lv: m[1].length, text: m[2].replace(/\*\*/g, '').trim() });
  }
  tocEl.innerHTML = toc.length
    ? toc.map(t => '<a class="lvl-' + t.lv + '" data-text="' + esc(t.text) + '">' + esc(t.text) + '</a>').join('')
    : '<div class="mem-sub">无标题，正文将整体显示。</div>';
  $$('.mem-toc a', tocEl).forEach(el => el.onclick = () => {
    const h = Array.from(viewportEl.querySelectorAll('.md-h')).find(x => x.textContent.trim() === el.dataset.text);
    if (h) h.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
  try {
    const bl = await api('/api/notes/backlinks?title=' + encodeURIComponent(n.title || ''));
    backlinksPanelEl.innerHTML = bl.length
      ? bl.map(b => '<div class="mem-backlink" data-id="' + b.id + '">' + esc(b.title) + '<span class="bl-meta">' + esc(b.folder || '') + '</span></div>').join('')
      : '<div class="mem-sub">无反向链接。</div>';
    $$('.mem-backlink', backlinksPanelEl).forEach(el => el.onclick = () => openNote(+el.dataset.id));
  } catch (_) {}
}

async function jumpToTitle(title) {
  if (!title) return;
  const notes = await api('/api/notes?limit=500');
  const hit = notes.find(n => (n.title || '') === title);
  if (hit) openNote(hit.id);
  else if (confirm(`未找到「${title}」，要新建这条笔记吗？`)) {
    const id = await api('/api/notes', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title, markdown: `[[${title}]]`, folder: '收件箱' }) });
    if (id && id.id) openNote(id.id);
  }
}

async function newNote() {
  const title = (prompt('新笔记标题：') || '').trim();
  if (!title) return;
  const r = await api('/api/notes', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, markdown: `# ${title}\n\n`, folder: '收件箱', tags: '' })
  });
  if (r && r.id) { state.folder = null; state.tag = null; refresh(); openNote(r.id); }
}

/* ---------------- 图谱视图（canvas 力导向） ---------------- */
let graphAnim = null;
async function showGraph() {
  const data = await api('/api/notes/graph');
  if (!data.nodes.length) { toast('暂无可绘制的笔记（需要带正文的笔记）'); return; }
  graphWrap.hidden = false; panel.classList.add('graph-on');
  const cv = graphCanvas, ctx = cv.getContext('2d');
  const W = cv.width = graphWrap.clientWidth, H = cv.height = graphWrap.clientHeight;
  const nodes = data.nodes.map(n => ({ ...n, x: Math.random() * W, y: Math.random() * H, vx: 0, vy: 0 }));
  const idMap = {}; nodes.forEach(n => idMap[n.id] = n);
  const edges = data.edges.filter(e => idMap[e.source] && idMap[e.target]).map(e => ({ s: idMap[e.source], t: idMap[e.target] }));
  const colorOf = (f) => ({ '每日笔记': '#22D3EE', '人物': '#A78BFA', '演示': '#F5B544' }[f] || '#2DD4BF');
  let drag = null;
  cv.onmousedown = (ev) => {
    const r = cv.getBoundingClientRect(), mx = ev.clientX - r.left, my = ev.clientY - r.top;
    drag = nodes.find(n => Math.hypot(n.x - mx, n.y - my) < 16) || null;
    if (drag) cv.style.cursor = 'pointer';
  };
  cv.onmouseup = (ev) => {
    if (drag) { const r = cv.getBoundingClientRect(), mx = ev.clientX - r.left, my = ev.clientY - r.top;
      if (Math.hypot(drag.x - mx, drag.y - my) < 8) openNote(drag.id); }
    drag = null; cv.style.cursor = 'default';
  };
  cv.onmousemove = (ev) => {
    if (!drag) return;
    const r = cv.getBoundingClientRect(); drag.x = ev.clientX - r.left; drag.y = ev.clientY - r.top;
  };
  function step() {
    for (const n of nodes) {
      let fx = (W / 2 - n.x) * 0.002, fy = (H / 2 - n.y) * 0.002;
      for (const m of nodes) {
        if (m === n) continue;
        const dx = n.x - m.x, dy = n.y - m.y, d2 = dx * dx + dy * dy + 0.01;
        const f = 1400 / d2; fx += dx * f; fy += dy * f;
      }
      n.vx = (n.vx + fx) * 0.85; n.vy = (n.vy + fy) * 0.85;
    }
    for (const e of edges) {
      const dx = e.t.x - e.s.x, dy = e.t.y - e.s.y, d = Math.sqrt(dx * dx + dy * dy) + 0.01;
      const f = (d - 90) * 0.01; e.s.vx += dx / d * f; e.s.vy += dy / d * f;
      e.t.vx -= dx / d * f; e.t.vy -= dy / d * f;
    }
    for (const n of nodes) {
      if (n === drag) continue;
      n.x += Math.max(-12, Math.min(12, n.vx)); n.y += Math.max(-12, Math.min(12, n.vy));
      n.x = Math.max(20, Math.min(W - 20, n.x)); n.y = Math.max(20, Math.min(H - 20, n.y));
    }
    ctx.clearRect(0, 0, W, H);
    ctx.strokeStyle = 'rgba(45,212,191,.25)'; ctx.lineWidth = 1;
    for (const e of edges) { ctx.beginPath(); ctx.moveTo(e.s.x, e.s.y); ctx.lineTo(e.t.x, e.t.y); ctx.stroke(); }
    for (const n of nodes) {
      ctx.beginPath(); ctx.arc(n.x, n.y, 6 + Math.min(8, n.val), 0, Math.PI * 2);
      ctx.fillStyle = colorOf(n.folder); ctx.globalAlpha = 0.85; ctx.fill(); ctx.globalAlpha = 1;
      ctx.fillStyle = '#E6EDF3'; ctx.font = '11px Rajdhani, sans-serif'; ctx.textAlign = 'center';
      ctx.fillText((n.title || '').slice(0, 10), n.x, n.y + 20);
    }
    graphAnim = requestAnimationFrame(step);
  }
  cancelAnimationFrame(graphAnim); step();
}

/* ---------------- 记忆图谱（渲染 /api/memories/graph，参考参考实现记忆节点图） ---------------- */
let memGraphAnim = null;
const TYPE_COLORS = { person: '#A78BFA', knowledge: '#2DD4BF', fact: '#22D3EE', self_constraint: '#F5B544', event: '#F472B6' };
async function showMemGraph() {
  let g, list;
  try { [g, list] = await Promise.all([api('/api/memories/graph'), api('/api/memories?limit=500')]); }
  catch (e) { toast('记忆图谱加载失败：' + e.message); return; }
  state.archiveView = false; setArchiveBtn();
  const byId = {}; (list || []).forEach(m => { byId[m.mem_id || ('id:' + m.id)] = m; });
  if (!g.nodes.length) { toast('记忆库暂无节点（对话沉淀后自动生成）'); return; }
  memMemGraphWrap.hidden = false; panel.classList.add('graph-on');
  const cv = memMemGraph, ctx = cv.getContext('2d');
  const W = cv.width = memMemGraphWrap.clientWidth, H = cv.height = memMemGraphWrap.clientHeight;
  const nodes = g.nodes.map(n => ({ ...n, x: Math.random() * W, y: Math.random() * H, vx: 0, vy: 0 }));
  const idMap = {}; nodes.forEach(n => idMap[n.id] = n);
  const edges = g.edges.filter(e => idMap[e.source] && idMap[e.target]).map(e => ({ s: idMap[e.source], t: idMap[e.target] }));
  const colorOf = (t) => TYPE_COLORS[t] || '#7dd3fc';
  let drag = null;
  cv.onmousedown = (ev) => {
    const r = cv.getBoundingClientRect(), mx = ev.clientX - r.left, my = ev.clientY - r.top;
    drag = nodes.find(n => Math.hypot(n.x - mx, n.y - my) < 18) || null;
    if (drag) cv.style.cursor = 'pointer';
  };
  cv.onmouseup = (ev) => {
    if (drag) { const r = cv.getBoundingClientRect(), mx = ev.clientX - r.left, my = ev.clientY - r.top;
      if (Math.hypot(drag.x - mx, drag.y - my) < 8) showMemDetail(drag, byId); }
    drag = null; cv.style.cursor = 'default';
  };
  cv.onmousemove = (ev) => { if (!drag) return; const r = cv.getBoundingClientRect(); drag.x = ev.clientX - r.left; drag.y = ev.clientY - r.top; };
  function step() {
    for (const n of nodes) {
      let fx = (W / 2 - n.x) * 0.002, fy = (H / 2 - n.y) * 0.002;
      for (const m of nodes) {
        if (m === n) continue;
        const dx = n.x - m.x, dy = n.y - m.y, d2 = dx * dx + dy * dy + 0.01;
        const f = 1400 / d2; fx += dx * f; fy += dy * f;
      }
      n.vx = (n.vx + fx) * 0.85; n.vy = (n.vy + fy) * 0.85;
    }
    for (const e of edges) {
      const dx = e.t.x - e.s.x, dy = e.t.y - e.s.y, d = Math.sqrt(dx * dx + dy * dy) + 0.01;
      const f = (d - 90) * 0.01; e.s.vx += dx / d * f; e.s.vy += dy / d * f; e.t.vx -= dx / d * f; e.t.vy -= dy / d * f;
    }
    for (const n of nodes) {
      if (n === drag) continue;
      n.x += Math.max(-12, Math.min(12, n.vx)); n.y += Math.max(-12, Math.min(12, n.vy));
      n.x = Math.max(20, Math.min(W - 20, n.x)); n.y = Math.max(20, Math.min(H - 20, n.y));
    }
    ctx.clearRect(0, 0, W, H);
    ctx.strokeStyle = 'rgba(167,139,250,.22)'; ctx.lineWidth = 1;
    for (const e of edges) { ctx.beginPath(); ctx.moveTo(e.s.x, e.s.y); ctx.lineTo(e.t.x, e.t.y); ctx.stroke(); }
    for (const n of nodes) {
      const rad = 6 + Math.min(11, (n.salience || 0) * 2);
      ctx.beginPath(); ctx.arc(n.x, n.y, rad, 0, Math.PI * 2);
      ctx.fillStyle = colorOf(n.type); ctx.globalAlpha = 0.85; ctx.fill(); ctx.globalAlpha = 1;
      ctx.fillStyle = '#E6EDF3'; ctx.font = '11px Rajdhani, sans-serif'; ctx.textAlign = 'center';
      ctx.fillText((n.label || '').slice(0, 10), n.x, n.y + rad + 14);
    }
    memGraphAnim = requestAnimationFrame(step);
  }
  cancelAnimationFrame(memGraphAnim); step();
}
function showMemDetail(n, byId) {
  const m = byId[n.id] || {};
  state.tabs = []; renderTabs();
  viewportEl.innerHTML =
    '<div class="mem-note-head"><div class="mem-note-title">' + esc(n.label) + '</div>' +
      '<button class="mem-btn mem-archive" data-mem="' + esc(n.id) + '"><svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-box"/></svg> 归档</button></div>' +
    '<div class="mem-note-body">' +
      '<p class="md-p"><b>类型</b>：' + esc(n.type || '-') + '　<b>显著性</b>：' + esc(String(n.salience)) + '</p>' +
      (m.content ? '<p class="md-p">' + esc(m.content).slice(0, 2000) + '</p>' : '<p class="md-sub">无更多详情</p>') +
    '</div>';
  $('.mem-archive', viewportEl).onclick = async () => {
    const r = await archiveMemory(n.id);
    if (r && r.ok) { toast('已归档：' + esc(n.label)); state.archiveView = false; showMemGraph(); }
  };
}

/* ---------------- 人物卡片（参考参考实现，自动从对话抽取） ---------------- */
async function showPersons() {
  let list;
  try { list = await api('/api/memories?type=person'); }
  catch (e) { toast('人物卡片加载失败：' + e.message); return; }
  state.archiveView = false;
  setArchiveBtn();
  memMemGraphWrap.hidden = true; cancelAnimationFrame(memGraphAnim);
  graphWrap.hidden = true; cancelAnimationFrame(graphAnim);
  panel.classList.remove('graph-on');
  state.tabs = []; renderTabs();
  if (!list.length) {
    viewportEl.innerHTML = '<div class="mem-empty">暂无人物卡片。在对话中提到的人（如「我同事小李」）会在当天自动沉淀为画像。</div>';
    return;
  }
  viewportEl.innerHTML =
    '<div class="mem-note-head"><div class="mem-note-title"><svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-user"/></svg> 人物卡片</div></div>' +
    '<div class="mem-note-body">' +
      list.map(p =>
        '<div class="mem-person-card"><div class="mem-person-name">' + esc(p.title || '未知') + '</div>' +
        '<p class="md-p">' + esc(p.content || '').slice(0, 600) + '</p>' +
        '<button class="mem-btn mem-archive" data-mem="' + esc(p.mem_id) + '"><svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-box"/></svg> 归档</button></div>'
      ).join('') +
    '</div>';
  $$('.mem-archive', viewportEl).forEach(el => el.onclick = async () => {
    const r = await archiveMemory(el.dataset.mem);
    if (r && r.ok) { toast('已归档'); showPersons(); }
  });
}

/* ---------------- 归档记忆列表（冷存储视图） ---------------- */
async function showArchived() {
  let list;
  try { list = await api('/api/memories?archived=1&limit=500'); }
  catch (e) { toast('归档记忆加载失败：' + e.message); return; }
  state.archiveView = true;
  setArchiveBtn();
  memMemGraphWrap.hidden = true; cancelAnimationFrame(memGraphAnim);
  graphWrap.hidden = true; cancelAnimationFrame(graphAnim);
  panel.classList.remove('graph-on');
  state.tabs = []; renderTabs();
  if (!list.length) {
    viewportEl.innerHTML = '<div class="mem-empty">归档库为空。在「人物」或记忆详情中点击「<svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-box"/></svg> 归档」即可把记忆移入冷存储，可随时恢复。</div>';
    return;
  }
  viewportEl.innerHTML =
    '<div class="mem-note-head"><div class="mem-note-title"><svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-box"/></svg> 归档记忆 · ' + list.length + ' 条</div>' +
      '<button class="mem-btn" id="memArchiveExit">返回活跃</button></div>' +
    '<div class="mem-note-body mem-arch-list">' +
      list.map(m =>
        '<div class="mem-arch-item" data-mem="' + esc(m.mem_id) + '">' +
          '<div class="mem-arch-main">' +
            '<div class="mem-arch-title">' + esc(m.title || m.mem_id || '未命名') + '</div>' +
            '<div class="mem-arch-meta">' + esc(m.event_type || '') +
              (m.content ? ' · ' + esc(String(m.content).slice(0, 90)) : '') + '</div>' +
          '</div>' +
          '<button class="mem-btn mem-restore" data-mem="' + esc(m.mem_id) + '">恢复</button>' +
        '</div>'
      ).join('') +
    '</div>';
  $('#memArchiveExit').onclick = () => { state.archiveView = false; setArchiveBtn(); showPersons(); };
  $$('.mem-restore', viewportEl).forEach(el => el.onclick = async () => {
    const r = await restoreMemory(el.dataset.mem);
    if (r && r.ok) { toast('已恢复：' + esc(el.dataset.mem)); showArchived(); }
  });
}

function setArchiveBtn() {
  const btn = $('#memArchiveBtn');
  if (!btn) return;
  btn.textContent = state.archiveView ? '返回活跃' : '<svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-box"/></svg> 归档';
  btn.classList.toggle('on', state.archiveView);
}

/* ---------------- 面板开关 ---------------- */
function open() {
  panel.hidden = false;
  document.body.classList.add('mem-open');
  state = freshState();
  setArchiveBtn();
  searchEl.value = '';
  graphWrap.hidden = true; panel.classList.remove('graph-on');
  memMemGraphWrap.hidden = true; cancelAnimationFrame(memGraphAnim);
  cancelAnimationFrame(graphAnim);
  tabsEl.innerHTML = '';
  tocEl.innerHTML = '<div class="mem-sub">打开笔记后显示大纲。</div>';
  backlinksPanelEl.innerHTML = '<div class="mem-sub">无反向链接。</div>';
  viewportEl.innerHTML = '<div class="mem-empty">从左侧文件树选择一条笔记，或点击「＋ 新建」。</div>';
  sideEl.classList.remove('collapsed'); outlineEl.classList.remove('collapsed');
  $('#memSideToggle').classList.remove('on'); $('#memOutlineToggle').classList.remove('on');
  refresh();
  if (window.OverlayManager) {
    window.OverlayManager.track('jz-memory', {
      el: panel,
      onClose: _closeVisual,
      type: window.OverlayManager.OverlayType.PANEL,
      trap: false,
      autofocus: false
    });
  }
}
function _closeVisual() {
  panel.hidden = true;
  document.body.classList.remove('mem-open');
  cancelAnimationFrame(graphAnim);
}
  function close() {
    if (window.OverlayManager && window.OverlayManager.isOpen('jz-memory')) {
      window.OverlayManager.close('jz-memory');
    } else {
      _closeVisual();
    }
  }
$('#memClose').onclick = close;
$('#memNew').onclick = newNote;
$('#memGraphBtn').onclick = () => { if (graphWrap.hidden) showGraph(); else { graphWrap.hidden = true; panel.classList.remove('graph-on'); cancelAnimationFrame(graphAnim); } };
$('#memMemGraphBtn').onclick = () => {
  if (memMemGraphWrap.hidden) {
    if (!graphWrap.hidden) { graphWrap.hidden = true; cancelAnimationFrame(graphAnim); }
    showMemGraph();
  } else { memMemGraphWrap.hidden = true; cancelAnimationFrame(memGraphAnim); }
};
$('#memPersonsBtn').onclick = () => showPersons();
$('#memArchiveBtn').onclick = () => { if (state.archiveView) { state.archiveView = false; showPersons(); } else { showArchived(); } };
$('#memSideToggle').onclick = function () {
  var c = window.PanelManager ? PanelManager.collapse('memory', 'side') : !(state.sideCollapsed = !state.sideCollapsed);
  if (!window.PanelManager) sideEl.classList.toggle('collapsed', state.sideCollapsed);
  state.sideCollapsed = c;
  $('#memSideToggle').classList.toggle('on', c);
};
$('#memOutlineToggle').onclick = function () {
  var c = window.PanelManager ? PanelManager.collapse('memory', 'outline') : !(state.outlineCollapsed = !state.outlineCollapsed);
  if (!window.PanelManager) outlineEl.classList.toggle('collapsed', state.outlineCollapsed);
  state.outlineCollapsed = c;
  $('#memOutlineToggle').classList.toggle('on', c);
};
  searchEl.oninput = () => { state.q = searchEl.value.trim(); refresh(); };
// 点击卡片外的遮罩区域关闭
panel.addEventListener('click', (e) => { if (e.target === panel) close(); });

// 暴露给 app.js 的「记忆」按钮，及认知星云的节点点击
window.JZMemory = { open, close, refresh, openNote };
// Workspace：把折叠区域交给 PanelManager 统一管理，消除面板自存工作区状态（Sprint 3/4）
if (window.PanelManager) {
  PanelManager.registerCollapse('memory', 'side', { el: function () { return document.getElementById('memSide'); }, cls: 'collapsed' });
  PanelManager.registerCollapse('memory', 'outline', { el: function () { return document.getElementById('memOutline'); }, cls: 'collapsed' });
}
// 保险：页面加载/恢复会话时确保面板默认关闭
close();
