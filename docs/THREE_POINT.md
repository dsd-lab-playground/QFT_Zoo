# Three-point functions: data and presentation

The zoo presents **three-point functions**, not OPE coefficients one by one (David, 2026-11-07: "we are presenting
three point functions, not OPE coefficients. A three point function is a linear combination of coefficients times
structures"). The three-point function $\langle O_1 O_2 O_3\rangle$ of three primary operators is fixed by conformal
symmetry up to a sum $\sum_a \lambda_a\,\langle O_1O_2O_3\rangle_a$ of independent **structures** with constant
**coefficients**: one structure for three scalars, several for spinning operators ($n_B$ and $n_F$ of
$\langle TTT\rangle$ in 3d). A recorded number is the coefficient of one structure in one three-point function. The
same coefficient can be quoted in different normalizations (Simmons-Duffin 2016's block-normalized structure and
Reehorst et al.'s structure of Poland, Rychkov and Vichi differ by $2^{\ell/2}$), so the zoo records, for every value,
the three operators and the structure. That is the *data*. How a theory page groups and orders the values is the
*presentation*, a fixed rule applied in the same way to every entry. The summary for contributors is in
[CONTRIBUTING.md](../CONTRIBUTING.md), *Three-point functions*.

The three operators are an **unordered triple** (David: "we want to organize according to unordered triples of
operators"): one item per triple, whatever order the sources wrote. Since a coefficient's sign can depend on the order
(e.g. $\lambda_{\sigma\epsilon O} = (-1)^\ell\lambda_{\epsilon\sigma O}$ at spin $\ell$), each value says which order
its structure assumes.

---

## 1. Data

### 1.1 Three-point functions: `three_point_functions`

Each item of an entry's `three_point_functions` list is one three-point function, an unordered triple of operators,
and holds every value recorded for it:

```yaml
three_point_functions:
  - operators: ['\sigma', '\sigma', 'T''_{\mu\nu}']     # names from the operators table; written lightest first
    values:
      - structure: sd16                                # the structure whose coefficient this is (1.2)
        value: '0.0105745(42)'
        method: CB-EFM
        refs: [simmonsduffin2016]
        symbol: "f_{\\sigma\\sigma T'}"                # optional: the source's symbol (information only)
        note: '[@simmonsduffin2016, Table 2, p. 72], $T''_{\mu\nu}$ row. Not rigorous.'
      - structure: reehorst2021                        # the same coefficient, in another paper's structure
        value: '0.02107(20)'
        method: CB, rigorous
        refs: [reehorst2021]
        note: '[@reehorst2021, Table 1, p. 4]. Rigorous, assuming ...'
  - operators: ['\epsilon', 'T_{\mu\nu}', 'T_{\mu\nu}']
    values:
      - structure: chang2024-tte                       # written by its source as <T(X1,Z1) T(X2,Z2) eps(X3)>
        order: ['T_{\mu\nu}', 'T_{\mu\nu}', '\epsilon']  # so its order differs from `operators`: said explicitly
        value: '0.95331513(42)'
        method: CB, non-rigorous error
        refs: [chang2024]
  - operators: ['T_{\mu\nu}', 'T_{\mu\nu}', 'T_{\mu\nu}']
    values:                                            # two structures of one three-point function
      - structure: ttt-free-boson-3d                   # standard structures need no definition in the entry
        value: '0.933444559(75)'
        method: CB, non-rigorous error
        refs: [chang2024]
      - structure: ttt-free-fermion-3d
        value: '0.013094116(33)'
        method: CB, non-rigorous error
        refs: [chang2024]
```

- **`operators`**: the three operators, an unordered triple. Each is the `name` of an operator in the entry's
  `operators` table, written exactly as there, so the build can check that it exists and the page can read its
  dimension. Write them lightest first (the order the page shows); the structures of the item's values assume this
  order unless a value says otherwise. An operator that is not in the table is written `{label: '...'}` (LaTeX); the
  build counts these (`! N operator(s) of three-point functions named by a label`), and adding the operator to the
  table is better.
- **`values`**: every determination of a coefficient of this three-point function: by different methods or papers, of
  the same structure or of different ones. Each value has `structure` (required) and `value`, and as usual `method`,
  `refs` and `note`; optionally:
  - `order`: the order of the three operators that the value's structure assumes (operator 1, 2, 3 of its `form`),
    when it differs from `operators`; the same three operators. Values are never re-signed to another order.
  - `value_of`: `square` or `modulus` when the number is $\lambda^2$ (a bound on the square) or $|\lambda|$ (phase
    unknown); omitted, it is the coefficient itself.
  - `symbol`: the coefficient as the source writes it ($f_{\sigma\sigma T}$, $C_{\sigma\sigma\epsilon}$), information
    only (the page writes every coefficient with one letter, 1.5).
  - `description`: about this value, rarely needed.
- One item per triple: two items with the same three operators (in any order) are an error.
- **Never convert values between structures.** A value quoted in a paper's own structure is recorded in that
  structure; if two papers use different structures, they are two values of the same three-point function with
  different `structure`s.
- Notes are about the value: where in the paper it is, its rigor, assumptions, agreement with other values. A
  statement of convention (how operators or blocks are normalized) belongs in the structure, once.

Why a separate list rather than `quantities` with extra fields: a coefficient is identified by its three-point function
and its structure, not by a symbol; the schema can then require both; all values of one three-point function sit
together in the file as they do on the page; and the site needs no guessing (the old site inferred OPE coefficients and
their operators by parsing symbols like `\lambda_{\sigma\sigma\epsilon}`). `quantities` keep the theory's other numbers
($c$, $C_T$, exponents). Three-point data that is not a coefficient of one three-point function (a structure constant
as a function of continuous labels, such as the DOZZ formula; a reflection amplitude; a ratio of coefficients; one value
for several theories) stays in `quantities` with `category: ope` and is shown in the same section, after the
three-point functions.

### 1.2 Structures

A value's `structure` is an id: one of the few **standard structures** of
[`data/three_point_structures.yaml`](../data/three_point_structures.yaml), or one the entry defines in its
**`three_point_structures`** list. People invent many bases, and the zoo does not try to define a universal vocabulary:
a structure that is a choice of a paper is defined in the entry, in that paper's notation (1.4).

**Standard structures** (shared by all entries; add one only when the literature really agrees on it):

| id | name | form |
|---|---|---|
| `scalar` | three scalars, unit-normalized | $\lambda_{123}/(P_{12}^{\frac{\Delta_1+\Delta_2-\Delta_3}{2}}P_{23}^{\frac{\Delta_2+\Delta_3-\Delta_1}{2}}P_{31}^{\frac{\Delta_3+\Delta_1-\Delta_2}{2}})$ in embedding space, $\langle O_iO_i\rangle = \lvert x\rvert^{-2\Delta_i}$ (default) |
| `vector-vector-singlet` | vector × vector → singlet, $\delta_{ij}$ | $\langle\phi_i\phi_j s\rangle = \lambda\,\delta_{ij}\times$ the three-scalar structure, $O(N)$ (default) |
| `ttt-free-boson-3d`, `ttt-free-fermion-3d` | free-scalar / free-Majorana $\langle TTT\rangle$ | $n_B\langle TTT\rangle_B$, $n_F\langle TTT\rangle_F$: $\langle TTT\rangle = n_B\langle TTT\rangle_B + n_F\langle TTT\rangle_F$ in 3d (one basis, two coefficients) |

A standard structure may say which spins its operators have (`spins`, in the order the structure assumes) and in which
dimension it is defined (`d`); the build checks both against the entry. `default: true` marks a structure that a reader
assumes when none is named.

**An entry's own structures**:

```yaml
three_point_structures:
  - id: chang2024-tte                       # what values write in `structure:`
    name: 'parity-even $\langle TT\epsilon\rangle$'
    form: '\langle \hat T(X_1,Z_1)\,\hat T(X_2,Z_2)\,\epsilon(X_3)\rangle = \lambda_{TT\epsilon}\,\frac{1}{X_{12}^{\cdots}\cdots}\Big(V_1^2V_2^2 + \cdots\Big)'
    symbol: '\lambda'                       # the source's symbol (optional)
    ref: 'chang2024, Eq. (2.2)'             # the formula that defines it: a reference key and a locator
    description: 'The parity-even structure of $\langle TT\epsilon\rangle$ as written and normalized by [@chang2024, Eq. (2.2)], ...'
  - id: reehorst2021
    name: 'scalar–scalar–spin-$\ell$, $(Z_{123}\cdot\zeta)^\ell$'
    form: '\langle O_{\Delta_1}(x_1)\,O_{\Delta_2}(x_2)\,O_{\Delta_3,\ell}(x_3,\zeta)\rangle = \lambda_{123}\,\frac{(Z_{123}\cdot\zeta)^\ell - \text{traces}}{\cdots}'
    ref: 'reehorst2021, p. 6, fn. 3'
    description: 'The normalization of [@poland2019, Eqs. (23)–(24)], which Reehorst et al. use ...'
    relation: 'A coefficient in this structure is $2^{\ell/2}$ times the coefficient of the same three-point function in the block-normalized structure of [@simmonsduffin2016, Eq. (A.16)] ...'
```

- `id` (required): unique in the entry, different from the standard ids.
- `ref` or `name` (at least one): `ref` cites the formula that defines the structure (`'key, Eq. (2.2)'`; the key must
  be in the entry's references); `name` is a short name that says what the structure is ("vector × vector → tensor",
  "parity-even ⟨TTε⟩"). The Structure column of a row shows the name, else the citation.
- `form`: what the structure is, as a LaTeX formula shown in its line in the structures list (never folded), so that a
  reader can identify it without opening the reference (David, 2026-11-07: "Label every OPE structure by what it is,
  never by a bare λ plus a citation"), **written in the notation of the source its values come from** (1.4): its
  symbols, its formula, its operators in its order. Where the source writes the three-point function, the form is that
  formula (Chang et al.'s ⟨TTε⟩ in embedding space; the review of Poland, Rychkov and Vichi for Reehorst et al.; the
  $O(2)$ flavor structures $T_{\mathbf q_1\mathbf q_2\mathbf q_3}(y_i)$ of Chester et al. 2019). Where the source defines
  the coefficient by something else, the form is that definition (Simmons-Duffin 2016's block normalization, its
  Eq. (A.16)), or the three-point tensor that the source's definition implies, marked as inferred, with how it was
  checked (the $O(3)$ tensors of Chester et al. 2020, from their four-point structures). If the formula contains the
  coefficient, it is written with the site's letter (1.5). A single-monomial `embedding` serves as the form when no
  source pins a notation; otherwise `form` is required (the build checks it). The citation follows the form as the
  source of the convention.
- `symbol`: the source's symbol ($\lambda$, $f$, $n_B$, ...), information only.
- `description`: what the structure is, precisely: which three-point function, how the operators are normalized, how the
  tensor structure or conformal block is normalized (e.g. "blocks start as $z^{(\Delta-\ell)/2}\bar z^{(\Delta+\ell)/2}$"),
  the definitions of the form's symbols, with citations.
- `relation` (optional): how it relates to another structure, **only as a source states it** (or as it follows from
  formulas the sources state, each cited), with the citation, comparing structures (not letters). It is information for
  readers; values are never converted with it.
- `embedding` (optional): the three-point function in embedding space, in the notation of *Spinning Conformal
  Correlators* (1.4), as a LaTeX formula without `$...$`. Give it only when the structure is a single monomial (one
  product of $V_{i,jk}$ and $H_{ij}$ over powers of $P_{ij}$; David, 2026-11-07: "By simple, I meant like 1 monomial")
  and it adds something to the source's form: the line shows it when the structure has no `form`; otherwise it folds
  with the description, as a cross-check (Simmons-Duffin 2016's block normalization is $2^{\ell/2}V_{3,12}^\ell$). When
  the source's own form already says the same, leave it out. The coefficient appears in it with the factor its
  source's normalization needs, and the description says how that factor follows from the sources, with citations.
  Where a factor depends on a convention that the sources do not pin down, leave `embedding` out and say so, rather
  than guess. Citations go in the description, not in the formula.
- `basis` (rare): for a structure that is one element of a basis of several independent structures of the same
  three-point function, an id shared by its elements (as `ttt-free-3d` for $n_B$, $n_F$). Values of different elements
  are different coefficients (2.2). A structure that is the only one of its three-point function in its paper's basis
  (scalar–scalar–spin-$\ell$, $\langle TT\epsilon\rangle$ parity-even) has no `basis`.

Adding a new paper's values therefore takes one structure definition (its id, its form in the paper's notation, the
citation of its defining formula, a sentence of description) and its values; nothing in other entries or in the site
changes.

### 1.3 Checks (`scripts/build.py`, `scripts/ope.py`)

- every operator name is in the entry's operators table (or is a flagged `{label}`);
- every `structure` is a standard id or one of the entry's `three_point_structures`; entry ids are unique, do not shadow
  a standard id, and are each used by some value; a structure's `ref` and every value's `refs` name the entry's
  references;
- a value's `order` lists the same three operators as `operators`, and differs from it;
- the operators' spins (from the table), in the order the value's structure assumes, match the structure's `spins`, and
  the entry's `d` its `d`;
- one item per triple (in any order); no two values claim the same (triple, structure, method, refs, value);
- `value_of` is `square` or `modulus` (schema);
- a `form` or `embedding` is a string with no `$` and no citation in it; a standard structure that cites a key
  (`[@costa2011, ...]`) needs that key in the references of every entry that uses it (citations are read against the
  entry's references); the build reports how many structures give their embedding-space form;
- methods as for every row (CONTRIBUTING.md, *Methods*). `tests/test_ope.py` tests these checks.

### 1.4 Embedding-space notation (Costa, Penedones, Poland, Rychkov)

**Notation rule** (David, 2026-11-07: "For three point structures, it makes sense to prefer notation from the source
where the number comes from"): a structure's `form` is written in the notation of the source its values come from —
its basis, its symbols, its formula, its order of the operators — so a reader can match the number to the paper. The
embedding-space notation below is used only to write out simple structures that no source pins to a notation of its
own (three scalars, vector × vector → singlet), and as a common language in the `embedding` field, where it can
cross-check a source's normalization.

Embedding-space forms follow *Spinning Conformal Correlators* by Costa, Penedones, Poland and Rychkov (arXiv:1107.3554,
JHEP 11 (2011) 071; reference key `costa2011`; equation numbers of arXiv v3). A point $x\in\mathbb R^d$ is a null ray
$P$ of $\mathbb R^{d+1,1}$, and a symmetric traceless spin-$\ell$ operator is a polynomial of degree $\ell$ in a
polarization $Z$ with $Z^2 = Z\cdot P = 0$, homogeneous of degree $-\Delta$ in $P$. On the Poincaré section
$P = (1, x^2, x)$, $Z = (0, 2x\cdot z, z)$ [Eq. (4.36)].

- $P_{ij} \equiv -2P_i\cdot P_j$ [Eq. (2.9)], which becomes $x_{ij}^2$ [Eq. (2.10)]. (Later papers, e.g.
  Chang et al. 2024, Eq. (2.2), write the points $X_i$ and $X_{ij}$ for $P_{ij}$.)
- $C_i^{AB} \equiv Z_i^AP_i^B - Z_i^BP_i^A$ [Eq. (3.28)];
  $V_{i,jk} \equiv \dfrac{P_j\cdot C_i\cdot P_k}{P_j\cdot P_k} = \dfrac{(Z_i\cdot P_j)(P_i\cdot P_k)-(Z_i\cdot P_k)(P_i\cdot P_j)}{P_j\cdot P_k}$
  [Eq. (4.14)], and
  $H_{ij} \equiv -C_i\cdot C_j = -2\left[(Z_i\cdot Z_j)(P_i\cdot P_j)-(Z_i\cdot P_j)(Z_j\cdot P_i)\right]$ [Eq. (4.15)];
  $V_{i,jk} = -V_{i,kj}$, $H_{ij} = H_{ji}$, and $V_1\equiv V_{1,23}$, $V_2\equiv V_{2,31}$, $V_3\equiv V_{3,12}$ [Eq. (4.16)].
- Two-point function of a spin-$\ell$ operator: $H_{12}^\ell/P_{12}^{\Delta+\ell}$ times a constant [Eq. (4.9)]; the
  zoo's unit normalization is constant $1$, which on the Poincaré section is $(z_1\cdot I(x_{12})\cdot z_2)^\ell/x_{12}^{2\Delta}$.
- Three scalars: $\lambda_{123}/(P_{12}^{\frac{\Delta_1+\Delta_2-\Delta_3}{2}}P_{23}^{\frac{\Delta_2+\Delta_3-\Delta_1}{2}}P_{31}^{\frac{\Delta_3+\Delta_1-\Delta_2}{2}})$ [Eq. (2.8)].
- General spins: $Q(\{P_i;Z_i\})/(P_{12}^{\frac{\tau_1+\tau_2-\tau_3}{2}}P_{23}^{\frac{\tau_2+\tau_3-\tau_1}{2}}P_{31}^{\frac{\tau_3+\tau_1-\tau_2}{2}})$
  with $\tau_i = \Delta_i+\ell_i$ [Eq. (4.12)], where $Q$ is a combination of the monomials
  $\prod_i V_i^{m_i}\prod_{i<j}H_{ij}^{n_{ij}}$, $m_i + \sum_{j\ne i} n_{ij} = \ell_i$ [Eqs. (4.17)–(4.18)].
- Scalar–scalar–spin-$\ell$ (Sec. 4.2.1, Eqs. (4.10)–(4.11)): the single structure $V_{3,12}^\ell$, i.e.
  $\langle\phi_1(P_1)\phi_2(P_2)O(P_3,Z_3)\rangle = \lambda_{12O}\,V_{3,12}^\ell/(P_{12}^{\frac{\Delta_1+\Delta_2-\Delta-\ell}{2}}P_{23}^{\frac{\Delta_2+\Delta+\ell-\Delta_1}{2}}P_{31}^{\frac{\Delta+\ell+\Delta_1-\Delta_2}{2}})$.
  On the Poincaré section $P_{12}V_3 = z_3\cdot\tilde x_{12}$, $\tilde x_{12} = x_{13}x_{23}^2 - x_{23}x_{13}^2$ [Eqs. (4.30), (4.37)],
  so this is $\lambda_{12O}(Z\cdot z_3)^\ell/(x_{12}^{\Delta_1+\Delta_2-\Delta+\ell}x_{13}^{\Delta_1+\Delta-\Delta_2-\ell}x_{23}^{\Delta_2+\Delta-\Delta_1-\ell})$,
  $Z^\mu = x_{13}^\mu/x_{13}^2 - x_{23}^\mu/x_{23}^2$: the structure of Poland, Rychkov and Vichi's review
  (arXiv:1805.04405, Eqs. (22)–(24)), whose blocks start as $\lambda_{12O}\lambda_{34O}(-\frac12)^\ell z^{(\Delta-\ell)/2}\bar z^{(\Delta+\ell)/2}$
  (its Eqs. (52), (54)). Its coefficient is antisymmetric for odd $\ell$: $\lambda_{21O} = (-1)^\ell\lambda_{12O}$.
- Normalizations by blocks: a coefficient defined by a block normalization (rather than by a three-point structure) is
  related to $\lambda_{12O}$ by comparing the leading terms of the blocks. For the blocks of Simmons-Duffin 2016, which
  start as $f_{12O}f_{43O}z^{(\Delta-\ell)/2}\bar z^{(\Delta+\ell)/2}$ (its Eq. (A.16)), this gives
  $f_{12O}f_{43O} = 2^{-\ell}\lambda_{12O}\lambda_{43O}$, i.e. $\lambda = 2^{\ell/2}f$ (the review's Table I lists the same
  factor $2^\ell$ between the two normalizations; Reehorst's $\lambda$, in the review's normalization, satisfies
  $\lambda^2 = 2^\ell f^2$). The sign of a single coefficient is fixed only together with the sign of $O$.

### 1.5 Coefficient letter

A letter is a convention, not information (PRINCIPLES §2): the page writes every coefficient with one letter, $\lambda$
(chosen by a survey of the literature, below), except the elements of a basis with their own names ($n_B$, $n_F$).
The three-point function and the structure identify the number, so rows carry no per-row symbol; a structure's `form`
writes its coefficient with this letter when the formula includes it. The source's own letter ($f$, $C$) may be kept in
a value's `symbol`, as information.

**Evidence for λ** (survey of 2026-11-07, letter read from each paper's definition, weighted by INSPIRE citations):
λ is used by about 20 of the influential $d \geq 3$ papers sampled (~6,200 citations), including
Rattazzi–Rychkov–Tonni–Vichi 2008, the Poland–Rychkov–Vichi review (2019), Rychkov's EPFL lectures, Chester's lectures,
the Kos–Poland–Simmons-Duffin(–Vichi) series, SDPB, and the O(N), fermion, GNY and stress-tensor bootstrap papers through
Chang et al. 2024; $f$ by 7 (~3,500: the 3d Ising I–II papers, the OPE-convergence paper, Simmons-Duffin's TASI
lectures, the light-ray and lightcone papers, Caron-Huot's inversion formula); $C$ and $c$ mostly in 2d and analytic
work.

---

## 2. Presentation policy

The page shows the entry's three-point data in the **Three-point functions** section (in the single *Data* table of an
entry with few quantities, after the other quantities), with a one-line introduction: a three-point function is a sum
of coefficients times structures, each row is the coefficient of one structure, the structures are defined below the
table. The columns are *Three-point function* | *Structure* | *Notes* | *Coefficient* | *Source*. The rule:

### 2.1 Items and their order

One item per three-point function, labelled $\langle O_1\,O_2\,O_3\rangle$ with its operators **lightest first** (by
dimension, from the operators table, the smallest when an operator has several determinations; ties in data order;
an operator named by label counts as heaviest), whatever order the sources used. Items are ordered by the dimensions of
their operators: each triple's three dimensions are sorted, lightest first, and compared in turn, so
$\langle\sigma\sigma\epsilon\rangle$, $\langle\sigma\sigma T\rangle$, $\langle\sigma\sigma\epsilon'\rangle$, …,
$\langle\epsilon\epsilon\epsilon\rangle$, …; ties keep the data order. Quantities with `category: ope` follow, in data
order.

### 2.2 Lines inside an item

An item has one line per independent coefficient: each element of a multi-element basis (a structure with `basis`) is
its own line ($n_B$ and $n_F$ of $\langle TTT\rangle$); all other values of the three-point function are one line, one
coefficient, even when its values are quoted in different structures (Simmons-Duffin's and Reehorst's normalizations of
$\langle\sigma\sigma T'\rangle$). A three-point function with a single structure therefore looks like a single row; the
label is shown on the item's first row.

Inside a line, values are grouped by structure (standard structures in the order of
`data/three_point_structures.yaml`, then the entry's in the order of its `three_point_structures`), and within a
structure ordered best first as for every quantity (exact, then rigorous intervals by width, then by relative error).
The first value shows; the others fold under "+n more". The disagreement badge compares a value only with the best
value **of the same structure, in the same operator order**: values in different structures are different numbers.

### 2.3 The Structure column

**Labels** (David, 2026-11-08): a structure is labelled by its numerator when that is simple ($1$, $2^{\ell/2}V_3^\ell$,
$V_3^\ell$, $\delta_{ij}$, an $O(N)$ tensor); when the numerator is too complicated, by a short name
("parity-even $\langle TT\epsilon\rangle$", $\langle TTT\rangle_B$). The coefficient column sits right before the
structure it multiplies. In the list of structures below the table, a structure labelled by its numerator shows only the label and its citation, with the full formula under "details"; a named structure shows its formula. **Details are uniform and short** (David, 2026-11-08): the formula in the source's notation (`form`, only when it says more than the label), one sentence on normalization (`description`), and at most one `relation` that a source states. How a normalization or relation follows from the sources goes in `derivation`, which is kept for verifiers and not shown. **In 2d** the three-point function of three primaries has a unique structure, so 2d entries
have no Structure column and no list of structures.

Each row names the structure of its coefficient: the structure's name, else its citation (plus the citation after a
name); clicking it shows the definition. When the value's structure assumes another operator order than the label's,
the cell says so ("in the order $\langle T\,T\,\epsilon\rangle$"). A value that is the square or the modulus of its
coefficient (`value_of`) shows it in the Coefficient cell ($\lambda^2 = \dots$, $|\lambda| = \dots$). The switch
`OPE_LABEL_DEFAULTS` in `site/app.js` (on) labels the default standard structures too.

### 2.4 Definitions, once

Below the table, a short **Structures** list defines every structure used on the page, once, one line each: its name,
its form (`form`, else its single-monomial `embedding`) and its citation; the description, an `embedding` given beside
a `form`, and any stated relation to other structures fold under "details". Row notes never repeat a convention.

---

## 3. Migration (November 2026)

All OPE rows of `quantities` moved to `ope_coefficients` without changing any value, method or refs (checked by script:
every pre-existing value string, with its method and refs, is present exactly once in the same entry, and the number of
values rendered on each of the 169 pages is unchanged). Convention prose moved from row descriptions and notes into
structure definitions; notes about values stayed. Entries: `ising-3d` (15 triplets), `o3-model-3d` (5), `o2-model-3d` (4),
`gny-n1-3d`, `ising-2d`, `ising-star-3d`, `lee-yang-2d`, `lee-yang-3d`, `minimal-ad-4d` (1 each). Left in `quantities`
with `category: ope`: the ratio $\lambda_{\epsilon\epsilon\epsilon}/\lambda_{\sigma\sigma\epsilon}$ (`gny-n1-3d`), the
$H_1$/$H_2$ value of $\lambda^2_{u^2}$ (`argyres-douglas-4d`: one value for two theories), and the structure constants
and reflection amplitudes of `liouville-cft`, `super-liouville`, `h3-wzw`, `toda-cft` (functions of continuous labels).

Open point: the normalization of `lee-yang-3d`'s $\lvert C_{\phi\phi\phi}\rvert$ is assumed to be the standard unit
normalization.

**Embedding-space forms (November 2026).** David: "When a structure is a simple embedding space structure, you should
use the notation of Spinning Conformal Correlators." Structures gained `embedding` (1.4): `scalar`,
`vector-vector-singlet` (Eq. (2.8)); `sd16` ($2^{\ell/2}V_{3,12}^\ell$). The reference `costa2011` was added to every
entry that shows one (`poland2019` to `ising-3d`, for the block normalization).

**Source notation (November 2026).** David: "For three point structures, it makes sense to prefer notation from the
source where the number comes from." Every entry structure's `form` was rewritten in its source's notation: `sd16`
as the block normalization of Simmons-Duffin 2016, Eq. (A.16) (its embedding-space form folded as a cross-check);
`reehorst2021` as the three-point function of Poland, Rychkov and Vichi, Eqs. (23)–(24) (its `embedding` dropped as
redundant); `chang2024-tte` exactly as Chang et al. 2024, Eq. (2.2), with $X_{ij}$; the $\langle TTT\rangle$ pair as
$n_B\langle TTT\rangle_B$, $n_F\langle TTT\rangle_F$ (Chang et al., Eq. (2.7)); `chiral` as the three-scalar structure
that the chiral-channel expansions of Gimenez-Grau–Liendo (Eq. (2.13)) and Cornagliotto et al. (Eq. (2.8)) define. The
$O(N)$ placeholders "$\lambda\,T^{O(N)}_{abc}$" were replaced by explicit tensors, one structure per three-point
function: for $O(2)$ the flavor structures of Chester et al. 2019, Eqs. (11)–(13); for $O(3)$ the tensors implied by the
four-point structures of Chester et al. 2020, App. C, Eq. (32), which the paper does not write: they were inferred and
checked numerically to reproduce all nine four-point structures that involve them (with $\langle tt\rangle$ of its
Eq. (13)), and give $\lambda_{\phi\phi t} = 1$ in free theory. No value, method or refs changed (checked by script).

**Three-point functions (November 2026).** David: "we are presenting three point functions, not OPE coefficients"; "we
want to organize according to unordered triples of operators." `ope_coefficients` became `three_point_functions` and
`ope_structures` became `three_point_structures` (the standard file `data/three_point_structures.yaml`, its schema
`schema/three_point_structures.schema.json`, this document `docs/THREE_POINT.md`), in all nine entries; the quantity
category `ope` keeps its id. Items are unordered triples written lightest first; the one value whose source used
another order (⟨TTε⟩ of Chang et al.) carries `order`. Values that are a square or a modulus say so (`value_of`). The
page section is "Three-point functions", labelled by $\langle O_1O_2O_3\rangle$, without per-row symbols. Every value is
present exactly once after the rename (checked by script), and all 169 pages render without console errors.
