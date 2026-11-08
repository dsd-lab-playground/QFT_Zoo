# OPE coefficients: data and presentation

An OPE coefficient is a number attached to a **triplet of operators** and a **three-point structure**: the
three-point function $\langle O_1 O_2 O_3\rangle$ is a sum of independent tensor structures, and each coefficient
multiplies one of them. The same physical coefficient can be quoted in different normalizations or bases (Simmons-Duffin's
$f_{\sigma\sigma T'}$ and Reehorst's $\lambda_{\sigma\sigma T'}$ differ by $\lambda^2 = 2^\ell f^2$), and a spinning
three-point function can have several independent coefficients ($n_B$ and $n_F$ of $\langle TTT\rangle$ in 3d).
So the zoo records, for every value, both the triplet and the structure it multiplies. That is the *data*. How a theory
page groups and orders the values is the *presentation*, a fixed rule applied in the same way to every entry. The
summary for contributors is in [CONTRIBUTING.md](../CONTRIBUTING.md), *OPE coefficients*.

---

## 1. Data

### 1.1 Triplets: `ope_coefficients`

OPE coefficients are not `quantities`. Each item of an entry's `ope_coefficients` list is one triplet of operators and
holds every value recorded for it:

```yaml
ope_coefficients:
  - operators: ['\sigma', '\sigma', 'T''_{\mu\nu}']     # names from the operators table, exactly as written there
    values:
      - structure: sd16                                # what this value multiplies (1.2)
        symbol: "f_{\\sigma\\sigma T'}"                # how it is written; defaults to the structure's symbol
        value: '0.0105745(42)'
        method: CB-EFM
        refs: [simmonsduffin2016]
        note: '[@simmonsduffin2016, Table 2, p. 72], $T''_{\mu\nu}$ row. Not rigorous.'
      - structure: reehorst2021                        # the same coefficient, in another paper's basis
        symbol: "\\lambda_{\\sigma\\sigma T'}"
        value: '0.02107(20)'
        method: CB, rigorous
        refs: [reehorst2021]
        note: '[@reehorst2021, Table 1, p. 4]. Rigorous, assuming ...'
  - operators: ['T_{\mu\nu}', 'T_{\mu\nu}', 'T_{\mu\nu}']
    values:
      - structure: ttt-free-boson-3d                   # standard structures need no definition in the entry
        value: '0.933444559(75)'                       # symbol: n_B, from the structure
        method: CB, non-rigorous error
        refs: [chang2024]
      - structure: ttt-free-fermion-3d
        value: '0.013094116(33)'
        method: CB, non-rigorous error
        refs: [chang2024]
```

- **`operators`**: the three operators of $\langle O_1 O_2 O_3\rangle$, with $O_3$ the operator exchanged in
  $O_1\times O_2$, in the order that the values' structures assume (the sign of a coefficient can depend on it). Each
  is the `name` of an operator in the entry's `operators` table, written exactly as there, so the build can check that
  it exists and the page can read its dimension. An operator that is not in the table is written `{label: '...'}`
  (LaTeX); the build counts these (`! N OPE operator(s) named by a label`), and adding the operator to the table is better.
- **`values`**: every determination of a coefficient of this triplet: by different methods or papers, in the same
  structure or in different ones. Each value has `structure` (required) and `value`, and as usual `method`, `refs` and
  `note`; optionally `symbol` (the coefficient as written, e.g. `'\lambda_{\sigma\sigma\epsilon}'`, `'\lambda^2_{u^2}'`,
  `'|C_{\phi\phi\phi}|'` when the number is the square or the modulus) and `description` (about this value, rarely needed).
- One item per triplet: two items with the same three operators (in any order) are an error.
- **Never convert values between structures.** A value quoted in a paper's own basis is recorded in that basis, labelled
  by it; if two papers use different bases, they are two values of the same triplet with different `structure`s.
- Notes are about the value: where in the paper it is, its rigor, assumptions, agreement with other values. A
  statement of convention (how operators or blocks are normalized) belongs in the structure, once.

Why a separate list rather than `quantities` with extra fields: an OPE coefficient is identified by its triplet and its
structure, not by a symbol; the schema can then require both; all values of one triplet sit together in the file as they
do on the page; and the site needs no guessing (the old site inferred OPE coefficients and their operators by parsing
symbols like `\lambda_{\sigma\sigma\epsilon}`). `quantities` keep the theory's other numbers ($c$, $C_T$, exponents).
Three-point data that is not one triplet's coefficient (a structure constant as a function of continuous labels, such
as the DOZZ formula; a reflection amplitude; a ratio of OPE coefficients; one value for several theories) stays in
`quantities` with `category: ope` and is shown in the same section, after the triplets.

### 1.2 Structures

A value's `structure` is an id: one of the few **standard structures** of
[`data/ope_structures.yaml`](../data/ope_structures.yaml), or one the entry defines in its **`ope_structures`** list.
People invent many bases, and the zoo does not try to define a universal vocabulary: a structure that is a choice of a
paper is defined in the entry by reference to that paper's basis.

**Standard structures** (shared by all entries; add one only when the literature really agrees on it):

| id | symbol | name | meaning |
|---|---|---|---|
| `scalar` | $\lambda$ | three scalars, unit-normalized | three scalars, singlets of any continuous symmetry, with $\langle O_iO_i\rangle = \lvert x\rvert^{-2\Delta_i}$ (default); in embedding space $\lambda_{123}/(P_{12}^{\frac{\Delta_1+\Delta_2-\Delta_3}{2}}P_{23}^{\frac{\Delta_2+\Delta_3-\Delta_1}{2}}P_{31}^{\frac{\Delta_3+\Delta_1-\Delta_2}{2}})$ |
| `vector-vector-singlet` | $\lambda$ | vector × vector → singlet, $\delta_{ij}$ | $\langle\phi_i\phi_j s\rangle = \lambda\,\delta_{ij}\times$ the three-scalar structure, $O(N)$ (default) |
| `ttt-free-boson-3d`, `ttt-free-fermion-3d` | $n_B$, $n_F$ | free-boson / free-fermion structure | $\langle TTT\rangle = n_B\langle TTT\rangle_B + n_F\langle TTT\rangle_F$ in 3d (one basis, two coefficients) |

A standard structure may say which spins its operators have (`spins`) and in which dimension it is defined (`d`); the
build checks both against the entry. `default: true` marks a structure that a reader assumes when none is named: its
values carry no label on the page (2.3).

**An entry's own structures**:

```yaml
ope_structures:
  - id: chang2024-tte                       # what values write in `structure:`
    symbol: '\lambda'                       # the source's symbol (optional)
    ref: 'chang2024, Eq. (2.2)'             # the formula that defines it: a reference key and a locator
    description: 'The parity-even structure of $\langle TT\epsilon\rangle$ as normalized by [@chang2024, Eq. (2.2)], ...'
  - id: reehorst2021
    symbol: '\lambda'
    ref: 'reehorst2021, p. 6, fn. 3'
    description: 'Scalar–scalar–spin-$\ell$ structure, external scalars unit-normalized, with the block normalization of ...;
      in embedding space the coefficient of $V_{3,12}^\ell$ [@costa2011, Eqs. (4.10)–(4.12)] ...'
    embedding: '\langle\phi_1(P_1)\,\phi_2(P_2)\,O(P_3,Z_3)\rangle = \lambda_{12O}\, \frac{V_{3,12}^{\,\ell}}{P_{12}^{\frac{\Delta_1+\Delta_2-\Delta-\ell}{2}} P_{23}^{\frac{\Delta_2+\Delta+\ell-\Delta_1}{2}} P_{31}^{\frac{\Delta+\ell+\Delta_1-\Delta_2}{2}}}'
    relation: '$\lambda^2 = 2^\ell f^2$ relative to the structure of [@simmonsduffin2016, Eq. (A.16)] ([@reehorst2021, p. 16]).'
```

- `id` (required): unique in the entry, different from the standard ids.
- `ref` or `name` (at least one): `ref` cites the formula that defines the structure (`'key, Eq. (2.2)'`; the key must
  be in the entry's references); `name` is a short name readers will recognize, for a structure that has one. The page
  labels the structure by its name, else by the citation.
- `symbol`: the source's symbol ($\lambda$, $f$, $n_B$, ...); a value without its own `symbol` shows it.
- `description`: what the structure is, precisely: which three-point function, how the operators are normalized, how the
  tensor structure or conformal block is normalized (e.g. "blocks start as $z^{(\Delta-\ell)/2}\bar z^{(\Delta+\ell)/2}$"),
  with citations.
- `relation` (optional): how it relates to another basis, **only as a source states it** (or as it follows from formulas
  the sources state, each cited), with the citation. It is information for readers; values are never converted with it.
- `form`: what the structure is, as a LaTeX formula shown in its line (never folded), so that a reader can identify
  it without opening the reference (David, 2026-11-07: "Label every OPE structure by what it is, never by a bare λ plus
  a citation"). Write the structure out where that is practical; for a complicated one use a form some work has given
  it, citing that work: an embedding-space combination (⟨TTε⟩ of Chang et al.), the form in a source's own basis
  (e.g. ScalarParityEven$_{\Delta_\epsilon}$), an SO(3) structure $|j_{12}, j_{123}\rangle$, a q-basis structure
  $[q_1, q_2, q_3]$. Choose by judgement. A single-monomial `embedding` serves as the form; otherwise `form` is required
  (the build checks it). The citation follows the form as the source of the convention.
- `embedding` (optional): the three-point function in embedding space, in the notation of *Spinning Conformal
  Correlators* (1.4), as a LaTeX formula without `$...$`; the page shows it in display math under the description. Give
  it only when the structure is a single monomial: one product of $V_{i,jk}$ and $H_{ij}$ over powers of $P_{ij}$
  (David, 2026-11-07: "By simple, I meant like 1 monomial"). A combination of several monomials, such as the
  $\langle TT\epsilon\rangle$ structure of Chang et al. 2024, Eq. (2.2), is identified by its citation only. The coefficient appears in it with the factor its source's normalization needs, e.g.
  $2^{\ell/2} f_{12O}$ for the blocks of Simmons-Duffin 2016, Eq. (A.16); the description says how that factor
  follows from the sources, with citations, and that the other operators are unit-normalized (two-point function
  $H_{12}^\ell/P_{12}^{\Delta+\ell}$). Where a factor depends on a convention that the sources do not pin down, leave
  `embedding` out and say so, rather than guess. Citations go in the description, not in the formula. A structure
  whose source defines it in another basis (the $\langle TTT\rangle$ free-field structures; the $O(N)$ tensor
  structures of Chester et al., whose tensor normalization is not recorded) has none.
- `basis` (rare): for a structure that is one element of a basis of several independent structures of the same
  three-point function, an id shared by its elements (as `ttt-free-3d` for $n_B$, $n_F$). Values of different elements
  are different coefficients (2.2). A structure that is the only one of its three-point function in its paper's basis
  (scalar–scalar–spin-$\ell$, $\langle TT\epsilon\rangle$ parity-even) has no `basis`.

Adding a new paper's values therefore takes one structure definition (its id, the citation of its defining formula, a
sentence of description) and its values; nothing in other entries or in the site changes.

### 1.3 Checks (`scripts/build.py`, `scripts/ope.py`)

- every operator name is in the entry's operators table (or is a flagged `{label}`);
- every `structure` is a standard id or one of the entry's `ope_structures`; entry ids are unique, do not shadow a standard
  id, and are each used by some value; a structure's `ref` and every value's `refs` name the entry's references;
- the operators' spins (from the table) match the structure's `spins`, and the entry's `d` its `d`;
- one item per triplet; no two values claim the same (triplet, structure, method, refs, value);
- an `embedding` is a string (schema) with no `$` and no citation in it; a standard structure that cites a key
  (`[@costa2011, ...]`) needs that key in the references of every entry that uses it (citations are read against the
  entry's references); the build reports how many structures give their embedding-space form;
- methods as for every row (CONTRIBUTING.md, *Methods*). `tests/test_ope.py` tests these checks.

### 1.4 Embedding-space notation (Costa, Penedones, Poland, Rychkov)

*Provisional* (docs/PRINCIPLES.md §2): this notation was adopted before surveying how the field writes three-point
structures; it will follow the outcome of that survey.

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

---

## 2. Presentation policy

The page shows the entry's OPE data in the **OPE coefficients** section (in the single *Data* table of an entry with few
quantities, after the other quantities). The rule:

### 2.1 Items and their order

One item per triplet. Items are ordered by the dimensions of their operators: each triplet's three dimensions (from the
operators table; the smallest when an operator has several determinations) are sorted, lightest first, and compared in
turn, so $\lambda_{\sigma\sigma\epsilon}$, $f_{\sigma\sigma T}$, $\lambda_{\sigma\sigma\epsilon'}$, …, $\lambda_{\epsilon\epsilon\epsilon}$, …;
ties keep the data order; an operator named by label counts as heaviest. Quantities with `category: ope` follow the
triplets, in data order.

### 2.2 Lines inside an item

An item has one line per independent coefficient: each element of a multi-element basis (a structure with `basis`) is
its own line ($n_B$ and $n_F$ of $\langle TTT\rangle$); all other values of the triplet are one line, one coefficient,
even when its values are quoted in different bases ($f_{\sigma\sigma T'}$ and Reehorst's $\lambda_{\sigma\sigma T'}$).
A triplet with a single structure therefore looks like a single row.

Inside a line, values are grouped by structure (standard structures in the order of `data/ope_structures.yaml`, then the
entry's in the order of its `ope_structures`), and within a structure ordered best first as for every quantity (exact,
then rigorous intervals by width, then by relative error). The first value shows; the others fold under "+n more". The
disagreement badge compares a value only with the best value **in the same structure**: values in different bases are
different numbers.

### 2.3 Labels

Each row names the structure its value multiplies, under its symbol: the structure's name, else "structure" and the
citation of its defining formula; clicking it shows the definition. A value in a **default** standard structure (three
scalars, unit-normalized; $O(N)$ vector × vector → singlet) carries no label, since that is what readers assume. A
folded row shows its own symbol when it differs from the line's first row (e.g. $\lambda_{\sigma\sigma T'}$ under
$f_{\sigma\sigma T'}$). The switch `OPE_LABEL_DEFAULTS` in `site/app.js` labels default structures too.

### 2.4 Definitions, once

Below the table, a short **Structures** list defines every structure used on the page, once: its symbol, its name or
citation, "(standard)" for a standard one (and, for a default one, that its values carry no label), its description,
its embedding-space form (`embedding`, in display math, 1.4) and any stated relation to other bases. Row descriptions
never repeat a convention.

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

Open points: the $O(2)$ and $O(3)$ entries' coefficients involving the symmetric traceless $t$ are labelled by the
papers' normalization (Chester et al. 2019, 2020) without a locator, so they have no embedding-space form; the
normalization of `lee-yang-3d`'s $\lvert C_{\phi\phi\phi}\rvert$ is assumed to be the standard unit normalization.

**Embedding-space forms (November 2026).** David: "When a structure is a simple embedding space structure, you should
use the notation of Spinning Conformal Correlators." Structures gained `embedding` (1.4): `scalar`,
`vector-vector-singlet`, `chiral` (Eq. (2.8)); `sd16` and `reehorst2021` ($V_{3,12}^\ell$, with $2^{\ell/2}f$ and
$\lambda$); `chang2024-tte` (the combination of Chang et al. 2024, Eq. (2.2)). The $\langle TTT\rangle$ free-field structures
and the $O(N)$ tensor structures have none. The reference `costa2011` was added to every entry that shows one
(`poland2019` to `ising-3d`, for the block normalization). No value, method or refs changed (checked by script).
