// 小6 · 首次启动引导（P7-3）
// 纯前端、零密钥：首启欢迎 + 快速个性化（名字 / 主题 / 语音 / 主动智能）。
// 设置全部落 localStorage；AI 名字与主题额外最佳努力持久化到服务端配置。

const ONB_KEY = 'xiao6_onboarded';
const ONB_VERSION = 1; // 引导流程大改时提升此值可强制所有用户重引导

const SETTINGS_KEY = 'xiao6_settings_v1';

function onbLoadSettings() {
  try {
    return JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{}') || {};
  } catch {
    return {};
  }
}

function onbSaveSettings(patch) {
  const s = onbLoadSettings();
  Object.assign(s, patch);
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(s));
  } catch {}
}

function onbApplyTheme(t) {
  const norm = (t === 'dark' || t === 'system' || !t) ? 'dark-cyan' : t;
  if (window.ZZSettings && window.ZZSettings.set) {
    // ZZSettings.set 会落 localStorage 并实时应用 data-theme
    window.ZZSettings.set({ theme: norm });
  } else {
    document.body.setAttribute('data-theme', norm);
  }
}

const ZZOnboarding = {
  _current: 0,
  _dirty: {},

  // 首启检测：未引导过才弹
  maybeShow() {
    let done = false;
    try { done = localStorage.getItem(ONB_KEY) === String(ONB_VERSION); } catch {}
    if (!done) this.show();
  },

  show() {
    const overlay = document.getElementById('onbOverlay');
    if (!overlay) return;
    overlay.hidden = false;
    requestAnimationFrame(() => overlay.classList.add('show'));

    this._current = 0;
    this._dirty = {};

    const s = onbLoadSettings();
    const nameInput = document.getElementById('onbName');
    if (nameInput) nameInput.value = s.aiName || '小6';
    const tts = document.getElementById('onbTts');
    if (tts) tts.checked = !!s.autoTts;
    const pro = document.getElementById('onbProactive');
    if (pro) pro.checked = s.proactive !== false;

    this._selectTheme(s.theme || 'dark-cyan', false);
    this._goto(0);
  },

  hide() {
    const overlay = document.getElementById('onbOverlay');
    if (!overlay) return;
    overlay.classList.remove('show');
    setTimeout(() => { overlay.hidden = true; }, 300);
  },

  _goto(step) {
    this._current = step;
    document.querySelectorAll('#onbOverlay .onb-step').forEach((el) => {
      const i = Number(el.getAttribute('data-step'));
      el.classList.toggle('active', i === step);
    });
    document.querySelectorAll('#onbOverlay .onb-dot').forEach((el) => {
      const i = Number(el.getAttribute('data-step'));
      el.classList.toggle('active', i <= step);
      el.classList.toggle('done', i < step);
    });
    const card = document.querySelector('#onbOverlay .onb-card');
    if (card) { card.classList.remove('re-pop'); void card.offsetWidth; card.classList.add('re-pop'); }
  },

  _selectTheme(t, apply = true) {
    document.querySelectorAll('#onbOverlay .onb-theme').forEach((b) => {
      b.classList.toggle('active', b.getAttribute('data-theme') === t);
    });
    this._dirty.theme = t;
    if (apply) onbApplyTheme(t);
  },

  async _finish() {
    const s = onbLoadSettings();
    const nameInput = document.getElementById('onbName');
    const name = (nameInput && nameInput.value.trim()) || '小6';
    const tts = document.getElementById('onbTts');
    const pro = document.getElementById('onbProactive');
    const patch = {
      aiName: name,
      autoTts: !!(tts && tts.checked),
      proactive: !(pro && !pro.checked),
      theme: this._dirty.theme || s.theme || 'dark-cyan',
    };
    onbSaveSettings(patch);
    if (window.ZZSettings && window.ZZSettings.set) {
      window.ZZSettings.set(patch);
    } else {
      onbApplyTheme(patch.theme);
    }
    // 后端持久化（最佳努力：零密钥 / 离线时静默失败，不影响本机体验）
    try {
      await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ AI_DISPLAY_NAME: name, XIAO6_THEME: patch.theme }),
      });
    } catch (_) {}
    try { localStorage.setItem(ONB_KEY, String(ONB_VERSION)); } catch {}
    this.hide();
  },

  _skip() {
    try { localStorage.setItem(ONB_KEY, String(ONB_VERSION)); } catch {}
    this.hide();
  },

  _bind() {
    const overlay = document.getElementById('onbOverlay');
    if (!overlay || overlay.dataset.bound) return;
    overlay.dataset.bound = '1';

    overlay.querySelectorAll('[data-action]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const a = btn.getAttribute('data-action');
        if (a === 'next') this._goto(Math.min(this._current + 1, 2));
        else if (a === 'back') this._goto(Math.max(this._current - 1, 0));
        else if (a === 'finish') this._finish();
        else if (a === 'skip') this._skip();
      });
    });

    overlay.querySelectorAll('.onb-theme').forEach((b) => {
      b.addEventListener('click', () => this._selectTheme(b.getAttribute('data-theme'), true));
    });

    const nameInput = document.getElementById('onbName');
    if (nameInput) {
      nameInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); this._goto(1); }
      });
    }
  },
};

window.ZZOnboarding = ZZOnboarding;

function onbInit() {
  ZZOnboarding._bind();
  ZZOnboarding.maybeShow();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', onbInit);
} else {
  onbInit();
}
