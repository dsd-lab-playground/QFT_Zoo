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
| `scalar` | $\lambda$ | three scalars, unit-normalized | three scalars, singlets of any continuous symmetry, with $\langle O_iO_i\rangle = \lvert x\rvert^{-2\Delta_i}$ (default) |
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
    description: 'Scalar–scalar–spin-$\ell$ structure, external scalars unit-normalized, with the block normalization of ...'
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
- `relation` (optional): how it relates to another basis, **only as a source states it**, with the citation. It is
  information for readers; values are never converted with it.
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
- methods as for every row (CONTRIBUTING.md, *Methods*). `tests/test_ope.py` tests these checks.

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

Above the table, a short **Structures** list defines every structure used on the page, once: its symbol, its name or
citation, "(standard)" for a standard one (and, for a default one, that its values carry no label), its description
and any stated relation to other bases. Row descriptions never repeat a convention.

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
papers' normalization (Chester et al. 2019, 2020) without a locator; the normalization of `lee-yang-3d`'s
$\lvert C_{\phi\phi\phi}\rvert$ is assumed to be the standard unit normalization.
