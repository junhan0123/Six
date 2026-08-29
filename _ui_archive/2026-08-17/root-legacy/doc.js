// doc.js —— 全屏「文档」面板
// 由 app.js handleToolEvent 收到 { xiao6_event:'panel', panel:'doc', data } 时调用 window.ZZDoc.open(data)
// 行为：
//   - 若 data 为空（无即时内容）：GET /api/doc?action=list → 渲染文档列表 {docs:[{name,size,mtime,ext}]}
//   - 点击某行 → GET /api/doc?action=read&name=<encodeURIComponent(name)> → 渲染 {name,ext,content}
//   - 阅读视图提供「返回列表」按钮

const DOC = { panel: null, open: false, view: 'list', current: null };

// 本地转义：避免依赖其它模块作用域内的 escapeHtml
function escapeHtml(str) {
  return String(str == null ? '' : str).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

function docBuild() {
  if (DOC.panel) return;
  const html = `
  <div class="doc-panel" id="doc-panel" role="dialog" aria-label="文档服务">
    <div class="doc-backdrop" data-close="1"></div>
    <div class="doc-stage glass">
      <div class="doc-bar">
        <div class="doc-title"><span class="doc-dot"></span>文档</div>
        <button class="doc-back" id="doc-back" title="返回列表">‹ 列表</button>
        <button class="doc-close" id="doc-close" title="关闭（Esc）" aria-label="关闭"><svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-close"/></svg></button>
      </div>
      <div class="doc-body" id="doc-body"></div>
    </div>
  </div>`;
  document.body.insertAdjacentHTML('beforeend', html);
  DOC.panel = document.getElementById('doc-panel');
  document.getElementById('doc-close').addEventListener('click', docClose);
  DOC.panel.querySelector('[data-close]').addEventListener('click', docClose);
  document.getElementById('doc-back').addEventListener('click', () => docList());
}

// 文件大小可读化
function docFmtSize(bytes) {
  if (bytes == null) return '—';
  const n = Number(bytes);
  if (!isFinite(n)) return '—';
  if (n < 1024) return n + ' B';
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB';
  return (n / 1024 / 1024).toFixed(2) + ' MB';
}

function docFmtTime(ts) {
  if (!ts) return '—';
  const d = new Date(ts * (String(ts).length <= 10 ? 1000 : 1));
  if (isNaN(d.getTime())) return String(ts);
  const p = (x) => String(x).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

async function docList() {
  DOC.view = 'list';
  const body = document.getElementById('doc-body');
  body.innerHTML = `<div class="doc-loading">正在读取文档列表…</div>`;
  try {
    const r = await fetch('/api/doc?action=list', { method: 'GET' });
    const d = await r.json();
    const docs = (d && Array.isArray(d.docs)) ? d.docs : [];
    if (!docs.length) {
      body.innerHTML = `<div class="doc-empty">暂无文档</div>`;
      return;
    }
    body.innerHTML = `
      <div class="doc-list-head">共 ${docs.length} 个文档</div>
      <div class="doc-list">${docs.map((doc, i) => `
        <div class="doc-row" data-name="${escapeHtml(String(doc.name))}" data-idx="${i}">
          <div class="doc-row-main">
            <div class="doc-row-name">${escapeHtml(String(doc.name))}</div>
            <div class="doc-row-meta">
              <span class="doc-ext">${escapeHtml(doc.ext ? String(doc.ext) : '—')}</span>
              <span class="doc-size">${docFmtSize(doc.size)}</span>
              <span class="doc-mtime">${docFmtTime(doc.mtime)}</span>
            </div>
          </div>
          <div class="doc-row-go">›</div>
        </div>`).join('')}</div>`;
    body.querySelectorAll('.doc-row').forEach((row) => {
      row.addEventListener('click', () => docRead(row.getAttribute('data-name')));
    });
  } catch (e) {
    body.innerHTML = `<div class="doc-empty">读取文档列表失败：${escapeHtml(String(e && e.message || e))}</div>`;
  }
}

async function docRead(name) {
  if (!name) return;
  DOC.view = 'read';
  DOC.current = name;
  const body = document.getElementById('doc-body');
  body.innerHTML = `<div class="doc-loading">正在打开 ${escapeHtml(name)}…</div>`;
  try {
    const r = await fetch('/api/doc?action=read&name=' + encodeURIComponent(name), { method: 'GET' });
    const d = await r.json();
    if (d && d.error) {
      body.innerHTML = `<div class="doc-empty">无法打开：${escapeHtml(String(d.error))}</div>`;
      return;
    }
    const doc = d && d.doc ? d.doc : d;
    const content = doc && doc.content != null ? String(doc.content) : '';
    body.innerHTML = `
      <div class="doc-read-head">
        <div class="doc-read-name">${escapeHtml(doc && doc.name != null ? String(doc.name) : name)}</div>
        <div class="doc-read-meta">${escapeHtml((doc && doc.ext) ? String(doc.ext) : '')} · ${docFmtSize(doc && doc.size)}</div>
      </div>
      <pre class="doc-content">${escapeHtml(content)}</pre>`;
  } catch (e) {
    body.innerHTML = `<div class="doc-empty">读取文档失败：${escapeHtml(String(e && e.message || e))}</div>`;
  }
}

function docOpen(data) {
  docBuild();
  if (data && data.content != null) {
    // 后端已带即时内容：直接进阅读视图
    DOC.view = 'read';
    DOC.current = data.name || '文档';
    const body = document.getElementById('doc-body');
    body.innerHTML = `
      <div class="doc-read-head">
        <div class="doc-read-name">${escapeHtml(String(DOC.current))}</div>
        <div class="doc-read-meta">${escapeHtml(data.ext ? String(data.ext) : '')}</div>
      </div>
      <pre class="doc-content">${escapeHtml(String(data.content))}</pre>`;
  } else {
    docList();
  }
  requestAnimationFrame(() => document.body.classList.add('doc-mode'));
  DOC.open = true;
  window.dispatchEvent(new CustomEvent('xiao6:doc-mode', { detail: { active: true } }));
  // Sprint 1/2：登记到 OverlayManager（统一 ESC / 焦点 / 栈）
  if (window.OverlayManager) window.OverlayManager.track('doc', { el: DOC.panel, onClose: docCloseImpl, type: window.OverlayManager.OverlayType.PANEL, trap: false });
}

function docCloseImpl() {
  document.body.classList.remove('doc-mode');
  DOC.open = false;
  DOC.view = 'list';
  DOC.current = null;
  window.dispatchEvent(new CustomEvent('xiao6:doc-mode', { detail: { active: false } }));
}

function docClose() {
  if (window.OverlayManager && window.OverlayManager.isOpen('doc')) window.OverlayManager.close('doc');
  else docCloseImpl();
}

window.ZZDoc = { open: docOpen, close: docClose, list: docList };
