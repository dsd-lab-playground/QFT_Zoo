#!/usr/bin/env python3
"""Check and summarise spectrum files (data/spectra/**/*.json).

A spectrum file gives a 2d CFT torus partition function as

    Z(q, qbar) = sum_{[i, j, coef] in Z}  coef * b_i(q) * conj(b_j(q)),
    b(q) = q^(h - c/24) * sum_n coeffs[n] * q^(n*step),

where the blocks b are usually characters of a chiral algebra. The checks:

  * Z expands, up to h, hbar <= H (H = how far every block is known), with
    non-negative integer degeneracies, integer spins, h, hbar >= 0 and a
    unique vacuum;
  * Z(tau) = Z(-1/tau) numerically at three points;
  * Z decomposes into Virasoro characters with non-negative integer
    multiplicities (generic and vacuum characters for c > 1, degenerate ones
    at h = n^2/4 for c = 1, Kac-table characters for the minimal models);
  * the lightest non-vacuum Virasoro primary has the gap given in the theory
    file.

Run on single files while writing a generator:

    python scripts/zoo_spectrum.py data/spectra/ising-2d.json
"""

from __future__ import annotations

import cmath
import heapq
import json
import math
import re
import sys
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPECTRA = ROOT / "data" / "spectra"
SPECTRUM_SCHEMA = ROOT / "schema" / "spectrum.schema.json"

# S-invariance test points: away from tau = i (where S is trivially satisfied)
# and with Im tau, Im(-1/tau) large enough that truncated series converge.
TAUS = (complex(0.1, 1.2), complex(-0.27, 1.13), complex(0.41, 0.97))
S_TOL = 1e-8
SHOW_BLOCK_TERMS = 14      # q-expansion terms kept per block for display
SHOW_VIRASORO = 400        # Virasoro primaries listed on the site at most
H_CAP = F(10)              # degeneracies are checked for h, hbar <= min(H, H_CAP)


def rat(x) -> F:
    return F(x)


def member_slug(at, variant=None) -> str:
    s = str(at) + (f"_{variant}" if variant else "")
    s = s.replace("\\sqrt", "sqrt").replace("+", "p").replace("−", "m").replace("-", "m")
    return re.sub(r"[^A-Za-z0-9_]", "", s)


def expected_path(theory: str, member: dict | None) -> str:
    if member is None:
        return f"data/spectra/{theory}.json"
    return f"data/spectra/{theory}/{member_slug(member['at'], member.get('variant'))}.json"


# ------------------------------------------------------------- characters

_PART: list[int] = [1]


def partitions(n: int) -> list[int]:
    """p(0..n) (number of partitions), cached."""
    while len(_PART) <= n:
        m = len(_PART)
        total, k = 0, 1
        while True:
            g1 = k * (3 * k - 1) // 2
            if g1 > m:
                break
            sign = 1 if k % 2 else -1
            total += sign * _PART[m - g1]
            g2 = k * (3 * k + 1) // 2
            if g2 <= m:
                total += sign * _PART[m - g2]
            k += 1
        _PART.append(total)
    return _PART[: n + 1]


def minimal_m(c: F) -> int | None:
    """m with c = 1 - 6/(m(m+1)), if c is a unitary minimal-model value."""
    if c >= 1:
        return None
    x = 6 / (1 - c)               # = m(m+1)
    if x.denominator != 1:
        return None
    m = int((math.isqrt(4 * int(x) + 1) - 1) // 2)
    return m if m * (m + 1) == x and m >= 3 else None


class VirasoroCharacters:
    """q-expansions (as lists over integer levels) of Virasoro characters
    with the q^(h - c/24) prefactor stripped."""

    def __init__(self, c: F):
        self.c = c
        self.m = minimal_m(c)
        self.kac: dict[F, tuple[int, int]] = {}
        if c < 1:
            if self.m is None:
                raise ValueError(f"c = {c} < 1 is not a unitary minimal-model central charge")
            p, pp = self.m, self.m + 1
            for r in range(1, p):
                for s in range(1, pp):
                    self.kac.setdefault(F((pp * r - p * s) ** 2 - 1, 4 * p * pp), (r, s))

    def allowed(self, h: F) -> bool:
        return h in self.kac if self.c < 1 else h >= 0

    def levels(self, h: F, n: int) -> list[int]:
        part = partitions(n)
        if self.c > 1:
            if h == 0:
                return [part[k] - (part[k - 1] if k >= 1 else 0) for k in range(n + 1)]
            return part[:]
        if self.c == 1:
            r = 4 * h
            if r.denominator == 1 and math.isqrt(int(r)) ** 2 == int(r):
                shift = math.isqrt(int(r)) + 1          # (j+2)^2/4 - j^2/4
                return [part[k] - (part[k - shift] if k >= shift else 0) for k in range(n + 1)]
            return part[:]
        # unitary minimal model M(p, p+1): Rocha-Caridi
        p, pp = self.m, self.m + 1
        r, s = self.kac[h]
        num = [0] * (n + 1)
        kmax = 1 + int(math.sqrt(n + 1))
        for k in range(-kmax - 2, kmax + 3):
            for e, sign in ((F((2 * p * pp * k + pp * r - p * s) ** 2 - 1, 4 * p * pp), 1),
                            (F((2 * p * pp * k + pp * r + p * s) ** 2 - 1, 4 * p * pp), -1)):
                d = e - h
                if d.denominator == 1 and 0 <= d <= n:
                    num[int(d)] += sign
        out = [0] * (n + 1)
        for i, a in enumerate(num):
            if a:
                for j in range(n + 1 - i):
                    out[i + j] += a * part[j]
        return out


# ------------------------------------------------------------- the checks

def _block_top(b) -> F:
    return rat(b["h"]) + rat(b.get("step", 1)) * (len(b["coeffs"]) - 1)


def expand(spec) -> tuple[dict, F]:
    """Double series {(h, hbar): degeneracy} for h, hbar <= H."""
    blocks = spec["blocks"]
    used = sorted({i for i, _, _ in spec["Z"]} | {j for _, j, _ in spec["Z"]})
    H = min(min(_block_top(blocks[i]) for i in used), H_CAP)
    terms = {}
    for i in used:
        b = blocks[i]
        h, st = rat(b["h"]), rat(b.get("step", 1))
        terms[i] = [(h + n * st, a) for n, a in enumerate(b["coeffs"]) if a and h + n * st <= H]
    D: dict[tuple[F, F], F] = {}
    for i, j, coef in spec["Z"]:
        coef = rat(coef)
        for h1, a in terms[i]:
            for h2, b2 in terms[j]:
                key = (h1, h2)
                D[key] = D.get(key, 0) + coef * a * b2
    return {k: v for k, v in D.items() if v != 0}, H


def s_error(spec) -> float:
    """max over test points of |Z(tau) - Z(-1/tau)| / |Z(tau)|."""
    c = rat(spec["c"])
    blocks = spec["blocks"]
    worst = 0.0
    for tau in TAUS:
        vals = []
        for t in (tau, -1 / tau):
            bv = []
            for b in blocks:
                h, st = rat(b["h"]), rat(b.get("step", 1))
                e0 = float(h - c / 24)
                s = 0j
                for n, a in enumerate(b["coeffs"]):
                    if a:
                        s += a * cmath.exp(2j * math.pi * t * (e0 + n * float(st)))
                bv.append(s)
            z = 0j
            for i, j, coef in spec["Z"]:
                z += float(rat(coef)) * bv[i] * bv[j].conjugate()
            vals.append(z)
        worst = max(worst, abs(vals[0] - vals[1]) / abs(vals[0]))
    return worst


def virasoro_decompose(D: dict, c: F, H: F, errors: list[str]) -> dict:
    vc = VirasoroCharacters(c)
    rem = dict(D)
    heap = [(h + hb, h, hb) for (h, hb) in D]
    heapq.heapify(heap)
    seen = set()
    out = {}
    cache: dict[F, list[tuple[int, int]]] = {}

    def char(h):
        if h not in cache:
            n = int(H - h)
            cache[h] = [(k, a) for k, a in enumerate(vc.levels(h, n)) if a]
        return cache[h]

    while heap:
        _, h, hb = heapq.heappop(heap)
        if (h, hb) in seen:
            continue
        seen.add((h, hb))
        n = rem.get((h, hb), 0)
        if n == 0:
            continue
        if n < 0 or n.denominator != 1:
            errors.append(f"Virasoro multiplicity {n} at (h, hbar) = ({h}, {hb}) is not a non-negative integer")
            return out
        if not (vc.allowed(h) and vc.allowed(hb)):
            errors.append(f"({h}, {hb}) is not an allowed Virasoro highest weight at c = {c}")
            return out
        out[(h, hb)] = int(n)
        for a, x in char(h):
            for b, y in char(hb):
                key = (h + a, hb + b)
                if key not in rem:
                    rem[key] = F(0)
                    heapq.heappush(heap, (key[0] + key[1], key[0], key[1]))
                rem[key] -= n * x * y
    return out


def check(spec: dict, c_exact: F | None = None, gap_exact: F | None = None) -> tuple[dict, list[str]]:
    """Run every check; return (summary for the site, error messages)."""
    errors: list[str] = []
    c = rat(spec["c"])
    if c_exact is not None and c != c_exact:
        errors.append(f"c = {c} but the theory file says c = {c_exact}")
    nb = len(spec["blocks"])
    for k, (i, j, _) in enumerate(spec["Z"]):
        if i >= nb or j >= nb:
            errors.append(f"Z[{k}] refers to block {max(i, j)}, but there are only {nb} blocks")
    if errors:
        return {}, errors

    D, H = expand(spec)
    if D.get((F(0), F(0))) != 1:
        errors.append(f"the vacuum (0, 0) has degeneracy {D.get((F(0), F(0)), 0)}, not 1")
    for (h, hb), v in sorted(D.items()):
        if v < 0 or v.denominator != 1:
            errors.append(f"degeneracy {v} at (h, hbar) = ({h}, {hb}) is not a non-negative integer")
            break
        if (h - hb).denominator != 1:
            errors.append(f"non-integer spin at (h, hbar) = ({h}, {hb})")
            break
        if h < 0 or hb < 0:
            errors.append(f"negative weight at (h, hbar) = ({h}, {hb})")
            break

    err = s_error(spec)
    if not err < S_TOL:
        errors.append(f"not modular invariant: |Z(tau) - Z(-1/tau)|/|Z| = {err:.2e} (tolerance {S_TOL:.0e})")

    vir = virasoro_decompose(D, c, H, errors) if not errors else {}
    nonvac = [(h + hb, h, hb) for (h, hb) in vir if (h, hb) != (0, 0)]
    gap = min(nonvac)[0] if nonvac else None
    if gap_exact is not None and not errors:
        if gap_exact > H:
            errors.append(f"the gap {gap_exact} lies above the cutoff h <= {H}; give longer q-expansions")
        elif gap != gap_exact:
            errors.append(f"lightest non-vacuum Virasoro primary has Delta = {gap}, "
                          f"but the theory file says gap = {gap_exact}")

    blocks_out = []
    for b in spec["blocks"]:
        row = {"label": b["label"], "h": str(rat(b["h"])), "coeffs": b["coeffs"][:SHOW_BLOCK_TERMS]}
        if "step" in b and rat(b["step"]) != 1:
            row["step"] = str(rat(b["step"]))
        blocks_out.append(row)

    summary = {k: spec[k] for k in ("theory", "member", "chiral_algebra", "Z_tex",
                                    "character_tex", "description", "generator") if k in spec}
    summary.update({
        "c": str(c),
        "irreducible": bool(spec.get("irreducible")),
        "cutoff": str(H),
        "s_error": float(f"{err:.1e}"),
        "gap": str(gap) if gap is not None else None,
        "blocks": blocks_out,
        "n_blocks": nb,
    })
    if spec.get("irreducible"):
        prim = {}
        for i, j, coef in spec["Z"]:
            key = (rat(spec["blocks"][i]["h"]), rat(spec["blocks"][j]["h"]))
            p = prim.setdefault(key, {"h": str(key[0]), "hb": str(key[1]), "mult": 0, "pairs": []})
            p["mult"] += int(rat(coef))
            p["pairs"].append([i, j, int(rat(coef))])
        summary["primaries"] = [prim[k] for k in sorted(prim, key=lambda k: (k[0] + k[1], k[0]))]
    vrows = sorted(vir.items(), key=lambda kv: (kv[0][0] + kv[0][1], kv[0][0]))
    summary["virasoro"] = [[str(h), str(hb), n] for (h, hb), n in vrows[:SHOW_VIRASORO]]
    summary["n_virasoro"] = len(vrows)
    return summary, errors


# ------------------------------------------------------------- CLI

def exact_targets(spec, entries, parse_value):
    """(c, gap) from the theory file (or its family member), as Fractions or None."""
    e = next((x for x in entries if x["id"] == spec["theory"]), None)
    if e is None:
        return None, None, f"no theory '{spec['theory']}' in data/theories"
    if "member" in spec:
        at, var = str(spec["member"]["at"]), spec["member"].get("variant")
        hits = [m for m in e.get("members", []) if str(m["at"]) == at and m.get("variant") == var]
        if not hits:
            return None, None, f"'{spec['theory']}' has no member at={at} variant={var}"
        src = hits[0]
        vals = {q: src.get(q) for q in ("c", "gap")}
    else:
        if "family" in e:
            return None, None, f"'{spec['theory']}' is a family: give a member"
        vals = {q["key"]: q["value"] for q in e.get("quantities", []) if q.get("key") in ("c", "gap")}
    out = []
    for q in ("c", "gap"):
        v = parse_value(vals.get(q)) if vals.get(q) is not None else None
        out.append(v if isinstance(v, F) else None)
    return out[0], out[1], None


def main(argv):
    import jsonschema
    sys.path.insert(0, str(ROOT / "scripts"))
    import build
    entries, _ = build.load_all()
    schema = json.loads(SPECTRUM_SCHEMA.read_text())
    status = 0
    for arg in argv:
        spec = json.loads(Path(arg).read_text())
        bad = [e.message for e in jsonschema.Draft202012Validator(schema).iter_errors(spec)]
        if bad:
            print(f"✗ {arg}: schema: {bad[0]}")
            status = 1
            continue
        c_ex, gap_ex, problem = exact_targets(spec, entries, build.parse_value)
        summary, errors = check(spec, c_ex, gap_ex)
        if problem:
            errors.insert(0, problem)
        want = expected_path(spec["theory"], spec.get("member"))
        if Path(arg).resolve() != (ROOT / want).resolve():
            errors.append(f"file should be at {want}")
        if errors:
            status = 1
            print(f"✗ {arg}")
            for e in errors:
                print(f"    {e}")
        else:
            v = summary["virasoro"]
            print(f"✓ {arg}: c = {summary['c']}, cutoff h <= {summary['cutoff']}, "
                  f"S error {summary['s_error']:.0e}, gap {summary['gap']} (theory file: {gap_ex}), "
                  f"{summary['n_virasoro']} Virasoro primaries up to the cutoff")
            for h, hb, n in v[:8]:
                print(f"      ({h}, {hb}) x {n}")
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
