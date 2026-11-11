/* sotawhat lessons · HyperFrames kit · the 3D templates (three.js): vectors3d and volume3d.
   vectors3d: vectors from a common origin in a real 3D space.
   Drawn from the timeline time only (hf-seek gives the time of the whole video; `offset` is the scene start), so
   every frame renders on its own. The dot products shown are computed here from the vectors of the storyboard,
   and an arc between the query and each key shows the angle that the dot product measures. */
import * as THREE from "../lib/three.module.js";
import { MarchingCubes } from "../lib/MarchingCubes.js";

const W = 1920, H = 1080, FOV = 30;
const ease = (x) => 1 - Math.pow(1 - Math.max(0, Math.min(1, x)), 3);
const ramp = (t, at, d) => ease((t - at) / d);

function glowTexture() {
  const c = document.createElement("canvas");
  c.width = c.height = 128;
  const g = c.getContext("2d"), grd = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  grd.addColorStop(0, "rgba(255,255,255,1)"); grd.addColorStop(0.22, "rgba(255,255,255,0.5)"); grd.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = grd; g.fillRect(0, 0, 128, 128);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

function arcPoints(a, b, r, n) {      // points on the great arc from unit vector a to unit vector b, at radius r
  const out = [], angle = a.angleTo(b), axis = new THREE.Vector3().crossVectors(a, b).normalize();
  for (let i = 0; i <= n; i++) out.push(a.clone().applyAxisAngle(axis, (angle * i) / n).multiplyScalar(r));
  return out;
}

/* ---- the viewer's orbit (the interactive page): the scripted camera turned around its own target -------------
   The video never moves it (all zero), so a render is the scripted camera. On the page, dragging turns and zooms
   the same camera the overlay projects with, so the HTML labels stay on their parts. */
export const orbit = { yaw: 0, pitch: 0, zoom: 1 };
function applyOrbit(camera, target) {
  if (!orbit.yaw && !orbit.pitch && orbit.zoom === 1) return;
  const off = camera.position.clone().sub(target);
  const r = off.length() * Math.max(0.35, Math.min(2.6, orbit.zoom));
  const el = Math.max(-1.3, Math.min(1.3, Math.asin(Math.max(-1, Math.min(1, off.y / (off.length() || 1)))) + orbit.pitch));
  const az = Math.atan2(off.x, off.z) + orbit.yaw;
  camera.position.set(target.x + r * Math.cos(el) * Math.sin(az), target.y + r * Math.sin(el), target.z + r * Math.cos(el) * Math.cos(az));
  camera.lookAt(target);
  camera.updateMatrixWorld();
}
// a page that hosts several scenes seeks only the one on screen (`only`); HyperFrames never sets it
const seekOf = (id, offset, renderAt) => (e) => { if (!e.detail.only || e.detail.only === id) renderAt(e.detail.time - offset); };

export function mount3d(id, data, offset) {
  MK.fontsReady().then(() => {
    const root = MK.rootOf(id);
    const stage = MK.el("div", "mk-scene", root);
    const layer = MK.el("div", "mk-stage", stage);
    const canvas = MK.el("canvas", "mk-canvas3d", layer);
    canvas.width = W; canvas.height = H;
    const overlay = MK.el("div", "mk-stage", layer);
    const tl = gsap.timeline({ paused: true });
    const T = MK.Track(tl);
    T.init(layer, { opacity: 1, filter: "blur(0px)" });
    MK.header(T, layer, data.num, data.title);

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
    renderer.setPixelRatio(1);
    renderer.setSize(W, H, false);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(FOV, W / H, 0.1, 80);
    scene.add(new THREE.HemisphereLight(0xa8c0ff, 0x0a101e, 1.0));
    const key = new THREE.DirectionalLight(0xffe6c8, 2.4); key.position.set(3, 6, 5); scene.add(key);
    const rim = new THREE.DirectionalLight(0x6fa8ff, 1.6); rim.position.set(-5, 2, -4); scene.add(rim);

    // the vectors, scaled so that the longest one is 2.4 units long
    const vecs = data.vectors.map((v) => ({ ...v, raw: new THREE.Vector3(v.x, v.y, v.z) }));
    const maxLen = Math.max(...vecs.map((v) => v.raw.length())) || 1;
    const k = 2.4 / maxLen;
    const query = vecs.find((v) => v.role === "query") || vecs[0];
    const qhat = query.raw.clone().normalize();

    // frame the origin and every tip: the camera distance fits their bounding sphere in the picture
    const pts = [new THREE.Vector3(0, 0, 0), ...vecs.map((v) => v.raw.clone().multiplyScalar(k))];
    const box = new THREE.Box3().setFromPoints(pts);
    const center = box.getCenter(new THREE.Vector3());
    const radius = Math.max(...pts.map((p) => p.distanceTo(center))) + 0.35;
    // the content must fit between the header and the captions (about 700 of the 1080 px): fit it in 0.72 of
    // the frame height and raise the picture by 40 px with a view offset
    const dist = radius / Math.sin(THREE.MathUtils.degToRad(FOV / 2)) / 0.72;
    camera.setViewOffset(W, H, 0, 40, W, H);
    scene.fog = new THREE.Fog(0x0a101e, dist + 1.5, dist + 9);

    // floor grid under the origin and three faint axes give the space a scale
    const grid = new THREE.GridHelper(9, 18, 0x2f4470, 0x1b2a49);
    grid.position.set(center.x, -0.45, center.z);
    grid.material.transparent = true; grid.material.opacity = 0.2;
    scene.add(grid);
    const axisMat = new THREE.LineBasicMaterial({ color: 0x6b7c99, transparent: true, opacity: 0.25 });
    for (const d of [[1, 0, 0], [0, 1, 0], [0, 0, 1]]) {
      const g = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), new THREE.Vector3(...d).multiplyScalar(2.6)]);
      scene.add(new THREE.Line(g, axisMat));
    }
    const glow = glowTexture();
    const origin = new THREE.Mesh(new THREE.SphereGeometry(0.08, 28, 18),
      new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xffffff, emissiveIntensity: 0.7 }));
    scene.add(origin);
    const originGlow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glow, color: 0xbfd4ff, blending: THREE.AdditiveBlending,
      transparent: true, depthWrite: false, opacity: 0.7 }));
    originGlow.scale.setScalar(0.8); scene.add(originGlow);

    const up = new THREE.Vector3(0, 1, 0);
    vecs.forEach((v, i) => {
      const color = new THREE.Color(MK.ROLE[v.role] || MK.ROLE.neutral);
      const isQ = v === query;
      const mat = new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 0.5, roughness: 0.42, metalness: 0.08, transparent: true });
      const r = isQ ? 0.062 : 0.048;
      const shaft = new THREE.Mesh(new THREE.CylinderGeometry(r, r, 1, 24), mat);
      shaft.geometry.translate(0, 0.5, 0);
      const cone = new THREE.Mesh(new THREE.ConeGeometry(isQ ? 0.16 : 0.13, 0.34, 32), mat);
      const g = new THREE.Group();
      g.add(shaft, cone);
      const dir = v.raw.clone().normalize();
      g.quaternion.setFromUnitVectors(up, dir);
      scene.add(g);
      const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: glow, color, blending: THREE.AdditiveBlending, transparent: true, depthWrite: false, opacity: 0 }));
      scene.add(sprite);
      let arc = null;
      if (!isQ) {
        const arcMat = new THREE.MeshBasicMaterial({ color: 0xffd54a, transparent: true, opacity: 0 });
        const curve = new THREE.CatmullRomCurve3(arcPoints(qhat, dir, 0.7 + 0.16 * i, 40));
        arc = new THREE.Mesh(new THREE.TubeGeometry(curve, 48, 0.018, 8, false), arcMat);
        scene.add(arc);
      }
      const tag = MK.el("div", `mk-tag3d mk-r-${v.role}`, overlay, MK.esc(v.label));
      const dot = v.raw.dot(query.raw);
      const score = MK.el("div", "mk-score3d", overlay, `q·k = ${MK.num(dot, Math.abs(dot - Math.round(dot)) < 0.05 ? 0 : 1)}`);
      tag.style.opacity = "0"; score.style.opacity = "0";
      Object.assign(v, { dir, mat, shaft, cone, g, sprite, arc, tag, score, dot, len: v.raw.length() * k,
        tw: tag.offsetWidth, th: tag.offsetHeight, sw: score.offsetWidth, sh: score.offsetHeight,
        showAt: Infinity, scoreAt: Infinity, level: [[0, 1]], glowLevel: [[0, 0.35]], pulses: [] });
    });

    // schedule
    const note = MK.notes({ T, layer: overlay, area: { y1: 862 } });
    for (const a of data.actions) {
      const ids = a.ids.length ? a.ids : vecs.map((v) => v.id);
      const sel = vecs.filter((v) => ids.includes(v.id));
      if (a.do === "show") sel.forEach((v, i) => { v.showAt = Math.min(v.showAt, a.t + i * 0.3); });
      else if (a.do === "score" || a.do === "project") sel.filter((v) => v !== query).forEach((v, i) => { v.scoreAt = Math.min(v.scoreAt, a.t + i * 0.35); });
      else if (a.do === "focus") vecs.forEach((v) => {
        const on = ids.includes(v.id) || v === query;
        v.level.push([a.t, on ? 1 : 0.22]); v.glowLevel.push([a.t, ids.includes(v.id) ? 1 : 0.2]);
      });
      else if (a.do === "unfocus") vecs.forEach((v) => { v.level.push([a.t, 1]); v.glowLevel.push([a.t, 0.35]); });
      else if (a.do === "dim") sel.forEach((v) => { v.level.push([a.t, 0.2]); v.glowLevel.push([a.t, 0]); });
      else if (a.do === "pulse") sel.forEach((v) => v.pulses.push(a.t));
      else if (a.do === "note") note(a, null, "info");
    }
    vecs.forEach((v) => { if (v.showAt === Infinity) v.showAt = 0.6; });
    const levelAt = (track, t) => {      // eased steps through (time, level) pairs
      let val = track[0][1];
      for (let i = 1; i < track.length; i++) {
        const [at, to] = track[i];
        if (t <= at) break;
        val = val + (to - val) * ease((t - at) / 0.45);
      }
      return val;
    };
    // the camera angle where the vectors look most apart on screen (largest smallest angle between them)
    const phi = 0.42;
    const spreadAt = (theta) => {
      const eye = new THREE.Vector3(Math.cos(phi) * Math.sin(theta), Math.sin(phi), Math.cos(phi) * Math.cos(theta));
      const right = new THREE.Vector3().crossVectors(new THREE.Vector3(0, 1, 0), eye).normalize();
      const upv = new THREE.Vector3().crossVectors(eye, right).normalize();
      const angs = vecs.map((v) => Math.atan2(v.raw.clone().normalize().dot(upv), v.raw.clone().normalize().dot(right)));
      const lens = vecs.map((v) => { const d = v.raw.clone().normalize(); return Math.hypot(d.dot(upv), d.dot(right)); });
      let best = Infinity;
      for (let i = 0; i < angs.length; i++) for (let j = i + 1; j < angs.length; j++) {
        let d = Math.abs(angs[i] - angs[j]); if (d > Math.PI) d = 2 * Math.PI - d;
        best = Math.min(best, d);
      }
      return best * Math.min(...lens);           // vectors pointing at the camera look short: avoid them
    };
    let theta0 = 0, bestSpread = -1;
    for (let i = 0; i < 72; i++) { const th = (i / 72) * Math.PI * 2, sp = spreadAt(th); if (sp > bestSpread) { bestSpread = sp; theta0 = th; } }
    theta0 -= 0.12;
    const tmp = new THREE.Vector3();
    const toScreen = (p) => { tmp.copy(p).project(camera); return { x: (tmp.x + 1) / 2 * W, y: (1 - tmp.y) / 2 * H }; };

    function renderAt(t) {
      const tt = Math.max(0, Math.min(data.dur, t));
      const theta = theta0 + 0.24 * (tt / data.dur), r = dist * (1.03 - 0.06 * ease(tt / data.dur));
      camera.position.set(center.x + r * Math.cos(phi) * Math.sin(theta), center.y + r * Math.sin(phi),
        center.z + r * Math.cos(phi) * Math.cos(theta));
      camera.lookAt(center.x, center.y + 0.1, center.z);
      camera.updateMatrixWorld();
      applyOrbit(camera, new THREE.Vector3(center.x, center.y + 0.1, center.z));
      const s0 = toScreen(new THREE.Vector3(0, 0, 0));
      const boxes = [];
      for (const v of vecs) {
        const grow = ramp(tt, v.showAt, 0.9), lvl = levelAt(v.level, tt);
        let pulse = 0;
        for (const p of v.pulses) { const x = (tt - p) / 0.9; if (x > 0 && x < 1) pulse = Math.max(pulse, Math.sin(Math.PI * x)); }
        const L = Math.max(0.0001, v.len * grow);
        v.g.visible = grow > 0.001;
        v.shaft.scale.set(1, Math.max(0.0001, L - 0.3), 1);
        v.cone.position.set(0, Math.max(0.17, L - 0.17), 0);
        v.mat.opacity = lvl;
        v.mat.emissiveIntensity = 0.42 + 1.0 * pulse + 0.3 * levelAt(v.glowLevel, tt);
        v.sprite.position.copy(v.dir).multiplyScalar(L);
        v.sprite.material.opacity = grow * lvl * (0.3 + 0.7 * Math.max(levelAt(v.glowLevel, tt), pulse));
        v.sprite.scale.setScalar(0.55 + 0.7 * pulse);
        if (v.arc) v.arc.material.opacity = 0.85 * ramp(tt, v.scoreAt, 0.6) * lvl;
        // the label sits beyond the tip, along the vector as seen on screen
        const s1 = toScreen(v.dir.clone().multiplyScalar(v.len));
        const dx = s1.x - s0.x, dy = s1.y - s0.y, n = Math.hypot(dx, dy) || 1;
        const hasScore = v.scoreAt < Infinity;
        const bw = Math.max(v.tw, hasScore ? v.sw : 0), bh = v.th + (hasScore ? v.sh + 8 : 0);
        const reach = 0.5 * Math.hypot(bw * dx / n, bh * dy / n) + 26;
        boxes.push({ v, x: s1.x + dx / n * reach - bw / 2, y: s1.y + dy / n * reach - bh / 2, w: bw, h: bh, lvl });
      }
      // labels never cover each other: the lower one (in screen order) moves down until it is free
      boxes.sort((a, b) => a.y - b.y);
      for (let i = 1; i < boxes.length; i++) for (let j = 0; j < i; j++) {
        const a = boxes[j], b = boxes[i];
        if (a.x < b.x + b.w + 8 && b.x < a.x + a.w + 8 && a.y < b.y + b.h + 8 && b.y < a.y + a.h + 8) b.y = a.y + a.h + 10;
      }
      for (const b of boxes) {
        const v = b.v, x = Math.max(130, Math.min(W - 130 - b.w, b.x)), y = Math.max(150, Math.min(860 - b.h, b.y));
        v.tag.style.left = (x + (b.w - v.tw) / 2).toFixed(1) + "px"; v.tag.style.top = y.toFixed(1) + "px";
        v.tag.style.opacity = (ramp(tt, v.showAt + 0.55, 0.4) * Math.max(b.lvl, 0.35)).toFixed(3);
        v.score.style.left = (x + (b.w - v.sw) / 2).toFixed(1) + "px"; v.score.style.top = (y + v.th + 8).toFixed(1) + "px";
        v.score.style.opacity = (ramp(tt, v.scoreAt, 0.45) * Math.max(b.lvl, 0.35)).toFixed(3);
      }
      renderer.render(scene, camera);
    }
    window.addEventListener("hf-seek", seekOf(id, offset, renderAt));
    renderAt(0);
    MK.exit(T, layer, data.dur);
    tl.set({}, {}, data.dur);
    window.__timelines = window.__timelines || {};
    window.__timelines[id] = tl;
  });
}

/* ---- volume3d: a synthetic CT/MRI volume (never a real patient) -------------------------------------------------
   One implicit field defines the organ (anisotropic Gaussian blobs, iso 0.5) and the finding. The slices are cuts
   of that field and the 3D surface is its marching-cubes mesh, so what the slices show and the surface agree.
   Body coordinates: x left–right, y foot–head, z back–front, all in [-1, 1]. */
const ORGANS = {   // [cx, cy, cz, sx, sy, sz, weight]
  "pulmão": [[-0.46, 0.16, 0.02, 0.3, 0.5, 0.42, 1], [-0.47, -0.32, 0.04, 0.33, 0.34, 0.46, 1], [-0.4, 0.58, -0.02, 0.2, 0.24, 0.28, 1],
    [0.46, 0.16, 0.0, 0.27, 0.5, 0.4, 1], [0.48, -0.32, -0.02, 0.3, 0.32, 0.43, 1], [0.4, 0.58, -0.04, 0.19, 0.24, 0.27, 1]],
  "fígado": [[-0.3, 0.04, 0.06, 0.46, 0.36, 0.52, 1], [0.1, 0.16, 0.16, 0.34, 0.25, 0.38, 1], [0.42, 0.24, 0.24, 0.22, 0.17, 0.26, 0.9]],
  "cérebro": [[-0.3, 0.1, 0.02, 0.4, 0.46, 0.7, 1], [0.3, 0.1, 0.02, 0.4, 0.46, 0.7, 1], [0, -0.5, -0.42, 0.42, 0.2, 0.28, 0.9]],
  "rim": [[-0.5, 0.34, -0.36, 0.17, 0.27, 0.16, 1], [-0.57, 0.0, -0.4, 0.2, 0.24, 0.18, 1], [-0.5, -0.34, -0.36, 0.17, 0.27, 0.16, 1],
    [0.5, 0.3, -0.36, 0.17, 0.27, 0.16, 1], [0.57, -0.04, -0.4, 0.2, 0.24, 0.18, 1], [0.5, -0.38, -0.36, 0.17, 0.27, 0.16, 1]],
  "coração": [[0.06, 0.1, 0.16, 0.42, 0.38, 0.38, 1], [0.32, -0.34, 0.3, 0.24, 0.24, 0.24, 0.95], [-0.14, 0.46, 0.0, 0.28, 0.2, 0.28, 0.9]],
  "corpo": [[0, 0.06, 0.05, 0.46, 0.55, 0.42, 1], [0.24, -0.28, 0.12, 0.28, 0.26, 0.28, 0.9]],
};
const ORGAN_GRAY = { "pulmão": 0.06, "fígado": 0.58, "cérebro": 0.52, "rim": 0.62, "coração": 0.55, "corpo": 0.57 };
const EXT = 1.12;          // the slice image covers x, z in [-EXT, EXT]

function organField(organ) {
  const blobs = ORGANS[organ] || ORGANS["corpo"];
  const gyri = organ === "cérebro";
  return (x, y, z) => {
    let f = 0;
    for (const [cx, cy, cz, sx, sy, sz, w] of blobs) {
      const dx = (x - cx) / sx, dy = (y - cy) / sy, dz = (z - cz) / sz;
      f += w * Math.exp(-(dx * dx + dy * dy + dz * dz));
    }
    if (gyri && f > 0.3) f += 0.07 * Math.sin(15 * x) * Math.sin(13 * y + 1) * Math.sin(15 * z);
    return f;
  };
}

function inBody(organ, x, z) {      // the body section: a torso ellipse, or a head
  const a = organ === "cérebro" ? 0.84 : 1.0, b = organ === "cérebro" ? 1.0 : 0.72;
  return 1 - Math.sqrt((x / a) * (x / a) + (z / b) * (z / b));      // > 0 inside; ~ distance to the skin
}

function sliceCanvases(organ, lesion, y, seed, segColor, lesColor) {
  const N = 256, plain = document.createElement("canvas"), seg = document.createElement("canvas");
  plain.width = plain.height = seg.width = seg.height = N;
  const gp = plain.getContext("2d"), gs = seg.getContext("2d");
  const ip = gp.createImageData(N, N), is = gs.createImageData(N, N);
  const field = organField(organ), r = MK.rng(seed);
  const sc = new THREE.Color(segColor), lc = new THREE.Color(lesColor);
  const smooth = (a, b, v) => { const t = Math.max(0, Math.min(1, (v - a) / (b - a))); return t * t * (3 - 2 * t); };
  for (let j = 0; j < N; j++) {
    for (let i = 0; i < N; i++) {
      const x = -EXT + (2 * EXT * (i + 0.5)) / N, z = EXT - (2 * EXT * (j + 0.5)) / N, k = (j * N + i) * 4;
      const d = inBody(organ, x, z);
      if (d <= 0) { ip.data[k + 3] = is.data[k + 3] = 0; continue; }
      let g = 0.42 + 0.05 * (r() - 0.5);
      if (organ === "cérebro") {
        if (d < 0.07) g = 0.93;                                        // skull
        else g = 0.47;
      } else {
        if (d < 0.012) g = 0.52; else if (d < 0.075) g = 0.24;        // skin, then subcutaneous fat
        const vx = x, vz = z + 0.52;                                   // a vertebra at the back
        if (vx * vx + vz * vz < 0.018) g = 0.8;
      }
      const f = field(x, y, z), inside = smooth(0.46, 0.54, f);
      let og = ORGAN_GRAY[organ] ?? 0.56;
      if (organ === "pulmão" && r() < 0.012) og = 0.5;                 // vessels in the dark lung
      if (organ === "cérebro" && f > 0.9) og = 0.6;                    // white matter
      g = g * (1 - inside) + (og + 0.04 * (r() - 0.5)) * inside;
      let lin = 0;
      if (lesion) {
        const dx = x - lesion.x, dy = y - lesion.y, dz = z - lesion.z;
        lin = smooth(0.0, 0.2, 1 - Math.sqrt(dx * dx + dy * dy + dz * dz) / lesion.r);
        const lg = organ === "fígado" ? 0.32 : 0.74;
        g = g * (1 - lin) + lg * lin;
      }
      const v = Math.round(Math.max(0, Math.min(1, g)) * 255);
      ip.data[k] = v; ip.data[k + 1] = v; ip.data[k + 2] = Math.min(255, v + 4); ip.data[k + 3] = 245;
      const edge = inside > 0.15 && inside < 0.85 ? 1 : 0;
      const tint = Math.max(0.5 * inside, edge * 0.95);
      let R = v / 255 * (1 - tint) + sc.r * tint, G = v / 255 * (1 - tint) + sc.g * tint, B = v / 255 * (1 - tint) + sc.b * tint;
      const lt = 0.85 * lin;
      R = R * (1 - lt) + lc.r * lt; G = G * (1 - lt) + lc.g * lt; B = B * (1 - lt) + lc.b * lt;
      is.data[k] = Math.round(R * 255); is.data[k + 1] = Math.round(G * 255); is.data[k + 2] = Math.round(B * 255); is.data[k + 3] = 245;
    }
  }
  gp.putImageData(ip, 0, 0); gs.putImageData(is, 0, 0);
  return { plain, seg };
}

export function mountVolume(id, data, offset) {
  MK.fontsReady().then(() => {
    const vol = data.volume || {}, organ = ORGANS[vol.organ] ? vol.organ : "corpo";
    const N = Math.max(8, Math.min(24, vol.slices || 16));
    const root = MK.rootOf(id);
    const stage = MK.el("div", "mk-scene", root);
    const layer = MK.el("div", "mk-stage", stage);
    const canvas = MK.el("canvas", "mk-canvas3d", layer);
    canvas.width = W; canvas.height = H;
    const overlay = MK.el("div", "mk-stage", layer);
    const tl = gsap.timeline({ paused: true });
    const T = MK.Track(tl);
    T.init(layer, { opacity: 1, filter: "blur(0px)" });
    MK.header(T, layer, data.num, data.title);

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
    renderer.setPixelRatio(1);
    renderer.setSize(W, H, false);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.05;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(FOV, W / H, 0.1, 80);
    scene.add(new THREE.HemisphereLight(0xa8c0ff, 0x0a101e, 1.1));
    const key = new THREE.DirectionalLight(0xffe6c8, 2.2); key.position.set(3, 6, 5); scene.add(key);
    const rim = new THREE.DirectionalLight(0x6fa8ff, 1.8); rim.position.set(-5, 3, -4); scene.add(rim);

    // schedule from the actions
    const acts = data.actions || [];
    const first = (name) => { const a = acts.find((x) => x.do === name); return a ? a.t : Infinity; };
    let showAt = first("show"), stackAt = first("stack");
    const segmentAt = first("segment");
    const cuts = acts.filter((a) => a.do === "slice").map((a) => ({ t: a.t, v: a.value }));   // v = 0: auto (below)
    const focusLevels = [[0, 0]].concat(acts.filter((a) => a.do === "focus" || a.do === "unfocus")
      .map((a) => [a.t, a.do === "focus" ? 1 : 0]).sort((a, b) => a[0] - b[0]));
    const pulses = acts.filter((a) => a.do === "pulse").map((a) => a.t);
    let exploded = true;
    if (showAt === Infinity && stackAt === Infinity) { showAt = 0.5; exploded = false; }
    else if (showAt === Infinity) showAt = Math.max(0.3, stackAt - 1.9);
    const acquire = 0.11 * N;                       // the scanner sweeps the slices in this long

    const S = 1.25, He = exploded ? 5.0 : 2.1, Hc = 2.1, half = EXT * S;
    const seg = MK.ROLE.info, les = MK.ROLE.alert;
    const fz = organField(organ);
    const blob = (ORGANS[organ] || ORGANS["corpo"])[0];
    const lesion = vol.finding && vol.finding !== "nenhum"
      ? { x: blob[0] + 0.14 * blob[3], y: blob[1] + 0.12 * blob[4], z: blob[2] + 0.22 * blob[5], r: vol.finding === "massa" ? 0.17 : 0.1 } : null;
    const ys = Array.from({ length: N }, (_, k) => -0.92 + (1.84 * k) / (N - 1));
    for (const c of cuts) if (!(c.v > 0 && c.v <= 1)) c.v = lesion ? Math.min(1, Math.max(0, (lesion.y + 0.92) / 1.84)) : 0.5;
    const slices = ys.map((y, k) => {
      const c = sliceCanvases(organ, lesion, y, MK.hash(id) + k, seg, les);
      const mk = (cv) => {
        const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
        const m = new THREE.MeshBasicMaterial({ map: tex, transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide, toneMapped: false });
        const mesh = new THREE.Mesh(new THREE.PlaneGeometry(2 * half, 2 * half), m);
        mesh.rotation.x = -Math.PI / 2; mesh.renderOrder = k; scene.add(mesh);
        return mesh;
      };
      return { y, k, canvas: c, plain: mk(c.plain), seg: mk(c.seg) };
    });
    // the body outline: an ellipse at the top and bottom of the stack, faint verticals between them
    const ringPts = (yy) => Array.from({ length: 97 }, (_, i) => {
      const a = (i / 96) * Math.PI * 2, ea = organ === "cérebro" ? 0.84 : 1, eb = organ === "cérebro" ? 1 : 0.72;
      return new THREE.Vector3(Math.cos(a) * ea * S, yy, -Math.sin(a) * eb * S);
    });
    const lineMat = new THREE.LineBasicMaterial({ color: 0x8fa6cc, transparent: true, opacity: 0 });
    const outline = new THREE.Group();
    const topRing = new THREE.Line(new THREE.BufferGeometry().setFromPoints(ringPts(0)), lineMat);
    const botRing = new THREE.Line(new THREE.BufferGeometry().setFromPoints(ringPts(0)), lineMat);
    outline.add(topRing, botRing);
    scene.add(outline);
    // the CT gantry: a ring that sweeps along the body while the slices are acquired
    const gantry = new THREE.Mesh(new THREE.TorusGeometry(half * 1.12, 0.045, 16, 120),
      new THREE.MeshStandardMaterial({ color: seg, emissive: seg, emissiveIntensity: 0.9, transparent: true, opacity: 0 }));
    gantry.rotation.x = Math.PI / 2; scene.add(gantry);
    // the organ surface (marching cubes of the same field) and the finding
    const R = 44;
    const organMat = new THREE.MeshStandardMaterial({ color: seg, roughness: 0.36, metalness: 0.04, emissive: seg, emissiveIntensity: 0.16, transparent: true, opacity: 0 });
    const surface = new MarchingCubes(R, organMat, false, false, 90000);
    surface.isolation = 0.5;
    for (let iz = 0; iz < R; iz++) for (let iy = 0; iy < R; iy++) for (let ix = 0; ix < R; ix++) {
      const hx = (ix - R / 2) / (R / 2), hy = (iy - R / 2) / (R / 2), hz = (iz - R / 2) / (R / 2);
      surface.field[R * R * iz + R * iy + ix] = fz(hx * EXT, hy, -hz * EXT);
    }
    surface.update();
    scene.add(surface);
    let lesionMesh = null, lesionGlow = null;
    const glow = glowTexture();
    if (lesion) {
      lesionMesh = new THREE.Mesh(new THREE.SphereGeometry(1, 32, 24),
        new THREE.MeshStandardMaterial({ color: les, emissive: les, emissiveIntensity: 0.8, roughness: 0.3, transparent: true, opacity: 0,
          depthTest: false }));
      lesionMesh.renderOrder = 100;          // drawn through the organ: the finding is the point of the scene
      scene.add(lesionMesh);
      lesionGlow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glow, color: les, blending: THREE.AdditiveBlending, transparent: true, depthWrite: false, depthTest: false, opacity: 0 }));
      lesionGlow.renderOrder = 101;
      scene.add(lesionGlow);
    }
    const cutFill = new THREE.Mesh(new THREE.PlaneGeometry(2 * half, 2 * half),
      new THREE.MeshBasicMaterial({ color: seg, transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide }));
    cutFill.rotation.x = -Math.PI / 2; scene.add(cutFill);
    const cutFrame = new THREE.Line(new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(-half, 0, -half), new THREE.Vector3(half, 0, -half), new THREE.Vector3(half, 0, half),
      new THREE.Vector3(-half, 0, half), new THREE.Vector3(-half, 0, -half)]),
      new THREE.LineBasicMaterial({ color: seg, transparent: true, opacity: 0 }));
    scene.add(cutFrame);

    // 2D overlay: the modality chip, the inset with the current cut, the organ and finding tags, the notes
    const chip = MK.el("div", "mk-modality", overlay, `${MK.esc(vol.modality === "ressonância" ? "ressonância" : "tomografia")} · ${N} fatias`);
    const inset = MK.el("div", "mk-inset", overlay);
    const insetCanvas = MK.el("canvas", "", inset); insetCanvas.width = insetCanvas.height = 360;
    const insetCap = MK.el("div", "mk-inset-cap", inset, "corte axial");
    const ix = insetCanvas.getContext("2d");
    const hasCuts = cuts.length > 0, hasNotes = acts.some((a) => a.do === "note");
    const shiftX = hasCuts || hasNotes ? 240 : 0;        // the volume moves left of the right column
    const colR = W - 120;
    chip.style.left = (colR - chip.offsetWidth) + "px"; chip.style.top = "150px";
    let colY = 150 + chip.offsetHeight + 22;
    for (const a of acts) {
      if (a.do !== "note") continue;
      const n = MK.el("div", "mk-note mk-r-info", overlay, `<i></i>${MK.esc(a.text)}`);
      n.style.left = (colR - n.offsetWidth) + "px"; n.style.top = colY + "px"; colY += n.offsetHeight + 12;
      T.init(n, { opacity: 0, x: -12, filter: "blur(6px)" }); T.to(n, { opacity: 1, x: 0, filter: "blur(0px)" }, a.t, 0.45, "expo.out");
    }
    inset.style.left = (colR - 388) + "px"; inset.style.top = Math.max(290, colY + 14) + "px";
    inset.style.opacity = "0"; chip.style.opacity = "0";
    const organTag = MK.el("div", "mk-tag3d mk-r-info", overlay, MK.esc(organ));
    const lesionTag = lesion ? MK.el("div", "mk-tag3d mk-r-alert", overlay, MK.esc(vol.finding)) : null;
    organTag.style.opacity = "0"; if (lesionTag) lesionTag.style.opacity = "0";

    // framing: the camera fits the stack (taller while the slices are apart) between the header and the captions
    camera.setViewOffset(W, H, shiftX, 30, W, H);
    const fit = (h) => Math.hypot(half, h / 2, half * 0.72) / Math.sin(THREE.MathUtils.degToRad(FOV / 2)) / 0.74;
    const phi = 0.4, theta0 = Math.PI + 0.55;      // the front of the body faces -z
    const tmp = new THREE.Vector3();
    const toScreen = (p) => { tmp.copy(p).project(camera); return { x: (tmp.x + 1) / 2 * W, y: (1 - tmp.y) / 2 * H }; };
    const levelAt = (track, t) => {
      let val = track[0][1];
      for (let i = 1; i < track.length; i++) {
        const [at, to] = track[i];
        if (t <= at) break;
        val = val + (to - val) * ease((t - at) / 1.4);
      }
      return val;
    };
    let lastInset = "";

    function renderAt(t) {
      const tt = Math.max(0, Math.min(data.dur, t));
      const stacked = stackAt < Infinity ? ramp(tt, stackAt, 1.5) : (exploded ? 0 : 1);
      const height = He + (Hc - He) * stacked;
      const segP = ramp(tt, segmentAt, 1.1);
      const focusP = levelAt(focusLevels, tt);
      // camera: a slow orbit; it comes closer to the finding on focus
      const dist = fit(height) * (1 - 0.34 * focusP);
      const target = new THREE.Vector3(0, 0, 0);
      if (lesion) target.lerp(new THREE.Vector3(lesion.x * S, lesion.y * Hc / 2, -lesion.z * S), 0.7 * focusP);
      const theta = theta0 + 0.42 * (tt / data.dur);
      camera.position.set(target.x + dist * Math.cos(phi) * Math.sin(theta), target.y + dist * Math.sin(phi),
        target.z + dist * Math.cos(phi) * Math.cos(theta));
      camera.lookAt(target);
      camera.updateMatrixWorld();
      applyOrbit(camera, target);
      // the cut: the plane moves to the height of the latest slice action
      let cutV = null;
      for (let i = 0; i < cuts.length; i++) {
        if (tt < cuts[i].t) break;
        const from = i ? cuts[i - 1].v : 1, p = ramp(tt, cuts[i].t, 1.4);
        cutV = from + (cuts[i].v - from) * p;
      }
      const cutK = cutV === null ? -1 : Math.round(cutV * (N - 1));
      for (const s of slices) {
        const yWorld = s.y * height / 2;
        const appear = ramp(tt, showAt + (s.k / N) * acquire, 0.35);
        const base = appear * (0.93 - 0.5 * stacked) * (1 - 0.6 * segP);
        const isCut = s.k === cutK;
        s.plain.position.y = s.seg.position.y = yWorld;
        s.plain.material.opacity = isCut ? Math.max(base, 0.97 * (1 - segP)) : base * (cutK >= 0 ? 0.55 : 1);
        s.seg.material.opacity = appear * segP * (isCut ? 0.95 : 0.36 + 0.2 * (1 - stacked));
      }
      const acq = Math.min(1, Math.max(0, (tt - showAt) / acquire));
      gantry.position.y = (-0.92 + 1.84 * acq) * height / 2;
      gantry.material.opacity = 0.85 * ramp(tt, showAt - 0.2, 0.3) * (1 - ramp(tt, showAt + acquire, 0.5));
      gantry.visible = gantry.material.opacity > 0.002;
      lineMat.opacity = 0.32 * stacked * ramp(tt, showAt, 0.6);
      topRing.position.y = 0.92 * height / 2; botRing.position.y = -0.92 * height / 2;
      surface.scale.set(EXT * S, height / 2, EXT * S);
      organMat.opacity = (lesion ? 0.62 : 0.88) * segP;
      surface.visible = segP > 0.002;
      if (lesion) {
        let pulse = 0;
        for (const p of pulses) { const x = (tt - p) / 0.9; if (x > 0 && x < 1) pulse = Math.max(pulse, Math.sin(Math.PI * x)); }
        const lw = new THREE.Vector3(lesion.x * S, lesion.y * height / 2, -lesion.z * S);
        lesionMesh.position.copy(lw);
        lesionMesh.scale.setScalar(lesion.r * S * (1 + 0.25 * pulse));
        lesionMesh.material.opacity = Math.max(segP, focusP);
        lesionGlow.position.copy(lw);
        lesionGlow.scale.setScalar(0.9 + 0.8 * Math.max(focusP, pulse));
        lesionGlow.material.opacity = 0.75 * Math.max(segP * 0.6, focusP, pulse);
        lesionMesh.visible = lesionMesh.material.opacity > 0.002; lesionGlow.visible = lesionGlow.material.opacity > 0.002;
      }
      cutFrame.position.y = cutV === null ? 0 : (-0.92 + 1.84 * (cutK / (N - 1))) * height / 2;
      cutFrame.material.opacity = cutV === null ? 0 : 0.95 * ramp(tt, cuts[0].t, 0.3);
      cutFill.position.y = cutFrame.position.y;
      cutFill.material.opacity = 0.1 * cutFrame.material.opacity;
      cutFill.visible = cutFrame.visible = cutFrame.material.opacity > 0.002;
      // overlay
      chip.style.opacity = ramp(tt, showAt + 0.3, 0.5).toFixed(3);
      inset.style.opacity = (cutK >= 0 ? ramp(tt, cuts[0].t, 0.4) : 0).toFixed(3);
      const insetKey = `${cutK}:${segP > 0.5}`;
      if (cutK >= 0 && insetKey !== lastInset) {
        ix.clearRect(0, 0, 360, 360); ix.fillStyle = "#000"; ix.fillRect(0, 0, 360, 360);
        ix.imageSmoothingEnabled = true;
        // radiological convention, as the camera sees the body from the front: the patient's right on the left
        ix.setTransform(-1, 0, 0, 1, 360, 0);
        ix.drawImage(segP > 0.5 ? slices[cutK].canvas.seg : slices[cutK].canvas.plain, 0, 0, 360, 360);
        ix.setTransform(1, 0, 0, 1, 0, 0);
        insetCap.textContent = `corte axial · fatia ${cutK + 1} de ${N}`;
        lastInset = insetKey;
      }
      const top = toScreen(new THREE.Vector3(blob[0] * S, (blob[1] + blob[4] * 0.9) * height / 2, -blob[2] * S));
      organTag.style.left = (top.x - organTag.offsetWidth / 2).toFixed(1) + "px";
      organTag.style.top = (top.y - organTag.offsetHeight - 30).toFixed(1) + "px";
      organTag.style.opacity = (0.95 * segP).toFixed(3);
      if (lesionTag) {
        const p = toScreen(new THREE.Vector3(lesion.x * S, lesion.y * height / 2, -lesion.z * S));
        lesionTag.style.left = (p.x + 34).toFixed(1) + "px"; lesionTag.style.top = (p.y - lesionTag.offsetHeight / 2).toFixed(1) + "px";
        lesionTag.style.opacity = Math.max(segP * 0.9, focusP).toFixed(3);
      }
      renderer.render(scene, camera);
    }
    window.addEventListener("hf-seek", seekOf(id, offset, renderAt));
    renderAt(0);
    MK.exit(T, layer, data.dur);
    tl.set({}, {}, data.dur);
    window.__timelines = window.__timelines || {};
    window.__timelines[id] = tl;
  });
}

/* ---- mechanism3d: a 3D mechanism written for one scene ----------------------------------------------------------
   The scene module (written by the LLM, checked by the code policy and a headless probe) exports `build(kit)` and
   returns { update(t), view? }. It creates the geometry once, registers each part of the storyboard with
   kit.part(id, object, { anchor }) and moves things in update(t), a pure function of the scene time.
   The kit owns everything else: renderer and lights; the camera (it frames the parts over the whole scene between
   the title and the captions, orbits slowly, comes closer on focus); the HTML labels of the parts, with a leader
   line and without overlaps; the notes; and when each part appears, dims, pulses or leaves (the storyboard actions,
   at the spoken word). Every frame starts from the state the build left, so update(t) never accumulates. */
const PALETTE = { text: "#eef2f7", muted: "#9aa8bf", blue: "#4ea1ff", green: "#3ddc97", orange: "#ff9f45",
  yellow: "#ffd54a", purple: "#b48cff", red: "#ff5c70", pink: "#ff6f91", teal: "#2dd4d0", gray: "#8f9cb4",
  skin: "#d9a184", bone: "#e8e1d0", organ: "#d0706f", metal: "#aab6c8", dark: "#1a2438" };
const SAFE = { x0: 40, x1: W - 40, y0: 118, y1: 900 };
const UP = new THREE.Vector3(0, 1, 0);
const vec3 = (p) => (p && p.isVector3 ? p.clone() : new THREE.Vector3(...(p || [0, 0, 0])));

export function mountFree(id, data, offset, build) {
  MK.fontsReady().then(() => {
    const root = MK.rootOf(id);
    const stage = MK.el("div", "mk-scene", root);
    const layer = MK.el("div", "mk-stage", stage);
    const canvas = MK.el("canvas", "mk-canvas3d", layer);
    canvas.width = W; canvas.height = H;
    const overlay = MK.el("div", "mk-stage", layer);
    const leaders = MK.svgEl("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}`, class: "mk-leaders" }, overlay);
    const tl = gsap.timeline({ paused: true });
    const T = MK.Track(tl);
    T.init(layer, { opacity: 1, filter: "blur(0px)" });
    MK.header(T, layer, data.num, data.title);

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
    renderer.setPixelRatio(1);
    renderer.setSize(W, H, false);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.08;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(FOV, W / H, 0.05, 400);
    scene.add(new THREE.HemisphereLight(0xa8c0ff, 0x0a101e, 1.15));
    const key = new THREE.DirectionalLight(0xffe6c8, 2.3); key.position.set(4, 7, 6); scene.add(key);
    const rim = new THREE.DirectionalLight(0x6fa8ff, 1.7); rim.position.set(-6, 3, -5); scene.add(rim);
    const world = new THREE.Group();
    scene.add(world);

    // the storyboard: parts (nodes) and what happens to them, at the spoken word
    const nodes = data.nodes || [], byId = Object.fromEntries(nodes.map((n) => [n.id, n]));
    const beats = (data.beats || []).map(([a, b]) => ({ start: a, end: b, duration: Math.max(0.01, b - a) }));
    const acts = data.actions || [];
    const touches = (a, pid) => !a.ids.length || a.ids.includes(pid);
    const sched = {};
    for (const n of nodes) {
      const show = acts.find((a) => a.do === "show" && touches(a, n.id));
      const shownAt = show ? show.t : 0.4;
      const hide = acts.find((a) => a.do === "hide" && a.ids.includes(n.id) && a.t > shownAt);
      const level = [[0, 1]], pulses = [], labels = [[0, n.label]];
      for (const a of acts) {
        if (a.do === "focus") level.push([a.t, a.ids.includes(n.id) ? 1 : 0.24]);
        else if (a.do === "unfocus") level.push([a.t, 1]);
        else if (a.do === "dim" && a.ids.includes(n.id)) level.push([a.t, 0.22]);
        else if (a.do === "pulse" && a.ids.includes(n.id)) pulses.push(a.t);
        else if (a.do === "label" && a.ids[0] === n.id && a.text) labels.push([a.t, a.text]);
      }
      sched[n.id] = { shownAt, hideAt: hide ? hide.t : Infinity, level, pulses, labels };
    }
    const focusTrack = [[0, 0, []]];
    for (const a of acts) if (a.do === "focus" || a.do === "unfocus") focusTrack.push([a.t, a.do === "focus" ? 1 : 0, a.ids]);
    const levelAt = (track, t, d) => {          // eased steps through (time, level) pairs
      let v = track[0][1];
      for (let i = 1; i < track.length; i++) { const [at, to] = track[i]; if (t <= at) break; v = v + (to - v) * ease((t - at) / d); }
      return v;
    };

    // the kit the scene module gets
    const parts = new Map(), errors = [];
    let glowTex = null;
    const kit = {
      THREE, palette: PALETTE, beats, dur: data.dur, root: world,
      color: (pid) => (byId[pid] && MK.ROLE[byId[pid].role]) || PALETTE.gray,
      part(pid, obj, opts = {}) {
        if (!obj.parent) world.add(obj);
        parts.set(pid, { obj, anchor: opts.anchor ? vec3(opts.anchor) : null });
        return obj;
      },
      add(obj) { if (!obj.parent) world.add(obj); return obj; },
      material: (color, o = {}) => new THREE.MeshStandardMaterial(Object.assign({ color, roughness: 0.42, metalness: 0.08,
        emissive: color, emissiveIntensity: 0.14 }, o)),
      glow: (color, o = {}) => new THREE.MeshBasicMaterial(Object.assign({ color, transparent: true, opacity: 0.55,
        blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false }, o)),
      sprite(color, size = 1) {
        glowTex = glowTex || glowTexture();
        const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color, blending: THREE.AdditiveBlending,
          transparent: true, depthWrite: false }));
        s.scale.setScalar(size);
        return s;
      },
      stretch(mesh, a, b) {        // a mesh of height 1 along y (a rod, a beam) from point a to point b
        const A = vec3(a), d = vec3(b).sub(A), L = Math.max(1e-4, d.length());
        mesh.position.copy(A).addScaledVector(d, 0.5);
        mesh.quaternion.setFromUnitVectors(UP, d.normalize());
        mesh.scale.y = L;
        return mesh;
      },
      rod(a, b, r = 0.05, mat) {
        const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, 1, 24), mat || kit.material(PALETTE.yellow));
        return kit.stretch(m, a, b);
      },
      progress(t, i, share = 0.6) {
        const b = beats[Math.max(0, Math.min(i, beats.length - 1))];
        return b ? Math.max(0, Math.min(1, (t - b.start) / (b.duration * share))) : 1;
      },
      shownAt: (pid) => (sched[pid] ? sched[pid].shownAt : 0),
      ease, lerp: (a, b, x) => a + (b - a) * x, clamp: (x, a = 0, b = 1) => Math.max(a, Math.min(b, x)),
      random: (seed = 1) => MK.rng(seed),
      fade(obj, alpha) {             // scenery that is not a part: hide it, or fade it (alpha 0–1)
        obj.visible = alpha > 0.01;
        obj.traverse((o) => { for (const m of o.material ? [].concat(o.material) : []) { m.transparent = true; m.opacity *= alpha; } });
      },
    };
    const user = build(kit) || {};
    const view = Object.assign({ azimuth: 32, elevation: 18, distance: 1, orbit: 0.22 }, user.view || {});

    // the state the build left: every frame starts from it, so update(t) is a pure function of t
    const base = [], seenMats = new Set();
    world.traverse((o) => {
      base.push([o, o.visible]);
      for (const m of o.material ? [].concat(o.material) : []) {
        if (seenMats.has(m)) continue;
        seenMats.add(m);
        m.transparent = true;
        base.push([m, m.opacity, m.emissiveIntensity]);
      }
    });
    const restore = () => {
      for (const b of base) {
        if (b.length === 2) b[0].visible = b[1];
        else { b[0].opacity = b[1]; if (b[2] !== undefined) b[0].emissiveIntensity = b[2]; }
      }
    };
    const step = (t) => {
      restore();
      if (user.update) { try { user.update(t); } catch (e) { if (errors.length < 3) errors.push(String((e && e.message) || e)); } }
      world.updateMatrixWorld(true);
    };
    // what each part owns: its meshes, without the parts nested in it (a tube on a turning gantry is its own part)
    const partObjs = new Set([...parts.values()].map((p) => p.obj));
    const own = new Map();
    for (const [pid, p] of parts) {
      const meshes = [];
      const walk = (o) => { if (o !== p.obj && partObjs.has(o)) return; if (o.material) meshes.push(o); o.children.forEach(walk); };
      walk(p.obj);
      own.set(pid, meshes);
    }

    // framing: the parts over the whole scene (motion included) fit between the title and the captions
    const box = new THREE.Box3(), tmpBox = new THREE.Box3();
    for (const t of [0, ...beats.map((b) => b.end - 0.05), data.dur * 0.5, data.dur]) {
      step(t);
      for (const p of parts.values()) { tmpBox.setFromObject(p.obj); if (!tmpBox.isEmpty()) box.union(tmpBox); }
    }
    if (box.isEmpty()) box.setFromObject(world);
    if (box.isEmpty()) box.set(new THREE.Vector3(-1, -1, -1), new THREE.Vector3(1, 1, 1));
    const sphere = box.getBoundingSphere(new THREE.Sphere());
    const center = sphere.center.clone(), radius = Math.max(0.1, sphere.radius);
    const hasNotes = acts.some((a) => a.do === "note");
    const tmp = new THREE.Vector3();
    const toScreen = (p) => { tmp.copy(p).project(camera); return { x: (tmp.x + 1) / 2 * W, y: (1 - tmp.y) / 2 * H, z: tmp.z }; };
    // the box of the parts, seen from the start, the middle and the end of the orbit, fills the free area (room
    // for the labels at the sides, the notes column on the right, the title above and the captions below)
    const corners = [];
    for (const x of [box.min.x, box.max.x]) for (const y of [box.min.y, box.max.y]) for (const z of [box.min.z, box.max.z]) corners.push(new THREE.Vector3(x, y, z));
    const area = { x0: 300, x1: hasNotes ? W - 620 : W - 300, y0: 175, y1: 840 };
    const el0 = THREE.MathUtils.degToRad(view.elevation), az0 = THREE.MathUtils.degToRad(view.azimuth);
    const dirAt = (az) => new THREE.Vector3(Math.cos(el0) * Math.sin(az), Math.sin(el0), Math.cos(el0) * Math.cos(az));
    const rectAt = (d, az) => {
      camera.clearViewOffset();
      camera.position.copy(center).addScaledVector(dirAt(az), d);
      camera.lookAt(center);
      camera.updateMatrixWorld();
      const xs = [], ys = [];
      for (const c of corners) { const q = toScreen(c); xs.push(q.x); ys.push(q.y); }
      return { x0: Math.min(...xs), x1: Math.max(...xs), y0: Math.min(...ys), y1: Math.max(...ys) };
    };
    let dist0 = radius / Math.sin(THREE.MathUtils.degToRad(FOV / 2)) / 0.8;
    for (let i = 0; i < 5; i++) {
      let k = 0;
      for (const az of [az0, az0 + view.orbit / 2, az0 + view.orbit]) {
        const r = rectAt(dist0, az);
        k = Math.max(k, (r.x1 - r.x0) / (area.x1 - area.x0), (r.y1 - r.y0) / (area.y1 - area.y0));
      }
      dist0 = Math.max(radius * 1.2, dist0 * Math.max(0.5, Math.min(2, k)));
    }
    dist0 *= view.distance;
    const mid = rectAt(dist0, az0 + view.orbit / 2);
    camera.setViewOffset(W, H, (mid.x0 + mid.x1) / 2 - (area.x0 + area.x1) / 2, (mid.y0 + mid.y1) / 2 - (area.y0 + area.y1) / 2, W, H);
    camera.far = dist0 * 4 + radius * 6;
    camera.updateProjectionMatrix();
    scene.fog = new THREE.Fog(0x0a101e, dist0 + radius * 0.6, dist0 + radius * 5);
    const grid = new THREE.GridHelper(radius * 5, 20, 0x2f4470, 0x1b2a49);
    grid.position.set(center.x, box.min.y - radius * 0.04, center.z);
    grid.material.transparent = true; grid.material.opacity = 0.16;
    scene.add(grid);

    // overlay: a label per part (with its leader line) and the notes in the right column
    const tags = {};
    for (const n of nodes) {
      const tag = MK.el("div", `mk-tag3d mk-r-${n.role}`, overlay);
      const line = MK.svgEl("line", { class: `mk-leader mk-r-${n.role}`, x1: 0, y1: 0, x2: 0, y2: 0 }, leaders);
      const dot = MK.svgEl("circle", { class: `mk-leader-dot mk-r-${n.role}`, cx: 0, cy: 0, r: 6 }, leaders);
      tags[n.id] = { tag, line, dot, text: null, w: 0, h: 0 };
      tag.style.opacity = "0"; line.style.opacity = "0"; dot.style.opacity = "0";
    }
    const setTag = (n, text) => {
      const g = tags[n.id];
      if (g.text === text) return;
      g.tag.innerHTML = MK.esc(text) + (n.gloss ? `<span class="mk-tag3d-gloss">${MK.esc(n.gloss)}</span>` : "");
      g.text = text; g.w = g.tag.offsetWidth; g.h = g.tag.offsetHeight;
    };
    const colR = W - 120;
    let colY = 160;
    for (const a of acts) {
      if (a.do !== "note") continue;
      const el = MK.el("div", "mk-note mk-r-info", overlay, `<i></i>${MK.esc(a.text)}`);
      el.style.left = (colR - el.offsetWidth) + "px"; el.style.top = colY + "px"; colY += el.offsetHeight + 12;
      T.init(el, { opacity: 0, x: -12, filter: "blur(6px)" }); T.to(el, { opacity: 1, x: 0, filter: "blur(0px)" }, a.t, 0.45, "expo.out");
    }
    const labelX1 = hasNotes ? W - 600 : W - 120;

    const anchorOf = (p) => {
      if (p.anchor) return p.obj.localToWorld(p.anchor.clone());
      tmpBox.setFromObject(p.obj);
      if (tmpBox.isEmpty()) return p.obj.getWorldPosition(new THREE.Vector3());
      return tmpBox.getCenter(new THREE.Vector3()).setY(tmpBox.max.y);
    };
    const alphaOf = (pid, t) => {
      const s = sched[pid];
      return s ? ramp(t, s.shownAt, 0.6) * (1 - ramp(t, s.hideAt, 0.4)) * levelAt(s.level, t, 0.45) : 1;
    };
    const pulseOf = (pid, t) => {
      let p = 0;
      for (const at of sched[pid] ? sched[pid].pulses : []) { const x = (t - at) / 0.9; if (x > 0 && x < 1) p = Math.max(p, Math.sin(Math.PI * x)); }
      return p;
    };
    const focusedAt = (t) => { let ids = []; for (const f of focusTrack) if (f[0] <= t) ids = f[1] === 1 ? f[2] : []; return ids; };
    let lastFocus = center.clone();

    function renderAt(t) {
      const tt = Math.max(0, Math.min(data.dur, t));
      step(tt);
      // the parts: appear, dim, pulse (on top of what update(t) did)
      const fids = focusedAt(tt);
      for (const [pid, meshes] of own) {
        const a = alphaOf(pid, tt), boost = 0.9 * pulseOf(pid, tt) + (fids.includes(pid) ? 0.25 : 0);
        for (const m of meshes) {
          if (a <= 0.01) m.visible = false;
          for (const mat of [].concat(m.material)) {
            mat.opacity *= a;
            if (mat.emissiveIntensity !== undefined) mat.emissiveIntensity += boost;
          }
        }
      }
      // the camera: a slow orbit around the parts; closer to what the narration focuses on
      const fp = levelAt(focusTrack, tt, 1.2);
      const pts = fids.filter((pid) => parts.has(pid)).map((pid) => anchorOf(parts.get(pid)));
      if (pts.length) lastFocus = pts.reduce((s, p) => s.add(p), new THREE.Vector3()).multiplyScalar(1 / pts.length);
      const target = center.clone().lerp(lastFocus, 0.55 * fp);
      const dist = dist0 * (1 - 0.26 * fp);
      const az = THREE.MathUtils.degToRad(view.azimuth) + view.orbit * (tt / data.dur);
      const el = THREE.MathUtils.degToRad(view.elevation);
      camera.position.set(target.x + dist * Math.cos(el) * Math.sin(az), target.y + dist * Math.sin(el), target.z + dist * Math.cos(el) * Math.cos(az));
      camera.lookAt(target);
      camera.updateMatrixWorld();
      applyOrbit(camera, target);
      // the labels: beside the anchor, away from the middle, never over each other
      const midS = toScreen(target), boxes = [];
      for (const n of nodes) {
        const g = tags[n.id], p = parts.get(n.id), s = sched[n.id];
        if (!p) continue;
        let text = n.label;
        for (const [at, txt] of s.labels) if (at <= tt) text = txt;
        setTag(n, text);
        const a = toScreen(anchorOf(p)), side = a.x < midS.x ? -1 : 1;
        const show = ramp(tt, s.shownAt + 0.35, 0.4) * (1 - ramp(tt, s.hideAt, 0.3)) * Math.max(levelAt(s.level, tt, 0.45), 0.35);
        boxes.push({ g, a, side, show, x: side > 0 ? a.x + 64 : a.x - 64 - g.w, y: a.y - g.h - 34, w: g.w, h: g.h, behind: a.z > 1 });
      }
      boxes.sort((p, q) => p.y - q.y);
      for (let i = 0; i < boxes.length; i++) {
        const b = boxes[i];
        b.x = Math.max(120, Math.min(labelX1 - b.w, b.x)); b.y = Math.max(150, Math.min(862 - b.h, b.y));
        for (let k = 0; k < 6; k++) {
          const hit = boxes.slice(0, i).find((o) => o.show > 0.05 && b.x < o.x + o.w + 10 && o.x < b.x + b.w + 10 && b.y < o.y + o.h + 10 && o.y < b.y + b.h + 10);
          if (!hit) break;
          b.y = hit.y + hit.h + 12;
          if (b.y + b.h > 862) { b.y = Math.max(150, hit.y - b.h - 12); b.x = b.side > 0 ? hit.x + hit.w + 16 : hit.x - b.w - 16; }
        }
      }
      for (const b of boxes) {
        const op = b.behind ? 0 : b.show;
        b.g.tag.style.left = b.x.toFixed(1) + "px"; b.g.tag.style.top = b.y.toFixed(1) + "px"; b.g.tag.style.opacity = op.toFixed(3);
        const ex = b.side > 0 ? b.x : b.x + b.w, ey = b.y + b.h / 2;
        b.g.line.setAttribute("x1", b.a.x.toFixed(1)); b.g.line.setAttribute("y1", b.a.y.toFixed(1));
        b.g.line.setAttribute("x2", ex.toFixed(1)); b.g.line.setAttribute("y2", ey.toFixed(1));
        b.g.dot.setAttribute("cx", b.a.x.toFixed(1)); b.g.dot.setAttribute("cy", b.a.y.toFixed(1));
        b.g.line.style.opacity = (0.85 * op).toFixed(3); b.g.dot.style.opacity = op.toFixed(3);
      }
      renderer.render(scene, camera);
    }

    // the probe (a headless check before the render): the parts the storyboard names, parts off the frame, errors
    function check(t) {
      renderAt(t);
      const out = errors.map((e) => `erro em update(t): ${e}`);
      for (const n of nodes) if (!parts.has(n.id)) out.push(`a peça "${n.id}" do storyboard não foi registrada: use kit.part("${n.id}", objeto)`);
      for (const pid of parts.keys()) if (!byId[pid]) out.push(`kit.part("${pid}"): "${pid}" não é uma peça do storyboard (use ${nodes.map((n) => n.id).join(", ")}; o cenário vai em kit.add)`);
      for (const [pid, p] of parts) {
        if (!byId[pid] || alphaOf(pid, t) < 0.5) continue;
        tmpBox.setFromObject(p.obj);
        if (tmpBox.isEmpty()) { out.push(`a peça "${pid}" não tem malha visível`); continue; }
        if (![tmpBox.min.x, tmpBox.min.y, tmpBox.min.z, tmpBox.max.x, tmpBox.max.y, tmpBox.max.z].every(Number.isFinite)) { out.push(`a peça "${pid}" tem posição inválida (NaN)`); continue; }
        const xs = [], ys = [];
        for (const x of [tmpBox.min.x, tmpBox.max.x]) for (const y of [tmpBox.min.y, tmpBox.max.y]) for (const z of [tmpBox.min.z, tmpBox.max.z]) {
          const s = toScreen(new THREE.Vector3(x, y, z)); xs.push(s.x); ys.push(s.y);
        }
        const r = { x0: Math.min(...xs), x1: Math.max(...xs), y0: Math.min(...ys), y1: Math.max(...ys) };
        if (r.x0 < SAFE.x0 - 40 || r.x1 > SAFE.x1 + 40 || r.y0 < SAFE.y0 - 40 || r.y1 > SAFE.y1 + 40) out.push(`a peça "${pid}" sai do quadro`);
        else if (r.x1 - r.x0 < 28 && r.y1 - r.y0 < 28) out.push(`a peça "${pid}" fica pequena demais na tela (aumente-a)`);
      }
      return [...new Set(out)];
    }
    window.__check3d = window.__check3d || {};
    window.__check3d[id] = check;
    window.addEventListener("hf-seek", seekOf(id, offset, renderAt));
    renderAt(0);
    MK.exit(T, layer, data.dur);
    tl.set({}, {}, data.dur);
    window.__timelines = window.__timelines || {};
    window.__timelines[id] = tl;
  });
}
