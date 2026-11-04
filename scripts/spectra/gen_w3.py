#!/usr/bin/env python3
"""Spectra of the unitary W_3 minimal models W_3(p, p+1) = SU(3)_{p-3} x SU(3)_1 / SU(3)_{p-2}
(diagonal invariant, p = 4..11), the partial conjugation invariant C_a of W_3(6,7), and the
orbifolds by charge conjugation C: W -> -W of W_3(5,6), W_3(6,7) and W_3(6,7)^{C_a}.

    python scripts/spectra/gen_w3.py

Characters (Frenkel-Kac-Wakimoto / Fateev-Lukyanov), with p' = p + 1, lambda a level-(p-3)
and mu a level-(p-2) SU(3) weight:

    chi_{lambda;mu} = eta^{-2} sum_{w in W} eps(w) sum_{alpha in Q} q^{|p'(lambda+rho) - p w(mu+rho) + p p' alpha|^2 / (2 p p')}.

Fields are pairs modulo the simultaneous Z_3 rotation (lambda; mu) ~ (sigma lambda; sigma mu).

C maps (lambda; mu) -> (lambda*; mu*). On a self-conjugate field (lambda + rho = a rho,
mu + rho = b rho) only w = 1, w_0 and alpha in Z rho survive in the twined trace:

    t_{a,b} = sum_n [q^{(p'a - p b + p p' n)^2/(p p')} - q^{(p'a + p b + p p' n)^2/(p p')}] / eta(2 tau),

and the twisted sector follows by Poisson resummation (scripts/spectra/corbifold.py).
"""

from __future__ import annotations

import math
from fractions import Fraction as F

from common import ROOT, Series, write_spectrum
from corbifold import (Builder, add_twisted, add_untwisted, inv_eta_2tau, inv_eta_half,
                       ldl, theta_comb, twisted_form)
from zoo_spectrum import partitions

GEN = "scripts/spectra/gen_w3.py"
TOP = 8

# Weyl group of A_2 acting on Dynkin labels, with signs
_WEYL = (
    (lambda a, b: (a, b), 1),
    (lambda a, b: (-a, a + b), -1),
    (lambda a, b: (a + b, -b), -1),
    (lambda a, b: (-a - b, a), 1),
    (lambda a, b: (b, -a - b), 1),
    (lambda a, b: (-b, -a), -1),
)


def ip(x, y) -> F:
    """Inner product of A_2 weights in Dynkin labels (roots have length^2 2)."""
    return F(2 * x[0] * y[0] + x[0] * y[1] + x[1] * y[0] + 2 * x[1] * y[1], 3)


def weights(k):
    return [(a, b) for a in range(k + 1) for b in range(k + 1 - a)]


def sigma(w, k):
    """Z_3 outer automorphism (lambda_0, lambda_1, lambda_2) -> (lambda_2, lambda_0, lambda_1)."""
    return (k - w[0] - w[1], w[0])


def triality(w):
    return (w[0] + 2 * w[1]) % 3


def dual(w):
    return (w[1], w[0])


def _p2(n):
    p = partitions(n)
    return [sum(p[i] * p[j - i] for i in range(j + 1)) for j in range(n + 1)]


class W3:
    """W_3(p, p+1): field representatives, weights, characters, conjugation, twinings."""

    def __init__(self, p: int):
        self.p, self.pp = p, p + 1
        self.c = 2 - F(24, p * (p + 1))
        self.k1, self.k2 = p - 3, p - 2          # levels of lambda and mu
        # representative of each Z_3 orbit: triality 0 for the label whose level is not 0 mod 3
        self.fix_mu = (self.k1 % 3 == 0)
        reps = {self.rep(lam, mu) for lam in weights(self.k1) for mu in weights(self.k2)}
        self.fields: list[tuple] = sorted(reps, key=lambda f: (self._h(*f), f))
        self.index: dict[tuple, int] = {}
        for lam in weights(self.k1):
            for mu in weights(self.k2):
                self.index[(lam, mu)] = self.fields.index(self.rep(lam, mu))
        self.conj = [self.index[(dual(l), dual(m))] for l, m in self.fields]
        self._chars: dict = {}

    def rep(self, lam, mu):
        for _ in range(3):
            if triality(mu if self.fix_mu else lam) == 0:
                return (lam, mu)
            lam, mu = sigma(lam, self.k1), sigma(mu, self.k2)
        raise AssertionError("no triality-zero representative")

    def _v(self, lam, mu, w=0):
        L = (lam[0] + 1, lam[1] + 1)
        M = _WEYL[w][0](mu[0] + 1, mu[1] + 1)
        return (self.pp * L[0] - self.p * M[0], self.pp * L[1] - self.p * M[1])

    def _h(self, lam, mu) -> F:
        v = self._v(lam, mu)
        return (ip(v, v) - 2) / (2 * self.p * self.pp)

    def h(self, i) -> F:
        return self._h(*self.fields[i])

    def label(self, i) -> str:
        """LaTeX name of field i, using the member of its Z_3 orbit with the smallest labels."""
        lam, mu = self.fields[i]
        orbit = []
        for _ in range(3):
            orbit.append((lam, mu))
            lam, mu = sigma(lam, self.k1), sigma(mu, self.k2)
        selfconj = lambda f: f[0] == dual(f[0]) and f[1] == dual(f[1])
        (a, b), (c, d) = min(orbit, key=lambda f: (not selfconj(f), sum(f[0]) + sum(f[1]), f[1], f[0]))
        return f"\\chi_{{({a},{b};{c},{d})}}"

    def top(self, i):
        """Absolute weight up to which the character of field i is kept: at least TOP and
        at least four levels above the primary."""
        h = self.h(i)
        return h + math.ceil(max(F(TOP), h + 4) - h)

    def char(self, i, top_weight=None) -> Series:
        """Exact up to absolute weight top_weight (default: self.top(i))."""
        tw = self.top(i) if top_weight is None else F(top_weight)
        key = (i, tw)
        if key in self._chars:
            return self._chars[key]
        lam, mu = self.fields[i]
        N = math.floor(tw - self.h(i))
        PP = self.p * self.pp
        v1 = self._v(lam, mu)
        E0 = ip(v1, v1) / (2 * PP)
        num = [0] * (N + 1)
        R = 6                               # |alpha| <= ~3.5 suffices (|v| < 1.7 p p')
        for w, (_, sgn) in enumerate(_WEYL):
            v = self._v(lam, mu, w)
            for x in range(-R, R + 1):
                for y in range(-R, R + 1):
                    al = (2 * x - y, -x + 2 * y)
                    u = (v[0] + PP * al[0], v[1] + PP * al[1])
                    e = ip(u, u) / (2 * PP) - E0
                    assert e.denominator == 1 and e >= 0
                    if e <= N:
                        assert max(abs(x), abs(y)) < R
                        num[int(e)] += sgn
        p2 = _p2(N)
        coeffs = [sum(num[j] * p2[n - j] for j in range(n + 1)) for n in range(N + 1)]
        assert coeffs[0] == 1 and min(coeffs) >= 0, (self.fields[i], coeffs)
        s = Series.from_list(self.h(i) - self.c / 24, coeffs)
        self._chars[key] = s
        return s

    # -- charge conjugation
    def self_conjugate(self):
        return [i for i in range(len(self.fields)) if self.conj[i] == i]

    def ab(self, i):
        (l1, l2), (m1, m2) = self.fields[i]
        assert l1 == l2 and m1 == m2
        return l1 + 1, m1 + 1

    def twining_f(self, i):
        """t_i = sum_m f(m) theta_{m, pp'} / eta(2 tau) (leading coefficient +1)."""
        a, b = self.ab(i)
        P, Q = self.p, self.pp
        return {2 * (Q * a - P * b): 1, 2 * (Q * a + P * b): -1}

    def twining(self, i, top_weight=None) -> Series:
        tw = self.top(i) if top_weight is None else F(top_weight)
        top = tw - self.c / 24
        M = self.p * self.pp
        s = theta_comb(self.twining_f(i), M, top + F(1, 12)) * inv_eta_2tau(top)
        s = s.truncate(top)
        assert s.c[min(s.c)] == 1 and min(s.c) == self.h(i) - self.c / 24
        return s

    def twisted(self, top_weight=TOP + 1):
        """C-twisted characters, Z_{C,1} = sum_r |T_r|^2, with
        T_r = eta(tau/2)^{-1} (sum_{x = r mod pp'} - sum_{x = r* mod pp'}) q^{x^2/4pp'},
        r* = r mod p, r* = -r mod p'. Returns [(r, r*, Series)], derived by Poisson resummation
        and checked against this closed form."""
        P, Q = self.p, self.pp
        M = P * Q
        H = twisted_form([(1, self.twining_f(i)) for i in self.self_conjugate()], M)
        top = F(top_weight) - self.c / 24
        cls = lambda m: min(m % (2 * M), (-m) % (2 * M))
        out = []
        for d, w in ldl(H, list(range(M + 1))):
            if d != 1 or any(x.denominator != 1 for x in w.values()):
                raise ValueError(f"W3({P},{Q}): twisted sector does not split into characters")
            r = min(w)
            rs = next(x for x in range(M) if (x - r) % P == 0 and (x + r) % Q == 0)
            closed: dict = {}
            for x, a in ((r, 1), (r + M, 1), (rs, -1), (rs + M, -1)):
                closed[cls(x)] = closed.get(cls(x), 0) + a
            assert w == {m: a for m, a in closed.items() if a}, (r, w, closed)
            ser = (theta_comb({m: int(a) for m, a in w.items()}, M, top + F(1, 48)) * inv_eta_half(top)).truncate(top)
            assert min(ser.c) + self.c / 24 == F(1, 16) + F(r * r - 4, 4 * M)
            out.append((r, rs, ser))
        assert len(out) == len(self.self_conjugate())
        return out


# ------------------------------------------------------------- invariants

def diag_summands(W: W3):
    return [(i, i) for i in range(len(W.fields))]


def ca_summands(W: W3):
    """Partial conjugation C_a: conjugate the level-(p-3) label only, in triality-zero (mu)
    representatives (needs p - 3 = 0 mod 3)."""
    assert W.fix_mu
    return [(i, W.index[(dual(l), m)]) for i, (l, m) in enumerate(W.fields)]


# ------------------------------------------------------------- output

CHAR_TEX = ("Frenkel-Kac-Wakimoto characters $\\chi_{(\\lambda;\\mu)} = \\eta(\\tau)^{-2}\\sum_{w\\in W(A_2)}"
            "\\epsilon(w)\\sum_{\\alpha\\in Q} q^{|p'(\\lambda+\\rho)-p\\,w(\\mu+\\rho)+pp'\\alpha|^2/2pp'}$, "
            "$p'=p+1$, with $\\lambda = (\\lambda_1,\\lambda_2)$ a level-$(p-3)$ and $\\mu = (\\mu_1,\\mu_2)$ a "
            "level-$(p-2)$ $SU(3)$ weight in Dynkin labels, $(\\lambda;\\mu)\\sim(\\sigma\\lambda;\\sigma\\mu)$ "
            "under the $\\mathbb{Z}_3$ rotation of affine Dynkin labels; "
            "$h = \\frac{|p'(\\lambda+\\rho)-p(\\mu+\\rho)|^2-|\\rho|^2}{2pp'}$.")

ORB_CHAR_TEX = (CHAR_TEX + " On a self-conjugate field ($\\lambda+\\rho = a\\rho$, $\\mu+\\rho = b\\rho$) the "
                "$C$-twined character is $t_{a,b} = \\eta(2\\tau)^{-1}\\sum_{n\\in\\mathbb{Z}}\\big(q^{(p'a-pb+pp'n)^2/pp'}"
                "-q^{(p'a+pb+pp'n)^2/pp'}\\big)$ and $\\chi^{\\pm} = \\frac12(\\chi\\pm t_{a,b})$. Twisted characters "
                "(Poisson resummation of $t_{a,b}$): $\\mathcal{T}_r = \\eta(\\tau/2)^{-1}\\big(\\sum_{x\\equiv r\\ (pp')}"
                "-\\sum_{x\\equiv r^*\\ (pp')}\\big)\\,q^{x^2/4pp'}$ with $r^*\\equiv r$ mod $p$, $r^*\\equiv -r$ mod $p'$, "
                "of weight $h_r = \\frac1{16}+\\frac{r^2-4}{4pp'}$; $\\mathcal{T}^{\\pm}_r$ are its parts with $L_0-h_r$ "
                "in $\\mathbb{Z}$ and $\\mathbb{Z}+\\frac12$.")


def write_diag(W: W3, theory: str, member=None):
    B = Builder(W.c)
    for i in range(len(W.fields)):
        a = B.block(i, W.label(i), W.char(i))
        B.add(a, a)
    blocks, Z = B.result()
    spec = {"theory": theory}
    if member:
        spec["member"] = member
    spec.update({
        "c": str(W.c),
        "chiral_algebra": f"\\mathcal{{W}}_3({W.p},{W.pp})",
        "irreducible": True,
        "Z_tex": "Z = \\sum_{(\\lambda;\\mu)/\\mathbb{Z}_3} |\\chi_{(\\lambda;\\mu)}|^2",
        "character_tex": CHAR_TEX + f" Here $p = {W.p}$.",
        "description": (f"Diagonal modular invariant of the $\\mathcal{{W}}_3({W.p},{W.pp})$ minimal model "
                        f"$SU(3)_{{{W.k1}}}\\times SU(3)_1/SU(3)_{{{W.k2}}}$ (Fateev-Zamolodchikov 1987; "
                        f"Fateev-Lukyanov 1988): {len(W.fields)} $\\mathcal{{W}}_3$ primaries, characters from the "
                        f"Frenkel-Kac-Wakimoto formula."),
        "generator": GEN, "blocks": blocks, "Z": Z})
    p = write_spectrum(spec)
    print("wrote", p.relative_to(ROOT))
    return spec


def write_ca(W: W3, theory: str):
    B = Builder(W.c)
    for i, j in ca_summands(W):
        a = B.block(i, W.label(i), W.char(i))
        b = B.block(j, W.label(j), W.char(j))
        B.add(a, b)
    blocks, Z = B.result()
    spec = {
        "theory": theory, "c": str(W.c),
        "chiral_algebra": f"\\mathcal{{W}}_3({W.p},{W.pp})",
        "irreducible": True,
        "Z_tex": "Z = \\sum_{(\\lambda;\\mu),\\ t(\\mu)=0} \\chi_{(\\lambda;\\mu)}\\,\\overline{\\chi_{(\\lambda^*;\\mu)}}",
        "character_tex": CHAR_TEX + f" Here $p = {W.p}$.",
        "description": (f"Partial charge-conjugation invariant $C_a$ of $\\mathcal{{W}}_3({W.p},{W.pp}) = "
                        f"SU(3)_{{{W.k1}}}\\times SU(3)_1/SU(3)_{{{W.k2}}}$ in the Beltaos-Gannon classification: "
                        f"each field is written with its level-{W.k2} label $\\mu$ of triality zero, and only the "
                        f"level-{W.k1} label is conjugated, $(\\lambda;\\mu)\\mapsto(\\lambda^*;\\mu)$."),
        "generator": GEN, "blocks": blocks, "Z": Z}
    p = write_spectrum(spec)
    print("wrote", p.relative_to(ROOT))
    return spec


def c_orbifold(W: W3, summands):
    """Blocks and Z of the C-orbifold of the theory sum_{(i,j)} chi_i chi_j-bar (C acting with
    eigenvalue +1 on every fixed primary)."""
    B = Builder(W.c)
    add_untwisted(B, summands, W.conj, W.char, W.label, twining=W.twining)
    tw = W.twisted()
    chars = [(f"\\mathcal{{T}}_{{{r}}}", ser) for r, _, ser in tw]
    add_twisted(B, chars, {(j, j): 1 for j in range(len(chars))})
    return B, tw


def write_orbifold(W: W3, theory: str, summands, base: str, base_tex: str):
    B, tw = c_orbifold(W, summands)
    blocks, Z = B.result()
    rr = ", ".join(f"({r},{rs})" for r, rs, _ in tw)
    spec = {
        "theory": theory, "c": str(W.c),
        "chiral_algebra": f"\\mathcal{{W}}_3({W.p},{W.pp})^{{C}}",
        "irreducible": True,
        "Z_tex": (f"Z = \\tfrac12\\big(Z_{{1,1}}+Z_{{1,C}}+Z_{{C,1}}+Z_{{C,C}}\\big) = "
                  f"\\sum_{{C\\text{{-orbits}}}} {base_tex} + \\sum_{{\\text{{fixed}}}}\\big(|\\chi^+|^2+|\\chi^-|^2\\big)"
                  f" + \\sum_r \\big(|\\mathcal{{T}}^+_r|^2+|\\mathcal{{T}}^-_r|^2\\big)"),
        "character_tex": ORB_CHAR_TEX + f" Here $p = {W.p}$ and $(r,r^*) \\in \\{{{rr}\\}}$.",
        "description": (f"Orbifold of {base} by charge conjugation $C: W\\to -W$, $(\\lambda;\\mu)\\mapsto"
                        f"(\\lambda^*;\\mu^*)$ (Dijkgraaf-Vafa-Verlinde-Verlinde 1989). The untwisted sector keeps one "
                        f"copy of each $C$-orbit of terms and the $C$-even parts of the "
                        f"{len(W.self_conjugate())} terms on self-conjugate fields ($C = +1$ on their primaries, the "
                        f"only choice whose twisted sector has non-negative integer multiplicities and spins in "
                        f"$\\frac12\\mathbb{{Z}}$); the twisted sector $\\sum_r|\\mathcal{{T}}_r|^2$ is the Poisson "
                        f"resummation of $Z_{{1,C}} = \\sum|t_{{a,b}}|^2$, projected to integer spin."),
        "generator": GEN, "blocks": blocks, "Z": Z}
    p = write_spectrum(spec)
    print("wrote", p.relative_to(ROOT))
    return spec


def main():
    models = {}
    for p in range(4, 12):
        W = W3(p)
        models[p] = W
        write_diag(W, "w3-minimal-models", {"at": p})
    write_diag(models[5], "w3-5-6")
    write_diag(models[6], "w3-6-7")
    W5, W6 = models[5], models[6]
    write_orbifold(W5, "w3-5-6-c", diag_summands(W5), "$\\mathcal{W}_3(5,6)$",
                   "|\\chi_{(\\lambda;\\mu)}|^2")
    write_orbifold(W6, "w3-6-7-c", diag_summands(W6), "$\\mathcal{W}_3(6,7)$",
                   "|\\chi_{(\\lambda;\\mu)}|^2")
    write_ca(W6, "w3-6-7-ca")
    write_orbifold(W6, "w3-6-7-ca-c", ca_summands(W6), "$\\mathcal{W}_3(6,7)^{C_a}$",
                   "\\chi_{(\\lambda;\\mu)}\\overline{\\chi_{(\\lambda^*;\\mu)}}")


if __name__ == "__main__":
    main()
