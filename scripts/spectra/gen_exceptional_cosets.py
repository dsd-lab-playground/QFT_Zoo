#!/usr/bin/env python3
"""Spectra of the exceptional diagonal cosets

    w-e7-coset        (E_7)_1 x (E_7)_2 / (E_7)_3   = W(E_7) minimal model, (p, p') = (20, 21)
    w-e8-coset        (E_8)_1 x (E_8)_3 / (E_8)_4   = W(E_8) minimal model, (p, p') = (33, 34)
    w-e8-coset-perm   the same characters with the exceptional (E_8)_4 automorphism invariant
    g2-coset          (G_2)_1 x (G_2)_2 / (G_2)_3   (48 branching functions)

The W(E_r) characters come from the Frenkel-Kac-Wakimoto formula (affine Weyl orbit
summed by folding lattice points into the alcove), the G_2 branching functions from
Weyl-Kac characters decomposed grade by grade; see exceptional_lie.py.

    python scripts/spectra/gen_exceptional_cosets.py [--selftest]

--selftest first checks the two engines against independent results: Rocha-Caridi
(A_1) and 3-state Potts W_3 (A_2) characters, FKW versus affine branching functions
for SU(4) and SO(8) cosets, and (G_2)_1 x (F_4)_1 = (E_8)_1.
"""

from __future__ import annotations

import sys
import time
from fractions import Fraction as F

from common import Series, block, write_spectrum
from exceptional_lie import (A, E7, E7_OUTER, E8, G2, AffineStrings, Lie, Tensor, _chain_cartan,
                             branching, fkw_characters, outer_action)

GEN = "scripts/spectra/gen_exceptional_cosets.py"
TOP = 9          # every block is given up to this absolute weight

FKW_TEX = ("Frenkel-Kac-Wakimoto characters $\\chi_{{\\lambda,\\mu}} = \\eta(\\tau)^{{-{r}}}\\sum_{{w\\in W}}\\epsilon(w)"
           "\\sum_{{\\alpha\\in Q}} q^{{|p'(\\lambda+\\rho)-p\\,w(\\mu+\\rho)+pp'\\alpha|^2/2pp'}}$ of $\\mathcal{{W}}({g})$ at "
           "$(p,p') = ({p},{pp})$, with $\\lambda$ an integrable $({g})_{{{k}}}$ weight and $\\mu$ an integrable "
           "$({g})_{{{k1}}}$ weight (both labelled by the dimension of the $\\mathfrak{{{gl}}}$ irrep), "
           "$h_{{\\lambda,\\mu}} = \\frac{{|p'(\\lambda+\\rho)-p(\\mu+\\rho)|^2-|\\rho|^2}}{{2pp'}}$. "
           "Equivalently $\\chi_{{\\lambda,\\mu}}$ is the branching function of the $({g})_{{{k1}}}$ module "
           "$\\mu$ in the $({g})_1\\times({g})_{{{k}}}$ module $\\nu\\otimes\\lambda$, the level-one label $\\nu$ "
           "being fixed by the conjugacy classes of $\\lambda$ and $\\mu$.")


def bold(n):
    return f"\\mathbf{{{n}}}"


def fkw_series(h, coeffs, c) -> Series:
    return Series.from_list(h - c / 24, coeffs)


# ------------------------------------------------------------- W(E_7), W(E_8)

def w_e7():
    L = E7()
    p, pp = 20, 21
    k, k1 = p - L.hv, pp - L.hv
    c = L.r * (1 - F(L.hv * (L.hv + 1), p * pp))
    assert c == F(13, 10)
    ch = fkw_characters(L, p, pp, TOP)
    lams, mus = L.integrable(k), L.integrable(k1)
    assert (len(L.integrable(1)), len(lams), len(mus), len(ch)) == (2, 6, 12, 72)
    J2 = {lam: outer_action(L, E7_OUTER, k, lam) for lam in lams}
    J3 = {mu: outer_action(L, E7_OUTER, k1, mu) for mu in mus}
    assert all(J3[mu] != mu for mu in mus), "(E_7)_3 has no fixed points"
    fixed2 = [lam for lam in lams if J2[lam] == lam]
    assert sorted(L.dim(x) for x in fixed2) == [56, 912]
    # field identification (lam, mu) ~ (J lam, J mu): free on pairs; characters must agree
    fields = []
    seen = set()
    for lam in lams:
        for mu in mus:
            if (lam, mu) in seen:
                continue
            orb = [(lam, mu), (J2[lam], J3[mu])]
            seen.update(orb)
            assert ch[orb[0]] == ch[orb[1]], f"field identification fails for {orb}"
            rep = min(orb, key=lambda lm: (L.h(k1, lm[1]), L.h(k, lm[0]), lm[1], lm[0]))
            fields.append(rep)
    assert len(fields) == 36
    # the coset simple current (J0; 0) has h = 9/2 and fixes exactly the fields with J lam = lam;
    # check that these are exactly the fields of odd monodromy charge
    J0 = J2[(0,) * L.r]
    hJ = ch[(J0, (0,) * L.r)][0]
    assert hJ == F(9, 2)
    for lam, mu in fields:
        Q = (hJ + ch[(lam, mu)][0] - ch[(J2[lam], mu)][0]) % 1
        assert Q in (0, F(1, 2)) and (Q == F(1, 2)) == (J2[lam] == lam)
    return L, c, ch, fields, (k, k1)


def w_e8():
    L = E8()
    p, pp = 33, 34
    k, k1 = p - L.hv, pp - L.hv
    c = L.r * (1 - F(L.hv * (L.hv + 1), p * pp))
    assert c == F(256, 187)
    ch = fkw_characters(L, p, pp, TOP)
    lams, mus = L.integrable(k), L.integrable(k1)
    assert (len(L.integrable(1)), len(lams), len(mus), len(ch)) == (1, 5, 10, 50)
    fields = [(lam, mu) for lam in lams for mu in mus]
    return L, c, ch, fields, (k, k1)


def check_fkw(L, c, ch, fields):
    for f in fields:
        h, co = ch[f]
        assert co[0] == 1 and min(co) >= 0, f
    vac = [f for f in fields if ch[f][0] == 0]
    assert vac == [((0,) * L.r, (0,) * L.r)], vac
    # vacuum module: Virasoro vacuum below the first W current (spin 6 for E_7, 8 for E_8)
    first_w = {"E7": 6, "E8": 8}[L.name]
    vir = [1, 0, 1, 1, 2, 2, 4, 4, 7, 8]
    co = ch[vac[0]][1]
    assert co[:first_w] == vir[:first_w] and co[first_w] == vir[first_w] + 1, co


def fkw_blocks(L, c, ch, fields, levels):
    k, k1 = levels
    order = sorted(fields, key=lambda f: (ch[f][0], L.dim(f[0]), L.dim(f[1])))
    blocks, index = [], {}
    for f in order:
        h, co = ch[f]
        label = f"\\chi_{{({bold(L.dim(f[0]))};\\,{bold(L.dim(f[1]))})}}"
        blocks.append(block(fkw_series(h, co, c), c, label, TOP))
        index[f] = len(blocks) - 1
    return blocks, index


def spectrum_w_e7():
    L, c, ch, fields, levels = w_e7()
    check_fkw(L, c, ch, fields)
    blocks, index = fkw_blocks(L, c, ch, fields, levels)
    Z = [[i, i, 1] for i in range(len(blocks))]
    return {
        "theory": "w-e7-coset",
        "c": str(c),
        "chiral_algebra": "\\mathcal{W}(E_7)_{13/10} = \\left((E_7)_1\\times(E_7)_2/(E_7)_3\\right)",
        "irreducible": True,
        "Z_tex": "Z = \\sum_{(\\lambda,\\mu)/\\sim} |\\chi_{\\lambda,\\mu}|^2",
        "character_tex": FKW_TEX.format(r=7, g="E_7", gl="e_7", p=20, pp=21, k=2, k1=3)
        + " Fields are identified as $(\\lambda,\\mu)\\sim(J\\lambda,J\\mu)$ under the $\\mathbb{Z}_2$ simple "
          "current, which acts freely on the 72 pairs because $(E_7)_3$ has no fixed points, leaving 36 fields "
          "(the level-2 fixed points $\\mathbf{56}$, $\\mathbf{912}$ are identified only through the level-3 label).",
        "description": "Diagonal invariant of the coset $(E_7)_1\\times(E_7)_2/(E_7)_3$, the $\\mathcal{W}(E_7)$ "
                       "minimal model (Bais-Bouwknegt-Surridge-Schoutens 1988; Frenkel-Kac-Wakimoto 1992). "
                       "The affine Weyl orbit sum is done exactly by enumerating weight-lattice points in a ball "
                       "and folding them into the level-21 alcove; the same code reproduces Rocha-Caridi and "
                       "$\\mathcal{W}_3$ characters and independently computed $SU(4)$ and $SO(8)$ coset branching "
                       "functions.",
        "generator": GEN,
        "blocks": blocks,
        "Z": Z,
    }


SIGMA_E8 = {(0, 0, 0, 0, 0, 0, 0, 1): (0, 0, 1, 0, 0, 0, 0, 0),
            (0, 0, 1, 0, 0, 0, 0, 0): (0, 0, 0, 0, 0, 0, 0, 1)}   # 248 <-> 6696000 at level 4


def spectra_w_e8():
    L, c, ch, fields, levels = w_e8()
    check_fkw(L, c, ch, fields)
    k, k1 = levels
    a, b = SIGMA_E8
    assert (L.dim(a), L.dim(b)) == (248, 6696000)
    assert (L.h(k1, a), L.h(k1, b)) == (F(15, 17), F(49, 17))
    blocks, index = fkw_blocks(L, c, ch, fields, levels)
    common = {
        "c": str(c),
        "chiral_algebra": "\\mathcal{W}(E_8)_{256/187} = \\left((E_8)_1\\times(E_8)_3/(E_8)_4\\right)",
        "irreducible": True,
        "character_tex": FKW_TEX.format(r=8, g="E_8", gl="e_8", p=33, pp=34, k=3, k1=4)
        + " $E_8$ has trivial centre, so there is no field identification: $5\\times10 = 50$ fields.",
        "generator": GEN,
        "blocks": blocks,
    }
    diag = dict(common)
    diag.update({
        "theory": "w-e8-coset",
        "Z_tex": "Z = \\sum_{\\lambda,\\mu} |\\chi_{\\lambda,\\mu}|^2",
        "description": "Diagonal invariant of the coset $(E_8)_1\\times(E_8)_3/(E_8)_4$, the $\\mathcal{W}(E_8)$ "
                       "minimal model (Bais-Bouwknegt-Surridge-Schoutens 1988; Frenkel-Kac-Wakimoto 1992). "
                       "The affine Weyl orbit sum is done exactly by enumerating $E_8$ lattice points in a ball "
                       "and folding them into the level-34 alcove (no sum over the finite Weyl group); the same "
                       "code reproduces Rocha-Caridi and $\\mathcal{W}_3$ characters and independently computed "
                       "$SU(4)$ and $SO(8)$ coset branching functions.",
        "Z": [[i, i, 1] for i in range(len(blocks))],
    })
    sigma = lambda mu: SIGMA_E8.get(mu, mu)  # noqa: E731
    Zp = sorted([index[(lam, mu)], index[(lam, sigma(mu))], 1] for lam, mu in fields)
    for lam, mu in fields:     # T-invariance of the permutation
        assert (ch[(lam, mu)][0] - ch[(lam, sigma(mu))][0]).denominator == 1
    perm = dict(common)
    perm.update({
        "theory": "w-e8-coset-perm",
        "Z_tex": "Z = \\sum_{\\lambda,\\mu} \\chi_{\\lambda,\\mu}\\,\\overline{\\chi_{\\lambda,\\sigma(\\mu)}}",
        "description": "The $\\mathcal{W}(E_8)$ characters of $(E_8)_1\\times(E_8)_3/(E_8)_4$ combined with the "
                       "exceptional automorphism invariant of $(E_8)_4$ (Gannon-Ruelle-Walton 1995) on the "
                       "level-4 label: $\\sigma$ exchanges $\\mathbf{248}$ ($h = 15/17$) and "
                       "$\\mathbf{6696000}$ ($h = 49/17$) and fixes the other eight $(E_8)_4$ modules. "
                       "Characters as for the diagonal model (alcove folding of the Frenkel-Kac-Wakimoto sum).",
        "Z": Zp,
    })
    return diag, perm


# ------------------------------------------------------------- G_2

def spectrum_g2():
    L = G2()
    c = L.c_wzw(1) + L.c_wzw(2) - L.c_wzw(3)
    assert c == F(22, 15)
    hmax3 = max(L.h(3, mu) for mu in L.integrable(3))
    N = TOP + int(hmax3) + 2
    aff = AffineStrings(L, N)
    tens = Tensor(L)
    br = branching(aff, tens, 1, 2)
    assert [len(L.integrable(k)) for k in (1, 2, 3)] == [2, 4, 6] and len(br) == 48
    rows = []
    for (nu, lam, mu), m in br.items():
        assert any(m) and min(m) >= 0, (nu, lam, mu)
        h0 = L.h(1, nu) + L.h(2, lam) - L.h(3, mu)
        s = Series({h0 - c / 24 + n: x for n, x in enumerate(m) if x}, h0 - c / 24 + N)
        rows.append((min(s.c) + c / 24, L.dim(nu), L.dim(lam), L.dim(mu), s))
    rows.sort(key=lambda t: t[:4])
    assert [r[0] for r in rows].count(0) == 1
    blocks = [block(s, c, f"b_{{({bold(a)},{bold(b)};\\,{bold(d)})}}", TOP) for _, a, b, d, s in rows]
    return {
        "theory": "g2-coset",
        "c": str(c),
        "chiral_algebra": "(G_2)_1\\times(G_2)_2/(G_2)_3",
        "irreducible": True,
        "Z_tex": "Z = \\sum_{\\nu,\\lambda,\\mu} |b_{\\nu,\\lambda;\\mu}|^2",
        "character_tex": "Branching functions $\\chi^{(G_2)_1}_\\nu(\\tau,z)\\,\\chi^{(G_2)_2}_\\lambda(\\tau,z) = "
                         "\\sum_\\mu b_{\\nu,\\lambda;\\mu}(\\tau)\\,\\chi^{(G_2)_3}_\\mu(\\tau,z)$ with "
                         "$\\nu\\in\\{\\mathbf{1},\\mathbf{7}\\}$, $\\lambda\\in\\{\\mathbf{1},\\mathbf{7},\\mathbf{14},"
                         "\\mathbf{27}\\}$, $\\mu\\in\\{\\mathbf{1},\\mathbf{7},\\mathbf{14},\\mathbf{27},\\mathbf{64},"
                         "\\mathbf{77}\\}$; $b_{\\nu,\\lambda;\\mu} = q^{h_\\nu+h_\\lambda-h_\\mu-c/24}\\sum_{n\\ge0}"
                         "m_n q^n$ with $h^{(k)}_\\lambda = \\frac{(\\lambda,\\lambda+2\\rho)}{2(k+4)}$. $G_2$ has "
                         "trivial centre, so there is no selection rule or field identification: 48 fields.",
        "description": "Diagonal invariant of the coset $(G_2)_1\\times(G_2)_2/(G_2)_3$ (Goddard-Kent-Olive 1985). "
                       "Weyl-Kac characters graded by the $G_2$ weight lattice are decomposed into finite $G_2$ "
                       "irreps grade by grade; the products are reduced with Brauer-Klimyk and peeled off into "
                       "$(G_2)_3$ characters. The same code reproduces the $SU(2)$ and $SU(3)$ coset (Virasoro and "
                       "$\\mathcal{W}_3$) characters and the conformal embedding $(G_2)_1\\times(F_4)_1 = (E_8)_1$.",
        "generator": GEN,
        "blocks": blocks,
        "Z": [[i, i, 1] for i in range(len(blocks))],
    }


# ------------------------------------------------------------- self-tests

def selftest():
    from rcft import minimal_c, minimal_char
    t0 = time.time()
    # 1. FKW and affine branching for A_1 = Virasoro (unitary and non-unitary)
    for p, pp in [(3, 4), (4, 5), (6, 7), (3, 5), (2, 7)]:
        for (lam, mu), (h, co) in fkw_characters(A(1), p, pp, 10).items():
            ref = minimal_char(p, pp, lam[0] + 1, mu[0] + 1, 10)
            e0 = min(ref.c)
            assert e0 + minimal_c(p, pp) / 24 == h and [ref.coeff(e0 + n) for n in range(len(co))] == co
    L = A(1)
    aff, tens = AffineStrings(L, 10), Tensor(L)
    for k in (1, 2, 3, 4):
        c = minimal_c(k + 2, k + 3)
        for (nu, lam, mu), m in branching(aff, tens, 1, k).items():
            if (nu[0] + lam[0] + mu[0]) % 2:
                assert not any(m)
                continue
            _check_branch(L, (1, k, k + 1), (nu, lam, mu), m, minimal_char(k + 2, k + 3, lam[0] + 1, mu[0] + 1, 20), c)
    print(f"  A_1: FKW and SU(2)_1 x SU(2)_k / SU(2)_k+1 = Rocha-Caridi characters  ({time.time() - t0:.1f}s)")
    # 2. A_2 at (4, 5): W_3 characters of the 3-state Potts model
    vir = lambda r, s: minimal_char(5, 6, r, s, 20)  # noqa: E731
    W3 = {F(0): vir(1, 1) + vir(1, 5), F(2, 5): vir(2, 1) + vir(2, 5), F(1, 15): vir(2, 3), F(2, 3): vir(1, 3)}
    c = F(4, 5)
    for (lam, mu), (h, co) in fkw_characters(A(2), 4, 5, 10).items():
        ref = W3[h]
        e0 = min(ref.c)
        assert [ref.coeff(e0 + n) for n in range(len(co))] == co
    L = A(2)
    aff, tens = AffineStrings(L, 8), Tensor(L)
    for key, m in branching(aff, tens, 1, 1).items():
        if any(m):
            h = L.h(1, key[0]) + L.h(1, key[1]) - L.h(2, key[2]) + next(i for i, x in enumerate(m) if x)
            _check_branch(L, (1, 1, 2), key, m, W3[h], c)
    print(f"  A_2: FKW and SU(3)_1 x SU(3)_1 / SU(3)_2 = Potts W_3 characters  ({time.time() - t0:.1f}s)")
    # 3. FKW versus affine branching for A_3 at (5, 6) and D_4 at (7, 8)
    D4 = Lie("D4", _chain_cartan(4, [(1, 2), (2, 3), (2, 4)]))
    for L, p, pp, N in [(A(3), 5, 6, 7), (D4, 7, 8, 6)]:
        fk = fkw_characters(L, p, pp, N)
        br = branching(AffineStrings(L, N), Tensor(L), 1, p - L.hv)
        for (lam, mu), (h, co) in fk.items():
            hits = [(nu, m) for (nu, l2, m3), m in br.items() if (l2, m3) == (lam, mu) and any(m)]
            assert len(hits) == 1
            nu, m = hits[0]
            sh = h - (L.h(1, nu) + L.h(p - L.hv, lam) - L.h(pp - L.hv, mu))
            assert sh.denominator == 1 and not any(m[:int(sh)])
            tail = m[int(sh):]
            n = min(len(tail), len(co))
            assert n >= 4 and tail[:n] == co[:n]
        print(f"  {L.name}: FKW characters = affine branching functions at (p, p') = ({p}, {pp})  "
              f"({time.time() - t0:.1f}s)")
    # 4. non-simply-laced Weyl-Kac: (G_2)_1 x (F_4)_1 = (E_8)_1
    F4 = Lie("F4", [[2, -1, 0, 0], [-1, 2, -1, 0], [0, -2, 2, -1], [0, 0, -1, 2]], d=[1, 1, F(1, 2), F(1, 2)])
    N = 5
    aG, aF = AffineStrings(G2(), N), AffineStrings(F4, N)

    def dims(aff, k, lam):
        return [sum(m * aff.L.dim(nu) for nu, m in row.items()) for row in aff.string(k, lam)]

    g0, g7 = dims(aG, 1, (0, 0)), dims(aG, 1, (1, 0))
    f0, f26 = dims(aF, 1, (0, 0, 0, 0)), dims(aF, 1, (0, 0, 0, 1))
    assert F4.dim((0, 0, 0, 1)) == 26 and G2().h(1, (1, 0)) + F4.h(1, (0, 0, 0, 1)) == 1
    e8 = [sum(g0[a] * f0[n - a] for a in range(n + 1)) + sum(g7[a] * f26[n - 1 - a] for a in range(n))
          for n in range(N + 1)]
    assert e8 == [1, 248, 4124, 34752, 213126, 1057504], e8
    print(f"  G_2, F_4: (G_2)_1 x (F_4)_1 characters add up to (E_8)_1  ({time.time() - t0:.1f}s)")


def _check_branch(L, levels, key, m, ref, c):
    k1, k2, k3 = levels
    nu, lam, mu = key
    h0 = L.h(k1, nu) + L.h(k2, lam) - L.h(k3, mu)
    e0 = min(ref.c)
    sh = e0 + c / 24 - h0
    assert sh.denominator == 1 and sh >= 0
    sh = int(sh)
    assert m == [0] * sh + [ref.coeff(e0 + n) for n in range(len(m) - sh)], key


# ------------------------------------------------------------- main

def report(spec):
    c = F(spec["c"])
    hs = sorted(F(b["h"]) for b in spec["blocks"])
    print(f"  {spec['theory']}: c = {c}, {len(spec['blocks'])} blocks, lowest h: "
          + ", ".join(str(h) for h in hs[:4]))


def main(argv):
    t0 = time.time()
    if "--selftest" in argv:
        print("self-tests:")
        selftest()
    specs = [spectrum_w_e7()]
    specs += list(spectra_w_e8())
    specs.append(spectrum_g2())
    for spec in specs:
        path = write_spectrum(spec)
        report(spec)
        print(f"    wrote {path.relative_to(path.parents[2])}")
    print(f"done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main(sys.argv[1:])
