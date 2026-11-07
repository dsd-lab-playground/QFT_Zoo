#!/usr/bin/env python3
"""Spectra of WZW models G_k with the diagonal invariant (entry wzw-models):

    SU(3)_1, SU(3)_2, SU(4)_1, SO(5)_1, (G_2)_1, SO(8)_1, (F_4)_1, (E_6)_1, (E_7)_1, (E_8)_1.

Characters are the Weyl-Kac formula in its theta-function form (Kac-Peterson 1984; see e.g.
Walton, hep-th/9911187, eq. (4.69)) specialised to z = 0: by l'Hopital in z, the finite
Weyl-group sum turns into the Weyl dimension factor, and the Macdonald identity turns the
denominator into prod (alpha, rho) eta^{dim G}:

    chi_lam(q) = eta(q)^{-dim G} sum_{beta in Q^vee} D(lam + rho + K beta) q^{|lam + rho + K beta|^2 / 2K},
    D(mu)      = prod_{alpha > 0} (alpha, mu) / (alpha, rho),        K = k + h^vee,

long roots of length^2 2. D(mu) = eps(w) dim(nu) if w(mu) = nu + rho is strictly dominant and
0 if mu is singular, so every term is an integer. Equivalently

    chi_lam(q) = q^{h_lam - c/24} sum_{beta} D(lam + rho + K beta) q^{(lam + rho, beta) + K|beta|^2/2}
                 / prod_{n >= 1} (1 - q^n)^{dim G}.

All arithmetic is exact (Python integers); floating point only bounds the lattice search,
and every point found is re-checked exactly.

    python scripts/spectra/gen_wzw.py              # self-tests, then write the 10 files
    python scripts/spectra/gen_wzw.py --selftest   # self-tests only

Self-tests (independent code paths):
  * Macdonald identity: the level-0 vacuum numerator equals prod (1 - q^n)^{dim G};
  * leading term dim(lam) q^{h - c/24} with h = (lam, lam + 2 rho) / 2K; weight-1 space of the vacuum
    module = dim G; all coefficients non-negative;
  * simply-laced level 1 (SU(3), SU(4), SO(8), E_6, E_7, E_8): chi_lam = Theta_{lam + Q} / eta^r,
    the theta series summed directly over the root lattice (Frenkel-Kac, Segal);
  * (E_8)_1 vacuum = E_4 / eta^8 with E_4 = 1 + 240 sum sigma_3(n) q^n;
  * SO(5)_1, SO(6)_1 = SU(4)_1, SO(8)_1: free-fermion characters
    (theta_3^{N/2} +- theta_4^{N/2}) / 2 eta^{N/2} and theta_2^{N/2} / (sqrt2 or 2) eta^{N/2};
  * (G_2)_1 x (F_4)_1 in (E_8)_1: chi_1 chi_1 + chi_7 chi_26 = chi_1^{E_8}; likewise the pairs
    SU(3)_1 x (E_6)_1 and SO(8)_1 x SO(8)_1 (Mukhi-Poddar, arXiv:2011.09487, eq. (1.2));
  * SU(3)_1 x SU(3)_1 = SU(3)_2 x (3-state Potts W_3): every product chi_a chi_b of level-1
    characters equals sum_c b_{ab}^c chi_c^{(2)} with b the Rocha-Caridi W_3 characters at c = 4/5.
"""

from __future__ import annotations

import math
import sys
import time
from fractions import Fraction as F

import numpy as np

from common import Series, block, qpoch, write_spectrum
from exceptional_lie import A, E7, E8, G2, Lie, _chain_cartan, ball_points

GEN = "scripts/spectra/gen_wzw.py"
TOP = 12         # every block is given up to this conformal weight
THEORY = "wzw-models"


# ------------------------------------------------------------- the algebras

def B2():
    """so(5) = sp(4): node 1 long (vector 5 = omega_1), node 2 short (spinor 4 = omega_2)."""
    return Lie("B2", [[2, -1], [-2, 2]], d=[1, F(1, 2)])


def D4():
    """so(8), Bourbaki labels: node 2 central; omega_1 = 8_v, omega_3 = 8_s, omega_4 = 8_c."""
    return Lie("D4", _chain_cartan(4, [(1, 2), (2, 3), (2, 4)]))


def E6():
    """Bourbaki labels: 1-3-4-5-6 with 2 attached to 4; omega_1 = 27, omega_6 = 27bar."""
    return Lie("E6", _chain_cartan(6, [(1, 3), (3, 4), (4, 5), (5, 6), (2, 4)]))


def F4():
    """Bourbaki labels: nodes 1, 2 long, 3, 4 short; omega_4 = 26."""
    return Lie("F4", [[2, -1, 0, 0], [-1, 2, -1, 0], [0, -2, 2, -1], [0, 0, -1, 2]],
               d=[1, 1, F(1, 2), F(1, 2)])


def bold(s):
    return f"\\mathbf{{{s}}}"


def bar(s):
    return f"\\bar{{\\mathbf{{{s}}}}}"


# member at-string, algebra, level, chiral algebra (LaTeX), {Dynkin label: (irrep label, dim)}, c, gap
MEMBERS = [
    ("SU(3)_1", A(2), 1, "\\widehat{\\mathfrak{su}}(3)_1",
     {(0, 0): (bold(1), 1), (1, 0): (bold(3), 3), (0, 1): (bar(3), 3)}, F(2), F(2, 3)),
    ("SU(3)_2", A(2), 2, "\\widehat{\\mathfrak{su}}(3)_2",
     {(0, 0): (bold(1), 1), (1, 0): (bold(3), 3), (0, 1): (bar(3), 3),
      (2, 0): (bold(6), 6), (0, 2): (bar(6), 6), (1, 1): (bold(8), 8)}, F(16, 5), F(8, 15)),
    ("SU(4)_1", A(3), 1, "\\widehat{\\mathfrak{su}}(4)_1",
     {(0, 0, 0): (bold(1), 1), (1, 0, 0): (bold(4), 4), (0, 1, 0): (bold(6), 6),
      (0, 0, 1): (bar(4), 4)}, F(3), F(3, 4)),
    ("SO(5)_1", B2(), 1, "\\widehat{\\mathfrak{so}}(5)_1",
     {(0, 0): (bold(1), 1), (1, 0): (bold(5), 5), (0, 1): (bold(4), 4)}, F(5, 2), F(5, 8)),
    ("(G_2)_1", G2(), 1, "(\\widehat{\\mathfrak{g}}_2)_1",
     {(0, 0): (bold(1), 1), (1, 0): (bold(7), 7)}, F(14, 5), F(4, 5)),
    ("SO(8)_1", D4(), 1, "\\widehat{\\mathfrak{so}}(8)_1",
     {(0, 0, 0, 0): (bold(1), 1), (1, 0, 0, 0): (bold("8_v"), 8), (0, 0, 1, 0): (bold("8_s"), 8),
      (0, 0, 0, 1): (bold("8_c"), 8)}, F(4), F(1)),
    ("(F_4)_1", F4(), 1, "(\\widehat{\\mathfrak{f}}_4)_1",
     {(0, 0, 0, 0): (bold(1), 1), (0, 0, 0, 1): (bold(26), 26)}, F(26, 5), F(1)),
    ("(E_6)_1", E6(), 1, "(\\widehat{\\mathfrak{e}}_6)_1",
     {(0,) * 6: (bold(1), 1), (1, 0, 0, 0, 0, 0): (bold(27), 27), (0, 0, 0, 0, 0, 1): (bar(27), 27)},
     F(6), F(1)),
    ("(E_7)_1", E7(), 1, "(\\widehat{\\mathfrak{e}}_7)_1",
     {(0,) * 7: (bold(1), 1), (0, 0, 0, 0, 0, 0, 1): (bold(56), 56)}, F(7), F(1)),
    ("(E_8)_1", E8(), 1, "(\\widehat{\\mathfrak{e}}_8)_1",
     {(0,) * 8: (bold(1), 1)}, F(8), F(1)),
]


NAMES = {"A2": "SU(3)", "A3": "SU(4)", "B2": "SO(5)", "G2": "G_2", "D4": "SO(8)", "F4": "F_4",
         "E6": "E_6", "E7": "E_7", "E8": "E_8"}

_E8PAIR = "with the partner level-1 theory, $\\sum_i \\chi_i\\tilde\\chi_i = \\chi^{(E_8)_1}$ "
CHECKS = {
    "SU(3)_1": ("$A_2$ root-lattice theta functions $\\Theta_{\\lambda+Q}/\\eta^2$; " + _E8PAIR
                + "for $SU(3)_1\\times(E_6)_1$; every product of two $SU(3)_1$ characters equals "
                "$\\sum_c b^c_{ab}\\chi^{SU(3)_2}_c$ with $b$ the 3-state Potts $\\mathcal{W}_3$ characters"),
    "SU(3)_2": ("every product of two $SU(3)_1$ characters equals $\\sum_c b^c_{ab}\\chi^{SU(3)_2}_c$ with $b$ the "
                "3-state Potts $\\mathcal{W}_3$ (Rocha-Caridi) characters at $c = 4/5$ (the coset "
                "$SU(3)_1\\times SU(3)_1/SU(3)_2$)"),
    "SU(4)_1": ("$A_3$ root-lattice theta functions $\\Theta_{\\lambda+Q}/\\eta^3$, and the $SO(6)_1$ characters of six "
                "Majorana fermions, $(\\theta_3^3\\pm\\theta_4^3)/2\\eta^3$ and $\\theta_2^3/2\\eta^3$"),
    "SO(5)_1": ("the characters of five Majorana fermions, $(\\theta_3^{5/2}\\pm\\theta_4^{5/2})/2\\eta^{5/2}$ "
                "($\\mathbf{1}$, $\\mathbf{5}$) and $\\theta_2^{5/2}/\\sqrt2\\,\\eta^{5/2}$ ($\\mathbf{4}$)"),
    "(G_2)_1": "the conformal embedding $(G_2)_1\\times(F_4)_1\\subset(E_8)_1$: "
               "$\\chi_{\\mathbf{1}}\\chi_{\\mathbf{1}} + \\chi_{\\mathbf{7}}\\chi_{\\mathbf{26}} = \\chi^{(E_8)_1}$",
    "SO(8)_1": ("$D_4$ root-lattice theta functions $\\Theta_{\\lambda+Q}/\\eta^4$; the characters of eight Majorana "
                "fermions, $(\\theta_3^4\\pm\\theta_4^4)/2\\eta^4$ and $\\theta_2^4/2\\eta^4$; "
                "$\\chi_{\\mathbf{1}}^2 + \\chi_{\\mathbf{8_v}}^2 + 2\\chi_{\\mathbf{8_s}}\\chi_{\\mathbf{8_c}} = \\chi^{(E_8)_1}$"),
    "(F_4)_1": "the conformal embedding $(G_2)_1\\times(F_4)_1\\subset(E_8)_1$: "
               "$\\chi_{\\mathbf{1}}\\chi_{\\mathbf{1}} + \\chi_{\\mathbf{7}}\\chi_{\\mathbf{26}} = \\chi^{(E_8)_1}$",
    "(E_6)_1": "$E_6$ root-lattice theta functions $\\Theta_{\\lambda+Q}/\\eta^6$; " + _E8PAIR + "for $SU(3)_1\\times(E_6)_1$",
    "(E_7)_1": "$E_7$ root-lattice theta functions $\\Theta_{\\lambda+Q}/\\eta^7$",
    "(E_8)_1": ("the $E_8$ lattice theta function over $\\eta^8$, and $E_4/\\eta^8$ with "
                "$E_4 = 1 + 240\\sum_n\\sigma_3(n)q^n$; the cube of the character is $j(\\tau) = q^{-1} + 744 + 196884q + \\dots$"),
}


# ------------------------------------------------------------- Weyl-Kac at z = 0

def dimG(L: Lie) -> int:
    return L.r + len(L.roots)


def inv_phi_power(r: int, N: int) -> list[int]:
    """Coefficients of prod_{n>=1} (1 - q^n)^{-r} up to q^N."""
    out = [1] + [0] * N
    for _ in range(r):
        for n in range(1, N + 1):
            for m in range(n, N + 1):
                out[m] += out[m - n]
    return out


def mul(a: list[int], b: list[int]) -> list[int]:
    N = min(len(a), len(b))
    return [sum(a[i] * b[n - i] for i in range(n + 1)) for n in range(N)]


class WeylKac:
    """z = 0 Weyl-Kac numerators and characters of the affine algebra of L."""

    def __init__(self, L: Lie):
        self.L = L
        r = L.r
        self.dim = dimG(L)
        self.FintL = [[int(x) for x in row] for row in L.Fint.tolist()]       # den * (omega_i, omega_j)
        self.pos = [tuple(a) for a in L.positive]
        # (alpha, mu) * den = sum_j w_alpha[j] mu[j]
        self.w = [[sum(a[i] * self.FintL[i][j] for i in range(r)) for j in range(r)] for a in self.pos]
        self.rho = (1,) * r
        self.den_rho = math.prod(self._ipa(k, self.rho) for k in range(len(self.pos)))
        # coroot lattice: Gram (alpha_i^vee, alpha_j^vee) and Dynkin labels of the coroots
        self.cos = np.array(L.cosimple, dtype=np.int64)
        self.gram_v = np.array([[float(L.ip(L.cosimple[i], L.cosimple[j])) for j in range(r)]
                                for i in range(r)])

    def _ipa(self, k, mu) -> int:
        return sum(x * y for x, y in zip(self.w[k], mu))

    def D(self, mu) -> int:
        num = math.prod(self._ipa(k, mu) for k in range(len(self.pos)))
        q, rem = divmod(num, self.den_rho)
        assert rem == 0, "Weyl dimension factor is not an integer"
        return q

    def numerator(self, k: int, lam, N: int) -> list[int]:
        """sum_beta D(lam + rho + K beta) q^{g(beta)}, g = (lam+rho, beta) + K|beta|^2/2, for g <= N."""
        L, r = self.L, self.L.r
        K = k + L.hv
        lr = tuple(x + 1 for x in lam)
        n_lr = L.ip(lr, lr)
        # g = (K/2)|beta + lr/K|^2 - |lr|^2/(2K) <= N  <=>  |beta - center|^2 <= (2N + |lr|^2/K)/K,
        # center = -lr/K in coroot coordinates (= (omega_i, -lr)/K).
        center = np.array([-float(sum(L.Fm[i][j] * lr[j] for j in range(r))) / K for i in range(r)])
        R2 = float((2 * N + n_lr / K) / K)
        B = ball_points(self.gram_v, center, R2 * (1 + 1e-9) + 1e-9)
        num = [0] * (N + 1)
        for b in B.tolist():
            beta = [sum(b[i] * int(self.cos[i][j]) for i in range(r)) for j in range(r)]   # Dynkin labels
            g = L.ip(lr, beta) + F(K, 2) * L.ip(beta, beta)
            assert g.denominator == 1
            g = int(g)
            if g > N:
                continue
            assert g >= 0
            mu = tuple(lr[j] + K * beta[j] for j in range(r))
            num[g] += self.D(mu)
        return num

    def character(self, k: int, lam, N: int) -> list[int]:
        """q^{-(h - c/24)} chi_lam(q) up to q^N."""
        return mul(self.numerator(k, lam, N), inv_phi_power(self.dim, N))


def char_series(L: Lie, k: int, lam, coeffs) -> Series:
    c = L.c_wzw(k)
    return Series.from_list(L.h(k, lam) - c / 24, coeffs)


# ------------------------------------------------------------- independent references

def theta_coset(L: Lie, lam, N: int) -> list[int]:
    """Simply-laced: Theta_{lam+Q}(q) q^{-|lam|^2/2} = sum_{v in lam+Q} q^{(|v|^2 - |lam|^2)/2},
    summed directly over the root lattice (Gram = Cartan matrix), up to q^N."""
    r = L.r
    assert all(d == 1 for d in L.d), "simply-laced only"
    C = np.array(L.C, dtype=np.int64)
    lam_root = [sum(L.Cinv[i][j] * lam[j] for j in range(r)) for i in range(r)]   # lam in root coordinates
    den = math.lcm(*[x.denominator for x in lam_root])
    n_lam = L.ip(lam, lam)
    R2 = float(2 * N + n_lam)
    pts = ball_points(C.astype(float), np.array([-float(x) for x in lam_root]), R2 * (1 + 1e-9) + 1e-9)
    X = pts * den + np.array([int(x * den) for x in lam_root], dtype=np.int64)     # den * (lam + n)
    nv2 = np.einsum("ij,jk,ik->i", X, C, X)                                        # den^2 |v|^2
    e2 = nv2 - int(n_lam * den * den)                                              # den^2 (|v|^2 - |lam|^2)
    assert (e2 % (2 * den * den) == 0).all()
    e = e2 // (2 * den * den)
    assert e.min() >= 0
    out = [0] * (N + 1)
    for v, cnt in zip(*np.unique(e[e <= N], return_counts=True)):
        out[int(v)] = int(cnt)
    return out


def e4_over_eta8(N: int) -> list[int]:
    """q^{1/3} E_4(q) / eta(q)^8 with E_4 = 1 + 240 sum_n sigma_3(n) q^n."""
    e4 = [1] + [240 * sum(d ** 3 for d in range(1, n + 1) if n % d == 0) for n in range(1, N + 1)]
    return mul(e4, inv_phi_power(8, N))


def fermion_chars(n: int, top) -> dict[str, Series]:
    """SO(n)_1 from n Majorana fermions, absolute exponents, exact up to weight `top`:
    vac/vec = (theta_3^{n/2} +- theta_4^{n/2}) / 2 eta^{n/2},
    spinor  = theta_2^{n/2} / (sqrt2 eta^{n/2}) for n odd, theta_2^{n/2} / (2 eta^{n/2}) per spinor for n even."""
    c = F(n, 2)
    e = top - c / 24 + 1
    ns_p = qpoch(F(1, 2), 1, e, sign=1) ** n          # prod (1 + q^{m-1/2})^n
    ns_m = qpoch(F(1, 2), 1, e, sign=-1) ** n         # prod (1 - q^{m-1/2})^n
    r = qpoch(1, 1, e, sign=1) ** n                   # prod (1 + q^m)^n
    vac = ((ns_p + ns_m) * F(1, 2)).shift(-c / 24)
    vec = ((ns_p - ns_m) * F(1, 2)).shift(-c / 24)
    # theta_2/eta = 2 q^{1/12} prod (1+q^m)^2  =>  (theta_2/eta)^{n/2} = 2^{n/2} q^{n/24} prod (1+q^m)^n;
    # divided by sqrt2 (n odd) this is 2^{(n-1)/2}, divided by 2 (n even) it is 2^{n/2 - 1}
    norm = 2 ** ((n - 1) // 2) if n % 2 else 2 ** (n // 2 - 1)
    sp = (r * norm).shift(F(n, 24))
    return {"vac": vac, "vec": vec, "spinor": sp}


def same(a: Series, b: Series, top) -> bool:
    """a == b for every exponent <= top (both must be known exactly up to top)."""
    top = F(top)
    assert top <= min(a.top, b.top), "comparison beyond the known range"
    keys = {e for e in a.c if e <= top} | {e for e in b.c if e <= top}
    return all(a.coeff(e) == b.coeff(e) for e in keys)


# ------------------------------------------------------------- self-tests

def selftest(N=TOP + 1, verbose=True):
    from rcft import minimal_char
    t0 = time.time()
    log = []

    def say(msg):
        log.append(msg)
        if verbose:
            print("  " + msg + f"  ({time.time() - t0:.1f}s)")

    chars = {}       # (name, k, lam) -> Series (absolute exponents)
    algebras = {}
    for at, L, k, _, labels, c_plan, gap_plan in MEMBERS:
        wk = algebras.setdefault(L.name, WeylKac(L))
        # 1. Macdonald identity (level 0 vacuum)
        num0 = wk.numerator(0, (0,) * L.r, N)
        assert num0 == euler_power(wk.dim, N), f"{L.name}: Macdonald identity fails"
        # strange formula |rho|^2 / 2h = dim G / 24
        assert L.ip(L.rho, L.rho) / (2 * L.hv) == F(wk.dim, 24)
        # 2. central charge, integrable weights, leading terms
        c = L.c_wzw(k)
        assert c == c_plan, (at, c)
        assert sorted(L.integrable(k)) == sorted(labels), (at, L.integrable(k))
        hs = []
        for lam, (lab, d) in labels.items():
            co = wk.character(k, lam, N)
            assert co[0] == L.dim(lam) == d, (at, lam, co[0])
            assert min(co) >= 0, (at, lam)
            chars[(at, lam)] = char_series(L, k, lam, co)
            if lam != (0,) * L.r:
                hs.append(L.h(k, lam))
        vac = wk.character(k, (0,) * L.r, N)
        assert vac[0] == 1 and vac[1] == wk.dim, (at, vac[:3])
        gap = min([2 * h for h in hs] + [F(1)])
        assert gap == gap_plan, (at, gap)
        say(f"{at}: c = {c}, h^v = {L.hv}, dim G = {wk.dim}, weights {[str(x) for x in sorted(set(hs))]}, "
            f"gap min(2h, 1) = {gap}; Macdonald identity to q^{N}; vacuum q^1 coefficient = {vac[1]} = dim G")

    # 3. simply-laced level 1 = root-lattice theta functions over eta^r
    for at in ("SU(3)_1", "SU(4)_1", "SO(8)_1", "(E_6)_1", "(E_7)_1", "(E_8)_1"):
        _, L, k, _, labels, _, _ = next(m for m in MEMBERS if m[0] == at)
        for lam in labels:
            th = theta_coset(L, lam, N)
            lat = mul(th, inv_phi_power(L.r, N))
            assert L.h(1, lam) == L.ip(lam, lam) / 2
            got = chars[(at, lam)]
            e0 = L.h(1, lam) - L.c_wzw(1) / 24
            assert [got.coeff(e0 + n) for n in range(N + 1)] == lat, (at, lam)
        say(f"{at}: every character = Theta_(lam+Q)/eta^{L.r} (direct root-lattice sum) to q^{N}")

    # 4. E_8 vacuum = E_4/eta^8
    e8 = chars[("(E_8)_1", (0,) * 8)]
    co = [e8.coeff(F(-1, 3) + n) for n in range(N + 1)]
    assert co == e4_over_eta8(N)
    say(f"(E_8)_1: q^(1/3) chi = E_4/eta^8 = {co[:7]} ...")
    # j = chi^3 (q^{-1} + 744 + 196884 q + ...)
    j = (e8 ** 3)
    say(f"(E_8)_1: chi^3 = q^-1 + {j.coeff(0)} + {j.coeff(1)} q + {j.coeff(2)} q^2 + ... (j-function)")
    assert (j.coeff(-1), j.coeff(0), j.coeff(1), j.coeff(2)) == (1, 744, 196884, 21493760)

    # 5. free fermions: SO(5)_1, SO(6)_1 = SU(4)_1, SO(8)_1
    top = F(N) - 1
    f5 = fermion_chars(5, top)
    m = {"vac": (0, 0), "vec": (1, 0), "spinor": (0, 1)}
    for key, lam in m.items():
        assert same(chars[("SO(5)_1", lam)], f5[key], top - F(5, 48)), key
    f6 = fermion_chars(6, top)
    for key, lams in {"vac": [(0, 0, 0)], "vec": [(0, 1, 0)], "spinor": [(1, 0, 0), (0, 0, 1)]}.items():
        for lam in lams:
            assert same(chars[("SU(4)_1", lam)], f6[key], top - F(1, 8)), key
    f8 = fermion_chars(8, top)
    for key, lams in {"vac": [(0, 0, 0, 0)], "vec": [(1, 0, 0, 0)],
                      "spinor": [(0, 0, 1, 0), (0, 0, 0, 1)]}.items():
        for lam in lams:
            assert same(chars[("SO(8)_1", lam)], f8[key], top - F(1, 6)), key
    say("SO(5)_1, SU(4)_1 = SO(6)_1, SO(8)_1: characters = free-fermion theta quotients")

    # 6. (G_2)_1 x (F_4)_1 in (E_8)_1
    g0, g7 = chars[("(G_2)_1", (0, 0))], chars[("(G_2)_1", (1, 0))]
    f0, f26 = chars[("(F_4)_1", (0, 0, 0, 0))], chars[("(F_4)_1", (0, 0, 0, 1))]
    lhs = g0 * f0 + g7 * f26
    assert same(lhs, e8, N - 1 - F(1, 3)), "G2 x F4 != E8"
    say(f"(G_2)_1 x (F_4)_1: chi_1 chi_1 + chi_7 chi_26 = chi^(E_8) to q^{N - 1}")
    # the other level-1 pairs in this list: SU(3)_1 x (E_6)_1 and SO(8)_1 x SO(8)_1
    a = {lam: chars[("SU(3)_1", lam)] for lam in ((0, 0), (1, 0), (0, 1))}
    e6 = {lam: chars[("(E_6)_1", lam)] for lam in ((0,) * 6, (1, 0, 0, 0, 0, 0), (0, 0, 0, 0, 0, 1))}
    lhs = a[(0, 0)] * e6[(0,) * 6] + a[(1, 0)] * e6[(0, 0, 0, 0, 0, 1)] + a[(0, 1)] * e6[(1, 0, 0, 0, 0, 0)]
    assert same(lhs, e8, N - 1 - F(1, 3)), "A2 x E6 != E8"
    d = [chars[("SO(8)_1", lam)] for lam in ((0, 0, 0, 0), (1, 0, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))]
    assert same(d[0] * d[0] + d[1] * d[1] + d[2] * d[3] + d[3] * d[2], e8, N - 1 - F(1, 3)), "D4 x D4 != E8"
    say(f"SU(3)_1 x (E_6)_1 and SO(8)_1 x SO(8)_1: sum_i chi_i chi~_i = chi^(E_8) to q^{N - 1}")

    # 7. SU(3)_1 x SU(3)_1 = SU(3)_2 x Potts W_3
    W = {F(0): minimal_char(5, 6, 1, 1, N) + minimal_char(5, 6, 1, 5, N),
         F(2, 5): minimal_char(5, 6, 2, 1, N) + minimal_char(5, 6, 2, 5, N),
         F(1, 15): minimal_char(5, 6, 2, 3, N), F(2, 3): minimal_char(5, 6, 1, 3, N)}
    L = A(2)
    tri = lambda lam: (lam[0] + 2 * lam[1]) % 3      # noqa: E731
    lev1 = L.integrable(1)
    lev2 = L.integrable(2)
    for a in lev1:
        for b in lev1:
            lhs = chars[("SU(3)_1", a)] * chars[("SU(3)_1", b)]
            rhs = None
            for cc in lev2:
                if tri(cc) != (tri(a) + tri(b)) % 3:
                    continue
                hw = (L.h(1, a) + L.h(1, b) - L.h(2, cc)) % 1
                term = W[hw] * chars[("SU(3)_2", cc)]
                rhs = term if rhs is None else rhs + term
            cut = min(lhs.top, rhs.top) - 1
            assert same(lhs, rhs, cut), (a, b)
    say("SU(3)_1 x SU(3)_1: every product chi_a chi_b = sum_c (Potts W_3 char) chi_c^(2) of SU(3)_2")
    return chars, log


def euler_power(r: int, N: int) -> list[int]:
    """Coefficients of prod_{n>=1} (1 - q^n)^r up to q^N (Euler's pentagonal series, r-th power)."""
    e = [0] * (N + 1)
    j = 0
    while True:
        g1, g2 = j * (3 * j - 1) // 2, j * (3 * j + 1) // 2
        if g1 > N:
            break
        s = -1 if j % 2 else 1
        e[g1] = s
        if g2 <= N:
            e[g2] = s
        j += 1
    out = [1] + [0] * N
    for _ in range(r):
        out = mul(out, e)
    return out


# ------------------------------------------------------------- output

def spectrum(member):
    at, L, k, alg, labels, c, gap = member
    wk = WeylKac(L)
    N = int(TOP) + 1
    order = sorted(labels, key=lambda lam: (L.h(k, lam), list(labels).index(lam)))
    blocks = []
    for lam in order:
        co = wk.character(k, lam, N)
        lab, d = labels[lam]
        blocks.append(block(char_series(L, k, lam, co), c, f"\\chi_{{{lab}}}", TOP))
    Z = [[i, i, 1] for i in range(len(blocks))]
    ztex = "Z = " + " + ".join(f"|\\chi_{{{labels[lam][0]}}}|^2" for lam in order)
    weights = ", ".join(f"$h_{{{labels[lam][0]}}} = {_tex(L.h(k, lam))}$" for lam in order)
    g = NAMES[L.name]
    char_tex = ("Weyl-Kac characters at $z = 0$: $\\chi_\\lambda(q) = \\eta(q)^{-\\dim G}\\sum_{\\beta\\in Q^\\vee}"
                "\\prod_{\\alpha>0}\\frac{(\\alpha,\\lambda+\\rho+K\\beta)}{(\\alpha,\\rho)}\\,"
                "q^{|\\lambda+\\rho+K\\beta|^2/2K}$, $K = k + h^\\vee$, long roots of length$^2$ 2 "
                f"(here $\\dim G = {dimG(L)}$, $h^\\vee = {L.hv}$, $K = {k + L.hv}$). One block per integrable "
                f"highest weight, labelled by the ${g}$ irrep; {weights}.")
    desc = (f"Diagonal modular invariant of the ${g}$ WZW model at level {k}, $c = k\\dim G/(k+h^\\vee) = {_tex(c)}$. "
            "Characters from the Weyl-Kac formula specialised to $z=0$ (the finite Weyl sum becomes the Weyl "
            "dimension factor and the denominator becomes $\\eta^{\\dim G}$ by the Macdonald identity), "
            "summed exactly over the coroot lattice. The generator checks the Macdonald identity, "
            "the leading terms $\\dim\\lambda\\, q^{h_\\lambda-c/24}$ and that the weight-1 space of the vacuum "
            f"module has dimension $\\dim G = {dimG(L)}$, and compares with independent formulas: {CHECKS[at]}.")
    spec = {
        "theory": THEORY,
        "member": {"at": at},
        "c": str(c),
        "chiral_algebra": alg,
        "irreducible": True,
        "Z_tex": ztex,
        "character_tex": char_tex,
        "description": desc,
        "generator": GEN,
        "blocks": blocks,
        "Z": Z,
    }
    return spec


def _tex(x: F) -> str:
    x = F(x)
    return str(x.numerator) if x.denominator == 1 else f"\\tfrac{{{x.numerator}}}{{{x.denominator}}}"


def main(argv):
    t0 = time.time()
    print("self-tests:")
    selftest()
    if "--selftest" in argv:
        return 0
    for m in MEMBERS:
        p = write_spectrum(spectrum(m))
        print("wrote", p.relative_to(p.parents[2]))
    print(f"done ({time.time() - t0:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
