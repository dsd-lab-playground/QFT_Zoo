"""Affine SU(2)_k characters graded by the Cartan generator, and what they give:
coset branching functions (decomposition of products) and Z_k parafermion
characters (string functions).

A graded character is  sum_{n, w} a[n, w] q^(E + n) z^w  with w = 2 J^3_0.
Arrays are numpy int64 with columns w = -W..W (index w + W).
"""

from __future__ import annotations

from fractions import Fraction as F
from functools import lru_cache

import numpy as np

from common import Series, phi

W = 160            # half-width of the z-grading kept (|2 J^3| <= W)


def c_su2(k: int) -> F:
    return F(3 * k, k + 2)


def h_su2(k: int, l: int) -> F:
    return F(l * (l + 2), 4 * (k + 2))


class Graded:
    def __init__(self, E: F, a: np.ndarray):
        self.E = F(E)
        self.a = a              # shape (N+1, 2W+1)

    @property
    def N(self):
        return self.a.shape[0] - 1

    def column(self, w: int) -> list[int]:
        return [int(x) for x in self.a[:, w + W]]


def _shift(row: np.ndarray, s: int) -> np.ndarray:
    out = np.zeros_like(row)
    if s > 0:
        out[s:] = row[:-s]
    elif s < 0:
        out[:s] = row[-s:]
    else:
        out[:] = row
    return out


@lru_cache(maxsize=None)
def _inv_denominator(N: int) -> np.ndarray:
    """1 / prod_{n>=1} (1-q^n)(1-q^n z^2)(1-q^n z^-2), levels 0..N."""
    a = np.zeros((N + 1, 2 * W + 1), dtype=np.int64)
    a[0, W] = 1
    for n in range(1, N + 1):
        for s in (0, 2, -2):
            for lev in range(n, N + 1):
                a[lev] += _shift(a[lev - n], s)
    return a


def _finite(a: int) -> np.ndarray:
    """(z^{a+1} - z^{-a-1}) / (z - z^{-1}) as a row."""
    row = np.zeros(2 * W + 1, dtype=np.int64)
    if a >= 0:
        row[W - a: W + a + 1: 2] = 1
    elif a <= -2:
        b = -a - 2
        row[W - b: W + b + 1: 2] = -1
    return row


@lru_cache(maxsize=None)
def su2_char(k: int, l: int, N: int) -> Graded:
    """Weyl-Kac character of the level-k, spin-l/2 module, levels 0..N."""
    K = k + 2
    num = np.zeros((N + 1, 2 * W + 1), dtype=np.int64)
    j = 0
    while True:
        hit = False
        for jj in ((j, -j) if j else (0,)):
            lev = K * jj * jj + (l + 1) * jj
            if 0 <= lev <= N:
                num[lev] += _finite(l + 2 * K * jj)
                hit = True
        if not hit and j > 1:
            break
        j += 1
    inv = _inv_denominator(N)
    out = np.zeros_like(num)
    for L in range(N + 1):
        if not num[L].any():
            continue
        nz = np.nonzero(num[L])[0]
        for n in range(N + 1 - L):
            row = inv[n]
            for idx in nz:
                out[L + n] += num[L, idx] * _shift(row, idx - W)
    assert np.abs(out).max() < 2**60
    return Graded(h_su2(k, l) - c_su2(k) / 24, out)


def product(A: Graded, B: Graded, N: int | None = None) -> Graded:
    N = min(A.N, B.N) if N is None else N
    out = np.zeros((N + 1, 2 * W + 1), dtype=np.int64)
    for n1 in range(N + 1):
        ra = A.a[n1]
        nz = np.nonzero(ra)[0]
        if not len(nz):
            continue
        for n2 in range(N + 1 - n1):
            rb = B.a[n2]
            if not rb.any():
                continue
            for idx in nz:
                out[n1 + n2] += ra[idx] * _shift(rb, idx - W)
    return Graded(A.E + B.E, out)


def decompose(X: Graded, k: int) -> dict[int, Series]:
    """Write X = sum_l b_l(q) chi^{(k)}_l(q, z); returns {l: b_l} (exact up to their .top)."""
    N = X.N
    R = X.a.copy()
    found: dict[int, dict[int, int]] = {}
    for n in range(N + 1):
        row = R[n]
        mults = {}
        for w in range(0, W - 1):
            m = int(row[w + W] - row[w + 2 + W])
            if m:
                mults[w] = m
        for w, m in mults.items():
            if m < 0 or w > k:
                raise ValueError(f"decomposition failed at level {n}: weight {w}, multiplicity {m}")
            found.setdefault(w, {})[n] = m
            C = su2_char(k, w, N).a
            for jlev in range(N + 1 - n):
                R[n + jlev] -= m * C[jlev]
        assert not R[n].any(), f"residual at level {n}"
    out = {}
    for w, terms in found.items():
        E3 = h_su2(k, w) - c_su2(k) / 24
        out[w] = Series({X.E + n - E3: m for n, m in terms.items()}, X.E + N - E3)
    return out


def coset_branching(k1: int, k2: int, N: int) -> dict[tuple[int, int, int], Series]:
    """b_{l1, l2; l3} for SU(2)_k1 x SU(2)_k2 / SU(2)_{k1+k2} (all labels, no identification)."""
    out = {}
    for l1 in range(k1 + 1):
        for l2 in range(k2 + 1):
            X = product(su2_char(k1, l1, N), su2_char(k2, l2, N), N)
            for l3, b in decompose(X, k1 + k2).items():
                out[(l1, l2, l3)] = b
    return out


def parafermion_char(k: int, l: int, m: int, N: int) -> Series:
    """Character of the Z_k parafermion field (l, m) = eta * q^{-w^2/4k} [z^w] chi_l, w = m mod 2k."""
    if (l - m) % 2:
        raise ValueError("l and m must have equal parity")
    w = min((m + 2 * k * t for t in range(-3, 4)), key=abs)
    G = su2_char(k, l, N)
    col = Series({G.E + n: a for n, a in enumerate(G.column(w)) if a}, G.E + N)
    eta = phi(N + 2).shift(F(1, 24))
    return (col * eta).shift(-F(w * w, 4 * k))


def parafermion_h(k: int, l: int, m: int) -> F:
    """Weight of (l, m) in the standard range |m| <= l (else use the identification)."""
    if abs(m) > l:
        l, m = k - l, (m + k) if m < 0 else (m - k)
    return F(l * (l + 2), 4 * (k + 2)) - F(m * m, 4 * k)
