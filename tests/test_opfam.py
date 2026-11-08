#!/usr/bin/env python3
"""Tests of operator families (scripts/opfam.py; docs/REPRESENTATIONS.md, 1.7).

    python tests/test_opfam.py

Checks expression reading and evaluation, range display, family labels, and that the entry check accepts valid
synthetic entries (a structured one with a family and a member, a legacy one, a two-parameter family) and rejects each
of a list of mistakes with the expected message. The entries are invented for the test, not physics.
"""

from __future__ import annotations

import copy
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from opfam import FamError, check_families, evaluate, range_tex, tokens  # noqa: E402
from reps import check_entry_reps  # noqa: E402

FAILS = []


def expect(cond, what):
    if not cond:
        FAILS.append(what)


def check(data):
    return check_entry_reps(data, "x") + check_families(data, "x")


# Expressions: symbols are the declared ones; implicit products; TeX fractions; O(...) is not evaluated.
S = {"k", "N", "n", "w", "R", "\\ell"}
expect(evaluate("k", S, {"k": Fraction(3)}) == 3, "k")
expect(evaluate("k(N-k)", S, {"k": Fraction(2), "N": Fraction(5)}) == 6, "k(N-k)")
expect(evaluate("2k + 1", S, {"k": Fraction(3)}) == 7, "2k + 1")
expect(evaluate("nw", S, {"n": Fraction(2), "w": Fraction(-3)}) == -6, "nw")
expect(evaluate("\\frac{n^2}{R^2} + \\frac{w^2R^2}{4}", S, {"n": Fraction(1), "w": Fraction(2), "R": Fraction(2)}) == Fraction(17, 4), "compact boson")
expect(evaluate("\\ell + 1", S, {"\\ell": Fraction(4)}) == 5, "\\ell + 1")
expect(evaluate("\\tfrac{k}{2}", S, {"k": Fraction(3)}) == Fraction(3, 2), "tfrac")
expect(evaluate("k", S, {}) is None, "unknown value gives None")
expect(evaluate("k + 1 + O(1/N)", S, {"k": Fraction(1), "N": Fraction(4)}) is None, "O(...) not evaluated")
for bad in ("m", "\\Delta", "k_1"):
    try:
        tokens(bad, S)
        FAILS.append(f"undeclared symbol {bad!r} accepted")
    except FamError:
        pass

# Range display.
expect(range_tex([{"symbol": "k", "from": 2, "to": "N"}]) == "k = 2, 3, \\dots, N", "k = 2..N")
expect(range_tex([{"symbol": "\\ell", "from": 2, "step": 2}]) == "\\ell = 2, 4, 6, \\dots", "even spins")
expect(range_tex([{"symbol": "n", "from": 0}]) == "n = 0, 1, 2, \\dots", "n >= 0")
expect(range_tex([{"symbol": "n"}, {"symbol": "w"}]) == "n, w \\in \\mathbb{Z}", "Z^2")
expect(range_tex([{"symbol": "k", "from": 1, "to": 3}]) == "k = 1, 2, 3", "short range listed")
expect("k \\neq 3" in range_tex([{"symbol": "k", "from": 1, "except": [3]}]), "except")

# A structured entry: SU(4) R-symmetry, a half-BPS-like family with one member listed separately.
VALID = {
    "d": 4, "parameters": [{"symbol": "N", "description": "x"}],
    "symmetry": {"parity": "conditional", "supercharges": 16, "global_group": [{"id": "SU(4)_R", "group": "SU(4)", "tex": "SU(4)_R"}]},
    "operators": [
        {"name": "\\mathcal{O}_k", "family": {"id": "bps", "parameters": [{"symbol": "k", "from": 2, "to": "N"}]},
         "Delta": "k", "spin": 0, "parity": "unknown", "global": {"SU(4)_R": "Dynkin(0,k,0)"},
         "multiplet": {"name": "$\\mathcal{O}_k$", "component": "primary", "type": "$\\mathcal{B}_{[0,k,0]}$",
                       "cdi": "$B_1\\bar B_1[0;0]^{(0,k,0)}_k$"}},
        {"name": "\\mathcal{O}_2", "member_of": "bps", "at": {"k": 2}, "Delta": 2, "spin": 0, "parity": "even",
         "global": {"SU(4)_R": "Dynkin(0,2,0)"}, "multiplet": {"name": "stress tensor", "component": "primary",
         "type": "$\\mathcal{B}_{[0,2,0]}$", "cdi": "$B_1\\bar B_1[0;0]^{(0,2,0)}_2$"}},
        {"name": "K", "Delta": "2 + O(g^2)", "spin": 0, "parity": "even", "global": {"SU(4)_R": "singlet"}},
    ],
}
d = copy.deepcopy(VALID)
errs = check(d)
expect(not errs, f"valid structured entry rejected: {errs}")
fam, mem = d["operators"][0], d["operators"][1]
expect(fam.get("family_view", {}).get("range") == "k = 2, 3, \\dots, N", f"range text: {fam.get('family_view')}")
expect(fam.get("family_view", {}).get("members") == 1, "member counted")
expect(fam.get("family_view", {}).get("sort") == {"Delta": 2.0, "spin": 0.0}, "family placed by its first member")
g = fam.get("irrep", {}).get("global", [{}])[0]
expect(g.get("canon") == "Dynkin(0,k,0)" and g.get("short") == "$[0,k,0]$" and not g.get("trivial"), f"family label {g}")
m = mem.get("irrep", {}).get("global", [{}])[0]
expect(g.get("sort", [])[:-1] == m.get("sort") and g["sort"] > m["sort"], "family label sorts just after its first member's irrep")
expect(mem.get("member_view", {}).get("at") == "k = 2", "member at")


def broken(change, needle, base=VALID):
    data = copy.deepcopy(base)
    change(data)
    errs = check(data)
    expect(any(needle in e for e in errs), f"{needle!r} not reported; got {errs}")


op = lambda d, i: d["operators"][i]
# Parameters and ranges.
broken(lambda d: op(d, 0)["family"]["parameters"].append({"symbol": "k"}), "declared twice")
broken(lambda d: op(d, 0)["family"]["parameters"].__setitem__(0, {"symbol": "N", "from": 2}), "already a parameter of the entry")
broken(lambda d: op(d, 0)["family"]["parameters"][0].update({"from": 5, "to": 3}), "empty range")
broken(lambda d: op(d, 0)["family"]["parameters"][0].update({"step": 0}), "positive number")
broken(lambda d: op(d, 0)["family"]["parameters"][0].update({"to": "M"}), "neither a family parameter nor a parameter")
broken(lambda d: op(d, 0)["family"]["parameters"][0].update({"from": 1, "to": 6, "step": 2}), "is not reached")
broken(lambda d: op(d, 0)["family"]["parameters"].__setitem__(0, {"symbol": "k", "step": 2}), "give `from` with `step`")
broken(lambda d: op(d, 0)["family"]["parameters"].__setitem__(0, {"symbol": "2k", "from": 2}), "is not a symbol")
# Expressions use only declared symbols; every parameter is used.
broken(lambda d: op(d, 0).update({"Delta": "m"}), "operators/0/Delta: 'm' is neither")
broken(lambda d: op(d, 0)["global"].update({"SU(4)_R": "Dynkin(0,m,0)"}), "operators/0/global/SU(4)_R")
broken(lambda d: op(d, 0)["global"].update({"SU(4)_R": "Dynkin(0,k)"}), "3 Dynkin labels")
broken(lambda d: op(d, 0)["family"]["parameters"].append({"symbol": "j", "from": 0}), "parameter 'j' appears in none")
broken(lambda d: op(d, 2).update({"degeneracy": "k"}), "an expression is for family rows")
broken(lambda d: op(d, 0).update({"member_of": "bps", "at": {"k": 2}}), "not both")
broken(lambda d: d["operators"].append(copy.deepcopy(op(d, 0))), "used twice")
# Members: an existing family, every parameter, a value in range, data that agree with the family.
broken(lambda d: op(d, 1).update({"member_of": "nope"}), "no family 'nope'")
broken(lambda d: op(d, 1).update({"at": {"j": 2}}), "give a value for each parameter")
broken(lambda d: op(d, 1).update({"at": {"k": 1}}), "below the range start")
broken(lambda d: op(d, 1).update({"at": {"k": "x"}}), "is not a number")
broken(lambda d: op(d, 1).update({"Delta": 3}), "differs from family 'bps' at k = 2")
broken(lambda d: op(d, 1).update({"spin": 1}), "operators/1/spin")
broken(lambda d: op(d, 1)["global"].update({"SU(4)_R": "Dynkin(1,0,1)"}), "but family 'bps' at k = 2 is Dynkin(0,2,0)")
broken(lambda d: op(d, 1)["multiplet"].update({"type": "long"}), "multiplet/type")
broken(lambda d: op(d, 1)["multiplet"].update({"cdi": "$B_1\\bar B_1[0;0]^{(0,3,0)}_2$"}), "multiplet/cdi")


def family_parity(d):
    op(d, 0)["parity"] = "odd"


broken(family_parity, "but family 'bps' is odd")

# A legacy (unmigrated) entry: families work with the free-text rep; an expression with an entry parameter.
LEGACY = {
    "d": 4, "parameters": [{"symbol": "N", "description": "x"}], "symmetry": {},
    "operators": [
        {"name": "\\mathrm{Tr}\\,\\phi^k", "family": {"id": "cb", "parameters": [{"symbol": "k", "from": 2, "to": "N"}]},
         "Delta": "k", "spin": 0, "rep": "singlet"},
        {"name": "Q^{(k)}", "family": {"id": "q", "parameters": [{"symbol": "k", "from": 1, "to": "N-1"}]},
         "Delta": "k(N-k)", "spin": 0, "degeneracy": "k", "rep": "x"},
        {"name": "u_3", "member_of": "q", "at": {"k": 3}, "Delta": "3(N-3)", "spin": 0, "rep": "x"},
    ],
}
d = copy.deepcopy(LEGACY)
errs = check(d)
expect(not errs, f"valid legacy entry rejected: {errs}")
expect(d["operators"][1]["family_view"]["range"] == "k = 1, 2, \\dots, N-1", f"N-1 range: {d['operators'][1]['family_view']['range']}")
broken(lambda d: op(d, 2).update({"at": {"k": 0}}), "below the range start", LEGACY)

# Two parameters, both all integers; an entry parameter in Δ; a U(1) charge as an expression.
TWO = {
    "d": 2, "parameters": [{"symbol": "R", "description": "x"}],
    "symmetry": {"parity": True, "global_group": [{"id": "U(1)_m", "group": "U(1)"}, {"id": "U(1)_w", "group": "U(1)"}]},
    "operators": [
        {"name": "V_{n,w}", "family": {"id": "v", "parameters": [{"symbol": "n"}, {"symbol": "w"}]},
         "Delta": "\\frac{n^2}{R^2} + \\frac{w^2R^2}{4}", "spin": "nw", "parity": "pair",
         "global": {"U(1)_m": "n", "U(1)_w": "w"}},
        {"name": "V_{1,0}", "member_of": "v", "at": {"n": 1, "w": 0}, "Delta": "\\frac{1}{R^2}", "spin": 0, "parity": "pair",
         "global": {"U(1)_m": 1, "U(1)_w": 0}},
    ],
}
d = copy.deepcopy(TWO)
errs = check(d)
expect(not errs, f"valid two-parameter entry rejected: {errs}")
expect(d["operators"][0]["family_view"]["range"] == "n, w \\in \\mathbb{Z}", "Z^2 range")
expect([v["short"] for v in d["operators"][0]["irrep"]["global"]] == ["charge $n$", "charge $w$"], "U(1) charge expressions")
broken(lambda d: op(d, 1).update({"global": {"U(1)_m": 2, "U(1)_w": 0}}), "U(1)_m: 2, but family 'v'", TWO)
broken(lambda d: op(d, 1).update({"spin": 1}), "operators/1/spin", TWO)

if FAILS:
    print(f"✗ {len(FAILS)} failure(s):")
    for f in FAILS:
        print("  •", f)
    sys.exit(1)
print("✓ operator family tests passed")
