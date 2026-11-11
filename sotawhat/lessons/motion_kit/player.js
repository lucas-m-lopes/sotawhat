/* sotawhat lessons · the player of the 3D scenes outside HyperFrames: the interactive page of a lesson (one tab
   per 3D scene: the narration, the timeline, drag to turn, wheel or pinch to zoom) and, with probe: true, the page
   the headless probe drives before a render (window.__probe: seek, check, errors).
   It does what the HyperFrames runtime does for a scene: it seeks the GSAP timelines of the ground, the scene and
   the captions, and dispatches `hf-seek` with the scene time (offset 0) and `only` (the scene on screen). */
(function () {
  "use strict";
  const W = 1920, H = 1080;
  const fmt = (x) => `${Math.floor(x / 60)}:${String(Math.floor(x % 60)).padStart(2, "0")}`;
  const el = (tag, cls, parent, html) => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html !== undefined) e.innerHTML = html;
    if (parent) parent.appendChild(e);
    return e;
  };
  const waitFor = (test, ms) => new Promise((resolve, reject) => {
    const t0 = Date.now();
    (function poll() { if (test()) resolve(); else if (Date.now() - t0 > ms) reject(new Error("a cena não montou")); else setTimeout(poll, 30); })();
  });

  function start(opts) {
    const probe = !!opts.probe, orbit = opts.orbit || { yaw: 0, pitch: 0, zoom: 1 };
    const errors = [];
    window.addEventListener("error", (e) => errors.push(String(e.message || e)));
    window.addEventListener("unhandledrejection", (e) => errors.push(String((e.reason && e.reason.message) || e.reason)));
    document.body.classList.toggle("pl-probe", probe);
    const app = el("div", "pl-app", document.body);
    if (!probe) {
      const top = el("header", "pl-top", app);
      el("div", "pl-kicker", top, MK.esc(opts.kicker || "SOTA What · 3D interativo"));
      el("div", "pl-title", top, MK.esc(opts.title || ""));
    }
    const tabs = probe ? null : el("nav", "pl-tabs", app);
    const view = el("div", "pl-view", app);
    const frame = el("div", "pl-frame", view);
    let bar = null, play = null, range = null, clock = null;
    if (!probe) {
      bar = el("div", "pl-bar", app);
      play = el("button", "pl-play", bar, "▶ ouvir");
      range = el("input", "pl-range", bar);
      Object.assign(range, { type: "range", min: 0, step: 0.01, value: 0 });
      clock = el("span", "pl-clock", bar, "0:00");
      const reset = el("button", "pl-reset", bar, "↺ câmera da aula");
      el("span", "pl-hint", bar, "arraste para girar · roda ou pinça para aproximar");
      reset.onclick = () => { orbit.yaw = 0; orbit.pitch = 0; orbit.zoom = 1; seek(cur.t); };
    }

    const scenes = opts.scenes.map((s) => Object.assign({ t: 0, mounted: null, slot: null, audio: null }, s));
    let cur = null, playing = false;

    function fit() {
      const r = view.getBoundingClientRect();
      const k = probe ? 1 : Math.min(r.width / W, r.height / H) || 1;
      frame.style.transform = `translate(${(r.width - W * k) / 2}px, ${(r.height - H * k) / 2}px) scale(${k})`;
    }
    window.addEventListener("resize", fit);

    function mount(s) {
      if (s.mounted) return s.mounted;
      s.slot = el("div", "pl-slot", frame);
      for (const [cid, z] of [["bg-" + s.id, 0], [s.id, 20], ["caps-" + s.id, 60]]) {
        const d = el("div", "pl-layer", s.slot);
        d.setAttribute("data-composition-id", cid);
        d.style.zIndex = z;
      }
      MK.ground("bg-" + s.id, { duration: s.dur, start: 0, end: s.dur });
      MK.captions("caps-" + s.id, s.captions || [], s.dur);
      s.mount();
      if (s.audio) { s.audio = typeof s.audio === "string" ? new Audio(s.audio) : s.audio; s.audio.preload = "auto"; }
      s.mounted = waitFor(() => window.__timelines && window.__timelines[s.id] && window.__timelines["caps-" + s.id], 20000);
      return s.mounted;
    }

    function seek(t) {
      if (!cur) return;
      const s = cur;
      s.t = Math.max(0, Math.min(s.dur, t));
      for (const cid of ["bg-" + s.id, s.id, "caps-" + s.id]) { const tl = window.__timelines && window.__timelines[cid]; if (tl) tl.seek(s.t, false); }
      window.dispatchEvent(new CustomEvent("hf-seek", { detail: { time: s.t, only: s.id, waitUntil() {} } }));
      if (range) { range.max = s.dur; range.value = s.t; clock.textContent = `${fmt(s.t)} / ${fmt(s.dur)}`; }
    }

    function pause() {
      playing = false;
      if (cur && cur.audio) cur.audio.pause();
      if (play) play.textContent = "▶ ouvir";
    }
    let t0 = 0, w0 = 0;
    function loop() {
      if (!playing || !cur) return;
      const t = cur.audio ? cur.audio.currentTime : cur.t + 0;
      seek(cur.audio ? t : w0 + (performance.now() - t0) / 1000);
      if (cur.t >= cur.dur - 0.02 || (cur.audio && cur.audio.ended)) { pause(); return; }
      requestAnimationFrame(loop);
    }
    function resume() {
      if (!cur) return;
      if (cur.t >= cur.dur - 0.05) seek(0);
      playing = true;
      if (play) play.textContent = "❚❚ pausar";
      if (cur.audio) { cur.audio.currentTime = cur.t; cur.audio.play().catch(() => pause()); }
      t0 = performance.now(); w0 = cur.t;
      requestAnimationFrame(loop);
    }

    async function show(i) {
      pause();
      const s = scenes[i];
      for (const x of scenes) if (x.slot) x.slot.style.display = x === s ? "block" : "none";
      if (tabs) [...tabs.children].forEach((b, k) => b.classList.toggle("on", k === i));
      await mount(s);
      s.slot.style.display = "block";
      cur = s;
      orbit.yaw = 0; orbit.pitch = 0; orbit.zoom = 1;
      fit();
      seek(s.t);
    }

    if (tabs) scenes.forEach((s, i) => { const b = el("button", "pl-tab", tabs, `<b>${String(s.num).padStart(2, "0")}</b> ${MK.esc(s.title)}`); b.onclick = () => show(i); });
    if (play) play.onclick = () => (playing ? pause() : resume());
    if (range) range.oninput = () => { seek(Number(range.value)); if (playing && cur.audio) cur.audio.currentTime = cur.t; w0 = cur.t; t0 = performance.now(); };
    window.addEventListener("keydown", (e) => { if (e.code === "Space" && !probe) { e.preventDefault(); playing ? pause() : resume(); } });

    // drag to turn, wheel or pinch to zoom: the same camera the labels are projected with
    const pts = new Map();
    let pinch = 0;
    const redraw = () => { if (!playing) seek(cur.t); };
    view.addEventListener("pointerdown", (e) => { pts.set(e.pointerId, { x: e.clientX, y: e.clientY }); view.setPointerCapture(e.pointerId); });
    view.addEventListener("pointermove", (e) => {
      const p = pts.get(e.pointerId);
      if (!p || !cur) return;
      if (pts.size === 1) {
        orbit.yaw -= (e.clientX - p.x) * 0.006;
        orbit.pitch = Math.max(-1.2, Math.min(1.2, orbit.pitch + (e.clientY - p.y) * 0.004));
      } else if (pts.size === 2) {
        const [a, b] = [...pts.values()];
        const d = Math.hypot(a.x - b.x, a.y - b.y);
        if (pinch) orbit.zoom = Math.max(0.4, Math.min(2.4, orbit.zoom * pinch / Math.max(1, d)));
        pinch = d;
      }
      p.x = e.clientX; p.y = e.clientY;
      redraw();
    });
    const up = (e) => { pts.delete(e.pointerId); pinch = 0; };
    view.addEventListener("pointerup", up);
    view.addEventListener("pointercancel", up);
    view.addEventListener("wheel", (e) => { e.preventDefault(); orbit.zoom = Math.max(0.4, Math.min(2.4, orbit.zoom * Math.exp(e.deltaY * 0.0012))); redraw(); }, { passive: false });

    const ready = show(0);
    window.__probe = {
      errors,
      ready: false,
      seek: (t) => seek(t),
      check: (t) => (window.__check3d && window.__check3d[cur.id] ? window.__check3d[cur.id](t) : []),
    };
    ready.then(() => { window.__probe.ready = true; }, (e) => { errors.push(String(e.message || e)); window.__probe.ready = true; });
  }

  window.PLAYER = { start };
})();
