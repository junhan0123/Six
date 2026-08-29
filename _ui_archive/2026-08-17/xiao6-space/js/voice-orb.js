/* ═══════════════════════════════════════════════════════════════════
   SIX NEXUS · voice-orb.js
   3D 语音反应球（Three.js + GLSL）· 组件化自 https://github.com/aguscruiz/voiceorb
   状态：idle / listening / thinking / speaking · 麦克风 FFT 音响应激
   配色改为 NEXUS 科技青紫系
   ═══════════════════════════════════════════════════════════════════ */
(function (global) {
  'use strict';

  var scene, camera, renderer, orbLayers = [];
  var audioContext, analyser, microphone, dataArray;
  var isActive = false;        // 麦克风已开启
  var manualOverride = true;   // true=手动状态，false=音响应激
  var currentState = 'idle';
  var targetScale = 1.0, currentScale = 1.0;
  var speakingCadence = { time: 0, intensity: 0, nextChange: 0 };
  var listeningDemo = { time: 0, intensity: 0, nextChange: 0, pattern: [] };
  var rafId = null;
  var container = null;

  var states = {
    idle: {
      layers: [
        { color: 0x22d3ee, opacity: 0.16, scale: 1.0, rotationSpeed: { x: 0.001, y: 0.002, z: 0 } },
        { color: 0x3b82f6, opacity: 0.18, scale: 0.85, rotationSpeed: { x: -0.002, y: 0.003, z: 0.001 } },
        { color: 0x8b5cf6, opacity: 0.32, scale: 0.70, rotationSpeed: { x: 0.003, y: -0.002, z: -0.001 } }
      ],
      audioLevel: 0.15, audioFrequency: 0.2, timeSpeed: 0.015, pulsate: false,
      chromaticAberration: 0.8, description: '在线待命'
    },
    listening: {
      layers: [
        { color: 0x22d3ee, opacity: 0.18, scale: 1.0, rotationSpeed: { x: 0.002, y: 0.004, z: 0 } },
        { color: 0x34d399, opacity: 0.2, scale: 0.85, rotationSpeed: { x: -0.003, y: 0.005, z: 0.002 } },
        { color: 0x00e5ff, opacity: 0.38, scale: 0.70, rotationSpeed: { x: 0.004, y: -0.003, z: -0.001 } }
      ],
      audioLevel: 0.6, audioFrequency: 0.7, timeSpeed: 0.022, pulsate: true,
      pulsateMode: 'audio-reactive', pulsateMin: 0.02, pulsateMax: 0.3,
      chromaticAberration: 1.3, description: '倾听中'
    },
    thinking: {
      layers: [
        { color: 0x8b5cf6, opacity: 0.18, scale: 0.85, rotationSpeed: { x: 0.003, y: 0.003, z: 0 } },
        { color: 0xa78bfa, opacity: 0.2, scale: 0.72, rotationSpeed: { x: -0.004, y: 0.004, z: 0.002 } },
        { color: 0x7c3aed, opacity: 0.36, scale: 0.60, rotationSpeed: { x: 0.005, y: -0.004, z: -0.002 } }
      ],
      audioLevel: 0.45, audioFrequency: 0.5, timeSpeed: 0.022, pulsate: true,
      pulsateMode: 'thinking', pulsateMin: 0.0, pulsateMax: 0.16,
      chromaticAberration: 0.9, description: '思考中'
    },
    speaking: {
      layers: [
        { color: 0xf472b6, opacity: 0.18, scale: 1.0, rotationSpeed: { x: 0.004, y: 0.005, z: 0 } },
        { color: 0xec4899, opacity: 0.2, scale: 0.85, rotationSpeed: { x: -0.005, y: 0.006, z: 0.003 } },
        { color: 0xfb7185, opacity: 0.36, scale: 0.70, rotationSpeed: { x: 0.006, y: -0.005, z: -0.002 } }
      ],
      audioLevel: 0.8, audioFrequency: 0.9, timeSpeed: 0.027, pulsate: true,
      pulsateMode: 'cadence', pulsateMin: 0.05, pulsateMax: 0.24,
      chromaticAberration: 1.5, description: '说话中'
    }
  };

  var vertexShader = `
    varying vec3 vNormal;
    varying vec3 vPosition;
    varying vec2 vUv;
    uniform float time;
    uniform float audioLevel;
    uniform float layerOffset;
    vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
    vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
    vec4 permute(vec4 x) { return mod289(((x*34.0)+1.0)*x); }
    vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }
    float snoise(vec3 v) {
      const vec2 C = vec2(1.0/6.0, 1.0/3.0);
      const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
      vec3 i  = floor(v + dot(v, C.yyy));
      vec3 x0 = v - i + dot(i, C.xxx);
      vec3 g = step(x0.yzx, x0.xyz);
      vec3 l = 1.0 - g;
      vec3 i1 = min(g.xyz, l.zxy);
      vec3 i2 = max(g.xyz, l.zxy);
      vec3 x1 = x0 - i1 + C.xxx;
      vec3 x2 = x0 - i2 + C.yyy;
      vec3 x3 = x0 - D.yyy;
      i = mod289(i);
      vec4 p = permute(permute(permute(
          i.z + vec4(0.0, i1.z, i2.z, 1.0))
          + i.y + vec4(0.0, i1.y, i2.y, 1.0))
          + i.x + vec4(0.0, i1.x, i2.x, 1.0));
      float n_ = 0.142857142857;
      vec3 ns = n_ * D.wyz - D.xzx;
      vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
      vec4 x_ = floor(j * ns.z);
      vec4 y_ = floor(j - 7.0 * x_);
      vec4 x = x_ *ns.x + ns.yyyy;
      vec4 y = y_ *ns.x + ns.yyyy;
      vec4 h = 1.0 - abs(x) - abs(y);
      vec4 b0 = vec4(x.xy, y.xy);
      vec4 b1 = vec4(x.zw, y.zw);
      vec4 s0 = floor(b0)*2.0 + 1.0;
      vec4 s1 = floor(b1)*2.0 + 1.0;
      vec4 sh = -step(h, vec4(0.0));
      vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy;
      vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww;
      vec3 p0 = vec3(a0.xy, h.x);
      vec3 p1 = vec3(a0.zw, h.y);
      vec3 p2 = vec3(a1.xy, h.z);
      vec3 p3 = vec3(a1.zw, h.w);
      vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2,p2), dot(p3,p3)));
      p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
      vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
      m = m * m;
      return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
    }
    void main() {
      vUv = uv;
      vNormal = normalize(normalMatrix * normal);
      vec3 pos = position;
      float wave1 = sin(pos.y * 2.5 + time * 1.5 + layerOffset) * cos(pos.x * 2.0 - time * 1.2);
      float wave2 = sin(pos.x * 3.0 - time * 1.8 + layerOffset) * cos(pos.z * 2.5 + time * 1.5);
      float wave3 = sin(pos.z * 2.8 + time * 1.6 + layerOffset) * cos(pos.y * 2.3 - time * 1.3);
      float noise1 = snoise(pos * 1.2 + time * 0.3 + layerOffset);
      float noise2 = snoise(pos * 2.0 - time * 0.2 + layerOffset * 0.5);
      float distortion = (wave1 + wave2 + wave3) * 0.008;
      distortion += (noise1 * 0.008 + noise2 * 0.007);
      distortion *= (0.3 + audioLevel * 0.6);
      pos = pos + normal * distortion;
      vPosition = pos;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
    }
  `;

  var fragmentShader = `
    varying vec3 vNormal;
    varying vec3 vPosition;
    varying vec2 vUv;
    uniform vec3 sphereColor;
    uniform float opacity;
    uniform float time;
    uniform float chromaticAberration;
    vec3 rgb2hsv(vec3 c) {
      vec4 K = vec4(0.0, -1.0 / 3.0, 2.0 / 3.0, -1.0);
      vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g));
      vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r));
      float d = q.x - min(q.w, q.y);
      float e = 1.0e-10;
      return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x);
    }
    vec3 hsv2rgb(vec3 c) {
      vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
      vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
      return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
    }
    void main() {
      vec3 viewDirection = normalize(cameraPosition - vPosition);
      float fresnel = pow(1.0 - abs(dot(viewDirection, normalize(vNormal))), 2.0);
      vec3 normalWorld = normalize(vNormal);
      float rainbowShift = normalWorld.x * 0.5 + normalWorld.y * 0.2 + normalWorld.z * 0.1;
      rainbowShift += sin(vPosition.x * 5.0 + time * 0.5) * 0.01;
      rainbowShift += cos(vPosition.y * 4.0 - time * 0.3) * 0.01;
      rainbowShift = fract(rainbowShift);
      vec3 rainbow = hsv2rgb(vec3(rainbowShift, 0.8, 1.0));
      vec3 hsv = rgb2hsv(sphereColor);
      float aberrationAmount = chromaticAberration * fresnel;
      vec3 hsvR = hsv;
      hsvR.x = fract(hsv.x + aberrationAmount * 0.15);
      vec3 colorR = hsv2rgb(hsvR);
      vec3 colorG = sphereColor;
      vec3 hsvB = hsv;
      hsvB.x = fract(hsv.x - aberrationAmount * 0.15);
      vec3 colorB = hsv2rgb(hsvB);
      vec3 color = vec3(colorR.r, colorG.g, colorB.b);
      float holographicIntensity = fresnel * 0.6 + 0.2;
      color = mix(color, rainbow, holographicIntensity * 0.6);
      color += fresnel * chromaticAberration * 0.15;
      float brightness = 1.0 + sin(vPosition.x * 3.0 + time) * 0.1;
      brightness += sin(vPosition.y * 2.5 - time * 0.8) * 0.1;
      float shimmer = sin(vPosition.x * 8.0 + vPosition.y * 6.0 + time * 2.0) * 0.04 + 0.96;
      brightness *= shimmer;
      color *= brightness;
      gl_FragColor = vec4(color, opacity);
    }
  `;

  function updateListeningDemo() {
    listeningDemo.time += 0.016;
    if (listeningDemo.time >= listeningDemo.nextChange) {
      listeningDemo.nextChange = listeningDemo.time + (0.3 + Math.random() * 0.6);
      listeningDemo.intensity = 0.15 + Math.random() * 0.85;
    }
    return listeningDemo.intensity * (0.6 + Math.sin(listeningDemo.time * 30) * 0.2);
  }

  function updateSpeakingCadence() {
    speakingCadence.time += 0.016;
    if (speakingCadence.time >= speakingCadence.nextChange) {
      speakingCadence.nextChange = speakingCadence.time + (0.12 + Math.random() * 0.25);
      speakingCadence.intensity = 0.2 + Math.random() * 0.8;
    }
    return speakingCadence.intensity * (0.5 + Math.sin(speakingCadence.time * 45) * 0.3);
  }

  /* ── 挂载：绑定 canvas 容器 ── */
  function mount(canvas) {
    if (container) return; // 已挂载
    container = canvas;
    if (!window.THREE) return;

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(75, 1, 0.1, 100);
    camera.position.z = 5;

    renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    resize();

    var initialState = states.idle;
    initialState.layers.forEach(function (layerConfig, index) {
      var geometry = new THREE.SphereGeometry(layerConfig.scale, 72, 72);
      var material = new THREE.ShaderMaterial({
        vertexShader: vertexShader,
        fragmentShader: fragmentShader,
        uniforms: {
          time: { value: 0 },
          audioLevel: { value: 0 },
          layerOffset: { value: index * 2.0 },
          sphereColor: { value: new THREE.Color(layerConfig.color) },
          opacity: { value: layerConfig.opacity },
          chromaticAberration: { value: initialState.chromaticAberration || 0.1 },
          cameraPosition: { value: camera.position }
        },
        transparent: true,
        side: THREE.DoubleSide,
        blending: THREE.NormalBlending,
        depthWrite: false
      });
      var sphere = new THREE.Mesh(geometry, material);
      sphere.userData = { baseScale: layerConfig.scale, rotationSpeed: layerConfig.rotationSpeed, layerIndex: index };
      scene.add(sphere);
      orbLayers.push(sphere);
    });

    var ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
    scene.add(ambientLight);
    var pointLight1 = new THREE.PointLight(0x22d3ee, 0.7, 100);
    pointLight1.position.set(5, 5, 5);
    scene.add(pointLight1);
    var pointLight2 = new THREE.PointLight(0x8b5cf6, 0.6, 100);
    pointLight2.position.set(-4, -3, 4);
    scene.add(pointLight2);

    window.addEventListener('resize', resize);
    animate();
  }

  function resize() {
    if (!container || !renderer) return;
    var w = container.clientWidth || container.parentElement.clientWidth || 320;
    var h = container.clientHeight || container.parentElement.clientHeight || 320;
    renderer.setSize(w, h, false);
    if (camera) {
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    }
  }

  function setState(name) {
    if (!states[name]) return;
    if (currentState === 'speaking' && name !== 'speaking') { /* stop tts */ }
    currentState = name;
    var state = states[name];
    orbLayers.forEach(function (layer, index) {
      var cfg = state.layers[index];
      if (!cfg) return;
      layer.material.uniforms.sphereColor.value.setHex(cfg.color);
      layer.material.uniforms.opacity.value = cfg.opacity;
      layer.userData.rotationSpeed = cfg.rotationSpeed;
      layer.userData.baseScale = cfg.scale;
    });
  }

  /* ── 麦克风音响应激 ── */
  function startMic() {
    if (isActive) return Promise.resolve();
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      return Promise.reject(new Error('no getUserMedia'));
    }
    return navigator.mediaDevices.getUserMedia({ audio: true })
      .then(function (stream) {
        audioContext = audioContext || new (window.AudioContext || window.webkitAudioContext)();
        microphone = audioContext.createMediaStreamSource(stream);
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        dataArray = new Uint8Array(analyser.frequencyBinCount);
        microphone.connect(analyser);
        isActive = true;
        manualOverride = false;
        setState('listening');
      })
      .catch(function () { throw new Error('mic denied'); });
  }

  function stopMic() {
    isActive = false;
    manualOverride = true;
    if (microphone && microphone.disconnect) { try { microphone.disconnect(); } catch (e) {} }
    microphone = null;
    analyser = null;
    if (audioContext && audioContext.state === 'running') { try { audioContext.suspend(); } catch (e) {} }
    setState('idle');
  }

  function animate() {
    rafId = requestAnimationFrame(animate);
    var state = states[currentState];
    var audioLevel = 0, audioFrequency = 0;

    if (isActive && analyser && dataArray && !manualOverride) {
      analyser.getByteFrequencyData(dataArray);
      var sum = 0;
      for (var i = 0; i < dataArray.length; i++) sum += dataArray[i];
      audioLevel = sum / dataArray.length / 255;
      audioFrequency = dataArray.slice(10, 40).reduce(function (a, b) { return a + b; }, 0) / 30 / 255;
    } else {
      audioLevel = state.audioLevel;
      audioFrequency = state.audioFrequency;
    }

    if (state.pulsate) {
      var volumeScale;
      if (state.pulsateMode === 'audio-reactive') {
        if (isActive && analyser && dataArray) {
          volumeScale = Math.min(1.0, audioLevel * 2.5);
          if (volumeScale < 0.1) volumeScale = volumeScale * 2;
        } else {
          volumeScale = updateListeningDemo();
        }
        targetScale = 1.0 + state.pulsateMin + (volumeScale * (state.pulsateMax - state.pulsateMin));
      } else if (state.pulsateMode === 'thinking') {
        var tp = (Math.sin(Date.now() * 0.0015) + 1.0) / 2.0;
        targetScale = 1.0 + state.pulsateMin + (tp * (state.pulsateMax - state.pulsateMin));
      } else if (state.pulsateMode === 'cadence') {
        var ci = updateSpeakingCadence();
        targetScale = 1.0 + state.pulsateMin + (ci * (state.pulsateMax - state.pulsateMin));
      }
      var smoothing = (isActive && analyser && state.pulsateMode === 'audio-reactive') ? 0.25 : 0.15;
      currentScale += (targetScale - currentScale) * smoothing;
    } else {
      targetScale = 1.0;
      currentScale += (targetScale - currentScale) * 0.1;
    }

    orbLayers.forEach(function (layer, index) {
      var cfg = state.layers[index];
      if (!cfg) return;
      layer.material.uniforms.time.value += state.timeSpeed;
      layer.material.uniforms.audioLevel.value = audioLevel;
      layer.material.uniforms.chromaticAberration.value = state.chromaticAberration || 0.1;

      var rs = layer.userData.rotationSpeed;
      layer.rotation.x += rs.x + audioFrequency * 0.004;
      layer.rotation.y += rs.y + audioLevel * 0.008;
      layer.rotation.z += rs.z;

      var s = layer.userData.baseScale * currentScale;
      layer.scale.set(s, s, s);
      layer.material.opacity = cfg.opacity * (1.0 + audioLevel * 0.15);
    });

    if (renderer && scene && camera) renderer.render(scene, camera);
  }

  function destroy() {
    if (rafId) cancelAnimationFrame(rafId);
    if (renderer) { try { renderer.dispose(); } catch (e) {} }
    if (microphone) { try { microphone.disconnect(); } catch (e) {} }
    scene = camera = renderer = null;
    orbLayers = [];
    container = null;
  }

  global.ZZVoiceOrb = {
    mount: mount,
    setState: setState,
    startMic: startMic,
    stopMic: stopMic,
    destroy: destroy,
    isMicActive: function () { return isActive; }
  };
})(window);
