/* 小6桌宠 · 渲染控制（contextIsolation 安全模式，经 preload bridge 访问 IPC） */
const HOST = document.getElementById('lottieHost');
const WRAP = document.getElementById('petWrap');
const BUBBLE = document.getElementById('bubble');

let anim = null;

try {
  anim = lottie.loadAnimation({
    container: HOST,
    renderer: 'svg',
    loop: true,
    autoplay: true,
    path: './robot-futuristic.json'
  });
} catch (e) {
  console.error('Lottie load failed:', e);
}

/* 对外暴露的桌宠 API（IPC 经 preload bridge，无 Node 权限） */
window.Pet = {
  say(text, ms = 3200) {
    BUBBLE.textContent = text;
    BUBBLE.classList.add('show');
    WRAP.classList.add('bounce');
    setTimeout(() => {
      BUBBLE.classList.remove('show');
      WRAP.classList.remove('bounce');
    }, ms);
  },
  hide() { if (window.petAPI) window.petAPI.hide(); },
  show() { if (window.petAPI) window.petAPI.show(); },
  bounce() { WRAP.classList.add('bounce'); setTimeout(() => WRAP.classList.remove('bounce'), 500); }
};

/* 演示：桌宠加载后自我介绍 */
setTimeout(() => {
  window.Pet.say('老板，我在桌面上。有事随时叫我。', 4200);
}, 1200);

/* 右键菜单占位 */
WRAP.addEventListener('contextmenu', (e) => {
  e.preventDefault();
  // TODO: 调用主进程弹出上下文菜单（隐藏/退出/切换状态）
});
