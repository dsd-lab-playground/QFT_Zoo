"""Rational-CFT building blocks: Virasoro minimal-model characters, the ADE
(Cappelli-Itzykson-Zuber) invariants of SU(2)_k, tensor products, and
Kreuzer-Schellekens simple-current invariants.

A "chiral theory" here is a list of fields  Field(label, h, char)  where char
is a Series with absolute exponents (h - c/24 + level).
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction as F
from itertools import product as iproduct

from common import Series, block, frac_str, inv_phi


@dataclass
class Field:
    label: str          # LaTeX
    h: F
    char: Series


# ------------------------------------------------------------- Virasoro

def minimal_c(p: int, pp: int) -> F:
    return 1 - F(6 * (pp - p) ** 2, p * pp)


def minimal_h(p: int, pp: int, r: int, s: int) -> F:
    return F((pp * r - p * s) ** 2 - (pp - p) ** 2, 4 * p * pp)


def minimal_char(p: int, pp: int, r: int, s: int, top_weight) -> Series:
    """Rocha-Caridi character of M(p, p'), exact up to weight top_weight."""
    c = minimal_c(p, pp)
    top = F(top_weight) - c / 24
    num = {}
    k = 0
    while True:
        added = False
        for kk in ({k, -k} if k else {0}):
            for x, sign in ((2 * p * pp * kk + pp * r - p * s, 1), (2 * p * pp * kk + pp * r + p * s, -1)):
                e = F(x * x - (pp - p) ** 2, 4 * p * pp) - c / 24
                if e <= top:
                    num[e] = num.get(e, 0) + sign
                    added = True
        if not added and k > 2:
            break
        k += 1
    numerator = Series(num, top)
    return (numerator * inv_phi(top + c / 24 + 1)).truncate(top)


def minimal_fields(m: int, top_weight) -> dict[tuple[int, int], Field]:
    """Kac table of M_m = M(m, m+1), keyed by every (r, s) (both representatives)."""
    p, pp = m, m + 1
    out = {}
    for r in range(1, p):
        for s in range(1, pp):
            if (r, s) in out:
                continue
            rep = min((r, s), (p - r, pp - s))
            h = minimal_h(p, pp, *rep)
            f = Field(f"\\chi_{{{rep[0]},{rep[1]}}}", h, minimal_char(p, pp, *rep, max(F(top_weight), h + 2)))
            out[(r, s)] = out[(p - r, pp - s)] = f
    return out


# ------------------------------------------------------------- ADE invariants

def ade(kind: str, k: int) -> dict[tuple[int, int], int]:
    """CIZ invariant of SU(2)_k on 0-indexed labels l = 0..k: {(l, l'): N}."""
    M: dict[tuple[int, int], int] = {}

    def add(a, b, n=1):
        M[(a, b)] = M.get((a, b), 0) + n

    def block_sq(ls):
        for a in ls:
            for b in ls:
                add(a, b)

    if kind == "A":
        for l in range(k + 1):
            add(l, l)
    elif kind == "D":
        if k % 2:
            raise ValueError("D-type needs even k")
        if k % 4 == 0:
            for l in range(0, k // 2, 2):
                block_sq([l, k - l])
            add(k // 2, k // 2, 2)
        else:
            for l in range(0, k + 1, 2):
                add(l, l)
            for l in range(1, k, 2):
                add(l, k - l)
    elif kind == "E6" and k == 10:
        for bl in ([0, 6], [3, 7], [4, 10]):
            block_sq(bl)
    elif kind == "E7" and k == 16:
        for bl in ([0, 16], [4, 12], [6, 10]):
            block_sq(bl)
        add(8, 8)
        for a in (2, 14):
            add(a, 8)
            add(8, a)
    elif kind == "E8" and k == 28:
        for bl in ([0, 10, 18, 28], [6, 12, 16, 22]):
            block_sq(bl)
    else:
        raise ValueError(f"no {kind} invariant at level {k}")
    return M


def minimal_invariant(m: int, gr: str, gs: str, top_weight):
    """Fields (orbit representatives) and multiplicity matrix of M_m^{(gr, gs)}.
    gr acts on r (SU(2)_{m-2}), gs on s (SU(2)_{m-1})."""
    allf = minimal_fields(m, top_weight)
    reps = []
    index = {}
    for (r, s), f in sorted(allf.items()):
        rep = min((r, s), (m - r, m + 1 - s))
        if rep not in index:
            index[rep] = len(reps)
            reps.append(allf[rep])
        index[(r, s)] = index[rep]
    Mr, Ms = ade(gr, m - 2), ade(gs, m - 1)
    Z: dict[tuple[int, int], F] = {}
    for (a, b), x in Mr.items():
        for (c_, d), y in Ms.items():
            i, j = index[(a + 1, c_ + 1)], index[(b + 1, d + 1)]
            Z[(i, j)] = Z.get((i, j), 0) + F(x * y, 2)
    assert all(v.denominator == 1 for v in Z.values()), "non-integer minimal-model multiplicity"
    return reps, {k: int(v) for k, v in Z.items() if v}


# ------------------------------------------------------------- products, simple currents

def tensor(*theories: list[Field]) -> list[Field]:
    out = []
    for combo in iproduct(*theories):
        label = " ".join(f.label for f in combo)
        out.append(Field(label, sum((f.h for f in combo), F(0)),
                         _prod([f.char for f in combo])))
    return out


def _prod(chars):
    s = chars[0]
    for x in chars[1:]:
        s = s * x
    return s


def tensor_matrix(*mats):
    """Kronecker product of multiplicity matrices (dicts), matching tensor()."""
    sizes = [max(max(i, j) for i, j in M) + 1 for M in mats]
    out = {}
    for combo in iproduct(*[list(M.items()) for M in mats]):
        n = 1
        idx_i, idx_j = 0, 0
        for ((a, b), x), size in zip(combo, sizes):
            idx_i = idx_i * size + a
            idx_j = idx_j * size + b
            n *= x
        out[(idx_i, idx_j)] = out.get((idx_i, idx_j), 0) + n
    return out


def simple_current_invariant(fields: list[Field], J: dict[int, int], order: int) -> dict:
    """Kreuzer-Schellekens invariant of a cyclic simple current.
    J maps field index -> index of J x field. Uses h_J = r(N-1)/(2N) mod 1 and
    M_{a,b} = sum_n delta(b = J^n a) delta(Q_J(a) + n r / (2N) in Z)."""
    N = order
    hJ = fields[J[0]].h
    # r from h_J = r (N-1) / (2N); for odd N it must be even, so that the
    # condition below is periodic in n with period N
    r = None
    for cand in (range(2 * N) if N % 2 == 0 else range(0, 2 * N, 2)):
        if ((F(cand * (N - 1), 2 * N) - hJ).denominator == 1):
            r = cand
            break
    if r is None:
        raise ValueError("h_J is not of the simple-current form")
    M: dict[tuple[int, int], int] = {}
    for a, fa in enumerate(fields):
        Q = (fa.h + hJ - fields[J[a]].h) % 1
        b = a
        for n in range(N):
            if (Q + F(n * r, 2 * N)).denominator == 1:
                M[(a, b)] = M.get((a, b), 0) + 1
            b = J[b]
    return M


def spectrum_from(fields: list[Field], M: dict, c, top_weight=None, drop_unused=True):
    """Blocks + Z entries from fields and an integer matrix."""
    used = sorted({i for i, _ in M} | {j for _, j in M}) if drop_unused else list(range(len(fields)))
    new = {old: n for n, old in enumerate(used)}
    blocks = [block(fields[i].char, c, fields[i].label,
                    None if top_weight is None else max(F(top_weight), fields[i].h + 2)) for i in used]
    Z = [[new[i], new[j], frac_str(x)] for (i, j), x in sorted(M.items(), key=lambda kv: (new[kv[0][0]], new[kv[0][1]])) if x]
    return blocks, Z
