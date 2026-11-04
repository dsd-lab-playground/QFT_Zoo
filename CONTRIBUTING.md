# Contributing to the QFT Zoo

Thank you for helping! There are three ways to contribute, from easiest to most
flexible:

1. **Suggest via a form**: open a [new-theory issue](https://github.com/nathansbenjamin/QFT_Zoo/issues/new?template=new-theory.yml)
   or a [correction](https://github.com/nathansbenjamin/QFT_Zoo/issues/new?template=correction.yml). No YAML needed.
2. **Edit on GitHub in the browser**: use *Edit this entry* on any theory page, or
   *Add a theory* on the home page (it opens GitHub's editor pre-filled with the
   template). GitHub forks the repository for you; commit and open a pull request.
3. **Work locally**: fork, clone, edit, then
   ```bash
   pip install -r requirements.txt
   python scripts/build.py --serve     # preview at http://localhost:8000
   ```
   and open a pull request.

Every pull request is checked automatically, then reviewed by a maintainer before
merging. Once merged, the website updates within a minute or two.

## Adding a theory

Copy [`data/TEMPLATE.yaml`](data/TEMPLATE.yaml) to `data/theories/<id>.yaml`, where
`<id>` is a short lowercase slug such as `o2-3d` or `n4-sym`. The `id:` field must
match the filename. See the existing entries for worked examples, e.g.
[`ising-3d.yaml`](data/theories/ising-3d.yaml).

### Fields

| Field | Required | Content |
|---|---|---|
| `id` | yes | slug, equal to the filename |
| `name` | yes | display name (Markdown, may contain `$...$`) |
| `aliases` | | other names; used by search |
| `d` | yes | spacetime dimension |
| `summary` | yes | one or two sentences for the catalogue table |
| `tags` | yes | from the list in [`schema/theory.schema.json`](schema/theory.schema.json) |
| `description` | | longer Markdown text; a `### Title` line starts a separate section, shown after the data and listed in the page's contents bar |
| `lagrangian` | | LaTeX, shown in display mode |
| `parameters` | | `symbol`, `description`, `range` |
| `family` | | marks the entry as a family of theories (see *Families* below) |
| `symmetry` | | `spacetime`, `supercharges` (number of real Poincaré supercharges), `global`, `gauge`, `notes` |
| `quantities` | | central charges, exponents, OPE coefficients, …: `key`, `symbol`, `description`, `value`, `method`, `refs`, `note` |
| `operators` | | `name`, `Delta`, `spin`, `weights` (2d: `(h, \bar h)`), `degeneracy`, `rep`, `method`, `refs`, `note` |
| `relations` | | `type`, `target`, `at`, `variant`, `note` (see below) |
| `references` | yes | `key`, `title`, `authors`, `year`, `journal`, `note`, and at least one of `arxiv` / `doi` / `url` |
| `contributors` | | GitHub usernames |

### Writing LaTeX in YAML

- **Wrap LaTeX in single quotes**: `global: '$\mathbb{Z}_2$'`. In single-quoted
  YAML, backslashes are literal. (Inside double quotes you would need `\\`.) To use
  a literal `'` inside single quotes, write `''`.
- For multi-line text use a block scalar (`description: |`), which also keeps
  backslashes literal.
- **Prose fields** (`name`, `summary`, `description`, `note`, `rep`, `global`, …)
  are Markdown: write math as `$...$` or `$$...$$`.
- **Math-only fields** (`lagrangian`, `symbol`, operator `name`, `value`,
  `Delta`, `spin`) are typeset as math automatically: **no `$` signs**.

### Numbers and uncertainties

- Write values as quoted strings so trailing digits survive:
  `Delta: '0.518148806(24)'` (the digits in parentheses are the uncertainty in the
  last digits).
- Exact values are LaTeX: `value: '\frac{1}{2}'`.
- Give a `method` (`exact`, `conformal bootstrap`, `Monte Carlo`,
  `epsilon-expansion`, `perturbation theory`, `derived`, …) and `refs: [key]`
  pointing to an entry in the theory's `references` list.

### Standard data keys (2d CFTs and the landscape plot)

Give a quantity a `key` when it has a standard meaning, so it can be sorted and
plotted. For 2d CFTs, add both of these and the theory appears on the
[landscape plot](https://nathansbenjamin.github.io/QFT_Zoo/#/landscape):

```yaml
quantities:
  - key: c                   # Virasoro central charge, c_L = c_R
    symbol: 'c'
    value: '8/7'             # exact rational: write a/b
    method: exact
  - key: gap                 # dimension h + hbar of the lightest non-vacuum Virasoro primary
    symbol: '\Delta_{\rm gap}'
    value: '4/35'
    method: exact
```

Other keys: `a`, `C_T`, `F`. Each key may appear once per entry.

### Families

An infinite or continuous family (minimal models, parafermions, the $c=1$ circle
line, …) is **one entry** with a `family` block, not one file per member.

- **Closed form** (infinite discrete families). Give the first value and step, plus
  formulas in plain arithmetic (`+ - * / **`, parentheses). The build evaluates
  them exactly and lists the members on the page and in the plot:
  ```yaml
  family:
    parameter: m
    start: 4                 # m = 4, 5, 6, ...
    step: 1
    formulas: {c: '3/2 - 6/(m*(m+1))', gap: '3/(2*m*(m+1))'}
    variants: ['+', '-']     # optional: several theories per value of m
    overrides:               # members where the closed form fails
      - {at: 5, gap: '1/8', note: 'Ising spin field is lighter.'}
    show: 8                  # values listed before "show more"
  ```
- **Explicit list** (finite families, or special points of a continuous family):
  `members: [{at: 11, label: '$(A_{10}, E_6)$', c: '21/22', gap: '5/88'}, …]`.
  The `at` value can be LaTeX, e.g. `'\sqrt{2}'`.
- **Continuous families** at fixed $c$ also give `span: {c: '1', gap: ['0', '1/2']}`,
  drawn as a bar on the landscape plot.

A notable member gets its own entry and points back to its family with
`{type: member_of, target: <family id>, at: <value>}` (plus `variant` if needed).
The family's members table then links to it, and the plot uses the family colour.

### Relations

List a relation **once**, on one of the two theories; the reverse link is shown
automatically on the other page. `at` (and `variant`) name a specific member when
the target is a family.

| `type` | Meaning | Shown on the target as |
|---|---|---|
| `member_of` | this theory is a member of the `target` family | *Members with their own page* |
| `orbifold_of` | this theory is an orbifold (gauging of a finite symmetry) of `target` | *Orbifolds* |
| `product_of` | `target` is a tensor factor of this theory | *Appears as a factor in* |
| `same_partition_function` | equal torus partition functions (not necessarily the same CFT) | *Same torus partition function as* |
| `flows_to` | this theory (UV) flows to `target` (IR) | *Flows from (UV)* |
| `dual_to` | the two theories are dual | *Dual to* |
| `related_to` | any other connection; explain in `note` | *Related to* |

### References

Every entry needs at least one reference. If no paper contains the specific theory
yet, cite the papers that supply its ingredients and say so with
`note: construction ingredients`.

### New tags or fields

Tags come from a fixed list so that filtering stays consistent. To add one, add it
to the `tags` enum in `schema/theory.schema.json` in the same pull request.
Proposals for new fields are welcome; open an issue to discuss them.

## Spectra of 2d CFTs

A 2d CFT entry can have a torus partition function in `data/spectra/<id>.json`
(for a family member: `data/spectra/<family-id>/<member>.json`, e.g.
`data/spectra/n1-minimal-ad-da/6_ADp.json` for $m = 6$, variant `(A,D)+`; the
build tells you the expected path). The format is in
[`schema/spectrum.schema.json`](schema/spectrum.schema.json):

```json
{
  "theory": "tricritical-ising",
  "c": "7/10",
  "chiral_algebra": "\\mathrm{Vir}_{7/10}",
  "irreducible": true,
  "Z_tex": "Z = \\sum |\\chi_{r,s}|^2",
  "character_tex": "Rocha-Caridi characters ...",
  "description": "How Z was obtained (Markdown, $...$ math).",
  "generator": "scripts/spectra/gen_minimal.py",
  "blocks": [
    {"label": "\\chi_{1,1}", "h": "0",    "coeffs": [1, 0, 1, 1, 2, 2, 4, 4, 7]},
    {"label": "\\chi_{2,2}", "h": "3/80", "coeffs": [1, 1, 2, 3, 4, 6, 8, 11, 15]}
  ],
  "Z": [[0, 0, 1], [1, 1, 1]]
}
```

(abbreviated: the real file lists all six characters, each to higher order.)

Each block is $b(q) = q^{h - c/24}\sum_n \texttt{coeffs}[n]\, q^{n\cdot\texttt{step}}$
(`step` defaults to 1), and
$Z = \sum_{[i, j, \kappa]} \kappa\, b_i(q)\,\overline{b_j(q)}$. Blocks are usually
characters, but twined or twisted traces are fine too (then `"irreducible": false`,
and coefficients $\kappa$ may be fractions such as `"1/2"`). Give every block up to
weight about 6–8; the checks run up to the smallest weight that all blocks reach.

`python scripts/build.py --check` (and, for one file,
`python scripts/zoo_spectrum.py data/spectra/<file>.json`) verifies that:

- $Z(\tau) = Z(-1/\tau)$ numerically at three points away from $\tau = i$;
- the degeneracies are non-negative integers, spins are integers, and the vacuum is unique;
- $Z$ decomposes into Virasoro characters with non-negative integer multiplicities;
- the lightest non-vacuum Virasoro primary has the `gap` given in the theory file.

These checks are necessary but not sufficient, so say in `description` how the
spectrum was obtained, and add the generating script under `scripts/spectra/` if
you used one. The existing generators share exact $q$-series tools
(`common.py`), Virasoro/ADE/simple-current machinery (`rcft.py`) and graded affine
$SU(2)$ characters for cosets and parafermions (`su2.py`).

## Review criteria

Maintainers check that:

- the physics is correct, and every number is sourced;
- the entry renders correctly on the preview;
- the theory is not already in the zoo under another name (use `aliases`).
