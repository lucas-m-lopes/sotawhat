/* sotawhat lessons · HyperFrames kit · vectors3d: vectors from a common origin in a real 3D space (three.js).
   Drawn from the timeline time only (hf-seek gives the time of the whole video; `offset` is the scene start), so
   every frame renders on its own. The dot products shown are computed here from the vectors of the storyboard,
   and an arc between the query and each key shows the angle that the dot product measures. */
import * as THREE from "../lib/three.module.js";

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
    window.addEventListener("hf-seek", (e) => renderAt(e.detail.time - offset));
    renderAt(0);
    MK.exit(T, layer, data.dur);
    tl.set({}, {}, data.dur);
    window.__timelines = window.__timelines || {};
    window.__timelines[id] = tl;
  });
}
