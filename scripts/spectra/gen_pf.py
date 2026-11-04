#!/usr/bin/env python3
"""Spectra of the Z_k parafermion theories PF_k = SU(2)_k/U(1) (diagonal) and the
Z_3 simple-current extension of PF_9.

    python scripts/spectra/gen_pf.py
"""

from __future__ import annotations

from fractions import Fraction as F

from common import block, write_spectrum
from rcft import Field, simple_current_invariant, spectrum_from
from su2 import parafermion_char, parafermion_h

GEN = "scripts/spectra/gen_pf.py"
TOP = 8

CHAR_TEX = ("String functions: $\\chi^{SU(2)_k}_l(\\tau, z) = \\sum_{m \\in \\mathbb{Z}_{2k}} \\Phi^l_m(\\tau)\\,"
            "\\frac{\\Theta_{m,k}(\\tau,z)}{\\eta(\\tau)}$ with $\\Theta_{m,k} = \\sum_{n\\in\\mathbb{Z}+m/2k} q^{kn^2}z^{kn}$, "
            "computed from the Weyl-Kac formula; fields $(l,m)\\sim(k-l,m+k)$, $l \\equiv m \\pmod 2$, "
            "$h^l_m = \\frac{l(l+2)}{4(k+2)} - \\frac{m^2}{4k}$ for $|m| \\le l$.")


def pf_fields(k, top=TOP):
    """Representatives (l, m) with |m| <= l where possible; returns (fields, key->index)."""
    N = int(top + F(k, 4)) + 4
    seen, fields, index = {}, [], {}
    for l in range(k + 1):
        for m in range(-l, l + 1, 2):
            key = (l, m % (2 * k))
            alt = (k - l, (m + k) % (2 * k))
            if key in seen:
                continue
            ch = parafermion_char(k, l, m, N)
            fields.append(Field(f"\\Phi^{{{l}}}_{{{m}}}", parafermion_h(k, l, m), ch))
            seen[key] = seen[alt] = len(fields) - 1
    return fields, seen


def pf_diag(k, theory, member=None):
    c = F(2 * (k - 1), k + 2)
    fields, _ = pf_fields(k)
    M = {(i, i): 1 for i in range(len(fields))}
    blocks, Z = spectrum_from(fields, M, c, TOP)
    spec = {"theory": theory}
    if member:
        spec["member"] = member
    spec.update({
        "c": str(c),
        "chiral_algebra": f"\\mathrm{{PF}}_{{{k}}} = SU(2)_{{{k}}}/U(1)",
        "irreducible": True,
        "Z_tex": "Z = \\sum_{(l,m)/\\sim} |\\Phi^l_m|^2",
        "character_tex": CHAR_TEX,
        "description": (f"Diagonal invariant of the $\\mathbb{{Z}}_{{{k}}}$ parafermion theory "
                        f"(Fateev-Zamolodchikov; Gepner-Qiu): {len(fields)} fields."),
        "generator": GEN, "blocks": blocks, "Z": Z})
    p = write_spectrum(spec)
    print("wrote", p.relative_to(p.parents[2]))


def pf9_z3():
    k = 9
    c = F(2 * (k - 1), k + 2)
    fields, index = pf_fields(k)
    reps = {}
    for (l, mm), i in index.items():
        reps.setdefault(i, (l, mm))
    J = {}
    for i, (l, mm) in reps.items():
        J[i] = index[(l, (mm + 6) % (2 * k))]
    M = simple_current_invariant(fields, J, 3)
    blocks, Z = spectrum_from(fields, M, c, TOP)
    spec = {"theory": "pf9-z3", "c": str(c),
            "chiral_algebra": "\\mathrm{PF}_9 = SU(2)_9/U(1)",
            "irreducible": True,
            "Z_tex": "Z = \\sum_{Q_J(a) = 0} \\Big|\\sum_{n=0}^{2} \\Phi_{J^n a}\\Big|^2",
            "character_tex": CHAR_TEX,
            "description": ("Extension of $\\mathrm{PF}_9$ by the $\\mathbb{Z}_3$ simple currents "
                            "$J = \\Phi^0_{6}$, $J^2 = \\Phi^0_{12}$ (weight 2, the order-three parafermions); "
                            "Kreuzer-Schellekens invariant, no fixed points. Equivalently the orbifold of "
                            "$\\mathrm{PF}_9$ by its $\\mathbb{Z}_3$ rotation subgroup."),
            "generator": GEN, "blocks": blocks, "Z": Z}
    p = write_spectrum(spec)
    print("wrote", p.relative_to(p.parents[2]))


def main():
    for k in range(2, 11):
        pf_diag(k, "zk-parafermions", {"at": k})
    for k in (5, 7, 8, 9):
        pf_diag(k, f"pf{k}")
    pf9_z3()


if __name__ == "__main__":
    main()
