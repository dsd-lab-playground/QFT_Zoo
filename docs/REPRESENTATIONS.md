# Operator representations: data and presentation

Every operator in the zoo carries a **representation of the full symmetry group** of its
theory: the spacetime part (scaling dimension, Lorentz representation, parity) and the
internal part (an irrep of each factor of the global symmetry group). That is the *data*.
How a theory page groups and orders its operators table is a separate choice, the
*presentation policy*, applied to the data in the same way for every entry. This document
specifies both. The summary for contributors is in [CONTRIBUTING.md](../CONTRIBUTING.md),
*Operator representations*.

Until every entry is migrated, the old free-text `rep` field is still accepted (see
*Backward compatibility*).

---

## 1. Data

### 1.1 The symmetry declaration

The entry's `symmetry` block declares the group that operator labels refer to:

```yaml
symmetry:
  spacetime: '3d conformal group with parity'
  euclidean: '$O(4,1)$'
  lorentzian: '$O(3,2)$'
  supercharges: 0
  global: '$SU(N_f)$ flavor, $U(1)_{\rm top}$ ..., charge conjugation, parity and time reversal'
  parity: true
  global_group:
    - {id: SU(Nf), group: SU(N_f)}
    - {id: U(1)_top, group: U(1), tex: 'U(1)_{\rm top}'}
```

- `global` stays what it was: the global symmetry **in words** (Markdown), with
  higher-form symmetries, quotients, anomalies and anything else worth saying. It is shown on
  the page. It is not renamed, because it is prose and every entry already has it.
- `global_group` (new) is the global symmetry as a **list of factors**, in the order the
  tables group by. Each factor has
  - `id`: the key operators use (no spaces or `$`), e.g. `Z2`, `O(3)`, `SU(Nf)`, `U(1)_top`;
  - `group`: its type, one of `Z2`, `Z_n` (`Z3`, `Z_4`, ...), `U(1)`, `O(N)`, `SO(N)`,
    `SU(N)`, `Sp(N)` (N even, the dimension of the fundamental: `Sp(2)` = `SU(2)`), `S_n`,
    `D_n` (dihedral, of order $2n$) or `finite` (any other finite group, with its irreps
    listed). `N` is an integer or a parameter symbol of the entry (`SU(N_f)`, `O(N)`), which
    the build checks against `parameters`;
  - `tex` (optional): the display name when it is not the group's own, e.g.
    `'U(1)_{\rm top}'`, `'SU(4)_R'`;
  - `irreps` (for `finite` only): `[{label, tex, dim}]`, the trivial irrep first, in the order
    tables use;
  - `note` (optional): how the factor sits in the full group.

  A theory with no internal global symmetry writes `global_group: []`. Declaring
  `global_group` (even empty) marks the entry as migrated.
- `parity` (new, required with `global_group`): `true`, `false` or `conditional` (parity
  only at special values of the parameters, said in `spacetime`, e.g. $\theta \in \{0,\pi\}$
  in $\mathcal{N}=4$ SYM; operators then state their parity at those values). "Parity" means
  what CONTRIBUTING.md, *Spacetime symmetry*, says: a reflection, possibly combined with an
  internal symmetry. `spacetime` and `euclidean`/`lorentzian` keep saying it in words and
  groups; this field is the machine-readable form, and the two must agree.
- `time_reversal: independent` (new, rare): see 1.3.

**What the factor list does not yet express.** The full internal group is not always a direct
product of the declared factors: quotients ($(SU(2)\times U(1))/\mathbb{Z}_2$), and discrete
symmetries acting as outer automorphisms (charge conjugation acting on $SU(N_f)$ and
$U(1)_{\rm top}$ in QED$_3$; $S_3 = \mathbb{Z}_3 \rtimes \mathbb{Z}_2$ is declared as one
factor `S_3`, which is how such a case should be handled when the group has a standard name).
A quotient restricts which label combinations occur but does not change the labels, so it is
said in `note` or in `global`. An outer automorphism that is not part of a declared factor is
for now left out of `global_group` and said in words; a later extension can add it as an
extended factor (labels: orbits of irreps, plus a sign for self-conjugate ones), exactly as
parity is treated below.

### 1.2 Operator fields

```yaml
operators:
  - name: '\sigma'
    Delta: '0.518148806(24)'
    spin: 0
    parity: even
    global: {Z2: odd}
    method: CB
    refs: [chang2024]
```

| Field | Meaning |
|---|---|
| `Delta` | scaling dimension (unchanged) |
| `spin` | Lorentz representation in the default family: 3d spin $\ell \in \tfrac12\mathbb{Z}$; in $d \geq 4$ the symmetric traceless spin-$\ell$ tensor (4d: $(\ell/2, \ell/2)$); 2d: $h - \bar h$ |
| `weights` | 2d: $(h, \bar h)$ (unchanged) |
| `lorentz` | a Lorentz representation outside the default family: 4d `'(j, jbar)'`, e.g. `'(1/2, 0)'`, `'(1, 0)'`; $d \geq 5$ an $SO(d)$ highest weight `'[l1, l2, ...]'` (Young diagram rows for tensors, e.g. `'[1, 1]'` for a 2-form; half-integers for spinors, `'[1/2, 1/2]'`). Not used in 2d and 3d, where `spin`/`weights` say everything |
| `parity` | `even`, `odd`, `pair` or `unknown` (1.3) |
| `T` | time reversal, only with `symmetry.time_reversal: independent` (1.3) |
| `global` | a label for **every** declared factor: `{factor id: label}` (1.4); `unknown` where it is not known |
| `multiplet` | supersymmetric theories: `{name, component, type?}` (1.5) |
| `role` | what the operator is or does: `order parameter`, `thermal`, `supercurrent`, `Coulomb-branch generator` (Markdown). Never part of the representation |
| `degeneracy`, `method`, `refs`, `note` | unchanged |

### 1.3 Parity and time reversal

Parity is part of the spacetime representation, on the same footing as spin and $\Delta$.
When `symmetry.parity` is `true` or `conditional`, every operator states it:

- `even`, `odd`: the parity eigenvalue. With parity combined with an internal symmetry, it is
  the eigenvalue of the combined operation, in the convention the entry states.
- `pair`: parity maps the operator to a partner in a *different* representation of the rest of
  the group, so the pair forms one irrep of the full group and there is no eigenvalue. This is
  forced, and the build checks it, for a 2d operator of non-zero spin ($s \to -s$, e.g.
  $W$ with weights $(3,0)$ and $\bar W$ with $(0,3)$) and a 4d operator with $j \neq \bar\jmath$
  (left- and right-handed). It also covers internal charges reversed by parity: in QED$_3$ the
  topological current $j^{\rm top} = \star f/2\pi$ is an axial vector, so parity maps a monopole
  of charge $q$ to one of charge $-q$, and monopole operators are `pair`. In 3d (any odd $d$),
  $O(d) = SO(d)\times\{\pm1\}$, so every bosonic Lorentz irrep has a parity label.
- `unknown`: not recorded. Use it rather than guess. Two common reasons: fermionic operators,
  whose overall parity sign is a convention (the two lifts of a reflection to the Pin group)
  unless the entry fixes one; and parity combined with an internal rotation acting
  non-trivially inside a multiplet (the $SU(N_f)$-adjoint bilinear of QED$_3$), where the sign
  depends on how the combined operation is extended to that irrep.

Evidence for a parity that the source does not state in words is acceptable when it is a
standard argument from the data, e.g.: in 3d, the OPE of two parity-even scalars (or of a
parity-even scalar with itself) contains only parity-even operators, because the three-point
structure of two scalars and a spin-$\ell$ operator is unique and parity-even (in the frame
$x_1 = 0$, $x_2 = \infty$, $x_3 = e$ there is one vector, too few for $\epsilon_{\mu\nu\rho}$);
in 2d the same holds for scalar operators in the OPE (but not for spinning ones); a
conserved stress tensor is parity-even; a lattice spin or energy density is a reflection
invariant scalar. Say the argument in the pull request.

**Time reversal** is usually not an independent label. In a unitary Lorentzian theory CRT is
a symmetry, and $T = (CRT)\cdot P$ up to an internal symmetry, so an operator's $T$ eigenvalue
follows from its parity, spin and internal labels (CONTRIBUTING.md, *Spacetime symmetry*).
Set `symmetry.time_reversal: independent` and give `T` on operators only when that fails: when
the internal symmetry relating $T$ to $CRT \cdot P$ is not among the declared factors (so the
labels cannot determine it), or when $T$ is a symmetry and $P$ is not (then $CRT \cdot T$ is a
symmetry only combined with something undeclared). A Euclidean-only theory has no $T$.

### 1.4 Irrep labels

A label is written in the controlled vocabulary of its factor's group type. Different spellings
of the same irrep (`vector`, `Y(1)`, `sym(1)`) are the same label: the build converts each to a
canonical form, used for grouping. Labels containing commas (`Y(2,1)`, `Dynkin(0,2,0)`) must be
quoted in YAML flow style: `{SU(4)_R: 'Dynkin(0,2,0)'}`.

| Group | Labels | Shown as | Order in tables |
|---|---|---|---|
| `Z2` | `even`, `odd` | $\mathbb{Z}_2$-even, $\mathbb{Z}_2$-odd | even, odd |
| `Z_n` | charge `q` (integer, reduced to $-n/2 < q \le n/2$), `±q` for a conjugate pair in one row | $\mathbb{Z}_3$ charge $1$ | $\lvert q\rvert$, then $\pm$, $+$, $-$ |
| `U(1)` | charge `q`: integer, `a/b`, or `±q` | $U(1)$ charge $\tfrac12$; $U(1)$-neutral for 0 | $\lvert q\rvert$, then $\pm$, $+$, $-$ |
| `O(N)`, `SO(N)` | `singlet`, `vector`, `adjoint`, `sym(k)` (rank-$k$ symmetric traceless), `anti(k)` (rank-$k$ antisymmetric), `Y(r1,r2,...)` (Young diagram by rows), `spinor` (SO only); `k` may be a parameter expression (`sym(N/2)`) | $O(3)$ vector, $O(N)$ rank-2 symmetric traceless, $O(N)$ adjoint (rank-2 antisymmetric) | number of boxes, then shape (longer first row first: symmetric before antisymmetric); parameter-dependent sizes after numeric ones; spinors after tensors |
| `SU(N)` | `singlet`, `fundamental`, `antifundamental`, `adjoint`, `sym(k)`, `anti(k)`, `sym(k)bar`, `anti(k)bar`, `Dynkin(a1,...,a_{N-1})` (numeric N) | $SU(N_f)$ adjoint; with numeric N also the bold dimension and, when not named, the Dynkin label: $SU(4)_R$ $\mathbf{20}'$ $[0,2,0]$ | numeric N: dimension, then the pair $R, \bar R$ together ($R$ first); parametric N: number of indices, then fundamental, adjoint, symmetric, antisymmetric, conjugate after |
| `Sp(N)` | `singlet`, `fundamental`, `adjoint`, `anti(k)`, `Dynkin(...)` | | number of indices |
| `S_n` | `trivial`, `sign`, `standard`, `Y(partition)` | $S_3$ standard (2-dimensional) | dimension, then longer first row first |
| `D_n` | `A1`, `A2`, `B1`, `B2` ($n$ even), `E1` ... `E_{⌊(n−1)/2⌋}` | $D_4$ $E_1$ | as listed |
| `finite` | the declared `irreps` labels | their `tex` | as declared |
| `listed` | the declared `irreps` labels (the factor also gives `tex`) | their `tex` | as declared |
| `U(1)` (symbolic) | a symbol or expression for a row that stands for a family labelled by its charge: `n`, `l/(k+2)` | $U(1)$ charge $n$ | after every numeric charge |
| any | `unknown` | "$G$ representation not recorded" | last |
| any | a list, e.g. `[singlet, adjoint]` | $SU(N_f)$ singlet $\oplus$ adjoint | after its lowest summand |

The build rejects labels that are not valid for the group: a Young diagram that is not an
$O(N)$ irrep (first two columns longer than $N$), Dynkin labels of the wrong length, a partition
of the wrong size, a parameter that the entry does not define. A **list** is a direct sum: a row
that lists several operators in different irreps at once (QED$_3$'s "$J^{\rm top}_\mu$,
$J^{SU(N_f)}_\mu$"). It is accepted but counted by the build: one row per irrep is better.

`listed` is for a group outside the vocabulary that is not finite or has no fixed size: a non-compact group with
continuous series ($SL(2,\mathbb{C})$ of $H_3^+$), the shift group $\mathbb{R}$ of a non-compact boson, $U(1)^d$ with
vector charges, $S_Q$ or $O(n)$ at non-integer $Q$ or $n$. Like `finite`, it lists the irreps the entry uses, the
trivial one first.

Products of groups are lists of factors; each operator labels each factor. Groups not in the
table (exceptional groups, $Spin(N)$ with spinor-tensor irreps, $\mathfrak{osp}$ R-symmetries)
are added to the vocabulary in `scripts/reps.py` when a migrated entry first needs them; until
then `finite` (for finite groups) or a legacy entry serves.

*Added for the $d \geq 4$ entries* (`scripts/reps.py`, extension blocks):

| Group | Labels | Shown as |
|---|---|---|
| `E_6`, `E_7`, `E_8` | `singlet`, `adjoint` ($\mathbf{78}$, $\mathbf{133}$, $\mathbf{248}$); `fundamental` ($\mathbf{27}$ of $E_6$, $\mathbf{56}$ of $E_7$), `antifundamental` ($\overline{\mathbf{27}}$) | $E_8$ adjoint $\mathbf{248}$ |
| `Lie(G)` | `singlet`, `adjoint` | $G_L$ adjoint |
| `U(1)` | also a charge that is an expression in the entry's parameters, with an optional sign or `±`: `'2(N_f-N_c)/N_f'`, `'±N_c'` (after the numeric charges) | $U(1)_B$ charge $\pm N_c$ |

`Lie(G)` is a continuous group that differs between the members of a family, so that no single group type fits:
$G_L\times G_R$ of conformal matter, the $E_n$ of Seiberg's 5d theories, the flavor group of each Argyres–Douglas
theory. `G` is its display name; only labels valid for every member are offered, and `adjoint` is the adjoint of its
Lie algebra (reducible for a member whose group is not simple).

### 1.5 Supersymmetric theories

The R-symmetry is a factor of `global_group` like any other (`SU(4)_R`, `SU(2)_R`, `U(1)_r`),
and every component operator carries its own labels. In addition, `multiplet` places an operator
in its supermultiplet:

```yaml
multiplet: {name: '$\sigma$', component: 'Q^2'}           # epsilon = top component of the sigma multiplet
multiplet: {name: stress tensor, component: primary, type: half-BPS}
```

- `name`: the multiplet, by its superconformal primary (`'$\sigma$'`) or its standard name
  (`stress tensor`, `Konishi`). Components of one multiplet use the same name.
- `component`: `primary`, or the supercharges acting on the primary, in LaTeX (`Q`, `Q^2`,
  `Q\bar Q`).
- `type` (optional): shortening condition or standard symbol (`half-BPS`, `long`,
  `$A_1\bar A_1$`, `$\mathcal{B}_{[0,2,0]}$`).

The pilot uses this lightly. A full treatment would label each multiplet by its superconformal
representation (e.g. Cordova–Dumitrescu–Intriligator notation) and let the table group by
multiplet; that is a natural extension of the policy below.

### 1.6 Backward compatibility

Entries without `global_group` keep the free-text `rep` and are rendered by the old heuristic
code path, which is to be removed once all entries are migrated. `python scripts/build.py`
counts them, like free-text methods:

```
✓ 6 entries give structured operator representations (docs/REPRESENTATIONS.md)
! 325 operator rep(s) in 89 entries still free text instead of structured `global` / `parity`
```

In a migrated entry `rep` is an error; in an unmigrated one `global`, `parity` and `T` are
errors (declare the group first). `role`, `multiplet` and `lorentz` may be used in either.

The build adds a derived field `irrep` to every operator of a migrated entry in
`theories.json` (canonical label, display text, whether it is trivial, sort key per factor), and
`global_factors` to the entry, so that the site needs no knowledge of the vocabulary.

---

## 2. Presentation policy

The operators table is organized by a **grouping hierarchy** applied to the data. The same
rules hold for every migrated entry, so a contributor can predict the table from the YAML.

### 2.1 Levels

1. **Global-symmetry irrep** (the tuple of labels, one per factor). Order: the trivial
   representation first; then lexicographic over the factors in their declared order, each
   factor ordered by its group type's order (table in 1.4); `unknown` last.
2. **Parity**: even, odd, pair, unknown.
3. Within a group: by **spin**, then by **$\Delta$** (of the preferred determination), then data
   order.

This follows the usual practice of the field: sectors are labelled first by global symmetry
(the $\mathbb{Z}_2$-odd sector of Ising, the $O(N)$ vector sector), and parity is a second
label that makes each sector easier to read.

### 2.2 Which levels are used

- A level whose value is **the same for every operator** on the page is not a grouping level.
  It is stated once, above the table: "All operators listed: parity-even." The same holds for
  spin when all operators share it ("spin 0").
- If, after that, **no group would contain two operators**, the table is not grouped: it is one
  flat table, in the hierarchy's order, and the remaining levels become columns
  (*Representation*, *P*).
- Otherwise each group gets a heading naming its labels: "$\mathbb{Z}_2$-odd, parity-even".

### 2.3 Headings

- A heading names each factor in a non-trivial (or unknown) representation; factors in their
  trivial representation are omitted. A group trivial under every factor is "$\mathbb{Z}_2$-even",
  "$O(3)$ singlet" etc. for a single factor, and "singlet of $G_1\times G_2$" for several.
- Parity is written parity-even, parity-odd, parity-paired, parity not recorded.
- The number of operators follows the heading; the heading's ▾ folds the group. Nothing starts
  folded.

### 2.4 Columns

- A column is shown only if its value varies within the displayed groups. A label that a level
  groups by is in the heading, never in a column, and a label constant over the page is stated
  above the table: information is never repeated.
- Always: *Operator* (with its `role` as a muted tag), *Δ* (several determinations of one
  operator fold under "+n more", with the disagreement badge, as for quantities), *Source*.
- When present: $(h,\bar h)$ (2d), *Mult.* (degeneracy), *Spin* (or $(j,\bar\jmath)$ when some
  operator gives `lorentz` in 4d), *T* (only with `time_reversal: independent`), *Multiplet*,
  *Notes*.

### 2.5 Degenerate cases

- **No global symmetry** (`global_group: []`): parity is the only level (3d $\mathcal{N}=1$
  super-Ising: parity-even, parity-odd, parity not recorded).
- **No parity** (`parity: false`): the global irrep is the only level; no *P* column.
- **Neither**, or every level constant: a flat table ordered by spin, then $\Delta$.
- **Large tables** keep the same rules; groups fold individually.

### 2.6 Future refinements (not implemented)

- Per-group-type choices of which factor leads (e.g. R-symmetry before flavor symmetry in
  SCFTs, or grouping by supermultiplet), declared by order in `global_group` as now.
- Splitting very large groups (more than ~15 operators) by spin as a third heading level.

---

## 3. Pilot

Migrated: `ising-3d`, `o3-model-3d`, `gny-n1-3d`, `qed3-3d`, `potts-3-state`, `n4-sym`. Only
operator `rep` lines were replaced (by `parity`, `global`, `role`, `multiplet`) and `parity` and
`global_group` added to `symmetry`; every $\Delta$, spin, method, reference and note is unchanged.
Remarks that were part of `rep` ("order parameter", "thermal", "supercurrent") moved to `role`;
multiplet remarks ("superpartner of $\sigma$", "top of the $\sigma$ multiplet") became
`multiplet`.
