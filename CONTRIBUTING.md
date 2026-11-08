# Contributing to the QFT Zoo

**Read [docs/PRINCIPLES.md](docs/PRINCIPLES.md) first**: the standards every contribution follows (structured data with derived presentation, the field's standard concepts and notation, one convention site-wide, numbered citations with locators, concise pages).


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
| `symmetry` | | `spacetime`, `euclidean`, `lorentzian` (the spacetime symmetry in both signatures, see *Spacetime symmetry* below), `supercharges` (number of real Poincaré supercharges $Q$; used for sorting, not shown on the page), `global` (in words), `parity` and `global_group` (structured; see *Operator representations*), `gauge`, `notes` |
| `quantities` | | central charges, anomalies, exponents, …: `key`, `symbol`, `description`, `value`, `method`, `refs`, `note`, optional `category` and `relation` (see *How quantities are shown*) |
| `three_point_functions` | | one item per unordered triple of operators: `operators`, `values` (each with `structure`, `value`, `method`, `refs`, `note`, optional `order`, `value_of`, `symbol`); see *Three-point functions* |
| `three_point_structures` | | the three-point structures of this entry's three-point functions, beyond the standard ones, in their sources' notation: `id`, `name`, `form`, `ref`, `symbol`, `description`, `relation`, `embedding`, `basis` |
| `conventions` | | normalizations shared by one category of quantities, e.g. `central: 'C_T relative to one free real scalar'` (three-point functions define structures instead) |
| `operators` | | `name`, `Delta`, `spin`, `weights` (2d: `(h, \bar h)`), `lorentz`, `parity`, `global`, `role`, `multiplet`, `degeneracy`, `method`, `refs`, `note`; `family`, or `member_of` and `at`, for towers of operators (see *Operator representations*; older entries still use a free-text `rep`) |
| `relations` | | `type`, `target`, `at`, `variant`, `note`; for flows also `id`, `flow`, `target_expr` (see below) |
| `references` | yes | `key`, `title`, `authors`, `year`, `journal`, `note`, and at least one of `arxiv` / `doi` / `url` |
| `contributors` | | GitHub usernames |

### Spacetime symmetry

The spacetime symmetry is given in both signatures wherever the theory makes sense in both.
For $d \geq 3$, `symmetry` has three keys: `euclidean` and `lorentzian` hold the groups, and
`spacetime` the colloquial name and its qualifiers. The page shows them as one line,
"Euclidean $O(4,1)$ · Lorentzian $O(3,2)$ — 3d conformal group with parity":

```yaml
spacetime: '3d conformal group with parity'
euclidean: '$O(4,1)$'
lorentzian: '$O(3,2)$'

spacetime: '3d conformal group, no parity for $\lambda \neq 0$ (Chern–Simons level $k$)'
euclidean: '$SO(4,1)$'
lorentzian: '$SO(3,2)$'

spacetime: '4d $\mathcal{N}=4$ superconformal group (16 $Q$ + 16 $S$ supercharges), with parity at $\theta \in \{0, \pi\}$'
euclidean: '$O(5,1)$ (bosonic conformal part)'
lorentzian: '$PSU(2,2|4)$'

spacetime: '3d conformal group with parity; Euclidean only (non-unitary statistical model)'
euclidean: '$O(4,1)$'
```

In 2d the symmetry is the pair of Virasoro algebras, the same statement in either signature,
so there are no `euclidean` or `lorentzian` keys and `spacetime` says it all:

```yaml
spacetime: 'Two Virasoro algebras, $c = \bar c = \tfrac12$ — 2d conformal symmetry, with parity'
```

Conventions:

- **Euclidean signature** (`euclidean`). The conformal group of a $d$-dimensional CFT is
  written $SO(d+1,1)$: strictly its identity component, the orientation-preserving conformal
  maps of $S^d$. With a reflection symmetry it is $O(d+1,1)$ (strictly $O(d+1,1)/\{\pm 1\}$,
  since $-1$ acts trivially on the embedding-space null cone). Non-conformal theories use the
  Euclidean group $\mathbb{R}^d\rtimes SO(d)$, or $\mathbb{R}^d\rtimes O(d)$ with a reflection.
- **Lorentzian signature** (`lorentzian`). The conformal group is written $SO(d,2)$: the
  conformal maps that preserve the orientation of spacetime. That is the identity component
  $SO_0(d,2)$, generated by the conformal algebra, together with the component of CRT (the
  reflection $(t, x^1) \to (-t, -x^1)$ combined with charge conjugation, acting
  antiunitarily), which every unitary relativistic theory has by the CRT theorem. CRT is the
  continuation of the Euclidean rotation by $\pi$ in a time–space plane, so $SO(d+1,1)$
  always continues to $SO(d,2)$. $O(d,2)$ adds parity $P$ ($x^1 \to -x^1$, unitary) and
  time reversal $T$ (antiunitary); given CRT, each of them is CRT times the other, up to an
  internal symmetry, so they come together. Non-conformal theories use the Poincaré group
  $\mathbb{R}^{1,d-1}\rtimes SO(1,d-1)$ (again with the CRT component), or
  $\mathbb{R}^{1,d-1}\rtimes O(1,d-1)$ with $P$ and $T$.
- **The two match:** a Euclidean reflection is Lorentzian $P$ (equivalently $T$), so
  $O(d+1,1)$ goes with $O(d,2)$ and $SO(d+1,1)$ with $SO(d,2)$, and `spacetime` states parity
  once for both.
- **Covers.** On the Lorentzian cylinder $\mathbb{R}\times S^{d-1}$ the group that acts is
  the universal cover of $SO_0(d,2)$ (scaling dimensions need not be integers), and fermions
  carry representations of Spin or Pin covers in either signature. These are not distinguished.
- **"With parity"** means a reflection $x^1 \to -x^1$ is a symmetry, possibly combined
  with an internal symmetry (say which, e.g. "combined with charge conjugation"). Claim it only
  when the Lagrangian or a standard fact settles it (a Chern–Simons term, a parity-odd mass, a
  $\theta$ angle, or chirality breaks it). If it depends on parameters say how ("at
  $\theta \in \{0, \pi\}$"); if it is not settled, write $SO$ and "parity not recorded". Never
  guess.
- **Which theories get both.** A unitary (reflection-positive) theory has both: by
  Osterwalder–Schrader reconstruction its Euclidean correlators continue to a unitary
  Lorentzian theory, and back. A non-unitary theory is not reflection positive, so it has no
  unitary Lorentzian continuation: give `euclidean` only and add "Euclidean only" to
  `spacetime` with the reason, e.g. "Euclidean only (non-unitary statistical model)" for the
  Lee–Yang edge singularity, percolation, self-avoiding walks, loop models and branched
  polymers. Some of these still have non-unitary Lorentzian formulations (an $i\phi^3$ theory
  for Lee–Yang); the entry does not record them. If a Lorentzian form exists but its symmetry is
  unclear, omit `lorentzian` and write "Lorentzian form not recorded (reason)".
- **2d CFTs:** two Virasoro algebras, with their central charges $c$, $\bar c$; they contain the
  global conformal algebra, so no finite group is written in either signature. Parity (a
  reflection in Euclidean signature, $P$ exchanging $x^+$ and $x^-$ in Lorentzian) needs
  $c = \bar c$; holomorphic theories have one Virasoro algebra ($\bar c = 0$) and no parity.
  Supersymmetric theories have super-Virasoro algebras instead, e.g. "Two $\mathcal{N}=2$
  super-Virasoro algebras at $c = \bar c = \ldots$ — 2d $\mathcal{N}=(2,2)$ superconformal
  symmetry (4 $Q$ + 4 $S$ supercharges)". Non-unitary 2d theories also say "Euclidean only".
  Extended chiral algebras that are not spacetime symmetries ($\mathcal{W}$-algebras, current
  algebras) go under `global` or in the description.
- **Superconformal theories, $d \geq 3$:** `lorentzian` is the superconformal group under its
  usual name, whose bosonic part is $SO(d,2)$ (up to covers) times the R-symmetry:
  $OSp(\mathcal{N}|4)$ in 3d, $SU(2,2|\mathcal{N})$ ($PSU(2,2|4)$ for $\mathcal{N}=4$) in 4d,
  $F(4)$ in 5d, $OSp(8^*|2)$ or $OSp(8^*|4)$ in 6d. Euclidean real forms of these superalgebras
  are not standard (those with bosonic part containing $\mathfrak{so}(d+1,1)$ generally have a
  non-compact R-symmetry, e.g. bosonic part $\mathfrak{so}(5,1)\oplus\mathfrak{so}(5,1)$ for
  4d $\mathcal{N}=4$), so `euclidean` gives the bosonic conformal part, "$O(d+1,1)$ (bosonic
  conformal part)" or $SO(d+1,1)$; the R-symmetry goes under `global`. Give the number of real
  supercharges, Poincaré ($Q$) and superconformal ($S$), e.g. "(8 $Q$ + 8 $S$ supercharges)",
  and parity as above. Non-supersymmetric theories say nothing about supercharges.
- **Families:** say how the group depends on the parameters.
- Keep qualifiers about whether the symmetry is established (emergent Lorentz invariance,
  large $N_f$, lattice evidence, …) in `spacetime`, in parentheses after the name; they apply to
  both signatures.

The colloquial names (conformal group, conformal symmetry, Poincaré group, superconformal
group, Virasoro, parity, …) link to Wikipedia on the page automatically; don't add links
yourself.

### Operator representations

Each operator records a **representation of the full symmetry group**: its spacetime part
($\Delta$, spin or another Lorentz representation, parity) and an irrep of each factor of the
global symmetry. How the page groups the operators is a fixed policy applied to that data.
The full specification, with the label vocabulary, is
[`docs/REPRESENTATIONS.md`](docs/REPRESENTATIONS.md); in short:

```yaml
symmetry:
  global: '$SU(N_f)$ flavor, $U(1)_{\rm top}$ ...'   # in words, as before
  parity: true                                       # true | false | conditional
  global_group:                                      # the factors labels refer to; [] if none
    - {id: SU(Nf), group: SU(N_f)}
    - {id: U(1)_top, group: U(1), tex: 'U(1)_{\rm top}'}

operators:
  - name: '\bar\psi_k\psi^k'
    Delta: '2 + \frac{128}{3\pi^2 N_f} + O(N_f^{-2})'
    spin: 0
    parity: odd                                      # even | odd | pair | unknown
    global: {SU(Nf): singlet, U(1)_top: 0}           # a label for every factor, or unknown
```

- **Groups**: `Z2`, `Z_n`, `U(1)`, `O(N)`, `SO(N)`, `SU(N)`, `Sp(N)`, `S_n`, `D_n`, or `finite`
  with its irreps listed; `N` may be a parameter. **Labels**: `even`/`odd` ($\mathbb{Z}_2$);
  charges ($\mathbb{Z}_n$, $U(1)$); `singlet`, `vector`, `adjoint`, `sym(k)`, `anti(k)`,
  `Y(rows)` ($O(N)$); `fundamental`, `antifundamental`, `adjoint`, `sym(k)`, `anti(k)`,
  `'Dynkin(a,b,c)'` ($SU(N)$); `trivial`, `sign`, `standard` ($S_n$); `unknown` anywhere. The
  build rejects a label that is not an irrep of the group.
- **Parity** is stated for every operator when the theory has parity: `pair` when parity maps
  the operator to a partner in another representation (2d spin $s \neq 0$, 4d $j \neq \bar\jmath$,
  a charge reversed by parity), `unknown` rather than a guess. Time reversal (`T`) is recorded
  only where it is not fixed by parity and the other labels through CRT (rare).
- **Lorentz representations** other than symmetric traceless spin: `lorentz: '(1/2, 0)'` in 4d,
  an $SO(d)$ highest weight `'[1, 1]'` in $d \ge 5$.
- **Remarks** such as "order parameter", "thermal", "superpartner of $\sigma$" are never part of
  the representation: use `role`, or `multiplet: {name: '$\sigma$', component: Q}` in
  supersymmetric theories, with `type` (the multiplet in its case's house notation) and `cdi` (its
  Cordova–Dumitrescu–Intriligator label; docs/REPRESENTATIONS.md 1.5).
- **Tables** group by global irrep (trivial first, then each group type's natural order, factors
  in their declared order), then by parity (even first), and order each group by spin, then
  $\Delta$. A label shared by every operator is said once above the table; a table where no group
  would hold two operators is flat, with the labels as columns.
- **Families.** A tower of operators known as a function of a label (half-BPS operators,
  Coulomb-branch operators, conserved currents, free-field towers) is **one row**, not one row per
  member: `family: {id: half-BPS, parameters: [{symbol: k, from: 2, to: N}]}`, with `Delta: 'k'`,
  `global: {SU(4)_R: 'Dynkin(0,k,0)'}` and so on as expressions in `k` (and the entry's
  parameters). Ranges: `from`, `to`, `step`, `except`; none for all integers. A member that needs a
  row of its own (the stress-tensor multiplet, its own references) keeps its full data and adds
  `member_of: half-BPS` and `at: {k: 2}`; it is listed under the family, and the build checks that
  it agrees with the family there. Operators known only one by one (e.g. numerically determined
  double-twist operators) stay individual rows. Details: `docs/REPRESENTATIONS.md`, 1.7 and 2.7.
- **Older entries** still give a free-text `rep`; it is accepted and counted by the build
  (`! N operator rep(s) ... still free text`) until they are migrated.

### Writing LaTeX in YAML

- **Wrap LaTeX in single quotes**: `global: '$\mathbb{Z}_2$'`. In single-quoted
  YAML, backslashes are literal. (Inside double quotes you would need `\\`.) To use
  a literal `'` inside single quotes, write `''`.
- For multi-line text use a block scalar (`description: |`), which also keeps
  backslashes literal.
- **Prose fields** (`name`, `summary`, `description`, `note`, `role`, `global`, …)
  are Markdown: write math as `$...$` or `$$...$$`.
- **Math-only fields** (`lagrangian`, `symbol`, operator `name`, `value`,
  `Delta`, `spin`) are typeset as math automatically: **no `$` signs**.

### Numbers and uncertainties

- Write values as quoted strings so trailing digits survive:
  `Delta: '0.518148806(24)'` (the digits in parentheses are the uncertainty in the
  last digits).
- Exact values are LaTeX: `value: '\frac{1}{2}'`.
- Give a `method` (an abbreviation such as `exact`, `CB`, `MC`, `ε-exp`; see
  *Methods* below) and `refs: [key]` pointing to an entry in the theory's `references` list.

### Methods

How a number was obtained is named by an abbreviation from
[`data/methods.yaml`](data/methods.yaml), listed with explanations and links on the site's
[Methods page](https://nathansbenjamin.github.io/QFT_Zoo/#/methods). A short qualifier may follow
after a comma, for the model, order or kind of error that the method's name does not already say:

```yaml
method: CB                                   # numerical conformal bootstrap
method: 'CB, rigorous'
method: 'MC-BC, isotropic'                   # Monte Carlo, improved Blume–Capel model
method: 'ε-exp, 6 − ε, five loops, resummed'
method: 'exact, planar limit'
method: 'CB, rigorous, from Δε′'              # ω = Δε′ − 3, from a rigorous bootstrap interval
```

- The abbreviation is the text before the first comma. The build rejects one that is not in
  `data/methods.yaml`; write the qualifier in words, and put anything longer (assumptions,
  lattice sizes, where in the paper) in the row's `note`.
- **Values computed from another determination** by a relation (an exponent from a scaling
  dimension, $\eta = 2\Delta_\sigma - 1$; a dimension from an RG eigenvalue, $3 - y_t$; a
  normalization change) get the method of their input, with a qualifier `from X` naming the input:
  `method: 'CB, from Δσ'`, `'MC, from ν'`, `'ε-exp, 6 − ε, five loops, resummed, from ω'`. Keep
  `rigorous` only when the input is a rigorous interval and the relation is monotone, so that the
  result is a rigorous interval too. `refs` cite the paper of the input, with a locator where the
  input (or the computed value, if the paper states it) appears; if the paper does not state the
  value itself, say in the `note` that it is computed by the relation. There is no separate
  "derived" method: a bootstrap value converted to an exponent is still a bootstrap determination,
  on the same footing as the Monte Carlo one, and each goes in its own row (see *How quantities are
  shown*). Values fixed by symmetry or an exact argument use `exact` with a short qualifier, e.g.
  `'exact, free field'`; a value whose only uncertainty comes from a numerical input keeps the
  input's method even when the relation is exact (`'CB, from Δσ'` for $\Delta_\psi = \Delta_\sigma + \tfrac12$
  by supersymmetry).
- **Never put another determination in a note** ("Bootstrap: 0.5189(1)", "compare Monte Carlo
  ..."): give it its own row with the same `symbol` and `description`, its method and `refs`.
- If no method fits, add one to `data/methods.yaml`: `abbr` (short, no spaces; an established
  abbreviation if there is one), `name`, a one-to-three-sentence `description`, optionally a
  `parent` (`MC-BC` is a kind of `MC`) and `links` to its Wikipedia article (or, where Wikipedia
  has none, a standard review or the paper that introduced it). Prefer a qualifier on an existing
  method to a new method used by one row.
- Older entries may still describe a method in free text (`semiclassical (monopole
  quantization)`): text with a space before the first comma is accepted for now, shown as it is,
  and counted by the build (`! N method(s) still free text`).

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

### How quantities are shown

A theory page shows its quantities by kind, each kind in its own section:
**Central charges and free energy** (`central`: $c$ in 2d, $C_T$, $C_J$, flavor central
charges, sphere and thermal free energies), **Anomalies** (`anomaly`: the Weyl anomalies
$a$, $c$ in $d \ge 4$ and $a$, $c_i$ in 6d, 't Hooft anomalies, anomaly polynomials),
**Three-point functions** (the entry's `three_point_functions`, see *Three-point functions* below,
and quantities with `category: ope`), **Critical exponents** (`exponent`) and **Other data**.
Every entry gets the same sections, however few its quantities, so the same kind of data looks the same on every page.

- The kind is inferred from `key`, `symbol` and `description` ("anomaly", "exponent",
  "two-point coefficient", `\nu`, ...). Set `category:` only when the inference is wrong.
  `ope` is never inferred: three-point data that is not a coefficient of one three-point
  function (a structure constant as a function of continuous labels, a reflection
  amplitude, a ratio of OPE coefficients) is a quantity with `category: ope`.
- Exponents show their relation to scaling dimensions, taken from the description's
  `$...$` (e.g. `'Critical exponent, $\nu = 1/(3-\Delta_\epsilon)$'`) or from `relation:`.
- **Several determinations** of one quantity (other papers or methods): give each its own
  row with the same `symbol` and the same `description` (or one that only adds the method
  after a comma or colon, or starts with "Same"). The page shows them as one quantity, the
  most precise value first and the others folded below it. Rows that fix a parameter in the
  description (`$N = 25$`, `$k = 1$`) stay separate quantities.

### Three-point functions

Three-point functions have their own list, `three_point_functions`: one item per **unordered triple of operators**
$\langle O_1O_2O_3\rangle$, and in it every value recorded for it, each the coefficient of one **three-point structure**
(a three-point function is a sum of coefficients times structures). The full specification, with the presentation rule,
is [docs/THREE_POINT.md](docs/THREE_POINT.md).

```yaml
three_point_structures:               # structures that are a choice of a paper: defined once, in its notation
  - id: reehorst2021
    name: 'scalar–scalar–spin-$\ell$, $(Z_{123}\cdot\zeta)^\ell$'   # what it is, in a few words
    form: '\langle O_{\Delta_1}(x_1)\,O_{\Delta_2}(x_2)\,O_{\Delta_3,\ell}(x_3,\zeta)\rangle = \lambda_{123}\,\frac{(Z_{123}\cdot\zeta)^\ell - \text{traces}}{\cdots}'   # the source's formula
    ref: 'reehorst2021, p. 6, fn. 3'              # the formula that defines it
    description: 'The normalization of [@poland2019, Eqs. (23)–(24)] that Reehorst et al. use; $h_{ijk} \equiv \Delta_i+\Delta_j-\Delta_k$, ...'
    relation: 'A coefficient in this structure is $2^{\ell/2}$ times the coefficient of the same three-point function in the block-normalized structure of [@simmonsduffin2016, Eq. (A.16)] [@reehorst2021, p. 16].'   # only as a source states it

three_point_functions:
  - operators: ['\sigma', '\sigma', '\epsilon']   # `name`s from the operators table, lightest first
    values:
      - structure: scalar                           # standard: three scalars, unit-normalized
        value: '1.0518537(41)'
        method: CB
        refs: [kos2016]
  - operators: ['\sigma', '\sigma', 'T''_{\mu\nu}']
    values:                                         # one coefficient, quoted in two papers' structures
      - {structure: sd16, value: '0.0105745(42)', method: CB-EFM, refs: [simmonsduffin2016]}
      - {structure: reehorst2021, value: '0.02107(20)', method: 'CB, rigorous', refs: [reehorst2021]}
  - operators: ['\epsilon', 'T_{\mu\nu}', 'T_{\mu\nu}']
    values:                                         # the source writes <T T eps>: its order, explicitly
      - {structure: chang2024-tte, order: ['T_{\mu\nu}', 'T_{\mu\nu}', '\epsilon'], value: '0.95331513(42)', method: 'CB, non-rigorous error', refs: [chang2024]}
  - operators: ['T_{\mu\nu}', 'T_{\mu\nu}', 'T_{\mu\nu}']
    values:                                         # two structures of one three-point function (one basis)
      - {structure: ttt-free-boson-3d, value: '0.933444559(75)', method: 'CB, non-rigorous error', refs: [chang2024]}
      - {structure: ttt-free-fermion-3d, value: '0.013094116(33)', method: 'CB, non-rigorous error', refs: [chang2024]}
```

- **Operators** are named exactly as in the entry's `operators` table (the build checks
  it); `{label: '...'}` for one that is not there (counted by the build). They are an
  unordered triple: write them lightest first, as the page shows them.
- **Operator order.** A coefficient's sign can depend on the order of the operators
  ($\lambda_{12O} = (-1)^\ell\lambda_{21O}$). A value's structure assumes the order of
  `operators`; when its source used another order, give it in the value's `order`. Never
  re-sign a value to another order.
- **Every value names its structure**: a standard one from
  [`data/three_point_structures.yaml`](data/three_point_structures.yaml) (`scalar`: three scalars with
  unit-normalized two-point functions; `vector-vector-singlet`: $\delta_{ij}$ for $O(N)$;
  `ttt-free-boson-3d`, `ttt-free-fermion-3d`: $n_B$, $n_F$), or one defined in the entry's
  `three_point_structures` in the source's notation: `id`, its `form`, a short `name`, the citation of its defining
  formula `ref`, a precise `description` (normalization of the operators and of the blocks or tensor structures, the
  definitions of the form's symbols), and a `relation` to other structures only when a source states one. Never
  convert a value to another structure: record it in its paper's structure, as its own value.
- **What the structure is** (`form`): every structure says what it is, in its own line on the page, never by a bare
  symbol plus a citation, **in the notation of the source its values come from** (David: "For three point structures,
  it makes sense to prefer notation from the source where the number comes from"): the source's three-point function
  where it writes one (an embedding-space combination, a physical-space formula, a flavor structure), else its defining
  formula (a block normalization), or the three-point tensor its definition implies, marked as inferred and checked.
  Write a coefficient in the formula with the site's letter $\lambda$. Only structures that no source pins to a
  notation (three scalars) are written in the common embedding-space notation below, as a single-monomial `embedding`.
- **A square or a modulus**: if the number is $\lambda^2$ or $|\lambda|$, say so with `value_of: square` or
  `value_of: modulus`.
- **Embedding-space form** (`embedding`, optional; David: "When a structure is a simple
  embedding space structure, you should use the notation of Spinning Conformal
  Correlators"): the three-point function as a LaTeX formula (no `$`), in the notation
  below, for a single monomial only, with the coefficient times whatever factor its source's normalization needs
  ($2^{\ell/2}$ for the blocks of Simmons-Duffin 2016). Give it beside a `form` only when it adds a cross-check; leave
  it out when the source's form says the same. Say in the `description` how the
  factor follows from the sources, citing `[@costa2011, Eq. (…)]` and the source's formulas;
  if it depends on a convention you cannot pin down from the sources, leave `embedding` out
  and say so. Add `costa2011` to the entry's references.
- **Notation** (Costa, Penedones, Poland, Rychkov, *Spinning Conformal Correlators*,
  arXiv:1107.3554, JHEP 11 (2011) 071; reference key `costa2011`; equations of arXiv v3):
  points $P_i$ on the null cone of $\mathbb R^{d+1,1}$ and polarizations $Z_i$
  ($Z_i^2 = Z_i\cdot P_i = 0$); $P_{ij} \equiv -2P_i\cdot P_j$ (Eq. (2.9), $= x_{ij}^2$ on the
  Poincaré section; later papers write $X_{ij}$);
  $V_{i,jk} \equiv \frac{(Z_i\cdot P_j)(P_i\cdot P_k)-(Z_i\cdot P_k)(P_i\cdot P_j)}{P_j\cdot P_k}$ (Eq. (4.14));
  $H_{ij} \equiv -2\left[(Z_i\cdot Z_j)(P_i\cdot P_j)-(Z_i\cdot P_j)(Z_j\cdot P_i)\right]$ (Eq. (4.15));
  $V_1 \equiv V_{1,23}$, $V_2 \equiv V_{2,31}$, $V_3 \equiv V_{3,12}$ (Eq. (4.16)). Unit-normalized
  spin-$\ell$ operators have $\langle O(P_1,Z_1)O(P_2,Z_2)\rangle = H_{12}^\ell/P_{12}^{\Delta+\ell}$
  (Eq. (4.9)); three scalars give $\lambda/(P_{12}^{\frac{\Delta_1+\Delta_2-\Delta_3}{2}}P_{23}^{\frac{\Delta_2+\Delta_3-\Delta_1}{2}}P_{31}^{\frac{\Delta_3+\Delta_1-\Delta_2}{2}})$
  (Eq. (2.8)); general spins $Q/(P_{12}^{\frac{\tau_1+\tau_2-\tau_3}{2}}P_{23}^{\frac{\tau_2+\tau_3-\tau_1}{2}}P_{31}^{\frac{\tau_3+\tau_1-\tau_2}{2}})$,
  $\tau_i = \Delta_i+\ell_i$, with $Q$ built from $V_i$ and $H_{ij}$ (Eqs. (4.12), (4.17)); scalar–scalar–spin-$\ell$
  is $Q = \lambda_{12O}V_{3,12}^\ell$ (Sec. 4.2.1). More, with the projection to physical space
  and the relation to block normalizations, in [docs/THREE_POINT.md](docs/THREE_POINT.md), 1.4.
- Several determinations of a coefficient are several `values` of one three-point function,
  of the same structure or of different ones. Conventions go in the structure, once; a
  value's `note` is about the value (locator, rigor, assumptions, agreement).
- The page shows one item per three-point function, labelled $\langle O_1O_2O_3\rangle$ with
  its operators lightest first, the items lightest first; each element of a basis of several
  structures ($n_B$, $n_F$) on its own line, all other values on one line, best first within
  each structure, the rest folded. Each row names its structure (and the operator order it
  assumes, if not the label's); the structures used are defined once below the table.

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

### RG flows in detail

A `flows_to` relation with only a `note` is fine. To say more, give the flow an `id`
(a slug, unique among the entry's flows) and a `flow` block. Each arrow in the RG-flow
diagrams then opens a panel with these details, and two flows between the same two
theories (say, the two signs of a coupling) stay two separate arrows.

```yaml
relations:
  - type: flows_to
    id: thermal-positive              # names this flow; required with `flow`
    target: some-ir-theory
    note: 'The free-text description, as before.'
    flow:
      identification:                 # required: who showed that UV flows to this IR, and how
        status: established           # established | conjectured | disputed
        method: 'lattice Monte Carlo'
        refs: [author2020]
        # competing_refs: [other2021]  # required for disputed
      deformations:                   # relevant operators added to the action
        - operator: '\epsilon'        # as named in this entry
          coupling: 't'
          Delta: '1.41(1)'            # optional
          sign: positive              # positive | negative | zero | either
          sign_convention: '$S = S_{\rm CFT} + t\int\epsilon$, ...'   # required with sign
          refs: [author2020]
      # vevs:                         # instead of, or as well as, deformations
      #   - {operator: '\phi', direction: 'a generic point of the Coulomb branch', branch: 'Coulomb branch', refs: [...]}
      tuned:                          # couplings tuned to reach this IR
        - {operator: '\phi^2', coupling: 'm^2', condition: 'tuned to criticality', standard: true}
      symmetry_changes:               # in order; kind: explicit | spontaneous | emergent
        - {from: '$\mathbb{Z}_2$', to: 'nothing', kind: spontaneous, vacua: 2, refs: [author2020]}
      spectrum:                       # if the IR is gapped
        summary: 'One sentence for the panel.'
        vacua: 2
        particles:
          - {label: 'm_1', mass: '1', stable: true, method: exact, refs: [author2020]}
        refs: [author2020]
      integrability: {status: integrable, note: 'Exact S-matrix.', refs: [author2020]}   # or not_integrable, open
      page: some-flow-page            # an entry tagged 'RG flow' that covers this flow
      note: 'Assumptions, ranges of validity, the symmetry the deformed action keeps, ...'
```

- **Every statement needs its own source.** Each deformation, vev, tuning, symmetry change,
  spectrum and integrability record has `refs` (keys of *this*, the UV, entry's references),
  unless it is a textbook statement marked `standard: true`. Spectrum rows always need
  `method` and `refs`. The flow as a whole is cited in `identification`, which says who
  established the flow and by what argument (anomaly matching, numerics, lattice,
  supersymmetry, a duality, ...); if it is disputed, give the competing papers.
- **Absent means "not recorded".** Leaving out `symmetry_changes`, `tuned`, `sign`,
  `spectrum` or `integrability` never claims there is none; the panel shows *Not recorded*.
  Use `either` only when the source says both signs give this flow, and say why in `note`.
- **Operator names are labels**, written as in the UV entry; they are not links to rows of
  `operators`, so give `Delta` only with a source for it.
- **Composite IR theories.** When the IR is built from entries, e.g. a direct sum of two copies
  of a gapped theory, give `target_expr` instead of `target` (plus `id` and `flow`):
  ```yaml
  target_expr:
    operation: direct_sum             # direct_sum | tensor_product
    terms:
      - expr: {entry: trivial-tqft-3d}
        multiplicity: 2
    decoration: 'The $\mathbb{Z}_2$ symmetry exchanges the two summands.'
  ```
  Terms can nest, and `entry` leaves take `at`/`variant` for family members. Nothing is
  simplified or inferred: say how the symmetry acts in `decoration`. The pieces' pages show
  the flow under *Part of a composite IR*, not as a flow ending at them. Pages explaining the
  operations live in `data/operations/<id>.yaml` (`direct-sum`, `tensor-product`).
- **Flow pages.** A famous flow (e.g. the Ising field theory) can have an entry of its own,
  tagged `RG flow`, holding its data (spectrum, S-matrix, phase diagram). Point each relation
  it covers at it with `flow.page`; say in your pull request why the flow deserves a page.

### References

Every entry needs at least one reference. If no paper contains the specific theory
yet, cite the papers that supply its ingredients and say so with
`note: construction ingredients`.

A reference entry has a `key` (first author's surname, year and, if needed, a word:
`kos2016`, `caselle2016thermal`), `title`, `authors`, `year`, `arxiv` and/or `doi`,
`journal` once published, and a `note` saying what the entry takes from it (and which
arXiv version, if the numbering of sections or equations changed between versions).

### Citations

On the site every citation is a number in brackets, linked to the reference list at
the bottom of the page: `[3]`, or with a locator `[3, Table 2]`. Write citations so that
the site can do this; never cite a paper any other way.

**In data rows**, cite through `refs`. Each item is a reference key, optionally followed
by a comma and a locator:

```yaml
refs: [kos2016]                         # → [2]
refs: ['kos2016, Table 2', simmons2017]  # → [2, Table 2; 5]
```

**In prose** (every Markdown field: `description`, `summary`, `note`s, parameter and
symmetry text, flow notes), cite with `[@key]`:

```markdown
Moore and Saxena [@moore2025, Sec. 9] define it by the state space ...
... no genuine topological defects [@bhardwaj2024, Sec. 4.1.1, Eqs. (4.8)–(4.10)].
Both bounds agree [@kos2016; @simmons2017, Table 1].
```

- Authors' names may appear in the sentence, but never instead of the citation: write
  "Argyres and Douglas [@argyres1995] showed", not "Argyres and Douglas showed" or
  "(Argyres–Douglas 1995)".
- Never link a paper directly in prose (`[Caselle et al.](https://arxiv.org/abs/...)`),
  and never cite a paper that isn't in the entry's `references` list: add it there first.
- A key always means the current entry's reference. A note shown on another page (a flow
  shown on its IR theory's page) still finds it; the site handles this.
- A standard three-point structure (`data/three_point_structures.yaml`) cites by key too, and its keys mean
  the references of the entry that shows it: an entry that uses it must list them (e.g.
  `costa2011`, for the embedding-space notation). The build checks it.

**Locators** point to the passage that states the claim, in the paper's own numbering
(of the arXiv version unless the reference's `note` names another). Use these forms,
most general first, separated by commas, with an en dash for ranges:

| What | Form |
|---|---|
| section | `Sec. 4.1.1`, `Secs. 2–3` |
| equation | `Eq. (4.8)`, `Eqs. (4.8)–(4.10)`, `Eqs. (1), (4)` |
| table, figure | `Table 2`, `Fig. 3`, `Figs. 3–4` |
| appendix | `App. B` |
| page (printed) | `p. 28`, `pp. 27–29` |
| theorem etc. | `Thm. 2`, `Lemma 3`, `Prop. 1` |
| footnote | `fn. 7` |

For example `[@bhardwaj2024, Sec. 4.1.1, Eqs. (4.8)–(4.10)]`. A locator may contain
`$...$` math but no semicolon (semicolons separate sources). Prefer a locator whenever
the paper is long or the claim is not its main result; a verifier must be able to find
the statement from it.

`python scripts/build.py --check` rejects unknown keys and malformed citations, and
counts prose that still links papers directly.

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
