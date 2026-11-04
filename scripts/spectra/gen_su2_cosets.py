#!/usr/bin/env python3
"""Spectra of SU(2)_3 x SU(2)_4 / SU(2)_7 (diagonal) and of the same coset with
SU(2)_4 extended to SU(3)_1 (the D_4 invariant on the level-4 label).

    python scripts/spectra/gen_su2_cosets.py
"""

from __future__ import annotations

from fractions import Fraction as F

from common import ROOT, block, frac_str, write_spectrum
from rcft import ade
from su2 import coset_branching

GEN = "scripts/spectra/gen_su2_cosets.py"
K1, K2 = 3, 4
K3 = K1 + K2
C = F(3 * K1, K1 + 2) + F(3 * K2, K2 + 2) - F(3 * K3, K3 + 2)
N = 16


def build(M2, theory, **extra):
    b = coset_branching(K1, K2, N)
    reps, rep = [], {}
    for l1 in range(K1 + 1):
        for l2 in range(K2 + 1):
            for l3 in range(K3 + 1):
                if (l1 + l2 + l3) % 2:
                    continue
                t, twin = (l1, l2, l3), (K1 - l1, K2 - l2, K3 - l3)
                rep[t] = rep.get(twin, t)
                if rep[t] == t:
                    reps.append(t)
    missing = [t for t in reps if t not in b]
    assert not missing, f"branching functions not reached: {missing}"
    Z = {}
    for l1 in range(K1 + 1):
        for l3 in range(K3 + 1):
            for (a, a2), x in M2.items():
                t, u = (l1, a, l3), (l1, a2, l3)
                if t in rep and u in rep:
                    key = (rep[t], rep[u])
                    Z[key] = Z.get(key, 0) + F(x, 2)
    assert all(v.denominator == 1 for v in Z.values())
    used = sorted({i for i, _ in Z} | {j for _, j in Z})
    idx = {t: n for n, t in enumerate(used)}
    blocks = [block(b[t], C, f"b^{{({t[0]},{t[1]};{t[2]})}}") for t in used]
    Zl = [[idx[i], idx[j], frac_str(v)] for (i, j), v in sorted(Z.items(), key=lambda kv: (idx[kv[0][0]], idx[kv[0][1]])) if v]
    spec = {"theory": theory, "c": str(C), **extra, "generator": GEN, "blocks": blocks, "Z": Zl}
    p = write_spectrum(spec)
    print("wrote", p.relative_to(ROOT), f"({len(used)} branching functions)")


CHAR = ("Branching functions $\\chi^{(3)}_{l_1}(\\tau,z)\\,\\chi^{(4)}_{l_2}(\\tau,z) = \\sum_{l_3} "
        "b^{(l_1,l_2;l_3)}(\\tau)\\,\\chi^{(7)}_{l_3}(\\tau,z)$ of affine $SU(2)$ characters (Weyl-Kac), "
        "$l_1+l_2+l_3$ even, $(l_1,l_2;l_3)\\sim(3-l_1,4-l_2;7-l_3)$.")


def main():
    build(ade("A", K2), "su2-3-4-7-coset",
          chiral_algebra="SU(2)_3\\times SU(2)_4/SU(2)_7", irreducible=True,
          Z_tex="Z = \\sum_{(l_1,l_2;l_3)/\\sim} |b^{(l_1,l_2;l_3)}|^2",
          character_tex=CHAR,
          description="Diagonal coset $SU(2)_3\\times SU(2)_4/SU(2)_7$ (Goddard-Kent-Olive).")
    build(ade("D", K2), "su2-3-su3-1-su2-7",
          chiral_algebra="SU(2)_3\\times SU(3)_1/SU(2)_7", irreducible=True,
          Z_tex=("Z = \\sum_{l_1, l_3}\\left(\\tfrac12|b^{(l_1,0;l_3)} + b^{(l_1,4;l_3)}|^2 + "
                 "|b^{(l_1,2;l_3)}|^2\\right)\\Big/\\!\\sim"),
          character_tex=CHAR + " $SU(3)_1 \\supset SU(2)_4$ has characters $\\chi_0+\\chi_4$ and $\\chi_2$ (twice).",
          description=("The same coset with the $D_4$ invariant on the level-4 label, i.e. with $SU(2)_4$ "
                       "extended to $SU(3)_1$ (conformal embedding)."))


if __name__ == "__main__":
    main()
