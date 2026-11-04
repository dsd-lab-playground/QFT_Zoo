#!/usr/bin/env python3
"""Spectra of the unitary Virasoro minimal models (A, D, E invariants) and of
Ising x M_m (A, D, E types, the diagonal Z_2 orbifolds, and X_12).

    python scripts/spectra/gen_minimal.py
"""

from __future__ import annotations

from fractions import Fraction as F

from common import write_spectrum
from rcft import (Field, ade, minimal_c, minimal_fields, minimal_invariant,
                  simple_current_invariant, spectrum_from)

GEN = "scripts/spectra/gen_minimal.py"
TOP = 9                         # characters kept up to this conformal weight

ISING_LABELS = {(1, 1): "1", (1, 2): "\\sigma", (1, 3): "\\varepsilon"}
EXC = {"E6": 10, "E7": 16, "E8": 28}


def ising_fields(top):
    f = minimal_fields(3, top)
    return [Field(ISING_LABELS[rs], f[rs].h, f[rs].char) for rs in ((1, 1), (1, 2), (1, 3))]


def write(theory, c, blocks, Z, member=None, **extra):
    spec = {"theory": theory}
    if member is not None:
        spec["member"] = member
    spec.update({"c": str(c), **extra, "generator": GEN, "blocks": blocks, "Z": Z})
    p = write_spectrum(spec)
    print("wrote", p.relative_to(p.parents[2]))


def invariant_name(m, gr, gs):
    names = {"A": "A", "D": "D", "E6": "E_6", "E7": "E_7", "E8": "E_8"}
    def full(g, k):
        if g == "A":
            return f"A_{{{k + 1}}}"
        if g == "D":
            return f"D_{{{k // 2 + 2}}}"
        return names[g]
    return f"({full(gr, m - 2)},\\,{full(gs, m - 1)})"


def minimal(m, gr, gs, theory, member=None, top=TOP):
    reps, M = minimal_invariant(m, gr, gs, top)
    c = minimal_c(m, m + 1)
    blocks, Z = spectrum_from(reps, M, c, top)
    inv = invariant_name(m, gr, gs)
    if gr == gs == "A":
        ztex = "Z = \\sum_{(r,s)/\\sim} |\\chi_{r,s}|^2"
    else:
        ztex = ("Z = \\tfrac12 \\sum_{r,r',s,s'} N^{(1)}_{r r'}\\, N^{(2)}_{s s'}\\,"
                " \\chi_{r,s}\\overline{\\chi_{r',s'}}")
    write(theory, c, blocks, Z, member,
          chiral_algebra=f"\\mathrm{{Vir}}_{{c={c}}}",
          irreducible=True, Z_tex=ztex,
          character_tex=rc_tex(m),
          description=(f"$\\mathcal{{M}}({m},{m + 1})$ with the ${inv}$ modular invariant of "
                       "Cappelli-Itzykson-Zuber"
                       + ("" if gr == gs == "A" else
                          " ($N^{(1)}, N^{(2)}$ are the matrices of the two labels, $r$ at level "
                          f"{m - 2} and $s$ at level {m - 1} of $SU(2)$)")
                       + "; blocks are Virasoro characters and $Z$ gives their multiplicities."))


def rc_tex(m):
    return ("Rocha-Caridi characters "
            f"$\\chi_{{r,s}} = \\frac{{q^{{-c/24}}}}{{\\prod_{{n\\ge1}}(1-q^n)}}\\sum_{{k\\in\\mathbb{{Z}}}}"
            f"\\left(q^{{h_{{r+{2 * m}k,\\,s}}}}-q^{{h_{{-r+{2 * m}k,\\,s}}}}\\right)$, "
            f"$h_{{r,s}} = \\frac{{({m + 1}r-{m}s)^2-1}}{{{4 * m * (m + 1)}}}$, $(r,s)\\sim({m}-r,{m + 1}-s)$.")


# ------------------------------------------------------------- Ising x M_m

def product_theory(fieldsA, MA, fieldsB, MB):
    nB = len(fieldsB)
    fields = [Field(f"{a.label}\\otimes {b.label}", a.h + b.h, a.char * b.char) for a in fieldsA for b in fieldsB]
    M = {}
    for (i, j), x in MA.items():
        for (k, l), y in MB.items():
            key = (i * nB + k, j * nB + l)
            M[key] = M.get(key, 0) + x * y
    return fields, M


def ising_times(m, gr, gs, top):
    """Fields of Ising x M_m (Virasoro^2 characters) and the product matrix."""
    I = ising_fields(top)
    MI = {(0, 0): 1, (1, 1): 1, (2, 2): 1}
    reps, M = minimal_invariant(m, gr, gs, top)
    return product_theory(I, MI, reps, M), reps


def ising_x_minimal(m, kind, theory, member=None, top=TOP):
    c = F(1, 2) + minimal_c(m, m + 1)
    if kind == "Z2":
        (fields, _), reps = ising_times(m, "A", "A", top)
        # J = epsilon (x) phi_{m-1,1}: (a, (r,s)) -> (eps a, (m-r, s))
        index = {}
        for n, f in enumerate(reps):
            index[f.label] = n
        allf = minimal_fields(m, top)
        rep_of = {}
        for (r, s), f in allf.items():
            rep_of[(r, s)] = index[f.label]
        rs_of = {}
        for (r, s), n in rep_of.items():
            rs_of.setdefault(n, (r, s))
        nB = len(reps)
        eps = {0: 2, 1: 1, 2: 0}
        J = {}
        for a in range(3):
            for b in range(nB):
                r, s = rs_of[b]
                J[a * nB + b] = eps[a] * nB + rep_of[(m - r, s)]
        M = simple_current_invariant(fields, J, 2)
        hJ = F(1, 2) + F((m - 1) * (m - 2), 4)
        how = ("an extension by" if hJ.denominator == 1 else "the automorphism invariant of")
        desc = (f"Simple-current invariant of $J = \\varepsilon\\otimes\\phi_{{{m - 1},1}}$ "
                f"($h_J = {hJ}$), i.e. {how} $J$ (Kreuzer-Schellekens), on the Virasoro$^2$ characters "
                f"of Ising $\\times\\ \\mathcal{{M}}_{{{m}}}$. This is the orbifold of Ising $\\times\\ \\mathcal{{M}}_{{{m}}}$ "
                "by the diagonal spin flip.")
        ztex = "Z = \\sum M^{[J]}_{ab}\\, \\chi_a \\overline{\\chi_b}"
    else:
        gr, gs = {"A": ("A", "A")}.get(kind, None) or kind
        (fields, M), _ = ising_times(m, gr, gs, top)
        inv = invariant_name(m, gr, gs)
        desc = (f"Diagonal Ising times $\\mathcal{{M}}({m},{m + 1})$ with the ${inv}$ invariant; blocks are "
                "products of Virasoro characters.")
        ztex = f"Z = Z_{{\\rm Ising}}\\; Z^{{{inv}}}_{{\\mathcal M_{{{m}}}}}"
    blocks, Z = spectrum_from(fields, M, c, top)
    write(theory, c, blocks, Z, member,
          chiral_algebra=f"\\mathrm{{Vir}}_{{1/2}}\\otimes\\mathrm{{Vir}}_{{{minimal_c(m, m + 1)}}}",
          irreducible=True, Z_tex=ztex,
          character_tex="Products $\\chi^{\\rm Ising}_a\\,\\chi_{r,s}$ of Rocha-Caridi characters.",
          description=desc)


# ------------------------------------------------------------- E6 products: Z2 and X_12

def e6_extended(m, top):
    """E6-extended M_m (m = 11: E6 on s; m = 12: E6 on r). Returns fields keyed by
    (block, other label) for canonical reps and a dict giving every (B, x) its index."""
    allf = minimal_fields(m, top)
    blocks_l = {"1": (1, 7), "v": (5, 11), "s": (4, 8)}     # 1-indexed labels of SU(2)_10
    vmap = {"1": "v", "v": "1", "s": "s"}
    other = m if m == 11 else m + 1                          # range of the A label: 1..other-1
    fields, idx = [], {}
    for B, labs in blocks_l.items():
        for x in range(1, other):
            if (B, x) in idx:
                continue
            if m == 11:      # E6 on s, A on r: (r, B) ~ (11 - r, vB)
                pairs = [(x, s) for s in labs]
                twin = (vmap[B], m - x)
                name = f"\\chi_{{{x},\\{{{labs[0]},{labs[1]}\\}}}}"
            else:            # E6 on r, A on s: (B, s) ~ (vB, 13 - s)
                pairs = [(r, x) for r in labs]
                twin = (vmap[B], m + 1 - x)
                name = f"\\chi_{{\\{{{labs[0]},{labs[1]}\\}},{x}}}"
            ch = allf[pairs[0]].char + allf[pairs[1]].char
            h = min(allf[p].h for p in pairs)
            idx[(B, x)] = idx[twin] = len(fields)
            fields.append(Field(name, h, ch))
    return fields, idx


def e6_products(m, theory_plain_z2, theory_x12=None, top=TOP):
    c = F(1, 2) + minimal_c(m, m + 1)
    W, idx = e6_extended(m, top)
    I = ising_fields(top)
    nW = len(W)
    fields = [Field(f"{a.label}\\otimes {w.label}", a.h + w.h, a.char * w.char) for a in I for w in W]
    vmap = {"1": "v", "v": "1", "s": "s"}
    # J = eps (x) (v-block, trivial other label)
    J = {}
    for (B, x), n in idx.items():
        for a, ea in ((0, 2), (1, 1), (2, 0)):
            J[a * nW + n] = ea * nW + idx[(vmap[B], x)]
    M = simple_current_invariant(fields, J, 2)
    hJ = fields[J[0]].h
    side = "s" if m == 11 else "r"
    blocks, Z = spectrum_from(fields, M, c, top)
    write(theory_plain_z2, c, blocks, Z,
          chiral_algebra=(f"\\mathrm{{Vir}}_{{1/2}}\\otimes\\mathcal{{W}}"),
          irreducible=True, Z_tex="Z = \\sum M^{[J]}_{ab}\\, \\chi_a \\overline{\\chi_b}",
          character_tex=(f"$\\mathcal{{W}}$ is $\\mathcal{{M}}({m},{m + 1})$ extended by its $E_6$ current "
                         f"(on the ${side}$ label, blocks $\\{{1,7\\}},\\{{5,11\\}},\\{{4,8\\}}$); its characters are sums of two "
                         "Rocha-Caridi characters, and the blocks are their products with Ising characters."),
          description=(f"Extension of Ising $\\times\\ \\mathcal{{M}}_{{{m}}}^{{E_6}}$ by the simple current "
                       f"$J = \\varepsilon\\otimes\\phi$ of weight {hJ} (Kreuzer-Schellekens), i.e. the orbifold "
                       "by the diagonal $\\mathbb{Z}_2$."))
    if theory_x12 is None:
        return
    # X_12: Z = sum_I chi_I conj(chi_Phi(I)); W-modules are (B, s odd) = Ising^(9) x SO(3)_11^rev
    PHI = {("1", "1"): ("1", "1"), ("e", "1"): ("1", "v"), ("1", "v"): ("e", "1"), ("e", "v"): ("e", "v"),
           ("s", "1"): ("e", "s"), ("1", "s"): ("s", "v"), ("e", "s"): ("s", "1"), ("s", "v"): ("1", "s"),
           ("s", "s"): ("s", "s")}
    ia = {"1": 0, "s": 1, "e": 2}
    M = {}
    for (a, B), (a2, B2) in PHI.items():
        for s in range(1, m + 1, 2):
            i = ia[a] * nW + idx[(B, s)]
            j = ia[a2] * nW + idx[(B2, s)]
            M[(i, j)] = M.get((i, j), 0) + 1
    blocks, Z = spectrum_from(fields, M, c, top)
    write(theory_x12, c, blocks, Z,
          chiral_algebra="\\mathrm{Vir}_{1/2}\\otimes\\mathcal{W}",
          irreducible=True, Z_tex="Z = \\sum_I \\chi_I\\, \\overline{\\chi_{\\Phi(I)}}",
          character_tex=("$\\mathcal{W}$ is $\\mathcal{M}(12,13)$ extended by $\\phi_{7,1}$ ($h = 10$); "
                         "$\\mathcal{W}$-characters are $\\chi_{\\{r,r'\\},s} = \\chi_{r,s}+\\chi_{r',s}$ for the $E_6$ blocks "
                         "$\\{1,7\\}, \\{5,11\\}, \\{4,8\\}$, and the blocks are their products with Ising characters."),
          description=("Permutation invariant of Ising $\\times\\ \\mathcal{M}_{12}^{(E_6,A)}$. The $\\mathcal{W}$-modules "
                       "are labelled by an Ising-type triple $\\{1,\\psi',\\sigma'\\}$ (the $E_6$ blocks) and odd $s$; "
                       "$\\Phi$ exchanges $\\psi\\leftrightarrow\\psi'$ and sends $\\sigma\\mapsto\\psi\\sigma'$, "
                       "$\\sigma'\\mapsto\\sigma\\psi'$, fixing the $s$ label."))


def main():
    # individual minimal-model entries
    minimal(3, "A", "A", "ising-2d")
    minimal(4, "A", "A", "tricritical-ising")
    minimal(5, "A", "D", "potts-3-state")
    for m in range(3, 11):
        minimal(m, "A", "A", "virasoro-minimal-a", {"at": m})
    for m in range(5, 13):
        minimal(m, "D", "A", "virasoro-minimal-d", {"at": m}) if m % 2 == 0 else \
            minimal(m, "A", "D", "virasoro-minimal-d", {"at": m})
    for m, g in ((11, ("A", "E6")), (12, ("E6", "A")), (17, ("A", "E7")), (18, ("E7", "A")),
                 (29, ("A", "E8")), (30, ("E8", "A"))):
        minimal(m, *g, "virasoro-minimal-e", {"at": m}, top=8 if m < 20 else 6)

    for m in range(4, 12):
        ising_x_minimal(m, "A", "ising-x-minimal-a", {"at": m}, top=8)
        ising_x_minimal(m, "Z2", "ising-x-minimal-z2", {"at": m}, top=8)
    for m in range(5, 13):
        ising_x_minimal(m, ("D", "A") if m % 2 == 0 else ("A", "D"), "ising-x-minimal-d", {"at": m}, top=8)
    for m, g, tid in ((11, ("A", "E6"), "ising-x-m11-ae6"), (12, ("E6", "A"), "ising-x-m12-e6a"),
                      (17, ("A", "E7"), "ising-x-m17-ae7"), (18, ("E7", "A"), "ising-x-m18-e7a"),
                      (29, ("A", "E8"), "ising-x-m29-ae8"), (30, ("E8", "A"), "ising-x-m30-e8a")):
        ising_x_minimal(m, g, tid, top=7 if m < 20 else 5)
    e6_products(11, "ising-x-m11-ae6-z2", top=7)
    e6_products(12, "ising-x-m12-e6a-z2", "x12", top=7)


if __name__ == "__main__":
    main()
