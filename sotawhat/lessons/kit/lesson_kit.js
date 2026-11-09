// lesson_kit.js — base of every three.js scene of a sotawhat lesson (copied to data/lessons/_kit; do not edit per lesson).
// The scene module exports `build(kit)` and returns `{ update(t) }`, a pure function of the time t in seconds.
// Capture (?capture=1): capture.py calls __lesson.renderAt(t) frame by frame and __lesson.check(t) at the end of
// each sentence. Interactive (the /aulas page): play/pause with the narration, timeline and free orbit.
import * as THREE from 'three';
import { OrbitControls } from './OrbitControls.js';

export const palette = {
  text: '#f2f2f2', muted: '#9aa4b2', blue: '#4ea1ff', orange: '#ffb74d', green: '#7bd389', purple: '#b39ddb',
  red: '#ef6f6c', yellow: '#ffd54f', gray: '#8a94a6', teal: '#4dd0c4', skin: '#c99a7a', bone: '#e8e1d0', organ: '#c96f6f',
};

function wrap(text, width = 62) {
  const lines = []; let line = '';
  for (const w of text.split(/\s+/)) {
    if ((line + ' ' + w).trim().length > width && line) { lines.push(line); line = w; } else line = (line + ' ' + w).trim();
  }
  if (line) lines.push(line);
  const chunks = [];
  for (let i = 0; i < lines.length; i += 2) chunks.push(lines.slice(i, i + 2).join('\n'));
  return chunks.length ? chunks : [''];
}

const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));

export async function start(build) {
  const capture = new URLSearchParams(location.search).has('capture');
  document.body.classList.toggle('capture', capture);
  const spec = await (await fetch('./scene.json')).json();
  let acc = 0;
  const beats = spec.beats.map((b) => {
    const out = { text: b.text, start: acc, end: acc + b.duration, duration: b.duration, chunks: wrap(b.text) };
    acc += b.duration; return out;
  });
  const duration = acc;
  const canvas = document.getElementById('c');
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1); renderer.setSize(1920, 1080, false);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  const scene = new THREE.Scene(); scene.background = new THREE.Color('#0f141a');
  const camera = new THREE.PerspectiveCamera(40, 16 / 9, 0.1, 500); camera.position.set(0, 3, 12); camera.lookAt(0, 0, 0);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x2b3542, 1.3));
  const sun = new THREE.DirectionalLight(0xffffff, 2.0); sun.position.set(5, 8, 6); scene.add(sun);
  const labels = [];

  const kit = {
    THREE, scene, camera, beats, duration, palette, clamp,
    /** 0 → 1 during the first `share` of sentence i (before it: 0, after it: 1). */
    progress(t, i, share = 0.6) { const b = beats[Math.min(i, beats.length - 1)]; return clamp((t - b.start) / Math.max(0.001, b.duration * share)); },
    ease(x) { x = clamp(x); return x < 0.5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2; },
    lerp(a, b, x) { return a + (b - a) * x; },
    /** A seeded random generator (the same numbers in every frame): const rnd = kit.random(7); rnd() → [0, 1). */
    random(seed = 1) { let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; },
    /** A text label that always faces the camera; `height` in world units. */
    label(text, { height = 0.42, color = palette.text } = {}) {
      const c = document.createElement('canvas'); const ctx = c.getContext('2d'); const px = 64;
      ctx.font = `600 ${px}px "Segoe UI", sans-serif`;
      c.width = Math.ceil(ctx.measureText(text).width) + 28; c.height = px + 26;
      ctx.font = `600 ${px}px "Segoe UI", sans-serif`; ctx.fillStyle = 'rgba(15,20,26,0.55)'; ctx.fillRect(0, 0, c.width, c.height);
      ctx.fillStyle = color; ctx.textBaseline = 'middle'; ctx.fillText(text, 14, c.height / 2);
      const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace;
      const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false }));
      sprite.scale.set(height * c.width / c.height, height, 1); sprite.renderOrder = 10; sprite.userData.label = text;
      labels.push(sprite); return sprite;
    },
    /** Sets the opacity of an object and all its materials (0 hides it). */
    fade(obj, alpha) {
      obj.visible = alpha > 0.01;
      obj.traverse((o) => { const mats = o.material ? (Array.isArray(o.material) ? o.material : [o.material]) : [];
        for (const m of mats) { if (m.userData.baseOpacity === undefined) m.userData.baseOpacity = m.opacity; m.transparent = true; m.opacity = m.userData.baseOpacity * alpha; } });
    },
  };

  const user = build(kit);
  const sub = document.getElementById('sub');
  let freeCam = null;
  function subtitle(t) {
    const b = beats.find((x) => t >= x.start && t < x.end) || beats[beats.length - 1];
    const total = b.chunks.reduce((n, c) => n + c.length, 0); let edge = b.start;
    for (const c of b.chunks) { edge += b.duration * c.length / total; if (t < edge) return c; }
    return b.chunks[b.chunks.length - 1];
  }
  function renderAt(t) {
    user.update(t);
    renderer.render(scene, freeCam || camera);
    const text = subtitle(t); if (sub.textContent !== text) sub.textContent = text;
  }
  function shown(o) { for (let p = o; p; p = p.parent) if (!p.visible) return false; return o.material.opacity > 0.05; }
  /** Layout problems at time t: labels off screen or under the subtitles, and labels over each other. */
  function check(t) {
    user.update(t); scene.updateMatrixWorld(true); camera.updateMatrixWorld(true);
    const issues = []; const boxes = [];
    const halfH = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
    for (const s of labels) {
      if (!shown(s) || !s.parent) continue;
      const world = new THREE.Vector3(); s.getWorldPosition(world);
      const dist = world.distanceTo(camera.position);
      const ndc = world.clone().project(camera);
      if (ndc.z > 1) { issues.push(`o rótulo "${s.userData.label}" está atrás da câmera`); continue; }
      const w = s.scale.x / (dist * halfH * camera.aspect), h = s.scale.y / (dist * halfH);
      const box = { name: s.userData.label, l: ndc.x - w / 2, r: ndc.x + w / 2, b: ndc.y - h / 2, t: ndc.y + h / 2 };
      if (box.l < -0.97 || box.r > 0.97 || box.t > 0.97) issues.push(`o rótulo "${box.name}" sai da tela (aproxime a câmera ou mova o rótulo)`);
      else if (box.b < -0.66) issues.push(`o rótulo "${box.name}" fica sob as legendas (suba-o ou afaste a câmera)`);
      boxes.push(box);
    }
    for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) {
      const a = boxes[i], b = boxes[j];
      const w = Math.min(a.r, b.r) - Math.max(a.l, b.l), h = Math.min(a.t, b.t) - Math.max(a.b, b.b);
      const smaller = Math.min((a.r - a.l) * (a.t - a.b), (b.r - b.l) * (b.t - b.b));
      if (w > 0 && h > 0 && w * h > 0.3 * smaller) issues.push(`os rótulos "${a.name}" e "${b.name}" se sobrepõem`);
    }
    return issues;
  }
  window.__lesson = { duration, beats: beats.map((b) => ({ start: b.start, end: b.end })), renderAt, check };
  renderAt(0);
  if (!capture) interactive(renderAt, duration, camera, canvas, (cam) => { freeCam = cam; });
  window.__ready = true;
}

function interactive(renderAt, duration, camera, canvas, setFree) {
  const ui = document.getElementById('ui');
  const audio = new Audio('./audio.wav'); audio.preload = 'auto';
  const play = Object.assign(document.createElement('button'), { textContent: '▶ ouvir', type: 'button' });
  const range = Object.assign(document.createElement('input'), { type: 'range', min: 0, max: duration, step: 0.01, value: 0 });
  const clock = document.createElement('span');
  const orbit = Object.assign(document.createElement('label'), { innerHTML: '<input type="checkbox"> girar livremente' });
  ui.append(play, range, clock, orbit);
  let t = 0; let controls = null;
  const fmt = (x) => `${Math.floor(x / 60)}:${String(Math.floor(x % 60)).padStart(2, '0')}`;
  play.onclick = () => { if (audio.paused) { audio.currentTime = t; audio.play(); play.textContent = '❚❚ pausar'; } else { audio.pause(); play.textContent = '▶ ouvir'; } };
  range.oninput = () => { t = Number(range.value); audio.currentTime = t; };
  orbit.querySelector('input').onchange = (ev) => {
    if (ev.target.checked) { const cam = camera.clone(); controls = new OrbitControls(cam, canvas); controls.enableDamping = true; setFree(cam); }
    else { controls?.dispose(); controls = null; setFree(null); }
  };
  audio.onended = () => { play.textContent = '▶ ouvir'; };
  function loop() {
    if (!audio.paused) { t = Math.min(duration, audio.currentTime); range.value = t; }
    controls?.update();
    renderAt(t); clock.textContent = `${fmt(t)} / ${fmt(duration)}`;
    requestAnimationFrame(loop);
  }
  loop();
}
