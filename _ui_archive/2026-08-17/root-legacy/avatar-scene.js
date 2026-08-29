// avatar-scene.js — 小6 P11-3 可选 3D 化身（全息 HUD 化身层）
// 轻量风格化人形（胶囊躯干 + 球头）+ 环绕粒子场；三姿态 idle/thinking/speaking。
// 默认关闭（FEATURE_AVATAR_SCENE=false），仅 /api/hud/config.avatar_scene=true 时挂载。
// 暴露 window.ZZAvatarScene = { setState(mode) }。与 main-orb(语音球) 互补，可并存。

import * as THREE from './vendor/three/three.module.js';

let cfg = { enabled: false };
let canvas = null, renderer = null, scene = null, camera = null;
let figure = null, aura = null, auraMat = null;
let raf = 0, running = false, lastT = 0, mounted = false;
let mode = 'idle';

const POSTURE = {
  idle:     { color: 0x22d3ee, tilt: 0.04, bob: 0.10, spin: 0.10 },
  thinking: { color: 0xf5b544, tilt: 0.18, bob: 0.04, spin: 0.35 },
  speaking: { color: 0x22d3ee, tilt: -0.06, bob: 0.22, spin: 0.18 },
};

function prefersReduced() {
  return (
    document.body.classList.contains('reduced-motion') ||
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );
}

function buildFigure() {
  const g = new THREE.Group();
  const mat = new THREE.MeshStandardMaterial({
    color: 0x22d3ee, roughness: 0.35, metalness: 0.6,
    emissive: 0x0a2a33, emissiveIntensity: 0.6,
  });
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.5, 24, 24), mat);
  head.position.y = 1.5;
  const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.55, 1.4, 8, 16), mat);
  body.position.y = 0.2;
  g.add(head, body);

  // 环绕粒子场
  const N = 260;
  const geo = new THREE.BufferGeometry();
  const pos = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) {
    const a = Math.random() * Math.PI * 2;
    const r = 2.2 + Math.random() * 1.4;
    const y = (Math.random() - 0.5) * 4;
    pos[i * 3] = Math.cos(a) * r;
    pos[i * 3 + 1] = y;
    pos[i * 3 + 2] = Math.sin(a) * r;
  }
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  auraMat = new THREE.PointsMaterial({
    color: 0x22d3ee, size: 0.08, transparent: true, opacity: 0.8,
    blending: THREE.AdditiveBlending, depthWrite: false,
  });
  aura = new THREE.Points(geo, auraMat);
  g.add(aura);
  return g;
}

function mount() {
  if (mounted) return;
  if (!cfg.enabled) return;
  canvas = document.getElementById('avatarScene');
  if (!canvas) {
    canvas = document.createElement('canvas');
    canvas.id = 'avatarScene';
    canvas.style.cssText =
      'position:fixed;left:50%;top:46%;transform:translate(-50%,-50%);' +
      'width:min(46vmin,420px);height:min(46vmin,420px);pointer-events:none;' +
      'z-index:2;opacity:.92;';
    document.body.appendChild(canvas);
  }
  try {
    renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  } catch {
    return; // 不支持 WebGL 静默放弃（默认关闭，不影响主流程）
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
  renderer.setSize(canvas.clientWidth || 420, canvas.clientHeight || 420, false);
  renderer.setClearColor(0x000000, 0);

  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(50, 1, 0.1, 100);
  camera.position.set(0, 0.8, 6);

  scene.add(new THREE.AmbientLight(0xffffff, 0.6));
  const key = new THREE.DirectionalLight(0xffffff, 0.9);
  key.position.set(3, 5, 4);
  scene.add(key);

  figure = buildFigure();
  scene.add(figure);

  mounted = true;
  window.addEventListener('resize', onResize);
  new MutationObserver(() => { if (prefersReduced()) stop(); else start(); })
    .observe(document.body, { attributes: true, attributeFilter: ['class'] });
  start();
}

function onResize() {
  if (!renderer || !canvas) return;
  renderer.setSize(canvas.clientWidth || 420, canvas.clientHeight || 420, false);
}

function loop(now) {
  raf = requestAnimationFrame(loop);
  const t = now / 1000;
  const dt = Math.min((now - lastT) / 1000, 0.05);
  lastT = now;
  const p = POSTURE[mode] || POSTURE.idle;
  if (figure) {
    figure.rotation.z = Math.sin(t * 0.6) * p.tilt;
    figure.position.y = Math.sin(t * 1.2) * p.bob;
    figure.rotation.y += p.spin * dt;
  }
  if (auraMat) {
    const c = new THREE.Color(p.color);
    auraMat.color.lerp(c, 0.05);
    figure && figure.traverse((o) => {
      if (o.material && o.material.emissive) {
        o.material.color.lerp(c, 0.05);
        o.material.emissive.lerp(c.clone().multiplyScalar(0.25), 0.05);
      }
    });
  }
  renderer.render(scene, camera);
}

function start() {
  if (!renderer || running || prefersReduced()) return;
  running = true;
  lastT = performance.now();
  raf = requestAnimationFrame(loop);
}
function stop() {
  running = false;
  if (raf) cancelAnimationFrame(raf);
  raf = 0;
}

function setState(m) {
  if (!POSTURE[m]) return;
  mode = m;
}

async function bootstrap() {
  try {
    const r = await fetch('/api/hud/config');
    const d = await r.json();
    cfg.enabled = !!d.avatar_scene;
  } catch {
    cfg.enabled = false;
  }
  if (!cfg.enabled) return;
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount, { once: true });
  } else {
    mount();
  }
}

window.ZZAvatarScene = { setState, isEnabled: () => cfg.enabled, isMounted: () => mounted };

bootstrap();

export {};
