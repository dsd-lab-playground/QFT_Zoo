#!/usr/bin/env python3
"""Orbifolds of the diagonal Z_k parafermion theories PF_k = SU(2)_k/U(1) by a reflection of
their dihedral symmetry: PF_5/C, PF_7/C, PF_9/C and PF_8/Cr.

    python scripts/spectra/gen_pf_orbifolds.py

C maps the field (l, m) to (l, -m). The C-fixed fields are (l, 0) with l even and, for even k,
(k/2, k/2). On (l, 0) the C-twined character is (K = k + 2)

    t_l = (-1)^{l/2} Theta_l / eta(2 tau),   Theta_l = sum_{x = l+1 mod 2K} sin(pi x/2) q^{x^2/4K},

(the SU(2)_k character at the Weyl element, times eta(2 tau)/eta(tau)), and on (k/2, k/2) it is
t_f = eta(2 tau)/eta(tau). For even k the two classes of reflections, C and Cr (r the Z_k
rotation, which is -1 on (k/2, k/2)), differ only in the sign of |t_f|^2 in Z_{1,g}. Poisson
resummation (scripts/spectra/corbifold.py) gives the twisted sector

    Z_{g,1} = sum_{y = k mod 2, 0 < y <= k} |T_y|^2 + [k even] (|T_0|^2 + sigma |B|^2)/2,
    T_y = eta(tau/2)^{-1} sum_n (-1)^n q^{(y + 2Kn)^2/16K},   B = eta(tau/2)/eta(tau),

with sigma = +1 for C and -1 for Cr; T_y has ground-state weight (k - 2 + y^2)/(16K).
"""

from __future__ import annotations

import math
from fractions import Fraction as F

from common import ROOT, Series, write_spectrum
from corbifold import (Builder, add_twisted, add_untwisted, eta_2_over_eta, eta_ratio_half,
                       inv_eta_2tau, inv_eta_half, ldl, theta_comb, twisted_form)
from su2 import parafermion_char, parafermion_h

GEN = "scripts/spectra/gen_pf_orbifolds.py"
TOP = 8


class PF:
    def __init__(self, k: int):
        self.k, self.K = k, k + 2
        self.c = F(2 * (k - 1), k + 2)
        self.fields: list[tuple[int, int]] = []
        self.index: dict[tuple[int, int], int] = {}
        for l in range(k + 1):
            for m in range(-l, l + 1, 2):
                key = (l, m % (2 * k))
                if key in self.index:
                    continue
                self.index[key] = self.index[(k - l, (m + k) % (2 * k))] = len(self.fields)
                self.fields.append((l, m))
        self.conj = [self.index[(l, (-m) % (2 * k))] for l, m in self.fields]
        self.fixed_f = self.index[(k // 2, k // 2)] if k % 2 == 0 else None
        self._chars: dict = {}

    def h(self, i) -> F:
        return parafermion_h(self.k, *self.fields[i])

    def label(self, i) -> str:
        l, m = self.fields[i]
        return f"\\Phi^{{{l}}}_{{{m}}}"

    def pm_label(self, i, s) -> str:
        l, m = self.fields[i]
        return f"\\Phi^{{{l},{s}}}_{{{m}}}"

    def top(self, i):
        h = self.h(i)
        return h + math.ceil(max(F(TOP), h + 4) - h)

    def char(self, i) -> Series:
        if i not in self._chars:
            l, m = self.fields[i]
            N = int(self.top(i) - self.h(i))
            s = parafermion_char(self.k, l, m, N).truncate(self.top(i) - self.c / 24)
            assert min(s.c) == self.h(i) - self.c / 24 and s.c[min(s.c)] == 1
            self._chars[i] = s
        return self._chars[i]

    # -- the reflection
    def theta_f(self, l):
        """t_l = sum_X f(X) theta_{X, 4K} / eta(2 tau), X = 2x."""
        K = self.K
        return {2 * (l + 1): 1, 2 * (l + 1) + 4 * K: (-1) ** K}

    def twining(self, i) -> Series:
        top = self.top(i) - self.c / 24
        if i == self.fixed_f:
            t = eta_2_over_eta(top)
        else:
            l, m = self.fields[i]
            assert m == 0 and l % 2 == 0
            t = (theta_comb(self.theta_f(l), 4 * self.K, top + F(1, 12)) * inv_eta_2tau(top)).truncate(top)
        assert min(t.c) == self.h(i) - self.c / 24 and t.c[min(t.c)] == 1
        return t

    def twisted(self, sigma: int, top_weight=TOP + 1):
        """Twisted characters and their pairing N (Z_{g,1} = sum N_jk T_j T_k-bar) for the
        reflection class with sign sigma on |t_f|^2."""
        k, K, M = self.k, self.K, 4 * self.K
        H = twisted_form([(1, self.theta_f(l)) for l in range(0, k + 1, 2)], M)
        top = F(top_weight) - self.c / 24
        chars, half = [], []
        for d, w in ldl(H, list(range(M + 1))):
            y = min(w)
            assert w == {y: 1, 2 * K - y: -1, 2 * K + y: -1, 4 * K - y: 1} or (y == 0 and w == {0: 1, 2 * K: -2, 4 * K: 1})
            ser = (theta_comb({m: int(a) for m, a in w.items()}, M, top + F(1, 48)) * inv_eta_half(top)).truncate(top)
            assert F(k - 2 + y * y, 16 * K) - self.c / 24 == min(ser.c)
            if d == 1:
                chars.append((f"\\mathcal{{T}}_{{{y}}}", ser))
            else:
                assert d == F(1, 2) and y == 0 and k % 2 == 0
                half.append(ser)
        N = {(j, j): 1 for j in range(len(chars))}
        if k % 2 == 0:
            (T0,) = half
            B = eta_ratio_half(top)
            X, Y = (T0 + B) * F(1, 2), (T0 - B) * F(1, 2)
            j = len(chars)
            chars += [("\\mathcal{T}_{0}", X), ("\\tilde{\\mathcal{T}}_{0}", Y)]
            if sigma == 1:
                N[(j, j)] = N[(j + 1, j + 1)] = 1            # (|T0|^2 + |B|^2)/2 = |X|^2 + |Y|^2
            else:
                N[(j, j + 1)] = N[(j + 1, j)] = 1            # (|T0|^2 - |B|^2)/2 = X Ybar + Y Xbar
        else:
            assert not half
        return chars, N

    def orbifold(self, sigma: int = 1):
        B = Builder(self.c)
        summands = [(i, i) for i in range(len(self.fields))]
        sign = (lambda i, j: sigma if i == self.fixed_f else 1)
        add_untwisted(B, summands, self.conj, self.char, self.label, twining=self.twining, sign=sign,
                      pm_label=self.pm_label)
        chars, N = self.twisted(sigma)
        add_twisted(B, chars, N)
        return B.result()


CHAR_TEX = ("Parafermion characters (string functions) $\\Phi^l_m$ from $\\chi^{SU(2)_k}_l(\\tau,z) = "
            "\\sum_{m\\in\\mathbb{Z}_{2k}}\\Phi^l_m(\\tau)\\,\\Theta_{m,k}(\\tau,z)/\\eta(\\tau)$, fields $(l,m)\\sim(k-l,m+k)$. "
            "On the $C$-fixed fields $(l,0)$, $l$ even, the twined characters are $t_l = (-1)^{l/2}\\eta(2\\tau)^{-1}"
            "\\sum_{x\\equiv l+1\\ (2K)}\\sin\\frac{\\pi x}{2}\\,q^{x^2/4K}$, $K = k+2$, and $\\Phi^{l,\\pm}_0 = \\frac12(\\Phi^l_0\\pm t_l)$. "
            "Twisted characters: $\\mathcal{T}_y = \\eta(\\tau/2)^{-1}\\sum_{n\\in\\mathbb{Z}}(-1)^n q^{(y+2Kn)^2/16K}$ "
            "($y\\equiv k$ mod 2, $0<y\\le k$), of weight $h = \\frac{k-2+y^2}{16K}$; $\\mathcal{T}^{\\pm}_y$ are its parts "
            "with $L_0-h$ in $\\mathbb{Z}$ and $\\mathbb{Z}+\\frac12$.")

CHAR_TEX_EVEN = (" For even $k$ the fixed field $(k/2,\\pm k/2)$ has $t_f = \\eta(2\\tau)/\\eta(\\tau)$, $\\Phi^{k/2,\\pm}_{k/2} = \\frac12(\\Phi^{k/2}_{k/2}\\pm t_f)$, and the $y=0$ twisted "
                 "characters are $\\mathcal{T}_0 = \\frac12(D_0 + B)$, $\\tilde{\\mathcal{T}}_0 = \\frac12(D_0 - B)$ with "
                 "$D_0 = \\eta(\\tau/2)^{-1}\\sum_n(-1)^n q^{Kn^2/4}$ and $B = \\eta(\\tau/2)/\\eta(\\tau)$.")


def write(P: PF, theory: str, sigma: int, gname: str):
    blocks, Z = P.orbifold(sigma)
    k = P.k
    nfix = len([i for i in range(len(P.fields)) if P.conj[i] == i])
    if k % 2:
        zt = ("Z = \\tfrac12\\big(Z_{1,1}+Z_{1,C}+Z_{C,1}+Z_{C,C}\\big) = \\sum_{m\\neq 0\\ \\mathrm{pairs}} |\\Phi^l_{m}|^2 "
              "+ \\sum_{l\\ \\mathrm{even}}\\big(|\\Phi^{l,+}_0|^2+|\\Phi^{l,-}_0|^2\\big) "
              "+ \\sum_{y}\\big(|\\mathcal{T}^+_y|^2+|\\mathcal{T}^-_y|^2\\big)")
        desc = (f"Orbifold of the diagonal $\\mathbb{{Z}}_{{{k}}}$ parafermion theory by charge conjugation "
                f"$C: \\Phi^l_m\\to\\Phi^l_{{-m}}$ (Dijkgraaf-Vafa-Verlinde-Verlinde 1989). The untwisted sector keeps one "
                f"copy of each pair $\\{{(l,m),(l,-m)\\}}$ and the $C$-even parts of the {nfix} fixed fields $(l,0)$; "
                f"the twisted sector $Z_{{C,1}} = \\sum_y|\\mathcal{{T}}_y|^2$ is the Poisson resummation of "
                f"$Z_{{1,C}} = \\sum_l |t_l|^2$, projected to integer spin. Lightest twisted state: "
                f"$h = \\bar h = {F(k - 1, 16 * P.K)}$.")
        ctex = CHAR_TEX + f" Here $k = {k}$."
    else:
        zt = ("Z = \\tfrac12\\big(Z_{1,1}+Z_{1,g}+Z_{g,1}+Z_{g,g}\\big),\\quad Z_{1,g} = \\sum_{l\\ \\mathrm{even}}|t_l|^2"
              + (" + " if sigma == 1 else " - ") + "|t_f|^2,\\quad Z_{g,1} = \\sum_{y>0}|\\mathcal{T}_y|^2 + "
              + ("|\\mathcal{T}_0|^2 + |\\tilde{\\mathcal{T}}_0|^2" if sigma == 1 else
                 "\\mathcal{T}_0\\overline{\\tilde{\\mathcal{T}}_0} + \\tilde{\\mathcal{T}}_0\\overline{\\mathcal{T}_0}"))
        desc = (f"Orbifold of the diagonal $\\mathbb{{Z}}_{{{k}}}$ parafermion theory by the reflection {gname} "
                f"(Dijkgraaf-Vafa-Verlinde-Verlinde 1989). For even $k$ the dihedral reflections form two classes, $C$ and "
                f"$Cr$; they act alike on the fields $(l,0)$ and differ by a sign on the fixed field $({k // 2},\\pm{k // 2})$, "
                f"where the rotation $r$ is $-1$. Here that sign is "
                + ("$+1$" if sigma == 1 else "$-1$") +
                f": the untwisted sector pairs $\\Phi^{{{k // 2},\\pm}}_{{{k // 2}}}$ "
                + ("diagonally" if sigma == 1 else f"with $\\Phi^{{{k // 2},\\mp}}_{{{k // 2}}}$") +
                ", and the twisted sector, from Poisson resummation of $Z_{1,g}$, pairs $\\mathcal{T}_0$ "
                + ("with itself" if sigma == 1 else "with $\\tilde{\\mathcal{T}}_0$") +
                "; both sectors are projected to integer spin.")
        ctex = CHAR_TEX + CHAR_TEX_EVEN + f" Here $k = {k}$."
    spec = {
        "theory": theory, "c": str(P.c),
        "chiral_algebra": f"\\mathrm{{PF}}_{{{k}}}^{{C}}",
        "irreducible": True,
        "Z_tex": zt, "character_tex": ctex, "description": desc,
        "generator": GEN, "blocks": blocks, "Z": Z}
    p = write_spectrum(spec)
    print("wrote", p.relative_to(ROOT))
    return spec


def sym2_tim(H):
    """Expansion {(h, hbar): n} of Sym^2(TIM) = 1/2 [Z(tau)^2 + Z(2 tau) + Z(tau/2) + Z((tau+1)/2)]
    for h, hbar <= H, from the Rocha-Caridi characters of M(4,5) (diagonal invariant)."""
    from rcft import minimal_fields
    c = F(7, 10)
    L = 2 * H + 1                       # Z(tau/2) needs TIM states up to weight 2H
    chars = {f.label: f for f in minimal_fields(4, L).values()}
    D1: dict = {}
    for f in chars.values():
        terms = [(e + c / 24, a) for e, a in f.char.c.items() if e + c / 24 <= L]
        for h1, a in terms:
            for h2, b in terms:
                D1[(h1, h2)] = D1.get((h1, h2), 0) + a * b
    out: dict = {}

    def add(key, v):
        if key[0] <= H and key[1] <= H:
            out[key] = out.get(key, 0) + v

    small = [(k, v) for k, v in D1.items() if k[0] <= H and k[1] <= H]
    for (a, b), x in small:
        for (a2, b2), y in small:
            add((a + a2, b + b2), F(x * y, 2))
        add((2 * a, 2 * b), F(x, 2))
    for (a, b), x in D1.items():
        # q^{(h - c/24)/2} = q^{h' - 2c/24}:  h' = h/2 + c/16
        if (a - b) % 2 == 0:
            add((a / 2 + c / 16, b / 2 + c / 16), x)
    return {k: v for k, v in out.items() if v}


def reflection_class_c():
    """Which sign of |t_f|^2 in Z_{1,g} of PF_8 is the class C, i.e. gives PF_8/C = Sym^2(TIM)."""
    from zoo_spectrum import expand
    P = PF(8)
    target = None
    found = []
    for sigma in (1, -1):
        blocks, Z = P.orbifold(sigma)
        D, H = expand({"c": str(P.c), "blocks": blocks, "Z": Z})
        if target is None:
            target = sym2_tim(H)
        if {k: v for k, v in D.items() if k[0] <= H and k[1] <= H} == target:
            found.append(sigma)
    assert len(found) == 1, f"PF_8/C = Sym^2(TIM) singles out {found}"
    return found[0]


def main():
    for k in (5, 7, 9):
        write(PF(k), f"pf{k}-c", 1, "$C$")
    sigma_c = reflection_class_c()
    print(f"PF_8: the class C (PF_8/C = Sym^2(TIM)) has sign {sigma_c:+d}; Cr has {-sigma_c:+d}")
    write(PF(8), "pf8-cr", -sigma_c, "$Cr$")


if __name__ == "__main__":
    main()
