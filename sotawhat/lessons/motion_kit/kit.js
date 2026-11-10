/* sotawhat lessons · HyperFrames kit (2D templates, ground, intro, captions). The 3D template is scene3d.js.
   Every scene is a sub-composition whose script calls MK.scene(id, data): the kit builds the DOM, waits for the
   fonts, measures once, lays the diagram out, routes the links between the borders of the parts, and writes one
   paused GSAP timeline in which every tween is a fromTo from the state the previous tween left (seek-safe). */
(function () {
  "use strict";
  const W = 1920, H = 1080;
  const ROLE = { token: "#a9b6cc", embedding: "#c9d2e0", query: "#4ea1ff", key: "#3ddc97", value: "#ff9f45",
    score: "#ffd54a", weight: "#b48cff", output: "#ff5c70", neutral: "#8f9cb4", alert: "#ff6f91", info: "#2dd4d0" };
  const FACES = ["400 30px Manrope", "500 30px Manrope", "600 30px Manrope", "700 30px Manrope", "800 30px Manrope",
    "400 30px Fraunces", "600 30px Fraunces", "italic 600 30px Fraunces"];
  const SAMPLE = "AaÁãâçéêíóôõúÇ0123456789·×÷→√%,.";
  const GAPX_MIN = 120, GAPX_MAX = 250, GAPY = 46;
  const DEFAULTS = { opacity: 1, scale: 1, x: 0, y: 0, scaleX: 1, scaleY: 1, filter: "blur(0px)", strokeDashoffset: 0 };

  function rootOf(id) {   // the scene root: the innermost element with that composition id (the host has it too)
    const all = document.querySelectorAll(`[data-composition-id="${id}"]`);
    return all[all.length - 1];
  }
  function fontsReady() {
    return Promise.all(FACES.map((f) => document.fonts.load(f, SAMPLE))).then(() => document.fonts.ready);
  }
  function el(tag, cls, parent, html) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html !== undefined) e.innerHTML = html;
    if (parent) parent.appendChild(e);
    return e;
  }
  function svgEl(tag, attrs, parent) {
    const e = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  function rich(s) {   // W_Q → W<sub>Q</sub>
    return esc(s).replace(/([A-Za-zΑ-ω])_\{?([A-Za-z0-9]+)\}?/g, "$1<sub>$2</sub>");
  }
  function hash(s) {
    let h = 2166136261;
    for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
    return h >>> 0;
  }
  function rng(seed) {   // mulberry32
    let a = seed >>> 0;
    return function () {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function num(v, digits) {
    const d = digits === undefined ? (Math.abs(v) >= 10 ? 1 : (Math.abs(v) >= 1 ? 1 : 2)) : digits;
    return v.toFixed(d).replace(".", ",").replace("-", "−");
  }
  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function decOf(v) { return Number.isInteger(v) ? 0 : (Math.abs(v) >= 10 ? 1 : 2); }
  function fmtv(v) { return num(v, decOf(v)); }      // 45 → "45", −1000 → "−1000", 0.62 → "0,62"

  /* ---- seek-safe tweens: each fromTo starts where the previous tween of that property ended ---------------- */
  function Track(tl) {
    const state = new Map();
    function cur(e) { if (!state.has(e)) state.set(e, {}); return state.get(e); }
    return {
      tl,
      init(e, props) { gsap.set(e, props); Object.assign(cur(e), props); },
      to(e, props, at, dur, ease) {
        const c = cur(e), from = {};
        for (const k in props) from[k] = k in c ? c[k] : DEFAULTS[k];
        tl.fromTo(e, from, Object.assign({}, props, { duration: dur === undefined ? 0.6 : dur,
          ease: ease || "power3.out", immediateRender: false }), Math.max(0, at));
        Object.assign(c, props);
      },
      get(e, k) { const c = cur(e); return k in c ? c[k] : DEFAULTS[k]; },
      count(target, from, to, at, dur, fmt, ease) {   // a number that counts, drawn from a proxy (seek-safe)
        const proxy = { v: from };
        tl.fromTo(proxy, { v: from }, { v: to, duration: dur, ease: ease || "power2.out", immediateRender: false,
          onUpdate: () => { target.textContent = fmt(proxy.v); } }, Math.max(0, at));
      },
    };
  }
  const appear = (T, e, at, d) => T.to(e, { opacity: 1, scale: 1, filter: "blur(0px)" }, at, d || 0.55, "expo.out");
  const vanish = (T, e, at, d) => T.to(e, { opacity: 0, filter: "blur(6px)" }, at, d || 0.28, "power2.in");

  /* ---- shared pieces --------------------------------------------------------------------------------------- */
  function header(T, stage, num, title) {
    const head = el("div", "mk-head", stage);
    const n = el("div", "mk-head-num", head, String(num).padStart(2, "0"));
    const t = el("div", "mk-head-title", head, title.split(/\s+/).map((w) => `<span>${esc(w)}</span>`).join(" "));
    T.init(n, { opacity: 0, filter: "blur(8px)" });
    T.to(n, { opacity: 1, filter: "blur(0px)" }, 0.08, 0.5, "power4.out");
    [...t.children].forEach((w, i) => {
      T.init(w, { opacity: 0, filter: "blur(6px)" });
      T.to(w, { opacity: 1, filter: "blur(0px)" }, 0.18 + i * 0.067, 0.16, "power2.out");
    });
  }
  function exit(T, stage, dur) {
    T.to(stage, { opacity: 0, filter: "blur(8px)" }, dur - 0.34, 0.3, "power2.in");
  }
  function overlap(a, b, m) {
    return a.x < b.x + b.w + m && b.x < a.x + a.w + m && a.y < b.y + b.h + m && b.y < a.y + a.h + m;
  }
  function notes(ctx) {   // annotation chips: next to the anchor where nothing else is, else stacked top right
    const placed = [];
    const free = (r) => r.x >= 120 && r.x + r.w <= W - 120 && r.y >= 150 && r.y + r.h <= 878 &&
      !(ctx.obstacles || []).some((o) => overlap(r, o, 10)) && !placed.some((p) => overlap(r, p, 8));
    return function (a, A, role) {
      const n = el("div", `mk-note mk-r-${role || "info"}`, ctx.layer, `<i></i>${esc(a.text)}`);
      const w = n.offsetWidth, h = n.offsetHeight;
      let r = null;
      if (A) {
        const cands = [{ x: A.x + A.w / 2 - w / 2, y: A.y + A.h + 22 }, { x: A.x + A.w / 2 - w / 2, y: A.y - h - 22 },
          { x: A.x + A.w + 24, y: A.y + A.h / 2 - h / 2 }, { x: A.x - w - 24, y: A.y + A.h / 2 - h / 2 }];
        for (const c of cands) { const rr = { x: c.x, y: c.y, w, h }; if (free(rr)) { r = rr; break; } }
      }
      if (!r) {
        let y = 178, rr;
        do { rr = { x: W - 140 - w, y, w, h }; y += h + 14; } while (!free(rr) && y < 820);
        r = rr;
      }
      placed.push(r);
      n.style.left = r.x + "px"; n.style.top = r.y + "px";
      ctx.T.init(n, { opacity: 0, x: -12, filter: "blur(6px)" });
      ctx.T.to(n, { opacity: 1, x: 0, filter: "blur(0px)" }, a.t, 0.45, "expo.out");
      return n;
    };
  }
  function formula(ctx, parts) {
    if (!parts || !parts.length) return null;
    const row = el("div", "mk-formula", ctx.stage);
    const map = {};
    for (const p of parts) {
      const s = el("span", "mk-fpart", row);
      try { s.innerHTML = katex.renderToString(p.tex, { throwOnError: false, output: "html" }); }
      catch (e) { s.textContent = p.tex; }
      map[p.id] = s;
    }
    ctx.T.init(row, { opacity: 0, filter: "blur(8px)" });
    return { row, map, shown: false };
  }
  function formulaAction(ctx, f, a) {
    if (!f) return;
    if (!f.shown) { ctx.T.to(f.row, { opacity: 1, filter: "blur(0px)" }, a.t, 0.5, "power4.out"); f.shown = true; }
    const ids = a.ids.filter((i) => f.map[i]);
    for (const id in f.map) {
      const on = !ids.length || ids.includes(id);
      ctx.T.to(f.map[id], { opacity: on ? 1 : 0.35 }, a.t + 0.05, 0.35, "power2.out");
    }
  }

  /* ---- graph ------------------------------------------------------------------------------------------------- */
  function buildNode(n, labels) {
    const root = el("div", `mk-node mk-${n.kind} mk-r-${n.role}`);
    const inner = el("div", "mk-node-in", root);
    const halo = el("div", "mk-halo", inner);
    const texts = labels.length ? labels : [n.label];
    const stack = (cls) => {
      const box = el("div", cls);
      box.style.display = "grid";
      const spans = texts.map((t, i) => { const s = el("span", "", box, rich(t)); s.style.gridArea = "1 / 1"; if (i) s.style.opacity = "0"; return s; });
      return { box, spans };
    };
    let card, label;
    if (n.kind === "vector") {
      el("div", "mk-vlabel", inner, rich(n.label));
      card = el("div", "mk-card", inner);
      const vals = n.values && n.values.length ? n.values : [0.2, -1.4, 0.7];
      const dec = Math.min(2, Math.max(...vals.map((v) => { const s = String(Math.abs(v)); return s.includes(".") ? s.split(".")[1].length : 0; })));
      const cells = vals.map((v) => el("div", "mk-vcell", card, num(v, dec)));
      if (n.gloss) el("div", "mk-gloss", inner, esc(n.gloss));
      return { root, inner, halo, card, cells, spans: [] };
    }
    if (n.kind === "stat") {
      label = stack("mk-statnum");
      inner.appendChild(label.box);
      if (n.gloss) el("div", "mk-gloss", inner, esc(n.gloss));
      return { root, inner, halo, card: label.box, spans: label.spans };
    }
    if (n.kind === "stack") {
      const s1 = el("div", "mk-stack-sheet", inner), s2 = el("div", "mk-stack-sheet", inner);
      s1.style.transform = "translate(16px, -14px)"; s2.style.transform = "translate(8px, -7px)";
    }
    card = el("div", "mk-card", inner);
    if (n.kind === "matrix") {
      const g = el("div", "mk-mgrid", card), r = rng(hash(n.id));
      for (let i = 0; i < 9; i++) el("i", "", g).style.opacity = (0.25 + 0.75 * r()).toFixed(2);
      const right = el("div", "", card);
      label = stack("mk-label"); right.appendChild(label.box);
      if (n.gloss) el("div", "mk-gloss", right, rich(n.gloss));
    } else {
      label = stack("mk-label"); card.appendChild(label.box);
      if (n.gloss) el("div", "mk-gloss", card, rich(n.gloss));
    }
    if (n.kind === "stack") {
      [...inner.querySelectorAll(".mk-stack-sheet")].forEach((s) => { s.style.width = "auto"; });
    }
    return { root, inner, halo, card, spans: label.spans };
  }

  function layoutPanel(nodes, area) {
    const cols = [...new Set(nodes.map((n) => n.col))].sort((a, b) => a - b);
    const byCol = cols.map((c) => nodes.filter((n) => n.col === c).sort((a, b) => a.row - b.row));
    const colW = byCol.map((ns) => Math.max(...ns.map((n) => n.w)));
    const colH = byCol.map((ns) => ns.reduce((s, n) => s + n.h, 0) + GAPY * (ns.length - 1));
    const sumW = colW.reduce((a, b) => a + b, 0);
    const availW = area.x1 - area.x0, availH = area.y1 - area.y0;
    const gap = cols.length > 1 ? clamp((availW - sumW) / (cols.length - 1), GAPX_MIN, GAPX_MAX) : 0;
    const totalW = sumW + gap * (cols.length - 1);
    const scale = Math.min(1.25, availW / totalW, availH / Math.max(...colH));   // a small diagram grows to fill
    const cy = (area.y0 + area.y1) / 2;
    let x = (area.x0 + area.x1) / 2 - totalW / 2;
    byCol.forEach((ns, i) => {
      let y = 0;
      const tops = ns.map((n) => { const t = y; y += n.h + GAPY; return t; });
      // centre the column on the card centres of its first and last node (cards align across columns)
      const c0 = tops[0] + ns[0].cardCy, c1 = tops[ns.length - 1] + ns[ns.length - 1].cardCy;
      const shift = cy - (c0 + c1) / 2;
      ns.forEach((n, k) => { n.x = x + (colW[i] - n.w) / 2; n.y = tops[k] + shift; });
      x += colW[i] + gap;
    });
    return { scale, cols, colX: byCol.map((ns) => [Math.min(...ns.map((n) => n.x)), Math.max(...ns.map((n) => n.x + n.w))]),
      colY: byCol.map((ns) => [Math.min(...ns.map((n) => n.y)), Math.max(...ns.map((n) => n.y + n.h))]) };
  }

  function bezierPath(pts) {   // horizontal-tangent cubic segments through the points
    let d = `M ${pts[0].x} ${pts[0].y}`;
    for (let i = 1; i < pts.length; i++) {
      const a = pts[i - 1], b = pts[i], k = Math.max(30, Math.abs(b.x - a.x) * 0.45);
      d += ` C ${a.x + k} ${a.y}, ${b.x - k} ${b.y}, ${b.x} ${b.y}`;
    }
    return d;
  }

  function graph(ctx) {
    const { data, T } = ctx;
    const labelsOf = {};
    for (const a of data.actions) if (a.do === "label") for (const id of a.ids) (labelsOf[id] = labelsOf[id] || []).push(a.text);
    const panels = { 1: el("div", "mk-panel", ctx.stage), 2: el("div", "mk-panel", ctx.stage) };
    const svgs = { 1: svgEl("svg", { class: "mk-edges", viewBox: `0 0 ${W} ${H}` }, panels[1]),
      2: svgEl("svg", { class: "mk-edges", viewBox: `0 0 ${W} ${H}` }, panels[2]) };
    const defs = svgEl("defs", {}, svgs[1]);
    const nodes = {}, edges = {};
    for (const n of data.nodes) {
      const texts = labelsOf[n.id] ? [n.label, ...labelsOf[n.id]] : [];
      const b = buildNode(n, texts);
      panels[n.panel].appendChild(b.root);
      nodes[n.id] = Object.assign({}, n, b, { labelIndex: 0 });
    }
    // measure once (fonts are loaded), then lay out each panel
    for (const id in nodes) {
      const n = nodes[id];
      n.w = n.inner.offsetWidth; n.h = n.inner.offsetHeight;
      n.cardX = n.card.offsetLeft; n.cardY = n.card.offsetTop; n.cardW = n.card.offsetWidth; n.cardH = n.card.offsetHeight;
      if (n.kind === "vector") { n.cardY = n.card.offsetTop; }
      n.cardCy = n.cardY + n.cardH / 2;
    }
    const geo = {};
    for (const p of [1, 2]) {
      const ns = Object.values(nodes).filter((n) => n.panel === p);
      if (!ns.length) continue;
      geo[p] = layoutPanel(ns, ctx.area);
      if (Math.abs(geo[p].scale - 1) > 0.01) panels[p].style.transform = `scale(${geo[p].scale.toFixed(4)})`;
    }
    for (const id in nodes) {
      const n = nodes[id];
      n.root.style.left = n.x + "px"; n.root.style.top = n.y + "px";
      n.rect = { x: n.x + n.cardX, y: n.y + n.cardY, w: n.cardW, h: n.cardH };
      n.rect.cy = n.rect.y + n.rect.h / 2; n.rect.cx = n.rect.x + n.rect.w / 2;
      T.init(n.inner, { opacity: 0, scale: 0.92, filter: "blur(6px)" });
      T.init(n.halo, { opacity: 0 });
    }
    // incoming ports spread along the target border when several links arrive at the same side
    const incoming = {};
    for (const e of data.edges) (incoming[e.target] = incoming[e.target] || []).push(e);
    for (const e of data.edges) {
      const s = nodes[e.source], t = nodes[e.target];
      if (!s || !t) continue;
      const ins = incoming[e.target].filter((x) => nodes[x.source] && nodes[x.source].col < t.col)
        .sort((a, b) => nodes[a.source].rect.cy - nodes[b.source].rect.cy);
      let pts;
      if (t.col > s.col) {
        const k = ins.indexOf(e), m = ins.length;
        const spread = m > 1 ? (k - (m - 1) / 2) * Math.min(26, (t.rect.h * 0.6) / (m - 1)) : 0;
        const start = { x: s.rect.x + s.rect.w + 12, y: s.rect.cy };
        const end = { x: t.rect.x - 16, y: t.rect.cy + spread };
        if (Math.abs(end.y - start.y) < 7) end.y = start.y;          // a nearly flat link is drawn flat
        pts = [start, end];
        // a link that jumps columns goes around the parts in between
        const g = geo[s.panel];
        for (let ci = 0; ci < g.cols.length; ci++) {
          const c = g.cols[ci];
          if (c <= s.col || c >= t.col) continue;
          const mid = (g.colX[ci][0] + g.colX[ci][1]) / 2;
          const yAt = start.y + (end.y - start.y) * ((mid - start.x) / (end.x - start.x));
          const blockers = Object.values(nodes).filter((o) => o.panel === s.panel && o.col === c && yAt > o.rect.y - 26 && yAt < o.rect.y + o.rect.h + 26);
          if (blockers.length) {
            const above = g.colY[ci][0] - 40, below = g.colY[ci][1] + 40;
            const wy = Math.abs(above - yAt) <= Math.abs(below - yAt) && above > ctx.area.y0 - 20 ? above : below;
            pts.splice(pts.length - 1, 0, { x: mid, y: wy });
          }
        }
      } else if (t.col === s.col) {
        const down = t.rect.cy > s.rect.cy;
        const start = { x: s.rect.cx, y: down ? s.rect.y + s.rect.h + 10 : s.rect.y - 10 };
        const end = { x: t.rect.cx, y: down ? t.rect.y - 14 : t.rect.y + t.rect.h + 14 };
        pts = [start, end];
        pts.vertical = true;
      } else {
        const top = Math.min(s.rect.y, t.rect.y) - 70;
        pts = [{ x: s.rect.cx, y: s.rect.y - 10 }, { x: t.rect.cx, y: t.rect.y - 14 }];
        pts.arc = Math.max(ctx.area.y0 - 30, top);
      }
      let d;
      if (pts.vertical) {
        const [a, b] = pts, k = Math.abs(b.y - a.y) * 0.4;
        d = `M ${a.x} ${a.y} C ${a.x} ${a.y + Math.sign(b.y - a.y) * k}, ${b.x} ${b.y - Math.sign(b.y - a.y) * k}, ${b.x} ${b.y}`;
      } else if (pts.arc !== undefined) {
        const [a, b] = pts;
        d = `M ${a.x} ${a.y} C ${a.x} ${pts.arc}, ${b.x} ${pts.arc}, ${b.x} ${b.y}`;
      } else d = bezierPath(pts);
      const color = ROLE[e.role] || ROLE.neutral, from = ROLE[s.role] || color;
      const gid = `${ctx.id}-g-${e.id}`;
      const grad = svgEl("linearGradient", { id: gid, gradientUnits: "userSpaceOnUse", x1: pts[0].x, y1: pts[0].y,
        x2: pts[pts.length - 1].x, y2: pts[pts.length - 1].y }, defs);
      svgEl("stop", { offset: "0", "stop-color": from, "stop-opacity": "0.55" }, grad);
      svgEl("stop", { offset: "1", "stop-color": color, "stop-opacity": "1" }, grad);
      const group = svgEl("g", {}, svgs[s.panel]);
      const path = svgEl("path", { d, class: "mk-edge", stroke: `url(#${gid})` }, group);
      const len = path.getTotalLength();
      const end = path.getPointAtLength(len), before = path.getPointAtLength(Math.max(0, len - 6));
      const ang = Math.atan2(end.y - before.y, end.x - before.x);
      const tip = { x: end.x + Math.cos(ang) * 10, y: end.y + Math.sin(ang) * 10 };
      const bl = { x: tip.x - Math.cos(ang) * 20 + Math.cos(ang + Math.PI / 2) * 9, y: tip.y - Math.sin(ang) * 20 + Math.sin(ang + Math.PI / 2) * 9 };
      const br = { x: tip.x - Math.cos(ang) * 20 - Math.cos(ang + Math.PI / 2) * 9, y: tip.y - Math.sin(ang) * 20 - Math.sin(ang + Math.PI / 2) * 9 };
      const head = svgEl("path", { d: `M ${tip.x} ${tip.y} L ${bl.x} ${bl.y} L ${br.x} ${br.y} Z`, fill: color }, group);
      const samples = [];
      for (let i = 0; i <= 80; i++) { const p = path.getPointAtLength((len * i) / 80); samples.push([p.x, p.y]); }
      path.setAttribute("stroke-dasharray", `${len} ${len + 40}`);
      T.init(path, { strokeDashoffset: len, opacity: 0 });   // hidden: a round cap would leave a dot
      T.init(head, { opacity: 0 });
      const mid = path.getPointAtLength(len * ((incoming[e.target] || []).length > 1 ? 0.34 : 0.5));
      let pill = null, spans = [];
      const texts = [e.label, ...(labelsOf[e.id] || [])].filter((x) => x);
      if (texts.length) {
        pill = el("div", `mk-elabel mk-r-${e.role === "neutral" ? "score" : e.role}`, panels[s.panel]);
        pill.style.display = "grid";
        spans = texts.map((t, i) => { const sp = el("span", "", pill, esc(t)); sp.style.gridArea = "1 / 1"; sp.style.textAlign = "center"; if (i) sp.style.opacity = "0"; return sp; });
        const flat = Math.abs(end.y - samples[0][1]) < Math.abs(end.x - samples[0][0]);
        pill.style.left = (mid.x - pill.offsetWidth / 2) + "px";
        pill.style.top = (mid.y - pill.offsetHeight / 2 - (flat ? 30 : 0)) + "px";
        if (!flat) pill.style.left = (mid.x + 18) + "px";
        T.init(pill, { opacity: 0, scale: 0.8 });
      }
      edges[e.id] = Object.assign({}, e, { path, head, len, samples, pill, spans, group, color, labelIndex: e.label ? 0 : -1, shown: false });
    }

    const obstacles = { 1: [], 2: [] };
    for (const id in nodes) {
      const n = nodes[id], s = geo[n.panel].scale, c = { x: 960, y: 520 };
      obstacles[n.panel].push({ x: c.x + (n.x - c.x) * s, y: c.y + (n.y - c.y) * s, w: n.w * s, h: n.h * s });
    }
    ctx.obstacles = obstacles[1].slice();
    const visible = new Set();
    const note = notes(ctx);
    const F = formula(ctx, data.formula);
    const touching = (id) => Object.values(edges).filter((e) => e.source === id || e.target === id);
    const showNode = (n, at, i) => {
      if (visible.has(n.id)) return;
      visible.add(n.id);
      appear(T, n.inner, at + i * 0.08, n.kind === "stat" ? 0.7 : 0.55);
      if (n.cells) n.cells.forEach((c, k) => { T.init(c, { opacity: 0, x: -10 }); T.to(c, { opacity: 1, x: 0 }, at + 0.15 + k * 0.06, 0.35, "power3.out"); });
      if (n.kind === "stat") {
        const v = parseFloat(String(n.label).replace(",", "."));
        if (!isNaN(v) && n.spans[0]) {
          const dec = (String(n.label).split(/[.,]/)[1] || "").length;
          T.count(n.spans[0], 0, v, at, 1.1, (x) => num(x, dec), "power3.out");
        }
      }
    };
    const showEdge = (e, at) => {
      if (e.shown) return;
      e.shown = true;
      visible.add(e.id);
      T.to(e.path, { opacity: 1 }, at, 0.05, "none");
      T.to(e.path, { strokeDashoffset: 0 }, at, 0.7, "power2.inOut");
      T.to(e.head, { opacity: 1 }, at + 0.58, 0.16, "power2.out");
      if (e.pill && e.labelIndex >= 0) T.to(e.pill, { opacity: 1, scale: 1 }, at + 0.5, 0.35, "back.out(1.6)");
    };
    const hideEdge = (e, at) => {
      if (!e.shown) return;
      e.shown = false; visible.delete(e.id);
      T.to(e.path, { opacity: 0 }, at, 0.25, "power2.in");
      T.to(e.head, { opacity: 0 }, at, 0.2, "power2.in");
      if (e.pill) T.to(e.pill, { opacity: 0, scale: 0.9 }, at, 0.2, "power2.in");
    };
    const level = (id, op, at) => {
      if (nodes[id]) { if (visible.has(id)) T.to(nodes[id].inner, { opacity: op }, at, 0.4, "power2.out"); }
      else if (edges[id] && edges[id].shown) {
        const e = edges[id];
        T.to(e.path, { opacity: op }, at, 0.4, "power2.out"); T.to(e.head, { opacity: op }, at, 0.4, "power2.out");
        if (e.pill && e.labelIndex >= 0) T.to(e.pill, { opacity: op }, at, 0.4, "power2.out");
      }
    };
    const halo = (id, op, at, d) => { if (nodes[id]) T.to(nodes[id].halo, { opacity: op }, at, d || 0.45, "power2.out"); };

    let panel = 1;
    for (const a of data.actions) {
      const at = a.t;
      const ids = a.ids.filter((i) => nodes[i] || edges[i]);
      if (a.do === "show") {
        let k = 0;
        for (const id of ids) if (nodes[id]) showNode(nodes[id], at, k++);
        for (const id of ids) if (edges[id]) {
          const e = edges[id];
          showNode(nodes[e.source], at, 0); showNode(nodes[e.target], at, 0);
          showEdge(e, at + 0.12 + 0.1 * k++);
        }
      } else if (a.do === "hide") {
        for (const id of ids) {
          if (nodes[id] && visible.has(id)) {
            visible.delete(id); vanish(T, nodes[id].inner, at); T.to(nodes[id].halo, { opacity: 0 }, at, 0.2);
            touching(id).forEach((e) => hideEdge(e, at));
          } else if (edges[id]) hideEdge(edges[id], at);
        }
      } else if (a.do === "focus") {
        const keep = new Set(ids);
        for (const id of ids) if (edges[id]) { keep.add(edges[id].source); keep.add(edges[id].target); }
        for (const id of [...visible]) {
          if (nodes[id]) { level(id, keep.has(id) ? 1 : 0.26, at); halo(id, keep.has(id) ? 0.75 : 0, at); }
          else if (edges[id]) { const e = edges[id]; level(id, ids.includes(id) || (keep.has(e.source) && keep.has(e.target)) ? 1 : 0.16, at); }
        }
      } else if (a.do === "unfocus") {
        for (const id of [...visible]) { level(id, 1, at); halo(id, 0, at); }
      } else if (a.do === "dim") {
        for (const id of ids) {
          level(id, 0.24, at); halo(id, 0, at);
          if (nodes[id]) touching(id).forEach((e) => level(e.id, 0.16, at));
        }
      } else if (a.do === "pulse") {
        for (const id of ids) {
          if (nodes[id]) {
            halo(id, 0.95, at, 0.3); halo(id, 0.35, at + 0.45, 0.6);
            T.to(nodes[id].inner, { scale: 1.06 }, at, 0.3, "power2.out"); T.to(nodes[id].inner, { scale: 1 }, at + 0.32, 0.5, "power3.out");
          } else if (edges[id] && edges[id].shown) {
            const e = edges[id];
            T.to(e.path, { opacity: 1 }, at, 0.2); flow(e, at, 1.6);
          }
        }
      } else if (a.do === "label") {
        for (const id of ids) {
          const target = nodes[id] || edges[id];
          if (!target || !target.spans.length) continue;
          const next = target.labelIndex + 1;
          if (next >= target.spans.length) continue;
          if (target.labelIndex >= 0) T.to(target.spans[target.labelIndex], { opacity: 0 }, at, 0.25, "power2.in");
          T.init(target.spans[next], { opacity: 0 });
          T.to(target.spans[next], { opacity: 1 }, at + 0.15, 0.35, "power2.out");
          if (edges[id] && target.labelIndex < 0 && target.shown) T.to(target.pill, { opacity: 1, scale: 1 }, at, 0.35, "back.out(1.6)");
          target.labelIndex = next;
        }
      } else if (a.do === "flow") {
        for (const id of ids) if (edges[id] && edges[id].shown) flow(edges[id], at, Math.max(1.2, (a.until || at + 2.4) - at));
      } else if (a.do === "panel") {
        if (panel === 1 && panels[2].childElementCount > 1) {
          for (const id of [...visible]) if (nodes[id] && nodes[id].panel === 1) visible.delete(id);
          for (const id in edges) if (edges[id].panel !== 2 && nodes[edges[id].source].panel === 1) edges[id].shown = false;
          T.to(panels[1], { opacity: 0, filter: "blur(8px)" }, at, 0.32, "power2.in");
          ctx.obstacles.length = 0; ctx.obstacles.push(...obstacles[2]);
          ctx.layer.querySelectorAll(".mk-note").forEach((n) => T.to(n, { opacity: 0 }, at, 0.25, "power2.in"));
          panel = 2;
        }
      } else if (a.do === "note") {
        const anchor = ids.length && nodes[ids[0]] ? nodes[ids[0]] : null;
        let rect = null;
        if (anchor) {
          const s = geo[anchor.panel].scale, c = { x: 960, y: 520 };
          rect = { x: c.x + (anchor.rect.x - c.x) * s, y: c.y + (anchor.rect.y - c.y) * s, w: anchor.rect.w * s, h: anchor.rect.h * s };
        }
        note(a, rect, anchor ? anchor.role : "info");
      } else if (a.do === "formula") formulaAction(ctx, F, a);
    }

    function flow(e, at, span) {
      const r = rng(hash(e.id + at.toFixed(2)));
      for (let k = 0; k < 3; k++) {
        const dot = svgEl("circle", { r: 6, fill: e.color, class: "mk-flowdot" }, e.group);
        dot.style.color = e.color;
        T.init(dot, { opacity: 0 });
        const cycle = 1.15, start = at + k * 0.38 + r() * 0.05;
        const reps = Math.max(1, Math.floor((span - k * 0.38) / cycle));
        const proxy = { p: 0 };
        const place = () => {
          const f = proxy.p * 80, i = Math.min(79, Math.floor(f)), u = f - i;
          const [x0, y0] = e.samples[i], [x1, y1] = e.samples[i + 1];
          dot.setAttribute("cx", x0 + (x1 - x0) * u); dot.setAttribute("cy", y0 + (y1 - y0) * u);
        };
        T.tl.fromTo(proxy, { p: 0 }, { p: 1, duration: cycle, ease: "none", repeat: reps - 1, immediateRender: false, onUpdate: place }, start);
        T.to(dot, { opacity: 1 }, start, 0.15);
        T.to(dot, { opacity: 0 }, start + reps * cycle - 0.15, 0.15);
      }
    }
  }

  /* ---- bars: scores → ÷√d → softmax weights ------------------------------------------------------------------ */
  function plainBars(ctx) {   // raw quantities (densities, a metric by group): bars from a zero line, negatives down
    const { data, T } = ctx;
    const items = data.bars, n = items.length;
    const iw = Math.min(230, 1500 / n), gap = Math.min(80, iw * 0.4), total = n * iw + (n - 1) * gap;
    const x0 = 960 - total / 2, top = ctx.area.y0 + 80, bottom = 790;
    const vals = items.map((b) => b.value), hi = Math.max(0, ...vals), lo = Math.min(0, ...vals);
    const k = (bottom - top) / ((hi - lo) || 1), zeroY = top + hi * k;
    const layer = el("div", "mk-bars", ctx.stage);
    const zero = el("div", "mk-baseline", layer);
    zero.style.left = (x0 - 30) + "px"; zero.style.width = (total + 60) + "px"; zero.style.top = zeroY + "px";
    T.init(zero, { opacity: 0, scaleX: 0 });
    const it = items.map((b, i) => {
      const up = b.value >= 0, hgt = Math.max(5, Math.abs(b.value) * k), bw = iw * 0.62;
      const root = el("div", `mk-item mk-r-${b.role}`, layer);
      root.style.left = (x0 + i * (iw + gap)) + "px"; root.style.width = iw + "px";
      const bar = el("div", "mk-pbar", root);
      bar.style.left = ((iw - bw) / 2) + "px"; bar.style.width = bw + "px";
      bar.style.top = (up ? zeroY - hgt : zeroY) + "px"; bar.style.height = hgt + "px";
      const value = el("div", "mk-pval", root, fmtv(b.value));
      value.style.width = iw + "px";
      value.style.top = (up ? zeroY - hgt - value.offsetHeight - 12 : zeroY + hgt + 12) + "px";
      const label = el("div", "mk-itemlabel", root, esc(b.label));
      label.style.width = iw + "px";
      label.style.top = (up ? zeroY + 16 : zeroY - 16 - label.offsetHeight) + "px";
      T.init(bar, { scaleY: 0, opacity: 1, transformOrigin: up ? "50% 100%" : "50% 0%" });
      T.init(value, { opacity: 0 }); T.init(label, { opacity: 0, y: up ? 8 : -8 });
      return { b, root, bar, value, label, shown: false, rect: { x: x0 + i * (iw + gap), y: Math.min(zeroY - hgt, zeroY) - 60, w: iw, h: hgt + 120 } };
    });
    const note = notes(Object.assign({}, ctx, { obstacles: it.map((x) => x.rect) }));
    const F = formula(ctx, data.formula);
    const showItem = (x, at) => {
      if (x.shown) return; x.shown = true;
      T.to(x.bar, { scaleY: 1 }, at, 0.9, "expo.out");
      T.to(x.value, { opacity: 1 }, at + 0.1, 0.3);
      const dec = decOf(x.b.value);
      T.count(x.value, 0, x.b.value, at + 0.1, 0.9, (v) => num(v, dec));
      T.to(x.label, { opacity: 1, y: 0 }, at + 0.15, 0.4, "expo.out");
    };
    for (const a of data.actions) {
      const at = a.t, sel = a.ids.length ? it.filter((x) => a.ids.includes(x.b.id)) : it;
      if (a.do === "show") sel.forEach((x, i) => showItem(x, at + i * 0.12));
      else if (a.do === "focus" || a.do === "dim" || a.do === "unfocus") {
        const keep = new Set(sel.map((x) => x.b.id));
        it.forEach((x) => {
          if (!x.shown) return;
          const on = a.do === "unfocus" || (a.do === "focus" ? keep.has(x.b.id) : !keep.has(x.b.id));
          T.to(x.root, { opacity: on ? 1 : 0.26 }, at, 0.45, "power2.out");
        });
      } else if (a.do === "pulse") {
        sel.forEach((x) => { showItem(x, at - 0.6); T.to(x.bar, { scaleX: 1.14 }, at, 0.3, "power2.out"); T.to(x.bar, { scaleX: 1 }, at + 0.32, 0.5, "power3.out"); });
      } else if (a.do === "note") {
        const x = a.ids.length ? it.find((y) => y.b.id === a.ids[0]) : null;
        note(a, x ? x.rect : null, x ? x.b.role : "info");
      } else if (a.do === "formula") formulaAction(ctx, F, a);
    }
    if (!it.some((x) => x.shown)) it.forEach((x, i) => showItem(x, 0.5 + i * 0.12));
    T.to(zero, { opacity: 1, scaleX: 1 }, 0.4, 0.6, "power3.out");          // the zero line opens the scene
  }

  function bars(ctx) {
    const { data, T } = ctx;
    if (!data.actions.some((a) => a.do === "scale" || a.do === "softmax")) return plainBars(ctx);
    const items = data.bars;
    const n = items.length, iw = 220, gap = 90, total = n * iw + (n - 1) * gap;
    const x0 = 960 - total / 2, base = 760, maxH = 330, tileTop = 430;
    const layer = el("div", "mk-bars", ctx.stage);
    const baseline = el("div", "mk-baseline", layer);
    baseline.style.left = (x0 - 30) + "px"; baseline.style.width = (total + 60) + "px"; baseline.style.top = base + "px";
    T.init(baseline, { opacity: 0, scaleX: 0 });
    const it = items.map((b, i) => {
      const root = el("div", `mk-item mk-r-${b.role}`, layer);
      root.style.left = (x0 + i * (iw + gap)) + "px";
      const mkHalo = (role) => {
        const h = el("div", `mk-halo mk-r-${role}`, root);
        h.style.left = "-10px"; h.style.top = (tileTop - 30) + "px"; h.style.width = (iw + 20) + "px"; h.style.height = (base - tileTop + 60) + "px";
        return h;
      };
      const halo = mkHalo(b.role), haloW = mkHalo("weight");
      const tile = el("div", "mk-tile", root, `<b>${fmtv(b.value)}</b>`);
      tile.style.top = tileTop + "px";
      const bar = el("div", "mk-bar", root);
      bar.style.top = (base - maxH) + "px"; bar.style.height = maxH + "px";
      const pct = el("div", "mk-pct", root, "0%");
      const label = el("div", "mk-itemlabel", root, esc(b.label));
      label.style.top = (base + 22) + "px";
      T.init(tile, { opacity: 0, scale: 0.85, filter: "blur(6px)" }); T.init(bar, { scaleY: 0, opacity: 1 });
      T.init(pct, { opacity: 0 }); T.init(label, { opacity: 0, y: 10 }); T.init(halo, { opacity: 0 }); T.init(haloW, { opacity: 0 });
      return { b, root, tile, value: tile.querySelector("b"), bar, pct, label, halo, haloW, v: b.value };
    });
    const note = notes(ctx);
    const F = formula(ctx, data.formula);
    let chipY = 300;
    const chip = (text, role, at) => {
      const c = el("div", `mk-chip mk-r-${role}`, layer, esc(text));
      c.style.left = (x0 + total + 70) + "px"; c.style.top = chipY + "px"; chipY += 76;
      T.init(c, { opacity: 0, x: -14 }); T.to(c, { opacity: 1, x: 0 }, at, 0.45, "expo.out");
      return c;
    };
    let shown = false, weights = null, divider = null;
    for (const a of data.actions) {
      const at = a.t, sel = a.ids.length ? it.filter((x) => a.ids.includes(x.b.id)) : it;
      if (a.do === "show") {
        if (!shown) { T.to(baseline, { opacity: 1, scaleX: 1 }, at, 0.6, "power3.out"); shown = true; }
        sel.forEach((x, i) => { appear(T, x.tile, at + i * 0.09, 0.55); T.to(x.label, { opacity: 1, y: 0 }, at + 0.1 + i * 0.09, 0.4); });
      } else if (a.do === "scale" && a.value) {
        const div = el("div", "mk-chip mk-chip-big mk-r-score", layer, `÷ ${esc(num(a.value, Number.isInteger(a.value) ? 0 : 1))}`);
        div.style.left = (960 - div.offsetWidth / 2) + "px"; div.style.top = (tileTop - 104) + "px";
        T.init(div, { opacity: 0, y: -10 }); T.to(div, { opacity: 1, y: 0 }, at, 0.45, "expo.out");
        divider = div;
        const after = it.map((x) => x.v / a.value);
        const dec = after.every((v) => Math.abs(v * 10 - Math.round(v * 10)) < 1e-6) ? 1 : 2;
        it.forEach((x, i) => {
          const to = x.v / a.value;
          T.count(x.value, x.v, to, at + 0.15 + i * 0.06, 0.8, (v) => num(v, dec));
          T.to(x.tile, { scale: 0.9 }, at + 0.15, 0.5, "power3.out");
          x.v = to;
        });
      } else if (a.do === "softmax") {
        const m = Math.max(...it.map((x) => x.v));
        const ex = it.map((x) => Math.exp(x.v - m)), s = ex.reduce((p, q) => p + q, 0);
        weights = ex.map((e) => e / s);
        const wmax = Math.max(...weights);
        if (divider) T.to(divider, { opacity: 0, filter: "blur(6px)" }, at, 0.3, "power2.in");
        it.forEach((x, i) => {
          const w = weights[i], hgt = (w / wmax) * maxH;
          T.to(x.tile, { opacity: 0, y: 120, scale: 0.6, filter: "blur(8px)" }, at + i * 0.05, 0.45, "power2.in");
          T.to(x.bar, { scaleY: w / wmax }, at + 0.25 + i * 0.07, 0.8, "expo.out");
          x.pct.style.top = (base - hgt - 62) + "px";
          T.to(x.pct, { opacity: 1 }, at + 0.35 + i * 0.07, 0.3);
          T.count(x.pct, 0, w * 100, at + 0.35 + i * 0.07, 0.9, (v) => Math.round(v) + "%");
        });
      } else if (a.do === "total") {
        chip("soma = 100%", "weight", at);
      } else if (a.do === "focus" || a.do === "pulse") {
        const keep = new Set(sel.map((x) => x.b.id));
        const all = keep.size === it.length;          // lighting every item highlights nothing
        it.forEach((x) => {
          const on = keep.has(x.b.id), h = weights ? x.haloW : x.halo;
          if (a.do === "focus") T.to(x.root, { opacity: on ? 1 : 0.3 }, at, 0.4, "power2.out");
          if (on && !all) { T.to(h, { opacity: 0.7 }, at, 0.3); T.to(h, { opacity: a.do === "pulse" ? 0 : 0.3 }, at + 0.5, 0.6); }
        });
      } else if (a.do === "dim") {
        sel.forEach((x) => T.to(x.root, { opacity: 0.3 }, at, 0.4, "power2.out"));
      } else if (a.do === "unfocus") {
        it.forEach((x) => { T.to(x.root, { opacity: 1 }, at, 0.4); T.to(x.halo, { opacity: 0 }, at, 0.4); T.to(x.haloW, { opacity: 0 }, at, 0.4); });
      } else if (a.do === "note") {
        const anchor = a.ids.length ? it.find((x) => x.b.id === a.ids[0]) : null;
        const rect = anchor ? { x: anchor.root.offsetLeft, y: 300, w: iw, h: 10 } : null;
        note(a, rect ? null : null, "info");
      } else if (a.do === "formula") formulaAction(ctx, F, a);
    }
  }

  /* ---- patches: a synthetic image split into tokens -------------------------------------------------------- */
  function paintImage(kind, size, focus, rows, cols, seed) {
    const c = document.createElement("canvas");
    c.width = size; c.height = size;
    const g = c.getContext("2d"), r = rng(seed);
    const fx = (focus[1] + 0.5) * size / cols, fy = (focus[0] + 0.5) * size / rows, fr = 0.36 * size / Math.max(rows, cols);
    if (kind === "patologia") {
      g.fillStyle = "#e9b9cc"; g.fillRect(0, 0, size, size);
      for (let i = 0; i < 260; i++) {
        g.strokeStyle = `rgba(${200 + r() * 40},${120 + r() * 50},${160 + r() * 40},0.35)`; g.lineWidth = 6 + r() * 10;
        g.beginPath(); const x = r() * size, y = r() * size; g.moveTo(x, y);
        g.bezierCurveTo(x + r() * 80 - 40, y + r() * 80 - 40, x + r() * 120 - 60, y + r() * 120 - 60, x + r() * 140 - 70, y + r() * 140 - 70); g.stroke();
      }
      for (let i = 0; i < 2600; i++) {
        let x = r() * size, y = r() * size;
        const near = Math.hypot(x - fx, y - fy) < fr * 1.3;
        if (!near && r() < 0.35) continue;
        const rad = near ? 4 + r() * 5 : 2.5 + r() * 3.5;
        g.fillStyle = near ? `rgba(70,20,110,${0.7 + r() * 0.25})` : `rgba(95,45,150,${0.45 + r() * 0.35})`;
        g.beginPath(); g.ellipse(x, y, rad, rad * (0.7 + r() * 0.5), r() * Math.PI, 0, Math.PI * 2); g.fill();
      }
      return c;
    }
    g.fillStyle = "#000"; g.fillRect(0, 0, size, size);
    if (kind === "ultrassom") {
      const ax = size / 2, ay = -size * 0.08, R = size * 1.12, a0 = Math.PI / 2 - 0.62, a1 = Math.PI / 2 + 0.62;
      g.save(); g.beginPath(); g.moveTo(ax, ay); g.arc(ax, ay, R, a0, a1); g.closePath(); g.clip();
      g.fillStyle = "#151515"; g.fillRect(0, 0, size, size);
      for (let i = 0; i < 90000; i++) {
        const x = r() * size, y = r() * size, depth = y / size;
        const band = 0.5 + 0.25 * Math.sin(y * 0.03 + Math.sin(x * 0.01) * 2);
        let v = (0.25 + 0.6 * r() * r()) * (1 - depth * 0.55) * band;
        const d = Math.hypot((x - fx) / (fr * 1.25), (y - fy) / fr);
        if (d < 1 + 0.08 * Math.sin(Math.atan2(y - fy, x - fx) * 5)) v *= 0.18;            // hypoechoic lesion
        else if (d < 1.25) v *= 1.5;                                                         // its bright rim
        else if (Math.abs(x - fx) < fr * 1.1 && y > fy + fr && y < fy + fr * 3.2) v *= 1.35;  // posterior enhancement
        const s = Math.round(clamp(v, 0, 1) * 235);
        g.fillStyle = `rgb(${s},${s},${s})`; g.fillRect(x, y, 1.6 + r() * 1.4, 1.2 + r());
      }
      g.restore();
      g.filter = "blur(0.6px)"; g.drawImage(c, 0, 0); g.filter = "none";
      return c;
    }
    // raio-x / tomografia: a grey body section with two darker fields and a bright finding
    const grd = g.createRadialGradient(size / 2, size / 2, size * 0.1, size / 2, size / 2, size * 0.5);
    grd.addColorStop(0, "#9a9a9a"); grd.addColorStop(1, "#1a1a1a");
    g.fillStyle = grd; g.beginPath(); g.ellipse(size / 2, size / 2, size * 0.46, size * 0.4, 0, 0, Math.PI * 2); g.fill();
    g.fillStyle = "rgba(10,10,10,0.75)";
    g.beginPath(); g.ellipse(size * 0.33, size * 0.5, size * 0.13, size * 0.24, 0.1, 0, Math.PI * 2); g.fill();
    g.beginPath(); g.ellipse(size * 0.67, size * 0.5, size * 0.13, size * 0.24, -0.1, 0, Math.PI * 2); g.fill();
    for (let i = 0; i < 20000; i++) { const s = 90 + r() * 80; g.fillStyle = `rgba(${s},${s},${s},0.06)`; g.fillRect(r() * size, r() * size, 2, 2); }
    g.fillStyle = "rgba(235,235,235,0.9)"; g.beginPath(); g.arc(fx, fy, fr * 0.5, 0, Math.PI * 2); g.fill();
    return c;
  }

  function patches(ctx) {
    const { data, T } = ctx;
    const p = data.patches, rows = p.rows, cols = p.cols, size = 640;
    const X0 = 250, Y0 = 214, tw = size / cols, th = size / rows, spread = 16;
    const img = paintImage(p.image, size, [p.focus_row, p.focus_col], rows, cols, hash(ctx.id + p.image));
    const layer = el("div", "mk-img", ctx.stage);
    const svg = svgEl("svg", { class: "mk-edges", viewBox: `0 0 ${W} ${H}` });
    const tiles = [];
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
      const t = el("div", "mk-tilep", layer);
      t.style.left = (X0 + c * tw) + "px"; t.style.top = (Y0 + r * th) + "px";
      const cv = el("canvas", "", t); cv.width = Math.ceil(tw); cv.height = Math.ceil(th);
      cv.getContext("2d").drawImage(img, c * tw, r * th, tw, th, 0, 0, tw, th);
      const line = el("div", "mk-tileline", t);
      T.init(t, { opacity: 0, x: 0, y: 0, filter: "blur(10px)" });
      T.init(line, { opacity: 0 });
      tiles.push({ t, line, r, c, dx: (c - (cols - 1) / 2) * spread, dy: (r - (rows - 1) / 2) * spread });
    }
    layer.appendChild(svg);
    const tileCenter = (tile, spreadOn) => ({ x: X0 + (tile.c + 0.5) * tw + (spreadOn ? tile.dx : 0), y: Y0 + (tile.r + 0.5) * th + (spreadOn ? tile.dy : 0) });
    const focus = tiles.find((x) => x.r === p.focus_row && x.c === p.focus_col);
    const ring = el("div", "mk-ring mk-r-alert", layer);
    const fr = focus;
    T.init(ring, { opacity: 0, scale: 1.25 });
    const note = notes(Object.assign({}, ctx, { area: { y1: 860 } }));
    const noteX = X0 + size + spread * cols + 110;
    let spreadOn = false, noteY = 250, imageOn = false;
    const placeRing = () => {
      const c = tileCenter(fr, spreadOn);
      ring.style.left = (c.x - tw / 2 - 8) + "px"; ring.style.top = (c.y - th / 2 - 8) + "px";
      ring.style.width = (tw + 16 - 8) + "px"; ring.style.height = (th + 16 - 8) + "px";
    };
    placeRing();
    const showImage = (at) => {
      if (imageOn) return; imageOn = true;
      tiles.forEach((x, i) => T.to(x.t, { opacity: 1, filter: "blur(0px)" }, at + (x.r + x.c) * 0.03, 0.6, "power3.out"));
    };
    for (const a of data.actions) {
      const at = a.t;
      if (a.do === "show") showImage(at);
      else if (a.do === "tokenize") {
        showImage(at - 0.3);
        spreadOn = true; placeRing();
        tiles.forEach((x, i) => {
          T.to(x.t, { x: x.dx, y: x.dy }, at + 0.1 + (x.r + x.c) * 0.04, 0.7, "expo.out");
          T.to(x.line, { opacity: 1 }, at + 0.25 + (x.r + x.c) * 0.04, 0.4, "power2.out");
        });
        const caps = tiles.filter((x, i) => i % Math.max(2, Math.floor(tiles.length / 3)) === 0).slice(0, 3);
        caps.forEach((x, k) => {
          const cap = el("div", "mk-tilecap", layer, "token");
          const c = tileCenter(x, true);
          cap.style.left = (c.x - tw / 2 + 8) + "px"; cap.style.top = (c.y - th / 2 + 8) + "px";
          T.init(cap, { opacity: 0, y: 6 }); T.to(cap, { opacity: 1, y: 0 }, at + 0.6 + k * 0.12, 0.35);
        });
      } else if (a.do === "focus") {
        showImage(at - 0.3); placeRing();
        T.to(ring, { opacity: 1, scale: 1 }, at, 0.5, "expo.out");
      } else if (a.do === "attend") {
        showImage(at - 0.3);
        const r = rng(hash(ctx.id + "attend"));
        const others = tiles.filter((x) => x !== fr).map((x) => ({ x, d: Math.hypot(x.r - fr.r, x.c - fr.c) + r() * 0.6 }))
          .sort((a, b) => b.d - a.d).slice(0, Math.min(5, tiles.length - 1));
        const a0 = tileCenter(fr, spreadOn);
        others.forEach((o, k) => {
          const b = tileCenter(o.x, spreadOn);
          const mx = (a0.x + b.x) / 2, my = (a0.y + b.y) / 2 - 90 - r() * 60;
          const path = svgEl("path", { d: `M ${a0.x} ${a0.y} Q ${mx} ${my} ${b.x} ${b.y}`, fill: "none", stroke: ROLE.query,
            "stroke-width": (2.5 + r() * 4.5).toFixed(1), "stroke-linecap": "round", opacity: "0.9" }, svg);
          path.style.filter = `drop-shadow(0 0 6px ${ROLE.query})`;
          const len = path.getTotalLength();
          path.setAttribute("stroke-dasharray", `${len} ${len}`);
          T.init(path, { strokeDashoffset: len, opacity: 0 });
          T.to(path, { opacity: 0.9 }, at + k * 0.12, 0.05, "none");
          T.to(path, { strokeDashoffset: 0 }, at + k * 0.12, 0.8, "power2.inOut");
          const dot = svgEl("circle", { cx: b.x, cy: b.y, r: 7, fill: ROLE.query }, svg);
          T.init(dot, { opacity: 0, scale: 0.4 }); T.to(dot, { opacity: 1, scale: 1 }, at + k * 0.12 + 0.7, 0.3, "back.out(2)");
        });
      } else if (a.do === "conv") {
        const win = el("div", "mk-window mk-r-info", layer);
        const r0 = Math.max(0, fr.r - 1), r1 = Math.min(rows - 1, fr.r + 1), c0 = Math.max(0, fr.c - 1), c1 = Math.min(cols - 1, fr.c + 1);
        const tl0 = tileCenter(tiles.find((x) => x.r === r0 && x.c === c0), spreadOn), br0 = tileCenter(tiles.find((x) => x.r === r1 && x.c === c1), spreadOn);
        win.style.left = (tl0.x - tw / 2 - 12) + "px"; win.style.top = (tl0.y - th / 2 - 12) + "px";
        win.style.width = (br0.x - tl0.x + tw + 24 - 6) + "px"; win.style.height = (br0.y - tl0.y + th + 24 - 6) + "px";
        T.init(win, { opacity: 0, scale: 0.9 }); T.to(win, { opacity: 1, scale: 1 }, at, 0.5, "expo.out");
        if (a.text) {
          const tag = el("div", "mk-tilecap", layer, esc(a.text));
          tag.style.left = (tl0.x - tw / 2 - 12) + "px"; tag.style.top = (tl0.y - th / 2 - 46) + "px";
          T.init(tag, { opacity: 0 }); T.to(tag, { opacity: 1 }, at + 0.3, 0.3);
        }
      } else if (a.do === "dim") {
        tiles.forEach((x) => T.to(x.t, { opacity: 0.35 }, at, 0.5));
      } else if (a.do === "note") {
        const n = el("div", "mk-note mk-r-info", ctx.layer, `<i></i>${esc(a.text)}`);
        n.style.left = noteX + "px"; n.style.top = noteY + "px"; noteY += n.offsetHeight + 18;
        T.init(n, { opacity: 0, x: -12, filter: "blur(6px)" }); T.to(n, { opacity: 1, x: 0, filter: "blur(0px)" }, at, 0.45, "expo.out");
      }
    }
    if (!imageOn) showImage(0.4);
  }

  /* ---- chart: curves on two axes (ROC + AUC, learning curves, dose-response) ---------------------------------- */
  function niceStep(range, n) {
    const raw = range / Math.max(1, n), mag = Math.pow(10, Math.floor(Math.log10(raw))), f = raw / mag;
    return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * mag;
  }
  function ticksOf(a, b, n) {
    const step = niceStep(b - a, n), out = [];
    for (let v = Math.ceil(a / step - 1e-9) * step; v <= b + step * 1e-6; v += step) out.push(+v.toFixed(10));
    const dec = step >= 1 ? 0 : Math.min(3, Math.ceil(-Math.log10(step) - 1e-9) + (String(step).includes("25") ? 1 : 0));
    return { values: out, dec };
  }
  function monotone(xs, ys) {   // Fritsch–Carlson tangents: a smooth curve that never overshoots its points
    const n = xs.length, d = [], m = new Array(n).fill(0);
    for (let i = 0; i < n - 1; i++) d.push((ys[i + 1] - ys[i]) / ((xs[i + 1] - xs[i]) || 1e-9));
    if (n === 2) { m[0] = m[1] = d[0]; return m; }
    m[0] = d[0]; m[n - 1] = d[n - 2];
    for (let i = 1; i < n - 1; i++) m[i] = d[i - 1] * d[i] <= 0 ? 0 : (d[i - 1] + d[i]) / 2;
    for (let i = 0; i < n - 1; i++) {
      if (d[i] === 0) { m[i] = m[i + 1] = 0; continue; }
      const a = m[i] / d[i], b = m[i + 1] / d[i], s = a * a + b * b;
      if (s > 9) { const t = 3 / Math.sqrt(s); m[i] = t * a * d[i]; m[i + 1] = t * b * d[i]; }
    }
    return m;
  }

  function chart(ctx) {
    const { data, T } = ctx;
    const ax = data.axes || {}, list = data.series || [];
    const square = ax.x_min === 0 && ax.x_max === 1 && ax.y_min === 0 && ax.y_max === 1;   // ROC-like: a squarer plot
    const hasNotes = data.actions.some((a) => a.do === "note");      // then the notes get a column on the right
    const top = ctx.area.y0 + 30, bot = 770, wid = square ? Math.round((bot - top) * 1.35) : (hasNotes ? 900 : 1060);
    const cx = hasNotes ? 860 : 990;
    const P = { x0: cx - wid / 2, x1: cx + wid / 2, y0: top, y1: bot };
    const xr = (ax.x_max - ax.x_min) || 1, yr = (ax.y_max - ax.y_min) || 1;
    const sx = (x) => P.x0 + ((x - ax.x_min) / xr) * (P.x1 - P.x0);
    const sy = (y) => P.y1 - ((y - ax.y_min) / yr) * (P.y1 - P.y0);
    const dx = (px) => ax.x_min + ((px - P.x0) / (P.x1 - P.x0)) * xr;
    const layer = el("div", "mk-chart", ctx.stage);
    const svg = svgEl("svg", { class: "mk-edges", viewBox: `0 0 ${W} ${H}` }, layer);
    const defs = svgEl("defs", {}, svg);
    const frame = [];
    const xt = ticksOf(ax.x_min, ax.x_max, 5), yt = ticksOf(ax.y_min, ax.y_max, 5);
    for (const v of xt.values) {
      if (v > ax.x_min + 1e-9) frame.push(svgEl("line", { x1: sx(v), y1: P.y0, x2: sx(v), y2: P.y1, class: "mk-gridline" }, svg));
      const t = el("div", "mk-tick", layer, num(v, xt.dec));
      t.style.left = (sx(v) - t.offsetWidth / 2) + "px"; t.style.top = (P.y1 + 16) + "px"; frame.push(t);
    }
    for (const v of yt.values) {
      if (v > ax.y_min + 1e-9) frame.push(svgEl("line", { x1: P.x0, y1: sy(v), x2: P.x1, y2: sy(v), class: "mk-gridline" }, svg));
      const t = el("div", "mk-tick", layer, num(v, yt.dec));
      t.style.left = (P.x0 - 18 - t.offsetWidth) + "px"; t.style.top = (sy(v) - t.offsetHeight / 2) + "px"; frame.push(t);
    }
    frame.push(svgEl("path", { d: `M ${P.x0} ${P.y0 - 14} L ${P.x0} ${P.y1} L ${P.x1 + 14} ${P.y1}`, class: "mk-axis" }, svg));
    const xl = el("div", "mk-axlabel", layer, esc(ax.x_label || ""));
    xl.style.left = ((P.x0 + P.x1) / 2 - xl.offsetWidth / 2) + "px"; xl.style.top = (P.y1 + 62) + "px";
    const yl = el("div", "mk-axlabel mk-axlabel-y", layer, esc(ax.y_label || ""));
    yl.style.left = (P.x0 - 96 - yl.offsetWidth / 2) + "px"; yl.style.top = ((P.y0 + P.y1) / 2 - yl.offsetHeight / 2) + "px";
    frame.push(xl, yl);
    frame.forEach((f) => T.init(f, { opacity: 0 }));

    const curves = {};
    const used = new Set(), SPARE = ["query", "key", "value", "weight", "info", "output", "score"];
    list.forEach((s) => {
      const pts = (s.points || []).filter((p) => p.length >= 2);
      if (pts.length < 2) return;
      let role = s.role;
      if (role !== "neutral") {                         // two curves of the same role would be the same colour
        if (used.has(role)) role = SPARE.find((r) => !used.has(r)) || role;
        used.add(role);
      }
      const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]), m = monotone(xs, ys);
      let d = `M ${sx(xs[0])} ${sy(ys[0])}`;
      for (let i = 0; i < pts.length - 1; i++) {
        const h = xs[i + 1] - xs[i];
        d += ` C ${sx(xs[i] + h / 3)} ${sy(ys[i] + (m[i] * h) / 3)}, ${sx(xs[i + 1] - h / 3)} ${sy(ys[i + 1] - (m[i + 1] * h) / 3)}, ${sx(xs[i + 1])} ${sy(ys[i + 1])}`;
      }
      const color = ROLE[role] || ROLE.neutral;
      const gid = `${ctx.id}-area-${s.id}`;
      const grad = svgEl("linearGradient", { id: gid, x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
      svgEl("stop", { offset: "0", "stop-color": color, "stop-opacity": "0.42" }, grad);
      svgEl("stop", { offset: "1", "stop-color": color, "stop-opacity": "0.05" }, grad);
      const area = svgEl("path", { d: `${d} L ${sx(xs[xs.length - 1])} ${P.y1} L ${sx(xs[0])} ${P.y1} Z`, fill: `url(#${gid})` }, svg);
      const g = svgEl("g", {}, svg);
      const path = svgEl("path", { d, class: "mk-curve", stroke: color }, g);
      const ref = role === "neutral";                       // a reference line (chance, baseline): dotted, no draw-on
      if (ref) path.setAttribute("stroke-dasharray", "2 14");
      const len = path.getTotalLength();
      if (!ref) path.setAttribute("stroke-dasharray", `${len} ${len + 40}`);
      const dot = svgEl("circle", { cx: sx(xs[xs.length - 1]), cy: sy(ys[ys.length - 1]), r: 9, fill: color, class: "mk-flowdot" }, g);
      dot.style.color = color;
      const tag = el("div", `mk-seriestag mk-r-${role}`, layer, esc(s.label));
      T.init(area, { opacity: 0 });
      T.init(path, ref ? { opacity: 0 } : { strokeDashoffset: len, opacity: 0 });
      T.init(dot, { opacity: 0, scale: 0.4, transformOrigin: "50% 50%" }); T.init(tag, { opacity: 0, y: 8 });
      const at = (x) => {     // y on the drawn curve (the same Hermite segments)
        let i = 0;
        while (i < xs.length - 2 && x > xs[i + 1]) i++;
        const h = (xs[i + 1] - xs[i]) || 1e-9, t = Math.max(0, Math.min(1, (x - xs[i]) / h));
        const t2 = t * t, t3 = t2 * t;
        return (2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h * m[i] + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h * m[i + 1];
      };
      curves[s.id] = { s, role, ref, path, len, dot, tag, area, at, xs, ys, color, shown: false, els: [path, dot, tag] };
    });
    const all = Object.values(curves);

    // labels go on the curves, where nothing else is: candidates along each curve, above or below it
    const placed = [];
    const inPlot = (r) => r.x >= P.x0 + 8 && r.x + r.w <= P.x1 - 8 && r.y >= P.y0 - 6 && r.y + r.h <= P.y1 - 8;
    const crosses = (r, skip) => all.some((o) => {
      if (o === skip) return false;
      for (let k = 0; k <= 16; k++) {
        const py = sy(o.at(dx(r.x + (r.w * k) / 16)));
        if (py > r.y - 6 && py < r.y + r.h + 6) return true;
      }
      return false;
    });
    const hitsPlaced = (r) => placed.some((p) => overlap(r, p, 10));
    const neighbour = (c, x, side) => {     // the next curve (or the axis) above or below c at x, in data units
      const y = c.at(x);
      let best = side > 0 ? ax.y_max : ax.y_min;
      for (const o of all) {
        if (o === c) continue;
        const oy = o.at(x);
        if (side > 0 ? oy > y && oy < best : oy < y && oy > best) best = oy;
      }
      return best;
    };
    const place = (w, h, cands) => {
      let best = null;
      for (const c of cands) {
        const r = { x: c.x, y: c.y, w, h };
        if (!inPlot(r)) continue;
        const score = c.score - (hitsPlaced(r) ? 1e4 : 0) - (crosses(r, null) ? 2e3 : 0);
        if (!best || score > best.score) best = { r, score };
      }
      return best ? best.r : null;
    };
    for (const c of all) {
      const w = c.tag.offsetWidth, h = c.tag.offsetHeight, cands = [];
      for (let k = 0; k <= 14; k++) {
        const x = ax.x_min + xr * (0.12 + (0.76 * k) / 14), px = sx(x), py = sy(c.at(x));
        let hi = Infinity, lo = -Infinity;          // the curve's screen y across the label's width
        for (let q = 0; q <= 8; q++) { const yy = sy(c.at(dx(px - w / 2 + (w * q) / 8))); hi = Math.min(hi, yy); lo = Math.max(lo, yy); }
        for (const side of [1, -1]) {
          const room = Math.abs(sy(neighbour(c, x, side)) - py);
          const prefer = c.ref ? -Math.abs(k / 14 - 0.8) * 120 : -Math.abs(k / 14 - 0.45) * 60;
          cands.push({ x: px - w / 2, y: side > 0 ? hi - h - 16 : lo + 16, score: Math.min(room, 260) + prefer, own: c });
        }
      }
      const r = place(w, h, cands) || { x: P.x1 + 30, y: sy(c.ys[c.ys.length - 1]) - h / 2, w, h };
      placed.push(r);
      c.tag.style.left = r.x + "px"; c.tag.style.top = r.y + "px";
    }

    // the notes keep off the plot, its ticks and its axis labels
    const note = notes(Object.assign({}, ctx, { obstacles: [{ x: P.x0 - 150, y: P.y0 - 24, w: P.x1 - P.x0 + 190, h: P.y1 - P.y0 + 130 }] }));
    const F = formula(ctx, data.formula);
    let frameOn = false;
    const showFrame = (at) => {
      if (frameOn) return; frameOn = true;
      frame.forEach((f, i) => T.to(f, { opacity: 1 }, Math.max(0, at) + Math.min(0.5, i * 0.025), 0.45, "power2.out"));
    };
    const draw = (c, at) => {
      if (c.shown) return; c.shown = true;
      showFrame(at - 0.4);
      if (c.ref) T.to(c.path, { opacity: 0.75 }, at, 0.6, "power2.out");
      else { T.to(c.path, { opacity: 1 }, at, 0.05, "none"); T.to(c.path, { strokeDashoffset: 0 }, at, 1.5, "power2.inOut"); }
      T.to(c.dot, { opacity: 1, scale: 1 }, at + (c.ref ? 0.4 : 1.35), 0.35, "back.out(2)");
      T.to(c.tag, { opacity: 1, y: 0 }, at + (c.ref ? 0.5 : 1.2), 0.4, "expo.out");
    };
    const pick = (a) => (a.ids.length ? a.ids.map((i) => curves[i]).filter(Boolean) : all);
    for (const a of data.actions) {
      const at = a.t, sel = pick(a);
      if (a.do === "show") {
        showFrame(at);
        if (a.ids.length) sel.forEach((c, i) => draw(c, at + 0.25 + i * 0.5));
      } else if (a.do === "area") {
        const c = sel.find((x) => !x.ref) || sel[0];
        if (!c) continue;
        draw(c, at - 1.2);
        T.to(c.area, { opacity: 1 }, at, 0.9, "power2.out");
        const text = a.text || (c.s.auc ? `AUC ${num(c.s.auc, 2)}` : "");
        if (!text) continue;
        const chip = el("div", `mk-chip mk-chip-big mk-r-${c.role}`, layer, esc(text));
        const w = chip.offsetWidth, h = chip.offsetHeight, cands = [];
        for (let k = 0; k <= 16; k++) {      // the chip sits in the widest part of the area under the curve
          const x = ax.x_min + xr * (0.1 + (0.8 * k) / 16), y0 = sy(c.at(x)), y1 = sy(neighbour(c, x, -1));
          cands.push({ x: sx(x) - w / 2, y: (y0 + y1) / 2 - h / 2, score: Math.min(y1 - y0, 400) - Math.abs(k / 16 - 0.55) * 80, own: c });
        }
        const r = place(w, h, cands) || { x: sx(ax.x_min + xr * 0.6) - w / 2, y: (P.y0 + P.y1) / 2, w, h };
        placed.push(r);
        chip.style.left = r.x + "px"; chip.style.top = r.y + "px";
        T.init(chip, { opacity: 0, scale: 0.85 }); T.to(chip, { opacity: 1, scale: 1 }, at + 0.35, 0.5, "back.out(1.6)");
      } else if (a.do === "mark") {
        const c = sel.find((x) => !x.ref) || sel[0];
        if (!c) continue;
        draw(c, at - 1.2);
        const x = Math.min(ax.x_max, Math.max(ax.x_min, a.value)), y = c.at(x), px = sx(x), py = sy(y);
        const guide = svgEl("path", { d: `M ${P.x0} ${py} L ${px} ${py} L ${px} ${P.y1}`, class: "mk-guide", stroke: c.color }, svg);
        const dot = svgEl("circle", { cx: px, cy: py, r: 11, fill: "#0a101e", stroke: c.color, "stroke-width": 5 }, svg);
        T.init(guide, { opacity: 0 }); T.init(dot, { opacity: 0, scale: 0.3, transformOrigin: "50% 50%" });
        T.to(guide, { opacity: 0.85 }, at, 0.5, "power2.out"); T.to(dot, { opacity: 1, scale: 1 }, at + 0.1, 0.4, "back.out(2.2)");
        if (a.text) {
          const chip = el("div", `mk-note mk-r-${c.role}`, layer, `<i></i>${esc(a.text)}`);
          const w = chip.offsetWidth, h = chip.offsetHeight;
          const cands = [[px + 26, py - h - 16], [px + 26, py + 16], [px - w - 26, py - h - 16], [px - w - 26, py + 16]]
            .map(([cx, cy], k) => ({ x: cx, y: cy, score: -k * 10, own: c }));
          const r = place(w, h, cands) || { x: px + 26, y: py - h - 16, w, h };
          placed.push(r);
          chip.style.left = r.x + "px"; chip.style.top = r.y + "px";
          T.init(chip, { opacity: 0, y: 8 }); T.to(chip, { opacity: 1, y: 0 }, at + 0.3, 0.45, "expo.out");
        }
      } else if (a.do === "focus" || a.do === "dim" || a.do === "unfocus") {
        const keep = new Set(sel.map((c) => c.s.id));
        for (const c of all) {
          if (!c.shown) continue;
          const op = a.do === "unfocus" ? 1 : a.do === "focus" ? (keep.has(c.s.id) ? 1 : 0.22) : (keep.has(c.s.id) ? 0.22 : null);
          if (op === null) continue;
          c.els.forEach((e) => T.to(e, { opacity: op }, at, 0.45, "power2.out"));
        }
      } else if (a.do === "pulse") {
        sel.forEach((c) => { T.to(c.dot, { scale: 1.9 }, at, 0.3, "power2.out"); T.to(c.dot, { scale: 1 }, at + 0.32, 0.6, "power3.out"); });
      } else if (a.do === "note") {
        const c = a.ids.length ? curves[a.ids[0]] : null;
        const rect = c ? { x: sx(c.xs[c.xs.length - 1]) - 10, y: sy(c.ys[c.ys.length - 1]) - 10, w: 20, h: 20 } : null;
        note(a, rect, c ? c.role : "info");
      } else if (a.do === "formula") formulaAction(ctx, F, a);
    }
    if (!frameOn) showFrame(0.4);
    if (!all.some((c) => c.shown)) all.forEach((c, i) => draw(c, 1.0 + i * 0.6));     // curves no sentence named
  }

  /* ---- timeline: events in time order -------------------------------------------------------------------- */
  function timeline(ctx) {
    const { data, T } = ctx;
    const evs = data.events || [], n = evs.length;
    const X0 = 250, X1 = 1670, Y = Math.round((ctx.area.y0 + 862) / 2) + 10;
    const xs = evs.map((_, i) => (n > 1 ? X0 + (i * (X1 - X0)) / (n - 1) : (X0 + X1) / 2));
    const layer = el("div", "mk-timeline", ctx.stage);
    const L0 = X0 - 70, L1 = X1 + 70;
    const line = el("div", "mk-tline", layer);
    line.style.left = L0 + "px"; line.style.top = (Y - 2.5) + "px"; line.style.width = (L1 - L0) + "px";
    T.init(line, { scaleX: 0, opacity: 1 });
    const zig = n >= 3;
    const slot = n > 1 ? (X1 - X0) / (n - 1) : 600;
    const items = evs.map((e, i) => {
      const up = zig && i % 2 === 0;
      const dot = el("div", `mk-tdot mk-r-${e.role}`, layer);
      dot.style.left = (xs[i] - 15) + "px"; dot.style.top = (Y - 15) + "px";
      const halo = el("div", `mk-halo mk-r-${e.role}`, layer);
      halo.style.left = (xs[i] - 46) + "px"; halo.style.top = (Y - 46) + "px"; halo.style.width = "92px"; halo.style.height = "92px";
      halo.style.right = "auto"; halo.style.bottom = "auto"; halo.style.borderRadius = "50%";
      const card = el("div", `mk-tcard mk-r-${e.role}`, layer);
      el("div", "mk-twhen", card, esc(e.when));
      el("div", "mk-tlabel", card, esc(e.label));
      if (e.gloss) el("div", "mk-tgloss", card, esc(e.gloss));
      const w = Math.min(Math.max(240, (zig ? 2 * slot : slot) - 40), 460);
      card.style.width = w + "px";
      const left = Math.min(Math.max(xs[i] - w / 2, 130), W - 130 - w);
      card.style.left = left + "px";
      const stemLen = 46, h = card.offsetHeight;
      const top = up ? Y - stemLen - 14 - h : Y + stemLen + 14;
      card.style.top = top + "px";
      const stem = el("div", `mk-tstem mk-r-${e.role}`, layer);
      stem.style.left = (xs[i] - 1) + "px"; stem.style.top = (up ? Y - stemLen - 8 : Y + 14) + "px"; stem.style.height = stemLen + "px";
      stem.style.transformOrigin = up ? "50% 100%" : "50% 0%";
      T.init(dot, { opacity: 0, scale: 0.2 }); T.init(halo, { opacity: 0 }); T.init(stem, { scaleY: 0, opacity: 1 });
      T.init(card, { opacity: 0, y: up ? 14 : -14, filter: "blur(6px)" });
      return { e, i, dot, halo, card, stem, rect: { x: left, y: top, w, h }, shown: false };
    });
    const note = notes(Object.assign({}, ctx, { obstacles: items.map((it) => it.rect).concat([{ x: L0, y: Y - 20, w: L1 - L0, h: 40 }]) }));
    const F = formula(ctx, data.formula);
    let reach = 0;
    const grow = (x, at) => {
      const f = Math.min(1, (x - L0 + 70) / (L1 - L0));
      if (f <= reach) return;
      T.to(line, { scaleX: f }, at, 0.7, "power2.inOut");
      reach = f;
    };
    const showItem = (it, at) => {
      if (it.shown) return; it.shown = true;
      grow(xs[it.i], at);
      T.to(it.dot, { opacity: 1, scale: 1 }, at + 0.45, 0.4, "back.out(2.2)");
      T.to(it.stem, { scaleY: 1 }, at + 0.6, 0.3, "power2.out");
      T.to(it.card, { opacity: 1, y: 0, filter: "blur(0px)" }, at + 0.75, 0.5, "expo.out");
    };
    for (const a of data.actions) {
      const at = a.t;
      const sel = a.ids.length ? items.filter((it) => a.ids.includes(it.e.id)) : items;
      if (a.do === "show") {
        const todo = sel.filter((it) => !it.shown);
        todo.forEach((it, k) => showItem(it, at + k * (a.ids.length ? 0.35 : 0.55)));
      } else if (a.do === "focus" || a.do === "dim" || a.do === "unfocus") {
        const keep = new Set(sel.map((it) => it.e.id));
        for (const it of items) {
          if (!it.shown) continue;
          const on = a.do === "unfocus" || (a.do === "focus" ? keep.has(it.e.id) : !keep.has(it.e.id));
          [it.card, it.dot, it.stem].forEach((x) => T.to(x, { opacity: on ? 1 : 0.25 }, at, 0.45, "power2.out"));
          T.to(it.halo, { opacity: a.do === "focus" && keep.has(it.e.id) ? 0.8 : 0 }, at, 0.45, "power2.out");
        }
      } else if (a.do === "pulse") {
        sel.forEach((it) => {
          showItem(it, at - 0.8);
          T.to(it.halo, { opacity: 0.95 }, at, 0.3); T.to(it.halo, { opacity: 0.25 }, at + 0.5, 0.7);
          T.to(it.dot, { scale: 1.45 }, at, 0.3, "power2.out"); T.to(it.dot, { scale: 1 }, at + 0.32, 0.5, "power3.out");
        });
      } else if (a.do === "note") {
        const it = a.ids.length ? items.find((x) => x.e.id === a.ids[0]) : null;
        note(a, it ? it.rect : null, it ? it.e.role : "info");
      } else if (a.do === "formula") formulaAction(ctx, F, a);
    }
    if (!items.some((it) => it.shown)) items.forEach((it, k) => showItem(it, 0.5 + k * 0.5));
  }

  /* ---- compare: alternatives side by side on the same attributes ------------------------------------------- */
  function compare(ctx) {
    const { data, T } = ctx;
    const cols = (data.columns || []).slice(0, 3), rows = (data.rows || []).slice(0, 5);
    const nc = Math.max(1, cols.length), nr = Math.max(1, rows.length);
    const LX0 = 150, LX1 = 520, CX0 = 560, CX1 = 1770, gap = 34;
    const cw = (CX1 - CX0 - gap * (nc - 1)) / nc;
    const headH = 104, rh = Math.min(132, (850 - ctx.area.y0 - 20 - headH - 24) / nr);
    const top = Math.max(ctx.area.y0 + 20, Math.round((ctx.area.y0 + 862) / 2 - (headH + 24 + rh * nr) / 2));
    const layer = el("div", "mk-compare", ctx.stage);
    const colEls = cols.map((c, j) => {
      const x = CX0 + j * (cw + gap);
      const card = el("div", `mk-ccol mk-r-${c.role}`, layer);
      card.style.left = x + "px"; card.style.top = top + "px"; card.style.width = cw + "px";
      card.style.height = (headH + 24 + rh * nr) + "px";
      const head = el("div", "mk-chead", card, esc(c.title));
      head.style.height = headH + "px";
      const halo = el("div", `mk-halo mk-r-${c.role}`, card);
      T.init(card, { opacity: 0, y: 18, filter: "blur(6px)", height: headH + 24 }); T.init(halo, { opacity: 0 });
      return { c, j, x, card, halo, shown: false, rows: 0 };
    });
    const rowEls = rows.map((r, i) => {
      const y = top + headH + 12 + i * rh;
      const label = el("div", "mk-crowlabel", layer, esc(r.label));
      label.style.left = LX0 + "px"; label.style.width = (LX1 - LX0) + "px";
      label.style.top = (y + rh / 2 - label.offsetHeight / 2) + "px";
      const rule = el("div", "mk-crule", layer);
      rule.style.left = LX0 + "px"; rule.style.width = (CX1 - LX0) + "px"; rule.style.top = (y + rh) + "px";
      if (i === nr - 1) rule.style.display = "none";
      const cells = cols.map((c, j) => {
        const cell = el("div", "mk-ccell", layer, esc((r.cells || [])[j] || "—"));
        cell.style.left = colEls[j].x + "px"; cell.style.width = cw + "px"; cell.style.top = y + "px"; cell.style.height = rh + "px";
        T.init(cell, { opacity: 0, y: 10 });
        return cell;
      });
      T.init(label, { opacity: 0, x: -12 }); T.init(rule, { opacity: 0, scaleX: 0 });
      return { r, i, y, label, rule, cells, shown: false };
    });
    const note = notes(Object.assign({}, ctx, { obstacles: [{ x: LX0, y: top, w: CX1 - LX0, h: headH + rh * nr + 24 }] }));
    const F = formula(ctx, data.formula);
    let lowest = 0;                            // the cards grow down to the lowest row shown
    const grow = (ce, at) => {
      if (lowest > ce.rows) { T.to(ce.card, { height: headH + 24 + rh * lowest }, at, 0.55, "power3.out"); ce.rows = lowest; }
    };
    const showCol = (ce, at) => {
      if (ce.shown) return; ce.shown = true;
      T.to(ce.card, { opacity: 1, y: 0, filter: "blur(0px)" }, at, 0.55, "expo.out");
      grow(ce, at);
      rowEls.forEach((re) => { if (re.shown) T.to(re.cells[ce.j], { opacity: 1, y: 0 }, at + 0.25, 0.45, "expo.out"); });
    };
    const showRow = (re, at) => {
      if (re.shown) return;
      if (!colEls.some((ce) => ce.shown)) colEls.forEach((ce, j) => showCol(ce, at - 0.3 + j * 0.05));   // no column named yet
      re.shown = true;
      lowest = Math.max(lowest, re.i + 1);
      colEls.forEach((ce) => { if (ce.shown) grow(ce, at - 0.05); });
      T.to(re.label, { opacity: 1, x: 0 }, at, 0.45, "expo.out");
      T.to(re.rule, { opacity: 1, scaleX: 1 }, at + 0.1, 0.6, "power2.out");
      re.cells.forEach((cell, j) => { if (colEls[j].shown) T.to(cell, { opacity: 1, y: 0 }, at + 0.15 + j * 0.12, 0.45, "expo.out"); });
    };
    for (const a of data.actions) {
      const at = a.t;
      const cs = colEls.filter((ce) => a.ids.includes(ce.c.id)), rs = rowEls.filter((re) => a.ids.includes(re.r.id));
      if (a.do === "show") {
        if (!a.ids.length) { colEls.forEach((ce, j) => showCol(ce, at + j * 0.12)); rowEls.forEach((re, i) => showRow(re, at + 0.4 + i * 0.35)); }
        cs.forEach((ce, k) => showCol(ce, at + k * 0.15));
        rs.forEach((re, k) => showRow(re, at + k * 0.3));
      } else if (a.do === "pick") {
        const re = rs[0], ce = cs[0];
        if (!re || !ce) continue;
        showRow(re, at - 0.6); showCol(ce, at - 0.6);
        T.to(re.cells[ce.j], { opacity: 1 }, at, 0.3, "power2.out");
        const box = el("div", `mk-cpick mk-r-${ce.c.role}`, layer, "<i>✓</i>");
        box.style.left = (ce.x + 10) + "px"; box.style.top = (re.y + 8) + "px"; box.style.width = (cw - 20) + "px"; box.style.height = (rh - 16) + "px";
        T.init(box, { opacity: 0, scale: 0.92 }); T.to(box, { opacity: 1, scale: 1 }, at, 0.45, "back.out(1.7)");
      } else if (a.do === "focus" || a.do === "dim" || a.do === "unfocus") {
        const rowIds = new Set(rs.map((re) => re.r.id)), colIds = new Set(cs.map((ce) => ce.c.id));
        for (const re of rowEls) {
          if (!re.shown) continue;
          re.cells.forEach((cell, j) => {
            if (!colEls[j].shown) return;
            const hit = rowIds.has(re.r.id) || colIds.has(cols[j].id);
            const op = a.do === "unfocus" ? 1 : a.do === "focus" ? (hit ? 1 : 0.25) : (hit ? 0.25 : 1);
            T.to(cell, { opacity: op }, at, 0.45, "power2.out");
          });
          const op = a.do === "unfocus" ? 1 : a.do === "focus" ? (rowIds.has(re.r.id) || !rowIds.size ? 1 : 0.3) : (rowIds.has(re.r.id) ? 0.3 : 1);
          T.to(re.label, { opacity: op }, at, 0.45, "power2.out");
        }
        colEls.forEach((ce) => T.to(ce.halo, { opacity: a.do === "focus" && colIds.has(ce.c.id) ? 0.55 : 0 }, at, 0.45, "power2.out"));
      } else if (a.do === "pulse") {
        cs.forEach((ce) => { T.to(ce.halo, { opacity: 0.8 }, at, 0.3); T.to(ce.halo, { opacity: 0 }, at + 0.5, 0.7); });
        rs.forEach((re) => re.cells.forEach((cell) => { T.to(cell, { scale: 1.08 }, at, 0.3, "power2.out"); T.to(cell, { scale: 1 }, at + 0.32, 0.5, "power3.out"); }));
      } else if (a.do === "note") {
        const re = rs[0];
        note(a, re ? { x: LX0, y: re.y, w: CX1 - LX0, h: rh } : null, cs[0] ? cs[0].c.role : "info");
      } else if (a.do === "formula") formulaAction(ctx, F, a);
    }
    if (!colEls.some((ce) => ce.shown)) { colEls.forEach((ce, j) => showCol(ce, 0.4 + j * 0.12)); rowEls.forEach((re, i) => showRow(re, 0.8 + i * 0.35)); }
  }

  /* ---- scene entry ------------------------------------------------------------------------------------------- */
  function scene(id, data) {
    fontsReady().then(() => {
      const root = rootOf(id);
      const stage = el("div", "mk-scene", root);
      const tl = gsap.timeline({ paused: true });
      const T = Track(tl);
      const layer = el("div", "mk-stage", stage);
      const area = { x0: 150, x1: 1770, y0: data.formula && data.formula.length ? 270 : 175, y1: 862 };
      const ctx = { id, data, T, stage: layer, layer, area };
      T.init(layer, { opacity: 1, filter: "blur(0px)" });
      header(T, layer, data.num, data.title);
      const build = { graph, bars, patches, chart, timeline, compare }[data.template] || graph;
      build(ctx);
      exit(T, layer, data.dur);
      tl.set({}, {}, data.dur);       // the timeline spans the whole slot
      window.__timelines = window.__timelines || {};
      window.__timelines[id] = tl;
    });
  }

  /* ---- ground, intro, captions --------------------------------------------------------------------------- */
  function ground(id, d) {
    const root = rootOf(id);
    const g = el("div", "mk-ground", root);
    const a = el("div", "mk-glow-a", g), b = el("div", "mk-glow-b", g);
    el("div", "mk-dots", g);
    const grain = el("canvas", "mk-grain", g);
    grain.width = 960; grain.height = 540;
    const cx = grain.getContext("2d"), r = rng(7), img = cx.createImageData(960, 540);
    for (let i = 0; i < img.data.length; i += 4) { const v = Math.floor(r() * 255); img.data[i] = img.data[i + 1] = img.data[i + 2] = v; img.data[i + 3] = 255; }
    cx.putImageData(img, 0, 0);
    grain.style.width = "1920px"; grain.style.height = "1080px";
    el("div", "mk-vignette", g);
    const bar = el("div", "mk-progress", g);
    const tl = gsap.timeline({ paused: true });
    tl.fromTo(a, { x: 0, y: 0 }, { x: 140, y: 40, duration: d.duration, ease: "sine.inOut" }, 0);
    tl.fromTo(b, { x: 0, y: 0 }, { x: -220, y: -60, duration: d.duration, ease: "sine.inOut" }, 0);
    tl.fromTo(bar, { scaleX: 0 }, { scaleX: 1, duration: Math.max(1, d.end - d.start), ease: "none" }, d.start);
    tl.set({}, {}, d.duration);
    window.__timelines = window.__timelines || {};
    window.__timelines[id] = tl;
  }

  function intro(id, d) {
    fontsReady().then(() => {
      const root = rootOf(id);
      const box = el("div", "mk-intro", root);
      const k = el("div", "mk-kicker", box, esc(d.kicker));
      const t = el("div", "mk-title", box, d.title.split(/\s+/).map((w) => `<span>${esc(w)}</span>`).join(" "));
      const s = el("div", "mk-sub", box, d.sub.split(/\s+/).map((w) => `<span>${esc(w)}</span>`).join(" "));
      const tl = gsap.timeline({ paused: true });
      const T = Track(tl);
      T.init(k, { opacity: 0, x: -16 }); T.to(k, { opacity: 1, x: 0 }, 0.15, 0.5, "expo.out");
      [...t.children].forEach((w, i) => { T.init(w, { opacity: 0, filter: "blur(8px)" }); T.to(w, { opacity: 1, filter: "blur(0px)" }, 0.35 + i * 0.075, 0.18, "power2.out"); });
      [...s.children].forEach((w, i) => { T.init(w, { opacity: 0 }); T.to(w, { opacity: 1 }, 1.0 + i * 0.03, 0.25, "power2.out"); });
      T.init(box, { opacity: 1, filter: "blur(0px)" });
      T.to(box, { opacity: 0, filter: "blur(10px)" }, d.duration - 0.38, 0.32, "power2.in");
      tl.set({}, {}, d.duration);
      window.__timelines = window.__timelines || {};
      window.__timelines[id] = tl;
    });
  }

  function captions(id, groups, duration) {
    fontsReady().then(() => {
      const root = rootOf(id);
      const layer = el("div", "mk-caps", root);
      const tl = gsap.timeline({ paused: true });
      for (const g of groups) {
        const row = el("div", "mk-capgroup", layer);
        const box = el("div", "mk-capbox", row);
        const spans = g.words.map((w) => { const s = el("span", "", box, esc(w.text)); box.appendChild(document.createTextNode(" ")); return s; });
        tl.set(row, { opacity: 0, visibility: "visible" }, 0);
        tl.fromTo(row, { opacity: 0 }, { opacity: 1, duration: 0.16, ease: "power2.out", immediateRender: false }, g.start);
        g.words.forEach((w, i) => {
          tl.set(spans[i], { opacity: 0.45 }, 0);
          tl.fromTo(spans[i], { opacity: 0.45 }, { opacity: 1, duration: 0.12, ease: "power1.out", immediateRender: false }, Math.max(g.start, w.start - 0.03));
        });
        tl.to(row, { opacity: 0, duration: 0.12, ease: "power2.in" }, g.end - 0.12);
        tl.set(row, { opacity: 0, visibility: "hidden" }, g.end);
      }
      tl.set({}, {}, duration);
      window.__timelines = window.__timelines || {};
      window.__timelines[id] = tl;
    });
  }

  window.MK = { rootOf, scene, ground, intro, captions, fontsReady, header, exit, notes, formula, formulaAction, Track,
    ROLE, rng, hash, num, esc, el, svgEl, appear, vanish };
})();
