#!/usr/bin/env python3
"""Spectra of the N=2 superconformal minimal models, k = 1..8, as the bosonic
diagonal coset theory

    Z = sum over field-identification orbits of |chi^l_{m,s}|^2

of SU(2)_k x U(1)_2 / U(1)_{k+2} (NS and R sectors, s_L = s_R).

Branching functions. With Theta_{m,K}(q,z) = sum_{n in Z + m/2K} q^{K n^2} z^{K n},

    chi_l(q,z) Theta_{s,2}(q,z) = sum_{m mod 2(k+2)} chi^l_{m,s}(q) Theta_{m,k+2}(q,z)

(Sugawara, arXiv:2004.05742, eq. (A.16) at zero U(1) fugacity; the eta's of the
two U(1) characters cancel). A power z^u of Theta_{m,K} carries q^{u^2/K}, so

    chi^l_{m,s}(q) = q^{-u^2/K} [z^u] (chi_l Theta_{s,2}),   K = k+2,

for any u in m/2 + K Z, with no extra eta. su2.py grades by w = 2 J^3_0, so all
z-exponents are doubled here: Theta_{s,2} has terms z^t q^{t^2/8} with t in
4Z + s, the total doubled exponent is W = 2u = m mod 2K, and the shift is
q^{-W^2/(4K)}.

Labels: l + m + s even, (l, m, s) ~ (k-l, m+K, s+2), s mod 4, m mod 2K. Each
orbit is written once, with its representative s in {0, 1} (0: NS, 1: R) and
-K < m <= K.

    python scripts/spectra/gen_n2.py
"""

from __future__ import annotations

import math
from fractions import Fraction as F

from common import Series, block, write_spectrum
from su2 import W as W_HALF
from su2 import su2_char

GEN = "scripts/spectra/gen_n2.py"
TOP = 9            # every block is written up to weight 9 (> 8)
LEVELS = range(1, 9)


def c_n2(k: int) -> F:
    return F(3 * k, k + 2)


def h_formula(k: int, l: int, m: int, s: int) -> F:
    """h = (l(l+2) - m^2)/(4(k+2)) + s/8 for s = [l+m] in {0, 1} (Gray eq. (3)).
    It is the lowest weight of the block in the standard range |m - s| <= l,
    and equals it mod 1 elsewhere."""
    assert s in (0, 1) and (l + m + s) % 2 == 0
    return F(l * (l + 2) - m * m, 4 * (k + 2)) + F(s, 8)


def theta2_terms(s: int, emax) -> list[tuple[int, F]]:
    """Theta_{s,2} in the doubled grading: [(t, t^2/8)] for t in 4Z + s, t^2/8 <= emax."""
    tmax = math.isqrt(int(8 * F(emax))) + 2
    return [(t, F(t * t, 8)) for t in range(-tmax, tmax + 1)
            if (t - s) % 4 == 0 and F(t * t, 8) <= emax]


def branching(k: int, l: int, s: int, Wtot: int, N: int) -> Series:
    """q^{-Wtot^2/(4K)} [z^Wtot] (chi_l Theta_{s,2}) in the doubled grading,
    exact up to its .top (levels 0..N of chi_l)."""
    K = k + 2
    G = su2_char(k, l, N)
    shift = -F(Wtot * Wtot, 4 * K)
    out: dict[F, int] = {}
    for t, e in theta2_terms(s, N):
        w = Wtot - t
        assert (w - l) % 2 == 0
        # su2.py keeps |w| <= W_HALF; at level <= N the character has |w| <= l + 2N
        assert abs(w) <= W_HALF and l + 2 * N < W_HALF
        for n, a in enumerate(G.column(w)):
            if a and n + e <= N:
                x = G.E + n + e + shift
                out[x] = out.get(x, 0) + a
    return Series(out, G.E + N + shift)


def same(A: Series, B: Series) -> bool:
    top = min(A.top, B.top)
    a = {e: x for e, x in A.c.items() if e <= top}
    b = {e: x for e, x in B.c.items() if e <= top}
    return a == b


def orbits(k: int) -> list[tuple[int, int, int]]:
    """One representative (l, m, s) per orbit: s in {0, 1}, -K < m <= K."""
    K = k + 2
    reps = []
    for l in range(k + 1):
        for m in range(-K + 1, K + 1):
            s = (l + m) % 2
            reps.append((l, m, s))
    assert len(reps) == 2 * (k + 1) * (k + 2)
    return reps


def n2_spectrum(k: int):
    K = k + 2
    c = c_n2(k)
    N = math.ceil(TOP + F(9 * K, 4)) + 2     # enough for the representatives m and m +- 2K
    rows = []
    for (l, m, s) in orbits(k):
        A = branching(k, l, s, m, N)
        # (iii) the extracted series does not depend on the representative u
        for Walt in (m + 2 * K, m - 2 * K):
            assert same(A, branching(k, l, s, Walt, N)), (k, l, m, s, Walt)
        # (ii) the identified label (k-l, m+K, s+2) gives the same series
        Wid = m + K if m <= 0 else m - K
        assert same(A, branching(k, k - l, (s + 2) % 4, Wid, N)), (k, l, m, s)
        assert A.top >= TOP - c / 24, (k, l, m, s, A.top)
        lead = A.lead()
        h = lead + c / 24
        assert all(F(x).denominator == 1 and x > 0 for x in A.c.values()), (k, l, m, s)
        assert all((e - lead).denominator == 1 for e in A.c), (k, l, m, s)
        hf = h_formula(k, l, m, s)
        assert (h - hf).denominator == 1 and h >= 0, (k, l, m, s, h, hf)
        if abs(m - s) <= l:
            assert h == hf, (k, l, m, s, h, hf)
        rows.append((h, s, l, m, A))
    rows.sort(key=lambda r: (r[0], r[1], r[2], r[3]))

    # (i) the vacuum chi^0_{0,0} starts at q^{-c/24} with coefficient 1
    h0, s0, l0, m0, A0 = rows[0]
    assert (l0, m0, s0) == (0, 0, 0) and A0.lead() == -c / 24 and A0.coeff(-c / 24) == 1
    assert all(r[0] > 0 for r in rows[1:])
    if k == 1:
        hR = next(r[0] for r in rows if (r[2], r[3], r[1]) == (0, 1, 1))
        assert hR == F(1, 24) == c / 24
    # Ramond ground states (l, l+1, 1) at h = c/24; chiral primaries (l, l, 0) at h = l/(2K)
    for l in range(k + 1):
        m = l + 1 if l + 1 <= K else l + 1 - 2 * K
        assert next(r[0] for r in rows if (r[2], r[3], r[1]) == (l, m, 1)) == c / 24
        assert next(r[0] for r in rows if (r[2], r[3], r[1]) == (l, l, 0)) == F(l, 2 * K)
    gap_blocks = 2 * min(r[0] for r in rows[1:])
    assert gap_blocks == min(F(1, K), F(k, 4 * K)), (k, gap_blocks)

    blocks = [block(A, c, f"\\chi^{{{l}}}_{{{m},{s}}}", TOP) for (h, s, l, m, A) in rows]
    for b, r in zip(blocks, rows):
        assert F(b["h"]) == r[0] and all(isinstance(x, int) and x >= 0 for x in b["coeffs"])
        assert F(b["h"]) + F(b.get("step", 1)) * (len(b["coeffs"]) - 1) >= 8
    Z = [[i, i, 1] for i in range(len(blocks))]
    assert all(isinstance(z[2], int) for z in Z)       # integer multiplicities
    return c, blocks, Z


CHAR_TEX = ("Branching functions $\\chi^{SU(2)_k}_l(\\tau,z)\\,\\Theta_{s,2}(\\tau,z) = "
            "\\sum_{m\\in\\mathbb{Z}_{2(k+2)}} \\chi^l_{m,s}(\\tau)\\,\\Theta_{m,k+2}(\\tau,z)$, "
            "$\\Theta_{m,K}(\\tau,z) = \\sum_{n\\in\\mathbb{Z}+m/2K} q^{Kn^2}z^{Kn}$ "
            "(Sugawara, arXiv:2004.05742, eq. (A.16) at zero $U(1)$ fugacity), computed from the Weyl-Kac "
            "character $\\chi_l$ as $\\chi^l_{m,s} = q^{-u^2/(k+2)}\\,[z^u]\\big(\\chi_l\\,\\Theta_{s,2}\\big)$ "
            "for any $u \\in \\frac m2 + (k+2)\\mathbb{Z}$. Labels: $l+m+s$ even, "
            "$(l,m,s)\\sim(k-l,\\,m+k+2,\\,s+2)$; each orbit is labelled by its representative with "
            "$s\\in\\{0,1\\}$ ($s=0$ NS, $s=1$ R) and $-(k+2)<m\\le k+2$. For $|m-s|\\le l$ the weight is "
            "$h = \\frac{l(l+2)-m^2}{4(k+2)} + \\frac{s}{8}$. The NS and R characters of the "
            "$\\mathcal{N}=2$ algebra are $\\chi^l_{m,0}+\\chi^l_{m,2}$ and $\\chi^l_{m,1}+\\chi^l_{m,3}$.")

NOTES = {
    1: (" At $k=1$ the partition function equals that of the compact boson at $R = 2\\sqrt3$ "
        "(equivalently $R = 1/\\sqrt3$) in the convention of the compact-boson entry; Gray writes it as "
        "$Z_{R=\\sqrt6}$ with self-dual radius 1."),
    2: (" At $k=2$ the partition function equals that of the Ising model times the compact boson at "
        "$R = 2\\sqrt2$ in the convention of the compact-boson entry; Gray writes it as "
        "$Z_{\\rm Ising}Z_{R=2}$ with self-dual radius 1."),
}


def main():
    for k in LEVELS:
        c, blocks, Z = n2_spectrum(k)
        n = len(blocks)
        spec = {
            "theory": "n2-minimal-models",
            "member": {"at": k},
            "c": str(c),
            "chiral_algebra": f"\\big(SU(2)_{{{k}}}\\times U(1)_2\\big)/U(1)_{{{k + 2}}}",
            "irreducible": True,
            "Z_tex": "Z = \\sum_{(l,m,s)/\\sim} |\\chi^l_{m,s}|^2",
            "character_tex": CHAR_TEX,
            "description": (
                f"Bosonic diagonal coset theory at $k={k}$: one term $|\\chi^l_{{m,s}}|^2$ for each of the "
                f"{n} field-identification orbits, so the NS$\\otimes$NS and R$\\otimes$R sectors appear with "
                "$s_L = s_R$ and there is no NS$\\otimes$R sector. The supercurrents $G^\\pm$ appear only paired "
                "with antiholomorphic fermionic states; the lowest are the four states $G^a\\bar G^b$ at "
                "$(h,\\bar h) = (\\frac32,\\frac32)$, in the block of the orbit of $(0,0,2)$, labelled "
                f"$\\chi^{{{k}}}_{{{k + 2},0}}$. This is the diagonal "
                "invariant $Z = \\sum_{(a,c)\\in Q_k}|\\chi_{a,c}|^2$ of Cordova-Rizi (arXiv:2312.17308, "
                "eq. (2.31)) and Gray (arXiv:0812.1318, eq. (4) with $M$ the identity), the bosonization of the "
                "fermionic $\\mathcal{N}=2$ minimal model (Chen-Duan-Jia-Lee, arXiv:2511.22129, supplement A)."
                + NOTES.get(k, "")),
            "generator": GEN,
            "blocks": blocks,
            "Z": Z,
        }
        p = write_spectrum(spec)
        print("wrote", p.relative_to(p.parents[3]), f"({n} blocks)")


if __name__ == "__main__":
    main()
