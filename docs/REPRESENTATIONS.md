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
| `multiplet` | supersymmetric theories: `{name, component, type?, cdi}`: house name and Cordova–Dumitrescu–Intriligator label (1.5) |
| `role` | what the operator is or does: `order parameter`, `thermal`, `supercurrent`, `Coulomb-branch generator` (Markdown). Never part of the representation |
| `degeneracy`, `method`, `refs`, `note` | unchanged |
| `family` | makes the row one record for a tower of operators: `{id, parameters: [{symbol, from, to, step, except}]}`, with Δ, spin and labels as expressions in the parameters (1.7) |
| `member_of`, `at` | the row records one member of a family of the entry, at the parameter values `at`, e.g. `{k: 2}` (1.7) |

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

Added with the migration of the 2d entries (`scripts/reps.py`, *extension: index symbols, ...*):

- `symbols` on a factor: names other than the entry's parameters that its labels may use, a running
  index of a family of operators in one row (`spin(j)` for $\Phi_j$, `sym(L)` for the $L$-leg
  operator) or a formal group size (`O(n)` at $n \to 0$).
- $SU(2)$: `spin(j)`, with $j$ a half-integer (the same label as `Dynkin(2j)`) or an expression
  (`spin(k/2)`, `spin(j)`).
- `S_n` and `D_n` with $n$ a parameter (`S_Q`, `D_k`): `trivial`, `standard`, `Y(l1,...)` for the
  irrep $[n-|l|, l_1, \ldots]$; `A1`, `A2`, `B1`, `B2`, `E1`, `E2`, ... ($E_j$: rotations act as
  $e^{\pm 2\pi i j/n}$).
- `SL(2,R)` (universal cover): `trivial`, `adjoint`, `D+(j)`, `D-(j)`, `D±(j)` (discrete series),
  `C(j, alpha)` (continuous series).
- A group named by a parameter (`group: G`): a generic simple group, with `singlet`, `adjoint`,
  `hw(lambda)` and its conjugate `hw(lambda)bar`.

### 1.5 Supersymmetric theories

The R-symmetry is a factor of `global_group` like any other (`SU(4)_R`, `SU(2)_R`, `U(1)_r`),
and every component operator carries its own labels. In addition, `multiplet` places an operator
in its supermultiplet:

```yaml
multiplet: {name: '$\sigma$', component: 'Q^2', type: long, cdi: '$L[0]_\Delta$'}   # epsilon in the sigma multiplet
multiplet: {name: flavor current, component: primary, type: '$\hat{\mathcal{B}}_1$', cdi: '$B_1\bar B_1[0;0]^{(2;0)}_2$'}
multiplet: {name: stress tensor, component: 'Q\bar Q', cdi: '$A_1\bar A_1[2]^{(0)}_2$'}  # 3d N=2: no house symbol
```

- `name`: the multiplet, by its superconformal primary (`'$\sigma$'`) or its standard name
  (`stress tensor`, `Konishi`). Components of one multiplet use the same name.
- `component`: `primary`, or the supercharges acting on the primary, in LaTeX (`Q`, `Q^2`,
  `Q\bar Q`).
- `type`: the multiplet in the **house notation** of its case (table below), as a symbol or a
  descriptive name (`chiral`, `long`). Omitted where the house name is descriptive and `name`
  already says it (`stress tensor`, `flavor current` in 3d $\mathcal{N}\le2$ and 4d $\mathcal{N}=1$).
- `cdi`: the multiplet in the notation of Cordova, Dumitrescu and Intriligator (CDI, arXiv:1612.00809),
  $X[j]^{(R)}_\Delta$ with their normalizations (e.g. their 4d $\mathcal{N}=2$ $u(1)_r$ charge is twice
  Dolan–Osborn's). Required in $d \ge 3$ (`unknown` if it cannot be determined); not used in 2d,
  which CDI do not cover. The build checks both, and that a family member's `type` and `cdi` are the
  family's at the member's parameter values (1.7).

The page shows `type` (else `name`) with the CDI label in a tooltip on hover or focus. The entry's
`symmetry.notes` says which notation it uses and cites it.

**Why this rule.** A survey of about 45 papers' TeX sources, weighted by INSPIRE citations
(November 2026), found no nomenclature that is standard across cases: each dimension and amount of
supersymmetry has its own house notation, and only CDI covers every case in $d \ge 3$. So the page
uses each case's house notation, and CDI is always one hover away.

| Case | House notation | Examples | Evidence |
|---|---|---|---|
| 4d $\mathcal{N}=2$ | Dolan–Osborn (hep-th/0209056) | $\hat{\mathcal{B}}_R$ (Higgs branch; $\hat{\mathcal{B}}_1$ moment map), $\mathcal{E}_r$ (Coulomb branch), $\hat{\mathcal{C}}_{0(0,0)}$ stress tensor, $\mathcal{D}_{R(0,j)}$, $\mathcal{C}_{R,r(j,\bar\jmath)}$, $\mathcal{A}^\Delta_{R,r(j,\bar\jmath)}$ long | Beem et al. 1312.5344 |
| 4d $\mathcal{N}=4$ | Dolan–Osborn | $\mathcal{B}^{\frac12,\frac12}_{[0,p,0](0,0)}$ half-BPS, $\mathcal{C}$, $\mathcal{A}^\Delta_{[0,0,0](\ell/2,\ell/2)}$ long | Beem–Rastelli–van Rees 1304.1803 |
| 3d $\mathcal{N}=8$, $\mathcal{N}=6$ | Dolan (0811.2740) letters | $\mathcal{N}=8$: $(B,+)$ (stress tensor, $[0020]$), $(B,2)$, $(A,0)$ long, $(A,2)$, $(A,+)$; $\mathcal{N}=6$: $(B,2)$ stress tensor, $(B,n)$, $(A,n)$, $(A,+)$ | Chester–Lee–Pufu–Yacoby 1412.0334; Binder–Chester–Jerdee–Pufu 2011.05728 |
| 3d $\mathcal{N}=4$ | usage split: mostly Dolan/Pufu style; CDI in some | $(B,+)$, $(B,-)$ Higgs- and Coulomb-branch half-BPS (Dolan's $(2,B,\pm)$), conserved (stress tensor), $(A,\dots)$ | Beem–Peelaers–Rastelli 1601.05378; Dedushenko–Pufu–Yacoby 1610.00740; CDI in Chang et al. 1910.03600 |
| 5d $\mathcal{N}=1$, 6d $(1,0)$ | letters with the $SU(2)_R$ label | $\mathcal{D}[2]$ flavor current, $\mathcal{B}[0]_0$ stress tensor, $\mathcal{L}[0]_{\Delta,\ell}$ long; types $\mathcal{A}$–$\mathcal{D}$ | Chang–Fluder–Lin–Wang 1710.08418; Chang–Lin 1705.05392 |
| 6d $(2,0)$ | Beem–Rastelli–van Rees style | $\mathcal{D}[2,0]$ stress tensor, $\mathcal{D}[p,0]$ half-BPS, $\mathcal{B}$, $\mathcal{C}$, $\mathcal{A}$, long $\mathcal{L}[p_1p_2]_{\Delta,\ell}$ | 1507.05637; Beem–Lemos–Rastelli–van Rees 1404.1079 |
| 4d $\mathcal{N}=1$, 3d $\mathcal{N}=1, 2$ | descriptive | chiral, antichiral, linear (current) multiplet, stress-tensor (Ferrara–Zumino) multiplet, long | standard usage |
| 2d $\mathcal{N}=(2,2)$ | chiral-primary language | $(c,c)$, $(a,c)$ rings, Ramond ground states, BPS / non-BPS | Lerche–Vafa–Warner |
| 2d small $\mathcal{N}=4$ | Eguchi–Taormina | massless (short, BPS) or massive (long), by $h$ and $su(2)$ isospin | Eguchi–Taormina 1988 |

4d $\mathcal{N}=3$ is not covered by the survey; its entries show the name with CDI on hover.

The pilot uses this lightly. A full treatment would let the table group by multiplet; that is a
natural extension of the policy below.

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

### 1.7 Operator families

Some towers of operators are known exactly as functions of a label: the half-BPS operators of a
superconformal theory, Coulomb-branch operators, conserved higher-spin currents, the vertex
operators of a free boson. Such a tower is **one operator record**, a *family*, not one record per
member. Its representation is a pattern in a parameter: "$\Delta = k$, spin 0, $[0,k,0]$ of
$SU(4)_R$, $k = 2, \dots, N$".

```yaml
  - name: '\mathcal{O}_k = \mathrm{Tr}\,\phi^{\{I_1}\cdots\phi^{I_k\}}'
    family:
      id: half-BPS                       # what member rows refer to; unique in the entry
      parameters:
        - {symbol: k, from: 2, to: N}    # k = 2, 3, ..., N
    Delta: 'k'
    spin: 0
    parity: unknown
    global: {SU(4)_R: 'Dynkin(0,k,0)'}
    multiplet: {name: '$\mathcal{O}_k$', component: primary, type: half-BPS}
    method: exact
    refs: [maldacena1997]
```

- **Parameters.** `family.parameters` lists one or more parameters, each with a `symbol` (a letter
  or command, optionally with a subscript: `k`, `\ell`, `n`) that is not a parameter of the entry,
  and a range: `from` and `to` (a number, or an expression in the entry's parameters and the
  family's earlier parameters, e.g. `to: N`, `to: N-1`, `to: '\ell'`), `step` (default 1), and
  `except` (values left out). Leave out `to` for an unbounded range; leave out both `from` and `to`
  for all integers. Examples: $k = 2, \dots, N$ is `{symbol: k, from: 2, to: N}`; even spins from
  2 are `{symbol: '\ell', from: 2, step: 2}`; $n = 0, 1, \dots$ is `{symbol: n, from: 0}`;
  momentum and winding $(n, w) \in \mathbb{Z}^2$ are `[{symbol: n}, {symbol: w}]`. The build
  writes the range for the page ("$k = 2, 3, \dots, N$", "$n, w \in \mathbb{Z}$").
- **Expressions.** `Delta`, `spin`, `weights`, `degeneracy` (here an expression is allowed:
  `'k-2'`) and the global labels may be expressions in the family's parameters and the entry's:
  `Delta: 'k(N-k)'`, `'\frac{n^2}{R^2} + \frac{w^2R^2}{4}'`, `spin: nw`, `global: {SU(4)_R:
  'Dynkin(0,k,0)', U(1)_r: 'k'}`, `{O(N): 'sym(\ell)'}`. Expressions are TeX arithmetic: numbers,
  the declared symbols, `+ - / ^`, implicit products (`2k`, `nw`), `\frac`, `\tfrac`, `\cdot`,
  `\sqrt`, parentheses, and `O(...)` for an order term. Any other symbol is an error (so a typo, or
  a symbol that should have been declared, is caught). Labels that can depend on a parameter:
  Dynkin labels (numeric $N$), `sym(k)`/`anti(k)`, and $U(1)$ / $\mathbb{Z}_n$ charges. `parity`
  is one value for the whole family (or `unknown`); `name` and `multiplet` are text, and every
  family parameter must appear somewhere in the row (name, data or labels).
- **What is a family.** Use one when every member's data is known as a function of the parameter,
  exactly (protected or BPS operators, conserved currents, free fields, chiral rings) or to the
  same order for all members (the planar higher-spin currents $J_s$, $\Delta = s + 1 + O(1/N)$).
  Operators whose dimensions are known only individually, numerically, stay individual rows, even
  when they lie on a known Regge trajectory: e.g. the double-twist operators $[\sigma\sigma]_{0,\ell}$
  of the 3d Ising model, whose $\Delta$ and OPE coefficients are known only member by member. They
  may say which double-twist family they belong to in `role` or `note`; they are not folded into a
  family row (see *Not adopted* below).
- **Members listed separately.** A row that records one member because it carries something of its
  own (it is the stress-tensor multiplet, it has its own references or a note, an OPE coefficient
  names it) stays an ordinary row and points to its family:

  ```yaml
  - name: '\mathcal{O}_{\mathbf{20}^\prime} = \mathrm{Tr}\,\phi^{\{I}\phi^{J\}}'
    member_of: half-BPS
    at: {k: 2}
    Delta: 2
    spin: 0
    parity: even
    global: {SU(4)_R: 'Dynkin(0,2,0)'}
    multiplet: {name: stress tensor, component: primary, type: half-BPS}
    method: exact
    note: 'Half-BPS superconformal primary of the stress-tensor multiplet; protected.'
  ```

  It keeps its full data (so nothing has to be reconstructed to read it), and the build checks that
  the data agree with the family's at `at`: the family must exist in the entry, `at` must give every
  family parameter a value in its range, and wherever both are definite, $\Delta$, spin, global
  labels, parity and multiplet `type` must be those of the family at those values. A row that is a
  member is never also a family. Several rows with the same `at` are determinations of one member.
  Do not add member rows that carry nothing of their own: the family row already says it.
- **What the build adds.** `family_view` on a family row (the range as TeX, the first member, the
  spin and $\Delta$ of that first member for sorting, the number of member rows), `member_view` on a
  member row (the family, the values as TeX), and, in a structured entry, `irrep` for a family row
  with its pattern labels (canonical form, e.g. `Dynkin(0,k,0)`, shown as $[0,k,0]$, never trivial,
  sorted just after its first member's irrep).
- **Families in unmigrated entries** are allowed: the range, expressions and members are checked
  the same way, and the free-text `rep` stays until the entry is migrated.

*Why one record, and members as pointers.* The data are the representation of each operator; a
family is the compact form of infinitely many such representations, and it is the form in which the
field states them ("the $\mathcal{B}_{[0,k,0]}$ multiplets have $\Delta = k$"). Writing out members
would be arbitrary (which $k$ to stop at) and would bury the one row that matters. A member written
separately is kept as a row, rather than as a sub-field of the family, so that it is an operator like
any other (its own name, method, references, notes, and a name that OPE coefficients can cite), and
the pointer makes it impossible to list it twice, as an unrelated operator and as part of the family.

*Not adopted (possible extension).* Families known only asymptotically, e.g. double-twist
$[\sigma\sigma]_{n,\ell}$ with $\Delta = 2\Delta_\sigma + 2n + \ell + \gamma_{n,\ell}$,
$\gamma_{n,\ell} \to 0$ as $\ell \to \infty$, could be a family row with an `asymptotic` formula and
numerically known members pointing to it with `member_of`. This is not used: their dimensions and OPE
coefficients are known member by member, so for now they remain individual operators.

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

### 2.7 Families

- A family is **one row**, never one row per member. It is grouped by its representation
  *pattern*: in a structured entry its global labels and parity, like any operator, so the
  half-BPS family of $\mathcal{N}=4$ SYM falls under "$SU(4)_R$ $[0,k,0]$" (as a heading if the
  table is grouped, in the *Representation* column if it is flat). A pattern is its own group,
  never merged with the irrep of a member: $[0,k,0]$ is not $[0,2,0]$.
- **Order.** A family is placed by its **first member** (each parameter at its `from`, or 0 when
  unbounded): its pattern group sorts just after the group of that member's irrep, and within a
  group the family sorts by that member's spin and $\Delta$. A family whose first member depends on
  an entry parameter sorts last.
- **The row** shows the name, $\Delta$, spin and labels as given (expressions), with "family,
  $k = 2, 3, \dots, N$" under the name.
- **Members listed separately** follow the family's row, indented, each led by its values
  ("$k = 2$:"), with their own determinations folded as usual. "1 member listed ▾" under the
  family's name folds them; they start shown. They are not operators of their own: they do not count
  in group sizes, do not form groups, and do not decide which levels are constant.

---

## 3. Pilot

Migrated: `ising-3d`, `o3-model-3d`, `gny-n1-3d`, `qed3-3d`, `potts-3-state`, `n4-sym`. Only
operator `rep` lines were replaced (by `parity`, `global`, `role`, `multiplet`) and `parity` and
`global_group` added to `symmetry`; every $\Delta$, spin, method, reference and note is unchanged.
Remarks that were part of `rep` ("order parameter", "thermal", "supercurrent") moved to `role`;
multiplet remarks ("superpartner of $\sigma$", "top of the $\sigma$ multiplet") became
`multiplet`.

Families (1.7, 2.7): `n4-sym` has the half-BPS family $\mathcal{O}_k$, $k = 2, \dots, N$, and its
$\mathbf{20}'$ row became the $k = 2$ member (unchanged otherwise); `n2-sqcd-4d` (Coulomb-branch
operators $\mathrm{Tr}\,\phi^k$, $k = 2, \dots, N$) and `compact-boson` (vertex operators $V_{n,w}$,
$(n, w) \in \mathbb{Z}^2$) already wrote their towers as one row, and only gained the `family`
block. The 3d Ising double-twist rows stay individual operators.
