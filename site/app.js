"use strict";
/* QFT Zoo front end: loads data/theories.json (built by scripts/build.py) and
   renders a catalogue view and one page per theory, using hash routing:
     #/                 home: a directory of everything on the site
     #/catalogue        searchable catalogue; #/catalogue/<k>:<v> opens it filtered
                        (k = d, tag, q or spectrum)
     #/tables           summary tables, grouped by dimension and type
     #/flows            RG flows between the theories
     #/feedback         comments on the site, read live from GitHub issues
     #/theory/<id>      a theory (with its spectrum, if data/spectra has one)
     #/operation/<id>   how composite theories are built (direct sum, ...)
     #/landscape        2d CFTs in the (c, gap) plane
     #/contribute       how to contribute
     #/methods          the methods behind the data, with their abbreviations;
                        #/methods/<abbr> highlights one                     */

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

let DB = null; // { generated, repo, branch, template, theories: [...], methods: [...] }
const BY_ID = new Map();
const METHODS = new Map(); // abbr -> method (data/methods.yaml, with usage counts from build.py)
const filters = { q: "", d: new Set(), tags: new Set(), spectrum: false };
const app = document.getElementById("app");

/* ------------------------------------------------------------------ helpers */

const esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

/** A family parameter is a plain identifier (schema); spell Greek names as LaTeX commands. */
const GREEK = new Set(["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta", "kappa", "lambda", "mu", "nu", "xi", "rho", "sigma", "tau", "phi", "chi", "psi", "omega"]);
const paramTex = (p) => (GREEK.has(p) ? `\\${p}` : p);

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
/* Citations. A page keeps one numbered reference list (CITES) and every citation on it is a bracketed number
 * linked to that list, shown at the bottom of the page. Prose cites with [@key] or [@key, Sec. 4.1.1] (several:
 * [@a; @b, Eq. (3)]); build.py prefixes each key with its entry's id ([@ising-3d/kos2016]), so a note shown on
 * another page still finds its reference. Data rows cite through `refs`, each "key" or "key, Table 2". */
let CITES = null;
let CITE_OWNER = null; // entry whose unprefixed keys a citation means (build.py prefixes them all)
function citeStart(seed = []) {
  CITES = { list: [], num: new Map() };
  seed.forEach(([id, key]) => citeNum(id, key));
}
function citeNum(id, key) {
  if (!CITES) return null;
  const k = `${id}/${key}`;
  if (!CITES.num.has(k)) {
    const r = (BY_ID.get(id)?.references || []).find((x) => x.key === key);
    if (!r) return null;
    // The same paper under another entry's key keeps its number.
    const same = CITES.list.findIndex(({ r: o }) => (r.arxiv && o.arxiv === r.arxiv) || (r.doi && o.doi === r.doi));
    if (same >= 0) CITES.num.set(k, same + 1);
    else { CITES.list.push({ id, r }); CITES.num.set(k, CITES.list.length); }
  }
  return CITES.num.get(k);
}
const splitRef = (k) => { const i = String(k).indexOf(","); return i < 0 ? [String(k).trim(), ""] : [k.slice(0, i).trim(), k.slice(i + 1).trim()]; };
/** One bracket for several sources: parts = [[entry id, key, locator html]]. */
function citeBracket(parts) {
  if (!CITES) // no reference list on this page (e.g. a summary in the catalogue): point to the entry's page
    return parts.length ? `<a class="cite" href="#/theory/${encodeURIComponent(parts[0][0])}">[ref]</a>` : "";
  const bits = parts.map(([id, key, loc]) => {
    const n = citeNum(id, key);
    const label = `${n ?? "?"}${loc ? `, ${loc}` : ""}`;
    return n == null
      ? `<span class="cite-missing" title="${esc(`${id}: no reference ${key}`)}">${esc(key)}${loc ? `, ${loc}` : ""}</span>`
      : `<a class="cite" href="#" data-ref="${esc(`${id}/${key}`)}">${label}</a>`;
  });
  return bits.length ? `<span class="cite-group">[${bits.join("; ")}]</span>` : "";
}
/** Citations from a data row's refs list (keys of entry `id`). */
const citeRefs = (id, keys) => (keys?.length ? citeBracket(keys.map((k) => { const [key, loc] = splitRef(k); return [id, key, loc ? md(loc, true) : ""]; })) : "");
/** The page's reference list, for its last section. */
const citeList = () => `<ol class="refs">${CITES.list.map(({ id, r }) => refItem(r, id)).join("")}</ol>`;

function md(src, inline = false) {
  if (src == null || src === "") return "";
  const stash = [];
  const hold = (html) => `${stash.push(html) - 1}`;
  const s = String(src)
    .replace(/\$\$([\s\S]+?)\$\$/g, (_, m) => hold(tex(m, true)))
    .replace(/(^|[^\\])\$((?:\\.|[^$\\\n]|\n(?!\n))+?)\$/g, (_, pre, m) => pre + hold(tex(m)))
    .replace(/\\\$/g, "$")
    .replace(/\[(@[^\]]*)\]/g, (m, body) => {
      const parts = body.split(";").map((p) => p.match(/^\s*@(?:([a-z0-9-]+)\/)?([A-Za-z0-9_:-]+)(?:\s*,\s*(\S[^]*?))?\s*$/));
      if (parts.some((p) => !p)) return m;
      const unhold = (x) => x.replace(/\uE000(\d+)\uE001/g, (_, i) => stash[+i]);
      return hold(citeBracket(parts.map(([, id, key, loc]) => [id ?? CITE_OWNER, key, loc ? unhold(marked.parseInline(loc)) : ""])));
    });
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

/** A row's `method`: 'MC-BC, isotropic' -> the abbreviation linked to the Methods page (full name on hover),
    then the qualifier. Legacy free text (not starting with a listed abbreviation) is shown as it is. */
function methodHtml(value) {
  const s = String(value ?? "");
  const i = s.indexOf(",");
  const abbr = (i < 0 ? s : s.slice(0, i)).trim();
  const m = METHODS.get(abbr);
  if (!m) return esc(s);
  const q = i < 0 ? "" : s.slice(i + 1).trim();
  return `<a class="method" href="#/methods/${encodeURIComponent(abbr)}" title="${esc(plain(m.name))}">${esc(abbr)}</a>${
    q ? `<span class="method-q">, ${esc(q)}</span>` : ""}`;
}

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

/** Wikipedia articles for the standard names used in `symmetry.spacetime` (CONTRIBUTING.md, Spacetime symmetry). */
const SPACETIME_LINKS = [
  ["superconformal group", "Superconformal_algebra"],
  ["superconformal symmetry", "Superconformal_algebra"],
  ["super-Virasoro", "Super_Virasoro_algebra"],
  ["conformal group", "Conformal_group"],
  ["conformal symmetry", "Conformal_symmetry"],
  ["Poincaré group", "Poincar%C3%A9_group"],
  ["Virasoro", "Virasoro_algebra"],
  ["parity", "Parity_(physics)"],
  ["topological", "Topological_quantum_field_theory"],
];
const SPACETIME_RE = new RegExp(SPACETIME_LINKS.map(([w]) => w).join("|"), "gi");
/** Link the first occurrence of each standard name, outside $...$ math. */
function linkSpacetime(src) {
  const used = new Set();
  return String(src)
    .split(/(\$[^$]*\$)/)
    .map((part, i) =>
      i % 2
        ? part
        : part.replace(SPACETIME_RE, (m) => {
            const k = m.toLowerCase();
            if (used.has(k)) return m;
            used.add(k);
            const page = SPACETIME_LINKS.find(([w]) => w.toLowerCase() === k)[1];
            return `[${m}](https://en.wikipedia.org/wiki/${page})`;
          })
    )
    .join("");
}

/** The Spacetime row: "Euclidean G_E · Lorentzian G_L — name and qualifiers" (CONTRIBUTING.md, Spacetime symmetry). */
function spacetimeHtml(s) {
  const groups = [
    ["Euclidean", s.euclidean],
    ["Lorentzian", s.lorentzian],
  ]
    .filter(([, g]) => g)
    .map(([k, g]) => `<span class="muted">${k}</span> ${md(g, true)}`)
    .join(" · ");
  const name = s.spacetime && md(linkSpacetime(s.spacetime), true);
  return [groups, name].filter(Boolean).join(" — ");
}

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
          <a class="portal-btn" href="#/flows">RG Flows</a>
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
            item("#/methods", "Methods and their abbreviations", DB.methods?.length),
            item(gh.suggest(), "Suggest a theory", null, ext),
            item(`${gh.repo()}/issues/new?template=correction.yml`, "Report a problem", null, ext),
            item("https://arxiv.org/list/hep-th/recent", "arXiv hep-th", null, ext),
            item("https://inspirehep.net/", "INSPIRE", null, ext),
            item("https://www.math.ksu.edu/~gerald/voas/", "VOA database", null, ext),
            item("https://anyonatlas.org", "Anyon Atlas (3d TQFTs)", null, ext),
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
    [t.id, t.name, ...(t.aliases || []), t.summary, ...(t.tags || []), s.global, s.gauge, s.spacetime, s.euclidean, s.lorentzian, `${t.d}d`, `d=${t.d}`].join(" ")
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

/* ------------------------------------------------------------ theory data */

// A theory's quantities are shown by kind: central charges and free energies, anomalies, OPE
// coefficients, critical exponents, other. A quantity's kind is its `category`, or else inferred
// from its key, symbol and description (quantityCategory); `ope` is never inferred. Rows with the same
// symbol that describe the same quantity (other papers or methods) are one item: the most precise first,
// the rest folded. Three-point functions are their own data (`three_point_functions`, docs/THREE_POINT.md), shown by
// opeItems in the `ope` section, "Three-point functions".
const wiki = (page, text) => `<a href="https://en.wikipedia.org/wiki/${page}" target="_blank" rel="noopener">${text}</a>`;
const QCATS = {
  central: {
    id: "central-charges",
    title: "Central charges and free energy",
    intro: () => `Normalizations of the stress tensor and of conserved currents (${wiki("Central_charge", "central charges")}), and free energies.`,
  },
  anomaly: {
    id: "anomalies",
    title: "Anomalies",
    intro: () => `${wiki("Conformal_anomaly", "Conformal (Weyl) anomalies")} of the stress-tensor trace and ${wiki("%27t_Hooft_anomaly", "'t Hooft anomalies")} of global symmetries.`,
  },
  ope: {
    id: "three-point",
    title: "Three-point functions",
    intro: (triplets, d) =>
      triplets && d === 2
        ? `In 2d the ${wiki("Conformal_field_theory#Dependence_on_field_positions", "three-point function")} of three primaries is fixed by conformal symmetry up to one coefficient; each row gives it. Lightest operators first.`
        : triplets
        ? `A ${wiki("Conformal_field_theory#Dependence_on_field_positions", "three-point function")} of primary operators is a sum of coefficients times structures fixed by conformal symmetry: each row is the coefficient of one structure, named in its Structure column and defined below the table. Lightest operators first; values in different structures are different numbers and are never compared.`
        : `Three-point data: coefficients of ${wiki("Conformal_field_theory#Dependence_on_field_positions", "three-point functions")} and the ${wiki("Operator_product_expansion", "operator product expansion")}.`,
  },
  exponent: {
    id: "exponents",
    title: "Critical exponents",
    intro: (rel) =>
      `${wiki("Critical_exponent", "Critical exponents")} are derived quantities: ${
        rel ? "most follow from scaling dimensions of operators, by the relation shown." : "they follow from scaling dimensions of operators."}`,
  },
  other: { id: "data-other", title: "Other data", intro: () => "" },
};
const QCAT_ORDER = ["central", "anomaly", "ope", "exponent", "other"];

function quantityCategory(q, t) {
  if (q.category) return q.category;
  const s = String(q.symbol).trim();
  const d = q.description || "";
  if (q.key === "a") return "anomaly";
  if (q.key === "c" || q.key === "C_T" || q.key === "F") return "central";
  if (q.key === "gap") return "other";
  // a, c (4d) and a, c_i (6d) are Weyl-anomaly coefficients; in 2d, c is the Virasoro central charge.
  if (/\banomal(y|ies)\b/i.test(d) || (t.d >= 4 && /^(a|c|a\s*=\s*c|c_[1-3])$/.test(s)) || /^\[?I_\d/.test(s)) return "anomaly";
  if (/^(C_T|C_J|k(?![A-Za-z])|\\tau_|F(?![A-Za-z])|\\tilde\s*F|Z_\{?S|\(c_L|c_\{\\rm eff\}|c$)/.test(s) ||
      /central charge|two-point coefficient|free energy/i.test(d)) return "central";
  if (/exponent|anomalous dimension|fractal dimension|RG eigenvalue/i.test(d) ||
      /^(\\nu|\\eta|\\omega|\\beta|\\gamma|\\delta|\\theta|1\/\\nu|d_[fFH])(?![A-Za-z])/.test(s)) return "exponent";
  return "other";
}

/** LaTeX compared loosely: no spaces, primes as ', \varepsilon as \epsilon. */
const normTex = (s) =>
  String(s ?? "")
    .replace(/\s+/g, "")
    .replace(/\^\{((?:\\prime)+)\}/g, (_, p) => "'".repeat(p.length / 6))
    .replace(/\^\\prime/g, "'")
    .replace(/\\varepsilon/g, "\\epsilon");

/** A value as a range: { x, e } (central value and stated error; e = 0 when exact), { hi } or { lo } (a one-sided
 *  bound), or null when it states no error ("1.41", "\approx 0.86", a series in 1/N). */
function valueRange(value, method) {
  const s = String(value ?? "").trim().replace(/\\[,;: ]|~/g, " ").replace(/\s+/g, " ");
  const N = "(-?\\d*\\.?\\d+)";
  let m;
  if ((m = new RegExp(`^${N}\\((\\d+)\\)$`).exec(s))) return { x: +m[1], e: +m[2] * 10 ** -((m[1].split(".")[1] || "").length) };
  if ((m = new RegExp(`^${N} ?\\\\pm ?${N}$`).exec(s))) return { x: +m[1], e: Math.abs(+m[2]) };
  if ((m = new RegExp(`^${N} ?(?:\\\\text\\{[–-]\\}|–|--) ?${N}$`).exec(s)) || (m = new RegExp(`^\\[${N}, ?${N}\\]$`).exec(s)))
    return +m[2] >= +m[1] ? { x: (+m[1] + +m[2]) / 2, e: (+m[2] - +m[1]) / 2 } : null;
  if ((m = new RegExp(`^(?:\\\\leq?|≤|<) ?${N}$`).exec(s))) return { hi: +m[1] };
  if ((m = new RegExp(`^(?:\\\\geq?|≥|>) ?${N}$`).exec(s))) return { lo: +m[1] };
  if (/^-?\d+(?:\/\d+)?$|^\\[dt]?frac\{-?\d+\}\{\d+\}$/.test(s.replace(/ /g, "")) || (/^exact/i.test(method || "") && new RegExp(`^${N}$`).test(s)))
    return { x: leadingNumber(s.replace(/ /g, "")), e: 0 };
  return null;
}

/** Relative uncertainty of a value: 0 for an exact expression, Infinity if unknown. */
function relError(q) {
  const s = String(q.value);
  if (/^exact/i.test(q.method || "")) return 0;
  const r = valueRange(q.value, q.method);
  if (r && "x" in r) return r.e / (Math.abs(r.x) || 1);
  let m = s.match(/(-?\d*\.?\d+)\((\d+)\)/);
  if (m) return (+m[2] * 10 ** -((m[1].split(".")[1] || "").length)) / (Math.abs(+m[1]) || 1);
  m = s.match(/(-?\d*\.?\d+)\s*\\pm\s*(\d*\.?\d+)/);
  if (m) return +m[2] / (Math.abs(+m[1]) || 1);
  if (!/\d\.\d/.test(s) && !/\\(approx|sim|lesssim|gtrsim|leq?|geq?)|[<>≈~]|\.\.\./.test(s)) return 0;
  return Infinity;
}

/** A rigorous determination: the bootstrap's bounds and islands (bare `CB`) or a qualifier saying "rigorous". */
function isRigorous(method) {
  const s = String(method ?? "");
  if (/non-?rigorous|not rigorous|estimate/i.test(s)) return false;
  return /\brigorous\b/i.test(s) || s.split(",")[0].trim() === "CB";
}

/** Several determinations of one quantity or operator, best first: exact; then rigorous intervals, the narrowest
 *  first (a rigorous interval is never folded under a non-rigorous estimate that quotes a smaller error); then
 *  everything else by relative error; ties keep the data order. `val` and `meth` give a row's value and method. */
function orderDets(rows, val, meth = (q) => q.method) {
  const rank = (q) => {
    const e = relError({ value: val(q), method: meth(q) });
    return e === 0 ? [0, 0] : Number.isFinite(e) && isRigorous(meth(q)) ? [1, e] : [2, e];
  };
  const r = new Map(rows.map((q, i) => [q, [...rank(q), i]]));
  return [...rows].sort((a, b) => {
    const [x, y] = [r.get(a), r.get(b)];
    return x[0] - y[0] || x[1] - y[1] || x[2] - y[2];
  });
}

/** Does determination b disagree with the preferred one a beyond their stated errors? Two values disagree when
 *  they differ by more than twice their combined error (errors added in quadrature, i.e. beyond 2σ); a value and a
 *  one-sided bound when the value lies more than twice its error beyond the bound. Values without a stated error
 *  are not judged. Returns a short explanation, or "". */
function disagreement(a, b, val) {
  const [p, q] = [valueRange(val(a), a.method), valueRange(val(b), b.method)];
  if (!p || !q) return "";
  const fmt = (x) => (x >= 10 ? x.toFixed(0) : x.toPrecision(2));
  if ("x" in p && "x" in q) {
    const d = Math.abs(p.x - q.x), s = Math.hypot(p.e, q.e);
    if (s === 0) return d > 1e-12 * Math.max(1, Math.abs(p.x)) ? "differs from the exact value shown first" : "";
    return d > 2 * s ? `differs from the value shown first by ${fmt(d / s)}× the combined stated error` : "";
  }
  const [v, bd, vFirst] = "x" in p ? [p, q, true] : "x" in q ? [q, p, false] : [null];
  if (!v) return "";
  const out = "hi" in bd ? v.x - 2 * v.e > bd.hi : v.x + 2 * v.e < bd.lo;
  if (!out) return "";
  return vFirst ? "the value shown first lies more than twice its error beyond this bound" : "lies more than twice its error beyond the bound shown first";
}

/** "+n more" for a folded item, with a warning when some folded determination disagrees with the one shown. */
function detsButton(id, n, nbad) {
  return `<div class="sub"><button type="button" class="linkish dets" data-dets="${id}" data-n="${n}" aria-expanded="false"
    title="Other determinations (papers or methods)">+${n} more</button>${nbad
      ? ` <span class="badge warn" title="${nbad} of them disagree${nbad > 1 ? "" : "s"} with the value shown, beyond twice the combined stated error">${nbad} disagree${nbad > 1 ? "" : "s"}</span>` : ""}</div>`;
}
const disagreeBadge = (why) => (why ? ` <span class="badge warn" title="${esc(why)}">disagrees</span>` : "");

/** "Edge exponent" for "Edge exponent, from the dimer density": the description up to its first , : ; or ( outside
 *  math (so "$U(2)_1 \times U(2)_{-1}$" and "$U(2)_2 \times U(2)_{-2}$" stay apart). */
const descBase = (d) => String(d ?? "").replace(/\$[^$]*\$/g, (m) => m.replace(/[,:;(]/g, " ")).split(/[,:;(]/)[0].trim().toLowerCase();
// "N = 25", "$k = 1$": a description that fixes a parameter describes a different quantity.
const fixesParameter = (d) => /(^|[\s$(])([A-Za-z]|\\[a-zA-Z]+)\s*=\s*-?\d+(\.\d+)?\s*($|[$,;)])/.test(String(d ?? ""));

function sameQuantity(a, b) {
  const da = String(a.description ?? "").trim(), db = String(b.description ?? "").trim();
  if (da === db || /^same\b/i.test(db)) return true;
  return descBase(da) !== "" && descBase(da) === descBase(db) && !fixesParameter(da) && !fixesParameter(db);
}

/** Quantities as items { cat, rows }: rows of one quantity (same symbol, same description up to the
 *  method), best first (orderDets); items in the order of their first row. */
function quantityItems(t) {
  const items = [];
  for (const q of t.quantities || []) {
    const cat = quantityCategory(q, t);
    const it = items.find((i) => i.cat === cat && normTex(i.rows[0].symbol) === normTex(q.symbol) && sameQuantity(i.rows[0], q));
    if (it) it.rows.push(q);
    else items.push({ cat, rows: [q] });
  }
  for (const it of items) it.rows = orderDets(it.rows, (q) => q.value);
  return items;
}

/** The math in a description that relates an exponent to scaling dimensions ("$\nu = 1/(3-\Delta_\epsilon)$"). */
function exponentRelation(it) {
  const own = it.rows.find((q) => q.relation);
  if (own) return { tex: own.relation };
  const sym = normTex(it.rows[0].symbol);
  for (const q of it.rows)
    for (const m of String(q.description ?? "").matchAll(/\$([^$]+)\$/g)) {
      const x = m[1], lhs = normTex(x.split("=")[0]);
      if (/\\(propto|sim)\b/.test(x)) continue;
      if ([...x.matchAll(/\\Delta(_\{[^}]*\}|_\\?[A-Za-z0-9]+)?/g)].some(([D]) => normTex(D) !== sym)) return { tex: /=/.test(x) ? x : `${it.rows[0].symbol} = ${x}`, src: m[0] };
      if (/=/.test(x) && lhs === sym) return { tex: x, src: m[0] };
    }
  return null;
}

let DET_SEQ = 0;

/* Three-point functions (docs/THREE_POINT.md). Data: `three_point_functions`, one item per unordered triple of
   operators, each value the coefficient of one structure: a standard one (data/three_point_structures.yaml,
   DB.three_point_structures) or one the entry defines in `three_point_structures`, in its source's notation; a value
   whose structure assumes another order of the operators gives it (`order`). Presentation, by rule:
   - one item per triple, labelled <O1 O2 O3> with its operators lightest first (ties in data order), whatever order
     the sources used; a value whose structure assumes another order says so in its Structure cell;
   - items ordered by the dimensions of their operators (sorted, lightest first, compared in turn; operators named by
     label sort last), ties in data order;
   - in a triplet, each element of a basis of several structures (a structure with `basis`, e.g. n_B and n_F of
     <TTT>) is a coefficient of its own, on its own line; all other values are one line (one coefficient, possibly
     determined in different bases);
   - in a line, values are grouped by structure (standard structures in the order of data/three_point_structures.yaml,
     then the entry's in its order), best first within a structure (orderDets); the first value shows, the rest fold;
   - the disagreement badge compares a value only with the best value in the same structure (and operator order);
   - no per-row coefficient symbol: the three-point function and the structure say what the number is; a value that
     is the square or the modulus of the coefficient (`value_of`) says so in its value cell;
   - each value names its structure in its row, except a default standard structure (three scalars, unit-normalized),
     which the section states once (OPE_LABEL_DEFAULTS = true labels those too);
   - the structures used on the page are defined once, at the top of the section. */
const OPE_LABEL_DEFAULTS = true; // David: every value shows its structure, the standard scalar one included

/** The structures an entry's values may name, id -> structure (with `own` for the entry's and `order`). */
function opeStructures(t) {
  const out = new Map();
  for (const s of DB.three_point_structures || []) out.set(s.id, { ...s, own: false, order: out.size });
  for (const s of t.three_point_structures || []) out.set(s.id, { ...s, own: true, order: out.size });
  return out;
}

/** An operator of a three-point function as LaTeX: its name, or its label. */
const opeOp = (o) => (typeof o === "string" ? o : o.label || "");
/** ⟨O1 O2 O3⟩ for operators in the given order. */
const opeBracket = (ops) => `\\langle ${ops.map(opeOp).join("\\,")}\\rangle`;

function opeItems(t) {
  const sts = opeStructures(t);
  const dim = new Map();
  for (const o of t.operators || []) {
    const v = leadingNumber(o.Delta);
    const D = Number.isFinite(v) ? v : Infinity;
    if (!dim.has(o.name) || dim.get(o.name) > D) dim.set(o.name, D);
  }
  const D = (o) => (typeof o === "string" ? dim.get(o) ?? Infinity : Infinity);
  const items = (t.three_point_functions || []).map((c, i) => {
    // The label: the operators lightest first, ties in data order, whatever order the sources used.
    const canon = c.operators.map((o, j) => [o, j]).sort((a, b) => D(a[0]) - D(b[0]) || a[1] - b[1]).map(([o]) => o);
    const ck = canon.map(opeOp).join("|");
    const lines = new Map();
    for (const v of c.values) {
      const st = sts.get(v.structure);
      const k = st.basis ? `s:${st.id}` : "one";
      if (!lines.has(k)) lines.set(k, []);
      // The operator order this value's structure assumes; shown when it is not the label's (a sign can depend on it).
      const ord = v.order || c.operators;
      const ok = ord.map(opeOp).join("|");
      // One letter for every coefficient (David: "f vs lambda is not really a thing"): λ, or a basis element's own
      // name (⟨TTT⟩'s n_B, n_F). The page shows it only where a value is its square or modulus; the data keeps the
      // source's letter (`symbol`).
      lines.get(k).push({ ...v, symbol: st.basis && st.symbol ? st.symbol : "\\lambda", _st: st, _ord: ok === ck ? null : ord, _ok: ok });
    }
    const ordered = [...lines.values()].map((vals) => {
      const byst = new Map();
      for (const r of vals) (byst.get(r._st) ?? byst.set(r._st, []).get(r._st)).push(r);
      return [...byst.entries()].sort(([a], [b]) => a.order - b.order).flatMap(([, rs]) => {
        const best = orderDets(rs, (q) => q.value);
        // Compared only with the best value in the same structure and operator order.
        best.forEach((r) => (r._best = best.find((b) => b._ok === r._ok)));
        return best;
      });
    }).sort((a, b) => a[0]._st.order - b[0]._st.order);
    const key = canon.map(D);
    return { cat: "ope", ope: true, lines: ordered, rows: ordered.flat(), ops: canon, label: opeBracket(canon), key, i };
  });
  return items.sort((a, b) => {
    for (let j = 0; j < 3; j++) if (a.key[j] !== b.key[j]) return a.key[j] < b.key[j] ? -1 : 1;
    return a.i - b.i;
  });
}

/** The label of a structure in a row: its name, else the citation of the formula that defines it; "" for a default
 *  standard structure (unless OPE_LABEL_DEFAULTS). Clicking it shows the structure's definition at the top. */
function opeLabel(t, st) {
  if (!st || (st.default && !OPE_LABEL_DEFAULTS)) return "";
  return `<div class="ope-st"><button type="button" class="linkish" data-ope-st="${esc(st.id)}" title="Show the definition of this structure">${
    st.name ? md(st.name, true) : "structure"}</button></div>`; // its citation is in the Structures list below
}

/** The definitions of the structures that the items use, once for the section, in structure order (the standard ones
 *  first, a default one marked as carrying no label), each with its symbol, label, definition, its embedding-space form
 *  (`embedding`, in the notation of Costa, Penedones, Poland and Rychkov; docs/THREE_POINT.md 1.4) and stated relations. */
function opeStructuresHtml(t, items, title = "Structures") {
  if (t.d === 2) return ""; // unique structure in 2d: nothing to define
  const used = [...new Set(items.filter((it) => it.ope).flatMap((it) => it.rows.map((r) => r._st)))].sort((a, b) => a.order - b.order);
  if (!used.length) return "";
  const li = (st) => {
    // What the structure is, shown in the line: its name, then the structure written out (`form`, else its
    // single-monomial `embedding`), then the citation as the source of the convention. Only prose folds.
    const math = st.form || st.embedding;
    const cite = st.ref ? ` ${citeRefs(t.id, [st.ref])}` : "";
    // An `embedding` that is not the line's formula (the structure has its source's own `form`) folds with the prose.
    const emb = ""; // the page shows the source's form only; `embedding` and `derivation` stay in the data
    // A label that is itself the structure's numerator (pure math, e.g. $V_3^\ell$, $\delta_{ij}$) already says what it
    // is: then the full formula folds into "details" too. A named structure ("parity-even ⟨TTε⟩") shows its formula.
    const numeratorLabel = /^\s*\$[^$]+\$\s*$/.test(st.name || "");
    const formula = math ? `<div class="ope-st-formula">${tex(math, true)}</div>` : "";
    const more = [numeratorLabel ? formula : "", st.description ? md(st.description, true) : "", emb, st.relation ? md(st.relation, true) : ""].filter(Boolean).join(" ");
    return `<li id="ope-st-${esc(st.id)}">${st.name ? `<b>${md(st.name, true)}</b>` : ""}${!numeratorLabel && math ? `${st.name ? ": " : ""}${tex(math)}` : ""}${cite}${
      more ? ` <details class="ope-st-more"><summary>details</summary>${more}</details>` : ""}</li>`;
  };
  return `<div class="ope-structures small"><p class="ope-structures-title">${title}</p><ul>${used.map(li).join("")}</ul></div>`;
}


/** One table of quantity items (and OPE items). With `cat`, the table is shaped for that kind: exponents get a
 *  relation column. An item's lines each show their first row; the other rows of a line fold below it. */
function quantityTable(t, items, cat, source) {
  // Keyed by the item's rows: the table draws each item from a copy ({ ...it, id }), whose rows are the same array.
  const rel = new Map(cat === "exponent" ? items.map((it) => [it.rows, exponentRelation(it)]) : []);
  // OPE values name the structure they multiply in a column of its own.
  // In 2d a three-point function of primaries has a unique structure: no Structure column there.
  const hasOpe = items.some((it) => it.ope) && t.d !== 2;
  const hasRel = [...rel.values()].some(Boolean);
  // A three-point table shows its Notes column only when some row has a note or description.
  const hasNotes = cat !== "ope" || items.some((it) => it.rows.some((q) => q.note || (!it.ope && q.description)));
  const describe = (q, it) => {
    let d = String(q.description ?? "");
    const r = rel.get(it.rows);
    if (r?.src) d = d.replace(r.src, "").replace(/\s*[,:;]?\s*$/, "").replace(/\s*,\s*,/, ",").replace(/^\s*[,:;]\s*/, "").replace(/\s+([,;.])/g, "$1").replace(/,\s*\(/, " (");
    if (cat === "exponent" && /^critical exponent\.?$/i.test(d.trim())) d = "";
    // In the one-table layout (no OPE section), an OPE value says what it is.
    if (!cat && it.ope && !d.trim()) d = "coefficient in a three-point function";
    return d.trim();
  };
  // Disagreement: with the line's first row; for an OPE value, with the best value in its own structure.
  const against = (it, line, r) => (it.ope ? r._best : line[0]);
  const bad = (it, line, r) => (r === against(it, line, r) ? "" : disagreement(against(it, line, r), r, (x) => x.value));
  const row = (q, it, line, head) => {
    const d = describe(q, it);
    const desc = head || d !== describe(line[0], it) ? md(d, true) : "";
    const n = line.length - 1;
    const more = head && n ? detsButton(it.id, n, line.filter((r) => bad(it, line, r)).length) : head ? "" : disagreeBadge(bad(it, line, q));
    // A three-point function is labelled once, on its first row; other quantities show their symbol per line.
    const sym = it.ope ? (head && line === it.lines[0] ? tex(it.label) : "") : head ? tex(q.symbol) : "";
    // The structure, and the operator order it assumes when that is not the label's.
    const stCell = !it.ope ? "" : `${head || q._st !== line[0]._st || q._ord ? opeLabel(t, q._st) : ""}${
      q._ord ? `<div class="sub">in the order ${tex(opeBracket(q._ord))}</div>` : ""}`;
    // A value that is the square or the modulus of the coefficient says so.
    const of = it.ope && q.value_of ? `${tex(q.value_of === "square" ? `${q.symbol}^2` : `|${q.symbol}|`)} = ` : "";
    const valueCell = `${of ? `<span class="value-of">${of}<span class="value">${tex(q.value)}</span></span>` : `<span class="value">${tex(q.value)}</span>`}${more}`;
    const notes = desc + (q.note ? `<div class="sub">${md(q.note, true)}</div>` : "");
    const relCell = hasRel ? [head && rel.get(it.rows) ? `<span class="rel">${tex(rel.get(it.rows).tex)}</span>` : ""] : [];
    // A coefficient sits right before the structure it multiplies.
    return hasOpe
      ? [sym, valueCell, stCell, ...(hasNotes ? [notes] : []), ...relCell, source(q)]
      : cat === "ope"
        ? [sym, valueCell, ...(hasNotes ? [notes] : []), source(q)] // 2d: unique structure, no column
        : [sym, notes, ...relCell, valueCell, source(q)];
  };
  const tr = (cells, attrs = "") => `<tr${attrs}>${cells.map((c) => `<td>${c ?? ""}</td>`).join("")}</tr>`;
  const body = (it) =>
    `<tbody class="item${it.ope ? " ope-item" : ""}">${(it.lines || [it.rows]).map((line, k) => {
      const id = `det-${++DET_SEQ}`;
      const [head, ...rest] = line;
      const one = { ...it, id };
      return tr(row(head, one, line, true), k ? ' class="ope-line"' : "") + rest.map((q) => tr(row(q, one, line, false), ` class="det" data-det="${id}" hidden`)).join("");
    }).join("")}</tbody>`;
  const headers = cat === "ope"
    ? ["Three-point function", "Coefficient", ...(hasOpe ? ["Structure"] : []), ...(hasNotes ? ["Notes"] : []), "Source"]
    : hasOpe
      ? ["Quantity", "Value", "Structure", "Description", ...(hasRel ? ["Relation"] : []), "Source"]
      : [cat === "exponent" ? "Exponent" : "Quantity", "Description", ...(hasRel ? ["Relation"] : []), "Value", "Source"];
  return {
    html: `<div class="table-wrap"><table class="qty"><thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead>${items.map(body).join("")}</table></div>`,
    hasRel,
  };
}

/** The page sections for a theory's quantities. A small entry (one kind, or under six items and
 *  under three of any named kind) keeps one table; otherwise each kind gets its own section, in the
 *  contents bar. A description part
 *  titled like "Anomalies" or "Weyl anomaly" is shown in the anomalies section (its index is added
 *  to `used`). */
function dataSections(t, source, topics, used) {
  const quants = quantityItems(t);
  // Three-point data: the three-point functions (opeItems), then quantities set to `category: ope` (data that is not
  // a coefficient of one three-point function).
  const items = [...quants.filter((it) => it.cat !== "ope"), ...opeItems(t), ...quants.filter((it) => it.cat === "ope")];
  const cats = QCAT_ORDER.filter((c) => items.some((it) => it.cat === c));
  const conv = t.conventions || {};
  const convLine = (c) => (conv[c] ? `<p class="small conv">${md(conv[c], true)}</p>` : "");
  const allBtn = (its) => its.some((it) => (it.lines || [it.rows]).some((l) => l.length > 1))
    ? ` <button type="button" class="linkish small" data-dets-all aria-expanded="false">Show all determinations</button>` : "";
  const most = Math.max(...cats.filter((c) => c !== "other").map((c) => items.filter((it) => it.cat === c).length));
  // Every entry gets the same sections, however few its data (David, 2026-11-08: the same kind of thing looks the
  // same on every page); the one-table layout for small entries is gone.
  if (false) {
    const tb = quantityTable(t, items, null, source);
    const notes = QCAT_ORDER.filter((c) => conv[c]).map((c) => `<p class="small conv"><b>${QCATS[c].title}.</b> ${md(conv[c], true)}</p>`).join("");
    const btn = allBtn(items);
    return [section("data", "Data", `${notes}${btn ? `<p class="small">${btn}</p>` : ""}${tb.html}${opeStructuresHtml(t, items, "Structures of the three-point functions")}`)];
  }
  return cats.map((c) => {
    const its = items.filter((it) => it.cat === c);
    const tb = quantityTable(t, its, c, source);
    const meta = QCATS[c];
    let prose = "";
    if (c === "anomaly")
      topics.forEach((tp, i) => {
        if (!used.has(i) && /anomal/i.test(tp.title)) {
          used.add(i);
          prose += `<div class="prose">${md(tp.body)}</div>`;
        }
      });
    const intro = meta.intro(c === "ope" ? its.some((it) => it.ope) : tb.hasRel, t.d) + allBtn(its);
    const after = c === "ope" ? opeStructuresHtml(t, its) : ""; // the structures are defined below the table
    const id = cats.length === 1 && c === "other" ? "data" : meta.id;
    const title = cats.length === 1 && c === "other" ? "Data" : meta.title;
    return section(id, title, `${intro.trim() ? `<p class="small muted intro">${intro}</p>` : ""}${convLine(c)}${prose}${tb.html}${after}`);
  });
}

function setDets(btn, open) {
  app.querySelectorAll(`[data-det="${btn.dataset.dets}"]`).forEach((tr) => (tr.hidden = !open));
  btn.setAttribute("aria-expanded", open);
  btn.textContent = open ? "fold" : `+${btn.dataset.n} more`;
}

app.addEventListener("click", (e) => {
  const stl = e.target.closest("[data-ope-st]");
  if (stl) {
    e.preventDefault();
    const li = document.getElementById(`ope-st-${stl.dataset.opeSt}`);
    if (li) {
      li.scrollIntoView({ block: "center", behavior: "smooth" });
      li.classList.remove("flash");
      void li.offsetWidth;
      li.classList.add("flash");
    }
    return;
  }
  const one = e.target.closest("[data-dets]");
  if (one) return setDets(one, one.getAttribute("aria-expanded") !== "true");
  const all = e.target.closest("[data-dets-all]");
  if (all) {
    const open = all.getAttribute("aria-expanded") !== "true";
    all.closest("section").querySelectorAll("[data-dets]").forEach((b) => setDets(b, open));
    all.setAttribute("aria-expanded", open);
    all.textContent = open ? "Fold other determinations" : "Show all determinations";
  }
});

/* ------------------------------------------------------------ theory view */

/** Split a description at its "### Title" lines. The text before the first one is the
 *  overview; each titled part becomes a section of its own, listed in the contents bar. */
function splitDescription(src) {
  const [overview, ...parts] = String(src ?? "").split(/^### +/m);
  return {
    overview,
    topics: parts.map((part) => {
      const [title, ...body] = part.split("\n");
      return { title: title.trim(), body: body.join("\n") };
    }),
  };
}

/* ------------------------------------------------- operators by representation */

/** Leading numerical value of a Δ or spin: '1.412625(10)', '5/2', '\frac{1}{2}', '2 + \frac{3\lambda}{4\pi^2}' (leading
 *  term of a series), '\leq 10.9293'. NaN when the value is not a number (e.g. '0.265\,N_f - 0.0383'). */
function leadingNumber(s) {
  if (typeof s === "number") return s;
  const x = String(s ?? "").trim().replace(/^(?:\\leq?|\\geq?|\\approx|\\sim|[≤≥≈~<>])\s*/, "");
  let m, v;
  if ((m = /^\\[dt]?frac\s*\{\s*(-?\d+(?:\.\d+)?)\s*\}\s*\{\s*(\d+(?:\.\d+)?)\s*\}/.exec(x))) v = m[1] / m[2];
  else if ((m = /^(-?\d+(?:\.\d+)?)\s*\/\s*(\d+(?:\.\d+)?)/.exec(x))) v = m[1] / m[2];
  else if ((m = /^-?\d+(?:\.\d+)?(?:\(\d+\))?/.exec(x))) v = parseFloat(m[0]);
  else return NaN;
  const rest = x.slice(m[0].length).trim();
  return !rest || /^(?:[+\-−–]|\\pm|\\mp|\\text\{[–-]\})/.test(rest) ? v : NaN;
}

/** Split s at the separators in `seps` outside math, brackets and parentheses: [{ sep, text }], sep being the
 *  separator before the part ("" for the first). */
function topSplit(s, seps) {
  const out = [];
  let math = false, depth = 0, start = 0, sep = "";
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (c === "\\") i++;
    else if (c === "$") math = !math;
    else if (math) continue;
    else if ("([{".includes(c)) depth++;
    else if (")]}".includes(c)) depth--;
    else if (depth === 0 && seps.includes(c)) {
      out.push({ sep, text: s.slice(start, i).trim() });
      [sep, start] = [c, i + 1];
    }
  }
  out.push({ sep, text: s.slice(start).trim() });
  return out.filter((x) => x.text);
}

/** The parenthesized remarks of s outside math, " (...)" after a space: [{ start, end, inner }]. */
function parenGroups(s) {
  const out = [];
  let math = false, depth = 0, open = -1;
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (c === "\\") i++;
    else if (c === "$") math = !math;
    else if (math) continue;
    else if (c === "(") {
      if (depth === 0) open = i > 0 && s[i - 1] !== " " ? -1 : i;
      depth++;
    } else if (c === ")" && --depth === 0 && open >= 0) out.push({ start: open, end: i + 1, inner: s.slice(open + 1, i).trim() });
  }
  return out;
}
const cutParens = (s, groups) =>
  groups.reduceRight((acc, g) => acc.slice(0, g.start) + acc.slice(g.end), s).replace(/\s{2,}/g, " ").replace(/\s+([,;])/g, "$1").trim();

// LEGACY PATH, for entries not yet migrated to structured representations (no symmetry.global_group; see
// docs/REPRESENTATIONS.md and repTable below). Remove once every entry is migrated.
// A rep string mixes three things: the internal-symmetry representation ("$\mathbb{Z}_2$-even", "adjoint of $O(N)$"),
// spacetime parity / time reversal ("parity-odd", "odd under parity and time reversal", "$P$-odd") and remarks on
// the operator's role ("thermal", "order parameter", "superpartner of $\sigma$"). Each part (split at top-level , and ;
// with its parenthesized remarks) is classified by these words.
const OP_PARITY = /^(?:(?:parity|\$P\$)(?:[- ]and[- ](time[- ]reversal))?[- ](even|odd)|(even|odd) under (?:parity(?: and (time[- ]reversal))?|reflections?))$/i;
const OP_ROLE = /thermal|order parameter|energy|\\sim\b|∼|predominantly|at large|descends|contains|partner|multiplet|component|descendant|^degenerate|same anomalous|same for|walk|generator|permuted|sum over|Néel|VBS|primar(?:y|ies)\b|spin field|supercurrent|mass operator|^fermion|fermionic$|^dirac|^even \$|chirality/i;
const OP_REP = /singlet|adjoint|vector|symmetric|traceless|triplet|doublet|charge|neutral|\beven\b|\bodd\b|-even|-odd|bifundamental|representation|\brank\b|rank-|\\mathbf|irreducible|trivial|invariant|tensor|fundamental|\\wedge|winding|momentum|dimensional|sector|series|continu|discrete|completely degenerate|weights?\b|\$\s*\(?\s*(?:S?U|S?O|Sp|E_|SL|\\mathbb\s*\{Z\}|\\mathfrak)/i;
const mathOnly = (s) => /\$/.test(s) && !s.replace(/\$[^$]*\$/g, "").replace(/\b(?:and|or|resp\.?)\b|[\s,;()]/g, "");
const roleLike = (s) => OP_ROLE.test(s) || !(OP_REP.test(s) || mathOnly(s));

/** An operator's rep string as { internal, head, P, T, parityText, role }: the internal representation (head: its first
 *  part, which names the sector), parity and time reversal ("even" / "odd" / ""), the parity's wording, and the
 *  remarks on its role, which the table shows with the note. null without a rep. */
function repParts(rep) {
  if (rep == null || !String(rep).trim()) return null;
  const r = { P: "", T: "", parityText: "" }, kept = [], role = [];
  for (const { sep, text } of topSplit(String(rep), ",;")) {
    const parens = parenGroups(text), bare = cutParens(text, parens);
    const pm = OP_PARITY.exec(bare);
    if (pm) {
      r.P = (pm[2] || pm[3]).toLowerCase();
      if (pm[1] || pm[4]) r.T = r.P;
      r.parityText = bare;
      role.push(...parens.map((p) => p.inner));
    } else if (roleLike(bare)) role.push(text);
    else {
      const q = parens.filter((p) => roleLike(p.inner));
      role.push(...q.map((p) => p.inner));
      kept.push({ sep, text: cutParens(text, q) });
    }
  }
  r.internal = kept.map((k, i) => (i ? `${k.sep} ` : "") + k.text).join("");
  r.head = kept[0] ? cutParens(kept[0].text, parenGroups(kept[0].text)) : "";
  r.role = role.join("; ");
  return r;
}

/** Grouping key of a rep head: spelling-insensitive ('$\mathbb{Z}_2$-even' = 'Z2-even', case, spaces), nothing more. */
const repKey = (s) =>
  s.toLowerCase()
    .replace(/\\mathbb\s*\{\s*z\s*\}\s*_\s*\{?\s*(\d+)\s*\}?/g, "z$1")
    .replace(/\\(?:mathbf|mathrm|rm|text|bf)\s*\{([^{}]*)\}/g, "$1")
    .replace(/[$\s]+|\\[,;:! ]/g, " ")
    .replace(/\s*-\s*/g, "-")
    .replace(/traceless symmetric/g, "symmetric traceless")
    .trim();

/** The trivial sector (singlet, neutral, even, charge 0) comes first in the table. */
const trivialRep = (key) => /(?:^|\s)singlets?$|^(?:neutral|trivial|charge 0|r ?= ?0)$|-even$/.test(key);

/** Operator rows { o, i, parts, hk, key }: the sector key is the rep's head plus parity-odd, so parity-odd operators
 *  form their own sector and an unlabelled parity counts as even (T_{μν}, currents, ...). No internal rep and no
 *  parity: key null. */
function operatorRows(ops) {
  return ops.map((o, i) => {
    const parts = repParts(o.rep);
    if (!parts || (!parts.head && !parts.P)) return { o, i, parts, hk: null, key: null };
    const hk = repKey(parts.head);
    return { o, i, parts, hk, key: `${hk}|${parts.P === "odd" ? "odd" : ""}` };
  });
}

/** Rows that are one operator determined several times (by different methods or papers) as items { rows, id }: same
 *  name, spin, weights and multiplicity (rows already share a sector), and no theory parameter fixed differently
 *  ("N_f = 12" in the name, note or rep). Rows best first (orderDets); items in the order of their first row. */
function operatorItems(t, rows) {
  const pars = (t.parameters || []).map((p) => normTex(p.symbol)).filter(Boolean);
  const reEsc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const fixed = (o) => {
    const s = normTex([o.name, o.note, o.rep, o.role].join(" "));
    return pars.map((p) => new RegExp(`(?<![A-Za-z\\\\{])${reEsc(p)}=(-?\\d+(?:\\.\\d+)?)`).exec(s)?.[1] ?? "").join(",");
  };
  const key = (o) => [o.name, o.spin, o.weights, o.degeneracy].map(normTex).join("|") + "|" + fixed(o) + "|" + (o.family_view?.id ?? "");
  const items = new Map();
  for (const r of rows) {
    const k = key(r.o);
    if (!items.has(k)) items.set(k, { rows: [], first: r.i });
    items.get(k).rows.push(r);
  }
  const list = [...items.values()];
  for (const it of list) it.rows = orderDets(it.rows, (r) => r.o.Delta, (r) => r.o.method);
  return list;
}

/** Operators grouped into representation sectors, each a list of items ordered by spin, then by the Δ shown (the
 *  preferred determination). Returns { groups, grouped }; grouped is false when sectors would add nothing (no reps, or
 *  one rep): then one group, in data order. */
function operatorGroups(t) {
  const all = operatorRows(t.operators);
  const rows = all.filter((r) => !isMember(r));
  // In a theory with parity whose entry marks some operators parity-odd, an operator with no parity stated is
  // parity-even: say so (P column "+", heading "parity-even") rather than leave it blank.
  const sym = t.symmetry || {};
  const hasParity = /with parity/i.test(sym.spacetime || "") || /^\$O\(/.test(sym.euclidean || "");
  if (hasParity && rows.some((r) => r.parts?.P === "odd"))
    rows.forEach((r) => { if (r.parts && !r.parts.P) Object.assign(r.parts, { P: "even", parityText: "parity-even" }); });
  const groups = new Map();
  for (const r of rows) {
    if (!groups.has(r.key)) groups.set(r.key, { key: r.key, rows: [] });
    groups.get(r.key).rows.push(r);
  }
  const named = [...groups.values()].filter((g) => g.key !== null);
  if (named.length < 2 || named.every((g) => g.rows.length < 2)) {
    // Ungrouped: still one item per operator, though only rows of the same sector fold together.
    const items = [...groups.values()].flatMap((g) => operatorItems(t, g.rows)).sort((a, b) => a.first - b.first);
    attachMembers(items, all);
    return { grouped: false, groups: [{ key: "", heading: null, base: null, items }] };
  }

  const headOrder = new Map();
  rows.forEach((r) => r.key !== null && !headOrder.has(r.hk) && headOrder.set(r.hk, headOrder.size));
  const trivial = (r) => trivialRep(r.hk) || (!r.hk && r.parts.P === "even");
  const rank = (g) => (g.key === null ? [2, 0, 0] : [trivial(g.rows[0]) ? 0 : 1, headOrder.get(g.rows[0].hk), g.key.endsWith("|odd") ? 1 : 0]);
  const list = [...groups.values()].sort((a, b) => {
    const [x, y] = [rank(a), rank(b)];
    return x[0] - y[0] || x[1] - y[1] || x[2] - y[2];
  });

  const num = (v) => { const x = leadingNumber(v); return Number.isFinite(x) ? x : Infinity; };
  for (const g of list) {
    if (g.key !== null) {
      // The heading is the internal representation when the sector shares one (else the common head), plus the parity
      // when all its operators state the same one. The Representation column then shows a row's internal
      // representation only where it says more than the heading.
      const h = g.rows[0].parts;
      const same = g.rows.every((r) => r.parts.internal === h.internal);
      const showParity = g.rows.every((r) => r.parts.P && r.parts.P === h.P);
      g.base = same ? h.internal : h.head;
      g.heading = [g.base, showParity || !g.base ? h.parityText : ""].filter(Boolean).join(", ");
    } else [g.heading, g.base] = [null, null];
    g.items = operatorItems(t, g.rows);
    const sk = (it) => [...placeKey(it.rows[0].o), it.first];
    g.items.sort((a, b) => {
      const [x, y] = [sk(a), sk(b)];
      for (let k = 0; k < 3; k++) if (x[k] !== y[k]) return x[k] < y[k] ? -1 : 1;
      return 0;
    });
    attachMembers(g.items, all);
  }
  return { grouped: true, groups: list };
}

/** A group heading links its first common rep word to Wikipedia (one link at most, never inside math). */
const REP_WIKI = [
  [/\bsinglets?\b/i, "https://en.wikipedia.org/wiki/Trivial_representation"],
  [/\badjoint\b/i, "https://en.wikipedia.org/wiki/Adjoint_representation"],
  [/\bparity\b/i, "https://en.wikipedia.org/wiki/Parity_(physics)"],
];
function repWikiLinks(heading) {
  if (/\]\(/.test(heading)) return heading; // already has a link
  const parts = heading.split(/(\$[^$]*\$)/); // odd parts are math
  let best = null;
  for (let i = 0; i < parts.length; i += 2)
    for (const [re, url] of REP_WIKI) {
      const m = re.exec(parts[i]);
      if (m && (!best || i < best.i || (i === best.i && m.index < best.at))) best = { i, at: m.index, len: m[0].length, url };
    }
  if (best) {
    const p = parts[best.i];
    parts[best.i] = `${p.slice(0, best.at)}[${p.slice(best.at, best.at + best.len)}](${best.url})${p.slice(best.at + best.len)}`;
  }
  return parts.join("");
}

/* ------------------------------------- structured representations (docs/REPRESENTATIONS.md) */
// An entry with symmetry.global_group gives each operator a representation of the full symmetry group: Δ, spin (or
// `lorentz`, or 2d weights), `parity`, and a label per global factor (`global`), which the build has parsed into
// o.irrep.global = [{ factor, canon, text, trivial, sort }]. This is the presentation policy applied to that data:
// group by global irrep, then by parity; a level that is constant over the table is stated once above it; within a
// group, order by spin, then Δ.

const PARITY_RANK = { even: 0, odd: 1, pair: 2, unknown: 3 };
const PARITY_TEXT = { even: "parity-even", odd: "parity-odd", pair: "parity-paired", unknown: "parity not recorded" };
const PARITY_TIP = {
  even: "parity even", odd: "parity odd", unknown: "parity not recorded",
  pair: "no parity eigenvalue: parity maps the operator to a partner in another representation (spin s to −s in 2d, (j, j̄) to (j̄, j) in 4d, a charge q to −q)",
};
const PARITY_SIGN = { even: "+", odd: "−", pair: "↔", unknown: "?" };

/** Compare sort keys: numbers, or arrays of them compared lexicographically (shorter first on a tie). */
function cmpKey(x, y) {
  if (!Array.isArray(x) || !Array.isArray(y)) return x === y ? 0 : x < y ? -1 : 1;
  for (let i = 0; i < Math.min(x.length, y.length); i++) {
    const c = cmpKey(x[i], y[i]);
    if (c) return c;
  }
  return x.length - y.length;
}

/** Heading text of a global irrep: its non-trivial factors (a factor not named is in its trivial representation). */
function globalText(t, labels) {
  const fs = t.global_factors || [];
  const non = labels.filter((v) => !v.trivial);
  if (non.length) return non.map((v) => v.text).join(", ");
  return fs.length === 1 ? labels[0]?.text ?? "" : `singlet of $${fs.map((f) => f.tex).join(" \\times ")}$`;
}

/** The grouping levels of a structured entry, in the policy's order; each gives a row's key, sort key and text. */
function repLevels(t) {
  const sym = t.symmetry || {};
  const out = [];
  if ((t.global_factors || []).length)
    out.push({
      id: "global", header: "Representation",
      key: (r) => r.o.irrep?.key ?? "",
      sort: (r) => (r.o.irrep?.global || []).map((v) => v.sort),
      text: (r) => globalText(t, r.o.irrep?.global || []),
    });
  if (sym.parity === true || sym.parity === "conditional")
    out.push({
      id: "parity", header: `<span title="Parity: + even, − odd, ↔ paired with a partner, ? not recorded">P</span>`, narrow: true,
      key: (r) => r.o.parity ?? "unknown",
      sort: (r) => PARITY_RANK[r.o.parity ?? "unknown"],
      text: (r) => PARITY_TEXT[r.o.parity ?? "unknown"],
      cell: (r) => { const p = r.o.parity ?? "unknown"; return `<span title="${PARITY_TIP[p]}">${PARITY_SIGN[p]}</span>`; },
    });
  return out;
}

/** Operators of a structured entry as { groups, grouped, levels, constant }. Levels taking one value over the whole
 *  table are `constant` (stated above it); the others group the table. Grouped is false when no group would have two
 *  operators: then one group, the remaining levels become columns. */
function repGroups(t) {
  const all = t.operators.map((o, i) => ({ o, i }));
  const rows = all.filter((r) => !isMember(r));
  const levels = repLevels(t);
  const constant = levels.filter((L) => new Set(rows.map(L.key)).size === 1);
  const active = levels.filter((L) => !constant.includes(L));
  const groups = new Map();
  for (const r of rows) {
    const k = active.map((L) => L.key(r)).join("||");
    if (!groups.has(k)) groups.set(k, { key: k, rows: [] });
    groups.get(k).rows.push(r);
  }
  const list = [...groups.values()].sort((a, b) => {
    for (const L of active) {
      const c = cmpKey(L.sort(a.rows[0]), L.sort(b.rows[0]));
      if (c) return c;
    }
    return a.rows[0].i - b.rows[0].i;
  });
  for (const g of list) {
    g.items = operatorItems(t, g.rows);
    g.items.sort((a, b) => cmpKey([...placeKey(a.rows[0].o, 0), a.first], [...placeKey(b.rows[0].o, 0), b.first]));
    attachMembers(g.items, all);
    g.heading = active.map((L) => L.text(g.rows[0])).filter(Boolean).join(", ");
  }
  const grouped = active.length > 0 && list.some((g) => g.items.length > 1);
  return { groups: list, grouped, levels, constant, active };
}

/* ------------------------------------- operator families (docs/REPRESENTATIONS.md, 1.7 and 2.7) */
// A family row (o.family_view, from the build) stands for a whole tower of operators: it is one operator of the table,
// grouped by its representation pattern ("[0,k,0] of SU(4)_R") and placed by its first member. Rows that record one
// member separately (o.member_view) are listed under their family, never as operators of their own.

const isMember = (r) => r.o.member_view != null;

/** Spin and Δ that place an operator within its group (a family by its first member, as computed by the build). */
function placeKey(o, spinDefault) {
  const num = (v) => { const x = leadingNumber(v); return Number.isFinite(x) ? x : Infinity; };
  const f = o.family_view?.sort;
  if (f) return [f.spin ?? Infinity, f.Delta ?? Infinity];
  return [num(o.spin ?? spinDefault), num(o.Delta)];
}

/** Give each family item its members: one item per member (its determinations fold together), in parameter order. */
function attachMembers(items, all) {
  for (const it of items) {
    const fam = it.rows[0].o.family_view;
    if (!fam) continue;
    const byAt = new Map();
    for (const r of all.filter((x) => isMember(x) && x.o.member_view.family === fam.id)) {
      const k = r.o.member_view.at;
      if (!byAt.has(k)) byAt.set(k, { rows: [], first: r.i, sort: r.o.member_view.sort });
      byAt.get(k).rows.push(r);
    }
    it.members = [...byAt.values()].sort((a, b) => cmpKey(a.sort, b.sort) || a.first - b.first);
    for (const m of it.members) m.rows = orderDets(m.rows, (r) => r.o.Delta, (r) => r.o.method);
  }
}

/** Under a family's name: its parameter range and, when members are listed, the button that folds them. */
function familyLine(it) {
  const f = it.rows[0].o.family_view;
  if (!f) return "";
  const n = it.members?.length ?? 0;
  const btn = n ? ` · <button type="button" class="linkish op-members" data-members="${it.id}" aria-expanded="true"
    title="Fold the members listed separately">${n === 1 ? "1 member listed" : `${n} members listed`} ▾</button>` : "";
  return `<div class="sub op-family" title="One row for the whole family: its Δ, spin and labels are functions of the parameters">family, <span class="op-range">${tex(f.range)}</span>${btn}</div>`;
}

/** Before a member's name: its parameter values. */
const memberAt = (r) => (r.o.member_view ? `<span class="op-at">${tex(r.o.member_view.at)}:</span> ` : "");

/** A family's member rows, after the family's own row in its tbody: each member's preferred determination, the others
 *  folded under it ("+n more"). */
function memberRows(it, cols, td, g) {
  return (it.members || []).map((m) => {
    m.id = `det-${++DET_SEQ}`;
    const [first, ...rest] = m.rows;
    const tr = (r, isHead) => `<tr class="op-member${isHead ? "" : " det"}" data-memberof="${it.id}"${isHead ? "" : ` data-det="${m.id}" hidden`}>${
      cols.map(([, f], k) => td(f(r, m, g, isHead), k)).join("")}</tr>`;
    return tr(first, true) + rest.map((r) => tr(r, false)).join("");
  }).join("");
}

app.addEventListener("click", (e) => {
  const b = e.target.closest("[data-members]");
  if (!b) return;
  const open = b.getAttribute("aria-expanded") !== "true";
  app.querySelectorAll(`[data-memberof="${b.dataset.members}"]`).forEach((tr) => {
    if (!tr.classList.contains("det")) tr.hidden = !open;
    else if (!open) tr.hidden = true;
  });
  if (open) app.querySelectorAll(`[data-memberof="${b.dataset.members}"] [data-dets]`).forEach((x) => setDets(x, false));
  b.setAttribute("aria-expanded", open);
  b.innerHTML = b.innerHTML.replace(/[▾▸]$/, open ? "▾" : "▸");
  b.title = open ? "Fold the members listed separately" : "Show the members listed separately";
});

/** Lorentz label for the Spin column: `lorentz` when given ('(1/2, 0)' -> (\tfrac12, 0)), else the spin. */
function lorentzTex(o) {
  if (o.lorentz == null) return o.spin != null ? tex(o.spin) : "";
  return tex(String(o.lorentz).replace(/(\d+)\/(\d+)/g, "\\tfrac{$1}{$2}"));
}

/** The Multiplet cell: name, component and the house name (`type`); the CDI label shows on hover over the house name,
 *  or over the name when there is no house name (docs/REPRESENTATIONS.md 1.5). */
function multipletHtml(m) {
  if (!m) return "";
  const comp = m.component === "primary" ? "primary" : tex(m.component);
  const cdi = m.cdi && m.cdi !== "unknown"
    ? ` class="hover-label" tabindex="0" data-hover="${esc(`<span class="muted">Cordova–Dumitrescu–Intriligator:</span> ${md(m.cdi, true)}`)}"` : "";
  const name = m.type || !cdi ? md(m.name, true) : `<span${cdi}>${md(m.name, true)}</span>`;
  const type = m.type ? ` <span class="op-role nowrap">(<span${cdi}>${md(m.type, true)}</span>)</span>` : "";
  return `${name}, ${comp}${type}`;
}

/** The operators table of a structured entry (policy in docs/REPRESENTATIONS.md). */
function repTable(t, source) {
  const { groups, grouped, levels, constant, active } = repGroups(t);
  const ops = t.operators;
  const allItems = groups.flatMap((g) => g.items.flatMap((it) => [it, ...(it.members || [])]));
  const allRows = allItems.flatMap((it) => it.rows);
  const roleTag = (r) => (r.o.role ? ` <span class="op-role${r.o.role.length <= 24 ? " nowrap" : ""}">· ${md(r.o.role, true)}</span>` : "");
  const differs = (f) => (r, it, g, head) => {
    const v = f(r, it, g);
    return head || v !== f(it.rows[0], it, g) ? v : "";
  };
  const spins = new Set(ops.map((o) => normTex(o.lorentz ?? o.spin ?? "")));
  const spinConstant = spins.size === 1 && ops.every((o) => o.weights == null);
  const T = t.symmetry?.time_reversal === "independent";
  // Levels that group the table are in the headings; in an ungrouped table they are columns.
  const levelCols = grouped ? [] : active.map((L) => [L.header, differs((r) => (L.cell ? L.cell(r) : md(L.text(r), true))), true, L.narrow]);
  const cols = [
    ["Operator", (r, it, g, head) => (head ? memberAt(r) + tex(r.o.name) + roleTag(r) + familyLine(it) : (r.o.role ?? "") !== (it.rows[0].o.role ?? "") ? roleTag(r).trim() : ""), true],
    ["Δ", (r, it, g, head) => {
      const v = `<span class="value">${tex(r.o.Delta)}</span>`;
      const bad = (x) => disagreement(it.rows[0].o, x.o, (o) => o.Delta);
      if (!head) return v + disagreeBadge(bad(r));
      const n = it.rows.length - 1;
      return v + (n ? detsButton(it.id, n, it.rows.filter((x) => bad(x)).length) : "");
    }, true],
    [tex("(h, \\bar h)"), differs((r) => (r.o.weights ? tex(r.o.weights) : "")), ops.some((o) => o.weights != null)],
    ["Mult.", differs((r) => (r.o.degeneracy ? tex(r.o.degeneracy) : "")), ops.some((o) => o.degeneracy != null)],
    [ops.some((o) => o.lorentz != null) && t.d === 4 ? tex("(j, \\bar\\jmath)") : "Spin", differs((r) => lorentzTex(r.o)),
      ops.some((o) => o.spin != null || o.lorentz != null) && !spinConstant],
    ...levelCols,
    [`<span title="Time reversal: + even, − odd">T</span>`, differs((r) => (r.o.T ? `<span title="time reversal ${r.o.T}">${PARITY_SIGN[r.o.T]}</span>` : "")), T, true],
    ["Multiplet", differs((r) => multipletHtml(r.o.multiplet)), ops.some((o) => o.multiplet)],
    ["Notes", (r) => (r.o.note ? md(r.o.note, true) : ""), ops.some((o) => o.note != null)],
    ["Source", (r) => source(r.o), ops.some((o) => o.method || o.refs?.length)],
  ].filter(([, , shown]) => shown);
  const narrow = new Set(cols.map((c, k) => (c[3] ? k : -1)).filter((k) => k >= 0));
  const td = (c, k) => `<td${narrow.has(k) ? ` class="num"` : ""}>${c ?? ""}</td>`;
  let seq = 0;
  const body = groups
    .map((g) => {
      const gid = `opg-${++DET_SEQ}`;
      const head = !grouped ? "" : `<tbody class="op-head"><tr class="op-group"><th colspan="${cols.length}" scope="rowgroup">
        <button type="button" class="linkish op-fold" data-opgroup="${gid}" aria-expanded="true" title="Fold this group">▾</button>
        ${md(repWikiLinks(g.heading), true)} <span class="op-count">${g.items.length}</span></th></tr></tbody>`;
      return head + g.items
        .map((it) => {
          it.id = `det-${++DET_SEQ}`;
          const [first, ...rest] = it.rows;
          const tr = (r, isHead) => `<tr${isHead ? "" : ` class="det" data-det="${it.id}" hidden`}>${cols.map(([, f], k) => td(f(r, it, g, isHead), k)).join("")}</tr>`;
          return `<tbody class="item${seq++ % 2 ? " alt" : ""}"${grouped ? ` data-ingroup="${gid}"` : ""}>${tr(first, true)}${rest.map((r) => tr(r, false)).join("")}${memberRows(it, cols, td, g)}</tbody>`;
        })
        .join("");
    })
    .join("");
  // What every operator shares is said once, above the table.
  const shared = [
    ...constant.map((L) => L.text({ o: ops.find((o) => !o.member_view) })),
    spinConstant && ops[0].spin != null ? (ops[0].lorentz == null ? `spin $${ops[0].spin}$` : `Lorentz representation $${ops[0].lorentz}$`) : "",
  ].filter(Boolean);
  const caption = shared.length ? `<p class="small muted intro">All operators listed: ${md(shared.join(", "), true)}.</p>` : "";
  const btn = allRows.length > allItems.length
    ? `<p class="small"><button type="button" class="linkish small" data-dets-all aria-expanded="false">Show all determinations</button></p>` : "";
  return `${caption}${btn}<div class="table-wrap"><table class="ops"><thead><tr>${cols.map(([h], k) => `<th${narrow.has(k) ? ` class="num"` : ""}>${h}</th>`).join("")}</tr></thead>${body}</table></div>`;
}

app.addEventListener("click", (e) => {
  const b = e.target.closest("[data-opgroup]");
  if (!b) return;
  const open = b.getAttribute("aria-expanded") !== "true";
  app.querySelectorAll(`[data-ingroup="${b.dataset.opgroup}"]`).forEach((tb) => (tb.hidden = !open));
  b.setAttribute("aria-expanded", open);
  b.textContent = open ? "▾" : "▸";
  b.title = open ? "Fold this group" : "Show this group";
});

/** The operators table. One tbody per operator: the preferred determination shows (orderDets), the others fold under
 *  "+n more" in the same item. Parity (P) and time reversal (T) get their own columns, as + / −, where some operator
 *  states them. A grouped table has no Representation column: the sector heading carries the representation, and a
 *  row whose representation says more than its heading ("singlet; $SU(N_f)$ adjoint" under "singlet") states it in
 *  its note. An ungrouped table keeps a Representation column of internal representations only. Remarks on an
 *  operator's role ("thermal", "order parameter") are a muted tag after its name, never a representation. */
function operatorsTable(t, source) {
  if (t.symmetry?.global_group) return repTable(t, source);
  const { groups, grouped } = operatorGroups(t);
  const allItems = groups.flatMap((g) => g.items.flatMap((it) => [it, ...(it.members || [])]));
  const sign = (s, what) => (s ? `<span title="${what} ${s}">${s === "odd" ? "−" : "+"}</span>` : "");
  const repOf = (g, r) => {
    const x = r.parts?.internal ?? "";
    return grouped && g.key !== null && x === g.base ? "" : x;
  };
  // A short remark stays on one line with the name; a long one wraps.
  const roleTag = (r) => (r.parts?.role ? ` <span class="op-role${r.parts.role.length <= 24 ? " nowrap" : ""}">· ${md(r.parts.role, true)}</span>` : "");
  const ops = t.operators;
  // [header, cell(row, item, group, head?), shown?]. A folded row repeats a column only where it differs from the row shown.
  const differs = (f) => (r, it, g, head) => {
    const v = f(r, it, g);
    return head || v !== f(it.rows[0], it, g) ? v : "";
  };
  const extraRep = (r, it, g) => (grouped && repOf(g, r) ? `<div class="op-rep">Representation: ${md(repOf(g, r), true)}</div>` : "");
  const cols = [
    ["Operator", (r, it, g, head) => (head ? memberAt(r) + tex(r.o.name) + roleTag(r) + familyLine(it) : (r.parts?.role ?? "") !== (it.rows[0].parts?.role ?? "") ? roleTag(r).trim() : ""), true],
    ["Δ", (r, it, g, head) => {
      const v = `<span class="value">${tex(r.o.Delta)}</span>`;
      const bad = (x) => disagreement(it.rows[0].o, x.o, (o) => o.Delta);
      if (!head) return v + disagreeBadge(bad(r));
      const n = it.rows.length - 1;
      return v + (n ? detsButton(it.id, n, it.rows.filter((x) => bad(x)).length) : "");
    }, true],
    [tex("(h, \\bar h)"), differs((r) => (r.o.weights ? tex(r.o.weights) : "")), ops.some((o) => o.weights != null)],
    ["Mult.", differs((r) => (r.o.degeneracy ? tex(r.o.degeneracy) : "")), ops.some((o) => o.degeneracy != null)],
    ["Spin", differs((r) => (r.o.spin != null ? tex(r.o.spin) : "")), ops.some((o) => o.spin != null)],
    [`<span title="Parity: + even, − odd">P</span>`, differs((r) => sign(r.parts?.P, "parity")), allItems.some((it) => it.rows.some((r) => r.parts?.P))],
    [`<span title="Time reversal: + even, − odd">T</span>`, differs((r) => sign(r.parts?.T, "time reversal")), allItems.some((it) => it.rows.some((r) => r.parts?.T))],
    ["Representation", differs((r, it, g) => md(repOf(g, r), true)), !grouped && allItems.some((it) => it.rows.some((r) => r.parts?.internal))],
    ["Notes", (r, it, g, head) => differs(extraRep)(r, it, g, head) + (r.o.note ? md(r.o.note, true) : ""),
      ops.some((o) => o.note != null) || (grouped && groups.some((g) => g.items.some((it) => it.rows.some((r) => repOf(g, r)))))],
    ["Source", (r) => source(r.o), ops.some((o) => o.method || o.refs?.length)],
  ].filter(([, , shown]) => shown);
  const narrow = new Set(["P", "T"].map((h) => cols.findIndex(([x]) => x.endsWith(`>${h}</span>`))));
  const td = (c, k) => `<td${narrow.has(k) ? ` class="num"` : ""}>${c ?? ""}</td>`;
  const body = groups
    .map((g) => {
      const head = !grouped ? "" : `<tbody class="op-head"><tr class="op-group"><th colspan="${cols.length}" scope="rowgroup">${
        g.heading == null ? `<span class="op-group-none">representation not given</span>` : md(repWikiLinks(g.heading), true)}</th></tr></tbody>`;
      return head + g.items
        .map((it, j) => {
          it.id = `det-${++DET_SEQ}`;
          const [first, ...rest] = it.rows;
          const tr = (r, isHead) => `<tr${isHead ? "" : ` class="det" data-det="${it.id}" hidden`}>${cols.map(([, f], k) => td(f(r, it, g, isHead), k)).join("")}</tr>`;
          return `<tbody class="item${j % 2 ? " alt" : ""}">${tr(first, true)}${rest.map((r) => tr(r, false)).join("")}${memberRows(it, cols, td, g)}</tbody>`;
        })
        .join("");
    })
    .join("");
  const btn = allItems.some((it) => it.rows.length > 1)
    ? `<p class="small"><button type="button" class="linkish small" data-dets-all aria-expanded="false">Show all determinations</button></p>` : "";
  return `${btn}<div class="table-wrap"><table class="ops"><thead><tr>${cols.map(([h], k) => `<th${narrow.has(k) ? ` class="num"` : ""}>${h}</th>`).join("")}</tr></thead>${body}</table></div>`;
}

function viewTheory(id) {
  const t = BY_ID.get(id);
  if (!t) return viewNotFound(`No theory with id “${id}”.`);
  document.title = `${plain(t.name)} — QFT Zoo`;

  const refs = t.references || [];
  citeStart(refs.map((r) => [t.id, r.key])); // the entry's own references keep their order; others cited on the page follow
  CITE_OWNER = t.id;
  const cite = (keys) => citeRefs(t.id, keys);
  const source = (x) => [x.method ? methodHtml(x.method) : "", cite(x.refs)].filter(Boolean).join(" ");

  const out = [];

  const { overview, topics } = splitDescription(t.description);
  if (overview.trim()) out.push(section("overview", "Overview", `<div class="prose">${md(overview)}</div>`));

  const fs = theoryFlows(t);
  const mine = [...fs.from, ...fs.to, ...fs.part, ...fs.page];
  if (mine.length) {
    const clusters = flowClusters(allFlows()).filter((c) => c.some((f) => mine.includes(f)));
    out.push(section("flows", "RG flows", `${clusters.map((c) => flowDiagram(c, t.id)).join("")}${flowList(t, fs)}
      <p class="small"><a href="#/flows">All RG flows in the zoo →</a></p>`));
  }

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
      ["Spacetime", (s.spacetime || s.euclidean || s.lorentzian) && spacetimeHtml(s)],
      ["Global", s.global && md(s.global, true)],
      ["Gauge", s.gauge && md(s.gauge, true)],
      ["Notes", s.notes && md(s.notes, true)],
    ].filter(([, v]) => v);
    out.push(section("symmetry", "Symmetry", `<dl class="kv">${rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("")}</dl>`));
  }

  if (t.operators?.length) out.push(section("operators", "Operators", operatorsTable(t, source)));

  const usedTopics = new Set();
  if (t.quantities?.length || t.three_point_functions?.length) out.push(...dataSections(t, source, topics, usedTopics));

  if (t.spectra?.length) out.push(section("spectrum", "Spectrum", spectrumShell(t)));

  topics.forEach(({ title, body }, i) =>
    usedTopics.has(i) || out.push(section(`topic-${i}`, md(title, true), `<div class="prose">${md(body)}</div>`))
  );

  const others = theoryLinks(t).filter((l) => !isFlow(l));
  if (others.length) out.push(section("relations", "Relations", relationList(t, others)));

  if (CITES.list.length) out.push(section("references", "References", citeList()));

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
  drawFlowArrows();
}

/* ------------------------------------------------------------- relations */

const theoryLinks = (t) => [...(t.relations || []), ...(t.backlinks || [])];
const isFlow = (l) => l.type === "flows_to" || l.type === "flows_from";

/** "(p = 3, D-series)": which member of a family a link refers to. The parameter
 *  belongs to the family side of the link. */
function linkAt(t, l) {
  if (l.at == null) return "";
  const other = BY_ID.get(l.target);
  const famSide = other?.family ? other : t.family ? t : null;
  return ` <span class="muted">(${tex(`${paramTex(famSide?.family.parameter ?? "")}${famSide ? " = " : ""}${l.at}`)}${
    l.variant ? `, ${esc(l.variant)}` : ""})</span>`;
}

function relationList(t, links) {
  const groups = Object.keys(REL_LABEL)
    .map((type) => [type, links.filter((l) => l.type === type)])
    .filter(([, ls]) => ls.length);
  return `<dl class="kv relations">${groups
    .map(
      ([type, ls]) =>
        `<dt>${REL_LABEL[type]}</dt><dd><ul>${ls
          .map((l) => {
            const other = BY_ID.get(l.target);
            return `<li><a href="#/theory/${encodeURIComponent(l.target)}">${md(other ? other.name : l.target, true)}</a>${linkAt(t, l)}${
              l.note ? ` <span class="muted">— ${md(l.note, true)}</span>` : ""
            }</li>`;
          })
          .join("")}</ul></dd>`
    )
    .join("")}</dl>`;
}

/* ---------------------------------------------------------------- RG flows */

// A flow is identified by its UV entry and the relation's `id` (or its position), as
// build.py records in `flow_key`. Only flows_to relations are read, never the reverse
// links, so two flows between the same theories stay two flows, and none is counted twice.
let FLOWS = null;
const FLOW_BY_KEY = new Map();

/** Every recorded flow once, read from the UV side. A composite IR (`target_expr`) is a node
 *  of its own, "expr:<flow key>", so expressions from different flows never merge. */
function allFlows() {
  if (FLOWS) return FLOWS;
  FLOWS = [];
  for (const t of DB.theories)
    (t.relations || []).forEach((l, i) => {
      if (l.type !== "flows_to") return;
      const key = l.flow_key ?? `${t.id}@${i}`;
      let f;
      if (l.target_expr) {
        if (!exprLeaves(l.target_expr).every((x) => BY_ID.has(x.entry))) return;
        f = { key, uv: t.id, ir: `expr:${key}`, expr: l.target_expr, note: l.note, at: "", rel: l, flow: l.flow };
      } else {
        if (!BY_ID.has(l.target)) return;
        f = { key, uv: t.id, ir: l.target, note: l.note, at: linkAt(t, l), rel: l, flow: l.flow };
      }
      FLOWS.push(f);
      FLOW_BY_KEY.set(key, f);
    });
  return FLOWS;
}

const isExprNode = (id) => id.startsWith("expr:");
const exprLeaves = (x) => (x.entry ? [x] : x.terms.flatMap((term) => exprLeaves(term.expr)));
const nodeDim = (id) => BY_ID.get(isExprNode(id) ? FLOW_BY_KEY.get(id.slice(5)).uv : id).d;

const OPERATION = {
  direct_sum: { symbol: "⊕", page: "direct-sum", name: "direct sum" },
  tensor_product: { symbol: "⊗", page: "tensor-product", name: "tensor product" },
};
const operationPage = (op) => (DB.operations || []).find((o) => o.id === OPERATION[op].page);

/** A composite IR as HTML: entry names linked, operations linked to their explanation pages. */
function exprHtml(x, top = true) {
  if (x.entry) {
    const t = BY_ID.get(x.entry);
    const at = x.at != null
      ? ` <span class="muted">(${tex(`${paramTex(t.family?.parameter ?? "")}${t.family ? " = " : ""}${x.at}`)}${x.variant ? `, ${esc(x.variant)}` : ""})</span>`
      : "";
    return `<a href="#/theory/${encodeURIComponent(x.entry)}">${md(t.name, true)}</a>${at}`;
  }
  const op = OPERATION[x.operation];
  const sym = operationPage(x.operation)
    ? `<a class="flow-op" href="#/operation/${op.page}" title="${esc(op.name)}">${op.symbol}</a>`
    : `<span class="flow-op" title="${esc(op.name)}">${op.symbol}</span>`;
  const terms = x.terms.map((term) => {
    const inner = exprHtml(term.expr, false);
    return (term.multiplicity ?? 1) > 1 ? `${inner}<sup>${op.symbol}${term.multiplicity}</sup>` : inner;
  });
  const body = terms.join(` ${sym} `);
  return top ? body : `(${body})`;
}

function exprPlain(x, top = true) {
  if (x.entry) return plain(BY_ID.get(x.entry).name) + (x.at != null ? ` (${plain(String(x.at))})` : "");
  const op = OPERATION[x.operation];
  const body = x.terms
    .map((term) => exprPlain(term.expr, false) + ((term.multiplicity ?? 1) > 1 ? ` ${op.symbol}${term.multiplicity}` : ""))
    .join(` ${op.symbol} `);
  return top ? body : `(${body})`;
}

/** In flow diagrams, lists and previews a theory goes by its short name when it has one. */
const shortName = (t) => t.short_name ?? t.name;
const nodeName = (id) => (isExprNode(id) ? exprHtml(FLOW_BY_KEY.get(id.slice(5)).expr) : `<a href="#/theory/${encodeURIComponent(id)}">${md(shortName(BY_ID.get(id)), true)}</a>`);
const nodePlain = (id) => (isExprNode(id) ? exprPlain(FLOW_BY_KEY.get(id.slice(5)).expr) : plain(shortName(BY_ID.get(id))));

/** Flows grouped into connected networks. */
function flowClusters(flows) {
  const parent = new Map();
  const find = (x) => {
    while (parent.has(x)) x = parent.get(x);
    return x;
  };
  flows.forEach((f) => {
    const [a, b] = [find(f.uv), find(f.ir)];
    if (a !== b) parent.set(a, b);
  });
  const clusters = new Map();
  flows.forEach((f) => {
    const r = find(f.uv);
    clusters.set(r, [...(clusters.get(r) || []), f]);
  });
  return [...clusters.values()];
}

const SIGN_REL = { positive: "> 0", negative: "< 0", zero: "= 0", either: "\\gtrless 0" };
const SIGN_SHORT = { positive: "+", negative: "−", zero: "0", either: "±" };
const SIGN_WORD = { positive: "positive", negative: "negative", zero: "zero", either: "either sign" };

/** Plain-text name of an arrow, for screen readers and the tooltip's heading. */
function edgeName(f) {
  const fl = f.flow;
  const what = [];
  for (const d of fl?.deformations || [])
    what.push(`${plain(d.operator)}${d.sign ? `, ${plain(d.coupling)} ${SIGN_WORD[d.sign]}` : ""}`);
  for (const v of fl?.vevs || []) what.push(`vev of ${plain(v.operator)}`);
  const page = fl?.page && BY_ID.get(fl.page);
  return `Flow from ${nodePlain(f.uv)} to ${nodePlain(f.ir)}${what.length ? `: ${what.join("; ")}` : ""}${
    page ? `. Flow page: ${plain(page.name)}` : ""}`;
}

let FLOW_VIEWS = 0;

const MONOTONE_SYM = { 2: "c", 3: "F", 4: "a", 5: "\\tilde F", 6: "a" };

/** Rows of one network, UV at the top and IR at the bottom, as compact as the flows allow. Theories are taken
 *  in order of the quantity that decreases along flows (c, F or a: build.py's flow_height; where none is
 *  recorded, a rough count of UV degrees of freedom), always after their UV theories. A theory joins the
 *  lowest row so far unless a flow joins it to that row or its value is well below the row's (factor 1.6),
 *  so height follows the monotone roughly while unrelated theories sit side by side. */
function flowRows(cluster) {
  const ids = [...new Set(cluster.flatMap((f) => [f.uv, f.ir]))];
  const h = (id) => BY_ID.get(id).flow_height?.value;
  const parents = (id) => cluster.filter((f) => f.ir === id).map((f) => f.uv);
  const placed = new Set();
  const order = [];
  while (order.length < ids.length) {
    const ready = ids.filter((id) => !placed.has(id) && parents(id).every((p) => placed.has(p)));
    if (!ready.length) { order.push(...ids.filter((id) => !placed.has(id))); break; } // a cycle would be a data error
    ready.sort((a, b) => (h(b) ?? Infinity) - (h(a) ?? Infinity));
    placed.add(ready[0]);
    order.push(ready[0]);
  }
  const rows = [];
  for (const id of order) {
    const row = rows.at(-1);
    const [x, top] = [h(id), row && Math.max(...row.map(h).filter((v) => v != null))];
    const near = x == null || !isFinite(top) || x === top || (x > 0 && top / x <= 1.6);
    if (row && near && !parents(id).some((p) => row.includes(p))) row.push(id);
    else rows.push([id]);
  }
  // Within a row, order theories by where their UV theories sit, to keep arrows from crossing.
  const pos = new Map();
  rows.forEach((row) => {
    const bary = (id) => { const ps = parents(id).map((p) => pos.get(p)); return ps.length ? ps.reduce((s, v) => s + v, 0) / ps.length : 0.5; };
    row.sort((a, b) => bary(a) - bary(b));
    row.forEach((id, i) => pos.set(id, (i + 0.5) / row.length));
  });
  return rows;
}

function flowDiagram(cluster, current = null) {
  const node = (id) => {
    if (isExprNode(id)) {
      const f = FLOW_BY_KEY.get(id.slice(5));
      const deco = f.expr.decoration ? `<span class="flow-deco">${md(f.expr.decoration, true)}</span>` : "";
      return `<div class="flow-node composite" data-flow-node="${esc(id)}">${exprHtml(f.expr)}${deco}<span class="flow-kind">composite</span></div>`;
    }
    const t = BY_ID.get(id);
    const fh = t.flow_height;
    const sym = MONOTONE_SYM[t.d];
    // Tooltip: the full name, and the value that set the theory's height.
    const height = fh && sym
      ? (fh.estimated ? `$${sym}$ not recorded: placed by a rough count of UV degrees of freedom` : `$${sym}$ ${fh.exact ? "=" : "≈"} ${+fh.value.toPrecision(4)}`)
      : "";
    const title = ` data-tip="${esc(`<b>${md(t.name, true)}</b>${height ? `<div class="muted small">${md(height, true)}</div>` : ""}`)}"`;
    return id === current
      ? `<span class="flow-node current" data-flow-node="${esc(id)}" aria-current="page"${title}>${md(shortName(t), true)}</span>`
      : `<a class="flow-node" data-flow-node="${esc(id)}" href="#/theory/${encodeURIComponent(id)}"${title}>${md(shortName(t), true)}</a>`;
  };
  const view = `flowview-${++FLOW_VIEWS}`;
  const rows = flowRows(cluster).map(
    (row) => `<div class="flow-row" style="--n:${row.length}">${row.map(node).join("")}</div>`);
  // Parallel flows (same two nodes) get separate lanes, drawn as curves either side of the line.
  const lanes = new Map();
  cluster.forEach((f) => lanes.set(`${f.uv}|${f.ir}`, [...(lanes.get(`${f.uv}|${f.ir}`) || []), f.key]));
  const edges = cluster.map((f) => {
    const lane = lanes.get(`${f.uv}|${f.ir}`);
    return [f.uv, f.ir, f.key, lane.indexOf(f.key), lane.length];
  });
  return `<div class="flow-view" id="${view}">
    <div class="flow-graph" data-edges="${esc(JSON.stringify(edges))}">${rows.join("")}
      <div class="flow-tip" id="${view}-tip" role="tooltip" hidden></div></div>
    <p class="small muted flow-hint">Hover over an arrow to see what drives the flow; click or tap it for the details.</p>
    <section class="flow-panel" id="${view}-panel" aria-label="Flow details" tabindex="-1" hidden></section>
    <p class="visually-hidden" aria-live="polite" data-flow-status></p></div>`;
}

/** The arrows are decoration for keyboard and screen-reader users, who reach the same details from the
 *  list or table next to each diagram; for the mouse, each arrow is a thick line that shows a preview on hover
 *  and opens the details on click. Every arrow from a theory starts at one point, marked by a dot, in the middle
 *  of the bottom of its box; arrows into a box spread along its top edge in the order they arrive from. Each
 *  arrow takes the gentlest bend (straight first) that keeps it from being mistaken for another: running along
 *  another arrow, or passing near another box's dot or arrowheads. Passing under a box is allowed but costs a
 *  little, so an arrow curves around boxes when that takes only a slight bend. Parallel flows between the same
 *  two theories take lanes either side. */
function drawFlowArrows() {
  app.querySelectorAll(".flow-graph").forEach((g) => {
    g.querySelector("svg.flow-arrows:not(.flow-dots)")?.remove();
    const box = g.getBoundingClientRect();
    const rel = (r) => ({ l: r.left - box.left, t: r.top - box.top, r: r.right - box.left, b: r.bottom - box.top });
    const selected = g.closest(".flow-view")?.dataset.selected;
    const svg = svgEl("svg", { class: "flow-arrows", width: box.width, height: box.height, "aria-hidden": "true" });
    const els = new Map([...g.querySelectorAll("[data-flow-node]")].map((n) => [n.dataset.flowNode, n]));
    els.forEach((n) => (n.style.transform = ""));
    const R = new Map([...els].map(([id, n]) => [id, rel(n.getBoundingClientRect())]));
    const cx = (id) => (R.get(id).l + R.get(id).r) / 2;
    // Shift a box sideways (top row first) when that takes it out from under arrows that aren't its own,
    // keeping clear of its neighbours and inside the diagram.
    const E = JSON.parse(g.dataset.edges);
    const shift = (id, dx) => { const r = R.get(id); return { ...r, l: r.l + dx, r: r.r + dx }; };
    const crossing = (id, r) => E.filter(([u, v]) => u !== id && v !== id).filter(([u, v]) => {
      const [a, b] = [R.get(u), R.get(v)];
      const [x1, y1, x2, y2] = [(a.l + a.r) / 2, a.b, (b.l + b.r) / 2, b.t];
      if (Math.min(y1, y2) > r.b || Math.max(y1, y2) < r.t) return false;
      const x = (y) => x1 + ((x2 - x1) * (y - y1)) / (y2 - y1 || 1);
      const [xa, xb] = [x(Math.max(r.t, Math.min(y1, y2))), x(Math.min(r.b, Math.max(y1, y2)))];
      return Math.max(xa, xb) > r.l - 10 && Math.min(xa, xb) < r.r + 10;
    }).length;
    for (const [id] of [...R].sort((a, b) => a[1].t - b[1].t)) {
      const r0 = R.get(id);
      const row = [...R].filter(([o, r]) => o !== id && r.t < r0.b && r.b > r0.t).map(([, r]) => r);
      let best = { cost: crossing(id, r0), dx: 0 };
      for (const dx of [40, -40, 80, -80, 120, -120, 160, -160, 200, -200, 240, -240]) {
        const r = shift(id, dx);
        if (r.l < 30 || r.r > box.width - 30 || row.some((o) => r.l < o.r + 24 && o.l < r.r + 24)) continue;
        const cost = crossing(id, r) + Math.abs(dx) / 400;
        if (cost < best.cost - 0.2) best = { cost, dx };
      }
      if (best.dx) { R.set(id, shift(id, best.dx)); els.get(id).style.transform = `translateX(${best.dx}px)`; }
    }
    const arrows = E.map(([uv, ir, key, lane, n]) => ({ uv, ir, key,
      lane: (lane - (n - 1) / 2) * 112, x1: cx(uv), y1: R.get(uv).b, x2: cx(ir), y2: R.get(ir).t }));
    // A course bent `off` px sideways at its middle (quadratic), and points along it.
    const course = (A, off) => {
      const len = Math.hypot(A.x2 - A.x1, A.y2 - A.y1) || 1;
      return [(A.x1 + A.x2) / 2 - (2 * off * (A.y2 - A.y1)) / len, (A.y1 + A.y2) / 2 + (2 * off * (A.x2 - A.x1)) / len];
    };
    const sample = (A, [qx, qy]) => { const n = Math.ceil(Math.hypot(A.x2 - A.x1, A.y2 - A.y1) / 4);
      return [...Array(n + 1).keys()].map((i) => { const s = i / n;
        return [(1 - s) ** 2 * A.x1 + 2 * (1 - s) * s * qx + s * s * A.x2, (1 - s) ** 2 * A.y1 + 2 * (1 - s) * s * qy + s * s * A.y2]; }); };
    const into = new Map();
    arrows.forEach((A) => into.set(A.ir, [...(into.get(A.ir) || []), A]));
    const dots = [...new Set(arrows.map((A) => A.uv))].map((id) => [cx(id), R.get(id).b, id]);
    // Colour: arrows from one theory share a colour with its dot. The theories with several arrows out, the
    // busiest first (then top to bottom, left to right), take the four flow colours in fixed order; the rest
    // keep the site's green.
    const outs = (id) => arrows.filter((A) => A.uv === id).length;
    const hue = new Map(dots.map(([, , id]) => id).filter((id) => outs(id) > 1)
      .sort((a, b) => outs(b) - outs(a) || R.get(a).t - R.get(b).t || cx(a) - cx(b)).slice(0, 4).map((id, i) => [id, ` c${i + 1}`]));
    // The box takes the colour of its arrows.
    els.forEach((n, id) => { n.classList.remove("c1", "c2", "c3", "c4"); if (hue.has(id)) n.classList.add(hue.get(id).trim()); });
    const confusable = (A, p) => [...dots, ...arrows.map((B) => [B.x2, B.y2, B.ir])].some(([x, y, id]) =>
      id !== A.uv && id !== A.ir && p.some(([px, py]) => Math.hypot(px - x, py - y) < 14));
    const runsAlong = (p, q) => { // p stays within 6px of q for 20px or more
      let run = 0;
      for (let i = 1; i < p.length; i++) {
        const close = q.some(([x, y]) => Math.hypot(x - p[i][0], y - p[i][1]) < 6);
        run = close ? run + Math.hypot(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]) : 0;
        if (run >= 20) return true;
      }
      return false;
    };
    const under = (A, p) => [...R].filter(([id, o]) => id !== A.uv && id !== A.ir &&
      p.some(([x, y]) => x > o.l - 4 && x < o.r + 4 && y > o.t - 4 && y < o.b + 4)).length;
    const mid = box.width / 2;
    const offs = [0, ...[10, 20, 30, 40, 55, 70, 85, 100].flatMap((d) => [d, -d])];
    // Two passes: arrowheads ordered along each box's top by where the arrows come from (first the straight
    // courses, then the bent ones), and bends chosen for that order.
    for (let pass = 0; pass < 2; pass++) {
      for (const [id, list] of into) {
        const r = R.get(id), w = Math.min(r.r - r.l - 16, 22 * (list.length - 1));
        const from = (A) => { const [qx] = A.q ?? course(A, A.lane); return 0.36 * A.x1 + 0.48 * qx + 0.16 * A.x2 - 1e-3 * A.y1; };
        list.sort((a, b) => from(a) - from(b));
        list.forEach((A, i) => { A.x2 = list.length > 1 ? cx(id) - w / 2 + (w * i) / (list.length - 1) : cx(id); });
      }
      const done = [];
      for (const A of [...arrows].sort((a, b) => Math.hypot(a.x2 - a.x1, a.y2 - a.y1) - Math.hypot(b.x2 - b.x1, b.y2 - b.y1))) {
        const outward = Math.sign((A.x1 + A.x2) / 2 - mid) || 1; // a tie bends away from the diagram's middle
        let best = null;
        for (const off of offs) {
          const q = course(A, A.lane + off), p = sample(A, q);
          const bad = confusable(A, p) || done.some((B) => runsAlong(p, B.p));
          const side = off * (A.y2 > A.y1 ? -1 : 1); // > 0 bends right
          const cost = (bad ? 1000 : 0) + 30 * under(A, p) + Math.abs(off) + (off && Math.sign(side) !== outward ? 0.5 : 0);
          if (!best || cost < best.cost) best = { cost, q, p };
        }
        [A.q, A.p] = [best.q, best.p];
        done.push(A);
      }
    }
    for (const A of arrows) {
      const [qx, qy] = A.q;
      const t = Math.hypot(A.x2 - qx, A.y2 - qy) || 1;
      const [ux, uy] = [(A.x2 - qx) / t, (A.y2 - qy) / t];
      const [bx, by] = [A.x2 - 10 * ux, A.y2 - 10 * uy];
      const d = `M${A.x1},${A.y1} Q${qx},${qy} ${bx},${by}`;
      const on = A.key === selected ? " selected" : "";
      // The wide invisible copy comes first, so hovering it can thicken the visible line after it (CSS +).
      svgEl("path", { d, class: "flow-hit", "data-flow-open": A.key }, svg);
      const c = hue.get(A.uv) ?? "";
      svgEl("path", { d, class: `flow-line${on}${c}`, "data-flow-line": A.key }, svg);
      svgEl("polygon", { points: `${A.x2},${A.y2} ${bx - 5 * uy},${by + 5 * ux} ${bx + 5 * uy},${by - 5 * ux}`, class: `flow-head${on}${c}`, "data-flow-line": A.key }, svg);
    }
    // Dots go on their own layer above the boxes.
    g.querySelector(".flow-dots")?.remove();
    const top = svgEl("svg", { class: "flow-arrows flow-dots", width: box.width, height: box.height, "aria-hidden": "true" });
    for (const [x, y, id] of dots) svgEl("circle", { cx: x, cy: y, r: 4, class: `flow-dot${hue.get(id) ?? ""}` }, top);
    g.prepend(svg);
    g.append(top);
  });
}

/* Flow details: the panel opened from an arrow or from the list next to the diagram. */

/** The references a flow cites, numbered for the panel. Keys are always the UV entry's. */
function flowSources(f) {
  const uv = BY_ID.get(f.uv);
  const fl = f.flow || {};
  const keys = [];
  const add = (ks) => (ks || []).map((k) => splitRef(k)[0]).forEach((k) => keys.includes(k) || keys.push(k));
  add(fl.identification?.refs);
  add(fl.identification?.competing_refs);
  ["deformations", "vevs", "tuned", "symmetry_changes"].forEach((s) => (fl[s] || []).forEach((x) => add(x.refs)));
  add(fl.spectrum?.refs);
  (fl.spectrum?.particles || []).forEach((p) => add(p.refs));
  add(fl.integrability?.refs);
  const refs = keys.map((k) => (uv.references || []).find((r) => r.key === k)).filter(Boolean);
  // An item's sources, or "standard" for a textbook statement.
  const cite = (ks, x = {}) =>
    (ks || []).map(splitRef).map(([k, loc]) => [keys.indexOf(k), loc]).filter(([i]) => i >= 0)
      .map(([i, loc]) => `<span class="cite">[${i + 1}${loc ? `, ${md(loc, true)}` : ""}]</span>`).join("") +
    (x.standard ? ' <span class="muted small">(standard)</span>' : "");
  return { refs, cite };
}

function spectrumSummary(sp) {
  if (sp.summary) return md(sp.summary, true);
  const parts = [];
  const ps = sp.particles || [];
  if (ps.length) {
    const names = new Set(ps.map((p) => p.label));
    const stable = new Set(ps.filter((p) => p.stable).map((p) => p.label));
    parts.push(`${names.size} particle${names.size > 1 ? "s" : ""}${stable.size ? ` (${stable.size} recorded stable)` : ""}`);
  }
  if (sp.vacua) parts.push(`${sp.vacua} vacu${sp.vacua > 1 ? "a" : "um"}`);
  if (sp.kinks) parts.push(`kinks: ${md(sp.kinks, true)}`);
  return parts.join("; ");
}

const NOT_RECORDED = `<span class="muted">Not recorded</span>`;
const INTEGRABILITY = { integrable: "Integrable", not_integrable: "Not integrable", open: "Open question" };
const IDENT = { established: "Established", conjectured: "Conjectured", disputed: "Disputed" };

function flowPanel(f) {
  const fl = f.flow;
  const uv = BY_ID.get(f.uv);
  const { refs, cite } = flowSources(f);
  const note = (x) => (x.note ? `<div class="sub">${md(x.note, true)}</div>` : "");
  const rows = [];
  const row = (k, v) => rows.push(`<dt>${k}</dt><dd>${v}</dd>`);
  row("From (UV)", nodeName(f.uv) + f.at);
  row("To (IR)", nodeName(f.ir) + (f.expr?.decoration ? `<div class="sub">${md(f.expr.decoration, true)}</div>` : ""));
  if (f.note) row("Description", md(f.note, true));
  if (!fl) {
    row("Details", `${NOT_RECORDED}: this flow has no structured data yet (who identified it, operator, sign, symmetry, spectrum, integrability).`);
  } else {
    const id = fl.identification;
    row("Identification", `${IDENT[id.status]}, by ${md(id.method, true)} ${cite(id.refs)}${
      id.competing_refs ? `<div class="sub">Argued otherwise: ${cite(id.competing_refs)}</div>` : ""}${note(id)}`);
    const kind = [fl.deformations?.length && "relevant deformation", fl.vevs?.length && "vacuum expectation value"].filter(Boolean);
    row("Kind", kind.join(" and ").replace(/^./, (c) => c.toUpperCase()));
    for (const d of fl.deformations || []) {
      const dims = [d.Delta != null ? tex(`\\Delta = ${d.Delta}`) : "", d.rep ? md(d.rep, true) : ""].filter(Boolean).join(", ");
      const sign = d.sign
        ? `${tex(`${d.coupling} ${SIGN_REL[d.sign]}`)} <span class="muted">(${SIGN_WORD[d.sign]})</span><div class="sub">Convention: ${md(d.sign_convention, true)}</div>`
        : `<div class="sub">Sign: ${NOT_RECORDED}</div>`;
      row("Deformation", `${tex(d.operator)}${dims ? ` <span class="muted">(${dims})</span>` : ""}, coupling ${tex(d.coupling)} ${cite(d.refs, d)}<div>${sign}</div>${note(d)}`);
    }
    for (const v of fl.vevs || [])
      row("Vev", `${tex(`\\langle ${v.operator} \\rangle \\neq 0`)}: ${md(v.direction, true)}${v.branch ? ` <span class="muted">(${md(v.branch, true)})</span>` : ""} ${cite(v.refs, v)}${note(v)}`);
    row("Tuned", fl.tuned?.length
      ? fl.tuned.map((x) => `<div>${tex(x.operator)}, coupling ${tex(x.coupling)}: ${md(x.condition, true)} ${cite(x.refs, x)}${note(x)}</div>`).join("")
      : NOT_RECORDED);
    row("Symmetry", fl.symmetry_changes?.length
      ? fl.symmetry_changes.map((s) => `<div>${md(s.from, true)} → ${md(s.to, true)} <span class="muted">(${esc(s.kind)}${
          s.vacua ? `, ${s.vacua} vacu${s.vacua > 1 ? "a" : "um"}` : ""})</span>${s.manifold ? `, vacuum manifold ${md(s.manifold, true)}` : ""} ${cite(s.refs, s)}${note(s)}</div>`).join("")
      : NOT_RECORDED);
    const sp = fl.spectrum;
    let spec = NOT_RECORDED;
    if (sp) {
      spec = `${spectrumSummary(sp)} ${cite(sp.refs, sp)}${note(sp)}`;
      // With a flow page, the full table lives there; otherwise it can be opened here.
      if (sp.particles?.length && !fl.page)
        spec += `<details class="flow-particles"><summary>Particles (${sp.particles.length} rows)</summary>${table(
          ["Particle", "Mass", "Method", ""],
          sp.particles.map((p) => [tex(p.label) + (p.rep ? ` <span class="muted">${md(p.rep, true)}</span>` : ""),
            `<span class="value">${tex(p.mass)}</span>${p.stable === true ? ' <span class="muted">stable</span>' : p.stable === false ? ' <span class="muted">unstable</span>' : ""}`,
            esc(p.method) + " " + cite(p.refs), p.note ? md(p.note, true) : ""]), "data")}</details>`;
    }
    row("Massive spectrum", spec);
    const ig = fl.integrability;
    row("Integrability", ig ? `${INTEGRABILITY[ig.status]} ${cite(ig.refs, ig)}${note(ig)}` : NOT_RECORDED);
    if (fl.page && BY_ID.get(fl.page)) row("Flow page", `<a href="#/theory/${encodeURIComponent(fl.page)}">${md(BY_ID.get(fl.page).name, true)}</a>`);
    if (fl.note) row("Notes", md(fl.note, true));
  }
  const srcList = refs.length
    ? `<ol class="refs flow-refs">${refs.map(refItem).join("").replace(/ id="ref-[^"]*"/g, "")}</ol>`
    : `<span class="muted">None recorded for this flow.</span>`;
  row("Sources", `${srcList}<div class="sub">From the references of <a href="#/theory/${encodeURIComponent(f.uv)}">${md(uv.name, true)}</a>
    (<a href="${gh.blob(uv.source)}" target="_blank" rel="noopener">source file</a>).</div>`);
  return `<div class="flow-panel-head"><h3>${nodeName(f.uv)} → ${nodeName(f.ir)}</h3>
      <button type="button" class="linkish flow-close" aria-label="Close flow details">Close ✕</button></div>
    <dl class="kv flow-facts">${rows.join("")}</dl>`;
}

/** The short text shown on hover or keyboard focus. */
/** The hover preview: short on purpose, so it never hides the diagram. Which flow, the driving operator and
 *  sign when recorded, and a pointer to the details. */
function flowPreview(f) {
  const d = f.flow?.deformations?.[0];
  const v = f.flow?.vevs?.[0];
  const what = d ? tex(d.sign ? `${d.operator},\ ${d.coupling} ${SIGN_REL[d.sign]}` : d.operator)
    : v ? tex(`\langle ${v.operator} \rangle \neq 0`) : "";
  return `<b>${esc(nodePlain(f.uv))} → ${esc(nodePlain(f.ir))}</b>${what ? `<div>${what}</div>` : ""}
    <div class="muted small">Click for description</div>`;
}

/** The diagram whose panel shows a control's flow: its own, or for a list button the one drawing that flow. */
function viewOf(el) {
  const own = el.closest(".flow-view");
  if (own) return own;
  const views = [...(el.closest("section")?.querySelectorAll(".flow-view") || [])];
  const key = el.dataset.flowOpen;
  return views.find((v) => v.querySelector(`.flow-graph [data-flow-open="${CSS.escape(key ?? "")}"]`)) ?? views[0];
}

/** Open the details of `key` in `view` (or close them if they are already open from this trigger). */
function openFlow(view, key, trigger) {
  const panel = view.querySelector(".flow-panel");
  const f = FLOW_BY_KEY.get(key);
  if (!f) return;
  if (!panel.hidden && view.dataset.selected === key && panel._trigger === trigger) return closeFlow(view, false);
  view.dataset.selected = key;
  panel._trigger = trigger;
  panel.innerHTML = flowPanel(f);
  panel.hidden = false;
  view.querySelector(".flow-tip").hidden = true;
  markSelected(view);
  view.querySelector("[data-flow-status]").textContent = `Showing details: ${edgeName(f)}`;
  panel.scrollIntoView({ block: "nearest" });
}

function closeFlow(view, restoreFocus) {
  const panel = view.querySelector(".flow-panel");
  const trigger = panel._trigger;
  panel.hidden = true;
  panel.innerHTML = "";
  delete view.dataset.selected;
  markSelected(view);
  view.querySelector("[data-flow-status]").textContent = "Flow details closed";
  if (restoreFocus && trigger?.isConnected) trigger.focus();
}

function markSelected(view) {
  const key = view.dataset.selected;
  // The list buttons may sit outside the view, in the same section.
  const scope = view.closest("section.block") ?? view;
  scope.querySelectorAll("[data-flow-open]").forEach((b) => {
    if (b.tagName === "BUTTON") b.setAttribute("aria-expanded", b.dataset.flowOpen === key);
  });
  view.querySelectorAll("[data-flow-line]").forEach((p) => p.classList.toggle("selected", p.dataset.flowLine === key));
}

function showTip(el, e = null) {
  const view = viewOf(el);
  const g = el.closest(".flow-graph");
  if (!view || !g) return;
  const tip = view.querySelector(".flow-tip");
  const f = FLOW_BY_KEY.get(el.dataset.flowOpen);
  if (!f && !el.dataset.tip) return;
  tip.innerHTML = f ? flowPreview(f) : el.dataset.tip; // an arrow's preview, or a theory box's full name
  tip.hidden = false;
  const box = g.getBoundingClientRect();
  // Next to the pointer when there is one, else under the arrow.
  const r = el.getBoundingClientRect();
  const [px, py] = e ? [e.clientX, e.clientY] : [r.left + r.width / 2, r.bottom];
  const left = Math.max(4, Math.min(px - box.left + 12, box.width - tip.offsetWidth - 4));
  tip.style.left = `${left}px`;
  tip.style.top = `${py - box.top + 14}px`;
}

function hideTip(el) {
  const tip = viewOf(el)?.querySelector(".flow-tip");
  if (tip) tip.hidden = true;
}

/** The list of flows next to a diagram, each with a button opening the same panel. */
function flowItem(f, other, at = "", withSources = false) {
  const desc = f.note ? md(f.note, true) : f.flow ? flowPreviewText(f) : "";
  let ident = "";
  if (withSources && f.flow) {
    // On a flow's own page: who identified the flow, with the papers (from the UV entry's references).
    const id = f.flow.identification;
    const refs = BY_ID.get(f.uv).references || [];
    const list = (ks) => ks.map((k) => refs.find((r) => r.key === k)).filter(Boolean).map((r) => refItem(r).replace(/ id="ref-[^"]*"/, "")).join("");
    ident = `<div class="sub">Identification: ${IDENT[id.status]}, by ${md(id.method, true)}.</div><ol class="refs flow-refs">${list(id.refs)}</ol>${
      id.competing_refs ? `<div class="sub">Argued otherwise:</div><ol class="refs flow-refs">${list(id.competing_refs)}</ol>` : ""}`;
  }
  return `<li>${nodeName(other)}${at}${desc ? ` <span class="muted">— ${desc}</span>` : ""}
    <button type="button" class="linkish flow-open" data-flow-open="${esc(f.key)}" aria-expanded="false"
      aria-label="Details of the ${esc(edgeName(f).replace(/^Flow/, "flow"))}">details</button>${ident}</li>`;
}

function flowPreviewText(f) {
  const fl = f.flow;
  return [...(fl.deformations || []).map((d) => `${tex(d.operator)}${d.sign ? `, ${tex(`${d.coupling} ${SIGN_REL[d.sign]}`)}` : ""}`),
    ...(fl.vevs || []).map((v) => `vev ${tex(`\\langle ${v.operator} \\rangle`)}`)].join("; ");
}

/** The flows a theory page shows: from and to it, composite IRs it is part of, and flows its page describes. */
function theoryFlows(t) {
  const flows = allFlows();
  return {
    from: flows.filter((f) => f.ir === t.id),
    to: flows.filter((f) => f.uv === t.id),
    part: flows.filter((f) => f.expr && exprLeaves(f.expr).some((x) => x.entry === t.id)),
    page: flows.filter((f) => f.flow?.page === t.id),
  };
}

function flowList(t, fs) {
  const groups = [
    ["Flows from (UV)", fs.from.map((f) => flowItem(f, f.uv, linkAt(t, { target: f.uv, at: f.rel.at, variant: f.rel.variant })))],
    ["Flows to (IR)", fs.to.map((f) => flowItem(f, f.ir, linkAt(t, f.rel)))],
    ["Part of a composite IR", fs.part.map((f) => flowItem(f, f.ir, ` <span class="muted">(from ${nodeName(f.uv)})</span>`))],
    ["Flows described on this page", fs.page.map((f) => flowItem(f, f.ir, ` <span class="muted">(from ${nodeName(f.uv)})</span>`, true))],
  ].filter(([, items]) => items.length);
  return `<dl class="kv relations">${groups.map(([title, items]) => `<dt>${title}</dt><dd><ul>${items.join("")}</ul></dd>`).join("")}</dl>`;
}

function viewFlows() {
  document.title = "RG Flows — QFT Zoo";
  citeStart();
  const flows = allFlows();
  const dimOf = (c) => Math.min(...c.flatMap((f) => [nodeDim(f.uv), nodeDim(f.ir)]));
  const clusters = flowClusters(flows).sort((a, b) => dimOf(a) - dimOf(b));
  const nTheories = new Set(flows.flatMap((f) => [f.uv, ...(f.expr ? exprLeaves(f.expr).map((x) => x.entry) : [f.ir])])).size;
  const details = (f) => `<button type="button" class="linkish flow-open" data-flow-open="${esc(f.key)}" aria-expanded="false"
      aria-label="Details of the ${esc(edgeName(f).replace(/^Flow/, "flow"))}">details</button>`;
  app.innerHTML = `
    <header class="theory-head">
      <h1>RG Flows</h1>
      <p class="lede">Surf the zoo along its renormalization-group flows, from the UV at the top to the IR at the bottom.
        Open a theory and its page shows where it flows to and from.</p>
      <p class="small muted">${flows.length} flows among ${nTheories} theories so far. Height in a diagram follows the quantity
        that decreases along flows (${tex("c")} in 2d, ${tex("F")} in 3d, ${tex("a")} in 4d) where it is recorded, and otherwise a
        rough count of UV degrees of freedom; it is not an energy scale. Hover over an arrow, or select “details” in a table,
        to see what drives the flow. Know one that’s missing? Add a <code>flows_to</code> relation to the UV theory’s entry:
        see <a href="#/contribute">Contribute</a>.</p>
    </header>
    ${clusters
      .map((c) => `<section class="block"><h2>${tex(`d = ${dimOf(c)}`)}</h2>${flowDiagram(c)}
        ${table(["UV", "IR", "Deformation", ""], c.map((f) => [nodeName(f.uv) + f.at, nodeName(f.ir),
          f.note ? md(f.note, true) : f.flow ? flowPreviewText(f) : "", details(f)]), "data")}</section>`)
      .join("")}`;
  // The papers cited in the flow descriptions above (CITES filled while they were rendered).
  if (CITES.list.length) app.insertAdjacentHTML("beforeend", section("references", "References", citeList()));
  drawFlowArrows();
}

/** A page explaining an operation used in composite flow targets (data/operations/). */
function viewOperation(id) {
  const o = (DB.operations || []).find((x) => x.id === id);
  if (!o) return viewNotFound(`No operation page “${id}”.`);
  document.title = `${plain(o.name)} — QFT Zoo`;
  const op = Object.keys(OPERATION).find((k) => OPERATION[k].page === id);
  const uses = op ? allFlows().filter((f) => f.expr && JSON.stringify(f.expr).includes(`"operation":"${op}"`)) : [];
  app.innerHTML = `
    <nav class="crumbs"><a href="#/flows">← RG flows</a></nav>
    <header class="theory-head"><h1>${md(o.name, true)}</h1><p class="lede">${md(o.summary, true)}</p></header>
    ${section("overview", "Definition", `<div class="prose">${md(o.description)}</div>`)}
    ${uses.length ? section("uses", "Flows ending in such a theory", `<ul>${uses.map((f) => `<li>${nodeName(f.uv)} → ${nodeName(f.ir)}</li>`).join("")}</ul>`) : ""}
    ${section("references", "References", `<ol class="refs">${o.references.map(refItem).join("")}</ol>`)}
    <p class="muted small">Source: <a href="${gh.blob(o.source)}" target="_blank" rel="noopener"><code>${esc(o.source)}</code></a></p>`;
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
  const p = paramTex(f.parameter || "m");
  const values = [...new Set(t.members.map((m) => String(m.at)))];
  const shown = new Set(values.slice(0, f.show || 8));
  const hasVariant = t.members.some((m) => m.variant);
  const hasLabel = t.members.some((m) => m.label);
  const hasNotes = t.members.some((m) => m.entries?.length || m.note);
  // c and the gap are 2d data; families in other dimensions omit these columns.
  const hasC = t.members.some((m) => m.c != null);
  const hasGap = t.members.some((m) => m.gap != null);
  const specIndex = new Map((t.spectra || []).map((r, i) => [`${r.at}|${r.variant ?? ""}`, i]));
  const head = [tex(p), ...(hasVariant ? ["Variant"] : []), ...(hasLabel ? ["Theory"] : []),
    ...(hasC ? [tex("c")] : []), ...(hasGap ? [tex("\\Delta_{\\rm gap}")] : []),
    ...(hasNotes ? ["Entry / notes"] : []), ...(specIndex.size ? ["Spectrum"] : [])];
  const rows = t.members.map((m) => {
    const entries = (m.entries || [])
      .map((id) => `<a href="#/theory/${encodeURIComponent(id)}">${md(BY_ID.get(id)?.name ?? id, true)}</a>`)
      .join(", ");
    const notes = [entries, m.note ? md(m.note, true) : ""].filter(Boolean).join(" · ");
    const cells = [tex(m.at), ...(hasVariant ? [esc(m.variant ?? "")] : []), ...(hasLabel ? [md(m.label, true)] : []),
      ...(hasC ? [m.c != null ? tex(m.c) : ""] : []), ...(hasGap ? [m.gap != null ? tex(m.gap) : ""] : []),
      ...(hasNotes ? [notes] : [])];
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

function refItem(r, id = null) {
  const links = [];
  if (r.arxiv) links.push(`<a href="https://arxiv.org/abs/${encodeURI(r.arxiv)}" target="_blank" rel="noopener">arXiv:${esc(r.arxiv)}</a>`);
  if (r.doi) links.push(`<a href="https://doi.org/${encodeURI(r.doi)}" target="_blank" rel="noopener">DOI</a>`);
  if (r.url) links.push(`<a href="${esc(safeUrl(r.url))}" target="_blank" rel="noopener">link</a>`);
  const q = r.arxiv ? `arxiv:${r.arxiv}` : r.doi ? `doi:${r.doi}` : null;
  if (q) links.push(`<a href="https://inspirehep.net/literature?q=${encodeURIComponent(q)}" target="_blank" rel="noopener">INSPIRE</a>`);
  return `<li id="ref-${esc(id ? `${id}/${r.key}` : r.key)}">${r.authors ? `${esc(r.authors)}, ` : ""}<em>${md(r.title, true)}</em>${
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
      <p>How each number was obtained is given by a method abbreviation (${methodHtml("CB")}, ${methodHtml("MC-BC, isotropic")}, …),
      listed with explanations on the <a href="#/methods">Methods</a> page.</p>
      <p>The complete dataset is available as <a href="data/theories.json">one JSON file</a> for use in your own code.</p></div>`
    )}`;
}

/* ----------------------------------------------------------- methods view */

function viewMethods(focus = null) {
  document.title = "Methods — QFT Zoo";
  const list = DB.methods || [];
  // Each method followed by its sub-methods (parent: in data/methods.yaml), in file order.
  const kids = (abbr) => list.filter((m) => (m.parent ?? null) === abbr);
  const ordered = [];
  const walk = (m, depth) => { ordered.push([m, depth]); kids(m.abbr).forEach((k) => walk(k, depth + 1)); };
  kids(null).forEach((m) => walk(m, 0));
  const n = (k, one, many) => `${k} ${k === 1 ? one : many}`;
  const rows = ordered.map(([m, depth]) => {
    const used = m.entries.map((id) => `<a href="#/theory/${encodeURIComponent(id)}">${md(BY_ID.get(id)?.name ?? id, true)}</a>`);
    const usage = m.rows
      ? `<details class="method-uses"><summary>${n(m.rows, "row", "rows")}, ${n(m.entries.length, "entry", "entries")}</summary>${used.join(", ")}</details>`
      : `<span class="muted">none yet</span>`;
    const links = (m.links || []).map((l) => `<div class="method-link"><a href="${esc(safeUrl(l.url))}" target="_blank" rel="noopener">${esc(l.label)}</a></div>`).join("");
    return `<tr id="method-${esc(m.abbr)}" class="${m.abbr === focus ? "flash" : ""}">
      <td class="method-abbr" style="padding-left:${10 + 18 * depth}px">${depth ? '<span class="muted" aria-hidden="true">└ </span>' : ""}<b>${esc(m.abbr)}</b></td>
      <td><b>${md(m.name, true)}</b>${m.parent ? `<div class="sub">A kind of <a href="#/methods/${encodeURIComponent(m.parent)}">${esc(m.parent)}</a></div>` : ""}</td>
      <td>${md(m.description, true)}</td>
      <td class="small">${links}</td>
      <td class="small">${usage}</td></tr>`;
  });
  const legacy = DB.theories.reduce((k, t) =>
    k + [...(t.quantities || []), ...(t.operators || []), ...(t.three_point_functions || []).flatMap((c) => c.values)].filter((x) => x.method && !METHODS.has(String(x.method).split(",")[0].trim())).length, 0);
  app.innerHTML = `
    <header class="theory-head"><h1>Methods</h1>
      <p class="lede">How the numbers in the zoo were obtained. Data rows name a method by its abbreviation,
      sometimes followed by a short qualifier: ${methodHtml("CB, rigorous")} is the numerical conformal bootstrap with
      rigorous errors, ${methodHtml("MC-BC, isotropic")} Monte Carlo of an improved Blume–Capel model also tuned for isotropy.</p>
    </header>
    <div class="table-wrap"><table class="data methods">
      <thead><tr><th>Abbr.</th><th>Method</th><th>Description</th><th>Explained in</th><th>Used in</th></tr></thead>
      <tbody>${rows.join("")}</tbody></table></div>
    <p class="muted small">The list is <a href="${gh.blob("data/methods.yaml")}" target="_blank" rel="noopener"><code>data/methods.yaml</code></a>;
      to add a method, see the <a href="${gh.blob("CONTRIBUTING.md")}#methods" target="_blank" rel="noopener">contributing guide</a>.
      ${legacy ? `${n(legacy, "row still describes its", "rows still describe their")} method in free text.` : ""}</p>`;
  if (focus) requestAnimationFrame(() => document.getElementById(`method-${focus}`)?.scrollIntoView({ block: "center" }));
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
  [CITES, CITE_OWNER] = [null, null]; // each page starts its own reference list
  const [page, arg] = location.hash.replace(/^#\/?/, "").split("/");
  if (!page) viewHome();
  else if (page === "catalogue") {
    if (arg) applyCatalogueLink(decodeURIComponent(arg));
    viewBrowse();
  } else if (page === "tables") viewTables();
  else if (page === "flows") viewFlows();
  else if (page === "feedback") viewFeedback();
  else if (page === "theory" && arg) viewTheory(decodeURIComponent(arg));
  else if (page === "operation" && arg) viewOperation(decodeURIComponent(arg));
  else if (page === "contribute") viewContribute();
  else if (page === "landscape") viewLandscape();
  else if (page === "methods") viewMethods(arg ? decodeURIComponent(arg) : null);
  else viewNotFound();
  document.querySelectorAll("[data-nav]").forEach((a) =>
    a.classList.toggle("active", a.dataset.nav === (page === "theory" ? "catalogue" : page === "operation" ? "flows" : page))
  );
  window.scrollTo(0, 0);
}

window.addEventListener("resize", drawFlowArrows);
// Boxes change size after the first drawing (math fonts, KaTeX styles): redraw so arrows meet them exactly.
const FLOW_RESIZE = new ResizeObserver(() => requestAnimationFrame(drawFlowArrows));
new MutationObserver(() => app.querySelectorAll(".flow-node").forEach((n) => FLOW_RESIZE.observe(n)))
  .observe(app, { childList: true, subtree: true });
document.fonts?.addEventListener?.("loadingdone", drawFlowArrows);

app.addEventListener("change", (e) => {
  if (e.target.id === "spectrum-member" && SPEC_STATE.t) showSpectrum(SPEC_STATE.t, +e.target.value);
});

// Labels with a second notation (`data-hover`, e.g. a multiplet's CDI label): an instant tooltip on hover or focus.
const HOVER_TIP = Object.assign(document.createElement("div"), { className: "hover-tip", role: "tooltip", hidden: true });
document.body.append(HOVER_TIP);
function showHover(el) {
  HOVER_TIP.innerHTML = el.dataset.hover;
  HOVER_TIP.hidden = false;
  const r = el.getBoundingClientRect();
  const left = Math.max(4, Math.min(r.left, document.documentElement.clientWidth - HOVER_TIP.offsetWidth - 4));
  const below = r.bottom + 6 + HOVER_TIP.offsetHeight <= window.innerHeight;
  HOVER_TIP.style.left = `${left}px`;
  HOVER_TIP.style.top = `${below ? r.bottom + 6 : r.top - HOVER_TIP.offsetHeight - 6}px`;
}
const hideHover = () => (HOVER_TIP.hidden = true);
for (const [on, off] of [["mouseover", "mouseout"], ["focusin", "focusout"]]) {
  app.addEventListener(on, (e) => {
    const el = e.target.closest("[data-hover]");
    if (el) showHover(el);
  });
  app.addEventListener(off, (e) => {
    const el = e.target.closest("[data-hover]");
    if (el && !el.contains(e.relatedTarget)) hideHover();
  });
}
window.addEventListener("scroll", hideHover, { passive: true });
window.addEventListener("hashchange", hideHover);

// Flow arrows: a preview on hover; click or tap opens the details (keyboard: the "details" buttons by the diagram).
app.addEventListener("mouseover", (e) => {
  const el = e.target.closest(".flow-graph [data-flow-open], .flow-graph [data-tip]");
  if (el) showTip(el, el.dataset.tip ? null : e);
});
app.addEventListener("mouseout", (e) => {
  const el = e.target.closest(".flow-graph [data-flow-open], .flow-graph [data-tip]");
  if (el && !el.contains(e.relatedTarget)) hideTip(el);
});
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  const open = [...app.querySelectorAll(".flow-panel:not([hidden])")];
  app.querySelectorAll(".flow-tip:not([hidden])").forEach((t) => (t.hidden = true));
  hideHover();
  if (!open.length) return;
  // Close the panel the focus is in or came from, else every open one.
  const here = open.filter((p) => p.contains(document.activeElement) || p._trigger === document.activeElement);
  (here.length ? here : open).forEach((p) => closeFlow(p.closest(".flow-view"), p.contains(document.activeElement)));
});

// Clicks shared by all views: citation links, tag pills, "show more" members / rows.
app.addEventListener("click", (e) => {
  const flowOpen = e.target.closest("[data-flow-open]");
  if (flowOpen) {
    const view = viewOf(flowOpen);
    const trigger = flowOpen.tagName === "BUTTON" ? flowOpen : null; // the focus returns to a button on close
    if (view) openFlow(view, flowOpen.dataset.flowOpen, trigger);
    return;
  }
  const flowClose = e.target.closest(".flow-close");
  if (flowClose) {
    closeFlow(flowClose.closest(".flow-view"), true);
    return;
  }
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
    for (const m of DB.methods || []) METHODS.set(m.abbr, m);
    document.getElementById("repo-link").href = gh.repo();
    document.getElementById("footer").innerHTML =
      `QFT Zoo — an open catalogue of quantum field theories. ` +
      `<a href="${gh.repo()}" target="_blank" rel="noopener">Source &amp; data on GitHub</a> · ` +
      `<a href="#/methods">Methods</a> · ` +
      `${DB.theories.length} theories · built ${esc(DB.generated)}`;
    window.addEventListener("hashchange", route);
    route();
  })
  .catch((err) => {
    app.innerHTML = `<div class="error"><p><b>Could not load the data</b> (${esc(err.message)}).</p>
      <p>If you opened <code>index.html</code> directly from disk, run
      <code>python scripts/build.py --serve</code> and visit <code>http://localhost:8000</code> instead.</p></div>`;
  });
