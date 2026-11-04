#!/usr/bin/env python3
"""Spectra of two tricritical Ising models and their orbifolds / permutation
invariants: TIM^2, Sym^2(TIM), TIM^2/<f1 f2>, TIM^2 with the Fibonacci swap,
and X_E = TIM^2/Z_4 (whose partition function X_O shares).

Also cross-checks (printed): TIM^2/<f1f2, s> = PF_8, TIM^2/<f1f2, s>_tors =
TIM^2/Z_4 = N_10^(A,E6), TIM^2/<f1 f2> = N_10^(D,E6).

    python scripts/spectra/gen_tim2.py
"""

from __future__ import annotations

import json
from fractions import Fraction as F

from common import ROOT, Series, block, frac_str, write_spectrum
from rcft import minimal_fields
from zoo_spectrum import expand

GEN = "scripts/spectra/gen_tim2.py"
C = F(7, 5)
TOP = 8

# TIM = M(4,5): fields by weight; spin flip f is -1 on the two sigma fields;
# J = phi_{3,1} (h = 3/2) is the simple current; TIM = Fib x Ising_7.
H = [F(0), F(1, 10), F(3, 5), F(3, 2), F(7, 16), F(3, 80)]
NAME = {F(0): "0", F(1, 10): "\\tfrac1{10}", F(3, 5): "\\tfrac35", F(3, 2): "\\tfrac32",
        F(7, 16): "\\tfrac7{16}", F(3, 80): "\\tfrac3{80}"}
EPS = {h: (-1 if h in (F(7, 16), F(3, 80)) else 1) for h in H}
JMAP = {F(0): F(3, 2), F(3, 2): F(0), F(1, 10): F(3, 5), F(3, 5): F(1, 10), F(7, 16): F(7, 16), F(3, 80): F(3, 80)}
FIB = {F(0): ("1", "1"), F(3, 2): ("1", "psi"), F(7, 16): ("1", "sig"),
       F(3, 5): ("tau", "1"), F(1, 10): ("tau", "psi"), F(3, 80): ("tau", "sig")}
FIB_INV = {v: k for k, v in FIB.items()}


def tim_chars(top):
    f = minimal_fields(4, top)
    out = {}
    for fld in f.values():
        out[fld.h] = fld.char
    return out


class Builder:
    """Z as a sum of coef * b_i * conj(b_j) over named blocks."""

    def __init__(self):
        self.blocks: dict[str, tuple[str, Series]] = {}
        self.Z: dict[tuple[str, str], F] = {}

    def b(self, key, label, series):
        self.blocks.setdefault(key, (label, series))
        return key

    def add(self, coef, i, j):
        self.Z[(i, j)] = self.Z.get((i, j), 0) + F(coef)

    def spec(self, theory, **extra):
        Z = {k: v for k, v in self.Z.items() if v}
        used = sorted({i for i, _ in Z} | {j for _, j in Z}, key=list(self.blocks).index)
        idx = {k: n for n, k in enumerate(used)}
        blocks = [block(self.blocks[k][1], C, self.blocks[k][0]) for k in used]
        Zl = [[idx[i], idx[j], frac_str(v)] for (i, j), v in sorted(Z.items(), key=lambda kv: (idx[kv[0][0]], idx[kv[0][1]]))]
        return {"theory": theory, "c": str(C), **extra, "generator": GEN, "blocks": blocks, "Z": Zl}


def sign_flip(s: Series, e0: F) -> Series:
    """sum c_n q^{(e0+n)/2}  ->  sum (-1)^n c_n q^{(e0+n)/2}  (for s already at tau/2)."""
    return Series({e: a * (-1 if ((2 * e - e0) % 2) else 1) for e, a in s.c.items()}, s.top)


def ingredients(B: Builder, ch):
    """Register the blocks used below; returns helper dicts of keys."""
    prod, half, half_t, dbl = {}, {}, {}, {}
    for a in H:
        for b in H:
            prod[(a, b)] = B.b(f"P{a},{b}", f"\\chi_{{{NAME[a]}}}\\chi_{{{NAME[b]}}}", ch[a] * ch[b])
    for a in H:
        e0 = ch[a].lead()
        h2 = ch[a].subs(F(1, 2))
        half[a] = B.b(f"H{a}", f"\\chi_{{{NAME[a]}}}(\\tfrac{{\\tau}}{{2}})", h2)
        half_t[a] = B.b(f"T{a}", f"\\chi_{{{NAME[a]}}}(\\tfrac{{\\tau+1}}{{2}})", sign_flip(h2, e0))
        dbl[a] = B.b(f"D{a}", f"\\chi_{{{NAME[a]}}}(2\\tau)", ch[a].subs(2))
    return prod, half, half_t, dbl


def S_sign(a):
    """e^{2 pi i (h_a - h_{Ja})}: -1 on the f-even fields, +1 on the sigmas."""
    return -EPS[a]


def tim_squared(ch):
    B = Builder()
    prod, *_ = ingredients(B, ch)
    for a in H:
        for b in H:
            B.add(1, prod[(a, b)], prod[(a, b)])
    return B


def tim2_z2(ch, B=None, coef=1):
    """Z of TIM^2/<f1 f2> = 1/2 (Z^2 + Z_{1,f}^2 + Z_{f,1}^2 + Z_{f,f}^2)."""
    B = B or Builder()
    prod, *_ = ingredients(B, ch)
    for a in H:
        for b in H:
            B.add(F(coef, 2) * (1 + EPS[a] * EPS[b]), prod[(a, b)], prod[(a, b)])
            B.add(F(coef, 2) * (1 + S_sign(a) * S_sign(b)), prod[(a, b)], prod[(JMAP[a], JMAP[b])])
    return B


def sym2(ch, B=None, coef=1):
    """1/2 [Z(tau)^2 + Z(2 tau) + Z(tau/2) + Z((tau+1)/2)]."""
    B = B or Builder()
    prod, half, half_t, dbl = ingredients(B, ch)
    for a in H:
        for b in H:
            B.add(F(coef, 2), prod[(a, b)], prod[(a, b)])
        B.add(F(coef, 2), dbl[a], dbl[a])
        B.add(F(coef, 2), half[a], half[a])
        B.add(F(coef, 2), half_t[a], half_t[a])
    return B


def v4(ch, torsion: int):
    """TIM^2/<f1 f2, s> with discrete torsion sign `torsion` (+1: none)."""
    B = Builder()
    prod, half, half_t, dbl = ingredients(B, ch)
    q = F(1, 4)
    for a in H:
        for b in H:
            B.add(q, prod[(a, b)], prod[(a, b)])
            B.add(q * EPS[a] * EPS[b], prod[(a, b)], prod[(a, b)])
            B.add(q, prod[(a, b)], prod[(JMAP[a], JMAP[b])])
            B.add(q * S_sign(a) * S_sign(b), prod[(a, b)], prod[(JMAP[a], JMAP[b])])
    for a in H:
        # s and f1 f2 s sectors: 2 [Z(2tau) + Z(tau/2) + Z((tau+1)/2)]
        B.add(2 * q, dbl[a], dbl[a])
        B.add(2 * q, half[a], half[a])
        B.add(2 * q, half_t[a], half_t[a])
        # mixed sectors: 2 [Z_{f,1}(2tau) + Z_{1,f}(tau/2) + Z_{1,f}((tau+1)/2)]
        B.add(2 * q * torsion, dbl[a], dbl[JMAP[a]])
        B.add(2 * q * torsion * EPS[a], half[a], half[a])
        B.add(2 * q * torsion * EPS[a], half_t[a], half_t[a])
    return B


def z4(ch):
    """TIM^2/<f1 s> (Z_4), from the SL(2,Z) orbits of the twisted sectors."""
    B = Builder()
    prod, half, half_t, dbl = ingredients(B, ch)
    q = F(1, 4)
    for a in H:
        for b in H:
            B.add(q * (1 + EPS[a] * EPS[b]), prod[(a, b)], prod[(a, b)])
            B.add(q * (1 + S_sign(a) * S_sign(b)), prod[(a, b)], prod[(JMAP[a], JMAP[b])])
    for a in H:
        B.add(2 * q * EPS[a], dbl[a], dbl[a])                       # Z_{1,g} + Z_{1,g^3}
        B.add(-2 * q * EPS[a], dbl[a], dbl[JMAP[a]])                # Z_{g^2,g} + Z_{g^2,g^3}
        B.add(2 * q * (1 + S_sign(a)), half[a], half[JMAP[a]])      # Z_{g,1}+Z_{g^3,1}+Z_{g,g^2}+Z_{g^3,g^2}
        if EPS[a] == -1:
            B.add(4 * q, half_t[a], half_t[a])                      # Z_{g,g}+Z_{g,g^3}+CPT images
    return B


def fib_swap(ch):
    B = Builder()
    prod, *_ = ingredients(B, ch)
    for f1 in ("1", "tau"):
        for f2 in ("1", "tau"):
            for i1 in ("1", "psi", "sig"):
                for i2 in ("1", "psi", "sig"):
                    left = prod[(FIB_INV[(f1, i1)], FIB_INV[(f2, i2)])]
                    right = prod[(FIB_INV[(f2, i1)], FIB_INV[(f1, i2)])]
                    B.add(1, left, right)
    return B


def same_z(spec1, spec2):
    D1, H1 = expand(spec1)
    D2, H2 = expand(spec2)
    Hc = min(H1, H2)
    a = {k: v for k, v in D1.items() if k[0] <= Hc and k[1] <= Hc}
    b = {k: v for k, v in D2.items() if k[0] <= Hc and k[1] <= Hc}
    return a == b, Hc


def main():
    ch = tim_chars(2 * TOP + 2)
    TIM_TEX = ("Tricritical Ising characters $\\chi_h$ (Rocha-Caridi characters of $\\mathcal{M}(4,5)$), "
               "$h \\in \\{0, \\tfrac1{10}, \\tfrac35, \\tfrac32, \\tfrac7{16}, \\tfrac3{80}\\}$, evaluated at "
               "$\\tau$, $2\\tau$, $\\tau/2$ and $(\\tau+1)/2$ (up to a phase); $f$ is the spin flip, odd on "
               "$\\tfrac7{16}, \\tfrac3{80}$, and $J$ the simple current $\\chi_{3/2}$.")
    common = dict(character_tex=TIM_TEX)

    specs = {}
    specs["tim-squared"] = tim_squared(ch).spec(
        "tim-squared", chiral_algebra="\\mathrm{Vir}_{7/10}\\otimes\\mathrm{Vir}_{7/10}", irreducible=True,
        Z_tex="Z = Z_{\\rm TIM}(\\tau)^2",
        character_tex="Products of two tricritical Ising (Rocha-Caridi) characters.",
        description="Two decoupled tricritical Ising models.")
    specs["tim-sym2"] = sym2(ch).spec(
        "tim-sym2", irreducible=False,
        Z_tex="Z = \\tfrac12\\left[Z_{\\rm TIM}(\\tau)^2 + Z_{\\rm TIM}(2\\tau) + Z_{\\rm TIM}(\\tfrac{\\tau}{2}) + Z_{\\rm TIM}(\\tfrac{\\tau+1}{2})\\right]",
        description=("Symmetric orbifold of two tricritical Ising models: the standard formula for the "
                     "$\\mathbb{Z}_2$ permutation orbifold (Klemm-Schmidt; Dijkgraaf-Moore-Verlinde-Verlinde)."),
        **common)
    specs["tim2-z2-diag"] = tim2_z2(ch).spec(
        "tim2-z2-diag", irreducible=False,
        Z_tex="Z = \\tfrac12\\left[Z^2 + Z_{1,f}^2 + Z_{f,1}^2 + Z_{f,f}^2\\right],\\quad Z_{1,f} = \\sum_h \\epsilon_h|\\chi_h|^2,\\ Z_{f,1} = \\sum_h \\chi_h\\overline{\\chi_{Jh}}",
        description=("Orbifold of TIM$^2$ by the diagonal spin flip $f_1 f_2$; the $f$-twisted sector of one "
                     "TIM is $\\sum_h \\chi_h\\overline{\\chi_{Jh}}$, so this is the extension of "
                     "$\\mathrm{Vir}_{7/10}^{\\otimes 2}$ by $\\chi_{3/2}\\otimes\\chi_{3/2}$."),
        **common)
    specs["tim2-fib-swap"] = fib_swap(ch).spec(
        "tim2-fib-swap", chiral_algebra="\\mathrm{Vir}_{7/10}\\otimes\\mathrm{Vir}_{7/10}", irreducible=True,
        Z_tex="Z = \\sum \\chi_{(f_1,i_1)}\\chi_{(f_2,i_2)}\\,\\overline{\\chi_{(f_2,i_1)}\\chi_{(f_1,i_2)}}",
        character_tex=("Products of tricritical Ising characters, labelled by "
                       "$\\mathrm{Fib}\\boxtimes\\mathrm{Ising}^{(7)}$: $(f, i)$ with $f\\in\\{1,\\tau\\}$ "
                       "($h_\\tau = \\tfrac35$) and $i \\in\\{1,\\psi,\\sigma\\}$ ($h_\\psi = \\tfrac32$, $h_\\sigma = \\tfrac7{16}$)."),
        description=("Permutation invariant of TIM$^2$ that exchanges the Fibonacci labels of the two "
                     "factors and keeps their Ising-type labels; it comes from a braided autoequivalence of "
                     "$\\mathrm{Rep}(\\mathrm{TIM}^2)$ (Kong-Runkel; Davydov-Kong-Runkel)."))
    xe = z4(ch)
    for tid, extra in (("tim2-z4-xe", "This is $X_E$."),
                       ("tim2-d4tors-xo", "$X_O = \\mathrm{TIM}^2/D_4^{\\rm tors}$ has the same torus partition "
                                          "function as $X_E = \\mathrm{TIM}^2/\\mathbb{Z}_4$, computed here from the "
                                          "$\\mathbb{Z}_4$ orbifold; the two CFTs differ in how left and right "
                                          "modules with equal characters are paired.")):
        specs[tid] = xe.spec(
            tid, irreducible=False,
            Z_tex="Z = \\tfrac14\\sum_{a,b\\in\\mathbb{Z}_4} Z_{g^a,g^b},\\quad g = f_1 s",
            description=("Orbifold of TIM$^2$ by $\\mathbb{Z}_4 = \\langle f_1 s\\rangle$ ($s$ exchanges the "
                         "copies, $f_1$ flips the first spin). Untwined sectors of $g$ give $\\chi(2\\tau)$, "
                         "$g$-twisted sectors $\\chi(\\tau/2)$; the rest follow by $SL(2,\\mathbb{Z})$. " + extra),
            **common)

    for tid, spec in specs.items():
        p = write_spectrum(spec)
        print("wrote", p.relative_to(ROOT))

    # ---- cross-checks
    import gen_n1
    pf8 = json.loads((ROOT / "data/spectra/pf8.json").read_text())
    for name, a, b in (
        ("TIM^2/<f1f2,s> = PF_8", v4(ch, +1).spec("x"), pf8),
        ("TIM^2/<f1f2,s>_tors = TIM^2/Z_4", v4(ch, -1).spec("x"), specs["tim2-z4-xe"]),
        ("TIM^2/Z_4 = N_10^(A,E6)", specs["tim2-z4-xe"], gen_n1.make(10, "A", "E6", None, "x", write=False)),
        ("TIM^2/<f1f2> = N_10^(D,E6)", specs["tim2-z2-diag"], gen_n1.make(10, "D", "E6", None, "x", write=False)),
    ):
        ok, Hc = same_z(a, b)
        print(f"  {'OK ' if ok else 'FAIL'} {name} (compared up to h, hbar <= {Hc})")


if __name__ == "__main__":
    main()
