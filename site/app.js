"use strict";
/* QFT Zoo front end: loads data/theories.json (built by scripts/build.py) and
   renders a catalogue view and one page per theory, using hash routing:
     #/                 home: a directory of everything on the site
     #/catalogue        searchable catalogue; #/catalogue/<k>:<v> opens it filtered
                        (k = d, tag, q or spectrum)
     #/tables           summary tables, grouped by dimension and type
     #/feedback         comments on the site, read live from GitHub issues
     #/theory/<id>      a theory (with its spectrum, if data/spectra has one)
     #/landscape        2d CFTs in the (c, gap) plane
     #/contribute       how to contribute                                   */

// Display order and labels of relation types (incl. reverse links from build.py).
const REL_LABEL = {
  member_of: "Member of",
  has_member: "Members with their own page",
  product_of: "Tensor product containing",
  factor_of: "Appears as a factor in",
  orbifold_of: "Orbifold of",
  has_orbifold: "Orbifolds",
  same_partition_function: "Same torus partition function as",
  flows_from: "Flows from (UV)",
  flows_to: "Flows to (IR)",
  dual_to: "Dual to",
  related_to: "Related to",
};

let DB = null; // { generated, repo, branch, template, theories: [...] }
const BY_ID = new Map();
const filters = { q: "", d: new Set(), tags: new Set(), spectrum: false };
const app = document.getElementById("app");

/* ------------------------------------------------------------------ helpers */

const esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

function tex(src, display = false) {
  try {
    return katex.renderToString(String(src), { displayMode: display, throwOnError: false, strict: "ignore" });
  } catch {
    return `<code>${esc(src)}</code>`;
  }
}

marked.use({
  gfm: true,
  // Contributed text is data, not markup: show raw HTML literally.
  renderer: { html: (token) => esc(token.text ?? token.raw ?? "") },
  walkTokens(token) {
    if ((token.type === "link" || token.type === "image") && !/^(https?:|mailto:|#|\/|\.)/i.test(token.href || "")) {
      token.href = "#";
    }
  },
});

/** Markdown with $inline$ and $$display$$ math. Math is typeset first and
 *  protected from the Markdown parser by placeholders. */
function md(src, inline = false) {
  if (src == null || src === "") return "";
  const stash = [];
  const hold = (html) => `${stash.push(html) - 1}`;
  const s = String(src)
    .replace(/\$\$([\s\S]+?)\$\$/g, (_, m) => hold(tex(m, true)))
    .replace(/(^|[^\\])\$((?:\\.|[^$\\\n]|\n(?!\n))+?)\$/g, (_, pre, m) => pre + hold(tex(m)))
    .replace(/\\\$/g, "$");
  const html = inline ? marked.parseInline(s) : marked.parse(s);
  return html.replace(/(\d+)/g, (_, i) => stash[+i]);
}

/** Strip LaTeX markup for plain-text contexts (search, page titles). */
const TEX_SYMBOLS = { pm: "±", mp: "∓", times: "×", le: "≤", leq: "≤", ge: "≥", geq: "≥", prime: "′", sqrt: "√",
  Delta: "Δ", sigma: "σ", epsilon: "ε", phi: "φ", tau: "τ", lambda: "λ", mu: "μ", nu: "ν", eta: "η", theta: "θ", to: "→" };
const plain = (s) =>
  String(s ?? "")
    .replace(/\\([a-zA-Z]+)/g, (m, w) => TEX_SYMBOLS[w] ?? m)
    .replace(/\\(mathcal|mathbb|mathbf|mathrm|text|rm)\b/g, "")
    .replace(/\\([a-zA-Z]+)/g, "$1")
    .replace(/[${}\\^_]/g, "")
    .replace(/\s+/g, " ")
    .trim();

const safeUrl = (u) => (/^https?:\/\//i.test(u) ? u : "#");

const gh = {
  repo: () => `https://github.com/${DB.repo}`,
  blob: (path) => `${gh.repo()}/blob/${DB.branch}/${path}`,
  edit: (path) => `${gh.repo()}/edit/${DB.branch}/${path}`,
  newTheory: () =>
    `${gh.repo()}/new/${DB.branch}/data/theories?filename=${encodeURIComponent("my-theory.yaml")}` +
    `&value=${encodeURIComponent(DB.template)}`,
  suggest: () => `${gh.repo()}/issues/new?template=new-theory.yml`,
  feedback: (page = "") =>
    `${gh.repo()}/issues/new?template=feedback.yml&title=${encodeURIComponent(`[Feedback] ${page}`)}&page=${encodeURIComponent(page)}`,
  correction: (t) =>
    `${gh.repo()}/issues/new?template=correction.yml&title=${encodeURIComponent(`[Correction] ${plain(t.name)}`)}` +
    `&theory=${encodeURIComponent(t.id)}`,
};

const tagPill = (tag, active = false) =>
  `<button type="button" class="pill${active ? " on" : ""}" data-tag="${esc(tag)}" title="Filter by “${esc(tag)}”">${esc(tag)}</button>`;

function table(headers, rows, cls = "") {
  return `<div class="table-wrap"><table class="${cls}"><thead><tr>${headers
    .map((h) => `<th>${h}</th>`)
    .join("")}</tr></thead><tbody>${rows
    .map((r) => `<tr>${r.map((c) => `<td>${c ?? ""}</td>`).join("")}</tr>`)
    .join("")}</tbody></table></div>`;
}

const section = (id, title, body) => `<section class="block" id="sec-${id}"><h2>${title}</h2>${body}</section>`;

function symmetrySummary(t) {
  const s = t.symmetry || {};
  const parts = [];
  if (s.global) parts.push(md(s.global, true));
  if (s.gauge) parts.push(`<span class="muted">gauge</span> ${md(s.gauge, true)}`);
  if (s.supercharges) parts.push(`<span class="muted">${s.supercharges} supercharges</span>`);
  return parts.join("<br>");
}

/* -------------------------------------------------------------- home view */

const catalogueLink = (key, value) => `#/catalogue/${key}:${encodeURIComponent(value)}`;

function viewHome() {
  document.title = "QFT Zoo";
  const theories = DB.theories;
  const count = (items) => {
    const m = new Map();
    items.forEach((x) => m.set(x, (m.get(x) || 0) + 1));
    return m;
  };
  const dims = count(theories.map((t) => t.d));
  const tags = count(theories.flatMap((t) => t.tags || []));
  const nSpectra = theories.filter((t) => t.spectra?.length).length;
  const ext = 'target="_blank" rel="noopener"';
  const item = (href, label, n, attrs = "") =>
    `<li><a href="${href}" ${attrs}>${label}</a>${n != null ? ` <span class="n">${n}</span>` : ""}</li>`;
  const group = (title, cls, items) =>
    `<details class="portal-group"><summary class="portal-btn">${title}</summary><ul class="${cls}">${items.join("")}</ul></details>`;

  app.innerHTML = `
    <section class="portal">
      <h1>QFT Zoo</h1>
      <p class="portal-sub">An open, community-curated catalogue of quantum field theories and their data</p>
      <p class="portal-meta">${theories.length} theories · data built ${esc(DB.generated)}</p>
      <form class="portal-search" role="search">
        <input id="home-q" type="search" placeholder="Search names, symmetries, tags…" autocomplete="off" aria-label="Search the catalogue">
      </form>
      <div class="portal-grid">
        <div class="portal-col">
          <a class="portal-btn" href="#/catalogue">Interactive Catalogue</a>
          <a class="portal-btn" href="#/tables">Summary Tables</a>
          <a class="portal-btn" href="#/landscape">2d CFT Landscape</a>
          <a class="portal-btn" href="#/contribute">Contribute</a>
          <a class="portal-btn" href="#/feedback">Comments &amp; Feedback</a>
        </div>
        <div class="portal-col">
          <a class="portal-btn" href="${gh.newTheory()}" ${ext}>Add a Theory</a>
          ${group("By Dimension", "", [...dims.keys()].sort((a, b) => a - b).map((d) => item(catalogueLink("d", d), `d = ${d}`, dims.get(d))))}
          ${group("Topical Index", "two-col", [...tags.keys()].sort((a, b) => tags.get(b) - tags.get(a) || a.localeCompare(b)).map((g) => item(catalogueLink("tag", g), esc(g), tags.get(g))))}
          ${group("Downloads &amp; Data", "", [
            item("data/theories.json", "All theories (JSON)"),
            item("data/theory.schema.json", "Theory schema"),
            item("data/spectrum.schema.json", "Spectrum schema"),
            item(catalogueLink("spectrum", 1), "Theories with full spectra", nSpectra),
          ])}
          ${group("Other Resources", "", [
            item(gh.repo(), "Source &amp; data on GitHub", null, ext),
            item(gh.blob("CONTRIBUTING.md"), "Contributing guide", null, ext),
            item(gh.suggest(), "Suggest a theory", null, ext),
            item(`${gh.repo()}/issues/new?template=correction.yml`, "Report a problem", null, ext),
            item("https://arxiv.org/list/hep-th/recent", "arXiv hep-th", null, ext),
            item("https://inspirehep.net/", "INSPIRE", null, ext),
          ])}
        </div>
      </div>
    </section>`;

  app.querySelector(".portal-search").addEventListener("submit", (e) => {
    e.preventDefault();
    const q = app.querySelector("#home-q").value.trim();
    location.hash = q ? catalogueLink("q", q) : "#/catalogue";
  });
}

/* ------------------------------------------------------------ summary tables */

// A theory goes in the first of these groups whose tag it has.
const TABLE_GROUPS_2D = [
  ["minimal model", "Minimal models"],
  ["free", "Free theories"],
  ["orbifold", "Orbifolds"],
  ["coset", "Cosets"],
  [null, "Other 2d CFTs"],
];

const keyed = (t) => Object.fromEntries((t.quantities || []).filter((x) => x.key).map((x) => [x.key, x.value]));

function summaryName(t) {
  return `<a href="#/theory/${encodeURIComponent(t.id)}">${md(t.name, true)}</a>${t.family ? ' <span class="muted small">(family)</span>' : ""}`;
}

function summaryTable2d(list) {
  const sorted = [...list].sort((a, b) => (a.c_num ?? Infinity) - (b.c_num ?? Infinity));
  return table(
    ["Theory", tex("c"), tex("\\Delta_{\\rm gap}"), "Global symmetry", "Spectrum"],
    sorted.map((t) => {
      const q = keyed(t);
      return [
        summaryName(t),
        q.c != null ? `<span class="value">${tex(q.c)}</span>` : "",
        q.gap != null ? `<span class="value">${tex(q.gap)}</span>` : "",
        md(t.symmetry?.global, true),
        t.spectra?.length ? (t.family ? `${t.spectra.length} members` : "yes") : "",
      ];
    }),
    "data summary-2d"
  );
}

function summaryTableHigherD(list) {
  // Some values carry their own relation ("≈ 0.86–0.90"), so "=" is added only when they don't.
  const delta = (v) => (/^\s*(≈|~|<|>|\\approx|\\sim|\\le|\\ge)/.test(String(v)) ? `\\Delta ${v}` : `\\Delta = ${v}`);
  const hasGauge = list.some((t) => t.symmetry?.gauge);
  return table(
    ["Theory", "Global symmetry", ...(hasGauge ? ["Gauge group"] : []), "First listed operators"],
    list.map((t) => [
      summaryName(t),
      md(t.symmetry?.global, true),
      ...(hasGauge ? [md(t.symmetry?.gauge, true)] : []),
      (t.operators || [])
        .filter((o) => o.Delta != null)
        .slice(0, 2)
        .map((o) => `<span class="value">${tex(`${o.name}:\\ ${delta(o.Delta)}`)}</span>`)
        .join("<br>"),
    ]),
    "data"
  );
}

function viewTables() {
  document.title = "Summary Tables — QFT Zoo";
  const groups = [];
  const remaining = DB.theories.filter((t) => t.d === 2);
  for (const [tag, title] of TABLE_GROUPS_2D) {
    const list = remaining.filter((t) => tag === null || (t.tags || []).includes(tag));
    list.forEach((t) => remaining.splice(remaining.indexOf(t), 1));
    if (list.length) groups.push({ id: `d2-${groups.length}`, title: `d = 2: ${title}`, list, render: summaryTable2d });
  }
  const higher = [...new Set(DB.theories.map((t) => t.d))].filter((d) => d !== 2).sort((a, b) => a - b);
  for (const d of higher)
    groups.push({ id: `d${d}`, title: `d = ${d}`, list: DB.theories.filter((t) => t.d === d), render: summaryTableHigherD });

  app.innerHTML = `
    <header class="theory-head">
      <h1>Summary Tables</h1>
      <p class="lede">Key data for every theory in the zoo, at a glance. Each theory appears once, in the first group that
        fits it; values, methods and references are on its own page.</p>
    </header>
    <nav class="jump" aria-label="Contents">
      ${groups.map((g) => `<button type="button" class="linkish" data-jump="${g.id}">${g.title} <span class="muted">(${g.list.length})</span></button>`).join("")}
    </nav>
    ${groups.map((g) => section(g.id, `${g.title} <span class="muted small">(${g.list.length})</span>`, g.render(g.list))).join("")}`;
}

/* ------------------------------------------------------------ browse view */

let rowCache = null; // id -> rendered <tr>

function searchText(t) {
  const s = t.symmetry || {};
  return plain(
    [t.id, t.name, ...(t.aliases || []), t.summary, ...(t.tags || []), s.global, s.gauge, s.spacetime, `${t.d}d`, `d=${t.d}`].join(" ")
  ).toLowerCase();
}

/** Catalogue "Key data" cell: keyed quantities (c, gap) if present, else symmetry. */
function keyData(t) {
  const q = Object.fromEntries((t.quantities || []).filter((x) => x.key).map((x) => [x.key, x.value]));
  const parts = [];
  if (q.c != null) parts.push(tex(`c = ${q.c}`));
  if (q.gap != null) parts.push(tex(`\\Delta_{\\rm gap} = ${q.gap}`));
  const spec = t.spectra?.length ? `<div class="sub">${t.family ? `spectra of ${t.spectra.length} members` : "full spectrum"}</div>` : "";
  if (parts.length) return parts.join("<br>") + spec;
  return symmetrySummary(t) + spec;
}

function renderRow(t) {
  return `<tr data-id="${esc(t.id)}">
    <td class="name"><a href="#/theory/${encodeURIComponent(t.id)}">${md(t.name, true)}</a>
      <div class="pills">${(t.tags || []).map((g) => tagPill(g)).join("")}</div></td>
    <td class="num">${t.d}</td>
    <td class="sym">${keyData(t)}</td>
    <td class="summary">${md(t.summary, true)}</td>
  </tr>`;
}

function viewBrowse() {
  document.title = "Catalogue — QFT Zoo";
  const theories = DB.theories;
  const dims = [...new Set(theories.map((t) => t.d))].sort((a, b) => a - b);
  const tagCount = new Map();
  theories.forEach((t) => (t.tags || []).forEach((g) => tagCount.set(g, (tagCount.get(g) || 0) + 1)));
  const tags = [...tagCount.keys()].sort((a, b) => tagCount.get(b) - tagCount.get(a) || a.localeCompare(b));

  if (!rowCache) rowCache = new Map(theories.map((t) => [t.id, renderRow(t)]));

  app.innerHTML = `
    <header class="theory-head">
      <h1>Interactive Catalogue</h1>
      <p class="lede">Symmetries, spectra, central charges, RG flows and dualities. Every entry is a plain-text file in a
        public GitHub repository, and anyone can propose additions.</p>
    </header>

    <section class="controls" aria-label="Filters">
      <input id="q" type="search" placeholder="Search names, symmetries, tags…" autocomplete="off"
             aria-label="Search" value="${esc(filters.q)}">
      <div class="chips"><span class="chips-label">Dimension</span>
        ${dims.map((d) => `<button type="button" class="chip" data-d="${d}" aria-pressed="${filters.d.has(d)}">d = ${d}</button>`).join("")}
      </div>
      <div class="chips"><span class="chips-label">Data</span>
        <button type="button" class="chip" data-chip-spectrum aria-pressed="${filters.spectrum}">Spectrum &amp; characters</button>
      </div>
      <div class="chips"><span class="chips-label">Tags</span>
        ${tags.map((g) => `<button type="button" class="chip" data-chip-tag="${esc(g)}" aria-pressed="${filters.tags.has(g)}">${esc(g)}</button>`).join("")}
      </div>
    </section>

    <div class="count-row"><span id="count" class="muted"></span>
      <button type="button" id="clear" class="linkish" hidden>Clear filters</button></div>

    <div class="table-wrap">
      <table class="catalogue">
        <thead><tr><th>Theory</th><th class="num">d</th><th>Key data</th><th>Summary</th></tr></thead>
        <tbody id="rows">${theories.map((t) => rowCache.get(t.id)).join("")}</tbody>
      </table>
    </div>
    <p id="empty" class="empty" hidden>No theories match these filters.</p>`;

  const q = app.querySelector("#q");
  q.addEventListener("input", () => {
    filters.q = q.value;
    applyFilters();
  });
  app.querySelectorAll("[data-d]").forEach((b) =>
    b.addEventListener("click", () => toggle(filters.d, +b.dataset.d))
  );
  app.querySelectorAll("[data-chip-tag]").forEach((b) =>
    b.addEventListener("click", () => toggle(filters.tags, b.dataset.chipTag))
  );
  app.querySelector("[data-chip-spectrum]").addEventListener("click", () => {
    filters.spectrum = !filters.spectrum;
    applyFilters();
  });
  app.querySelector("#clear").addEventListener("click", () => {
    filters.q = "";
    filters.d.clear();
    filters.tags.clear();
    filters.spectrum = false;
    q.value = "";
    applyFilters();
  });
  app.querySelector("#rows").addEventListener("click", (e) => {
    if (e.target.closest("a, button")) return;
    const tr = e.target.closest("tr[data-id]");
    if (tr) location.hash = `#/theory/${encodeURIComponent(tr.dataset.id)}`;
  });
  applyFilters();
}

function toggle(set, v) {
  set.has(v) ? set.delete(v) : set.add(v);
  applyFilters();
}

function applyFilters() {
  const terms = plain(filters.q).toLowerCase().split(/\s+/).filter(Boolean);
  let shown = 0;
  for (const t of DB.theories) {
    const ok =
      (filters.d.size === 0 || filters.d.has(t.d)) &&
      [...filters.tags].every((g) => (t.tags || []).includes(g)) &&
      (!filters.spectrum || t.spectra?.length > 0) &&
      terms.every((w) => t._search.includes(w));
    const tr = app.querySelector(`tr[data-id="${CSS.escape(t.id)}"]`);
    if (tr) tr.hidden = !ok;
    shown += ok;
  }
  app.querySelectorAll("[data-d]").forEach((b) => b.setAttribute("aria-pressed", filters.d.has(+b.dataset.d)));
  app.querySelectorAll("[data-chip-tag]").forEach((b) =>
    b.setAttribute("aria-pressed", filters.tags.has(b.dataset.chipTag))
  );
  app.querySelector("[data-chip-spectrum]").setAttribute("aria-pressed", filters.spectrum);
  app.querySelectorAll("#rows .pill").forEach((p) => p.classList.toggle("on", filters.tags.has(p.dataset.tag)));
  const total = DB.theories.length;
  app.querySelector("#count").textContent =
    shown === total ? `${total} theories` : `${shown} of ${total} theories`;
  app.querySelector("#clear").hidden = !(filters.q || filters.d.size || filters.tags.size || filters.spectrum);
  app.querySelector("#empty").hidden = shown > 0;
}

/* ------------------------------------------------------------ theory view */

function viewTheory(id) {
  const t = BY_ID.get(id);
  if (!t) return viewNotFound(`No theory with id “${id}”.`);
  document.title = `${plain(t.name)} — QFT Zoo`;

  const refs = t.references || [];
  const refNum = new Map(refs.map((r, i) => [r.key, i + 1]));
  const cite = (keys) =>
    (keys || []).map((k) => `<a class="cite" href="#" data-ref="${esc(k)}">[${refNum.get(k)}]</a>`).join("");
  const source = (x) => [x.method ? esc(x.method) : "", cite(x.refs)].filter(Boolean).join(" ");

  const out = [];

  if (t.description) out.push(section("overview", "Overview", `<div class="prose">${md(t.description)}</div>`));

  if (t.lagrangian) out.push(section("lagrangian", "Lagrangian", `<div class="display-math">${tex(t.lagrangian, true)}</div>`));

  if (t.parameters?.length)
    out.push(
      section(
        "parameters",
        "Parameters",
        table(
          ["Parameter", "Description", "Range"],
          t.parameters.map((p) => [tex(p.symbol), md(p.description, true), md(p.range, true)])
        )
      )
    );

  if (t.family && t.members?.length) out.push(section("members", "Members", membersTable(t)));

  if (t.symmetry) {
    const s = t.symmetry;
    const rows = [
      ["Spacetime", s.spacetime && md(s.spacetime, true)],
      ["Supercharges", s.supercharges != null && tex(s.supercharges)],
      ["Global", s.global && md(s.global, true)],
      ["Gauge", s.gauge && md(s.gauge, true)],
      ["Notes", s.notes && md(s.notes, true)],
    ].filter(([, v]) => v);
    out.push(section("symmetry", "Symmetry", `<dl class="kv">${rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("")}</dl>`));
  }

  if (t.quantities?.length)
    out.push(
      section(
        "data",
        "Data",
        table(
          ["Quantity", "Description", "Value", "Source"],
          t.quantities.map((q) => [
            tex(q.symbol),
            md(q.description, true) + (q.note ? `<div class="sub">${md(q.note, true)}</div>` : ""),
            `<span class="value">${tex(q.value)}</span>`,
            source(q),
          ]),
          "data"
        )
      )
    );

  if (t.spectra?.length) out.push(section("spectrum", "Spectrum", spectrumShell(t)));

  if (t.operators?.length) {
    // Only show columns that some operator fills.
    const cols = [
      ["Operator", (o) => tex(o.name), true],
      ["Δ", (o) => `<span class="value">${tex(o.Delta)}</span>`, true],
      [tex("(h, \\bar h)"), (o) => (o.weights ? tex(o.weights) : ""), "weights"],
      ["Mult.", (o) => (o.degeneracy ? tex(o.degeneracy) : ""), "degeneracy"],
      ["Spin", (o) => (o.spin != null ? tex(o.spin) : ""), "spin"],
      ["Representation", (o) => md(o.rep, true), "rep"],
      ["Notes", (o) => md(o.note, true), "note"],
      ["Source", source, null],
    ].filter(([, , key]) => key === true || key === null || t.operators.some((o) => o[key] != null));
    const hasSource = t.operators.some((o) => o.method || o.refs?.length);
    const use = cols.filter(([h]) => h !== "Source" || hasSource);
    out.push(section("operators", "Operators",
      table(use.map(([h]) => h), t.operators.map((o) => use.map(([, f]) => f(o))), "data")));
  }

  const links = [...(t.relations || []), ...(t.backlinks || [])];
  if (links.length) {
    const groups = Object.keys(REL_LABEL)
      .map((type) => [type, links.filter((l) => l.type === type)])
      .filter(([, ls]) => ls.length);
    out.push(
      section(
        "relations",
        "Relations",
        `<dl class="kv relations">${groups
          .map(
            ([type, ls]) =>
              `<dt>${REL_LABEL[type]}</dt><dd><ul>${ls
                .map((l) => {
                  const other = BY_ID.get(l.target);
                  // Which member of a family: the parameter belongs to the family side of the link.
                  const famSide = other?.family ? other : t.family ? t : null;
                  const at = l.at != null
                    ? ` <span class="muted">(${tex(`${famSide?.family.parameter ?? ""}${famSide ? " = " : ""}${l.at}`)}${
                        l.variant ? `, ${esc(l.variant)}` : ""})</span>`
                    : "";
                  return `<li><a href="#/theory/${encodeURIComponent(l.target)}">${md(other ? other.name : l.target, true)}</a>${at}${
                    l.note ? ` <span class="muted">— ${md(l.note, true)}</span>` : ""
                  }</li>`;
                })
                .join("")}</ul></dd>`
          )
          .join("")}</dl>`
      )
    );
  }

  if (refs.length)
    out.push(section("references", "References", `<ol class="refs">${refs.map(refItem).join("")}</ol>`));

  const contributors = (t.contributors || [])
    .map((u) => `<a href="https://github.com/${encodeURIComponent(u)}" target="_blank" rel="noopener">@${esc(u)}</a>`)
    .join(", ");

  app.innerHTML = `
    <nav class="crumbs"><a href="#/catalogue">← All theories</a></nav>
    <header class="theory-head">
      <h1>${md(t.name, true)}</h1>
      ${t.aliases?.length ? `<p class="aliases">Also known as: ${t.aliases.map((a) => md(a, true)).join(" · ")}</p>` : ""}
      <div class="pills"><span class="badge">d = ${t.d}</span>${(t.tags || []).map((g) => tagPill(g)).join("")}</div>
      <p class="lede">${md(t.summary, true)}</p>
      <p class="actions">
        <a class="btn" href="${gh.edit(t.source)}" target="_blank" rel="noopener">Edit this entry</a>
        <a class="btn" href="${gh.blob(t.source)}" target="_blank" rel="noopener">View source</a>
        <a class="btn" href="${gh.correction(t)}" target="_blank" rel="noopener">Report a problem</a>
        <a class="btn" href="${gh.feedback(t.id)}" target="_blank" rel="noopener">Leave a comment</a>
      </p>
    </header>
    ${jumpBar(out)}
    ${out.join("")}
    <p class="muted small">${contributors ? `Contributors: ${contributors}. ` : ""}Source:
      <a href="${gh.blob(t.source)}" target="_blank" rel="noopener"><code>${esc(t.source)}</code></a></p>`;
  if (t.spectra?.length) showSpectrum(t, 0);
}

/** Contents line for a page built from section() blocks; omitted on short pages. */
function jumpBar(sections) {
  const items = sections.map((s) => s.match(/id="sec-([^"]+)"><h2>(.*?)<\/h2>/)).filter(Boolean);
  if (items.length < 3) return "";
  return `<nav class="jump" aria-label="Contents">${items
    .map(([, id, title]) => `<button type="button" class="linkish" data-jump="${esc(id)}">${title}</button>`)
    .join("")}</nav>`;
}

/** Members of a family: the first `show` parameter values (all variants of each),
 *  with a toggle for the rest that build.py computed. */
function membersTable(t) {
  const f = t.family;
  const p = f.parameter || "m";
  const values = [...new Set(t.members.map((m) => String(m.at)))];
  const shown = new Set(values.slice(0, f.show || 8));
  const hasVariant = t.members.some((m) => m.variant);
  const hasLabel = t.members.some((m) => m.label);
  const hasNotes = t.members.some((m) => m.entries?.length || m.note);
  const specIndex = new Map((t.spectra || []).map((r, i) => [`${r.at}|${r.variant ?? ""}`, i]));
  const head = [tex(p), ...(hasVariant ? ["Variant"] : []), ...(hasLabel ? ["Theory"] : []), tex("c"), tex("\\Delta_{\\rm gap}"),
    ...(hasNotes ? ["Entry / notes"] : []), ...(specIndex.size ? ["Spectrum"] : [])];
  const rows = t.members.map((m) => {
    const entries = (m.entries || [])
      .map((id) => `<a href="#/theory/${encodeURIComponent(id)}">${md(BY_ID.get(id)?.name ?? id, true)}</a>`)
      .join(", ");
    const notes = [entries, m.note ? md(m.note, true) : ""].filter(Boolean).join(" · ");
    const cells = [tex(m.at), ...(hasVariant ? [esc(m.variant ?? "")] : []), ...(hasLabel ? [md(m.label, true)] : []),
      m.c != null ? tex(m.c) : "", m.gap != null ? tex(m.gap) : "", ...(hasNotes ? [notes] : [])];
    if (specIndex.size) {
      const i = specIndex.get(`${m.at}|${m.variant ?? ""}`);
      cells.push(i == null ? "" : `<button type="button" class="linkish" data-spec-member="${i}">show</button>`);
    }
    return `<tr${shown.has(String(m.at)) ? "" : ' class="extra" hidden'}>${cells.map((c) => `<td>${c}</td>`).join("")}</tr>`;
  });
  const more = values.length > shown.size
    ? `<p><button type="button" class="linkish" data-more-members>Show ${values.length - shown.size} more values of ${tex(p)}</button></p>`
    : "";
  const formula = f.formulas
    ? `<p class="muted small">Computed exactly from the closed forms ${Object.entries(f.formulas).map(([k, v]) => `<code>${esc(k)} = ${esc(v)}</code>`).join(", ")}${
        f.overrides?.length ? ", with listed exceptions" : ""}.</p>`
    : "";
  return `${formula}<div class="table-wrap"><table class="data members"><thead><tr>${head.map((h) => `<th>${h}</th>`).join("")}</tr></thead>
    <tbody>${rows.join("")}</tbody></table></div>${more}`;
}

function refItem(r) {
  const links = [];
  if (r.arxiv) links.push(`<a href="https://arxiv.org/abs/${encodeURI(r.arxiv)}" target="_blank" rel="noopener">arXiv:${esc(r.arxiv)}</a>`);
  if (r.doi) links.push(`<a href="https://doi.org/${encodeURI(r.doi)}" target="_blank" rel="noopener">DOI</a>`);
  if (r.url) links.push(`<a href="${esc(safeUrl(r.url))}" target="_blank" rel="noopener">link</a>`);
  const q = r.arxiv ? `arxiv:${r.arxiv}` : r.doi ? `doi:${r.doi}` : null;
  if (q) links.push(`<a href="https://inspirehep.net/literature?q=${encodeURIComponent(q)}" target="_blank" rel="noopener">INSPIRE</a>`);
  return `<li id="ref-${esc(r.key)}">${r.authors ? `${esc(r.authors)}, ` : ""}<em>${md(r.title, true)}</em>${
    r.journal ? `, ${esc(r.journal)}` : ""
  }${r.year ? ` (${r.year})` : ""}. <span class="ref-links">${links.join(" · ")}</span>${
    r.note ? ` <span class="muted small">— ${md(r.note, true)}</span>` : ""}</li>`;
}

/* ----------------------------------------------------------- spectra */

// Exact rationals for weights given as "a/b" strings.
const gcd = (a, b) => (b ? gcd(b, a % b) : Math.abs(a));
function rat(s) {
  const [n, d = "1"] = String(s).split("/");
  const N = parseInt(n, 10), D = parseInt(d, 10), g = gcd(N, D) || 1;
  return [N / g, D / g];
}
const radd = ([a, b], [c, d], sign = 1) => {
  const n = a * d + sign * c * b, m = b * d, g = gcd(n, m) || 1;
  return [n / g, m / g];
};
const rnum = ([a, b]) => a / b;
function rtex([n, d]) {
  if (d === 1) return String(n);
  return `${n < 0 ? "-" : ""}\\tfrac{${Math.abs(n)}}{${d}}`;
}

const SPECTRUM_CACHE = new Map();
const SPEC_STATE = { t: null, S: null, full: new Set() };
const SPEC_ROWS = 24; // rows shown before "show all"

function memberName(t, row) {
  const p = t.family?.parameter || "m";
  return `${p} = ${plain(String(row.at))}${row.variant ? `, ${row.variant}` : ""}`;
}

function spectrumShell(t) {
  const pick = t.family
    ? `<p class="viz-controls"><label class="select-label">Member
        <select id="spectrum-member">${t.spectra
          .map((r, i) => `<option value="${i}">${esc(memberName(t, r))}</option>`)
          .join("")}</select></label>
        <span class="muted small">${t.spectra.length} members have computed spectra.</span></p>`
    : "";
  return `${pick}<div id="spectrum-body" aria-live="polite"><p class="muted">Loading spectrum…</p></div>`;
}

function showSpectrum(t, i) {
  const row = t.spectra[i];
  const body = document.getElementById("spectrum-body");
  if (!row || !body) return;
  const done = (S) => {
    if (SPEC_STATE.t !== t || document.getElementById("spectrum-body") !== body) return;
    SPEC_STATE.S = S;
    SPEC_STATE.full = new Set();
    body.innerHTML = renderSpectrum(S);
  };
  SPEC_STATE.t = t;
  const hit = SPECTRUM_CACHE.get(row.path);
  if (hit) return done(hit);
  fetch(row.path, { cache: "no-cache" })
    .then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    })
    .then((S) => {
      SPECTRUM_CACHE.set(row.path, S);
      done(S);
    })
    .catch((err) => {
      body.innerHTML = `<p class="error">Could not load ${esc(row.path)} (${esc(err.message)}).</p>`;
    });
}

/** q-expansion sum_n a_n q^{n*step} as TeX, first `terms` nonzero terms. */
function qSeries(coeffs, step = "1", terms = 9) {
  const st = rat(step);
  const parts = [];
  let shown = 0;
  for (let n = 0; n < coeffs.length && shown < terms; n++) {
    const a = coeffs[n];
    if (!a) continue;
    const e = [st[0] * n, st[1]];
    const g = gcd(e[0], e[1]) || 1;
    const ex = [e[0] / g, e[1] / g];
    const q = ex[0] === 0 ? "" : ex[1] === 1 && ex[0] === 1 ? "q" : ex[1] === 1 ? `q^{${ex[0]}}` : `q^{${ex[0]}/${ex[1]}}`;
    const mag = Math.abs(a);
    const coef = q && mag === 1 ? "" : String(mag);
    parts.push(`${a < 0 ? "-" : parts.length ? "+" : ""}${coef}${q}`);
    shown++;
  }
  return parts.join(" ") + " + \\dots";
}

function specTable(key, headers, rows) {
  const full = SPEC_STATE.full.has(key);
  const show = full ? rows : rows.slice(0, SPEC_ROWS);
  const more = rows.length > show.length
    ? `<p><button type="button" class="linkish" data-spec-more="${key}">Show all ${rows.length} rows</button></p>` : "";
  return `<div data-spec-table="${key}">${table(headers, show.map((f) => f()), "data spectrum")}${more}</div>`;
}

function weightCells(h, hb) {
  const H = rat(h), HB = rat(hb);
  return [tex(`(${rtex(H)},\\ ${rtex(HB)})`), tex(rtex(radd(H, HB))), tex(rtex(radd(H, HB, -1)))];
}

function renderSpectrum(S) {
  const c = rat(S.c);
  const parts = [];
  const err = S.s_error ? S.s_error.toExponential(0).replace(/e([+-])(\d+)/, (_, s, d) => `\\times 10^{${s === "-" ? "-" : ""}${d}}`) : "0";
  parts.push(`<p class="spec-checks">${tex("c = " + rtex(c))} · lightest non-vacuum Virasoro primary ${
    S.gap != null ? tex("\\Delta = " + rtex(rat(S.gap))) : "—"} · modular invariance checked: ${tex(
    `|Z(\\tau) - Z(-1/\\tau)|/|Z| \\approx ${err}`)} · degeneracies are non-negative integers for ${tex(
    `h, \\bar h \\le ${rtex(rat(S.cutoff))}`)}.</p>`);
  if (S.Z_tex) parts.push(`<div class="display-math">${tex(S.Z_tex, true)}</div>`);
  if (S.description) parts.push(`<div class="prose">${md(S.description)}</div>`);

  if (S.primaries?.length) {
    const algebra = S.chiral_algebra ? ` of ${tex(S.chiral_algebra)}` : "";
    const rows = S.primaries.map((p) => () => [
      ...weightCells(p.h, p.hb),
      tex(String(p.mult)),
      p.pairs.slice(0, 3).map(([i, j]) => tex(`${S.blocks[i].label}\\,\\overline{${S.blocks[j].label}}`)).join(", ") +
        (p.pairs.length > 3 ? " …" : ""),
    ]);
    parts.push(`<h3>Primaries${algebra}</h3>
      <p class="muted small">Each term ${tex("N_{ij}\\,\\chi_i\\overline{\\chi_j}")} of ${tex("Z")}: left and right weights and multiplicity.</p>
      ${specTable("prim", [tex("(h, \\bar h)"), tex("\\Delta"), tex("s"), "Mult.", "Term"], rows)}`);
  }

  const showVir = !(S.irreducible && rnum(c) < 1) && S.virasoro?.length;
  if (showVir) {
    const rows = S.virasoro.map(([h, hb, n]) => () => [...weightCells(h, hb), tex(String(n))]);
    const capped = S.n_virasoro > S.virasoro.length
      ? ` (the ${S.virasoro.length} lightest of ${S.n_virasoro} up to the cutoff)` : "";
    parts.push(`<h3>Virasoro primaries</h3>
      <p class="muted small">${tex("Z")} decomposed into Virasoro characters${rnum(c) > 1
        ? ` (${tex("\\chi_h = q^{h-(c-1)/24}/\\eta")}, and ${tex("(1-q)\\,q^{-(c-1)/24}/\\eta")} for the vacuum)`
        : rnum(c) === 1 ? ` (degenerate at ${tex("h = n^2/4")})` : ""}, for ${tex(`h, \\bar h \\le ${rtex(rat(S.cutoff))}`)}${capped}.</p>
      ${specTable("vir", [tex("(h, \\bar h)"), tex("\\Delta"), tex("s"), "Degeneracy"], rows)}`);
  }

  const blockRows = S.blocks.map((b) => () => [
    tex(b.label),
    tex(rtex(rat(b.h))),
    tex(qSeries(b.coeffs, b.step || "1")),
  ]);
  parts.push(`<h3>${S.irreducible ? "Characters" : "Blocks"}</h3>
    ${S.character_tex ? `<div class="prose small">${md(S.character_tex)}</div>` : ""}
    <p class="muted small">Each ${S.irreducible ? "character" : "block"} is ${tex("q^{h - c/24}")} times the series shown.</p>
    ${specTable("blocks", [S.irreducible ? "Character" : "Block", tex("h"), tex("q^{c/24-h}\\times")], blockRows)}`);

  const links = [`<a href="${gh.blob(S.source)}" target="_blank" rel="noopener">data file</a>`];
  if (S.generator) links.push(`<a href="${gh.blob(S.generator)}" target="_blank" rel="noopener">generator script</a>`);
  parts.push(`<p class="muted small">Source: ${links.join(" · ")}.</p>`);
  return parts.join("");
}

/* --------------------------------------------------------- landscape view */

const SVGNS = "http://www.w3.org/2000/svg";
const LANDSCAPE = { range: "window", family: "" };
const KIND_LABEL = {
  theory: "Individual theory",
  member: "Member of a family (minimal models, parafermions, …)",
  continuous: "Continuous family at c = 1 (circle, orbifold)",
};

function svgEl(name, attrs = {}, parent) {
  const el = document.createElementNS(SVGNS, name);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  if (parent) parent.appendChild(el);
  return el;
}

/** All plottable 2d data: individual theories, family members, continuous spans. */
function landscapeData() {
  const points = [];
  const spans = [];
  const familyMemberEntries = new Set();
  for (const t of DB.theories) {
    if (t.d !== 2 || !t.family) continue;
    const continuous = !!t.family.span;
    if (t.span_num) spans.push({ fam: t, ...t.span_num });
    for (const m of t.members || []) {
      if (m.c_num == null || m.gap_num == null || m.c_num > 1.5 + 1e-12) continue;
      (m.entries || []).forEach((id) => familyMemberEntries.add(id));
      points.push({
        c: m.c_num, gap: m.gap_num, cs: m.c, gs: m.gap, fam: t, member: m,
        kind: continuous ? "continuous" : "member",
        link: m.entries?.length ? m.entries[0] : t.id,
      });
    }
  }
  for (const t of DB.theories) {
    if (t.d !== 2 || t.family || t.c_num == null || t.gap_num == null || familyMemberEntries.has(t.id)) continue;
    const q = Object.fromEntries(t.quantities.filter((x) => x.key).map((x) => [x.key, x.value]));
    points.push({ c: t.c_num, gap: t.gap_num, cs: q.c, gs: q.gap, theory: t, kind: "theory", link: t.id });
  }
  return { points, spans };
}

function pointLabel(p) {
  if (p.theory) return md(p.theory.name, true);
  const m = p.member;
  const own = m.entries?.length ? md(BY_ID.get(m.entries[0]).name, true) : md(p.fam.name, true);
  const where = m.label ? md(m.label, true) : tex(`${p.fam.family.parameter} = ${m.at}`) + (m.variant ? `, ${esc(m.variant)}` : "");
  return m.entries?.length ? `${own} <span class="muted">(${where})</span>` : `${own} <span class="muted">— ${where}</span>`;
}

function viewLandscape() {
  document.title = "2d CFT landscape — QFT Zoo";
  const { points, spans } = landscapeData();
  const families = DB.theories.filter((t) => t.d === 2 && t.family && points.some((p) => p.fam === t));

  app.innerHTML = `
    <header class="theory-head">
      <h1>2d CFT landscape</h1>
      <p class="lede">Every unitary compact 2d CFT in the zoo with known central charge $c$ and spectral gap
        $\\Delta_{\\rm gap}$ (lightest non-vacuum Virasoro primary). Infinite families are drawn member by member;
        hover a point for the theories there, click to open its page.</p>
    </header>
    <div class="viz-controls">
      <div class="chips" role="group" aria-label="Range of c">
        <span class="chips-label">Range</span>
        <button type="button" class="chip" data-range="window" aria-pressed="${LANDSCAPE.range === "window"}">${tex("1 \\le c \\le 3/2")}</button>
        <button type="button" class="chip" data-range="all" aria-pressed="${LANDSCAPE.range === "all"}">${tex("c \\le 3/2")}</button>
      </div>
      <label class="select-label">Highlight family
        <select id="fam-select">
          <option value="">None</option>
          ${families.map((f) => `<option value="${esc(f.id)}"${LANDSCAPE.family === f.id ? " selected" : ""}>${esc(plain(f.name))}</option>`).join("")}
        </select>
      </label>
    </div>
    <div class="viz-root">
      <ul class="legend" aria-label="Legend">
        <li><svg width="14" height="14" aria-hidden="true"><circle cx="7" cy="7" r="4.5" fill="var(--series-1)"/></svg>${KIND_LABEL.theory}</li>
        <li><svg width="14" height="14" aria-hidden="true"><circle cx="7" cy="7" r="4.5" fill="var(--series-2)"/></svg>${KIND_LABEL.member}</li>
        <li><svg width="14" height="14" aria-hidden="true"><rect x="4" y="1" width="6" height="12" rx="3" fill="var(--series-3)"/></svg>${KIND_LABEL.continuous.replace("c = 1", tex("c=1"))}</li>
      </ul>
      <div class="chart-wrap" id="chart"></div>
      <div class="tooltip" id="tip" role="status" hidden></div>
    </div>
    <details class="table-view">
      <summary>Table view (${points.length} points)</summary>
      <div class="table-wrap"><table class="data"><thead><tr><th>${tex("c")}</th><th>${tex("\\Delta_{\\rm gap}")}</th><th>Theory</th><th>Kind</th></tr></thead>
      <tbody>${[...points].sort((a, b) => a.c - b.c || a.gap - b.gap)
        .map((p) => `<tr><td>${tex(p.cs)}</td><td>${tex(p.gs)}</td><td><a href="#/theory/${encodeURIComponent(p.link)}">${pointLabel(p)}</a></td><td class="muted">${p.kind === "theory" ? "individual" : p.kind === "member" ? "family member" : "c = 1 branch"}</td></tr>`)
        .join("")}</tbody></table></div>
    </details>`;
  // Render the $...$ in the lede.
  const lede = app.querySelector(".lede");
  lede.innerHTML = md(lede.textContent.trim(), true);

  app.querySelectorAll("[data-range]").forEach((b) =>
    b.addEventListener("click", () => {
      LANDSCAPE.range = b.dataset.range;
      app.querySelectorAll("[data-range]").forEach((x) => x.setAttribute("aria-pressed", x === b));
      drawLandscape(points, spans);
    })
  );
  app.querySelector("#fam-select").addEventListener("change", (e) => {
    LANDSCAPE.family = e.target.value;
    drawLandscape(points, spans);
  });
  drawLandscape(points, spans);
}

function drawLandscape(points, spans) {
  const host = app.querySelector("#chart");
  const tip = app.querySelector("#tip");
  host.textContent = "";
  tip.hidden = true;

  const W = 960, H = 540, M = { l: 64, r: 24, t: 28, b: 52 };
  const [x0, x1] = LANDSCAPE.range === "window" ? [0.98, 1.52] : [0.45, 1.52];
  const cMin = LANDSCAPE.range === "window" ? 1 : x0;
  const [y0, y1] = [0, 0.52];
  const X = (c) => M.l + ((c - x0) / (x1 - x0)) * (W - M.l - M.r);
  const Y = (g) => H - M.b - ((g - y0) / (y1 - y0)) * (H - M.t - M.b);
  const crisp = (v) => Math.round(v) + 0.5;

  const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, role: "img",
    "aria-label": "Scatter plot of spectral gap against central charge for 2d CFTs; see the table view for the data." }, host);

  // Grid, ticks, axis titles.
  const grid = svgEl("g", { class: "grid" }, svg);
  for (let i = Math.ceil(x0 * 10); i <= Math.floor(x1 * 10); i++) {
    const c = i / 10, x = crisp(X(c));
    svgEl("line", { x1: x, x2: x, y1: M.t, y2: H - M.b }, grid);
    svgEl("text", { x, y: H - M.b + 20, class: "tick", "text-anchor": "middle" }, grid).textContent = c.toFixed(1);
  }
  for (let i = 0; i <= Math.floor(y1 * 10); i++) {
    const g = i / 10, y = crisp(Y(g));
    svgEl("line", { x1: M.l, x2: W - M.r, y1: y, y2: y, class: g === 0 ? "baseline" : "" }, grid);
    svgEl("text", { x: M.l - 10, y: y + 4, class: "tick", "text-anchor": "end" }, grid).textContent = g.toFixed(1);
  }
  svgEl("text", { x: (M.l + W - M.r) / 2, y: H - 10, class: "axis-title", "text-anchor": "middle" }, svg).textContent = "central charge c";
  svgEl("text", { x: 16, y: (M.t + H - M.b) / 2, class: "axis-title", "text-anchor": "middle",
    transform: `rotate(-90 16 ${(M.t + H - M.b) / 2})` }, svg).textContent = "spectral gap Δgap";

  // Continuous families at c = 1: side-by-side rounded columns, direct-labelled.
  spans.forEach((s, i) => {
    const w = 6, x = X(s.c) + (i - (spans.length - 1) / 2) * (w + 2) - w / 2;
    const yTop = Y(s.gap[1]), yBot = Y(s.gap[0]);
    const dim = LANDSCAPE.family && LANDSCAPE.family !== s.fam.id;
    svgEl("rect", { x, y: yTop, width: w, height: yBot - yTop, rx: 3, class: `span${dim ? " dim" : ""}` }, svg);
    const label = svgEl("text", { x: X(s.c) + (spans.length * (w + 2)) / 2 + 8, y: yTop + 4, class: "direct-label",
      "text-anchor": "start" }, svg);
    label.textContent = /orbifold/i.test(s.fam.id) ? "orbifold branch" : "circle branch";
  });

  // Highlighted family: thin connector through its members, per variant.
  if (LANDSCAPE.family) {
    const mine = points.filter((p) => p.fam?.id === LANDSCAPE.family && p.kind === "member");
    const byVar = new Map();
    mine.forEach((p) => byVar.set(p.member.variant ?? "", [...(byVar.get(p.member.variant ?? "") || []), p]));
    for (const ps of byVar.values()) {
      if (ps.length < 2) continue;
      svgEl("polyline", { points: ps.map((p) => `${X(p.c)},${Y(p.gap)}`).join(" "), class: "connector" }, svg);
    }
  }

  // Points, grouped by exact position so coincident theories share one mark.
  const groups = new Map();
  for (const p of points) {
    if (p.c < cMin - 1e-12 || p.c > x1) continue;
    const k = `${p.c.toFixed(10)}|${p.gap.toFixed(10)}`;
    if (!groups.has(k)) groups.set(k, { c: p.c, gap: p.gap, items: [] });
    groups.get(k).items.push(p);
  }
  const order = { continuous: 0, member: 1, theory: 2 };
  const marks = [...groups.values()].map((g) => {
    g.kind = g.items.map((p) => p.kind).sort((a, b) => order[b] - order[a])[0];
    g.on = !LANDSCAPE.family || g.items.some((p) => p.fam?.id === LANDSCAPE.family || p.link === LANDSCAPE.family);
    g.x = X(g.c);
    g.y = Y(g.gap);
    return g;
  });
  marks.sort((a, b) => a.on - b.on || order[a.kind] - order[b.kind]);
  const layer = svgEl("g", {}, svg);
  for (const g of marks) {
    g.el = svgEl("circle", { cx: g.x, cy: g.y, r: g.on && LANDSCAPE.family ? 5 : 4, class: `dot ${g.kind}${g.on ? "" : " dim"}` }, layer);
  }

  // Hover: nearest mark within 24px (in screen pixels); click opens or pins.
  let active = null, pinned = false;
  const show = (g, clientX, clientY) => {
    if (active && active !== g) active.el.classList.remove("hover");
    active = g;
    g.el.classList.add("hover");
    const items = g.items.map((p) => `<li><a href="#/theory/${encodeURIComponent(p.link)}">${pointLabel(p)}</a></li>`).join("");
    tip.innerHTML = `<div class="tip-value">${tex(`c = ${g.items[0].cs}`)} &nbsp; ${tex(`\\Delta_{\\rm gap} = ${g.items[0].gs}`)}</div><ul>${items}</ul>`;
    tip.hidden = false;
    const box = app.querySelector(".viz-root").getBoundingClientRect();
    const left = Math.min(clientX - box.left + 14, box.width - tip.offsetWidth - 4);
    tip.style.left = `${Math.max(4, left)}px`;
    tip.style.top = `${clientY - box.top + 14}px`;
  };
  const hide = () => {
    if (pinned) return;
    if (active) active.el.classList.remove("hover");
    active = null;
    tip.hidden = true;
  };
  const nearest = (evt) => {
    const pt = svg.createSVGPoint();
    pt.x = evt.clientX;
    pt.y = evt.clientY;
    const p = pt.matrixTransform(svg.getScreenCTM().inverse());
    const scale = svg.getBoundingClientRect().width / W;
    let best = null, bd = (24 / scale) ** 2;
    for (const g of marks) {
      const d = (g.x - p.x) ** 2 + (g.y - p.y) ** 2;
      if (d < bd) [best, bd] = [g, d];
    }
    return best;
  };
  svg.addEventListener("pointermove", (e) => {
    if (pinned) return;
    const g = nearest(e);
    g ? show(g, e.clientX, e.clientY) : hide();
  });
  svg.addEventListener("pointerleave", hide);
  svg.addEventListener("click", (e) => {
    const g = nearest(e);
    if (!g) { pinned = false; hide(); return; }
    const links = new Set(g.items.map((p) => p.link));
    if (links.size === 1) { location.hash = `#/theory/${encodeURIComponent([...links][0])}`; return; }
    pinned = false;
    show(g, e.clientX, e.clientY);
    pinned = true; // several theories here: keep the list open so its links can be clicked
  });
}

/* -------------------------------------------------------- contribute view */

function viewContribute() {
  document.title = "Contribute — QFT Zoo";
  app.innerHTML = `
    <header class="theory-head"><h1>Contribute</h1>
      <p class="lede">The QFT Zoo is maintained in the open on GitHub. Every addition and correction is
      proposed as a pull request or issue and reviewed by the maintainers before it appears here.</p>
    </header>

    <div class="cards">
      <article class="card">
        <h3>Suggest a theory</h3>
        <p>No code needed: fill in a short form with what you know and the references. A maintainer will turn it into an entry.</p>
        <a class="btn" href="${gh.suggest()}" target="_blank" rel="noopener">Open the form</a>
      </article>
      <article class="card">
        <h3>Add or edit an entry on GitHub</h3>
        <p>Use <b>Add a theory</b> (opens GitHub’s editor pre-filled with the template) or <b>Edit this entry</b> on any theory page.
        GitHub forks the repository for you and opens a pull request.</p>
        <a class="btn primary" href="${gh.newTheory()}" target="_blank" rel="noopener">Add a theory</a>
      </article>
      <article class="card">
        <h3>Work locally</h3>
        <p>Fork and clone, then preview your changes:</p>
        <pre><code>pip install -r requirements.txt
python scripts/build.py --serve</code></pre>
        <a class="btn" href="${gh.blob("CONTRIBUTING.md")}" target="_blank" rel="noopener">Contributing guide</a>
      </article>
    </div>

    ${section(
      "format",
      "Data format",
      `<div class="prose"><p>Each theory is one YAML file in
      <a href="${gh.repo()}/tree/${DB.branch}/data/theories" target="_blank" rel="noopener"><code>data/theories/</code></a>,
      validated against <a href="${gh.blob("schema/theory.schema.json")}" target="_blank" rel="noopener">a JSON schema</a>.
      Text fields accept Markdown and LaTeX math (e.g. ${tex("\\Delta_\\sigma = 0.518148806(24)")}). Every number should cite a reference.
      Automated checks run on every pull request, so problems are flagged before review.</p>
      <p>A 2d CFT can also have a torus partition function in
      <a href="${gh.repo()}/tree/${DB.branch}/data/spectra" target="_blank" rel="noopener"><code>data/spectra/</code></a>:
      characters as exact ${tex("q")}-series and the integer (or rational) matrix that combines them
      (<a href="${gh.blob("schema/spectrum.schema.json")}" target="_blank" rel="noopener">schema</a>). The build checks
      ${tex("Z(\\tau) = Z(-1/\\tau)")}, non-negative integer degeneracies, a unique vacuum, and that the lightest
      Virasoro primary matches the theory's ${tex("\\Delta_{\\rm gap}")}. See the
      <a href="${gh.blob("CONTRIBUTING.md")}#spectra-of-2d-cfts" target="_blank" rel="noopener">contributing guide</a>.</p>
      <p>The complete dataset is available as <a href="data/theories.json">one JSON file</a> for use in your own code.</p></div>`
    )}`;
}

/* ---------------------------------------------------------- feedback view */

const FEEDBACK_PREFIX = "[Feedback]";

/** Split an issue-form body into its Page and Comment fields. Other bodies are all comment. */
function parseFeedback(body) {
  const text = body || "";
  const comment = /^###\s*Comment\s*\n+([\s\S]*)$/m.exec(text);
  const page = /^###\s*Page\s*\n+(.*)$/m.exec(text);
  const p = page ? page[1].trim() : "";
  return { page: p === "_No response_" ? "" : p, comment: (comment ? comment[1] : text).trim() };
}

/** Comments are public and unreviewed, so unlike theory data they are shown as plain
 *  text: escaped, with no Markdown, links or images. */
function renderComment(issue) {
  const { page, comment } = parseFeedback(issue.body);
  const target = BY_ID.has(page)
    ? `<a href="#/theory/${encodeURIComponent(page)}">${md(BY_ID.get(page).name, true)}</a>`
    : esc(page);
  const replies = issue.comments ? `${issue.comments} ${issue.comments === 1 ? "reply" : "replies"}` : "Reply";
  return `<article class="comment">
    <p class="comment-meta small muted"><b>${esc(issue.user?.login ?? "unknown")}</b> · ${esc(String(issue.created_at).slice(0, 10))}${
      target ? ` · on ${target}` : ""}${issue.state === "closed" ? " · handled" : ""}</p>
    <p class="comment-body">${esc(comment)}</p>
    <p class="small"><a href="${safeUrl(issue.html_url)}" target="_blank" rel="noopener">${replies} on GitHub</a></p>
  </article>`;
}

function viewFeedback() {
  document.title = "Comments & Feedback — QFT Zoo";
  const all = `${gh.repo()}/issues?q=${encodeURIComponent(`"${FEEDBACK_PREFIX}" in:title`)}`;
  app.innerHTML = `
    <header class="theory-head">
      <h1>Comments &amp; Feedback</h1>
      <p class="lede">This site is a pilot, and your comments decide what changes next: what works, what doesn’t,
        and what you wish it had. Comments are public and need a free GitHub account.</p>
      <p class="actions">
        <a class="btn primary" href="${gh.feedback()}" target="_blank" rel="noopener">Leave a comment</a>
        <a class="btn" href="${all}" target="_blank" rel="noopener">See all on GitHub</a>
      </p>
    </header>
    <section class="block" aria-live="polite"><h2 id="feedback-count">Comments</h2>
      <div id="feedback-list"><p class="muted">Loading comments…</p></div></section>`;

  fetch(`https://api.github.com/repos/${DB.repo}/issues?state=all&sort=created&direction=desc&per_page=100`, {
    headers: { Accept: "application/vnd.github+json" },
  })
    .then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    })
    .then((issues) => {
      const list = document.getElementById("feedback-list");
      if (!list) return; // the reader has moved to another page
      const items = issues.filter((i) => !i.pull_request && String(i.title).startsWith(FEEDBACK_PREFIX));
      document.getElementById("feedback-count").textContent = `Comments (${items.length})`;
      list.innerHTML = items.length
        ? items.map(renderComment).join("")
        : `<p class="muted">No comments yet. Yours could be the first.</p>`;
    })
    .catch(() => {
      const list = document.getElementById("feedback-list");
      if (list) list.innerHTML = `<p class="muted">Comments couldn’t be loaded right now.
        <a href="${all}" target="_blank" rel="noopener">Read them on GitHub</a> instead.</p>`;
    });
}

function viewNotFound(msg = "Page not found.") {
  document.title = "Not found — QFT Zoo";
  app.innerHTML = `<header class="theory-head"><h1>Not found</h1><p class="lede">${esc(msg)}</p>
    <p><a class="btn" href="#/catalogue">Back to all theories</a></p></header>`;
}

/* ----------------------------------------------------------------- router */

/** Set the catalogue filters from a #/catalogue/<key>:<value> link. */
function applyCatalogueLink(arg) {
  const i = arg.indexOf(":");
  if (i < 0) return;
  const [key, value] = [arg.slice(0, i), arg.slice(i + 1)];
  filters.q = key === "q" ? value : "";
  filters.d = new Set(key === "d" ? [+value] : []);
  filters.tags = new Set(key === "tag" ? [value] : []);
  filters.spectrum = key === "spectrum";
}

function route() {
  const [page, arg] = location.hash.replace(/^#\/?/, "").split("/");
  if (!page) viewHome();
  else if (page === "catalogue") {
    if (arg) applyCatalogueLink(decodeURIComponent(arg));
    viewBrowse();
  } else if (page === "tables") viewTables();
  else if (page === "feedback") viewFeedback();
  else if (page === "theory" && arg) viewTheory(decodeURIComponent(arg));
  else if (page === "contribute") viewContribute();
  else if (page === "landscape") viewLandscape();
  else viewNotFound();
  document.querySelectorAll("[data-nav]").forEach((a) =>
    a.classList.toggle("active", a.dataset.nav === (page === "theory" ? "catalogue" : page))
  );
  window.scrollTo(0, 0);
}

app.addEventListener("change", (e) => {
  if (e.target.id === "spectrum-member" && SPEC_STATE.t) showSpectrum(SPEC_STATE.t, +e.target.value);
});

// Clicks shared by all views: citation links, tag pills, "show more" members / rows.
app.addEventListener("click", (e) => {
  const jump = e.target.closest("[data-jump]");
  if (jump) {
    document.getElementById(`sec-${jump.dataset.jump}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }
  const specMember = e.target.closest("[data-spec-member]");
  if (specMember && SPEC_STATE.t) {
    const sel = document.getElementById("spectrum-member");
    if (sel) sel.value = specMember.dataset.specMember;
    showSpectrum(SPEC_STATE.t, +specMember.dataset.specMember);
    document.getElementById("sec-spectrum")?.scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }
  const specMore = e.target.closest("[data-spec-more]");
  if (specMore && SPEC_STATE.S) {
    const key = specMore.dataset.specMore;
    SPEC_STATE.full.add(key);
    document.getElementById("spectrum-body").innerHTML = renderSpectrum(SPEC_STATE.S);
    document.querySelector(`[data-spec-table="${key}"]`)?.scrollIntoView({ block: "start" });
    return;
  }
  const more = e.target.closest("[data-more-members]");
  if (more) {
    more.closest("section").querySelectorAll("tr.extra").forEach((tr) => (tr.hidden = false));
    more.parentElement.remove();
    return;
  }
  const cite = e.target.closest("[data-ref]");
  if (cite) {
    e.preventDefault();
    const li = document.getElementById(`ref-${cite.dataset.ref}`);
    if (li) {
      li.scrollIntoView({ behavior: "smooth", block: "center" });
      li.classList.remove("flash");
      void li.offsetWidth;
      li.classList.add("flash");
    }
    return;
  }
  const pill = e.target.closest("[data-tag]");
  if (pill) {
    const tag = pill.dataset.tag;
    if (document.getElementById("rows")) {
      toggle(filters.tags, tag);
    } else {
      filters.q = "";
      filters.d.clear();
      filters.tags = new Set([tag]);
      location.hash = "#/catalogue";
    }
  }
});

// "no-cache": revalidate with GitHub Pages (cheap 304 if unchanged) so new data shows up at once.
fetch("data/theories.json", { cache: "no-cache" })
  .then((r) => {
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  })
  .then((db) => {
    DB = db;
    for (const t of DB.theories) {
      t._search = searchText(t);
      BY_ID.set(t.id, t);
    }
    document.getElementById("repo-link").href = gh.repo();
    document.getElementById("footer").innerHTML =
      `QFT Zoo — an open catalogue of quantum field theories. ` +
      `<a href="${gh.repo()}" target="_blank" rel="noopener">Source &amp; data on GitHub</a> · ` +
      `${DB.theories.length} theories · built ${esc(DB.generated)}`;
    window.addEventListener("hashchange", route);
    route();
  })
  .catch((err) => {
    app.innerHTML = `<div class="error"><p><b>Could not load the data</b> (${esc(err.message)}).</p>
      <p>If you opened <code>index.html</code> directly from disk, run
      <code>python scripts/build.py --serve</code> and visit <code>http://localhost:8000</code> instead.</p></div>`;
  });
