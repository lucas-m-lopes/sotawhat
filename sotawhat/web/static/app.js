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
  const VIEWS = { graph: "#view-graph", today: "#view-today", ideas: "#view-ideas", trends: "#view-trends",
                  lessons: "#view-lessons", tools: "#view-tools" };
  const HASHES = { "#grafo": "graph", "#hoje": "today", "#ideias": "ideas", "#tendencias": "trends", "#aulas": "lessons",
                   "#ferramentas": "tools" };
  const TITLES = { graph: "sotawhat · grafo", today: "sotawhat · hoje", ideas: "sotawhat · ideias",
                   trends: "sotawhat · tendências", lessons: "sotawhat · aulas",
                   tools: "sotawhat · ferramentas" };
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
    else if (name === "today") loadToday();
    else if (name === "ideas") loadIdeas();
    else if (name === "lessons") loadLessons();
    else if (name === "tools") loadTools();
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
      el("dl", {}, pairs([["Problema", d.problema_jtbd], ["Dono", d.stakeholder_dono], ["Como funciona", d.mecanismo], ["Por que agora", d.why_now], ["Hipótese nula", d.hipotese_nula],
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

  // --- tools radar (2026-11-10) -----------------------------------------------------
  const TOOL_VOTES = [["test", "🧪 testar"], ["up", "👍"], ["down", "👎"], ["archive", "🗄️ depois"]];
  const int = (n) => (n === null || n === undefined ? "–" : Number(n).toLocaleString("pt-BR"));

  function sparkline(history) {   // the stars of the last 30 days
    if (!history || history.length < 2) return null;
    const values = history.map((h) => h[1]);
    const lo = Math.min(...values);
    const hi = Math.max(...values);
    const w = 120;
    const h = 28;
    const y = (v) => (hi === lo ? h / 2 : h - 2 - ((v - lo) * (h - 4)) / (hi - lo));
    const ns = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(ns, "svg");
    for (const [k, v] of [["viewBox", `0 0 ${w} ${h}`], ["width", w], ["height", h], ["class", "spark"], ["role", "img"],
                          ["aria-label", `estrelas: ${int(values[0])} → ${int(values[values.length - 1])} em ${history.length} dias`]]) {
      svg.setAttribute(k, String(v));
    }
    const line = document.createElementNS(ns, "polyline");
    line.setAttribute("points", values.map((v, i) => `${((i * w) / (values.length - 1)).toFixed(1)},${y(v).toFixed(1)}`).join(" "));
    line.setAttribute("fill", "none");
    line.setAttribute("stroke", "currentColor");
    line.setAttribute("stroke-width", "1.5");
    svg.append(line);
    return svg;
  }

  function toolSignal(p) {
    const parts = [`★ ${int(p.stars)}`];
    if (p.week !== null && p.week !== undefined) parts.push(`+${int(p.week)} na semana${p.estimated ? " (estimativa)" : ""}`);
    if (p.downloads !== null && p.downloads !== undefined) parts.push(`${int(p.downloads)} downloads na semana`);
    if (p.hn_points) parts.push(`HN ${p.hn_points} pts`);
    return parts.join(" · ");
  }

  function toolVoteButtons(p) {
    const box = el("div", { class: "votes", role: "group", "aria-label": `Votar em ${p.name}` });
    for (const [value, label] of TOOL_VOTES) {
      box.append(el("button", { class: "vote", type: "button", title: label, "aria-pressed": String(p.vote === value),
                                onclick: async () => {
        try {
          const res = await api("/api/radar/vote", { method: "POST", headers: { "content-type": "application/json" },
                                                     body: JSON.stringify({ repo: p.name, value }) });
          box.querySelectorAll("button").forEach((b, i) => b.setAttribute("aria-pressed", String(TOOL_VOTES[i][0] === res.vote)));
        } catch (e) {
          box.append(el("span", { class: "error" }, " erro ao votar"));
        }
      } }, label));
    }
    return box;
  }

  function toolCard(p) {
    const url = safeUrl(p.url);
    return el("div", { class: "item" },
      el("div", { class: "head" }, el("span", { class: "badge" }, p.front_label),
        el("span", { class: "meta" }, `relevância ${p.relevance}/5 · ${p.kind} · ${p.license || "licença ?"}`)),
      el("div", { class: "tool-title" },
        url ? el("a", { href: url, target: "_blank", rel: "noopener noreferrer" }, `${p.rank}. ${p.name}`) : el("b", {}, p.name),
        sparkline(p.history)),
      el("p", { class: "meta" }, toolSignal(p)),
      el("p", {}, p.what),
      p.why ? el("div", { class: "why" }, el("b", {}, "Por que serve: "), p.why) : null,
      (p.risks || []).length ? el("p", { class: "muted" }, `Riscos: ${p.risks.join("; ")}`) : null,
      el("p", { class: "muted" }, p.test_from ? `Testar a partir de ${fmtDate(p.test_from)} (release de ${fmtDate(p.release_at)})`
        : "Sem release: fixe um commit com mais de 2 semanas"),
      toolVoteButtons(p));
  }

  async function loadTools() {
    let d;
    try { d = await api("/api/radar"); } catch (e) {
      $("#tools-meta").textContent = `Não consegui carregar o radar (${e.message}).`;
      return;
    }
    const scan = d.scanned_at ? `varrido em ${fmtDate(d.scanned_at)}` : "ainda não varrido (sotawhat radar scan)";
    $("#tools-meta").textContent = d.day
      ? `Radar de ${fmtDate(d.day)} · ${d.picks.length} ferramentas · ${int(d.tracked)} repositórios acompanhados · `
        + `${d.days} dias de retrato · ${scan}.`
      : `Ainda sem relatório do radar (sotawhat run weekly, domingo; ou sotawhat radar report) · `
        + `${int(d.tracked)} repositórios acompanhados · ${scan}.`;
    $("#tools-list").replaceChildren(...(d.picks.length ? d.picks.map(toolCard)
      : [el("p", { class: "muted" }, "Nenhuma ferramenta no radar ainda.")]));
  }

  // --- today (P6) --------------------------------------------------------------------
  const TODAY_SECTIONS = [["main", "IA ∩ Saúde"], ["frontier", "Fronteira de IA"], ["radar", "Radar"]];
  const RUN_KINDS = { daily: "diário", weekly: "semanal", ideate: "ideação", eval: "avaliação", graph: "grafo" };

  function todayCard(item) {
    const url = safeUrl(item.url);
    return el("div", { class: "item" },
      el("div", { class: "head" }, sectionBadge(item),
        el("span", { class: "meta" }, `${item.total !== null && item.total !== undefined ? `nota ${num(item.total)} · ` : ""}`
          + `${item.source}`,
          url ? el("a", { href: url, target: "_blank", rel: "noopener noreferrer", title: "abrir a fonte" }, " ↗") : null)),
      el("button", { class: "title", type: "button", title: "abrir no grafo",
                     onclick: () => { toGraph(); ensureGraph(); openItem(item.id); } }, item.title),
      item.summary_pt ? el("p", {}, item.summary_pt) : null,
      item.why_it_matters_pt ? el("div", { class: "why" }, el("b", {}, "Por que importa: "), item.why_it_matters_pt) : null,
      voteButtons(item.id, item.vote));
  }

  async function loadToday() {
    let d;
    let recent = [];
    try {
      [d, recent] = await Promise.all([api("/api/today"), api("/api/runs?limit=12")]);
    } catch (e) {
      $("#today-meta").textContent = `Não consegui carregar o digest (${e.message}).`;
      return;
    }
    const run = d.run;
    if (!run) {
      $("#today-meta").textContent = "Ainda não houve run diário (sotawhat run daily, todo dia às 07:00).";
      $("#today-list").replaceChildren();
    } else {
      $("#today-meta").textContent = `run diário de ${fmtDate(run.finished_at)}`
        + (run.collected !== undefined && run.collected !== null ? ` · ${run.collected} coletados, ${run.new ?? 0} novos` : "")
        + ` · US$ ${num(run.cost_usd || 0, 3)}` + (run.ok ? "" : ` · falhou: ${run.error || "?"}`)
        + (run.latest_id && run.latest_id !== run.id ? ` · o run diário mais recente (#${run.latest_id}) não teve digest` : "");
      const blocks = [];
      for (const [key, title] of TODAY_SECTIONS) {
        const items = d.sections[key] || [];
        if (!items.length) continue;
        blocks.push(el("h2", { class: "today-section" }, `${title} · ${items.length}`), ...items.map(todayCard));
      }
      $("#today-list").replaceChildren(...(blocks.length ? blocks
        : [el("p", { class: "empty-note" }, "Nada relevante no último digest.")]));
    }
    $("#runs-list").replaceChildren(...recent.map((r) => el("div", { class: `row${r.ok === false ? " fail" : ""}` },
      el("span", {}, `${RUN_KINDS[r.kind] || r.kind} #${r.id}`),
      el("span", { class: "muted grow" }, `${fmtDate(r.started_at)}${r.seconds !== null ? ` · ${Math.round(r.seconds / 60)} min` : " · rodando"}`),
      el("span", { class: "muted" }, `US$ ${num(r.cost_usd || 0, 3)}`),
      r.ok === false ? el("span", { title: r.error }, "falhou") : el("span", {}, r.ok ? "ok" : "…"))));
  }

  // --- lessons (aulas 3D) -------------------------------------------------------------
  const LESSON_STATUS = { nova: "nova", planejada: "roteiro pronto", narrada: "narrada", renderizada: "renderizada",
                          pronta: "pronta", entregue: "entregue", falhou: "parou" };
  const REVIEW = { ok: "✅ sem erros", erro: "⚠️ tem erro" };
  const COMPARISON = { melhor: "🏆 melhor que o NotebookLM", empate: "🤝 empate com o NotebookLM", pior: "📉 pior que o NotebookLM" };
  const CHECKLIST = ["Toda afirmação é rastreável e não é mais forte que a fonte", "Anatomia/orientação/rótulos corretos",
    "Molécula, alvo e simplificações declaradas", "Ordem causal dos passos correta", "Números, unidades e escalas corretos",
    "Status regulatório e off-label sinalizados", "Conteúdo de IA bate com os artigos; metáforas rotuladas",
    "Nenhum dado de paciente", "Licenças e créditos em ordem", "Uso de IA declarado", "Template pedagógico seguido",
    "Legendas legíveis e paleta segura"];
  const clock = (s) => `${Math.floor((s || 0) / 60)}:${String(Math.round((s || 0) % 60)).padStart(2, "0")}`;

  function lessonCard(lesson) {
    const [r0, r1] = lesson.quiz_score || [[0, 0], [0, 0]];
    const card = el("article", { class: "idea lesson" },
      el("div", { class: "head" }, el("span", { class: "badge" }, LESSON_STATUS[lesson.status] || lesson.status),
        meta(`aula #${lesson.id}`, fmtDate(lesson.created_at), lesson.duration_s ? clock(lesson.duration_s) : null,
             lesson.cost_usd !== null ? `US$ ${num(lesson.cost_usd, 3)}` + (lesson.cost_brl != null ? ` · R$ ${num(lesson.cost_brl, 2)}` : "") : null,
             lesson.voice,
             r0[1] ? `quiz ${r0[0]}/${r0[1]}` : null, r1[1] ? `re-quiz ${r1[0]}/${r1[1]}` : null,
             REVIEW[lesson.review], COMPARISON[lesson.comparison])),
      el("h2", {}, lesson.title),
      lesson.objective ? el("p", {}, lesson.objective) : null,
      lesson.error ? el("p", { class: "muted" }, `parou: ${lesson.error} — retome com sotawhat lessons resume ${lesson.id}`) : null,
      lesson.video ? el("video", { controls: true, preload: "metadata", src: lesson.video, class: "lesson-video" }) : null,
      lesson.scenes3d.length ? el("div", { class: "chips" }, el("span", { class: "muted" }, "Cenas 3D interativas: "),
        ...lesson.scenes3d.map((s) => el("a", { class: "chip", href: s.url, target: "_blank", rel: "noopener" }, `${s.n}. ${s.title}`))) : null,
      lesson.sources_md ? el("p", { class: "muted" }, "Linha de base: suba ",
        el("a", { href: lesson.sources_md, target: "_blank", rel: "noopener" }, "fontes.md"),
        " no NotebookLM e gere um Video Overview (Explainer, pt-BR) para comparar.") : null);
    const more = el("details", {}, el("summary", {}, "roteiro, quiz, portões e checklist"));
    more.addEventListener("toggle", async () => {
      if (!more.open || more.dataset.loaded) return;
      more.dataset.loaded = "1";
      try { more.append(...lessonDetails(await api(`/api/lessons/${lesson.id}`))); }
      catch (e) { more.append(el("p", { class: "muted" }, `não carregou (${e.message})`)); }
    });
    card.append(more);
    return card;
  }

  function lessonDetails(d) {
    const plan = d.plan || { scenes: [], quiz: [] };
    const report = d.report || {};
    const gates = report.gates || {};
    const scenes = report.scenes || {};
    const out = [el("h3", {}, "Roteiro"), el("ol", {}, plan.scenes.map((s, i) => {
      const r = scenes[String(i + 1)] || {};
      const status = r.fallback ? " · virou slide" : r.attempts ? ` · ${r.attempts} tentativa(s)` : "";
      const kind = s.template || (s.mode === "three" ? "3D" : "2D");
      return el("li", {}, el("b", {}, `${s.title} `), el("span", { class: "muted" }, `(${kind}${status})`),
                el("ul", {}, s.beats.map((b) => el("li", {}, b.narration, b.source >= 0 ? el("sup", {}, ` [${b.source}]`) : null))));
    }))];
    out.push(el("h3", {}, "Quiz"), el("ol", {}, plan.quiz.map((q) => el("li", {}, q.question,
      el("details", {}, el("summary", {}, "resposta"), el("p", {}, `${"ABCD"[q.answer]}) ${q.options[q.answer]} — ${q.explanation}`))))));
    const after = gates.G1_after || gates.G1_first || [];
    if (report.engine === "hyperframes") {        // the HyperFrames engine: gates, the check and what the lesson cost
      const check = report.check || {}, voice = report.voice || {}, ptax = report.ptax;
      out.push(el("h3", {}, "Portões automáticos"), el("ul", {},
        el("li", {}, `G1 fatos: ${(gates.G1_first || []).length} problema(s) na 1ª checagem, ${after.length} depois da revisão`),
        ...after.map((p) => el("li", { class: "muted" }, p)),
        el("li", {}, `G2 roteiro: ${(gates.G2 || []).length ? gates.G2.join("; ") : "ok"}`),
        el("li", {}, `hyperframes check: ${(check.errors || []).length} erro(s), ${(check.warnings || []).length} aviso(s)`)));
      if (report.cost_usd != null) out.push(el("h3", {}, "Custo"), el("ul", {},
        el("li", {}, `LLM: US$ ${num(report.llm_usd || 0, 3)}`),
        el("li", {}, `voz: ${voice.credits || 0} créditos ElevenLabs = US$ ${num(voice.usd || 0, 3)}` +
          (voice.plan ? ` (US$ ${num(voice.plan[0], 2)} por ${voice.plan[1]} créditos do plano)` : "")),
        el("li", {}, `total: US$ ${num(report.cost_usd, 3)}` +
          (report.cost_brl != null && ptax ? ` = R$ ${num(report.cost_brl, 2)} (PTAX de ${fmtDate(ptax.day)}: R$ ${num(ptax.brl, 4)})` : ""))));
      out.push(el("h3", {}, "Checklist da sua revisão (G8)"), el("ol", {}, CHECKLIST.map((c) => el("li", {}, c))));
      if (d.sources && d.sources.length) out.push(el("h3", {}, "Fontes"), el("ol", { start: 0 }, d.sources.map((s) => {
        const url = safeUrl(s.url);
        return el("li", {}, url ? el("a", { href: url, target: "_blank", rel: "noopener noreferrer" }, s.title) : s.title, ` (${s.published})`);
      })));
      return out;
    }
    const visual = Object.values(scenes).flatMap((s) => (s.visual || []).flatMap((r) => r.defects || []));
    const serious = visual.filter((d) => d.severity === "grave");
    const fixed = Object.values(scenes).reduce((n, s) => n + (s.visual_fixes || 0), 0);
    out.push(el("h3", {}, "Portões automáticos"), el("ul", {},
      el("li", {}, `G1 fatos: ${(gates.G1_first || []).length} problema(s) na 1ª checagem, ${after.length} depois da revisão`),
      ...after.map((p) => el("li", { class: "muted" }, p)),
      el("li", {}, `G2 roteiro: ${(gates.G2 || []).length ? gates.G2.join("; ") : "ok"}`),
      el("li", {}, `G3 render e layout: cenas na 1ª tentativa ${report.first_try ?? "?"} de ${plan.scenes.length}; slides de reserva: ${report.fallbacks ?? 0}`),
      el("li", {}, `G4 revisão visual: ${serious.length} defeito(s) grave(s) e ${visual.length - serious.length} leve(s) vistos nos quadros; ${fixed} correção(ões) feitas com as imagens`),
      ...serious.slice(0, 8).map((d) => el("li", { class: "muted" }, `${d.kind}: ${d.where} → ${d.fix}`))));
    out.push(el("h3", {}, "Checklist da sua revisão (G8)"), el("ol", {}, CHECKLIST.map((c) => el("li", {}, c))));
    if (d.sources && d.sources.length) out.push(el("h3", {}, "Fontes"), el("ol", { start: 0 }, d.sources.map((s) => {
      const url = safeUrl(s.url);
      return el("li", {}, url ? el("a", { href: url, target: "_blank", rel: "noopener noreferrer" }, s.title) : s.title, ` (${s.published})`);
    })));
    return out;
  }

  async function loadLessons() {
    let lessons;
    try { lessons = await api("/api/lessons"); }
    catch (e) { $("#lessons-meta").textContent = `Não consegui carregar as aulas (${e.message}).`; return; }
    $("#lessons-meta").textContent = lessons.length
      ? `${lessons.length} aula(s) · vídeo narrado com cenas 3D, quiz no Telegram e re-quiz em 2 dias`
      : "Nenhuma aula ainda: sotawhat lessons make --tema \"…\" (ou --auto, a tendência mais forte da semana).";
    $("#lessons-list").replaceChildren(...lessons.map(lessonCard));
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
