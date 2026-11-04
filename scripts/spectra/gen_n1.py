#!/usr/bin/env python3
"""Spectra of the bosonized N=1 minimal models N_m^{(G,G')(+-)}: the coset
SU(2)_{m-2} x SU(2)_2 / SU(2)_m with ADE invariants on the first and last labels.

Branching functions come from the N=1 character formulas (NS sector split into
integer and half-integer levels, Ramond sector as is); `--verify` compares them
with a direct decomposition of graded affine SU(2) characters.

    python scripts/spectra/gen_n1.py [--verify]
"""

from __future__ import annotations

import sys
from fractions import Fraction as F

from common import Series, block, frac_str, inv_phi, qpoch, write_spectrum
from rcft import ade

GEN = "scripts/spectra/gen_n1.py"
TOP = 7


def n1_c(m):
    return F(3, 2) - F(12, m * (m + 2))


def n1_char(m, r, s, top_weight) -> Series:
    """Full NS (r-s even) or one-copy Ramond (r-s odd) character of SM(m, m+2)."""
    p, pp = m, m + 2
    c = n1_c(m)
    R = (r - s) % 2
    top = F(top_weight) - c / 24
    num = {}
    shift = F(1, 16) if R else F(0)
    k = 0
    while True:
        added = False
        for kk in ({k, -k} if k else {0}):
            for x, sign in ((2 * p * pp * kk + pp * r - p * s, 1), (2 * p * pp * kk + pp * r + p * s, -1)):
                e = F(x * x - (pp - p) ** 2, 8 * p * pp) + shift - c / 24
                if e <= top:
                    num[e] = num.get(e, 0) + sign
                    added = True
        if not added and k > 2:
            break
        k += 1
    T = top + c / 24 + 1
    fermions = qpoch(1, 1, T, sign=1) if R else qpoch(F(1, 2), 1, T, sign=1)
    return (Series(num, top) * fermions * inv_phi(T)).truncate(top)


def h_su2(k, l):
    return F(l * (l + 2), 4 * (k + 2))


def coset_fields(m):
    """Representatives (l, e, l') of SU(2)_{m-2} x SU(2)_2 / SU(2)_m fields and a map label -> rep."""
    rep = {}
    reps = []
    for l in range(m - 1):
        for e in range(3):
            for lp in range(m + 1):
                if (l + e + lp) % 2:
                    continue
                t = (l, e, lp)
                twin = (m - 2 - l, 2 - e, m - lp)
                if twin in rep:
                    rep[t] = rep[twin]
                else:
                    rep[t] = t
                    reps.append(t)
    return reps, rep


def branching(m, top_weight):
    """{(l, e, l'): Series} for representatives, from the N=1 characters."""
    c = n1_c(m)
    reps, _ = coset_fields(m)
    out = {}
    for (l, e, lp) in reps:
        r, s = l + 1, lp + 1
        hb = h_su2(m - 2, l) + F(e * (e + 2), 16) - h_su2(m, lp)
        hN = F(((m + 2) * r - m * s) ** 2 - 4, 8 * m * (m + 2)) + (F(1, 16) if e == 1 else 0)
        tw = max(F(top_weight), hN + 3)
        ch = n1_char(m, r, s, tw)
        if e == 1:
            out[(l, e, lp)] = ch
        else:
            keep = {x: a for x, a in ch.c.items() if (x + c / 24 - hb).denominator == 1}
            out[(l, e, lp)] = Series(keep, ch.top)
    return out


def invariant(m, G, Gp, sign):
    """Integer matrix on resolved fields and the list of resolved fields
    [(label tuple, Series, latex)] for N_m^{(G,G')sign}."""
    c = n1_c(m)
    reps, rep = coset_fields(m)
    b = branching(m, TOP)
    MG, MGp = ade(G, m - 2), ade(Gp, m)
    N: dict = {}
    for (l, lt), x in MG.items():
        for (lp, ltp), y in MGp.items():
            for e in range(3):
                a, bb = (l, e, lp), (lt, e, ltp)
                if a not in rep or bb not in rep:
                    continue
                key = (rep[a], rep[bb])
                N[key] = N.get(key, 0) + F(x * y, 2)
    fixed = (m // 2 - 1, 1, m // 2) if m % 2 == 0 else None
    fields = {}
    for t in reps:
        fields[t] = b[t]
    if fixed is not None and any(fixed in k for k in N):
        bf = b[fixed]
        one = Series.mono(0, 1, bf.top)        # the constant 1 (h = c/24)
        f1 = Series({e: (bf.coeff(e) + one.coeff(e)) / 2 for e in set(bf.c) | set(one.c)}, bf.top)
        f2 = Series({e: (bf.coeff(e) - one.coeff(e)) / 2 for e in set(bf.c) | set(one.c)}, bf.top)
        del fields[fixed]
        fA, fB = fixed + ("a",), fixed + ("b",)
        fields[fA], fields[fB] = f1, f2
        if sign is None:
            raise ValueError(f"m={m} ({G},{Gp}) has a Ramond fixed point; give a sign")
        Nf = dict()
        for (i, j), x in N.items():
            I = [fA, fB] if i == fixed else [i]
            Jx = [fA, fB] if j == fixed else [j]
            for ii in I:
                for jj in Jx:
                    Nf[(ii, jj)] = Nf.get((ii, jj), 0) + x
        corr = F(MG.get((m // 2 - 1, m // 2 - 1), 0) * MGp.get((m // 2, m // 2), 0), 2)
        s = 1 if sign == "+" else -1
        for (ii, jj), w in (((fA, fA), s), ((fB, fB), s), ((fA, fB), -s), ((fB, fA), -s)):
            Nf[(ii, jj)] = Nf.get((ii, jj), 0) + w * corr
        N = Nf
    else:
        sign = None
    N = {k: v for k, v in N.items() if v}
    bad = [v for v in N.values() if v.denominator != 1 or v < 0]
    if bad:
        raise ValueError(f"m={m} ({G},{Gp}){sign}: non-integer multiplicities {bad[:3]}")
    return fields, N, sign


def label(t, m):
    l, e, lp = t[:3]
    sup = {0: "", 1: "", 2: ""}[e]
    lab = f"b^{{({l},{e},{lp})}}"
    if len(t) == 4:
        lab = f"b^{{({l},{e},{lp})}}_{{{'+' if t[3] == 'a' else '-'}}}"
    return lab


def make(m, G, Gp, sign, theory, member=None, write=True):
    c = n1_c(m)
    fields, N, sign = invariant(m, G, Gp, sign)
    used = sorted({i for i, _ in N} | {j for _, j in N}, key=lambda t: (t[:3], t[3:]))
    idx = {t: n for n, t in enumerate(used)}
    blocks = []
    for t in used:
        s = fields[t]
        s = Series({e: int(a) for e, a in s.c.items() if a}, s.top)
        blocks.append(block(s, c, label(t, m)))
    Z = [[idx[i], idx[j], frac_str(x)] for (i, j), x in sorted(N.items(), key=lambda kv: (idx[kv[0][0]], idx[kv[0][1]]))]
    gname = {"A": "A", "D": "D", "E6": "E_6", "E7": "E_7", "E8": "E_8"}
    inv = f"({gname[G]},{gname[Gp]})"
    pm = "" if sign is None else ("+" if sign == "+" else "-")
    desc = (f"Coset $SU(2)_{{{m - 2}}}\\times SU(2)_2/SU(2)_{{{m}}}$ with the {inv} invariant "
            f"({gname[G]} on the level-{m - 2} label, {gname[Gp]} on the level-{m} label). "
            "Blocks are the coset branching functions $b^{(l,\\epsilon,l')}$ with "
            "$(l,\\epsilon,l')\\sim(" + f"{m - 2}-l,2-\\epsilon,{m}-l')$.")
    if sign is not None:
        desc += (" The Ramond ground state $(" + f"{m // 2 - 1},1,{m // 2}" + ")$ is a fixed point of the "
                 "identification; its two resolved components $b_\\pm$ differ by the constant 1, and the sign "
                 + ("keeps $(c/24, c/24)$ as a scalar." if sign == "+" else "pairs $b_+$ with $b_-$, so the ground state appears at $(c/24, c/24+1)$."))
    spec = {"theory": theory}
    if member is not None:
        spec["member"] = member
    spec.update({
        "c": str(c),
        "chiral_algebra": f"\\left(SU(2)_{{{m - 2}}}\\times SU(2)_2/SU(2)_{{{m}}}\\right)",
        "irreducible": True,
        "Z_tex": ("Z = \\tfrac12\\sum N^{" + gname[G] + "}_{l\\tilde l}\\,N^{" + gname[Gp] + "}_{l'\\tilde l'}\\,"
                  "b^{(l,\\epsilon,l')}\\overline{b^{(\\tilde l,\\epsilon,\\tilde l')}}"
                  + ("" if sign is None else (" + \\tfrac12" if sign == "+" else " - \\tfrac12"))),
        "character_tex": ("The $\\mathcal{N}=1$ characters $\\chi^{NS}_{r,s} = q^{-c/24}\\prod_{n\\ge1}\\frac{1+q^{n-1/2}}{1-q^n}"
                          "\\sum_{k}\\left(q^{a_k}-q^{b_k}\\right)$ and $\\chi^{R}_{r,s} = q^{1/16-c/24}\\prod_{n\\ge1}\\frac{1+q^{n}}{1-q^n}"
                          "\\sum_{k}\\left(q^{a_k}-q^{b_k}\\right)$, "
                          f"$a_k = \\frac{{(2pp'k+p'r-ps)^2-4}}{{8pp'}}$, $b_k = \\frac{{(2pp'k+p'r+ps)^2-4}}{{8pp'}}$, $(p,p') = ({m},{m + 2})$. "
                          "With $r = l+1$, $s = l'+1$: $b^{(l,0,l')}$ and $b^{(l,2,l')}$ are the parts of $\\chi^{NS}_{r,s}$ at integer and "
                          "half-integer level (whichever matches the coset weight), and $b^{(l,1,l')} = \\chi^R_{r,s}$."),
        "description": desc,
        "generator": GEN,
        "blocks": blocks,
        "Z": Z,
    })
    if write:
        p = write_spectrum(spec)
        print("wrote", p.relative_to(p.parents[2]))
    return spec


def verify(ms=(5, 6, 8)):
    """Compare formula branching functions with graded SU(2) decomposition."""
    import su2
    for m in ms:
        c = n1_c(m)
        b = branching(m, 6)
        bb = su2.coset_branching(m - 2, 2, 12)
        reps, _ = coset_fields(m)
        worst = 0
        for t in reps:
            x, y = b[t], bb.get(t)
            if y is None:
                print(f"  m={m} {t}: missing in decomposition (high weight?)")
                continue
            top = min(x.top, y.top)
            d = (x - y).truncate(top)
            if d.c:
                print(f"  m={m} {t}: MISMATCH {d}")
                worst += 1
        print(f"m={m}: {len(reps)} fields compared, {worst} mismatches")


def main():
    if "--verify" in sys.argv:
        verify()
        return
    for m in range(5, 21, 2):
        make(m, "A", "A", None, "n1-minimal-aa-odd", {"at": m})
    for m in range(6, 18, 2):
        for sgn in "+-":
            make(m, "A", "A", sgn, "n1-minimal-aa-even", {"at": m, "variant": sgn})
    for m in range(6, 14, 2):
        for G, Gp in (("A", "D"), ("D", "A")):
            for sgn in "+-":
                make(m, G, Gp, sgn, "n1-minimal-ad-da", {"at": m, "variant": f"({G},{Gp}){sgn}"})
    make(12, "E6", "A", None, "n1-12-e6a")
    make(12, "E6", "D", None, "n1-12-e6d")
    make(16, "A", "E7", "+", "n1-16-ae7-plus")
    make(16, "A", "E7", "-", "n1-16-ae7-minus")
    make(18, "E7", "A", "+", "n1-18-e7a-plus")
    make(18, "E7", "A", "-", "n1-18-e7a-minus")
    make(28, "A", "E8", None, "n1-28-ae8")
    make(30, "E8", "A", None, "n1-30-e8a")


if __name__ == "__main__":
    main()
