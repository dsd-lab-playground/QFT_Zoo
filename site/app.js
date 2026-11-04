"use strict";
/* QFT Zoo front end: loads data/theories.json (built by scripts/build.py) and
   renders a catalogue view and one page per theory, using hash routing:
     #/                 catalogue
     #/theory/<id>      a theory
     #/contribute       how to contribute                                   */

const REL_LABEL = {
  flows_from: "Flows from (UV)",
  flows_to: "Flows to (IR)",
  dual_to: "Dual to",
  related_to: "Related to",
};

let DB = null; // { generated, repo, branch, template, theories: [...] }
const BY_ID = new Map();
const filters = { q: "", d: new Set(), tags: new Set() };
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
const plain = (s) =>
  String(s ?? "")
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

/* ------------------------------------------------------------ browse view */

let rowCache = null; // id -> rendered <tr>

function searchText(t) {
  const s = t.symmetry || {};
  return plain(
    [t.id, t.name, ...(t.aliases || []), t.summary, ...(t.tags || []), s.global, s.gauge, s.spacetime, `${t.d}d`, `d=${t.d}`].join(" ")
  ).toLowerCase();
}

function renderRow(t) {
  return `<tr data-id="${esc(t.id)}">
    <td class="name"><a href="#/theory/${encodeURIComponent(t.id)}">${md(t.name, true)}</a>
      <div class="pills">${(t.tags || []).map((g) => tagPill(g)).join("")}</div></td>
    <td class="num">${t.d}</td>
    <td class="sym">${symmetrySummary(t)}</td>
    <td class="summary">${md(t.summary, true)}</td>
  </tr>`;
}

function viewBrowse() {
  document.title = "QFT Zoo";
  const theories = DB.theories;
  const dims = [...new Set(theories.map((t) => t.d))].sort((a, b) => a - b);
  const tagCount = new Map();
  theories.forEach((t) => (t.tags || []).forEach((g) => tagCount.set(g, (tagCount.get(g) || 0) + 1)));
  const tags = [...tagCount.keys()].sort((a, b) => tagCount.get(b) - tagCount.get(a) || a.localeCompare(b));

  if (!rowCache) rowCache = new Map(theories.map((t) => [t.id, renderRow(t)]));

  app.innerHTML = `
    <section class="hero">
      <h1>QFT Zoo</h1>
      <p class="lede">An open, community-curated catalogue of quantum field theories and their data —
        symmetries, spectra, central charges, RG flows and dualities. Every entry is a plain-text file in a
        public GitHub repository, and anyone can propose additions.</p>
      <p class="actions">
        <a class="btn primary" href="${gh.newTheory()}" target="_blank" rel="noopener">Add a theory</a>
        <a class="btn" href="${gh.suggest()}" target="_blank" rel="noopener">Suggest one (no code)</a>
        <a class="btn" href="data/theories.json">Download all data (JSON)</a>
      </p>
    </section>

    <section class="controls" aria-label="Filters">
      <input id="q" type="search" placeholder="Search names, symmetries, tags…" autocomplete="off"
             aria-label="Search" value="${esc(filters.q)}">
      <div class="chips"><span class="chips-label">Dimension</span>
        ${dims.map((d) => `<button type="button" class="chip" data-d="${d}" aria-pressed="${filters.d.has(d)}">d = ${d}</button>`).join("")}
      </div>
      <div class="chips"><span class="chips-label">Tags</span>
        ${tags.map((g) => `<button type="button" class="chip" data-chip-tag="${esc(g)}" aria-pressed="${filters.tags.has(g)}">${esc(g)}</button>`).join("")}
      </div>
    </section>

    <div class="count-row"><span id="count" class="muted"></span>
      <button type="button" id="clear" class="linkish" hidden>Clear filters</button></div>

    <div class="table-wrap">
      <table class="catalogue">
        <thead><tr><th>Theory</th><th class="num">d</th><th>Symmetry</th><th>Summary</th></tr></thead>
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
  app.querySelector("#clear").addEventListener("click", () => {
    filters.q = "";
    filters.d.clear();
    filters.tags.clear();
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
      terms.every((w) => t._search.includes(w));
    const tr = app.querySelector(`tr[data-id="${CSS.escape(t.id)}"]`);
    if (tr) tr.hidden = !ok;
    shown += ok;
  }
  app.querySelectorAll("[data-d]").forEach((b) => b.setAttribute("aria-pressed", filters.d.has(+b.dataset.d)));
  app.querySelectorAll("[data-chip-tag]").forEach((b) =>
    b.setAttribute("aria-pressed", filters.tags.has(b.dataset.chipTag))
  );
  app.querySelectorAll("#rows .pill").forEach((p) => p.classList.toggle("on", filters.tags.has(p.dataset.tag)));
  const total = DB.theories.length;
  app.querySelector("#count").textContent =
    shown === total ? `${total} theories` : `${shown} of ${total} theories`;
  app.querySelector("#clear").hidden = !(filters.q || filters.d.size || filters.tags.size);
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

  if (t.operators?.length)
    out.push(
      section(
        "operators",
        "Operators",
        table(
          ["Operator", "Δ", "Spin", "Representation", "Notes", "Source"],
          t.operators.map((o) => [
            tex(o.name),
            `<span class="value">${tex(o.Delta)}</span>`,
            o.spin != null ? tex(o.spin) : "",
            md(o.rep, true),
            md(o.note, true),
            source(o),
          ]),
          "data"
        )
      )
    );

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
                  return `<li><a href="#/theory/${encodeURIComponent(l.target)}">${md(other ? other.name : l.target, true)}</a>${
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
    <nav class="crumbs"><a href="#/">← All theories</a></nav>
    <header class="theory-head">
      <h1>${md(t.name, true)}</h1>
      ${t.aliases?.length ? `<p class="aliases">Also known as: ${t.aliases.map((a) => md(a, true)).join(" · ")}</p>` : ""}
      <div class="pills"><span class="badge">d = ${t.d}</span>${(t.tags || []).map((g) => tagPill(g)).join("")}</div>
      <p class="lede">${md(t.summary, true)}</p>
      <p class="actions">
        <a class="btn" href="${gh.edit(t.source)}" target="_blank" rel="noopener">Edit this entry</a>
        <a class="btn" href="${gh.blob(t.source)}" target="_blank" rel="noopener">View source</a>
        <a class="btn" href="${gh.correction(t)}" target="_blank" rel="noopener">Report a problem</a>
      </p>
    </header>
    ${out.join("")}
    <p class="muted small">${contributors ? `Contributors: ${contributors}. ` : ""}Source:
      <a href="${gh.blob(t.source)}" target="_blank" rel="noopener"><code>${esc(t.source)}</code></a></p>`;
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
  }${r.year ? ` (${r.year})` : ""}. <span class="ref-links">${links.join(" · ")}</span></li>`;
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
      <p>The complete dataset is available as <a href="data/theories.json">one JSON file</a> for use in your own code.</p></div>`
    )}`;
}

function viewNotFound(msg = "Page not found.") {
  document.title = "Not found — QFT Zoo";
  app.innerHTML = `<header class="theory-head"><h1>Not found</h1><p class="lede">${esc(msg)}</p>
    <p><a class="btn" href="#/">Back to all theories</a></p></header>`;
}

/* ----------------------------------------------------------------- router */

function route() {
  const [page, arg] = location.hash.replace(/^#\/?/, "").split("/");
  if (!page) viewBrowse();
  else if (page === "theory" && arg) viewTheory(decodeURIComponent(arg));
  else if (page === "contribute") viewContribute();
  else viewNotFound();
  document.querySelectorAll("[data-nav]").forEach((a) =>
    a.classList.toggle("active", a.dataset.nav === (page || "browse"))
  );
  window.scrollTo(0, 0);
}

// Clicks shared by all views: citation links and tag pills.
app.addEventListener("click", (e) => {
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
      location.hash = "#/";
    }
  }
});

fetch("data/theories.json")
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
