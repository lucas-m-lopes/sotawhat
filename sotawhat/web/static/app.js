// sotawhat/web/static/app.js — the graph interface (SDD §6.11). Vanilla JS over the local API;
// graphology + graphology-library (ForceAtlas2, Louvain) + sigma.js 3, all served from /static/vendor.
// Three views behind the header tabs (#grafo, #ideias, #tendencias); the ideas and trends pages are P4.
// Every piece of data goes into the page through textContent, never as HTML.
"use strict";
(() => {
  const TYPES = {
    technique: { label: "técnica", color: "#4C78A8" },
    model: { label: "modelo", color: "#B279A2" },
    dataset: { label: "dataset", color: "#2FA39C" },
    organization: { label: "organização", color: "#F58518" },
    product: { label: "produto", color: "#54A24B" },
    problem: { label: "problema", color: "#E45756" },
    regulation: { label: "regulação", color: "#9D755D" },
  };
  const CATEGORIES = { domain: "domínio", problem_type: "tipo de problema", technique_family: "família de técnica" };
  const CATEGORY_COLOR = "#A8A29E";
  const COMMUNITY_COLORS = ["#4C78A8", "#F58518", "#54A24B", "#E45756", "#2FA39C", "#B279A2", "#E2B000", "#FF8FA3",
                            "#9D755D", "#6F7A85", "#2E86AB", "#C05621"];
  const DAYS = [[7, "7 dias"], [30, "30 dias"], [90, "90 dias"], [365, "1 ano"], [0, "tudo"]];
  const COLOR_BY = [["type", "tipo"], ["community", "comunidade"]];
  const VOTES = [["up", "👍", "relevante"], ["down", "👎", "não relevante"], ["test", "🧪", "quero testar"]];
  const ROLE = { main: "principal", used: "usado", mentioned: "citado", tag: "categoria" };

  const state = { days: 30, types: new Set(Object.keys(TYPES)), categories: false, min: 1, limit: 250,
                  colorBy: "type", focus: null, selected: null, hovered: null, data: null, stats: null, view: null };
  let renderer = null;
  let graph = null;

  // --- helpers ---------------------------------------------------------------
  const $ = (selector) => document.querySelector(selector);

  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs || {})) {
      if (value === null || value === undefined || value === false) continue;
      if (key === "class") node.className = value;
      else if (key === "text") node.textContent = value;
      else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
      else node.setAttribute(key, value === true ? "" : String(value));
    }
    for (const child of children.flat()) {
      if (child === null || child === undefined || child === false) continue;
      node.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return node;
  }

  const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const typeColor = (type) => (TYPES[type] || {}).color || CATEGORY_COLOR;
  const typeLabel = (type) => (TYPES[type] || {}).label || CATEGORIES[type] || type;
  const safeUrl = (url) => (/^https?:\/\//i.test(url || "") ? url : null);

  function fmtDate(iso) {
    if (!iso) return "?";
    const d = new Date(iso);
    return Number.isNaN(d.getTime()) ? String(iso).slice(0, 10)
      : d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "2-digit" });
  }

  const num = (value, digits = 2) => (value === null || value === undefined ? "–"
    : Number(value).toFixed(digits).replace(".", ","));

  async function api(path, options) {
    const response = await fetch(path, options);
    if (!response.ok) throw new Error(`${response.status} ${(await response.text()).slice(0, 200)}`);
    return response.json();
  }

  function hash(text) {   // FNV-1a: stable initial positions, so the layout does not jump on reload
    let h = 2166136261;
    for (let i = 0; i < text.length; i += 1) { h ^= text.charCodeAt(i); h = Math.imul(h, 16777619); }
    return h >>> 0;
  }

  function seededRandom(seed) {
    let a = seed >>> 0;
    return () => {
      a = (a + 0x6D2B79F5) >>> 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // --- filters (kept in this browser only) -----------------------------------
  function saveFilters() {
    try {
      localStorage.setItem("sotawhat.filters", JSON.stringify({ days: state.days, types: [...state.types],
        categories: state.categories, min: state.min, limit: state.limit, colorBy: state.colorBy }));
    } catch (e) { /* private window or blocked storage: filters just reset */ }
  }

  function loadFilters() {
    try {
      const saved = JSON.parse(localStorage.getItem("sotawhat.filters") || "null");
      if (!saved) return;
      if (DAYS.some(([d]) => d === saved.days)) state.days = saved.days;
      const types = (saved.types || []).filter((t) => TYPES[t]);
      if (types.length) state.types = new Set(types);
      state.categories = Boolean(saved.categories);
      state.min = Math.min(Math.max(Number(saved.min) || 1, 1), 10);
      state.limit = Math.min(Math.max(Number(saved.limit) || 250, 50), 1000);
      if (COLOR_BY.some(([c]) => c === saved.colorBy)) state.colorBy = saved.colorBy;
    } catch (e) { /* ignore */ }
  }

  function segmented(container, options, current, onPick) {
    container.replaceChildren(...options.map(([value, label]) => el("button", {
      type: "button", role: "radio", "aria-checked": String(value === current),
      onclick: () => {
        container.querySelectorAll("button").forEach((b) => b.setAttribute("aria-checked", "false"));
        container.querySelector(`[data-value="${value}"]`).setAttribute("aria-checked", "true");
        onPick(value);
      },
      "data-value": value,
    }, label)));
  }

  function buildFilters() {
    segmented($("#days"), DAYS, state.days, (value) => { state.days = value; refilter(); });
    segmented($("#color-by"), COLOR_BY, state.colorBy, (value) => {
      state.colorBy = value; saveFilters(); if (renderer) renderer.refresh({ skipIndexation: true });
    });
    $("#types").replaceChildren(...Object.entries(TYPES).map(([type, info]) => el("label", { class: "check" },
      el("input", { type: "checkbox", checked: state.types.has(type), onchange: (ev) => {
        if (ev.target.checked) state.types.add(type); else state.types.delete(type);
        refilter();
      } }),
      el("span", { class: "dot", style: `background:${info.color}` }), info.label,
      el("span", { class: "count", "data-type": type }))));
    const categories = $("#categories");
    categories.checked = state.categories;
    categories.addEventListener("change", () => { state.categories = categories.checked; refilter(); });
    for (const [id, key] of [["min", "min"], ["limit", "limit"]]) {
      const input = $(`#${id}`);
      const out = $(`#${id}-out`);
      input.value = state[key];
      out.textContent = state[key];
      input.addEventListener("input", () => { out.textContent = input.value; });
      input.addEventListener("change", () => { state[key] = Number(input.value); refilter(); });
    }
  }

  function refilter() {
    saveFilters();
    loadGraph();
  }

  // --- graph -------------------------------------------------------------------
  function setStatus(text) { $("#status").textContent = text; }

  function showOverlay(text) {
    const overlay = $("#overlay");
    overlay.hidden = !text;
    overlay.replaceChildren(text ? el("div", {}, text) : "");
  }

  async function loadGraph() {
    graphLoaded = true;
    const types = [...state.types];
    if (state.categories) types.push(...Object.keys(CATEGORIES));
    const params = new URLSearchParams({ days: String(state.days), min: String(state.min),
                                         limit: String(state.limit), types: types.join(",") });
    if (state.focus) params.set("focus", state.focus);
    setStatus("carregando…");
    try {
      state.data = await api(`/api/graph?${params}`);
    } catch (e) {
      setStatus("");
      showOverlay(`Não consegui carregar o grafo (${e.message}).`);
      return;
    }
    draw(state.data);
  }

  function nodeColor(attrs) {
    if (state.colorBy === "community" && attrs.community !== undefined) {
      return COMMUNITY_COLORS[attrs.community % COMMUNITY_COLORS.length];
    }
    return typeColor(attrs.kind);
  }

  function drawHover(context, data, settings) {
    const size = settings.labelSize;
    context.font = `600 ${size}px ${settings.labelFont}`;
    const label = data.label || "";
    const width = context.measureText(label).width + 14;
    const height = size + 10;
    const x = data.x + data.size + 5;
    const y = data.y - height / 2;
    context.fillStyle = css("--panel");
    context.strokeStyle = css("--line");
    context.lineWidth = 1;
    context.beginPath();
    if (context.roundRect) context.roundRect(x, y, width, height, 6); else context.rect(x, y, width, height);
    context.fill();
    context.stroke();
    context.fillStyle = css("--fg");
    context.fillText(label, x + 7, data.y + size / 3);
    context.beginPath();
    context.arc(data.x, data.y, data.size + 2.5, 0, Math.PI * 2);
    context.strokeStyle = css("--accent");
    context.lineWidth = 2;
    context.stroke();
  }

  function nodeReducer(node, data) {
    const res = { ...data, color: nodeColor(data) };
    const active = state.hovered || state.selected;
    if (active && graph.hasNode(active)) {
      if (node === active) {
        res.highlighted = true;
        res.zIndex = 2;
      } else if (graph.areNeighbors(active, node)) {
        res.zIndex = 1;
      } else {
        res.color = css("--dim");
        res.label = "";
        res.zIndex = 0;
      }
    }
    return res;
  }

  function edgeReducer(edge, data) {
    const res = { ...data, color: data.kind === "co" ? css("--edge") : css("--edge-typed") };
    const active = state.hovered || state.selected;
    if (active && graph.hasNode(active) && !graph.hasExtremity(edge, active)) res.hidden = true;
    return res;
  }

  function draw(data) {
    graph = new graphology.Graph({ type: "undirected", multi: false, allowSelfLoops: false });
    for (const node of data.nodes) {
      const start = seededRandom(hash(node.id));
      graph.addNode(node.id, { label: node.label, kind: node.type, entity: node, x: start(), y: start(),
                               size: Math.min(5 + 2.4 * Math.sqrt(node.count || 1), 22) });
    }
    for (const edge of data.edges) {
      if (!graph.hasNode(edge.source) || !graph.hasNode(edge.target) || graph.hasEdge(edge.source, edge.target)) continue;
      graph.addEdgeWithKey(edge.id, edge.source, edge.target, {
        kind: edge.kind, label: edge.label, weight: edge.weight, type: edge.directed ? "arrow" : "line",
        size: Math.min(0.6 + Math.log2(1 + edge.weight), 4) });
    }
    const lib = graphologyLibrary;
    if (graph.order > 1) {
      try {
        lib.communitiesLouvain.assign(graph, { rng: seededRandom(42) });
      } catch (e) { /* no edges at all: no communities */ }
      const settings = lib.layoutForceAtlas2.inferSettings(graph);
      lib.layoutForceAtlas2.assign(graph, { iterations: graph.order > 500 ? 150 : 300,
        settings: { ...settings, gravity: 0.6, scalingRatio: 18, slowDown: 3, barnesHutOptimize: graph.order > 300 } });
    }
    if (state.selected && !graph.hasNode(state.selected)) state.selected = null;
    if (renderer) renderer.kill();
    renderer = new Sigma(graph, $("#graph"), {
      // most entities start with a single mention: label them too and let the label grid avoid overlaps
      renderEdgeLabels: false, zIndex: true, labelRenderedSizeThreshold: 6, labelDensity: 0.8, labelGridCellSize: 60,
      labelFont: "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif", labelSize: 13, labelWeight: "500",
      labelColor: { color: css("--fg") }, defaultEdgeColor: css("--edge"), defaultNodeColor: CATEGORY_COLOR,
      minCameraRatio: 0.05, maxCameraRatio: 4, defaultDrawNodeHover: drawHover, nodeReducer, edgeReducer,
      allowInvalidContainer: true,   // the graph view can be hidden while another tab is open
    });
    renderer.on("enterNode", ({ node }) => { state.hovered = node; renderer.refresh({ skipIndexation: true }); });
    renderer.on("leaveNode", () => { state.hovered = null; renderer.refresh({ skipIndexation: true }); });
    renderer.on("leaveStage", () => {   // the pointer can leave the canvas without a leaveNode
      if (state.hovered) { state.hovered = null; renderer.refresh({ skipIndexation: true }); }
    });
    renderer.on("clickNode", ({ node }) => selectNode(node));
    renderer.on("doubleClickNode", ({ node, event }) => { event.preventSigmaDefault(); focusOn(node); });
    renderer.on("clickStage", () => { state.selected = null; renderer.refresh({ skipIndexation: true }); });
    updateCounts(data);
    const window = data.window.days ? `últimos ${data.window.days} dias` : "todo o período";
    setStatus(`${data.nodes.length} entidades · ${data.edges.length} conexões · ${window}`
              + (data.truncated ? ` · as ${data.nodes.length} mais citadas` : ""));
    $("#unfocus").hidden = !state.focus;
    if (!data.nodes.length) {
      const empty = state.stats && Object.values(state.stats.entities || {}).every((n) => !n);
      showOverlay(empty ? "O grafo ainda está vazio. Rode `sotawhat graph extract` para extrair as entidades dos "
                          + "itens já aprovados, ou espere o próximo run diário."
                        : "Nada com estes filtros. Aumente o período, marque mais tipos ou reduza o mínimo de menções.");
    } else {
      showOverlay("");
    }
    if (state.focus && graph.hasNode(state.focus)) selectNode(state.focus, false);
  }

  function updateCounts(data) {
    const counts = {};
    for (const node of data.nodes) counts[node.type] = (counts[node.type] || 0) + 1;
    document.querySelectorAll(".count[data-type]").forEach((span) => {
      span.textContent = counts[span.dataset.type] || "";
    });
  }

  function centerOn(node) {
    const display = renderer && renderer.getNodeDisplayData(node);
    if (!display) return;
    const camera = renderer.getCamera();
    camera.animate({ x: display.x, y: display.y, ratio: Math.min(camera.ratio, 0.7) }, { duration: 450 });
  }

  function selectNode(node, open = true) {
    state.selected = node;
    state.hovered = null;
    renderer.refresh({ skipIndexation: true });
    centerOn(node);
    if (open) openEntity(graph.getNodeAttribute(node, "entity").entity_id);
  }

  function focusOn(node) {
    state.focus = node;
    loadGraph();
    openEntity(String(node).replace(/^e/, ""));
  }

  async function goToEntity(entityId) {
    const node = `e${entityId}`;
    if (graph && graph.hasNode(node)) selectNode(node);
    else { state.focus = node; await loadGraph(); openEntity(entityId); }
  }

  // --- side panel --------------------------------------------------------------
  const panel = () => $("#panel");
  let history = [];

  function sectionBadge(item) {
    return el("span", { class: `badge ${item.decision || ""}` }, item.section || item.decision || "?");
  }

  function entityChip(entity, extra) {
    return el("button", { class: "chip", type: "button", title: typeLabel(entity.type),
                          onclick: () => goToEntity(entity.entity_id) },
      el("span", { class: "dot", style: `background:${typeColor(entity.type)}` }), entity.name,
      extra !== undefined ? el("small", {}, extra) : null);
  }

  function neighborChips(title, neighbors) {
    if (!neighbors.length) return null;
    return [el("h3", {}, title), el("div", { class: "chips" }, neighbors.map((n) => entityChip(n, n.shared)))];
  }

  function voteButtons(itemId, current) {
    const box = el("div", { class: "votes", role: "group", "aria-label": "Votar neste item" });
    for (const [value, emoji, title] of VOTES) {
      box.append(el("button", { class: "vote", type: "button", title, "aria-label": title,
                                "aria-pressed": String(current === value), onclick: async () => {
        try {
          const res = await api("/api/feedback", { method: "POST", headers: { "content-type": "application/json" },
                                                   body: JSON.stringify({ item_id: itemId, value }) });
          box.querySelectorAll("button").forEach((b, i) => b.setAttribute("aria-pressed", String(VOTES[i][0] === res.vote)));
        } catch (e) {
          box.append(el("span", { class: "error" }, " erro ao votar"));
        }
      } }, emoji));
    }
    return box;
  }

  function itemCard(item) {
    const url = safeUrl(item.url);
    return el("div", { class: "item" },
      el("div", { class: "head" }, sectionBadge(item),
        el("span", { class: "meta" }, `${fmtDate(item.fetched_at)} · ${item.source}`,
          url ? el("a", { href: url, target: "_blank", rel: "noopener noreferrer", title: "abrir a fonte" }, "↗") : null)),
      el("button", { class: "title", type: "button", onclick: () => openItem(item.id) }, item.title),
      item.summary_pt ? el("p", { class: "clamp" }, item.summary_pt) : null,
      voteButtons(item.id, item.vote));
  }

  function showPanel(...children) {
    panel().replaceChildren(...children.flat(Infinity).filter((c) => c !== null && c !== undefined && c !== false));
    panel().scrollTop = 0;
  }

  function meta(...parts) {   // each part in its own span, so the flex gap separates them
    return el("div", { class: "meta" }, parts.filter((p) => p !== null && p !== undefined && p !== false)
      .map((p) => (p instanceof Node ? p : el("span", {}, p))));
  }

  function backButton() {
    if (history.length < 2) return null;
    return el("button", { class: "back", type: "button", onclick: () => {
      history.pop();
      const previous = history.pop();
      if (previous) previous();
    } }, "← voltar");
  }

  async function openEntity(entityId) {
    let d;
    try { d = await api(`/api/entity/${encodeURIComponent(entityId)}`); }
    catch (e) { showPanel(el("p", { class: "error" }, `Entidade não encontrada (${e.message}).`)); return; }
    history.push(() => openEntity(entityId));
    const relations = d.relations.map((r) => el("div", { class: "rel" },
      el("span", { class: "muted" }, r.direction === "out" ? `${r.label} →` : `← ${r.label}`),
      entityChip(r.other), r.items > 1 ? el("small", { class: "muted" }, `${r.items} itens`) : null));
    showPanel(
      backButton(),
      el("div", {}, el("span", { class: "badge" }, el("span", { class: "dot", style: `background:${typeColor(d.type)}` }),
        typeLabel(d.type)), d.category_label ? el("span", { class: "badge", style: "margin-left:6px" },
        `${d.category} · ${d.category_label}`) : null),
      el("h1", {}, d.name),
      meta(`${d.mention_count} ${d.mention_count === 1 ? "item" : "itens"}`, `primeira vez ${fmtDate(d.first_seen)}`,
        `última ${fmtDate(d.last_seen)}`),
      d.aliases.length ? meta(`também: ${d.aliases.join(", ")}`) : null,
      el("div", { class: "toolbar" },
        el("button", { class: "chip", type: "button", onclick: () => focusOn(`e${d.entity_id}`) }, "focar no grafo")),
      relations.length ? [el("h3", {}, "Relações"), ...relations] : null,
      neighborChips("Aparece junto com", d.neighbors.filter((n) => TYPES[n.type])),
      neighborChips("Categorias frequentes", d.neighbors.filter((n) => !TYPES[n.type])),
      d.claims.length ? [el("h3", {}, "Números"), el("ul", { class: "claims" },
        d.claims.map((c) => el("li", {}, c.text_pt, el("span", { class: "muted" }, ` (${c.metric}: ${c.value})`))))] : null,
      el("h3", {}, `Itens (${d.items.length})`), d.items.map(itemCard));
  }

  async function openItem(itemId) {
    let d;
    try { d = await api(`/api/item?id=${encodeURIComponent(itemId)}`); }
    catch (e) { showPanel(el("p", { class: "error" }, `Item não encontrado (${e.message}).`)); return; }
    history.push(() => openItem(itemId));
    const url = safeUrl(d.url);
    const tags = [...(d.tags.domains || []), ...(d.tags.techniques || []), ...(d.tags.problem_types || [])];
    const entities = d.entities.filter((e) => e.role !== "tag");
    showPanel(
      backButton(),
      el("div", { class: "head" }, sectionBadge(d), d.total !== null ? el("span", { class: "badge" }, `nota ${num(d.total)}`)
        : null),
      el("h1", {}, url ? el("a", { href: url, target: "_blank", rel: "noopener noreferrer" }, d.title) : d.title),
      meta(fmtDate(d.fetched_at), (d.sources && d.sources.length ? d.sources : [d.source]).join(" + "),
        d.extraction ? `maturidade: ${d.extraction.maturity}` : null),
      d.summary_pt ? el("p", {}, d.summary_pt) : null,
      d.why_it_matters_pt ? el("div", { class: "why" }, el("b", {}, "Por que importa: "), d.why_it_matters_pt) : null,
      voteButtons(d.id, d.vote),
      entities.length ? [el("h3", {}, "Entidades"), el("div", { class: "chips" },
        entities.map((e) => entityChip(e, ROLE[e.role] || e.role)))] : null,
      tags.length ? [el("h3", {}, "Categorias da triagem"), el("div", { class: "chips" },
        tags.map((t) => el("span", { class: "chip" }, `${t.key} · ${t.label}`)))] : null,
      d.extraction && d.extraction.claims.length ? [el("h3", {}, "Números"), el("ul", { class: "claims" },
        d.extraction.claims.map((c) => el("li", {}, c.text_pt, el("span", { class: "muted" }, ` (${c.metric}: ${c.value})`))))]
        : null);
  }

  // --- search --------------------------------------------------------------------
  let searchTimer = null;

  function hideResults() { $("#results").hidden = true; }

  async function runSearch(text) {
    let res;
    try { res = await api(`/api/search?q=${encodeURIComponent(text)}`); } catch (e) { return; }
    const box = $("#results");
    const rows = [];
    if (res.entities.length) {
      rows.push(el("div", { class: "group" }, "Entidades"));
      rows.push(...res.entities.map((e) => el("button", { type: "button", role: "option",
        onclick: () => { hideResults(); openInGraph(e.entity_id); } },
        el("span", { class: "dot", style: `display:inline-block;width:8px;height:8px;border-radius:50%;background:${typeColor(e.type)}` }),
        e.name, el("small", { class: "muted" }, ` ${typeLabel(e.type)} · ${e.mentions}`))));
    }
    if (res.items.length) {
      rows.push(el("div", { class: "group" }, "Itens"));
      rows.push(...res.items.map((i) => el("button", { type: "button", role: "option",
        onclick: () => { hideResults(); toGraph(); ensureGraph(); openItem(i.id); } }, i.title,
        el("small", { class: "muted" }, ` ${i.section} · ${fmtDate(i.fetched_at)}`))));
    }
    if (!rows.length) rows.push(el("div", { class: "group" }, "nada encontrado"));
    box.replaceChildren(...rows);
    box.hidden = false;
  }

  function wireSearch() {
    const input = $("#search");
    input.addEventListener("input", () => {
      clearTimeout(searchTimer);
      const text = input.value.trim();
      if (text.length < 2) { hideResults(); return; }
      searchTimer = setTimeout(() => runSearch(text), 220);
    });
    input.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape") { hideResults(); input.blur(); }
      if (ev.key === "Enter") { const first = $("#results button"); if (first) first.click(); }
    });
    document.addEventListener("click", (ev) => { if (!ev.target.closest(".search")) hideResults(); });
  }

  // --- header ----------------------------------------------------------------------
  async function loadStats() {
    try { state.stats = await api("/api/stats"); } catch (e) { return; }
    const s = state.stats;
    const entities = Object.entries(s.entities).filter(([t]) => TYPES[t]).reduce((sum, [, n]) => sum + n, 0);
    const parts = [`${s.approved} itens aprovados`, `${entities} entidades`, `${s.relations} relações`];
    if (s.pending_extraction) parts.push(`${s.pending_extraction} na fila de extração`);
    $("#stats").textContent = parts.join(" · ");
    $("#stats").title = `${s.items} itens coletados · último run diário ${fmtDate(s.last_daily_run)}`;
  }

  // --- views (P4) --------------------------------------------------------------------
  const VIEWS = { graph: "#view-graph", ideas: "#view-ideas", trends: "#view-trends" };
  const HASHES = { "#grafo": "graph", "#ideias": "ideas", "#tendencias": "trends" };
  const TITLES = { graph: "sotawhat · grafo", ideas: "sotawhat · ideias", trends: "sotawhat · tendências" };
  let graphLoaded = false;

  function showView(name) {
    for (const [key, selector] of Object.entries(VIEWS)) $(selector).hidden = key !== name;
    document.querySelectorAll(".views a").forEach((a) => {
      if (a.dataset.view === name) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
    });
    document.title = TITLES[name];
    state.view = name;
  }

  function ensureGraph() {   // the graph loads the first time its tab is shown
    if (!graphLoaded) loadGraph();
    else if (renderer) { renderer.resize(); renderer.refresh(); }
  }

  function route() {
    const name = HASHES[location.hash] || "graph";
    showView(name);
    if (name === "graph") ensureGraph();
    else if (name === "ideas") loadIdeas();
    else loadTrends();
  }

  function toGraph() {       // before opening an entity or an item from another tab
    if (state.view === "graph") return;
    showView("graph");
    if (location.hash !== "#grafo") location.hash = "#grafo";
    if (renderer) { renderer.resize(); renderer.refresh(); }
  }

  function openInGraph(entityId) {
    if (entityId === null || entityId === undefined) return;
    toGraph();
    goToEntity(entityId);
  }

  function entityLink(id, name, type) {
    return el("button", { class: "chip", type: "button", title: `${typeLabel(type)} · abrir no grafo`,
                          onclick: () => openInGraph(id) },
      el("span", { class: "dot", style: `background:${typeColor(type)}` }), name);
  }

  function pairs(rows) {     // [[label, value]] -> <dt>/<dd>, skipping empty values
    return rows.filter(([, v]) => v !== null && v !== undefined && String(v).trim() !== "")
      .flatMap(([k, v]) => [el("dt", {}, k), el("dd", {}, v)]);
  }

  // --- ideas (P4) --------------------------------------------------------------------
  const IDEA_FILTERS = [["", "todas"], ["nova", "novas"], ["curtida", "👍 explorar"], ["testar", "🧪 testar"],
                        ["engavetada", "🗄️ engavetadas"], ["construida", "🛠️ construídas"], ["rejeitada", "👎 rejeitadas"],
                        ["descartada", "descartadas"]];
  const IDEA_STATUS = { nova: "nova", curtida: "👍 explorar", testar: "🧪 testar", engavetada: "🗄️ engavetada",
                        construida: "🛠️ construída", rejeitada: "👎 rejeitada", descartada: "descartada" };
  const IDEA_VOTES = [["up", "👍 explorar", "curtida"], ["test", "🧪 testar", "testar"],
                      ["archive", "🗄️ engavetar", "engavetada"], ["built", "🛠️ construí", "construida"],
                      ["down", "👎 não", "rejeitada"]];
  const AXES = { valor: "valor", viabilidade_tecnica: "viab. técnica", viabilidade_negocio: "viab. negócio",
                 novidade: "novidade", regulatorio: "regulatório", tempo_piloto: "tempo até piloto", fit: "fit",
                 adocao: "adoção" };
  const FACETS = { problema: "problema", tecnica: "técnica", dado: "dado", integracao: "integração",
                   modelo_negocio: "modelo de negócio", geografia: "geografia/BR" };
  const FACET_STATE = { nao_encontrado: "não encontrado", parcial: "parcial", igual: "igual", a_verificar: "a verificar" };
  const ROLES = { clinico: "Clínico", operacoes: "Operações/CFO", regulatorio: "Regulatório/LGPD", dados: "Dados/integração",
                  ml: "Cientista de ML", paciente_etica: "Paciente/ética" };
  const LENSES = { tech_push: "tech-push", jtbd: "JTBD", scamper: "SCAMPER", triz: "TRIZ", errc: "ERRC", analogia: "analogia",
                   cenario_2029: "cenário 2029", negativa: "contrária" };
  const FORMS = { produto_b2b: "produto B2B", plataforma: "plataforma", dispositivo: "dispositivo",
                  servico_corporativo: "serviço corporativo", b2b2c: "B2B2C" };
  const SAMD = { nao_samd: "não é SaMD", I: "classe I", II: "classe II", III: "classe III", IV: "classe IV", incerto: "incerta" };
  const ideasState = { status: "", all: false, reasons: [], loading: 0 };

  async function loadIdeas() {
    const ticket = ++ideasState.loading;
    const params = new URLSearchParams({ finalists: String(!ideasState.all), limit: "200" });
    if (ideasState.status) params.set("status", ideasState.status);
    let data;
    try { data = await api(`/api/ideas?${params}`); } catch (e) {
      $("#ideas-summary").textContent = `Não consegui carregar as ideias (${e.message}).`;
      return;
    }
    if (ticket !== ideasState.loading) return;     // a newer filter click already asked again
    ideasState.reasons = data.reasons || [];
    const counts = data.counts || {};
    segmented($("#ideas-status"), IDEA_FILTERS.map(([value, label]) => [value, `${label} ${value ? counts[value] || 0 : data.total}`]),
      ideasState.status, (value) => { ideasState.status = value; loadIdeas(); });
    const scope = ideasState.all ? "no ledger" : "finalistas";
    $("#ideas-summary").textContent = data.total
      ? `${data.total} ideias ${scope} · ${counts.curtida || 0} para explorar · ${counts.testar || 0} para testar · `
        + `${counts.engavetada || 0} engavetadas`
      : "";
    const list = $("#ideas-list");
    if (!data.ideas.length) {
      list.replaceChildren(el("p", { class: "empty-note" }, data.total
        ? "Nenhuma ideia com esta situação."
        : "Ainda não há ideias. Rode `sotawhat ideate --n 4` ou espere o run semanal (domingo, 20:00)."));
      return;
    }
    const blocks = [];
    let lastRun = null;
    for (const idea of data.ideas) {
      if (idea.run_id !== lastRun) {
        lastRun = idea.run_id;
        blocks.push(el("h3", {}, `Lote do run ${idea.run_id} · ${fmtDate(idea.created_at)}`));
      }
      blocks.push(ideaCard(idea));
    }
    list.replaceChildren(...blocks);
  }

  function ideaCard(idea) {
    const d = idea.draft || {};
    const badge = el("span", { class: `badge st-${IDEA_STATUS[idea.status] ? idea.status : "nova"}` },
                     IDEA_STATUS[idea.status] || idea.status);
    const card = el("article", { class: "idea" },
      el("div", { class: "head" }, badge, el("span", { class: "badge", title: "nota da rubrica (0–10)" },
        el("span", { class: "score" }, num(idea.score))),
        meta(`lente ${LENSES[idea.lens] || idea.lens || "?"}`, idea.persona, `${d.setor || "?"} ${idea.sector_label || ""}`.trim(),
             FORMS[d.forma] || d.forma, `idea:${idea.id}`)),
      el("h2", {}, idea.title),
      el("dl", {}, pairs([[`Problema${d.stakeholder_dono ? ` (dono: ${d.stakeholder_dono})` : ""}`, d.problema_jtbd],
                          ["Como funciona", d.mecanismo], ["Por que agora", d.why_now], ["Hipótese nula", d.hipotese_nula],
                          ["Descartada", idea.discard_reason]])),
      ideaDetails(idea));
    card.append(...ideaVotes(idea, badge));
    return card;
  }

  function neighborLine(layer, list) {
    const parts = [];
    list.forEach((n, i) => {
      if (i) parts.push("; ");
      const url = safeUrl(n.url);
      parts.push(url ? el("a", { href: url, target: "_blank", rel: "noopener noreferrer" }, n.title) : n.title);
      parts.push(` (${n.year || "?"})`);
    });
    return el("div", { class: "critique" }, el("b", {}, `${layer}: `), ...parts);
  }

  function ideaDetails(idea) {
    const d = idea.draft || {};
    const c = idea.candidate || {};
    const body = el("div", {});
    const box = el("details", {}, el("summary", {}, "rubrica, novidade, críticas, dossiê e evidências"), body);
    const axes = Object.entries(idea.axes || {});
    const facets = Object.entries(idea.facets || {});
    const dz = idea.dossie;
    const neighbors = Object.entries(idea.neighbors || {});
    const unverified = idea.unverified || [];
    const critiques = idea.critiques || [];
    const nasss = idea.nasss !== null && idea.nasss !== undefined ? ` · NASSS: ${idea.nasss} domínios complexos` : "";
    body.append(
      el("dl", {}, pairs([["Técnicas", (d.tecnicas || []).join(", ")], ["Capacidade", d.capacidade_intermediaria],
                          ["Dados", (d.dado_necessario || []).join(", ")], ["Integração", d.integracao],
                          ["Modelo de negócio", d.modelo_negocio], ["Riscos", (d.riscos || []).join("; ")]])));
    if (c.technique) {
      body.append(el("h3", {}, "Par do grafo que originou a ideia"),
        el("div", { class: "chips" }, entityLink(c.technique_id, c.technique, c.technique_type || "technique"),
          el("span", { class: "muted" }, "×"), entityLink(c.problem_id, c.problem, "problem")),
        meta(c.sampler ? `amostrador: ${c.sampler}` : null, c.why_now));
    }
    if (axes.length) {
      const gates = (idea.gates && idea.gates.length ? ` · gates: ${idea.gates.join(", ")}` : "")
        + (idea.disputed_gates && idea.disputed_gates.length
          ? ` · gates em disputa (só um juiz; confira): ${idea.disputed_gates.join(", ")}` : "");
      body.append(el("h3", {}, `Rubrica · confiança ${num(idea.confidence)}${gates}`),
        el("div", { class: "axes" }, axes.flatMap(([k, v]) => [el("span", {}, AXES[k] || k),
          el("span", { class: "bar" }, el("span", { style: `width:${Math.max(0, Math.min(10, Number(v) || 0)) * 10}%` })),
          el("span", { class: "muted" }, num(v, 1))])));
      if ((idea.justifications || []).length) {
        body.append(el("ul", { class: "claims" }, idea.justifications.map((j) => el("li", {}, j))));
      }
    }
    if (facets.length) {
      body.append(el("h3", {}, `Novidade por faceta · nota ${num(idea.novelty, 1)}`), el("div", { class: "facets" },
        facets.map(([k, f]) => el("span", { class: `facet ${FACET_STATE[f.estado] ? f.estado : ""}`,
                                            title: (f.vizinhos || []).join("; ") || null },
          `${FACETS[k] || k}: ${FACET_STATE[f.estado] || f.estado}`))));
    }
    if (neighbors.length || unverified.length) {
      body.append(el("h3", {}, "Prior art"), ...neighbors.map(([layer, list]) => neighborLine(layer, list)));
      if (unverified.length) body.append(el("div", { class: "critique muted" }, `não verificado: ${unverified.join("; ")}`));
    }
    if (critiques.length) {
      body.append(el("h3", {}, `Críticas por papel${nasss}`), ...critiques.map((r) => el("div", { class: "critique" },
        el("b", {}, `${ROLES[r.papel] || r.papel} · ${r.veredito}`),
        (r.kill_criteria || []).length ? ` — kill criteria: ${r.kill_criteria.join("; ")}` : "",
        r.o_que_mudaria ? el("div", { class: "muted" }, `o que mudaria o veredito: ${r.o_que_mudaria}`) : null)));
      if (idea.pre_mortem) body.append(el("div", { class: "why" }, el("b", {}, "Pré-mortem: "), idea.pre_mortem));
    }
    if (dz) {
      body.append(el("h3", {}, "Dossiê"), el("dl", {}, pairs([["Piloto de 90 dias", dz.piloto_90d],
        ["Plano de evidência", dz.plano_evidencia], ["Classe SaMD", SAMD[dz.classe_samd] || dz.classe_samd],
        ["Base legal LGPD", dz.base_legal_lgpd], ["Integração", dz.integracao_detalhe], ["Lean Canvas", dz.lean_canvas]])));
    }
    const extra = el("div", {});
    body.append(extra);
    box.addEventListener("toggle", async () => {   // the graph facts and the vote history come on demand
      if (!box.open || extra.dataset.loaded) return;
      extra.dataset.loaded = "1";
      let full;
      try { full = await api(`/api/ideas/${encodeURIComponent(idea.id)}`); } catch (e) {
        extra.append(el("p", { class: "error" }, `não consegui carregar as evidências (${e.message})`));
        return;
      }
      if (full.context.length) {
        extra.append(el("h3", {}, "Fatos do grafo que o gerador viu"),
          el("ul", { class: "claims" }, full.context.map((f) => el("li", {}, f))));
      } else {
        extra.append(el("p", { class: "muted" }, "Candidato de controle: gerado sem fatos do grafo."));
      }
      if (full.votes.length) {
        extra.append(el("h3", {}, "Decisões"), el("ul", { class: "claims" }, full.votes.map((v) => el("li", {},
          `${fmtDate(v.created_at)} · ${v.value} · ${v.channel}${v.note ? ` · ${v.note}` : ""}`))));
      }
    });
    return box;
  }

  function ideaVotes(idea, badge) {
    const box = el("div", { class: "idea-votes", role: "group", "aria-label": "Decidir sobre esta ideia" });
    const reasons = el("div", { class: "reasons" });
    reasons.hidden = true;
    const buttons = [];
    const mark = (status) => buttons.forEach(([wanted, button]) => button.setAttribute("aria-pressed", String(wanted === status)));

    async function send(value, note) {
      try {
        const res = await api("/api/ideas/vote", { method: "POST", headers: { "content-type": "application/json" },
                                                   body: JSON.stringify({ idea_id: idea.id, value, note: note || null }) });
        idea.status = res.status;
        badge.className = `badge st-${res.status}`;
        badge.textContent = IDEA_STATUS[res.status] || res.status;
        mark(res.status);
        reasons.hidden = true;
      } catch (e) {
        box.append(el("span", { class: "error" }, ` erro ao votar (${e.message})`));
      }
    }

    for (const [value, label, status] of IDEA_VOTES) {
      const button = el("button", { class: "vote", type: "button", "aria-pressed": String(idea.status === status),
        onclick: () => { if (value === "down") reasons.hidden = !reasons.hidden; else send(value); } }, label);
      buttons.push([status, button]);
      box.append(button);
    }
    reasons.append(el("span", { class: "muted" }, "por quê?"),
      ...ideasState.reasons.map((r) => el("button", { class: "chip", type: "button", onclick: () => send("down", r) }, r)),
      el("button", { class: "chip", type: "button", onclick: () => send("down", null) }, "sem motivo"));
    return [box, reasons];
  }

  // --- trends (P4) -------------------------------------------------------------------
  const GAPS = [["recent_technique", "Técnicas recentes sem ligação com problemas frequentes"],
                ["community_bridge", "Pontes entre comunidades que quase não se tocam"],
                ["serendipity", "Serendipidade: pares distantes"]];

  function gapRows(list) {   // one row per technique: technique × every problem it never met
    const byTechnique = new Map();
    for (const g of list) {
      if (!byTechnique.has(g.technique_id)) byTechnique.set(g.technique_id, { first: g, problems: [] });
      byTechnique.get(g.technique_id).problems.push(g);
    }
    return [...byTechnique.values()].map(({ first, problems }) => el("div", { class: "row", title: first.why_now || null },
      entityLink(first.technique_id, first.technique, first.technique_type || "technique"),
      el("span", { class: "pair-to" }, el("span", { class: "muted" }, "×"),
        ...problems.map((p) => entityLink(p.problem_id, p.problem, "problem")))));
  }

  async function loadTrends() {
    let d;
    try { d = await api("/api/trends"); } catch (e) {
      $("#trends-meta").textContent = `Não consegui carregar as tendências (${e.message}).`;
      return;
    }
    const w = d.weekly;
    $("#trends-meta").textContent = w
      ? `Último relatório semanal: ${fmtDate(w.day)} · ${w.ideas} ideias · US$ ${num((w.stats || {}).cost_usd || 0, 3)}. `
        + "Tendências e lacunas são recalculadas agora; os rótulos do mapa vêm do último run semanal."
      : "Ainda sem relatório semanal (sotawhat run weekly, domingo às 20:00). Tudo abaixo foi calculado agora.";
    const trends = d.trends.map((t) => el("div", { class: "row" }, entityLink(t.entity_id, t.name, t.type),
      el("span", { class: "muted grow" }, `${t.recent} na semana · ${t.baseline} antes`),
      t.new ? el("span", { class: "badge main" }, "novo")
        : el("span", { class: "muted", title: "z de Poisson contra as 4 semanas anteriores" }, `z ${num(t.z, 1)}`)));
    $("#trends-list").replaceChildren(...(trends.length ? trends
      : [el("p", { class: "muted" }, "Nada subiu nesta semana: uma entidade precisa de 2 itens aprovados ou mais.")]));
    const communities = d.communities.map((c) => el("div", { class: "community" },
      el("b", {}, c.label), el("span", { class: "muted" }, ` · ${c.size} entidades`), c.summary ? el("p", {}, c.summary) : null,
      el("div", { class: "chips" }, c.members.map((m) => entityLink(m.entity_id, m.name, m.type)))));
    $("#communities-list").replaceChildren(...(communities.length ? communities
      : [el("p", { class: "muted" }, "Comunidades aparecem quando o grafo tem conexões suficientes (3 entidades ou mais por grupo).")]));
    const groups = GAPS.filter(([key]) => (d.gaps[key] || []).length).map(([key, title]) => el("div", { class: "gap-group" },
      el("h3", {}, title), gapRows(d.gaps[key])));
    $("#gaps-list").replaceChildren(...(groups.length ? groups
      : [el("p", { class: "muted" }, "Sem lacunas: faltam técnicas ou problemas na janela de 90 dias.")]));
    $("#rules-box").hidden = !(d.rules || []).length;
    $("#rules-list").replaceChildren(...(d.rules || []).map((r) => el("li", {}, r)));
  }

  // --- start -----------------------------------------------------------------------
  function init() {
    loadFilters();
    buildFilters();
    wireSearch();
    $("#unfocus").addEventListener("click", () => { state.focus = null; loadGraph(); });
    let resizeTimer = null;
    window.addEventListener("resize", () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => { if (renderer) { renderer.resize(); renderer.refresh(); } }, 150);
    });
    const scheme = window.matchMedia("(prefers-color-scheme: dark)");
    scheme.addEventListener("change", () => {
      if (!renderer) return;
      renderer.setSetting("labelColor", { color: css("--fg") });
      renderer.setSetting("defaultEdgeColor", css("--edge"));
      renderer.refresh();
    });
    document.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape" && state.selected && renderer) { state.selected = null; renderer.refresh({ skipIndexation: true }); }
    });
    const all = $("#ideas-all");
    all.addEventListener("change", () => { ideasState.all = all.checked; loadIdeas(); });
    window.addEventListener("hashchange", route);
    loadStats();
    route();
  }

  init();
})();
