// 小6 · 高级质感虚拟人（替代 3D 地球）
// 纯程序化 Three.js 生成，离线可用：本地 three，零外部资源、零积分。
// 材质用 MeshPhysicalMaterial（清漆陶瓷感 + 自发光 + 程序化环境反射），身形平滑曲面 + 发光面部，
// 边缘光(Rim Light) + 背后辉光 + 接触阴影营造高级科技虚拟人质感。
// 复用地球组件的相机/灯光/交互框架；通过监听 .orb-wrap 的 thinking/speaking 类自动切换状态。
// 对外暴露 window.ZZAvatar（主接口）与兼容别名 window.ZZEarth（承接 app.js 地理定位调用）。
const THREE_LOCAL = './vendor/three/three.module.js';
const THREE_CDN = 'https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js';
const THREE_CDN_FALLBACK = 'https://unpkg.com/three@0.160.0/build/three.module.js';

const STATE_COLORS = {
  idle:     0x22d3ee, // 青
  thinking: 0xF5B544, // 琥珀
  speaking: 0x2DD4BF, // 青绿
};

let THREE = null;
async function loadThree() {
  if (THREE) return THREE;
  try { THREE = await import(THREE_LOCAL); }
  catch { try { THREE = await import(THREE_CDN); } catch { THREE = await import(THREE_CDN_FALLBACK); } }
  return THREE;
}

// 程序化环境贴图：给 PBR 材质提供反射/折射来源（无需任何外部 HDR 文件）
function makeEnvTexture(T, renderer) {
  const c = document.createElement('canvas');
  c.width = 512; c.height = 256;
  const ctx = c.getContext('2d');
  const g = ctx.createLinearGradient(0, 0, 0, 256);
  g.addColorStop(0.0, '#0c1f2b');
  g.addColorStop(0.5, '#06121a');
  g.addColorStop(1.0, '#02060a');
  ctx.fillStyle = g; ctx.fillRect(0, 0, 512, 256);
  // 几处冷色光斑，模拟棚灯，制造材质高光
  const blobs = [[110, 70, '#2dd4bf'], [400, 55, '#22d3ee'], [260, 210, '#1b6e7a'], [60, 180, '#0e4a57']];
  for (const [x, y, col] of blobs) {
    const rg = ctx.createRadialGradient(x, y, 0, x, y, 95);
    rg.addColorStop(0, col);
    rg.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = rg; ctx.fillRect(0, 0, 512, 256);
  }
  const tex = new T.CanvasTexture(c);
  tex.mapping = T.EquirectangularReflectionMapping;
  if (T.SRGBColorSpace) tex.colorSpace = T.SRGBColorSpace;
  const pmrem = new T.PMREMGenerator(renderer);
  const rt = pmrem.fromEquirectangular(tex);
  tex.dispose(); pmrem.dispose();
  return rt.texture;
}

// 径向渐变贴图（用于背后辉光 / 接触阴影）
function radialTexture(T, inner, outer) {
  const c = document.createElement('canvas');
  c.width = c.height = 256;
  const ctx = c.getContext('2d');
  const rg = ctx.createRadialGradient(128, 128, 0, 128, 128, 128);
  rg.addColorStop(0, inner);
  rg.addColorStop(1, outer);
  ctx.fillStyle = rg; ctx.fillRect(0, 0, 256, 256);
  const tex = new T.CanvasTexture(c);
  if (T.SRGBColorSpace) tex.colorSpace = T.SRGBColorSpace;
  return tex;
}

class Avatar {
  constructor(canvas) {
    this.canvas = canvas;
    this.renderer = this.scene = this.camera = null;
    this.human = null;
    this.head = this.armL = this.armR = null;
    this.bodyMat = this.eyeMat = this.mouthMat = null;
    this.particles = this.groundRing = this.groundInner = null;
    this.backglow = this.contactShadow = this.stars = null;
    this._armLBase = 0.20; this._armRBase = -0.20;
    this.state = 'idle';

    this.isDragging = false; this.prevMouse = { x: 0, y: 0 };
    this.rotX = 0.06; this.rotY = 0; this.velX = 0; this.velY = 0.004;
    this.camDist = 4.8; this.camDistMin = 3.4; this.camDistMax = 7.2;

    this.appearing = false; this.appearScale = 0;
    this.animFrame = null; this._bound = {};
    this._userLabel = '';
    this._markerUntil = 0;
  }

  async init() {
    const T = await loadThree();
    this.scene = new T.Scene();
    const w = this.canvas.clientWidth  || 280;
    const h = this.canvas.clientHeight || 280;
    this.camera = new T.PerspectiveCamera(42, w / h, 0.1, 100);
    this.camera.position.set(0, 0.25, this.camDist);

    this.renderer = new T.WebGLRenderer({ canvas: this.canvas, antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(w, h, false);
    if (T.SRGBColorSpace) this.renderer.outputColorSpace = T.SRGBColorSpace;
    if (T.ACESFilmicToneMapping) {
      this.renderer.toneMapping = T.ACESFilmicToneMapping;
      this.renderer.toneMappingExposure = 1.12;
    }

    // 程序化环境贴图（PBR 反射来源）
    try { this.scene.environment = makeEnvTexture(T, this.renderer); } catch (e) { /* 环境可选 */ }

    // 灯光：主光 + 边缘光(Rim) + 半球 + 环境 —— 边缘光是高级质感的关键
    const key = new T.DirectionalLight(0xffffff, 2.1);
    key.position.set(2.6, 4.2, 3.2);
    const rim = new T.DirectionalLight(0x7af0ff, 2.8);
    rim.position.set(-3.5, 2.2, -4.0);
    this.scene.add(key, rim);
    this.scene.add(new T.HemisphereLight(0xcfe9ff, 0x0a1018, 0.55));
    this.scene.add(new T.AmbientLight(0xffffff, 0.12));

    this._buildHuman(T);
    this._buildBackglow(T);
    this._buildContactShadow(T);
    this._buildParticles(T);
    this._buildGroundRing(T);
    this._buildStars(T);

    // 初始隐藏（出现动画）
    this.human.scale.setScalar(0);
    this.backglow.material.opacity = 0;
    this.contactShadow.material.opacity = 0;
    this.groundRing.scale.setScalar(0);
    this.groundInner.scale.setScalar(0);
    this.particles.material.opacity = 0;
    this.stars.material.opacity = 0;

    this._bindEvents();
    this._animate();
  }

  // ── 主体材质：深色陶瓷/玻璃质感（清漆 + 低粗糙 + 状态色自发光）──
  _bodyMaterial(T, color) {
    return new T.MeshPhysicalMaterial({
      color: 0x123039,
      metalness: 0.15,
      roughness: 0.22,
      clearcoat: 1.0,
      clearcoatRoughness: 0.12,
      emissive: new T.Color(color),
      emissiveIntensity: 0.18,
      envMapIntensity: 1.35,
      transparent: true,
      opacity: 0.94,
    });
  }

  // ── 发光材质：眼/嘴/外壳（强自发光）──
  _glowMaterial(T, color, intensity) {
    return new T.MeshStandardMaterial({
      color: new T.Color(color),
      emissive: new T.Color(color),
      emissiveIntensity: intensity,
      roughness: 0.4,
      metalness: 0,
      transparent: true,
      opacity: 0.95,
    });
  }

  _buildHuman(T) {
    const g = new T.Group();
    const col = STATE_COLORS.idle;

    // 头部（椭球 + 发光面部）
    this.head = new T.Group();
    const headMesh = new T.Mesh(new T.SphereGeometry(0.30, 36, 36), this._bodyMaterial(T, col));
    headMesh.scale.set(1, 1.16, 1.04);
    this.bodyMat = headMesh.material; // 主体共享材质
    const eyeGeo = new T.SphereGeometry(0.045, 18, 18);
    this.eyeMat = this._glowMaterial(T, col, 2.4);
    const eyeL = new T.Mesh(eyeGeo, this.eyeMat); eyeL.position.set(-0.10, 0.05, 0.27);
    const eyeR = new T.Mesh(eyeGeo, this.eyeMat); eyeR.position.set( 0.10, 0.05, 0.27);
    this.mouthMat = this._glowMaterial(T, col, 0.8);
    const mouth = new T.Mesh(new T.TorusGeometry(0.075, 0.013, 10, 24, Math.PI), this.mouthMat);
    mouth.position.set(0, -0.13, 0.28); mouth.rotation.z = Math.PI; // 朝下成微笑弧
    this.head.add(headMesh, eyeL, eyeR, mouth);
    this.head.position.set(0, 1.08, 0);
    g.add(this.head);

    // 颈
    const neck = new T.Mesh(new T.CylinderGeometry(0.085, 0.105, 0.18, 22), this.bodyMat);
    neck.position.set(0, 0.86, 0);
    g.add(neck);

    // 肩（球，平滑过渡）
    const shoulderGeo = new T.SphereGeometry(0.17, 22, 22);
    const shoulderL = new T.Mesh(shoulderGeo, this.bodyMat); shoulderL.position.set(-0.30, 0.58, 0);
    const shoulderR = new T.Mesh(shoulderGeo, this.bodyMat); shoulderR.position.set( 0.30, 0.58, 0);
    g.add(shoulderL, shoulderR);

    // 躯干（胶囊）
    const torso = new T.Mesh(new T.CapsuleGeometry(0.27, 0.56, 10, 28), this.bodyMat);
    torso.position.set(0, 0.28, 0);
    g.add(torso);

    // 手臂（胶囊，自肩部略外张）
    const armGeo = new T.CapsuleGeometry(0.075, 0.62, 8, 18);
    this.armL = new T.Mesh(armGeo, this.bodyMat);
    this.armL.position.set(-0.45, 0.40, 0); this.armL.rotation.z = this._armLBase;
    this.armR = new T.Mesh(armGeo, this.bodyMat);
    this.armR.position.set( 0.45, 0.40, 0); this.armR.rotation.z = this._armRBase;
    g.add(this.armL, this.armR);

    // 腿
    const legGeo = new T.CapsuleGeometry(0.10, 0.62, 8, 18);
    const legL = new T.Mesh(legGeo, this.bodyMat); legL.position.set(-0.14, -0.46, 0);
    const legR = new T.Mesh(legGeo, this.bodyMat); legR.position.set( 0.14, -0.46, 0);
    g.add(legL, legR);

    g.position.y = 0.1;
    this.human = g;
    this.scene.add(g);
  }

  _buildBackglow(T) {
    // 背后径向辉光（additive，状态色），营造光晕
    const tex = radialTexture(T, 'rgba(255,255,255,0.9)', 'rgba(255,255,255,0)');
    this.backglow = new T.Mesh(
      new T.PlaneGeometry(4.2, 4.2),
      new T.MeshBasicMaterial({ map: tex, color: STATE_COLORS.idle, transparent: true, opacity: 0, blending: T.AdditiveBlending, depthWrite: false }),
    );
    this.backglow.position.set(0, 0.2, -1.6);
    this.scene.add(this.backglow);
  }

  _buildContactShadow(T) {
    const tex = radialTexture(T, 'rgba(0,0,0,0.55)', 'rgba(0,0,0,0)');
    this.contactShadow = new T.Mesh(
      new T.PlaneGeometry(2.0, 2.0),
      new T.MeshBasicMaterial({ map: tex, transparent: true, opacity: 0, depthWrite: false }),
    );
    this.contactShadow.rotation.x = -Math.PI / 2;
    this.contactShadow.position.y = -1.06;
    this.scene.add(this.contactShadow);
  }

  _buildParticles(T) {
    const n = 320, pos = [];
    for (let i = 0; i < n; i++) {
      const a = Math.random() * Math.PI * 2;
      const b = Math.acos(2 * Math.random() - 1);
      const r = 1.9 + Math.random() * 1.5;
      pos.push(r * Math.sin(b) * Math.cos(a), Math.random() * 2.7 - 1.15, r * Math.sin(b) * Math.sin(a));
    }
    const geo = new T.BufferGeometry();
    geo.setAttribute('position', new T.Float32BufferAttribute(pos, 3));
    this.particles = new T.Points(geo, new T.PointsMaterial({ color: STATE_COLORS.idle, size: 0.028, transparent: true, opacity: 0, depthWrite: false }));
    this.scene.add(this.particles);
  }

  _buildGroundRing(T) {
    this.groundRing = new T.Mesh(
      new T.RingGeometry(0.60, 0.72, 56),
      new T.MeshBasicMaterial({ color: STATE_COLORS.idle, transparent: true, opacity: 0.55, side: T.DoubleSide, depthWrite: false }),
    );
    this.groundRing.rotation.x = -Math.PI / 2; this.groundRing.position.y = -1.05;
    this.groundInner = new T.Mesh(
      new T.RingGeometry(0.46, 0.50, 48),
      new T.MeshBasicMaterial({ color: STATE_COLORS.idle, transparent: true, opacity: 0.32, side: T.DoubleSide, depthWrite: false }),
    );
    this.groundInner.rotation.x = -Math.PI / 2; this.groundInner.position.y = -1.04;
    this.scene.add(this.groundRing, this.groundInner);
  }

  _buildStars(T) {
    const sv = [];
    for (let i = 0; i < 1300; i++) {
      const th = Math.random() * Math.PI * 2;
      const ph = Math.acos(2 * Math.random() - 1);
      const r = 15 + Math.random() * 11;
      sv.push(r * Math.sin(ph) * Math.cos(th), r * Math.cos(ph), r * Math.sin(ph) * Math.sin(th));
    }
    const sg = new T.BufferGeometry();
    sg.setAttribute('position', new T.Float32BufferAttribute(sv, 3));
    this.stars = new T.Points(sg, new T.PointsMaterial({ color: 0xffffff, size: 0.05, sizeAttenuation: true, transparent: true, opacity: 0 }));
    this.scene.add(this.stars);
  }

  _applyColor(hex) {
    const c = new THREE.Color(hex);
    if (this.bodyMat) this.bodyMat.emissive.copy(c);
    if (this.eyeMat) { this.eyeMat.color.copy(c); this.eyeMat.emissive.copy(c); }
    if (this.mouthMat) { this.mouthMat.color.copy(c); this.mouthMat.emissive.copy(c); }
    if (this.particles) this.particles.material.color.copy(c);
    if (this.groundRing) this.groundRing.material.color.copy(c);
    if (this.groundInner) this.groundInner.material.color.copy(c);
    if (this.backglow) this.backglow.material.color.copy(c);
  }

  setState(s) {
    if (!STATE_COLORS[s]) s = 'idle';
    this.state = s;
    this._applyColor(STATE_COLORS[s]);
  }

  // 承接地球时代的地理定位彩蛋：脚下光环高亮脉冲一段时间
  setUserMarker(lat, lon, label) {
    this._userLabel = label || '';
    this._markerUntil = performance.now() + 4000;
    if (this.groundRing) this.groundRing.material.opacity = 0.95;
  }

  _bindEvents() {
    const c = this.canvas;
    const onDown = (e) => {
      this.isDragging = true;
      const p = e.touches ? e.touches[0] : e;
      this.prevMouse = { x: p.clientX, y: p.clientY };
      this.velX = 0; this.velY = 0;
    };
    const onMove = (e) => {
      if (!this.isDragging) return;
      e.preventDefault();
      const p = e.touches ? e.touches[0] : e;
      const dx = p.clientX - this.prevMouse.x, dy = p.clientY - this.prevMouse.y;
      this.velY = dx * 0.003; this.velX = dy * 0.003;
      this.rotY += this.velY; this.rotX += this.velX;
      this.rotX = Math.max(-0.6, Math.min(0.6, this.rotX));
      this.prevMouse = { x: p.clientX, y: p.clientY };
    };
    const onUp = () => { this.isDragging = false; };
    const onWheel = (e) => {
      e.preventDefault();
      this.camDist += e.deltaY * 0.002;
      this.camDist = Math.max(this.camDistMin, Math.min(this.camDistMax, this.camDist));
    };
    c.addEventListener('mousedown', onDown);
    c.addEventListener('mousemove', onMove);
    c.addEventListener('mouseup', onUp);
    c.addEventListener('mouseleave', onUp);
    c.addEventListener('touchstart', onDown, { passive: true });
    c.addEventListener('touchmove', onMove, { passive: false });
    c.addEventListener('touchend', onUp);
    c.addEventListener('wheel', onWheel, { passive: false });
    this._bound = { onDown, onMove, onUp, onWheel };
  }

  triggerAppear() {
    this.appearing = true; this.appearScale = 0;
    if (this.human) this.human.scale.setScalar(0);
    if (this.groundRing) this.groundRing.scale.setScalar(0);
    if (this.groundInner) this.groundInner.scale.setScalar(0);
    if (this.backglow) this.backglow.material.opacity = 0;
    if (this.contactShadow) this.contactShadow.material.opacity = 0;
    if (this.particles) this.particles.material.opacity = 0;
    if (this.stars) this.stars.material.opacity = 0;
  }

  _animate() {
    this.animFrame = requestAnimationFrame(() => this._animate());
    const t = performance.now() * 0.001;

    if (this.appearing) {
      this.appearScale += (1 - this.appearScale) * 0.07;
      if (this.appearScale > 0.999) { this.appearing = false; this.appearScale = 1; }
    }
    const s = this.appearing ? this.appearScale : 1;

    // 呼吸 + 浮动
    const breathe = 1 + Math.sin(t * 1.5) * 0.018;
    if (this.human) {
      this.human.scale.set(s * breathe, s * breathe * 1.03, s * breathe);
      this.human.position.y = 0.1 + Math.sin(t * 1.1) * 0.035;
    }
    if (this.backglow) this.backglow.material.opacity = s * 0.55;
    if (this.contactShadow) this.contactShadow.material.opacity = s * 0.6;
    if (this.groundRing) this.groundRing.scale.setScalar(s);
    if (this.groundInner) this.groundInner.scale.setScalar(s);

    // 旋转（拖拽 + 缓慢自转）
    if (!this.isDragging) {
      this.velX *= 0.92; this.velY *= 0.92;
      this.rotY += this.velY + 0.004;
      this.rotX += this.velX;
      this.rotX = Math.max(-0.6, Math.min(0.6, this.rotX));
    }
    if (this.human) { this.human.rotation.y = this.rotY; this.human.rotation.x = this.rotX; }

    // 手臂摆动
    if (this.armL) this.armL.rotation.z = this._armLBase + Math.sin(t * 1.3) * 0.045;
    if (this.armR) this.armR.rotation.z = this._armRBase - Math.sin(t * 1.3) * 0.045;

    // 状态驱动：说话点头
    if (this.state === 'speaking' && this.head) {
      this.head.rotation.x = Math.sin(t * 7) * 0.09;
    } else if (this.head) {
      this.head.rotation.x *= 0.9;
    }

    // 状态脉冲：主体自发光 + 嘴部（说话时强脉动）
    const pulseSpeed = this.state === 'speaking' ? 8 : this.state === 'thinking' ? 3 : 1.2;
    const pulseAmt  = this.state === 'speaking' ? 0.30 : this.state === 'thinking' ? 0.20 : 0.10;
    const p = (Math.sin(t * pulseSpeed) + 1) / 2;
    if (this.bodyMat) this.bodyMat.emissiveIntensity = 0.16 + p * pulseAmt;
    if (this.mouthMat) this.mouthMat.emissiveIntensity = (this.state === 'speaking' ? 1.4 + p * 1.8 : 0.6);

    if (this.particles) {
      this.particles.rotation.y = t * 0.14;
      this.particles.material.opacity = 0.5 + p * 0.4;
    }

    if (this.groundRing) {
      this.groundRing.rotation.z = t * 0.3;
      this.groundInner.rotation.z = -t * 0.42;
      if (!this._markerUntil || performance.now() >= this._markerUntil) {
        this.groundRing.material.opacity = 0.55;
      }
    }

    if (this.backglow) this.backglow.scale.setScalar(1 + p * 0.04);
    if (this.stars) this.stars.material.opacity = Math.min(1, s * 1.4);

    this._checkResize();
    this.renderer.render(this.scene, this.camera);
  }

  _checkResize() {
    const c = this.canvas, w = c.clientWidth, h = c.clientHeight;
    if (!w || !h) return;
    const dpr = this.renderer.getPixelRatio();
    if (c.width !== Math.round(w * dpr) || c.height !== Math.round(h * dpr)) {
      this.renderer.setSize(w, h, false);
      this.camera.aspect = w / h;
      this.camera.updateProjectionMatrix();
    }
  }

  pause() { if (this.animFrame) { cancelAnimationFrame(this.animFrame); this.animFrame = null; } }
  resume() { if (!this.animFrame && this.renderer) this._animate(); }
  dispose() {
    if (this.animFrame) cancelAnimationFrame(this.animFrame);
    const c = this.canvas, b = this._bound;
    if (b.onDown) c.removeEventListener('mousedown', b.onDown);
    if (b.onMove) c.removeEventListener('mousemove', b.onMove);
    if (b.onUp) c.removeEventListener('mouseup', b.onUp);
    if (b.onUp) c.removeEventListener('mouseleave', b.onUp);
    if (b.onDown) c.removeEventListener('touchstart', b.onDown);
    if (b.onMove) c.removeEventListener('touchmove', b.onMove);
    if (b.onUp) c.removeEventListener('touchend', b.onUp);
    if (b.onWheel) c.removeEventListener('wheel', b.onWheel);
    this.renderer?.dispose(); this.renderer = null;
  }
}

// —— 状态同步：监听 .orb-wrap 的 thinking/speaking 类（app.js 已切换这些类，零侵入）——
function attachStateSync(av) {
  const orb = document.querySelector('.orb-wrap');
  if (!orb) return;
  const apply = () => {
    if (orb.classList.contains('thinking')) av.setState('thinking');
    else if (orb.classList.contains('speaking')) av.setState('speaking');
    else av.setState('idle');
  };
  apply();
  new MutationObserver(apply).observe(orb, { attributes: true, attributeFilter: ['class'] });
}

// —— 对外接口 ——
const ctrl = {
  _av: null,
  _pending: null,
  init(canvas) {
    if (!canvas) return;
    this._av = new Avatar(canvas);
    this._av.init().then(() => {
      this._av.triggerAppear();
      attachStateSync(this._av);
    }).catch((e) => {
      console.warn('[小6·人形] 初始化失败：', e);
    });
  },
  setLocation(lat, lon, label) { this._av ? this._av.setUserMarker(lat, lon, label) : (this._pending = { lat, lon, label }); },
  setState(s) { this._av && this._av.setState(s); },
  pause() { this._av?.pause(); },
  resume() { this._av?.resume(); },
};
window.ZZAvatar = ctrl;
window.ZZEarth = ctrl; // 兼容别名：承接 app.js 的地理定位调用，不破坏现有代码

// 自初始化：模块脚本在 DOM 解析后执行，canvas 已存在
const _c = document.getElementById('earth');
if (_c) ctrl.init(_c);
