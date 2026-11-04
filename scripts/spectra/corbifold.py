"""Z_2 (charge-conjugation type) orbifolds of rational CFTs from twining characters.

For a symmetry g of order two acting on a diagonal-type theory, the orbifold is

    Z = 1/2 (Z_{1,1} + Z_{1,g}) + P_Z Z_{g,1},

with Z_{g,1}(tau) = Z_{1,g}(-1/tau) and P_Z the projection on integer spin
(equivalently 1/2 (Z_{g,1} + Z_{g,g}), Z_{g,g}(tau) = Z_{g,1}(tau + 1)).

Here every twining character has the form

    t(tau) = sum_{m mod 2M} f(m) theta_{m,M}(tau) / eta(2 tau),
    theta_{m,M}(tau) = sum_{x = m mod 2M} q^{x^2/(4M)},

so Poisson resummation gives  t(-1/tau) = M^{-1/2} sum_m' fhat(m') theta_{m',M}(tau) / eta(tau/2)
with fhat(m') = sum_m f(m) exp(-i pi m m'/M).  The resulting Hermitian form on
theta_{m',M} theta_{m'',M}-bar is folded with theta_{-m} = theta_m, rationalised
(its entries are rational although the Gauss sums are not), and split exactly as
L D L^T into twisted-sector characters.
"""

from __future__ import annotations

import cmath
import math
from fractions import Fraction as F

from common import Series, block, frac_str, inv_phi


# ------------------------------------------------------------- q-series pieces

def theta(m: int, M: int, top) -> Series:
    """theta_{m,M} = sum_{x = m mod 2M} q^{x^2/(4M)}, exact up to exponent top."""
    top = F(top)
    out: dict = {}
    r = m % (2 * M)
    # x = r + 2M n for all integers n with x^2/(4M) <= top
    xmax = math.isqrt(int(4 * M * top) + 1) + 1 if top >= 0 else -1
    n0 = -((xmax + r) // (2 * M)) - 1
    x = r + 2 * M * n0
    while x <= xmax:
        e = F(x * x, 4 * M)
        if e <= top:
            out[e] = out.get(e, 0) + 1
        x += 2 * M
    return Series(out, top)


def theta_comb(f: dict[int, int], M: int, top) -> Series:
    """sum_m f(m) theta_{m,M}."""
    s = Series({}, F(top))
    for m, a in f.items():
        if a:
            s = s + theta(m, M, top) * a
    return s


def inv_eta_2tau(top) -> Series:
    """1/eta(2 tau) = q^{-1/12} sum p(n) q^{2n}."""
    top = F(top)
    return inv_phi(top + F(1, 12), 2).shift(-F(1, 12)).truncate(top)


def inv_eta_half(top) -> Series:
    """1/eta(tau/2) = q^{-1/48} sum p(n) q^{n/2}."""
    top = F(top)
    return inv_phi(top + F(1, 48), F(1, 2)).shift(-F(1, 48)).truncate(top)


def eta_ratio_half(top) -> Series:
    """B = eta(tau/2)/eta(tau) = q^{-1/48} prod_{n >= 1} (1 - q^{n - 1/2})."""
    top = F(top)
    s = Series.mono(0, 1, top + F(1, 48))
    e = F(1, 2)
    while e <= top + F(1, 48):
        s = s * Series({F(0): 1, e: -1}, top + F(1, 48))
        e += 1
    return s.shift(-F(1, 48)).truncate(top)


def eta_2_over_eta(top) -> Series:
    """eta(2 tau)/eta(tau) = q^{1/24} prod_{n >= 1} (1 + q^n)."""
    top = F(top)
    s = Series.mono(0, 1, top)
    n = 1
    while n <= top:
        s = s * Series({F(0): 1, F(n): 1}, top)
        n += 1
    return s.shift(F(1, 24)).truncate(top)


# ------------------------------------------------------------- Poisson resummation

def _rationalize(x: complex, M: int, tol=1e-9) -> F:
    if abs(x.imag) > tol:
        raise ValueError(f"twisted-sector coefficient {x} is not real")
    r = F(x.real).limit_denominator(64 * M * M)
    if abs(float(r) - x.real) > tol:
        raise ValueError(f"twisted-sector coefficient {x.real} is not rational")
    return r


def twisted_form(twinings: list[tuple[int, dict[int, int]]], M: int) -> dict[tuple[int, int], F]:
    """Z_{g,1} = sum_{a,b} H[a,b] theta_{a,M} theta_{b,M}-bar / |eta(tau/2)|^2 for
    Z_{1,g} = sum_i eps_i |t_i|^2, t_i = sum_m f_i(m) theta_{m,M}/eta(2 tau).
    twinings: [(eps_i, f_i)].  Classes a = 0..M stand for {a, -a} mod 2M."""
    N2 = 2 * M
    hats = []
    for eps, f in twinings:
        fh = []
        for mp in range(N2):
            fh.append(sum(a * cmath.exp(-1j * math.pi * m * mp / M) for m, a in f.items()))
        hats.append((eps, fh))
    cls = lambda m: min(m % N2, (-m) % N2)
    H: dict[tuple[int, int], complex] = {}
    for mp in range(N2):
        for mpp in range(N2):
            v = sum(eps * fh[mp] * fh[mpp].conjugate() for eps, fh in hats) / M
            key = (cls(mp), cls(mpp))
            H[key] = H.get(key, 0) + v
    out = {}
    for key, v in H.items():
        r = _rationalize(v, M)
        if r:
            out[key] = r
    return out


def ldl(H: dict[tuple[int, int], F], order: list[int]):
    """Exact H = sum_j d_j w_j w_j^T, w_j[order[j]] = 1, w_j[order[i<j]] = 0."""
    A = {k: F(v) for k, v in H.items()}
    out = []
    for a in order:
        d = A.get((a, a), F(0))
        if d == 0:
            if any(A.get((a, b), 0) for b in order):
                raise ValueError("L D L^T breaks down (zero pivot with non-zero row)")
            continue
        w = {b: A.get((a, b), F(0)) / d for b in order if A.get((a, b), 0)}
        out.append((d, w))
        for b, wb in w.items():
            for b2, wb2 in w.items():
                A[(b, b2)] = A.get((b, b2), F(0)) - d * wb * wb2
    return out


# ------------------------------------------------------------- assembling the orbifold

def split_mod1(s: Series) -> dict[F, Series]:
    """Split a series by the class of its exponents mod 1."""
    parts: dict[F, dict] = {}
    for e, a in s.c.items():
        parts.setdefault(e % 1, {})[e] = a
    return {r: Series(d, s.top) for r, d in parts.items()}


class Builder:
    """Collects blocks (by key) and Z entries for a spectrum file."""

    def __init__(self, c, top_weight=None):
        self.c = F(c)
        self.top_weight = top_weight
        self.blocks: list[dict] = []
        self.series: list[Series] = []
        self.keys: dict = {}
        self.Z: dict[tuple[int, int], F] = {}

    def block(self, key, label: str, series: Series, top_weight=None) -> int:
        if key not in self.keys:
            if not series.c:
                raise ValueError(f"block {label} vanishes")
            bad = [a for a in series.c.values() if a < 0 or F(a).denominator != 1]
            if bad:
                raise ValueError(f"block {label} has coefficient {bad[0]}")
            tw = self.top_weight if top_weight is None else top_weight
            self.keys[key] = len(self.blocks)
            self.blocks.append(block(series, self.c, label, tw))
            self.series.append(series)
        return self.keys[key]

    def add(self, i: int, j: int, coef=1):
        self.Z[(i, j)] = self.Z.get((i, j), F(0)) + F(coef)

    def result(self):
        Z = [[i, j, frac_str(v)] for (i, j), v in sorted(self.Z.items()) if v]
        return self.blocks, Z


def add_untwisted(B: Builder, summands, C, char, label, twining=None, sign=None, pm_label=None):
    """Untwisted sector 1/2 (Z_{1,1} + Z_{1,g}) of a theory sum_{(i,j) in summands} chi_i chi_j-bar.
    C: module index -> image; char(i), label(i): character and LaTeX label; twining(i): the
    g-twined character of a g-fixed module (leading coefficient +1); sign(i, j): eigenvalue
    (+1/-1) of g on the primary of a fixed summand (default +1); pm_label(i, "+"/"-"): label of
    the g-even/odd part (default label(i) + "^{+}")."""
    if pm_label is None:
        pm_label = lambda i, s: label(i) + "^{" + s + "}"
    cls = lambda i: min(i, C[i])
    done = set()
    for (i, j) in summands:
        if (i, j) in done:
            continue
        img = (C[i], C[j])
        done.add((i, j))
        done.add(img)
        if img != (i, j):
            a = B.block(("u", cls(i)), label(cls(i)), char(cls(i)))
            b = B.block(("u", cls(j)), label(cls(j)), char(cls(j)))
            B.add(a, b)
            continue
        parts = {}
        for k in {i, j}:
            ch, t = char(k), twining(k)
            plus, minus = (ch + t) * F(1, 2), (ch - t) * F(1, 2)
            parts[k] = (B.block(("+", k), pm_label(k, "+"), plus),
                        B.block(("-", k), pm_label(k, "-"), minus))
        s = 1 if sign is None else sign(i, j)
        if s == 1:
            B.add(parts[i][0], parts[j][0])
            B.add(parts[i][1], parts[j][1])
        else:
            B.add(parts[i][0], parts[j][1])
            B.add(parts[i][1], parts[j][0])


def add_twisted(B: Builder, chars: list[tuple[str, Series]], pairing: dict[tuple[int, int], int]):
    """P_Z of the twisted sector sum N_{jk} T_j T_k-bar.  Each twisted character is split by
    exponent mod 1 into its two eigenspaces of the lifted g; labels get ^{+} (the part with
    the ground state) and ^{-}."""
    split = []
    for lab, s in chars:
        lead = min(s.c)
        parts = split_mod1(s)
        if len(parts) > 2:
            raise ValueError(f"twisted character {lab} has weights in more than two classes mod 1")
        idx = {}
        for r, part in parts.items():
            tag = "+" if r == lead % 1 else "-"
            idx[r] = B.block(("t", lab, tag), f"{lab}^{{{tag}}}", part)
        split.append(idx)
    for (j, k), n in pairing.items():
        for rj, bj in split[j].items():
            for rk, bk in split[k].items():
                if rj == rk:
                    B.add(bj, bk, n)
