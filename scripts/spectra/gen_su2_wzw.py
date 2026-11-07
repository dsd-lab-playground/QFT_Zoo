#!/usr/bin/env python3
"""Spectra of the SU(2)_k WZW models with the Cappelli-Itzykson-Zuber
invariants: the diagonal (A_{k+1}) invariant for k = 1..10, the D-series
(D_{k/2+2}) for even k = 4..18, and the exceptional E_6, E_7, E_8 invariants
at k = 10, 16, 28.

Blocks are the k+1 integrable characters of affine SU(2)_k at z = 1 (the
graded Weyl-Kac characters of su2.py summed over the J^3_0 grading); Z lists
the integer CIZ multiplicities N_{l l'} (rcft.ade), so every Z coefficient is
an SU(2)_k multiplicity.

    python scripts/spectra/gen_su2_wzw.py
"""

from __future__ import annotations

import math
from fractions import Fraction as F

from common import Series, inv_phi, write_spectrum
from rcft import Field, ade, spectrum_from
from su2 import W, c_su2, h_su2, su2_char

GEN = "scripts/spectra/gen_su2_wzw.py"
TOP = 9                         # blocks kept to weight max(9, h + 2), so every block reaches h >= 8

CHAR_TEX = ("Integrable characters of affine $SU(2)_k$ at $z=1$, labelled by $l = 2j = 0,\\dots,k$: "
            "$\\chi_l(\\tau) = \\frac{q^{h_l - c/24}}{\\prod_{n\\ge1}(1-q^n)^3}\\sum_{m\\in\\mathbb{Z}} "
            "\\big(l+1+2(k+2)m\\big)\\, q^{(k+2)m^2 + (l+1)m}$, $h_l = \\frac{l(l+2)}{4(k+2)}$, "
            "$c = \\frac{3k}{k+2}$; computed from the graded Weyl-Kac formula and summed over the "
            "$J^3_0$ grading.")


def chars(k: int) -> list[Field]:
    """The k+1 characters chi_l(q), each exact up to weight max(TOP, h_l + 2)."""
    c = c_su2(k)
    out = []
    for l in range(k + 1):
        h = h_su2(k, l)
        top = max(F(TOP), h + 2)
        N = math.ceil(top - h) + 1
        G = su2_char(k, l, N)
        # the z-grading must not have been truncated at |2 J^3| = W
        assert not G.a[:, :3].any() and not G.a[:, -3:].any(), (k, l)
        coeffs = [int(x) for x in G.a.sum(axis=1)]
        assert coeffs[0] == l + 1, (k, l, coeffs[:2])          # spin-l/2 multiplet
        if l == 0 and k >= 1:
            assert coeffs[1] == 3, coeffs[:2]                   # the three currents J^a_{-1}
        ser = Series({G.E + n: a for n, a in enumerate(coeffs)}, G.E + N)
        assert ser.lead() == h - c / 24
        _check_specialized(k, l, ser)
        out.append(Field(f"\\chi_{{{l}}}", h, ser))
    return out


def _check_specialized(k: int, l: int, ser: Series) -> None:
    """Independent check: the z = 1 Weyl-Kac formula
    chi_l = q^{h-c/24} sum_m (l+1+2Km) q^{K m^2 + (l+1) m} / prod (1-q^n)^3, K = k+2."""
    K = k + 2
    E = h_su2(k, l) - c_su2(k) / 24
    n_top = int(ser.top - E)
    num = {}
    for m in range(-n_top - 2, n_top + 3):
        e = K * m * m + (l + 1) * m
        if 0 <= e <= n_top:
            num[F(e)] = num.get(F(e), 0) + (l + 1 + 2 * K * m)
    p = inv_phi(n_top)
    direct = (Series(num, n_top) * p * p * p).truncate(n_top).shift(E)
    for n in range(n_top + 1):
        assert direct.coeff(E + n) == ser.coeff(E + n), (k, l, n)


def write(theory: str, k: int, kind: str, member_at, Z_tex: str, description: str) -> None:
    c = c_su2(k)
    fields = chars(k)
    M = ade(kind, k)
    assert all(isinstance(v, int) and v > 0 for v in M.values()), M
    assert M.get((0, 0)) == 1
    blocks, Z = spectrum_from(fields, M, c, TOP)
    assert all(isinstance(z[2], int) and z[2] > 0 for z in Z), "non-integer multiplicity"
    spec = {
        "theory": theory,
        "member": {"at": member_at},
        "c": str(c),
        "chiral_algebra": f"\\widehat{{su}}(2)_{{{k}}}",
        "irreducible": True,
        "Z_tex": Z_tex,
        "character_tex": CHAR_TEX,
        "description": description,
        "generator": GEN,
        "blocks": blocks,
        "Z": Z,
    }
    p = write_spectrum(spec)
    print("wrote", p.relative_to(p.parents[2]), f"({len(blocks)} blocks, {len(Z)} Z entries)")


def chi(l: int) -> str:
    return f"\\chi_{{{l}}}"


def d_series_tex(k: int) -> str:
    if k % 4 == 0:
        terms = [f"|{chi(l)}+{chi(k - l)}|^2" for l in range(0, k // 2, 2)]
        return "Z = " + " + ".join(terms) + f" + 2|{chi(k // 2)}|^2"
    even = f"\\sum_{{l\\ \\mathrm{{even}}}} |\\chi_l|^2"
    odd = f"\\sum_{{l\\ \\mathrm{{odd}}}} \\chi_l\\,\\overline{{\\chi_{{{k}-l}}}}"
    return f"Z = {even} + {odd}"


E_TEX = {
    "E6": "Z = |\\chi_0+\\chi_6|^2 + |\\chi_3+\\chi_7|^2 + |\\chi_4+\\chi_{10}|^2",
    "E7": ("Z = |\\chi_0+\\chi_{16}|^2 + |\\chi_4+\\chi_{12}|^2 + |\\chi_6+\\chi_{10}|^2 + |\\chi_8|^2"
           " + \\big[(\\chi_2+\\chi_{14})\\,\\overline{\\chi_8} + \\mathrm{c.c.}\\big]"),
    "E8": "Z = |\\chi_0+\\chi_{10}+\\chi_{18}+\\chi_{28}|^2 + |\\chi_6+\\chi_{12}+\\chi_{16}+\\chi_{22}|^2",
}
E_LEVEL = {"E6": 10, "E7": 16, "E8": 28}
E_NOTE = {
    "E6": (" The three blocks $\\chi_0+\\chi_6$, $\\chi_3+\\chi_7$, $\\chi_4+\\chi_{10}$ are the basic, spinor "
           "and vector characters of $SO(5)_1$ (conformal embedding $SU(2)_{10}\\subset SO(5)_1$), so $Z$ "
           "equals the diagonal $SO(5)_1$ partition function."),
    "E7": (" Not block-diagonal: exchanging $\\chi_8$ with $\\chi_2+\\chi_{14}$ in the antiholomorphic factor "
           "turns it into the $D_{10}$ invariant."),
    "E8": (" The two blocks are the characters of $(G_2)_1$ (conformal embedding $SU(2)_{28}\\subset (G_2)_1$), "
           "so $Z$ equals the diagonal $(G_2)_1$ partition function."),
}


def main():
    for k in range(1, 11):
        write("su2-wzw", k, "A", k, f"Z = \\sum_{{l=0}}^{{{k}}} |\\chi_l|^2",
              (f"Diagonal ($A_{{{k + 1}}}$) invariant of the $SU(2)_{{{k}}}$ WZW model: each of the "
               f"{k + 1} integrable representations $l = 2j = 0,\\dots,{k}$ appears once as "
               f"$(h_l, h_l)$. Blocks are $SU(2)_{{{k}}}$ characters and $Z$ gives their multiplicities."))
    for k in range(4, 19, 2):
        if k % 4 == 0:
            kind = "block-diagonal (the $\\mathbb{Z}_2$ simple-current extension by $\\chi_{" + str(k) + "}$)"
            parity = "even"
        else:
            kind = f"a permutation invariant (odd $l$ paired with ${k}-l$)"
            parity = "odd"
        write("su2-wzw-d", k, "D", k, d_series_tex(k),
              (f"$D_{{{k // 2 + 2}}}$ invariant of $SU(2)_{{{k}}}$ (Cappelli-Itzykson-Zuber), {kind}; "
               f"equivalently the orbifold of the diagonal theory by the $\\mathbb{{Z}}_2$ centre, which "
               f"keeps the untwisted states with even $l$ and adds the twisted-sector states "
               f"$\\chi_l\\overline{{\\chi_{{{k}-l}}}}$ with $l$ {parity}. Blocks are $SU(2)_{{{k}}}$ "
               f"characters and $Z$ gives their multiplicities."))
    for name in ("E6", "E7", "E8"):
        k = E_LEVEL[name]
        write("su2-wzw-e", k, name, k, E_TEX[name],
              (f"${name[0]}_{name[1]}$ invariant of $SU(2)_{{{k}}}$ (Cappelli-Itzykson-Zuber). Blocks are "
               f"$SU(2)_{{{k}}}$ characters and $Z$ gives their multiplicities." + E_NOTE[name]))


if __name__ == "__main__":
    main()
