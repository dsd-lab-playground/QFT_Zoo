"""Shared tools for the spectrum generators: exact truncated q-series and the
spectrum-file writer. All arithmetic is exact (ints and Fractions).

A Series is a finite sum  sum_e a_e q^e  over rational exponents e (absolute
powers of q, including the -c/24), known exactly for every e <= top.
"""

from __future__ import annotations

import json
import math
import sys
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from zoo_spectrum import expected_path, partitions  # noqa: E402

INF = F(10**9)


class Series:
    __slots__ = ("c", "top")

    def __init__(self, coeffs: dict | None = None, top=INF):
        self.c = {F(e): a for e, a in (coeffs or {}).items() if a != 0 and F(e) <= top}
        self.top = F(top)

    # -- constructors
    @classmethod
    def mono(cls, e, a=1, top=INF):
        return cls({F(e): a}, top)

    @classmethod
    def from_list(cls, e0, coeffs, step=1, top=None):
        e0, step = F(e0), F(step)
        if top is None:
            top = e0 + step * (len(coeffs) - 1)
        return cls({e0 + n * step: a for n, a in enumerate(coeffs)}, top)

    # -- arithmetic
    def copy(self):
        s = Series()
        s.c, s.top = dict(self.c), self.top
        return s

    def __add__(self, other):
        if not isinstance(other, Series):
            other = Series.mono(0, other)
        top = min(self.top, other.top)
        out = {e: a for e, a in self.c.items() if e <= top}
        for e, a in other.c.items():
            if e <= top:
                out[e] = out.get(e, 0) + a
        return Series(out, top)

    __radd__ = __add__

    def __neg__(self):
        return Series({e: -a for e, a in self.c.items()}, self.top)

    def __sub__(self, other):
        return self + (-other)

    def __rsub__(self, other):
        return (-self) + other

    def __mul__(self, other):
        if not isinstance(other, Series):
            return Series({e: a * other for e, a in self.c.items()}, self.top)
        if not self.c or not other.c:
            top = min(self.top + (min(other.c) if other.c else INF),
                      other.top + (min(self.c) if self.c else INF))
            return Series({}, top)
        top = min(self.top + min(other.c), other.top + min(self.c))
        out: dict = {}
        b_items = sorted(other.c.items())
        for e1, a1 in sorted(self.c.items()):
            for e2, a2 in b_items:
                e = e1 + e2
                if e > top:
                    break
                out[e] = out.get(e, 0) + a1 * a2
        return Series(out, top)

    __rmul__ = __mul__

    def __pow__(self, n: int):
        out = Series.mono(0)
        base = self
        while n:
            if n & 1:
                out = out * base
            base = base * base
            n >>= 1
        return out

    def truncate(self, top):
        top = min(F(top), self.top)
        return Series({e: a for e, a in self.c.items() if e <= top}, top)

    def subs(self, k):
        """q -> q^k."""
        k = F(k)
        return Series({e * k: a for e, a in self.c.items()}, self.top * k)

    def shift(self, d):
        """multiply by q^d."""
        d = F(d)
        return Series({e + d: a for e, a in self.c.items()}, self.top + d)

    def inverse(self, top):
        """1/self, exact up to exponent `top`. The leading coefficient must be +-1."""
        e0 = min(self.c)
        a0 = self.c[e0]
        if abs(a0) != 1:
            raise ValueError("leading coefficient must be +-1 to stay integral")
        g = {e - e0: a * a0 for e, a in self.c.items()}          # 1 + higher terms
        T = min(F(top) + e0, self.top - e0)
        pos = [e for e in g if e > 0]
        step = pos[0] if pos else F(1)
        for e in pos:
            step = _fgcd(step, e)
        N = int(T / step)
        cs = [0] * (N + 1)
        for e, a in g.items():
            if e / step <= N:
                cs[int(e / step)] = a
        inv = [0] * (N + 1)
        inv[0] = 1
        nz = [k for k in range(1, N + 1) if cs[k]]
        for n in range(1, N + 1):
            inv[n] = -sum(cs[k] * inv[n - k] for k in nz if k <= n)
        return Series({k * step - e0: v * a0 for k, v in enumerate(inv) if v}, N * step - e0)

    # -- inspection
    def lead(self):
        return min(self.c) if self.c else None

    def coeff(self, e):
        return self.c.get(F(e), 0)

    def __repr__(self):
        items = sorted(self.c.items())[:8]
        body = " + ".join(f"{a}q^{e}" for e, a in items)
        return f"Series({body}{' + ...' if len(self.c) > 8 else ''}; top={self.top})"


def _fgcd(a: F, b: F) -> F:
    a, b = F(a), F(b)
    den = a.denominator * b.denominator // math.gcd(a.denominator, b.denominator)
    return F(math.gcd(int(a * den), int(b * den)), den)


# ------------------------------------------------------------- standard pieces

def phi(top, k=1) -> Series:
    """prod_{n>=1} (1 - q^{kn}) up to exponent top (Euler's pentagonal series)."""
    out = {}
    j = 0
    while True:
        done = True
        for g in ((j * (3 * j - 1)) // 2, (j * (3 * j + 1)) // 2):
            if g * k <= top:
                out[F(g * k)] = (-1) ** (j % 2)
                done = False
        if done and j > 0:
            break
        j += 1
    return Series(out, top)


def inv_phi(top, k=1) -> Series:
    """1/prod_{n>=1}(1 - q^{kn}) = sum p(n) q^{kn}."""
    n = int(F(top) / k)
    p = partitions(n)
    return Series({F(i * k): p[i] for i in range(n + 1)}, top)


def qpoch(a, d, top, sign=-1, inverse=False) -> Series:
    """prod_{n>=0} (1 + sign*q^{a + n d}) (or its inverse), exponents a, d > 0."""
    a, d, top = F(a), F(d), F(top)
    s = Series.mono(0, 1, top)
    e = a
    while e <= top:
        if inverse:
            # 1/(1 + sign x) = sum (-sign x)^k
            terms = {}
            k = 0
            while k * e <= top:
                terms[k * e] = (-sign) ** k
                k += 1
            s = s * Series(terms, top)
        else:
            s = s * Series({F(0): 1, e: sign}, top)
        e += d
    return s


# ------------------------------------------------------------- output

def block(series: Series, c, label: str, top_weight=None) -> dict:
    """Turn a Series into a block {label, h, step, coeffs}; coefficients must be integers."""
    c = F(c)
    if not series.c:
        raise ValueError(f"block {label} is zero")
    e0 = min(series.c)
    top = series.top if top_weight is None else min(series.top, F(top_weight) - c / 24)
    diffs = [e - e0 for e in series.c if e != e0 and e <= top]
    step = F(1)
    if diffs:
        step = diffs[0]
        for d in diffs:
            step = _fgcd(step, d)
        # prefer step 1 or 1/2 etc. as large as the data allow, but never larger than 1
        if F(1) / step != int(F(1) / step):
            step = _fgcd(step, F(1))
        else:
            step = min(step, F(1))
    n = int((top - e0) / step)
    coeffs = [0] * (n + 1)
    for e, a in series.c.items():
        if e <= top:
            k = (e - e0) / step
            if F(a).denominator != 1:
                raise ValueError(f"block {label}: non-integer coefficient {a} at q^{e}")
            coeffs[int(k)] = int(a)
    out = {"label": label, "h": str(e0 + c / 24)}
    if step != 1:
        out["step"] = str(step)
    out["coeffs"] = coeffs
    return out


def write_spectrum(spec: dict) -> Path:
    """Write spec to its canonical path data/spectra/... with one block per line."""
    rel = expected_path(spec["theory"], spec.get("member"))
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    order = ["theory", "member", "c", "chiral_algebra", "irreducible", "Z_tex", "character_tex",
             "description", "generator", "blocks", "Z"]
    lines = ["{"]
    keys = [k for k in order if k in spec] + [k for k in spec if k not in order]
    for n, k in enumerate(keys):
        comma = "," if n < len(keys) - 1 else ""
        v = spec[k]
        if k == "blocks":
            lines.append('  "blocks": [')
            for i, b in enumerate(v):
                lines.append("    " + json.dumps(b, ensure_ascii=False) + ("," if i < len(v) - 1 else ""))
            lines.append("  ]" + comma)
        elif k == "Z":
            lines.append('  "Z": [')
            per = 6
            rows = [json.dumps(z) for z in v]
            for i in range(0, len(rows), per):
                chunk = ", ".join(rows[i:i + per])
                lines.append("    " + chunk + ("," if i + per < len(rows) else ""))
            lines.append("  ]" + comma)
        else:
            lines.append(f"  {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}{comma}")
    lines.append("}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def frac_str(x) -> str | int:
    x = F(x)
    return int(x) if x.denominator == 1 else str(x)
