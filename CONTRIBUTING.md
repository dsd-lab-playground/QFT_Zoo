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
| `description` | | longer Markdown text |
| `lagrangian` | | LaTeX, shown in display mode |
| `parameters` | | `symbol`, `description`, `range` |
| `symmetry` | | `spacetime`, `supercharges` (number of real Poincaré supercharges), `global`, `gauge`, `notes` |
| `quantities` | | central charges, exponents, OPE coefficients, …: `symbol`, `description`, `value`, `method`, `refs`, `note` |
| `operators` | | `name`, `Delta`, `spin`, `rep`, `method`, `refs`, `note` |
| `relations` | | `type`, `target`, `note` (see below) |
| `references` | yes | `key`, `title`, `authors`, `year`, `journal`, and at least one of `arxiv` / `doi` / `url` |
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

### Relations

List a relation **once**, on one of the two theories; the reverse link is shown
automatically on the other page.

| `type` | Meaning | Shown on the target as |
|---|---|---|
| `flows_to` | this theory (UV) flows to `target` (IR) | *Flows from (UV)* |
| `dual_to` | the two theories are dual | *Dual to* |
| `related_to` | any other connection; explain in `note` | *Related to* |

### New tags or fields

Tags come from a fixed list so that filtering stays consistent. To add one, add it
to the `tags` enum in `schema/theory.schema.json` in the same pull request.
Proposals for new fields are welcome; open an issue to discuss them.

## Review criteria

Maintainers check that:

- the physics is correct, and every number is sourced;
- the entry renders correctly on the preview;
- the theory is not already in the zoo under another name (use `aliases`).
