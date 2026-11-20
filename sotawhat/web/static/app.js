// sotawhat/web/static/app.js — the graph interface (SDD §6.11). Vanilla JS over the local API;
// graphology + graphology-library (Louvain) from /static/vendor, and the 3D graph of graph3d.js (three.js).
// Three views behind the header tabs (#grafo, #ideias, #tendencias); the ideas and trends pages are P4.
// Every piece of data goes into the page through textContent, never as HTML.
"use strict";
(() => {
  const TYPES = {
    technique: { label: "técnica", color: "#4DA3FF" },        // light sources on a dark scene: saturated and bright
    model: { label: "modelo", color: "#B58CFF" },
    dataset: { label: "dataset", color: "#2EE6C8" },
    organization: { label: "organização", color: "#FFB454" },
    product: { label: "produto", color: "#7CF07C" },
    problem: { label: "problema", color: "#FF6B88" },
    regulation: { label: "regulação", color: "#E8C39A" },
  };
  const CATEGORIES = { domain: "domínio", problem_type: "tipo de problema", technique_family: "família de técnica" };
  const CATEGORY_COLOR = "#9AA7BD";
  const COMMUNITY_COLORS = ["#4DA3FF", "#FFB454", "#7CF07C", "#FF6B88", "#2EE6C8", "#B58CFF", "#FFE066", "#FF9AD5",
                            "#E8C39A", "#8FD3FF", "#5EE6FF", "#FF8A5B"];
  const DAYS = [[7, "7 dias"], [30, "30 dias"], [90, "90 dias"], [365, "1 ano"], [0, "tudo"]];
  const COLOR_BY = [["type", "tipo"], ["community", "comunidade"]];
  const DIMS = [[3, "3D"], [2, "2D"]];
  const VOTES = [["up", "👍", "relevante"], ["down", "👎", "não relevante"], ["test", "🧪", "quero testar"]];
  const ROLE = { main: "principal", used: "usado", mentioned: "citado", tag: "categoria" };

  const state = { days: 30, types: new Set(Object.keys(TYPES)), categories: false, min: 1, limit: 250,
                  colorBy: "type", dims: 3, focus: null, selected: null, hovered: null, data: null, stats: null, view: null };
  let scene3d = null;         // Graph3D of graph3d.js
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

  const typeColor = (type) => (TYPES[type] || {}).color || CATEGORY_COLOR;
  const typeLabel = (type) => (TYPES[type] || {}).label || CATEGORIES[type] || type;
  const safeUrl = (url) => (/^https?:\/\//i.test(url || "") ? url : null);

  function fmtDate(iso) {
    if (!iso) return "?";
    // a date without time ("2026-11-24") is a calendar day: read as UTC midnight it showed the day before in Brazil
    const day = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso));
    if (day) return `${day[3]}/${day[2]}/${day[1].slice(2)}`;
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
        categories: state.categories, min: state.min, limit: state.limit, colorBy: state.colorBy, dims: state.dims }));
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
      if (saved.dims === 2) state.dims = 2;
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
    segmented($("#dims"), DIMS, state.dims, (value) => {       // the same scene, flattened or in volume: no reload
      state.dims = value; saveFilters(); if (scene3d) scene3d.setFlat(value === 2);
    });
    segmented($("#color-by"), COLOR_BY, state.colorBy, (value) => {
      state.colorBy = value; saveFilters(); paint();
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

  // --- graph (3D, graph3d.js) ------------------------------------------------------
  let engine = null;          // the graph3d.js module: three.js is only loaded when the graph is first drawn

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
    await draw(state.data);
  }

  function nodeColor(attrs) {
    if (state.colorBy === "community" && attrs.community !== undefined) {
      return COMMUNITY_COLORS[attrs.community % COMMUNITY_COLORS.length];
    }
    return typeColor(attrs.kind);
  }

  function paint() {          // colors and the lit neighborhood, after the hover, the selection or "Cores" change
    if (!scene3d || !graph) return;
    scene3d.setColors(graph.mapNodes((node, attrs) => nodeColor(attrs)));
    scene3d.setActive(state.hovered || state.selected);
  }

  async function draw(data) {
    graph = new graphology.Graph({ type: "undirected", multi: false, allowSelfLoops: false });
    for (const node of data.nodes) {
      graph.addNode(node.id, { label: node.label, kind: node.type, entity: node,
                               size: Math.min(1 + 0.6 * Math.sqrt(node.count || 1), 5.5) });
    }
    for (const edge of data.edges) {
      if (!graph.hasNode(edge.source) || !graph.hasNode(edge.target) || graph.hasEdge(edge.source, edge.target)) continue;
      graph.addEdgeWithKey(edge.id, edge.source, edge.target, { kind: edge.kind, label: edge.label, weight: edge.weight });
    }
    if (graph.order > 1) {
      try {
        graphologyLibrary.communitiesLouvain.assign(graph, { rng: seededRandom(42) });
      } catch (e) { /* no edges at all: no communities */ }
    }
    if (state.selected && !graph.hasNode(state.selected)) state.selected = null;
    state.hovered = null;
    if (!engine) {
      try { engine = await import("/static/graph3d.js"); } catch (e) {
        setStatus("");
        showOverlay(`Não consegui carregar o grafo 3D (${e.message}).`);
        return;
      }
    }
    if (!scene3d) {
      if (!engine.supported()) {
        setStatus("");
        showOverlay("Este navegador está sem WebGL 2, e o grafo 3D precisa dele. As outras abas funcionam.");
        return;
      }
      scene3d = new engine.Graph3D($("#graph"), {
        onHover: (node) => { state.hovered = node; paint(); },
        onSelect: (node) => selectNode(node),
        onFocus: (node) => focusOn(node),
        onClear: () => { state.selected = null; paint(); },
      }, { flat: state.dims === 2 });
    }
    scene3d.setData(
      graph.mapNodes((node, attrs) => ({ id: node, label: attrs.label, size: attrs.size, color: nodeColor(attrs) })),
      graph.mapEdges((edge, attrs, source, target) => ({ source, target, typed: attrs.kind !== "co", weight: attrs.weight })));
    paint();
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

  function selectInGraph(node) {   // light a node and bring it to the center, when the current graph has it
    if (!scene3d || !graph || !graph.hasNode(node)) return;
    state.selected = node;
    state.hovered = null;
    paint();
    scene3d.flyTo(node);
  }

  function selectNode(node, open = true) {
    selectInGraph(node);
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
    history.push(() => { selectInGraph(`e${entityId}`); openEntity(entityId); });   // "← voltar" moves the graph too
    const arrow = { out: (label) => `${label} →`, in: (label) => `← ${label}`, both: (label) => `${label} ↔` };
    const relations = d.relations.map((r) => el("div", { class: "rel" },
      el("span", { class: "muted" }, (arrow[r.direction] || arrow.out)(r.label)),
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
                  lessons: "#view-lessons", tools: "#view-tools", glossary: "#view-glossary", ask: "#view-ask" };
  const HASHES = { "#grafo": "graph", "#hoje": "today", "#ideias": "ideas", "#tendencias": "trends", "#aulas": "lessons",
                   "#ferramentas": "tools", "#glossario": "glossary", "#perguntar": "ask" };
  const TITLE = "SOTA What";      // the browser tab keeps the name of the product, whichever view is open
  let graphLoaded = false;

  function showView(name) {
    for (const [key, selector] of Object.entries(VIEWS)) $(selector).hidden = key !== name;
    document.querySelectorAll(".views a").forEach((a) => {
      if (a.dataset.view === name) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
    });
    document.title = TITLE;
    state.view = name;
  }

  function ensureGraph() {   // the graph loads the first time its tab is shown
    if (!graphLoaded) loadGraph();
    else if (scene3d) scene3d.resize();
  }

  function route() {
    const name = HASHES[location.hash] || "graph";
    showView(name);
    if (name === "graph") ensureGraph();
    else if (name === "today") loadToday();
    else if (name === "ideas") loadIdeas();
    else if (name === "lessons") loadLessons();
    else if (name === "tools") loadTools();
    else if (name === "glossary") loadGlossary();
    else if (name === "ask") loadAsk();
    else loadTrends();
  }

  function toGraph() {       // before opening an entity or an item from another tab
    if (state.view === "graph") return;
    showView("graph");
    if (location.hash !== "#grafo") location.hash = "#grafo";
    if (scene3d) scene3d.resize();
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

  // --- questions to the graph (2026-11-20): hybrid retrieval, then who answers: the local SLM, Jev or nobody ---
  const ASK_DAYS = [[0, "automático"], [7, "7 dias"], [30, "30 dias"], [90, "90 dias"]];
  const ASK_EXAMPLES = ["O que saiu esta semana sobre agentes clínicos?", "Quais modelos abordam sepse e quem os desenvolveu?",
                        "Quais as organizações mais citadas este mês?", "O que é RAG e em que itens apareceu?",
                        "O que está em alta no grafo?"];
  const RANKINGS = { dense: "sentido", bm25: "palavras", graph: "grafo", mention: "menção", relation: "relação",
                     category: "categoria" };
  // Who answers. "sources" is nobody: the request goes with sources_only and brings the ranked sources alone.
  const ANSWERERS = [["slm", "modelo local"], ["jev", "Jev"], ["sources", "só as fontes"]];
  const WAITING = { slm: "buscando no grafo e perguntando ao modelo local…", jev: "buscando no grafo e julgando as fontes com a Jev…",
                    sources: "buscando no grafo…" };
  // engine: null until the server says its default; status: the last /api/rag/status
  const askState = { days: 0, busy: false, engine: null, status: null };

  function answerNodes(text, card) {   // the answer as text nodes, with each [n] as a button that shows its source
    const nodes = [];
    // the model writes Markdown: bullets become "•" and the emphasis marks go, the rest is plain text
    const plain = text.replace(/\*\*/g, "").replace(/^[ \t]*[*-][ \t]+/gm, "• ").replace(/\*([^*\n]+)\*/g, "$1");
    for (const part of plain.split(/(\[\d{1,2}\])/)) {
      const cite = /^\[(\d{1,2})\]$/.exec(part);
      if (!cite) { nodes.push(document.createTextNode(part)); continue; }
      nodes.push(el("button", { class: "cite", type: "button", title: "ver a fonte", onclick: () => {
        const target = card.querySelector(`[data-source="${cite[1]}"]`);
        if (target) { target.scrollIntoView({ block: "center", behavior: "smooth" }); target.classList.add("flash");
                      setTimeout(() => target.classList.remove("flash"), 1400); }
      } }, cite[1]));
    }
    return nodes;
  }

  function sourceCard(s, cited) {
    const url = safeUrl(s.url);
    const ranks = Object.entries(s.channels || {}).map(([name, rank]) => `${RANKINGS[name] || name} ${rank}º`).join(" · ");
    return el("div", { class: `item source${cited ? " cited" : ""}`, "data-source": s.n },
      el("div", { class: "head" },
        el("span", {}, el("span", { class: "cite static" }, String(s.n)), " ", sectionBadge({ decision: s.section === "Radar"
          ? "radar" : s.section === "Fronteira de IA" ? "frontier" : "main", section: s.section })),
        el("span", { class: "meta" }, `${fmtDate(s.day)} · ${s.source}`,
          url ? el("a", { href: url, target: "_blank", rel: "noopener noreferrer", title: "abrir a fonte" }, "↗") : null)),
      el("button", { class: "title", type: "button", title: "abrir o item no grafo",
                     onclick: () => { toGraph(); ensureGraph(); openItem(s.item_id); } }, s.title),
      s.summary ? el("p", { class: "clamp" }, s.summary) : null,
      s.excerpt ? el("details", {}, el("summary", {}, "trecho do original"), el("p", { class: "muted" }, s.excerpt)) : null,
      ranks ? el("p", { class: "meta" }, `achado por: ${ranks}`) : null);
  }

  function askCard(d) {
    const card = el("article", { class: "idea answer" });
    const cited = new Set(d.cited || []);
    const t = d.timings || {};
    card.append(el("h2", {}, d.question));
    if (d.answer) card.append(el("div", { class: "answer-text" }, answerNodes(d.answer, card)));
    else if (d.error) card.append(el("p", { class: "muted" },
      `${d.engine === "jev" ? "A Jev" : "O modelo local"} não respondeu (${d.error}). As fontes encontradas estão abaixo.`));
    for (const w of d.warnings || []) card.append(el("p", { class: "warn" }, `⚠️ ${w}`));
    card.append(d.engine === "jev"
      ? meta(d.model ? `${d.model} · frases extraídas das fontes, nada foi redigido` : "sem a Jev: só a busca",
             `total ${num(t.total || 0, 1)} s`, d.model ? `Jev ${num(d.seconds || 0, 1)} s` : null, ...(d.notes || []))
      : meta(d.model ? `modelo ${d.model}` : "sem modelo: só a busca",
             `busca ${num(t.total || 0, 1)} s`, d.answer && d.model ? `resposta ${num(d.seconds || 0, 1)} s` : null,
             ...(d.notes || [])));
    if ((d.entities || []).length) card.append(el("div", { class: "chips" }, el("span", { class: "muted" }, "No grafo: "),
      d.entities.map((e) => entityLink(e.entity_id, e.name, e.type))));
    if ((d.facts || []).length) card.append(el("details", { open: !d.answer }, el("summary", {}, `fatos do grafo (${d.facts.length})`),
      el("div", { class: "facts" }, d.facts.join("\n"))));
    if ((d.sources || []).length) card.append(el("h3", {}, `Fontes (${d.sources.length})`),
      el("div", { class: "sources" }, d.sources.map((s) => sourceCard(s, cited.has(s.n)))));
    return card;
  }

  async function sendQuestion(question) {
    if (askState.busy || question.trim().length < 3) return;
    askState.busy = true;
    const button = $("#ask-send");
    const mode = askState.engine;
    const waiting = el("article", { class: "idea answer" }, el("h2", {}, question),
      el("p", { class: "muted" }, WAITING[mode] || WAITING.slm));
    $("#ask-thread").prepend(waiting);
    button.disabled = true;
    const body = { question, sources_only: mode === "sources" };
    if (askState.days) body.days = askState.days;
    if (mode && mode !== "sources") body.engine = mode;
    try {
      const d = await api("/api/ask", { method: "POST", headers: { "content-type": "application/json" },
                                        body: JSON.stringify(body) });
      waiting.replaceWith(askCard(d));
    } catch (e) {
      waiting.replaceWith(el("article", { class: "idea answer" }, el("h2", {}, question),
        el("p", { class: "error" }, `Não consegui responder (${e.message}).`)));
    }
    askState.busy = false;
    button.disabled = false;
    loadAsk();
  }

  function readout(label, value, note, state) {
    return el("div", { "data-state": state || null }, el("dt", {}, label), el("dd", {}, value, note ? el("small", {}, note) : null));
  }

  function drawAskMeta(error) {              // the state of the index, as three short readouts beside the heading
    const s = askState.status;
    const box = $("#ask-meta");
    if (error) { box.replaceChildren(readout("Índice", "sem leitura", error, "bad")); return; }
    if (!s) return;
    if (!s.items_indexed) {
      box.replaceChildren(readout("Índice", "vazio", "rode sotawhat rag index (minutos na primeira vez)", "bad"));
      return;
    }
    const count = (n) => Number(n || 0).toLocaleString("pt-BR");
    const behind = s.approved_items - s.items_indexed;
    const passages = Object.values(s.kinds || {}).reduce((sum, kind) => sum + (kind.passages || 0), 0);
    box.replaceChildren(
      readout("Itens no índice", `${count(s.items_indexed)} / ${count(s.approved_items)}`,
              behind > 0 ? `faltam ${behind}: rode sotawhat rag index` : null, behind > 0 ? "bad" : null),
      readout("Trechos", count(passages)),
      readout("Atualizado", fmtDate(s.indexed_at)));
  }

  function engineHint() {                    // -> [what the chosen option does, whether it is a problem]
    const s = askState.status || {};
    const mode = askState.engine || "slm";
    if (mode === "sources") return ["sem resposta redigida: só as fontes, em ordem de relevância · ~3 s", false];
    if (mode === "jev") {
      if (s.jev && !s.jev.ok) return ["sem a chave do OpenRouter: quem responde é o modelo local", true];
      const model = s.jev && s.jev.model ? s.jev.model.split("/").pop() : "Jev";
      const kept = s.jev && s.jev.zdr ? " (ZDR, sem retenção)" : "";
      return [`extrai frases das fontes, sem redigir · ~2 s · ${model} via OpenRouter${kept}`, false];
    }
    if (s.slm && !s.slm.ok) return [`fora do ar: ${s.slm.detail} · rode sotawhat rag up`, true];
    return [`redige a resposta com citações · ~12 s · ${s.slm && s.slm.model ? `${s.slm.model}, ` : ""}neste computador`, false];
  }

  function drawAskHints() {
    const [text, bad] = engineHint();
    const hint = $("#ask-engine-hint");
    hint.textContent = text;
    hint.classList.toggle("bad", bad);
    $("#ask-days-hint").textContent = askState.days ? `só itens dos últimos ${askState.days} dias`
      : "segue a pergunta (“esta semana”); sem período nela, todo o grafo";
  }

  async function loadAsk() {
    let s;
    try { s = await api("/api/rag/status"); } catch (e) { drawAskMeta(e.message); return; }
    askState.status = s;
    if (askState.engine === null && s.engine) {        // the first status after a question brings the server's default
      let saved = null;
      try { saved = localStorage.getItem("sotawhat.engine"); } catch (e) { /* private window */ }
      askState.engine = ANSWERERS.some(([value]) => value === saved) ? saved : s.engine;
      drawEngines();
    }
    drawAskMeta();
    drawAskHints();
  }

  function drawEngines() {
    segmented($("#ask-engine"), ANSWERERS, askState.engine || "slm", (value) => {
      askState.engine = value;
      try { localStorage.setItem("sotawhat.engine", value); } catch (e) { /* private window */ }
      drawAskHints();
    });
    drawAskHints();
  }

  function wireAsk() {
    try {
      const saved = localStorage.getItem("sotawhat.engine");
      if (ANSWERERS.some(([value]) => value === saved)) askState.engine = saved;
    } catch (e) { /* private window */ }
    segmented($("#ask-days"), ASK_DAYS, askState.days, (value) => { askState.days = value; drawAskHints(); });
    drawEngines();
    const input = $("#ask-input");
    const fit = () => {                      // the field grows with the question, up to the max-height of the style
      input.style.height = "auto";
      input.style.height = `${input.scrollHeight}px`;
    };
    input.addEventListener("input", fit);
    $("#ask-examples").replaceChildren(...ASK_EXAMPLES.map((text) =>
      el("button", { class: "chip", type: "button", onclick: () => { input.value = text; fit(); sendQuestion(text); } }, text)));
    $("#ask-form").addEventListener("submit", (ev) => {
      ev.preventDefault();
      const question = input.value.trim();
      if (question.length < 3) return;
      input.value = "";
      fit();
      sendQuestion(question);
    });
    input.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" && !ev.shiftKey) { ev.preventDefault(); $("#ask-form").requestSubmit(); }
    });
  }

  // --- glossary of the digests (2026-11-20) ----------------------------------------------
  const GLOSSARY_FILTERS = [["", "todos"], ["ativo", "nos digests"], ["conhecido", "já sei"]];
  const glossaryState = { status: "", text: "", loading: 0 };
  const initial = (term) => {
    const letter = term.normalize("NFKD").replace(/[\u0300-\u036f]/g, "").charAt(0).toUpperCase();
    return /[A-Z]/.test(letter) ? letter : "#";
  };

  function termCard(t) {
    const known = t.status === "conhecido";
    const card = el("article", { class: `term${known ? " known" : ""}`, id: `termo-${t.id}` });
    const toggle = el("button", { class: "chip", type: "button", "aria-pressed": String(known),
      title: known ? "voltar a mostrar este termo nos digests" : "não mostrar mais este termo nos digests",
      onclick: async () => {
        try {
          await api("/api/glossary/status", { method: "POST", headers: { "content-type": "application/json" },
                                              body: JSON.stringify({ term_id: t.id, status: known ? "ativo" : "conhecido" }) });
          loadGlossary();
        } catch (e) { toggle.after(el("span", { class: "error" }, " não salvou")); }
      } }, known ? "✓ já sei" : "já sei");
    const seen = [t.items ? `em ${t.items} ${t.items === 1 ? "item" : "itens"}` : "ainda em nenhum item",
                  t.last_seen ? `último em ${fmtDate(t.last_seen)}` : null,
                  t.shown_count ? `saiu em ${t.shown_count} ${t.shown_count === 1 ? "digest" : "digests"}` : null];
    card.append(
      el("div", { class: "term-head" },
        el("h2", {}, t.term, t.expansion ? el("span", { class: "expansion" }, ` ${t.expansion}`) : null), toggle),
      el("p", { class: "definition" }, t.definition),
      meta(...seen, t.aliases.length ? `também: ${t.aliases.join(", ")}` : null),
      el("div", { class: "chips" },
        t.entity_id ? el("button", { class: "chip", type: "button", title: "abrir esta técnica no grafo",
                                     onclick: () => openInGraph(t.entity_id) },
          el("span", { class: "dot", style: `background:${typeColor("technique")}` }), `no grafo: ${t.entity}`) : null,
        t.latest.map((item) => el("button", { class: "chip", type: "button", title: `${item.title} · abrir o item`,
          onclick: () => { toGraph(); ensureGraph(); openItem(item.id); } },
          item.title.length > 54 ? `${item.title.slice(0, 53)}…` : item.title))));
    return card;
  }

  async function loadGlossary() {
    const ticket = ++glossaryState.loading;
    const params = new URLSearchParams();
    if (glossaryState.text) params.set("q", glossaryState.text);
    if (glossaryState.status) params.set("status", glossaryState.status);
    let d;
    try { d = await api(`/api/glossary?${params}`); } catch (e) {
      $("#glossary-meta").textContent = `Não consegui carregar o glossário (${e.message}).`;
      return;
    }
    if (ticket !== glossaryState.loading) return;       // a newer keystroke already asked again
    const counts = d.counts || {};
    segmented($("#glossary-status"), GLOSSARY_FILTERS.map(([value, label]) =>
      [value, `${label} ${value ? counts[value] || 0 : d.total}`]), glossaryState.status,
      (value) => { glossaryState.status = value; loadGlossary(); });
    $("#glossary-meta").textContent = d.total
      ? `${d.total} termos de ML/IA que apareceram nos seus digests, uma frase cada · ${counts.conhecido || 0} marcados como já sei`
      : "Ainda vazio: o run diário define os termos de cada digest (ou rode sotawhat glossary backfill).";
    const list = $("#glossary-list");
    if (!d.terms.length) {
      $("#glossary-letters").replaceChildren();
      list.replaceChildren(el("p", { class: "empty-note" }, d.total ? "Nenhum termo com este filtro." : "Nenhum termo ainda."));
      return;
    }
    const blocks = [];
    const letters = [];
    for (const t of d.terms) {
      const letter = initial(t.term);
      if (letters[letters.length - 1] !== letter) {
        letters.push(letter);
        blocks.push(el("h3", { class: "letter", id: `letra-${letter === "#" ? "0" : letter}` }, letter));
      }
      blocks.push(termCard(t));
    }
    $("#glossary-letters").replaceChildren(...letters.map((letter) => el("button", { type: "button", class: "chip",
      onclick: () => document.getElementById(`letra-${letter === "#" ? "0" : letter}`).scrollIntoView({ block: "start" }) },
      letter)));
    list.replaceChildren(...blocks);
  }

  function wireGlossary() {
    let timer = null;
    $("#glossary-filter").addEventListener("input", (ev) => {
      clearTimeout(timer);
      timer = setTimeout(() => { glossaryState.text = ev.target.value.trim(); loadGlossary(); }, 200);
    });
  }

  // --- today (P6) --------------------------------------------------------------------
  const TODAY_SECTIONS = [["main", "IA ∩ Saúde"], ["frontier", "Fronteira de IA"], ["radar", "Radar"]];
  const RUN_KINDS = { daily: "diário", weekly: "semanal", ideate: "ideação", eval: "avaliação", graph: "grafo",
                      lesson: "aula", radar: "radar" };

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
  // F1 of 2026-11-20 (docs/superpowers/specs/2026-11-20-aulas-pela-interface-design.md): a lesson is planned, reviewed
  // and produced from here. Each step is a `sotawhat lessons` process the server starts; one runs at a time.
  const LESSON_STATUS = { nova: "sem roteiro", planejada: "roteiro pronto", narrada: "narrada", renderizada: "renderizada",
                          pronta: "pronta", entregue: "entregue", falhou: "parou", descartada: "descartada" };
  const REVIEW = { ok: "✅ sem erros", erro: "⚠️ tem erro" };
  const COMPARISON = { melhor: "🏆 melhor que o NotebookLM", empate: "🤝 empate com o NotebookLM", pior: "📉 pior que o NotebookLM" };
  const CHECKLIST = ["Toda afirmação é rastreável e não é mais forte que a fonte", "Anatomia/orientação/rótulos corretos",
    "Molécula, alvo e simplificações declaradas", "Ordem causal dos passos correta", "Números, unidades e escalas corretos",
    "Status regulatório e off-label sinalizados", "Conteúdo de IA bate com os artigos; metáforas rotuladas",
    "Nenhum dado de paciente", "Licenças e créditos em ordem", "Uso de IA declarado", "Template pedagógico seguido",
    "Legendas legíveis e paleta segura"];
  const STAGE_LABELS = { roteiro: "roteiro", storyboard: "storyboard", voz: "voz", "3d": "cenas 3D", checagem: "checagem",
                         video: "vídeo", envio: "envio" };
  const JOB_VERB = { roteiro: "planejando", aula: "produzindo", envio: "enviando" };
  const LESSON_MODES = [["economico", "econômico"], ["equilibrado", "equilibrado"]];
  const MODE_HINT = { economico: "DeepSeek V4.1 Flash escreve o roteiro · 2 a 4 min · US$ 0,01 a 0,02",
                      equilibrado: "Kimi K3.1 Pro escreve o roteiro, com teto de preço maior · custo ainda não medido" };
  const lessonsState = { state: null, lessons: [], entities: [], mode: "economico", send: true, poll: null, ticker: null,
                         logOpen: false, searchTimer: null };
  const clock = (s) => `${Math.floor((s || 0) / 60)}:${String(Math.round((s || 0) % 60)).padStart(2, "0")}`;
  const minutes = (s) => (s >= 90 ? `~${Math.round(s / 60)} min` : `~${Math.max(1, Math.round(s || 0))} s`);
  const thousands = (n) => Number(n || 0).toLocaleString("pt-BR");
  const modeLabel = (mode) => (LESSON_MODES.find(([value]) => value === mode) || [null, "econômico"])[1];

  async function postJSON(path, body) {     // every write: a JSON body (the server refuses forms); the error is its detail
    const response = await fetch(path, { method: "POST", headers: { "content-type": "application/json" },
                                         body: JSON.stringify(body || {}) });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `erro ${response.status}`);
    return data;
  }

  function liveJob() {
    const job = lessonsState.state && lessonsState.state.job;
    return job && job.alive ? job : null;
  }

  function jobLine(job) {
    const what = JOB_VERB[job.action] || job.action;
    const stage = job.stage ? ` · etapa ${STAGE_LABELS[job.stage] || job.stage}` : "";
    return `aula #${job.lesson_id} · ${what}${stage}`;
  }

  // a button that asks for a second click ("confirmar?") and goes back after 4 s: no browser dialog
  function confirmButton(label, armedLabel, run, cls = "btn") {
    const button = el("button", { class: cls, type: "button" }, label);
    let timer = null;
    button.addEventListener("click", () => {
      if (!button.classList.contains("armed")) {
        button.classList.add("armed");
        button.textContent = armedLabel;
        timer = setTimeout(() => { button.classList.remove("armed"); button.textContent = label; }, 4000);
        return;
      }
      clearTimeout(timer);
      run(button);
    });
    return button;
  }

  async function lessonAction(card, path, body) {
    card.querySelectorAll(".actions button").forEach((b) => { b.disabled = true; });
    const error = card.querySelector(".action-error");
    try {
      await postJSON(path, body);
      await loadLessons();
    } catch (e) {
      if (error) error.textContent = e.message;
      card.querySelectorAll(".actions button").forEach((b) => { b.disabled = false; });
    }
  }

  function lessonHead(lesson, badge, badgeClass, ...parts) {
    return el("div", { class: "head" }, el("span", { class: `badge ${badgeClass || ""}` }, badge),
      meta(`aula #${lesson.id}`, fmtDate(lesson.created_at), ...parts));
  }

  function logBlock(lesson, job) {
    const lines = (job && job.log) || [];
    const folder = String(lesson.id).padStart(3, "0");
    const block = el("details", { class: "log", open: lessonsState.logOpen && lines.length ? true : null },
      el("summary", {}, "log"),
      lines.length ? el("pre", {}, lines.join("\n")) : el("p", { class: "muted" }, "as últimas linhas aparecem aqui"),
      el("a", { href: `/lessons/${folder}/job.log`, target: "_blank", rel: "noopener" }, "log completo"));
    block.addEventListener("toggle", () => { lessonsState.logOpen = block.open; });
    return block;
  }

  // the steps of a running job: the ones done with their time, the current one counting, the next ones with their
  // estimate (the review's, measured on lessons 6 to 8)
  function progressBody(lesson, job) {
    const s = lessonsState.state || {};
    const planned = (lesson.estimate || {}).stages || {};
    const expected = (name) => (name === "roteiro" ? s.plan_s || 200 : planned[name] || 0);
    const now = Date.now();
    let left = 0;
    for (const step of job.stages || []) {
      if (step.state === "pendente") left += expected(step.name);
      if (step.state === "rodando") left += Math.max(0, expected(step.name) - (now - Date.parse(step.started_at)) / 1000);
    }
    const steps = (job.stages || []).map((step) => {
      const label = STAGE_LABELS[step.name] || step.name;
      if (step.state === "feita") return el("li", { class: "step done" }, el("b", {}, label), el("span", {}, clock(step.seconds)));
      if (step.state === "parou") return el("li", { class: "step stop" }, el("b", {}, label), el("span", {}, clock(step.seconds)));
      if (step.state === "rodando") {
        return el("li", { class: "step run", "aria-current": "step" }, el("b", {}, label),
          el("span", { "data-since": step.started_at, "data-of": expected(step.name) || "" }, "…"));
      }
      return el("li", { class: "step todo" }, el("b", {}, label), el("span", {}, expected(step.name) ? minutes(expected(step.name)) : "—"));
    });
    return el("div", { class: "job-live" },
      lessonHead(lesson, JOB_VERB[job.action] || "rodando", "", job.origin === "terminal" ? "iniciada no terminal" : null,
                 job.detached === false ? "morre se a interface reiniciar" : null),
      el("h2", {}, lesson.title),
      steps.length ? el("ol", { class: "stepper" }, steps) : el("p", { class: "muted" }, "iniciando o processo…"),
      el("p", { class: "muted small" }, "decorrido ", el("span", { "data-since": job.started_at }, clock(job.elapsed_s)),
        left > 0 ? ` · faltam ${minutes(left)}` : "", " · pode fechar a página: a aula continua"));
  }

  function progressCard(lesson, job) {
    const card = el("article", { class: "idea lesson working", "data-lesson": lesson.id }, progressBody(lesson, job));
    card.append(el("div", { class: "actions" },
      confirmButton("Cancelar", "Cancelar mesmo?", () => lessonAction(card, `/api/lessons/${lesson.id}/cancel`))),
      el("p", { class: "action-error" }), logBlock(lesson, job));
    return card;
  }

  // a poll redraws the steps and the log only: a "Cancelar" waiting for its second click must stay armed
  function refreshProgress(card, lesson, job) {
    card.querySelector(".job-live").replaceWith(progressBody(lesson, job));
    card.querySelector(".log").replaceWith(logBlock(lesson, job));
  }

  function planDetails(lesson, open) {
    const more = el("details", { open: open || null }, el("summary", {}, open ? "roteiro, quiz e checagem de fatos" : "roteiro, quiz, portões e checklist"));
    const fill = async () => {
      if (more.dataset.loaded) return;
      more.dataset.loaded = "1";
      try { more.append(...lessonDetails(await api(`/api/lessons/${lesson.id}`))); }
      catch (e) { more.append(el("p", { class: "muted" }, `não carregou (${e.message})`)); }
    };
    more.addEventListener("toggle", () => { if (more.open) fill(); });
    if (open) fill();
    return more;
  }

  // the review: the plan with the numbers of its production, before any credit of voice
  function reviewCard(lesson) {
    const s = lessonsState.state || {};
    const est = lesson.estimate || {};
    const credits = s.credits;
    const short = Boolean(credits && !lesson.voice_paid && credits.left < est.credits);
    const busy = liveJob();
    const card = el("article", { class: "idea lesson review", "data-lesson": lesson.id },
      lessonHead(lesson, "roteiro pronto", "", `modelos ${modeLabel(lesson.mode)}`,
                 lesson.llm_usd != null ? `roteiro US$ ${num(lesson.llm_usd, 3)}` : null),
      el("h2", {}, lesson.title),
      lesson.objective ? el("p", {}, lesson.objective) : null,
      el("dl", { class: "readouts" },
        readout("Duração", `~${clock(est.video_s)}`),
        readout("Cenas", String(est.scenes || 0), est.free3d ? `${est.free3d} em 3D` : null),
        readout("Voz", `~${thousands(est.credits)}`, "créditos", short ? "bad" : null),
        readout("Custo", `~US$ ${num(est.total_usd, 2)}`),
        readout("Produção", minutes(est.seconds))),
      el("p", { class: "muted small" },
        `Créditos de voz disponíveis: ${credits ? thousands(credits.left) : "sem leitura"}`
        + (credits && credits.resets_at ? ` (renovam em ${fmtDate(credits.resets_at)})` : "")
        + `. Custo: voz ao preço do plano (US$ ${num(est.voice_usd, 2)}) + LLM do storyboard`
        + (est.free3d ? " e das cenas 3D" : "") + ` (US$ ${num(est.llm_usd, 2)}). Estimativas medidas nas aulas 6 a 8.`));
    const telegram = Boolean(s.telegram);
    const sendBox = el("input", { type: "checkbox", checked: telegram && lessonsState.send ? true : null,
                                  disabled: telegram ? null : true });
    sendBox.addEventListener("change", () => { lessonsState.send = sendBox.checked; });
    const produce = el("button", { class: "primary", type: "button", disabled: short || busy || !s.available ? true : null,
                                   onclick: () => lessonAction(card, `/api/lessons/${lesson.id}/produce`, { send: sendBox.checked }) },
      "Produzir aula");
    card.append(el("div", { class: "actions" }, produce,
      el("label", { class: "check-inline", title: telegram ? "" : "Telegram não configurado no .env" }, sendBox,
         "enviar ao Telegram ao terminar"),
      el("span", { class: "spacer" }),
      confirmButton("Refazer roteiro", "Refazer mesmo?", () => lessonAction(card, `/api/lessons/${lesson.id}/plan`)),
      confirmButton("Descartar", "Descartar mesmo?", () => lessonAction(card, `/api/lessons/${lesson.id}/discard`))),
      el("p", { class: "action-error" }, short ? `Faltam créditos de voz para esta aula (~${thousands(est.credits)}).`
        : busy ? `Espere: ${jobLine(busy)}.` : ""),
      planDetails(lesson, true));
    return card;
  }

  // a lesson that stopped: where and why, and the way on
  function stoppedCard(lesson, job) {
    const s = lessonsState.state || {};
    const where = job && job.stage ? STAGE_LABELS[job.stage] || job.stage : null;
    const why = lesson.error || (job && job.error) || (lesson.has_plan ? "a produção não terminou" : "o roteiro não terminou");
    const busy = liveJob();
    const card = el("article", { class: "idea lesson stopped", "data-lesson": lesson.id },
      lessonHead(lesson, lesson.has_plan ? "parou" : "sem roteiro", "radar",
                 job && job.finished_at ? `${job.state} em ${fmtDate(job.finished_at)}` : null),
      el("h2", {}, lesson.title),
      el("p", {}, where && !why.includes("(etapa") ? `Parou na etapa ${where}: ${why}` : `Parou: ${why}`));
    const again = lesson.has_plan
      ? el("button", { class: "primary", type: "button", disabled: busy || !s.available ? true : null,
                       onclick: () => lessonAction(card, `/api/lessons/${lesson.id}/produce`,
                                                   { send: job && job.send != null ? job.send : Boolean(s.telegram) }) },
          "Retomar produção")
      : el("button", { class: "primary", type: "button", disabled: busy || !s.available ? true : null,
                       onclick: () => lessonAction(card, `/api/lessons/${lesson.id}/plan`) }, "Planejar roteiro");
    card.append(el("div", { class: "actions" }, again,
      lesson.has_plan ? el("span", { class: "muted small" }, "o que já foi pago fica em cache") : null,
      el("span", { class: "spacer" }),
      lesson.has_plan ? confirmButton("Refazer roteiro", "Refazer mesmo?", () => lessonAction(card, `/api/lessons/${lesson.id}/plan`)) : null,
      confirmButton("Descartar", "Descartar mesmo?", () => lessonAction(card, `/api/lessons/${lesson.id}/discard`))),
      el("p", { class: "action-error" }, busy ? `Espere: ${jobLine(busy)}.` : ""));
    if (job) card.append(logBlock(lesson, job));
    if (lesson.has_plan) card.append(planDetails(lesson, false));
    return card;
  }

  function lessonCard(lesson) {
    const [r0, r1] = lesson.quiz_score || [[0, 0], [0, 0]];
    const card = el("article", { class: "idea lesson", "data-lesson": lesson.id },
      el("div", { class: "head" }, el("span", { class: `badge ${lesson.status === "entregue" ? "main" : ""}` },
                                      LESSON_STATUS[lesson.status] || lesson.status),
        meta(`aula #${lesson.id}`, fmtDate(lesson.created_at), lesson.duration_s ? clock(lesson.duration_s) : null,
             lesson.cost_usd !== null ? `US$ ${num(lesson.cost_usd, 3)}` + (lesson.cost_brl != null ? ` · R$ ${num(lesson.cost_brl, 2)}` : "") : null,
             lesson.voice ? el("span", { title: lesson.voice }, lesson.voice_label || lesson.voice) : null,
             r0[1] ? `quiz ${r0[0]}/${r0[1]}` : null, r1[1] ? `re-quiz ${r1[0]}/${r1[1]}` : null,
             REVIEW[lesson.review], COMPARISON[lesson.comparison])),
      el("h2", {}, lesson.title),
      lesson.objective ? el("p", {}, lesson.objective) : null,
      lesson.video ? el("video", { controls: true, preload: "metadata", src: lesson.video, class: "lesson-video" }) : null,
      lesson.scenes3d.length ? el("div", { class: "chips" }, el("span", { class: "muted" }, "Cenas 3D interativas: "),
        ...lesson.scenes3d.map((s) => el("a", { class: "chip", href: s.url, target: "_blank", rel: "noopener" }, `${s.n}. ${s.title}`))) : null,
      lesson.interactive ? el("div", { class: "chips" }, el("a", { class: "chip", href: lesson.interactive, target: "_blank",
        rel: "noopener" }, "🧊 3D interativo"), el("span", { class: "muted" }, "ouça cada cena 3D, arraste para girar")) : null,
      lesson.sources_md ? el("p", { class: "muted" }, "Linha de base: suba ",
        el("a", { href: lesson.sources_md, target: "_blank", rel: "noopener" }, "fontes.md"),
        " no NotebookLM e gere um Video Overview (Explainer, pt-BR) para comparar.") : null);
    if (lesson.video && !lesson.delivered_at) {          // ready and not sent yet (unchecked box, or the sending failed)
      const s = lessonsState.state || {};
      const busy = liveJob();
      const failed = lesson.job && lesson.job.action === "envio" && lesson.job.state !== "concluida" ? lesson.job.error : null;
      card.append(el("div", { class: "actions" },
        el("button", { class: "primary", type: "button", disabled: busy || !s.telegram || !s.available ? true : null,
                       title: s.telegram ? "" : "Telegram não configurado no .env",
                       onclick: () => lessonAction(card, `/api/lessons/${lesson.id}/send`) }, "Enviar ao Telegram"),
        el("span", { class: "muted small" }, "vídeo, 3D interativo e quiz")),
        el("p", { class: "action-error" }, failed ? `O último envio parou: ${failed}` : busy ? `Espere: ${jobLine(busy)}.` : ""));
    }
    card.append(planDetails(lesson, false));
    return card;
  }

  function lessonView(lesson) {
    const job = lesson.job;
    if (job && job.alive) return progressCard(lesson, job);
    if (!lesson.has_plan) return stoppedCard(lesson, job);
    if (!lesson.video) {
      const tried = job && job.action === "aula";     // a production started: no longer a review, a lesson to resume
      return lesson.status === "planejada" && !tried ? reviewCard(lesson) : stoppedCard(lesson, job);
    }
    return lessonCard(lesson);
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
        report.check ? el("li", {}, `hyperframes check: ${(check.errors || []).length} erro(s), ${(check.warnings || []).length} aviso(s)`) : null));
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

  // --- the composer of a new lesson ---------------------------------------------------
  function drawLessonsMeta() {
    const s = lessonsState.state || {};
    const credits = s.credits;
    const parts = [readout("Aulas", thousands(lessonsState.lessons.length), s.discarded ? `${s.discarded} descartada(s)` : null),
      credits ? readout("Créditos de voz", thousands(credits.left), `de ${thousands(credits.limit)}`)
        : readout("Créditos de voz", "sem leitura", s.available ? "a ElevenLabs não respondeu" : null, "bad")];
    if (credits && credits.resets_at) parts.push(readout("Renovam", fmtDate(credits.resets_at)));
    $("#lessons-meta").replaceChildren(...parts);
  }

  function drawComposer() {
    const s = lessonsState.state || {};
    const busy = liveJob();
    const problems = s.ready || [];
    let text = `Planejar gasta até ~US$ ${num(s.plan_usd ?? 0.02, 2)} em ${minutes(s.plan_s || 200)}. A voz só é paga depois que você aprovar o roteiro.`;
    if (!s.available) text = "Aulas pela interface desligadas neste servidor.";
    else if (busy) text = `Espere a tarefa em andamento: ${jobLine(busy)}.`;
    else if (problems.length) text = `Para produzir, falta: ${problems.join("; ")}.`;
    const note = $("#lesson-form-note");
    note.textContent = text;
    note.classList.toggle("bad", !s.available || Boolean(busy) || problems.length > 0);
    $("#lesson-plan").disabled = !s.available || Boolean(busy);
    $("#lesson-mode-hint").textContent = MODE_HINT[lessonsState.mode];
    $("#lesson-entities-hint").textContent = lessonsState.entities.length
      ? "o roteiro parte das fontes destas entidades" : "opcional; sem entidade, vale o que o grafo achar pelo tema";
    $("#lesson-entities").replaceChildren(...lessonsState.entities.map((e) => el("span", { class: "chip picked" },
      el("span", { class: "dot", style: `background:${typeColor(e.type)}` }), e.name,
      el("button", { class: "x", type: "button", title: "remover", "aria-label": `remover ${e.name}`, onclick: () => {
        lessonsState.entities = lessonsState.entities.filter((x) => x.id !== e.id);
        drawComposer();
      } }, "×"))));
    $("#lesson-entity-search").hidden = lessonsState.entities.length >= 3;
  }

  function drawSuggestions() {
    const list = (lessonsState.state || {}).suggestions || [];
    $("#lesson-suggestions").replaceChildren(...(list.length ? list.map((t) => el("button", { class: "chip", type: "button",
      title: `tendência da semana · z ${num(t.z, 1)} · ${t.mentions} menções · liga a aula a esta entidade`, onclick: () => {
        $("#lesson-topic").value = t.name;
        fitLessonTopic();
        lessonsState.entities = [{ id: t.entity_id, name: t.name, type: t.type }];
        drawComposer();
        $("#lesson-topic").focus();
      } }, el("span", { class: "dot", style: `background:${typeColor(t.type)}` }), t.name, el("small", {}, t.type_label)))
      : [el("span", { class: "muted" }, "nenhuma tendência nova com fontes no último relatório semanal")]));
  }

  function fitLessonTopic() {
    const input = $("#lesson-topic");
    input.style.height = "auto";
    input.style.height = `${input.scrollHeight}px`;
  }

  async function searchLessonEntities(text) {
    let found;
    try { found = await api(`/api/search?q=${encodeURIComponent(text)}`); } catch (e) { return; }
    const box = $("#lesson-entity-results");
    const picked = new Set(lessonsState.entities.map((e) => e.id));
    const options = (found.entities || []).filter((e) => !picked.has(e.entity_id)).slice(0, 8);
    box.replaceChildren(...(options.length ? options.map((e) => el("button", { type: "button", onclick: () => {
      lessonsState.entities.push({ id: e.entity_id, name: e.name, type: e.type });
      $("#lesson-entity-search").value = "";
      box.hidden = true;
      drawComposer();
    } }, el("span", { class: "dot", style: `background:${typeColor(e.type)}` }), el("span", {}, e.name),
         el("small", { class: "muted" }, `${e.type_label} · ${e.mentions} menções`)))
      : [el("p", { class: "muted pad" }, "nenhuma entidade com esse nome")]));
    box.hidden = false;
  }

  async function planNewLesson() {
    const input = $("#lesson-topic");
    const note = $("#lesson-form-note");
    const topic = input.value.trim();
    if (topic.length < 3) {
      note.textContent = "Escreva o tema da aula (ou escolha uma sugestão da semana).";
      note.classList.add("bad");
      return;
    }
    $("#lesson-plan").disabled = true;
    try {
      await postJSON("/api/lessons", { topic, entities: lessonsState.entities.map((e) => e.id), mode: lessonsState.mode });
      input.value = "";
      lessonsState.entities = [];
      fitLessonTopic();
      await loadLessons();
    } catch (e) {
      note.textContent = e.message;
      note.classList.add("bad");
      $("#lesson-plan").disabled = false;
    }
  }

  function wireLessons() {
    segmented($("#lesson-mode"), LESSON_MODES, lessonsState.mode, (value) => { lessonsState.mode = value; drawComposer(); });
    const input = $("#lesson-topic");
    input.addEventListener("input", fitLessonTopic);
    input.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" && !ev.shiftKey) { ev.preventDefault(); $("#lesson-form").requestSubmit(); }
    });
    $("#lesson-form").addEventListener("submit", (ev) => { ev.preventDefault(); planNewLesson(); });
    const search = $("#lesson-entity-search");
    search.addEventListener("input", () => {
      clearTimeout(lessonsState.searchTimer);
      const text = search.value.trim();
      if (text.length < 2) { $("#lesson-entity-results").hidden = true; return; }
      lessonsState.searchTimer = setTimeout(() => searchLessonEntities(text), 220);
    });
    search.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape") $("#lesson-entity-results").hidden = true;
      if (ev.key === "Enter") {             // the first result, not the form
        ev.preventDefault();
        const first = $("#lesson-entity-results button");
        if (first) first.click();
      }
    });
    document.addEventListener("click", (ev) => {
      if (!ev.target.closest(".entity-picker")) $("#lesson-entity-results").hidden = true;
    });
  }

  // --- a running job: polled every 2.5 s, its seconds counted here --------------------
  function tickLessonTimes() {
    if (state.view !== "lessons" || !liveJob()) {
      clearInterval(lessonsState.ticker);
      lessonsState.ticker = null;
      return;
    }
    const now = Date.now();
    document.querySelectorAll("#lessons-list [data-since]").forEach((node) => {
      const seconds = Math.max(0, (now - Date.parse(node.dataset.since)) / 1000);
      const of = Number(node.dataset.of || 0);
      node.textContent = of ? `${clock(seconds)} de ${minutes(of)}` : clock(seconds);
    });
  }

  function followJob() {
    clearTimeout(lessonsState.poll);
    if (state.view !== "lessons" || !liveJob()) return;
    if (!lessonsState.ticker) lessonsState.ticker = setInterval(tickLessonTimes, 1000);
    tickLessonTimes();
    lessonsState.poll = setTimeout(pollLessonJob, 2500);
  }

  async function pollLessonJob() {
    let data;
    try { data = await api("/api/lessons/job"); } catch (e) { followJob(); return; }
    const job = data.job;
    if (!job || !job.alive) { await loadLessons(); return; }        // it ended: the lesson changed
    lessonsState.state.job = job;
    const lesson = lessonsState.lessons.find((l) => l.id === job.lesson_id);
    const card = $(`#lessons-list [data-lesson="${job.lesson_id}"]`);
    if (!lesson || !card) { await loadLessons(); return; }
    lesson.job = job;
    if (card.classList.contains("working")) refreshProgress(card, lesson, job);
    else card.replaceWith(progressCard(lesson, job));
    followJob();
  }

  async function loadLessons() {
    let lessons, s;
    try { [s, lessons] = await Promise.all([api("/api/lessons/state"), api("/api/lessons")]); }
    catch (e) {
      $("#lessons-meta").replaceChildren(readout("Aulas", "sem leitura", e.message, "bad"));
      return;
    }
    lessonsState.state = s;
    lessonsState.lessons = lessons;
    for (const lesson of lessons) {        // the state's copy of the job has the end of the log
      if (s.job && lesson.job && s.job.id === lesson.job.id) lesson.job = s.job;
    }
    drawLessonsMeta();
    drawComposer();
    drawSuggestions();
    $("#lessons-list").replaceChildren(...(lessons.length ? lessons.map(lessonView)
      : [el("p", { class: "empty-note" }, "Nenhuma aula ainda: escreva um tema acima ou escolha uma sugestão da semana.")]));
    followJob();
  }

  // --- start -----------------------------------------------------------------------
  function init() {
    loadFilters();
    buildFilters();
    wireSearch();
    wireGlossary();
    wireAsk();
    wireLessons();
    $("#unfocus").addEventListener("click", () => { state.focus = null; loadGraph(); });
    let resizeTimer = null;
    window.addEventListener("resize", () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => { if (scene3d) scene3d.resize(); }, 150);
    });
    document.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape" && state.selected) { state.selected = null; paint(); }
    });
    let lightFrame = 0;       // the pointer lights the page: a soft glow follows it (style.css reads --mx and --my)
    window.addEventListener("pointermove", (ev) => {
      if (lightFrame) return;
      lightFrame = requestAnimationFrame(() => {
        lightFrame = 0;
        document.documentElement.style.setProperty("--mx", `${ev.clientX}px`);
        document.documentElement.style.setProperty("--my", `${ev.clientY}px`);
      });
    });
    const all = $("#ideas-all");
    all.addEventListener("change", () => { ideasState.all = all.checked; loadIdeas(); });
    window.addEventListener("hashchange", route);
    loadStats();
    route();
  }

  init();
})();
