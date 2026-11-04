"""Affine characters of a simple Lie algebra specialised along the principal
SU(2) grading (input for coset branching functions via su2.decompose).

The principal SU(2) has J^3 = rho^vee, so a weight mu of g gets the grading
w = 2 J^3 = <mu, 2 rho^vee> = 2 * (sum of its simple-root coordinates).
Under e^mu -> z^<mu, 2 rho^vee> the Weyl-Kac formula becomes

    chi_Lambda(q, z) = q^(h - c/24) * Num(q, z) / (Dfin(z) * Daff(q, z)),

    Num  = sum_{beta in Q^vee} q^{(Lambda+rho, beta) + K |beta|^2 / 2}
              prod_{alpha > 0} (z^{(mu, alpha^vee)} - z^{-(mu, alpha^vee)}),   mu = Lambda + rho + K beta,
    Dfin = prod_{alpha > 0} (z^{(rho, alpha^vee)} - z^{-(rho, alpha^vee)}),
    Daff = prod_{n >= 1} (1 - q^n)^rank prod_{alpha in roots} (1 - q^n z^{<alpha, 2 rho^vee>}),

with K = k + h^vee: the finite Weyl-group sum is done in closed form by the
Weyl denominator identity of the dual root system. Num is divided exactly by
Dfin (Laurent polynomials in z, grade by grade) and then by Daff (power series
in q). All arithmetic is exact (Python integers).

The result is an `su2.Graded` (columns w = -su2.W..su2.W), so `su2.decompose`
gives the branching functions into SU(2)_{k * index}, index = 2 |rho^vee|^2.
"""

from __future__ import annotations

import itertools
import math
from fractions import Fraction as F

import numpy as np

import su2


def _inverse(M):
    n = len(M)
    A = [[F(M[i][j]) for j in range(n)] + [F(int(i == j)) for j in range(n)] for i in range(n)]
    for col in range(n):
        piv = next(r for r in range(col, n) if A[r][col] != 0)
        A[col], A[piv] = A[piv], A[col]
        pv = A[col][col]
        A[col] = [x / pv for x in A[col]]
        for r in range(n):
            if r != col and A[r][col] != 0:
                f = A[r][col]
                A[r] = [x - f * y for x, y in zip(A[r], A[col])]
    return [row[n:] for row in A]


class Algebra:
    """Simple Lie algebra from the Gram matrix B[i][j] = (alpha_i, alpha_j) of its
    simple roots, long roots of length^2 2. Weights are tuples of Dynkin labels."""

    def __init__(self, name: str, B):
        self.name = name
        self.B = [[F(x) for x in row] for row in B]
        r = self.rank = len(B)
        self.d = [self.B[i][i] / 2 for i in range(r)]                       # |alpha_i|^2 / 2
        # C[i][j] = (alpha_i, alpha_j^vee): row i = Dynkin labels of alpha_i
        self.C = [[2 * self.B[i][j] / self.B[j][j] for j in range(r)] for i in range(r)]
        assert all(x.denominator == 1 for row in self.C for x in row)
        self.Cinv = _inverse(self.C)
        # (omega_i, omega_j) = (C^-1)_{ij} d_j
        self.G = [[self.Cinv[i][j] * self.d[j] for j in range(r)] for i in range(r)]
        self.rho = tuple([1] * r)
        self.pos = self._positive_roots()
        self.dim = r + 2 * len(self.pos)
        self.theta = max(self.pos, key=lambda a: (self.height(a), a))
        assert self.ip(self.theta, self.theta) == 2
        self.hdual = int(self.ip(self.theta, self.rho)) + 1
        rho_v = [sum(self.coroot_coeffs(a)[i] for a in self.pos) / 2 for i in range(r)]   # rho^vee in coroot coords
        self.rho_vee_sq = sum(rho_v[i] * rho_v[j] * self.B[i][j] / (self.d[i] * self.d[j])
                              for i in range(r) for j in range(r))
        self.index = 2 * self.rho_vee_sq          # embedding index of the principal SU(2)

    # -- weights
    def ip(self, lam, mu) -> F:
        r = self.rank
        return sum(F(lam[i]) * self.G[i][j] * mu[j] for i in range(r) for j in range(r))

    def root_coords(self, lam):
        """simple-root coordinates c with lam = sum c_i alpha_i."""
        r = self.rank
        return [sum(F(lam[i]) * self.Cinv[i][j] for i in range(r)) for j in range(r)]

    def height(self, lam) -> F:
        return sum(self.root_coords(lam))

    def grading(self, lam) -> int:
        """<lam, 2 rho^vee>."""
        w = 2 * self.height(lam)
        assert w.denominator == 1
        return int(w)

    def coroot_coeffs(self, alpha):
        """alpha^vee = sum_i m_i alpha_i^vee."""
        c = self.root_coords(alpha)
        na = self.ip(alpha, alpha)
        return [c[i] * self.B[i][i] / na for i in range(self.rank)]

    def pair_coroot(self, mu, alpha) -> int:
        """(mu, alpha^vee) = 2 (mu, alpha) / (alpha, alpha)."""
        x = 2 * self.ip(mu, alpha) / self.ip(alpha, alpha)
        assert x.denominator == 1
        return int(x)

    def _positive_roots(self):
        r = self.rank
        simple = [tuple(int(x) for x in self.C[i]) for i in range(r)]
        roots = set(simple)
        frontier = list(simple)
        while frontier:
            new = []
            for lam in frontier:
                for j in range(r):
                    mu = tuple(lam[t] - lam[j] * int(self.C[j][t]) for t in range(r))
                    if mu not in roots:
                        roots.add(mu)
                        new.append(mu)
            frontier = new
        pos = [a for a in roots if all(x >= 0 for x in self.root_coords(a))]
        assert 2 * len(pos) == len(roots)
        return sorted(pos, key=lambda a: (self.height(a), a))

    # -- affine data
    def level(self, lam) -> int:
        return int(self.ip(lam, self.theta))

    def integrable(self, k: int):
        r = self.rank
        out = []
        for lam in itertools.product(range(k + 1), repeat=r):
            if self.level(lam) <= k:
                out.append(lam)
        return out

    def central_charge(self, k: int) -> F:
        return F(k * self.dim, k + self.hdual)

    def h(self, lam, k: int) -> F:
        two_rho_plus = tuple(lam[i] + 2 for i in range(self.rank))
        return self.ip(lam, two_rho_plus) / (2 * (k + self.hdual))

    def weyl_dim(self, lam) -> int:
        num = F(1)
        lr = tuple(lam[i] + 1 for i in range(self.rank))
        for a in self.pos:
            num *= self.ip(lr, a) / self.ip(self.rho, a)
        assert num.denominator == 1
        return int(num)


# ------------------------------------------------------------- the characters

def _mul_binomial(row: np.ndarray, m: int) -> np.ndarray:
    """row * (z^m - z^-m), m > 0, on an object array of z-coefficients (centre index = len // 2)."""
    assert m > 0
    n = len(row)
    assert not row[:m].any() and not row[n - m:].any(), "z-window too small"
    out = np.zeros_like(row)
    out[m:] = row[:n - m]
    out[:n - m] -= row[m:]
    return out


def _div_binomial(row: np.ndarray, m: int) -> np.ndarray:
    """Exact row / (z^m - z^-m), m > 0: g_{v} = f_{v+m} + g_{v+2m}."""
    n = len(row)
    g = np.zeros_like(row)
    for v in range(n - 1 - m, -1, -1):
        acc = row[v + m]
        if v + 2 * m < n:
            acc = acc + g[v + 2 * m]
        g[v] = acc
    assert not (_mul_binomial(g, m) - row).any(), "inexact division by the Weyl denominator"
    return g


def principal_character(L: Algebra, k: int, lam, N: int, WL: int = 600) -> su2.Graded:
    """chi_lam at level k in the principal grading, grades 0..N (exact)."""
    r = L.rank
    K = k + L.hdual
    assert L.level(lam) <= k
    lr = [lam[i] + 1 for i in range(r)]
    # coroot Gram matrix (alpha_i^vee, alpha_j^vee)
    Bv = [[L.B[i][j] / (L.d[i] * L.d[j]) for j in range(r)] for i in range(r)]
    emin = min(np.linalg.eigvalsh(np.array([[float(x) for x in row] for row in Bv])))
    lnorm = math.sqrt(float(sum(x * x for x in lr)))
    bound = int(math.ceil((lnorm + math.sqrt(lnorm ** 2 + 2 * K * emin * N)) / (K * emin))) + 1
    # alpha_i^vee in Dynkin labels: C[i] / d_i
    cor = [[L.C[i][j] / L.d[i] for j in range(r)] for i in range(r)]
    width = 2 * WL + 1
    num = np.zeros((N + 1, width), dtype=object)
    num[:] = 0
    for n in itertools.product(range(-bound, bound + 1), repeat=r):
        grade = sum(n[i] * lr[i] for i in range(r)) + F(K, 2) * sum(
            n[i] * n[j] * Bv[i][j] for i in range(r) for j in range(r))
        assert grade.denominator == 1
        if grade > N:
            continue
        assert grade >= 0
        mu = [lr[j] + K * sum(n[i] * cor[i][j] for i in range(r)) for j in range(r)]
        exps = [L.pair_coroot(mu, a) for a in L.pos]
        if 0 in exps:
            continue
        row = np.zeros(width, dtype=object)
        row[:] = 0
        sign = 1
        for e in exps:
            if e < 0:
                sign, e = -sign, -e
        row[WL] = sign
        for e in exps:
            row = _mul_binomial(row, abs(e))
        num[int(grade)] += row
    # exact division by the finite Weyl denominator
    for e in [L.pair_coroot(L.rho, a) for a in L.pos]:
        for g in range(N + 1):
            num[g] = _div_binomial(num[g], e)
    # division by the affine part, factor by factor: 1/(1 - q^n z^w)
    A = num
    ws = [0] * r + [L.grading(a) for a in L.pos] + [-L.grading(a) for a in L.pos]
    for n in range(1, N + 1):
        for w in ws:
            for lev in range(n, N + 1):
                src = A[lev - n]
                if w > 0:
                    assert not src[width - w:].any(), "z-window too small"
                    A[lev, w:] += src[:width - w]
                elif w < 0:
                    assert not src[:-w].any(), "z-window too small"
                    A[lev, :width + w] += src[-w:]
                else:
                    A[lev] += src
    # back to an su2.Graded with columns -W..W
    W = su2.W
    nz = [i - WL for g in range(N + 1) for i in np.nonzero(A[g])[0]]
    assert max(abs(x) for x in nz) <= W - 2, "su2.W too small for this character"
    assert min(int(x) for x in A.flat) >= 0, "negative character coefficient"
    big = max(int(x) for x in A.flat)
    assert big < 2 ** 62
    out = np.array(A[:, WL - W: WL + W + 1].tolist(), dtype=np.int64)
    c = L.central_charge(k)
    return su2.Graded(L.h(lam, k) - c / 24, out)


# ------------------------------------------------------------- algebras used here

def A(n: int) -> Algebra:
    B = [[2 if i == j else (-1 if abs(i - j) == 1 else 0) for j in range(n)] for i in range(n)]
    return Algebra(f"A{n}", B)


def B2() -> Algebra:
    """so(5): alpha_1 = e1 - e2 (long), alpha_2 = e2 (short)."""
    return Algebra("B2", [[2, -1], [-1, 1]])


def C(n: int) -> Algebra:
    """sp(2n): alpha_i = e_i - e_{i+1} (short, length^2 1), alpha_n = 2 e_n (long)."""
    B = [[F(0)] * n for _ in range(n)]
    for i in range(n - 1):
        B[i][i] = F(1)
        if i + 1 < n - 1:
            B[i][i + 1] = B[i + 1][i] = F(-1, 2)
    B[n - 1][n - 1] = F(2)
    if n >= 2:
        B[n - 2][n - 1] = B[n - 1][n - 2] = F(-1)
    return Algebra(f"C{n}", B)


# ------------------------------------------------------------- numerical S matrix

def weyl_orbit_signed(L: Algebra, lam):
    """[(sign, w(lam))] over the finite Weyl group, for a regular weight lam."""
    r = L.rank
    seen = {tuple(lam): 1}
    frontier = [tuple(lam)]
    while frontier:
        new = []
        for mu in frontier:
            for j in range(r):
                nu = tuple(mu[t] - mu[j] * int(L.C[j][t]) for t in range(r))
                if nu not in seen:
                    seen[nu] = -seen[mu]
                    new.append(nu)
        frontier = new
    return [(s, mu) for mu, s in seen.items()]


def kac_peterson_S(L: Algebra, k: int, weights):
    """Unitary S matrix (rows/cols in the order of `weights`), normalised with S_00 > 0."""
    K = k + L.hdual
    n = len(weights)
    M = np.zeros((n, n), dtype=complex)
    orbits = [weyl_orbit_signed(L, tuple(x + 1 for x in lam)) for lam in weights]
    for i, lam in enumerate(weights):
        for j, mu in enumerate(weights):
            mr = tuple(x + 1 for x in mu)
            s = 0j
            for sg, wl in orbits[i]:
                s += sg * np.exp(-2j * np.pi * float(L.ip(wl, mr)) / K)
            M[i, j] = s
    norm = math.sqrt(sum(abs(M[0, j]) ** 2 for j in range(n)))
    phase = M[0, 0] / abs(M[0, 0])
    S = M / (norm * phase)
    assert np.allclose(S @ S.conj().T, np.eye(n), atol=1e-10)
    return S
