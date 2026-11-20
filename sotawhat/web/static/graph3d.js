// sotawhat/web/static/graph3d.js — the entity graph in 3D (2026-11-20). An ES module that app.js imports on demand.
// three.js (vendored under /static/vendor/three, no CDN) draws every entity as a glowing point and every connection
// as a thin additive line; the layout is a force simulation in three dimensions that settles on screen.
// A stated relation ("developed by", "addresses") has a direction, and small particles run along it from the
// subject to the object. The pointer is a light: what is near it brightens, as in a scene lit by the cursor.
// The same scene has a flat mode (2D): the simulation presses every node onto one plane and the camera looks at
// it from the front, panning instead of orbiting. Switching between the two is animated, not a reload.
// Names go into the page through textContent, never as HTML.
import * as THREE from "three";
import { OrbitControls } from "./vendor/three/OrbitControls.js";

const NODE_VERTEX = `
attribute float aSize;
attribute vec3 aColor;
attribute float aState;      // 0 = dimmed, 1 = normal, 2 = the active node
attribute float aPhase;
uniform float uScale;
uniform float uTime;
uniform vec2 uMouse;         // pointer in normalized device coordinates
uniform float uAspect;
uniform float uLight;        // 1 while the pointer is over the scene
uniform float uFar;
varying vec3 vColor;
varying float vAlpha;
void main() {
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  vec4 clip = projectionMatrix * mv;
  vec2 ndc = clip.xy / clip.w;
  float lit = uLight * smoothstep(0.5, 0.0, distance(ndc * vec2(uAspect, 1.0), uMouse * vec2(uAspect, 1.0)));
  float twinkle = 0.9 + 0.1 * sin(uTime * 1.6 + aPhase);
  float hot = step(1.5, aState);
  float depth = clamp(1.35 - (-mv.z) / uFar, 0.3, 1.0);
  vColor = aColor * (twinkle + 1.1 * lit + 0.7 * hot);
  vAlpha = (aState < 0.5 ? 0.13 : 1.0) * depth;
  gl_PointSize = max(2.0, aSize * uScale * (1.0 + 0.3 * lit + 0.45 * hot) / -mv.z);
  gl_Position = clip;
}`;

const NODE_FRAGMENT = `
varying vec3 vColor;
varying float vAlpha;
void main() {
  vec2 p = gl_PointCoord * 2.0 - 1.0;
  float r = dot(p, p);
  if (r > 1.0) discard;
  float core = smoothstep(0.10, 0.012, r);
  float halo = pow(1.0 - r, 3.0);
  gl_FragColor = vec4(vColor * (0.62 * halo + core) + vec3(0.5 * core), vAlpha * (0.7 * halo + core));
}`;

const EDGE_VERTEX = `
attribute vec3 aColor;
attribute float aAlpha;
uniform vec2 uMouse;
uniform float uAspect;
uniform float uLight;
uniform float uFar;
varying vec3 vColor;
varying float vAlpha;
void main() {
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  vec4 clip = projectionMatrix * mv;
  vec2 ndc = clip.xy / clip.w;
  float lit = uLight * smoothstep(0.42, 0.0, distance(ndc * vec2(uAspect, 1.0), uMouse * vec2(uAspect, 1.0)));
  float depth = clamp(1.35 - (-mv.z) / uFar, 0.25, 1.0);
  vColor = aColor * (1.0 + 1.2 * lit);
  vAlpha = aAlpha * (1.0 + 2.2 * lit) * depth;
  gl_Position = clip;
}`;

const EDGE_FRAGMENT = `
varying vec3 vColor;
varying float vAlpha;
void main() { gl_FragColor = vec4(vColor, vAlpha); }`;

const FLOW_VERTEX = `
attribute vec3 aEnd;
attribute float aPhase;
attribute float aSpeed;
attribute float aAlpha;
uniform float uScale;
uniform float uTime;
uniform vec2 uMouse;
uniform float uAspect;
uniform float uLight;
uniform float uFar;
varying float vAlpha;
void main() {
  float t = fract(uTime * aSpeed + aPhase);
  vec4 mv = modelViewMatrix * vec4(mix(position, aEnd, t), 1.0);
  vec4 clip = projectionMatrix * mv;
  vec2 ndc = clip.xy / clip.w;
  float lit = uLight * smoothstep(0.42, 0.0, distance(ndc * vec2(uAspect, 1.0), uMouse * vec2(uAspect, 1.0)));
  float depth = clamp(1.35 - (-mv.z) / uFar, 0.25, 1.0);
  vAlpha = aAlpha * sin(t * 3.14159) * (0.6 + 1.5 * lit) * depth;      // it fades in at one end and out at the other
  gl_PointSize = max(1.5, 3.2 * uScale * (1.0 + 0.6 * lit) / -mv.z);
  gl_Position = clip;
}`;

const FLOW_FRAGMENT = `
varying float vAlpha;
void main() {
  vec2 p = gl_PointCoord * 2.0 - 1.0;
  float r = dot(p, p);
  if (r > 1.0) discard;
  gl_FragColor = vec4(0.72, 0.95, 1.0, vAlpha * pow(1.0 - r, 1.6));
}`;

const EDGE = new THREE.Color("#7f9dff");          // co-occurrence
const EDGE_TYPED = new THREE.Color("#5ee6ff");    // a stated relation
const MAX_LABELS = 34;
const SPRITE = 5.2;                               // sprite diameter, in world units, per unit of node size (core + halo)

function seeded(seed) {                           // mulberry32: the same graph always starts from the same cloud
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hash(text) {
  let h = 2166136261;
  for (let i = 0; i < text.length; i += 1) { h ^= text.charCodeAt(i); h = Math.imul(h, 16777619); }
  return h >>> 0;
}

// A force layout in three dimensions: springs on the edges, repulsion between every pair, a pull to the center.
// Plain loops over typed arrays; a thousand nodes cost a few milliseconds a tick.
class Layout {
  constructor(count, links, sizes, ids, flat = false) {
    this.n = count;
    this.ids = ids;
    this.flat = flat;
    this.pos = new Float32Array(count * 3);
    this.vel = new Float32Array(count * 3);
    this.links = links;
    this.alpha = 1;
    this.degree = new Float32Array(count);
    for (const [s, t] of links) { this.degree[s] += 1; this.degree[t] += 1; }
    this.charge = new Float32Array(count);
    const spread = 14 * Math.cbrt(Math.max(count, 1));
    this.spread = spread;
    for (let i = 0; i < count; i += 1) {
      const random = seeded(hash(ids[i]));
      const u = random() * 2 - 1, phi = random() * Math.PI * 2, rad = spread * Math.cbrt(random());
      const s = Math.sqrt(1 - u * u);
      this.pos[3 * i] = rad * s * Math.cos(phi);
      this.pos[3 * i + 1] = rad * s * Math.sin(phi);
      this.pos[3 * i + 2] = flat ? 0 : rad * u;
      this.charge[i] = 26 + 5 * sizes[i];
    }
  }

  get done() { return this.alpha < 0.004; }

  // Flat: the next ticks press the cloud onto the plane z = 0. Back to three dimensions: every node gets its own
  // push out of the plane, always the same one, and the forces shape the volume again.
  setFlat(flat) {
    this.flat = flat;
    if (!flat) {
      for (let i = 0; i < this.n; i += 1) {
        this.pos[3 * i + 2] = (seeded(hash(`z${this.ids[i]}`))() - 0.5) * this.spread * 1.4;
      }
    }
    this.alpha = Math.max(this.alpha, 0.6);
  }

  tick() {
    const { n, pos, vel, links, degree, charge } = this;
    this.alpha *= 0.982;
    const alpha = this.alpha;
    for (const [s, t, weight] of links) {
      const a = 3 * s, b = 3 * t;
      let dx = pos[b] + vel[b] - pos[a] - vel[a];
      let dy = pos[b + 1] + vel[b + 1] - pos[a + 1] - vel[a + 1];
      let dz = pos[b + 2] + vel[b + 2] - pos[a + 2] - vel[a + 2];
      const dist = Math.sqrt(dx * dx + dy * dy + dz * dz) || 1e-3;
      const strength = Math.min(1, 0.5 + 0.15 * weight) / Math.min(degree[s], degree[t]);
      const f = ((dist - 26) / dist) * alpha * strength;
      dx *= f; dy *= f; dz *= f;
      const bias = degree[s] / (degree[s] + degree[t]);
      vel[b] -= dx * bias; vel[b + 1] -= dy * bias; vel[b + 2] -= dz * bias;
      vel[a] += dx * (1 - bias); vel[a + 1] += dy * (1 - bias); vel[a + 2] += dz * (1 - bias);
    }
    for (let i = 0; i < n; i += 1) {
      const a = 3 * i;
      for (let j = i + 1; j < n; j += 1) {
        const b = 3 * j;
        const dx = pos[b] - pos[a], dy = pos[b + 1] - pos[a + 1], dz = pos[b + 2] - pos[a + 2];
        const d2 = dx * dx + dy * dy + dz * dz;
        if (d2 > 40000) continue;                       // beyond 200 units the push is nothing
        const k = alpha / Math.max(d2, 4);
        const fi = k * charge[j], fj = k * charge[i];
        vel[a] -= dx * fi; vel[a + 1] -= dy * fi; vel[a + 2] -= dz * fi;
        vel[b] += dx * fj; vel[b + 1] += dy * fj; vel[b + 2] += dz * fj;
      }
    }
    const pull = 0.045 * alpha;
    for (let i = 0; i < 3 * n; i += 1) {
      vel[i] = (vel[i] - pos[i] * pull) * 0.6;
      pos[i] += vel[i];
    }
    if (this.flat) {
      for (let i = 2; i < 3 * n; i += 3) { vel[i] = 0; pos[i] *= 0.8; }
    }
  }

  radius() {                                           // the distance from the center that holds 95% of the nodes
    const d = [];
    for (let i = 0; i < this.n; i += 1) d.push(Math.hypot(this.pos[3 * i], this.pos[3 * i + 1], this.pos[3 * i + 2]));
    d.sort((x, y) => x - y);
    return Math.max(d[Math.floor(0.95 * (d.length - 1))] || 0, 20);
  }
}

export class Graph3D {
  // handlers: onHover(id | null), onSelect(id), onFocus(id), onClear(); options: { flat } starts in the 2D mode
  constructor(container, handlers = {}, options = {}) {
    this.container = container;
    this.handlers = handlers;
    this.flat = false;
    this.reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setClearColor(0x000000, 0);
    this.canvas = this.renderer.domElement;
    this.canvas.className = "graph3d";
    this.labels = document.createElement("div");
    this.labels.className = "labels3d";
    container.replaceChildren(this.canvas, this.labels);
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(50, 1, 1, 6000);
    this.camera.position.set(0, 60, 420);
    this.controls = new OrbitControls(this.camera, this.canvas);
    Object.assign(this.controls, { enableDamping: true, dampingFactor: 0.08, rotateSpeed: 0.6, zoomSpeed: 0.8,
                                   autoRotate: !this.reduced, autoRotateSpeed: 0.35 });
    this.uniforms = { uScale: { value: 1 }, uTime: { value: 0 }, uMouse: { value: new THREE.Vector2(9, 9) },
                      uAspect: { value: 1 }, uLight: { value: 0 }, uFar: { value: 900 } };
    this.group = new THREE.Group();
    this.scene.add(this.group, this._dust());
    this.nodes = [];
    this.index = new Map();
    this.neighbors = [];
    this.active = null;
    this.hovered = null;
    this.pool = [];
    this.screen = new Float32Array(0);
    this.fly = null;
    this.lastTouch = 0;
    this.started = performance.now();
    this._listen();
    this.resize();
    if (options.flat) this.setFlat(true);
    this.frame = requestAnimationFrame(() => this._loop());
  }

  _dust() {                                            // far, faint particles: depth behind the graph
    const count = 700, positions = new Float32Array(count * 3), random = seeded(7);
    for (let i = 0; i < count; i += 1) {
      const u = random() * 2 - 1, phi = random() * Math.PI * 2, rad = 700 + 1500 * random(), s = Math.sqrt(1 - u * u);
      positions.set([rad * s * Math.cos(phi), rad * u, rad * s * Math.sin(phi)], 3 * i);
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    this.dust = new THREE.Points(geometry, new THREE.PointsMaterial({
      color: 0x8fb4ff, size: 2.2, sizeAttenuation: false, transparent: true, opacity: 0.32,
      blending: THREE.AdditiveBlending, depthWrite: false }));
    return this.dust;
  }

  _listen() {
    const canvas = this.canvas;
    this.on = {
      move: (ev) => {
        const box = canvas.getBoundingClientRect();
        this.pointer = { x: ev.clientX - box.left, y: ev.clientY - box.top };
        this.uniforms.uMouse.value.set((this.pointer.x / box.width) * 2 - 1, -(this.pointer.y / box.height) * 2 + 1);
        this.uniforms.uLight.value = 1;
        if (!this.dragging) this._hover(this._pick());
      },
      leave: () => { this.pointer = null; this.uniforms.uLight.value = 0; this._hover(null); },
      down: (ev) => { this.dragging = false; this.press = { x: ev.clientX, y: ev.clientY }; this.lastTouch = performance.now(); },
      drag: (ev) => {
        if (this.press && Math.hypot(ev.clientX - this.press.x, ev.clientY - this.press.y) > 5) this.dragging = true;
      },
      up: () => {
        const clicked = this.press && !this.dragging;
        this.press = null;
        this.dragging = false;
        this.lastTouch = performance.now();
        if (!clicked) return;
        const node = this._pick();
        if (node !== null) { if (this.handlers.onSelect) this.handlers.onSelect(this.nodes[node].id); }
        else if (this.handlers.onClear) this.handlers.onClear();
      },
      double: (ev) => {
        const node = this._pick();
        if (node !== null && this.handlers.onFocus) { ev.preventDefault(); this.handlers.onFocus(this.nodes[node].id); }
      },
      wheel: () => { this.lastTouch = performance.now(); },
    };
    canvas.addEventListener("pointermove", this.on.move);
    canvas.addEventListener("pointermove", this.on.drag);
    canvas.addEventListener("pointerleave", this.on.leave);
    canvas.addEventListener("pointerdown", this.on.down);
    canvas.addEventListener("pointerup", this.on.up);
    canvas.addEventListener("dblclick", this.on.double);
    canvas.addEventListener("wheel", this.on.wheel, { passive: true });
  }

  // nodes: [{ id, label, size, color }], edges: [{ source, target, typed, weight }]
  setData(nodes, edges) {
    for (const child of [...this.group.children]) {
      this.group.remove(child);
      child.geometry.dispose();
      child.material.dispose();
    }
    this.nodes = nodes;
    this.index = new Map(nodes.map((node, i) => [node.id, i]));
    this.links = edges.filter((e) => this.index.has(e.source) && this.index.has(e.target))
      .map((e) => ({ s: this.index.get(e.source), t: this.index.get(e.target), typed: Boolean(e.typed), weight: e.weight || 1 }));
    this.neighbors = nodes.map(() => new Set());
    for (const link of this.links) { this.neighbors[link.s].add(link.t); this.neighbors[link.t].add(link.s); }
    this.active = null;
    this.hovered = null;
    this.fly = null;
    const n = nodes.length;
    this.layout = new Layout(n, this.links.map((l) => [l.s, l.t, l.weight]), nodes.map((node) => node.size),
                             nodes.map((node) => node.id), this.flat);
    if (this.reduced) { while (!this.layout.done) this.layout.tick(); }
    this.screen = new Float32Array(n * 4);             // x, y, radius in CSS pixels, depth (≤ 0 = behind the camera)
    this.byWeight = nodes.map((_, i) => i).sort((a, b) => nodes[b].size - nodes[a].size);

    const points = new THREE.BufferGeometry();
    points.setAttribute("position", new THREE.BufferAttribute(this.layout.pos, 3).setUsage(THREE.DynamicDrawUsage));
    points.setAttribute("aSize", new THREE.BufferAttribute(Float32Array.from(nodes, (node) => SPRITE * node.size), 1));
    points.setAttribute("aColor", new THREE.BufferAttribute(new Float32Array(n * 3), 3));
    points.setAttribute("aState", new THREE.BufferAttribute(new Float32Array(n).fill(1), 1));
    points.setAttribute("aPhase", new THREE.BufferAttribute(Float32Array.from(nodes, (node) => (hash(node.id) % 628) / 100), 1));
    this.points = new THREE.Points(points, new THREE.ShaderMaterial({
      uniforms: this.uniforms, vertexShader: NODE_VERTEX, fragmentShader: NODE_FRAGMENT, transparent: true,
      depthWrite: false, depthTest: false, blending: THREE.AdditiveBlending }));
    this.points.frustumCulled = false;

    const lines = new THREE.BufferGeometry();
    const m = this.links.length;
    lines.setAttribute("position", new THREE.BufferAttribute(new Float32Array(m * 6), 3).setUsage(THREE.DynamicDrawUsage));
    lines.setAttribute("aColor", new THREE.BufferAttribute(new Float32Array(m * 6), 3));
    lines.setAttribute("aAlpha", new THREE.BufferAttribute(new Float32Array(m * 2), 1));
    this.lines = new THREE.LineSegments(lines, new THREE.ShaderMaterial({
      uniforms: this.uniforms, vertexShader: EDGE_VERTEX, fragmentShader: EDGE_FRAGMENT, transparent: true,
      depthWrite: false, depthTest: false, blending: THREE.AdditiveBlending }));
    this.lines.frustumCulled = false;

    // two particles per stated relation, half a lap apart, each relation at its own pace
    this.typed = this.links.map((link, i) => (link.typed ? i : -1)).filter((i) => i >= 0);
    const k = this.typed.length * 2, flow = new THREE.BufferGeometry();
    flow.setAttribute("position", new THREE.BufferAttribute(new Float32Array(k * 3), 3).setUsage(THREE.DynamicDrawUsage));
    flow.setAttribute("aEnd", new THREE.BufferAttribute(new Float32Array(k * 3), 3).setUsage(THREE.DynamicDrawUsage));
    flow.setAttribute("aPhase", new THREE.BufferAttribute(Float32Array.from({ length: k }, (_, j) =>
      (hash(`${nodes[this.links[this.typed[j >> 1]].s].id}>${nodes[this.links[this.typed[j >> 1]].t].id}`) % 1000) / 1000 + 0.5 * (j & 1)), 1));
    flow.setAttribute("aSpeed", new THREE.BufferAttribute(Float32Array.from({ length: k }, (_, j) =>
      0.16 + 0.12 * ((hash(nodes[this.links[this.typed[j >> 1]].t].id) % 100) / 100)), 1));
    flow.setAttribute("aAlpha", new THREE.BufferAttribute(new Float32Array(k).fill(0.85), 1));
    this.flow = new THREE.Points(flow, new THREE.ShaderMaterial({
      uniforms: this.uniforms, vertexShader: FLOW_VERTEX, fragmentShader: FLOW_FRAGMENT, transparent: true,
      depthWrite: false, depthTest: false, blending: THREE.AdditiveBlending }));
    this.flow.frustumCulled = false;
    this.flow.visible = !this.reduced;
    this.group.add(this.lines, this.flow, this.points);
    this.setColors(nodes.map((node) => node.color));
    this._syncLines();
    this._paint();
    this.fitted = 0;
    this._fit(true);
  }

  setColors(colors) {
    if (!this.points) return;
    const attribute = this.points.geometry.getAttribute("aColor"), color = new THREE.Color();
    colors.forEach((value, i) => { color.set(value); attribute.setXYZ(i, color.r, color.g, color.b); });
    attribute.needsUpdate = true;
  }

  has(id) { return this.index.has(id); }

  // the active node (hovered, else selected) stays bright with its neighbors; everything else dims
  setActive(id) {
    const node = id !== null && id !== undefined && this.index.has(id) ? this.index.get(id) : null;
    if (node === this.active) return;
    this.active = node;
    this._paint();
  }

  _paint() {
    if (!this.points) return;
    const state = this.points.geometry.getAttribute("aState");
    const alpha = this.lines.geometry.getAttribute("aAlpha"), color = this.lines.geometry.getAttribute("aColor");
    const active = this.active, near = active === null ? null : this.neighbors[active];
    for (let i = 0; i < this.nodes.length; i += 1) {
      state.setX(i, active === null ? 1 : i === active ? 2 : near.has(i) ? 1 : 0);
    }
    this.links.forEach((link, i) => {
      const touches = active !== null && (link.s === active || link.t === active);
      const base = link.typed ? EDGE_TYPED : EDGE;
      const a = active === null ? (link.typed ? 0.34 : 0.1 + Math.min(0.12, 0.03 * link.weight)) : touches ? 0.85 : 0.012;
      for (const v of [2 * i, 2 * i + 1]) { color.setXYZ(v, base.r, base.g, base.b); alpha.setX(v, a); }
    });
    const flowing = this.flow.geometry.getAttribute("aAlpha");
    this.typed.forEach((linkIndex, j) => {
      const link = this.links[linkIndex];
      const a = active === null ? 0.85 : (link.s === active || link.t === active) ? 1 : 0;
      flowing.setX(2 * j, a);
      flowing.setX(2 * j + 1, a);
    });
    state.needsUpdate = true;
    alpha.needsUpdate = true;
    color.needsUpdate = true;
    flowing.needsUpdate = true;
  }

  _syncLines() {
    const position = this.lines.geometry.getAttribute("position"), pos = this.layout.pos;
    this.links.forEach((link, i) => {
      position.setXYZ(2 * i, pos[3 * link.s], pos[3 * link.s + 1], pos[3 * link.s + 2]);
      position.setXYZ(2 * i + 1, pos[3 * link.t], pos[3 * link.t + 1], pos[3 * link.t + 2]);
    });
    position.needsUpdate = true;
    const from = this.flow.geometry.getAttribute("position"), to = this.flow.geometry.getAttribute("aEnd");
    this.typed.forEach((linkIndex, j) => {
      const { s, t } = this.links[linkIndex];
      for (const v of [2 * j, 2 * j + 1]) {
        from.setXYZ(v, pos[3 * s], pos[3 * s + 1], pos[3 * s + 2]);
        to.setXYZ(v, pos[3 * t], pos[3 * t + 1], pos[3 * t + 2]);
      }
    });
    from.needsUpdate = true;
    to.needsUpdate = true;
  }

  _fit(jump = false) {                                 // the camera backs off until the whole cloud is in view
    const radius = this.layout.radius();
    this.radius = radius;
    this.controls.minDistance = Math.max(18, radius * 0.12);
    this.controls.maxDistance = radius * 7;
    this.uniforms.uFar.value = radius * 4.2;
    const distance = radius * 2.7;
    if (jump) {
      const direction = this.flat ? new THREE.Vector3(0, 0, 1)
        : this.camera.position.clone().sub(this.controls.target).normalize();
      this.controls.target.set(0, 0, 0);
      this.camera.position.copy(direction.multiplyScalar(distance));
    } else if (!this.fly && this.active === null) {
      this.fly = { from: this.camera.position.clone(), to: this.camera.position.clone().sub(this.controls.target).normalize()
        .multiplyScalar(distance).add(this.controls.target), target: this.controls.target.clone(),
        targetTo: this.controls.target.clone(), start: performance.now(), duration: 700 };
    }
  }

  // 2D: the nodes go to one plane, the camera faces it and the drag pans. 3D: the volume and the orbit come back.
  setFlat(flat) {
    flat = Boolean(flat);
    if (flat === this.flat) return;
    this.flat = flat;
    this.controls.enableRotate = !flat;
    this.controls.screenSpacePanning = true;
    this.controls.mouseButtons.LEFT = flat ? THREE.MOUSE.PAN : THREE.MOUSE.ROTATE;
    this.controls.touches.ONE = flat ? THREE.TOUCH.PAN : THREE.TOUCH.ROTATE;
    if (!this.layout) return;
    this.layout.setFlat(flat);
    this.fitted = 0;
    const distance = (this.radius || 200) * 2.7;
    const to = flat ? new THREE.Vector3(0, 0, distance)
      : new THREE.Vector3(0.42, 0.26, 0.87).normalize().multiplyScalar(distance);
    this.fly = { from: this.camera.position.clone(), to, target: this.controls.target.clone(),
                 targetTo: new THREE.Vector3(0, 0, 0), start: performance.now(), duration: this.reduced ? 1 : 900 };
  }

  flyTo(id) {                                          // bring a node to the center, closer when the camera is far
    if (!this.index.has(id)) return;
    const i = this.index.get(id), pos = this.layout.pos;
    const to = new THREE.Vector3(pos[3 * i], pos[3 * i + 1], pos[3 * i + 2]);
    const offset = this.camera.position.clone().sub(this.controls.target);
    const distance = Math.min(offset.length(), Math.max(this.radius * 2.1, 110));   // most of its neighbors stay in view
    this.fly = { from: this.camera.position.clone(), to: to.clone().add(offset.normalize().multiplyScalar(distance)),
                 target: this.controls.target.clone(), targetTo: to, start: performance.now(), duration: this.reduced ? 1 : 650 };
  }

  _pick() {                                            // the node under the pointer: the closest to the eye wins
    if (!this.pointer || !this.nodes.length) return null;
    let best = null, bestDepth = Infinity;
    for (let i = 0; i < this.nodes.length; i += 1) {
      const depth = this.screen[4 * i + 3];
      if (depth <= 0) continue;
      const reach = Math.max(7, this.screen[4 * i + 2] * 0.4);
      if (Math.hypot(this.screen[4 * i] - this.pointer.x, this.screen[4 * i + 1] - this.pointer.y) <= reach && depth < bestDepth) {
        best = i;
        bestDepth = depth;
      }
    }
    return best;
  }

  _hover(node) {
    if (node === this.hovered) return;
    this.hovered = node;
    this.canvas.style.cursor = node === null ? "grab" : "pointer";
    if (this.handlers.onHover) this.handlers.onHover(node === null ? null : this.nodes[node].id);
  }

  _project() {
    const width = this.canvas.clientWidth, height = this.canvas.clientHeight, pos = this.layout.pos;
    const m = new THREE.Matrix4().multiplyMatrices(this.camera.projectionMatrix, this.camera.matrixWorldInverse).elements;
    const scale = this.uniforms.uScale.value / (this.renderer.getPixelRatio() || 1);
    for (let i = 0; i < this.nodes.length; i += 1) {
      const x = pos[3 * i], y = pos[3 * i + 1], z = pos[3 * i + 2];
      const w = m[3] * x + m[7] * y + m[11] * z + m[15];
      if (w <= 0.001) { this.screen[4 * i + 3] = 0; continue; }
      this.screen[4 * i] = ((m[0] * x + m[4] * y + m[8] * z + m[12]) / w * 0.5 + 0.5) * width;
      this.screen[4 * i + 1] = (0.5 - (m[1] * x + m[5] * y + m[9] * z + m[13]) / w * 0.5) * height;
      this.screen[4 * i + 2] = (SPRITE * this.nodes[i].size * scale) / w;  // the sprite's diameter on screen
      this.screen[4 * i + 3] = w;
    }
  }

  _labels() {                                          // names for the active node and its neighbors, else the biggest
    const width = this.canvas.clientWidth, height = this.canvas.clientHeight;
    const active = this.active;
    let wanted;
    if (active !== null) {
      const near = [...this.neighbors[active]].sort((a, b) => this.nodes[b].size - this.nodes[a].size);
      wanted = [active, ...near];
    } else {
      wanted = this.byWeight;
    }
    const placed = [];
    let used = 0;
    for (const i of wanted) {
      if (used >= MAX_LABELS) break;
      const depth = this.screen[4 * i + 3];
      if (depth <= 0) continue;
      const x = this.screen[4 * i], y = this.screen[4 * i + 1], reach = this.screen[4 * i + 2] * 0.2 + 5;
      if (x < -40 || x > width + 40 || y < 0 || y > height) continue;
      const label = this.nodes[i].label, strong = i === active || i === this.hovered;
      const box = { left: x + reach - 3, right: x + reach + 6.3 * Math.min(label.length, 44) + 8, top: y - 9, bottom: y + 9 };
      if (!strong && placed.some((p) => box.left < p.right && box.right > p.left && box.top < p.bottom && box.bottom > p.top)) continue;
      placed.push(box);
      let element = this.pool[used];
      if (!element) {
        element = document.createElement("div");
        this.labels.append(element);
        this.pool.push(element);
      }
      if (element.dataset.node !== String(i)) {
        element.dataset.node = String(i);
        element.textContent = label.length > 44 ? `${label.slice(0, 43)}…` : label;
      }
      element.className = strong ? "label3d strong" : "label3d";
      element.style.transform = `translate(${Math.round(x + reach)}px, ${Math.round(y)}px) translateY(-50%)`;
      element.style.opacity = strong ? "1" : String(Math.min(1, 0.35 + 0.65 * Math.min(1, this.radius * 2.2 / depth)));
      element.hidden = false;
      used += 1;
    }
    for (let k = used; k < this.pool.length; k += 1) this.pool[k].hidden = true;
  }

  _loop() {
    this.frame = requestAnimationFrame(() => this._loop());
    if (!this.container.offsetParent || !this.layout) return;      // another tab is showing
    const now = performance.now();
    const elapsed = now - (this.lastFrame || now);
    this.lastFrame = now;
    if (!this.layout.done) {
      // three ticks a frame at 60 frames a second: the cloud unfolds in about two seconds; a slow or throttled
      // window gets more ticks per frame, so the graph never takes minutes to settle
      const ticks = Math.max(3, Math.min(14, Math.round(elapsed / 5.5)));
      for (let k = 0; k < ticks && !this.layout.done; k += 1) this.layout.tick();
      this.points.geometry.getAttribute("position").needsUpdate = true;
      this._syncLines();
      this.fitted += 1;
      if (this.fitted % 45 === 0 || this.layout.done) this._fit();
    }
    if (this.fly) {
      const t = Math.min(1, (now - this.fly.start) / this.fly.duration), e = 1 - (1 - t) ** 3;
      this.camera.position.lerpVectors(this.fly.from, this.fly.to, e);
      this.controls.target.lerpVectors(this.fly.target, this.fly.targetTo, e);
      if (t >= 1) this.fly = null;
    }
    this.controls.autoRotate = !this.reduced && !this.flat && this.hovered === null && !this.press
      && now - this.lastTouch > 4000;
    this.controls.update();
    this.uniforms.uTime.value = (now - this.started) / 1000;
    this.dust.rotation.y += 0.00012;
    this.camera.updateMatrixWorld();
    this.renderer.render(this.scene, this.camera);
    this._project();
    this._labels();
    if (this.pointer && !this.press) this._hover(this._pick());
  }

  resize() {
    const width = this.container.clientWidth, height = this.container.clientHeight;
    if (!width || !height) return;
    this.renderer.setSize(width, height, false);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.uniforms.uAspect.value = width / height;
    const buffer = this.renderer.getDrawingBufferSize(new THREE.Vector2());
    this.uniforms.uScale.value = buffer.y / (2 * Math.tan(THREE.MathUtils.degToRad(this.camera.fov) / 2));
  }

  dispose() {
    cancelAnimationFrame(this.frame);
    for (const [name, handler] of [["pointermove", this.on.move], ["pointermove", this.on.drag], ["pointerleave", this.on.leave],
                                   ["pointerdown", this.on.down], ["pointerup", this.on.up], ["dblclick", this.on.double],
                                   ["wheel", this.on.wheel]]) this.canvas.removeEventListener(name, handler);
    this.controls.dispose();
    this.scene.traverse((object) => {
      if (object.geometry) object.geometry.dispose();
      if (object.material) object.material.dispose();
    });
    this.renderer.dispose();
    this.container.replaceChildren();
  }
}

export function supported() {
  try {
    const canvas = document.createElement("canvas");
    return Boolean(window.WebGL2RenderingContext && canvas.getContext("webgl2"));
  } catch (e) {
    return false;
  }
}
