#!/usr/bin/env python3
"""Spectra of c = 1 theories: the compact boson at R^2 = 2M (a U(1)_{2M} lattice
theory), the S^1/Z_2 orbifold, and the isolated orbifolds SU(2)_1/T, O, I.

Conventions: X ~ X + 2 pi R, Delta = n^2/R^2 + w^2 R^2/4, self-dual R = sqrt 2.

    python scripts/spectra/gen_c1.py
"""

from __future__ import annotations

import json
from fractions import Fraction as F

from common import ROOT, Series, block, frac_str, inv_phi, phi, qpoch, write_spectrum
from gen_tim2 import same_z

GEN = "scripts/spectra/gen_c1.py"
C = F(1)
TOP = 9


def K(M, a, top=TOP):
    """U(1)_{2M} character K_a = eta^{-1} sum_j q^{(a + 2Mj)^2/(4M)}."""
    T = F(top) - C / 24
    num = {}
    j = 0
    while True:
        hit = False
        for jj in ((j, -j) if j else (0,)):
            e = F((a + 2 * M * jj) ** 2, 4 * M) - F(1, 24)
            if e <= T + 1:
                num[e] = num.get(e, 0) + 1
                hit = True
        if not hit and j > 1:
            break
        j += 1
    return (Series(num, T + 1) * inv_phi(T + 2)).truncate(T)


def twisted_blocks(top=TOP):
    T = F(top) - C / 24
    y2 = qpoch(1, 1, T + 1, sign=1, inverse=True).shift(-F(1, 24)).truncate(T)       # q^{-1/24}/prod(1+q^n)
    y4 = qpoch(F(1, 2), 1, T + 1, sign=-1, inverse=True).shift(F(1, 48)).truncate(T)  # q^{1/48}/prod(1-q^{n-1/2})
    y3 = qpoch(F(1, 2), 1, T + 1, sign=1, inverse=True).shift(F(1, 48)).truncate(T)   # q^{1/48}/prod(1+q^{n-1/2})
    return y2, y3, y4


class Z:
    def __init__(self):
        self.blocks, self.Z = {}, {}

    def b(self, key, label, s):
        self.blocks.setdefault(key, (label, s))
        return key

    def add(self, coef, i, j=None):
        j = i if j is None else j
        self.Z[(i, j)] = self.Z.get((i, j), 0) + F(coef)

    def circle(self, M, coef=1):
        for a in range(-M + 1, M + 1):
            k = self.b(f"K{M},{a}", f"K^{{({2 * M})}}_{{{a}}}", K(M, a))
            self.add(coef, k)

    def orbifold(self, M, coef=1):
        self.circle(M, F(coef, 2))
        y2, y3, y4 = twisted_blocks()
        self.add(F(coef, 2), self.b("y2", "q^{-1/24}\\prod_n(1+q^n)^{-1}", y2))
        self.add(coef, self.b("y3", "q^{1/48}\\prod_n(1+q^{n-1/2})^{-1}", y3))
        self.add(coef, self.b("y4", "q^{1/48}\\prod_n(1-q^{n-1/2})^{-1}", y4))

    def spec(self, theory, member=None, **extra):
        Zd = {k: v for k, v in self.Z.items() if v}
        keys = sorted({i for i, _ in Zd}, key=list(self.blocks).index)
        idx = {k: n for n, k in enumerate(keys)}
        blocks = [block(self.blocks[k][1], C, self.blocks[k][0]) for k in keys]
        Zl = [[idx[i], idx[j], frac_str(v)] for (i, j), v in sorted(Zd.items(), key=lambda kv: idx[kv[0][0]])]
        s = {"theory": theory}
        if member:
            s["member"] = member
        s.update({"c": "1", **extra, "generator": GEN, "blocks": blocks, "Z": Zl})
        return s


K_TEX = ("$K^{(2M)}_a = \\eta(\\tau)^{-1}\\sum_{j\\in\\mathbb{Z}} q^{(a+2Mj)^2/4M}$, the characters of the "
         "$U(1)_{2M}$ lattice algebra; at $R^2 = 2M$ the momentum and winding $(n, w)$ have "
         "$h = \\frac{(n+wM)^2}{4M}$, $\\bar h = \\frac{(n-wM)^2}{4M}$.")
ORB_TEX = (K_TEX + " Twisted sectors: $|\\eta/\\theta_4| = |q^{1/48}\\prod(1-q^{n-1/2})^{-1}|^2$, "
           "$|\\eta/\\theta_3| = |q^{1/48}\\prod(1+q^{n-1/2})^{-1}|^2$, and the untwisted projection uses "
           "$|\\eta/\\theta_2| = \\tfrac12|q^{-1/24}\\prod(1+q^n)^{-1}|^2$.")
ZORB = "Z_{\\rm orb}(R) = \\tfrac12 Z_{\\rm circ}(R) + \\left|\\tfrac{\\eta}{\\theta_2}\\right| + \\left|\\tfrac{\\eta}{\\theta_3}\\right| + \\left|\\tfrac{\\eta}{\\theta_4}\\right|"


def circle_spec(M, member):
    z = Z()
    z.circle(M)
    return z.spec("compact-boson", member, chiral_algebra=f"U(1)_{{{2 * M}}}", irreducible=True,
                  Z_tex=f"Z_{{\\rm circ}}(R) = \\sum_{{a=-{M - 1}}}^{{{M}}} |K^{{({2 * M})}}_a|^2,\\quad R^2 = {2 * M}",
                  character_tex=K_TEX,
                  description=(f"Compact boson at $R^2 = {2 * M}$: the even lattice $\\sqrt{{{2 * M}}}\\,\\mathbb{{Z}}$ "
                               "extends $U(1)$, and $Z$ is diagonal in its characters."))


def orbifold_spec(M, member):
    z = Z()
    z.orbifold(M)
    return z.spec("compact-boson-orbifold", member, irreducible=False, Z_tex=ZORB + f",\\quad R^2 = {2 * M}",
                  character_tex=ORB_TEX,
                  description=(f"$S^1/\\mathbb{{Z}}_2$ orbifold ($X\\to-X$) of the boson at $R^2 = {2 * M}$; "
                               "the two fixed points give twisted ground states at $h = \\bar h = 1/16$."))


def polyhedral(name, terms, theory, order, gap_note):
    """terms: list of (coef, kind, M) with kind 'circ' or 'orb'."""
    z = Z()
    pieces = []
    for coef, kind, M in terms:
        (z.circle if kind == "circ" else z.orbifold)(M, coef)
        R = {1: "\\sqrt2", 4: "2\\sqrt2", 9: "3\\sqrt2", 16: "4\\sqrt2", 25: "5\\sqrt2"}[M]
        cf = F(coef)
        sgn = "-" if cf < 0 else "+"
        mag = abs(cf)
        mags = "" if mag == 1 else (f"\\tfrac{{{mag.numerator}}}{{{mag.denominator}}}" if mag.denominator != 1 else str(mag))
        pieces.append(f"{sgn} {mags}Z_{{\\rm {kind}}}({R})")
    tex = " ".join(pieces).lstrip("+ ").strip()
    return z.spec(theory, irreducible=False,
                  Z_tex=f"Z_{{{name}}} = {tex}",
                  character_tex=ORB_TEX,
                  description=(f"Orbifold of $SU(2)_1$ (the self-dual boson) by the {gap_note} group $\\subset SO(3)$ "
                               f"of order {order}, acting through the diagonal $SO(3)$. "
                               "$Z = \\frac{1}{|\\Gamma|}\\sum_{gh=hg} Z_{g,h}$ is organized by the abelian subgroups "
                               "of $\\Gamma$ (Möbius inversion on the subgroup lattice): a cyclic $C_n$ gives the "
                               "circle at $R = n\\sqrt2$, the Klein group $V_4 = D_2$ the orbifold at $R = 2\\sqrt2$."))


def main():
    specs = {}
    for M, at in ((1, "\\sqrt{2}"), (2, "2"), (4, "2\\sqrt{2}")):
        specs[("circ", M)] = circle_spec(M, {"at": at})
    for M, at in ((1, "\\sqrt{2}"), (2, "2"), (3, "\\sqrt{6}"), (4, "2\\sqrt{2}")):
        specs[("orb", M)] = orbifold_spec(M, {"at": at})
    third, sixth = F(1, 3), F(1, 6)
    specs["T"] = polyhedral("T", [(1, "circ", 9), (third, "orb", 4), (-third, "circ", 1)],
                            "su2-1-orbifold-t", 12, "tetrahedral")
    specs["O"] = polyhedral("O", [(F(1, 2), "circ", 16), (F(1, 2), "circ", 9), (F(2, 3), "orb", 4),
                                  (-F(1, 2), "circ", 4), (-sixth, "circ", 1)],
                            "su2-1-orbifold-o", 24, "octahedral")
    specs["I"] = polyhedral("I", [(F(1, 2), "circ", 25), (F(1, 2), "circ", 9), (third, "orb", 4),
                                  (-third, "circ", 1)],
                            "su2-1-orbifold-i", 60, "icosahedral")
    for s in specs.values():
        p = write_spectrum(s)
        print("wrote", p.relative_to(ROOT))

    # cross-checks
    ising2 = None
    from gen_tim2 import Builder  # noqa: F401
    from rcft import minimal_fields
    f = {x.h: x.char for x in minimal_fields(3, 12).values()}
    hs = sorted(f)
    ising2 = {"c": "1", "blocks": [block(f[a] * f[b], 1, "x") for a in hs for b in hs],
              "Z": [[i, i, 1] for i in range(9)]}
    pf4 = json.loads((ROOT / "data/spectra/zk-parafermions/4.json").read_text())
    for name, a, b in (("orbifold(sqrt2) = circle(2 sqrt2)", specs[("orb", 1)], specs[("circ", 4)]),
                       ("orbifold(2) = Ising^2", specs[("orb", 2)], ising2),
                       ("orbifold(sqrt6) = PF_4", specs[("orb", 3)], pf4)):
        ok, Hc = same_z(a, b)
        print(f"  {'OK ' if ok else 'FAIL'} {name} (up to h, hbar <= {Hc})")


if __name__ == "__main__":
    main()
