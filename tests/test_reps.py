#!/usr/bin/env python3
"""Tests of structured operator representations (scripts/reps.py; docs/REPRESENTATIONS.md).

    python tests/test_reps.py

Checks label parsing, display, ordering and canonical forms for each group type, and that the entry check accepts a
valid synthetic entry and rejects each of a list of mistakes with the expected message.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from reps import RepError, check_entry_reps, label, parse_factor  # noqa: E402

FAILS = []


def expect(cond, what):
    if not cond:
        FAILS.append(what)


def lab(group, value, params=frozenset({"N", "N_f"}), **kw):
    return label(parse_factor({"id": "G", "group": group, **kw}, set(params)), value, set(params))


def rejects(group, value, needle, **kw):
    try:
        lab(group, value, **kw)
    except RepError as exc:
        expect(needle in str(exc), f"{group} {value!r}: message {exc} lacks {needle!r}")
        return
    FAILS.append(f"{group} {value!r} was accepted")


# Canonical forms: different spellings of one irrep agree.
expect(lab("O(3)", "vector")["canon"] == lab("O(3)", "Y(1)")["canon"] == lab("O(3)", "sym(1)")["canon"], "O(3) vector spellings")
expect(lab("O(N)", "adjoint")["canon"] == lab("O(N)", "anti(2)")["canon"] == "Y(1,1)", "O(N) adjoint = anti(2)")
expect(lab("SU(4)", "adjoint")["canon"] == lab("SU(4)", "Dynkin(1,0,1)")["canon"], "SU(4) adjoint = [1,0,1]")
expect(lab("SU(4)", "anti(2)")["canon"] == "Dynkin(0,1,0)", "SU(4) anti(2) = 6")
expect(lab("Z_3", 2)["canon"] == lab("Z_3", -1)["canon"], "Z3 charge 2 = -1")
expect(lab("S_3", "standard")["canon"] == "Y(2,1)", "S3 standard = (2,1)")
# Display.
expect(lab("Z2", "odd")["text"] == "$\\mathbb{Z}_2$-odd", "Z2 text")
expect("\\mathbf{20}'" in lab("SU(4)", "Dynkin(0,2,0)")["text"], "SU(4) 20' text")
expect("\\overline{\\mathbf{4}}" in lab("SU(4)", "antifundamental")["text"], "SU(4) 4bar text")
expect(lab("U(1)", 0)["text"] == "$U(1)$-neutral", "U(1) neutral")
expect("rank-$N_f/2$ antisymmetric" in lab("SU(N_f)", "anti(N_f/2)")["text"], "parametric rank")
expect(lab("SU(4)", "Dynkin(0,2,0)")["text"].count("[0,2,0]") == 1, "Dynkin label shown with the dimension")
# Trivial and ordering.
for g, v in [("Z2", "even"), ("U(1)", 0), ("O(3)", "singlet"), ("SU(N)", "singlet"), ("S_3", "trivial"), ("D_4", "A1")]:
    expect(lab(g, v)["trivial"], f"{g} {v} is trivial")
order = lambda g, vals: [v for v in sorted(vals, key=lambda v: lab(g, v)["sort"])]
expect(order("O(N)", ["anti(2)", "sym(2)", "vector", "singlet", "sym(4)"]) == ["singlet", "vector", "sym(2)", "anti(2)", "sym(4)"], "O(N) order")
expect(order("U(1)", [-1, 2, 1, 0, "±1"]) == [0, "±1", 1, -1, 2], "U(1) order")
expect(order("S_3", ["standard", "sign", "trivial"]) == ["trivial", "sign", "standard"], "S3 order")
expect(order("SU(N)", ["adjoint", "antifundamental", "singlet", "fundamental"]) == ["singlet", "fundamental", "antifundamental", "adjoint"], "SU(N) order")
expect(lab("SU(N)", ["adjoint", "singlet"])["canon"] == "singlet+adjoint", "direct sum, ordered")
# Invalid labels.
rejects("Z2", "+", "even")
rejects("O(3)", "Y(1,1,1,1)", "not an O(3) irrep")
rejects("O(3)", "spinor", "SO(N)")
rejects("SU(N)", "Dynkin(1,0)", "numeric N")
rejects("SU(4)", "Dynkin(1,0)", "3 Dynkin labels")
rejects("SU(N)", "anti(M)", "parameters")
rejects("S_3", "Y(2,2)", "partition of 3")
rejects("D_3", "B1", "D_3 label")
rejects("U(1)", "1.5", "charge")
rejects("U(1)", ["unknown", 1], "direct sum")
try:
    parse_factor({"id": "G", "group": "SU(M)"}, {"N"})
    FAILS.append("SU(M) without parameter M accepted")
except RepError:
    pass

# Entry checks.
VALID = {
    "d": 3, "parameters": [{"symbol": "N", "description": "x"}],
    "symmetry": {"parity": True, "global_group": [{"id": "O(N)", "group": "O(N)"}, {"id": "Z2", "group": "Z2"}]},
    "operators": [
        {"name": "a", "Delta": 1, "spin": 0, "parity": "even", "global": {"O(N)": "vector", "Z2": "odd"}, "role": "order parameter"},
        {"name": "b", "Delta": 2, "spin": 1, "parity": "unknown", "global": {"O(N)": "unknown", "Z2": "even"}},
    ],
}
errs = check_entry_reps(copy.deepcopy(VALID), "x")
expect(not errs, f"valid entry rejected: {errs}")


def broken(change, needle):
    data = copy.deepcopy(VALID)
    change(data)
    errs = check_entry_reps(data, "x")
    expect(any(needle in e for e in errs), f"{needle!r} not reported; got {errs}")


broken(lambda d: d["operators"][0].pop("parity"), "give `parity`")
broken(lambda d: d["operators"][0]["global"].pop("Z2"), "no label for ['Z2']")
broken(lambda d: d["operators"][0]["global"].update({"U1": 0}), "unknown factor")
broken(lambda d: d["operators"][0].update({"rep": "vector"}), "not the free-text `rep`")
broken(lambda d: d["symmetry"].pop("parity"), "states `parity`")
broken(lambda d: d["symmetry"].update({"parity": False}), "`parity` is given")
broken(lambda d: d["operators"][0].update({"T": "even"}), "time_reversal")
broken(lambda d: d["operators"][0].update({"lorentz": "(1/2, 0)"}), "not used in 3d")
broken(lambda d: d["operators"][0].update({"multiplet": {"name": "a", "component": "primary"}}), "supersymmetric")
broken(lambda d: d["symmetry"]["global_group"].append({"id": "Z2", "group": "Z_4"}), "unique")


def four_d(d):
    d["d"] = 4
    d["operators"][0].update({"lorentz": "(1/2, 0)", "parity": "even"})


broken(four_d, "write `pair`")


def two_d(d):
    d["d"] = 2
    d["operators"][1].update({"spin": 3, "parity": "odd"})


broken(two_d, "write `pair`")
legacy = {"d": 3, "symmetry": {}, "operators": [{"name": "a", "Delta": 1, "parity": "even"}]}
expect(any("structured symmetry declaration" in e for e in check_entry_reps(legacy, "x")), "parity on a legacy entry")

# Extension (2d batch b): symbols, SU(2) spins, parametric S_n and D_n, SL(2,R), generic G.
P = {"k", "Q", "G"}
L = lambda group, value, **kw: label(parse_factor({"id": "X", "group": group, **kw}, P), value, P)
expect(L("SU(2)", "spin(1/2)")["canon"] == L("SU(2)", "fundamental")["canon"] == "Dynkin(1)", "SU(2) spin(1/2) = doublet")
expect(L("SU(2)", "spin(3/2)")["canon"] == "Dynkin(3)", "SU(2) spin(3/2)")
expect(L("SU(2)", "spin(k/2)")["canon"] == "spin(k/2)", "SU(2) parametric spin")
expect(L("SU(2)", "spin(j)", symbols=["j"])["text"] == "$SU(2)$ spin $j$", "SU(2) spin from a symbol")
expect(L("O(n)", "sym(L)", symbols=["n", "L"])["canon"] == "sym(L)", "O(n) with formal n and running L")
expect(L("S_Q", "standard")["canon"] == "Y(1)" and L("S_Q", "trivial")["trivial"], "S_Q labels")
expect("Q-1" in L("S_Q", "standard")["text"], "S_Q standard dimension")
expect(L("D_k", "E1")["canon"] == "E1" and L("D_k", "A1")["trivial"], "D_k labels")
expect(L("SL(2,R)", "D±(j)", symbols=["j"])["canon"] == L("SL(2,R)", "D+-(j)", symbols=["j"])["canon"], "SL(2,R) D±")
expect(L("SL(2,R)", "C(1/2+i s, \\alpha)", symbols=["s", "\\alpha"])["canon"] == "C(1/2+is,\\alpha)", "SL(2,R) continuous")
expect(L("G", "hw(\\lambda)bar", symbols=["\\lambda"])["canon"] == "hw(\\lambda)bar", "generic G conjugate weight")
expect(L("G", ["singlet", "adjoint"])["canon"] == "singlet+adjoint", "generic G direct sum")
for group, value, needle, kw in [("SU(2)", "spin(j)", "symbols", {}), ("SU(2)", "spin(1/3)", "half-integer", {}),
                                 ("S_Q", "sign", "S_Q label", {}), ("D_k", "E0", "D_k label", {}),
                                 ("SL(2,R)", "D(j)", "SL(2,R) label", {"symbols": ["j"]}),
                                 ("G", "hw(\\mu)", "highest weight", {})]:
    try:
        L(group, value, **kw)
        FAILS.append(f"{group} {value!r} was accepted")
    except RepError as exc:
        expect(needle in str(exc), f"{group} {value!r}: message {exc} lacks {needle!r}")
unk = copy.deepcopy(VALID)
unk["symmetry"]["parity"] = "unknown"
for o in unk["operators"]:
    o.pop("parity")
expect(not check_entry_reps(unk, "x"), "symmetry.parity unknown (not recorded) with no operator parity")

if FAILS:
    print(f"✗ {len(FAILS)} failure(s):")
    for f in FAILS:
        print("  •", f)
    sys.exit(1)
print("✓ representation tests passed")
