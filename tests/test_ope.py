#!/usr/bin/env python3
"""Tests of the three-point-function checks (scripts/ope.py; docs/THREE_POINT.md).

    python tests/test_ope.py

A valid synthetic entry passes the schema and the entry check; each of a list of mistakes is rejected with the
expected message. The standard structures are read from data/three_point_structures.yaml.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from ope import check_entry_ope, labelled_operators, set_standard  # noqa: E402

FAILS = []


def expect(cond, what):
    if not cond:
        FAILS.append(what)


std = yaml.safe_load((ROOT / "data" / "three_point_structures.yaml").read_text(encoding="utf-8"))
std_errs = list(Draft202012Validator(json.loads((ROOT / "schema" / "three_point_structures.schema.json").read_text())).iter_errors(std))
expect(not std_errs, f"data/three_point_structures.yaml fails its schema: {[e.message for e in std_errs]}")
expect(not set_standard(std["structures"]), "standard structures have duplicate ids")
theory = Draft202012Validator(json.loads((ROOT / "schema" / "theory.schema.json").read_text()))

VALID = {
    "id": "x", "name": "X", "d": 3, "summary": "s", "tags": ["CFT"],
    "references": [{"key": "a2020", "title": "A", "arxiv": "2001.00001"}, {"key": "b2021", "title": "B", "arxiv": "2101.00001"},
                   {"key": "costa2011", "title": "Spinning Conformal Correlators", "arxiv": "1107.3554"}],
    "operators": [
        {"name": "\\sigma", "Delta": "0.5", "spin": 0},
        {"name": "\\epsilon", "Delta": "1.4", "spin": 0},
        {"name": "T_{\\mu\\nu}", "Delta": 3, "spin": 2},
    ],
    "three_point_structures": [
        {"id": "a-blocks", "symbol": "f", "ref": "a2020, Eq. (2.1)", "description": "Blocks of [@a2020, Eq. (2.1)].",
         "embedding": "\\langle\\phi_1(P_1)\\phi_2(P_2)O(P_3,Z_3)\\rangle = 2^{\\ell/2} f\\, V_{3,12}^\\ell/(\\cdots)"},
        {"id": "b-blocks", "symbol": "\\lambda", "ref": "b2021, fn. 3", "form": "\\lambda\\,V_{3,12}^\\ell/P_{12}^{a}", "relation": "$\\lambda^2 = 2^\\ell f^2$ [@b2021, p. 6]"},
    ],
    "three_point_functions": [
        {"operators": ["\\sigma", "\\sigma", "\\epsilon"], "values": [
            {"structure": "scalar", "symbol": "\\lambda_{\\sigma\\sigma\\epsilon}", "value": "1.05(1)", "method": "CB", "refs": ["a2020"]},
            {"structure": "scalar", "symbol": "\\lambda_{\\sigma\\sigma\\epsilon}", "value": "1.051(2)", "method": "MC", "refs": ["b2021, Eq. (3)"]},
        ]},
        # one coefficient, determined in two bases
        {"operators": ["\\sigma", "\\sigma", "T_{\\mu\\nu}"], "values": [
            {"structure": "a-blocks", "value": "0.326(1)", "method": "CB", "refs": ["a2020"]},
            {"structure": "b-blocks", "value": "0.65(1)", "method": "CB", "refs": ["b2021"]},
        ]},
        # two elements of one standard basis
        {"operators": ["T_{\\mu\\nu}", "T_{\\mu\\nu}", "T_{\\mu\\nu}"], "values": [
            {"structure": "ttt-free-boson-3d", "value": "0.93(1)", "method": "CB", "refs": ["a2020"]},
            {"structure": "ttt-free-fermion-3d", "value": "0.013(1)", "method": "CB", "refs": ["a2020"]},
        ]},
        # an operator that is not in the table, named by label
        {"operators": ["\\sigma", "\\sigma", {"label": "\\epsilon'"}], "values": [
            {"structure": "scalar", "value": "0.05(1)", "method": "CB", "refs": ["a2020"]},
        ]},
        # a value whose structure assumes another order of the operators than the item's, and a modulus
        {"operators": ["\\sigma", "\\epsilon", "T_{\\mu\\nu}"], "values": [
            {"structure": "a-blocks", "value": "0.1(1)", "method": "CB", "refs": ["a2020"], "value_of": "modulus"},
            {"structure": "a-blocks", "value": "0.1(1)", "method": "MC", "refs": ["a2020"],
             "order": ["\\epsilon", "\\sigma", "T_{\\mu\\nu}"]},
        ]},
    ],
}

schema_errs = [e.message for e in theory.iter_errors(VALID)]
expect(not schema_errs, f"valid entry fails the schema: {schema_errs}")
errs = check_entry_ope(copy.deepcopy(VALID), "x")
expect(not errs, f"valid entry rejected: {errs}")
expect(labelled_operators([VALID]) == 1, "labelled operators are counted")


def broken(change, needle, schema=False):
    data = copy.deepcopy(VALID)
    change(data)
    errs = [e.message for e in theory.iter_errors(data)] if schema else check_entry_ope(data, "x")
    if not any(needle in e for e in errs):
        FAILS.append(f"{change.__name__}: no error containing {needle!r} (got {errs})")


def unknown_operator(d):
    d["three_point_functions"][0]["operators"][2] = "\\varepsilon"


def unknown_structure(d):
    d["three_point_functions"][0]["values"][0]["structure"] = "unit"


def shadows_standard(d):
    d["three_point_structures"].append({"id": "scalar", "ref": "a2020"})


def duplicate_structure(d):
    d["three_point_structures"].append({"id": "a-blocks", "ref": "a2020"})


def unused_structure(d):
    d["three_point_structures"].append({"id": "c-blocks", "name": "other"})


def unknown_structure_ref(d):
    d["three_point_structures"][0]["ref"] = "c2022, Eq. (1)"


def unknown_value_ref(d):
    d["three_point_functions"][0]["values"][0]["refs"] = ["c2022"]


def same_triplet_twice(d):
    d["three_point_functions"].append({"operators": ["\\epsilon", "\\sigma", "\\sigma"], "values": [
        {"structure": "scalar", "value": "1.06(1)", "method": "CB", "refs": ["a2020"]}]})


def duplicate_claim(d):
    d["three_point_functions"][0]["values"].append(copy.deepcopy(d["three_point_functions"][0]["values"][0]))


def scalar_structure_on_spinning(d):
    d["three_point_functions"][1]["values"][0]["structure"] = "scalar"


def wrong_dimension(d):
    d["d"] = 4


def no_label_or_ref(d):
    d["three_point_structures"].append({"id": "c-blocks", "symbol": "g"})  # also lacks a form


def two_operators(d):
    d["three_point_functions"][0]["operators"].pop()


def value_without_structure(d):
    del d["three_point_functions"][0]["values"][0]["structure"]


def embedding_not_a_string(d):
    d["three_point_structures"][0]["embedding"] = ["V_{3,12}"]


def embedding_with_dollars(d):
    d["three_point_structures"][0]["embedding"] = "$V_{3,12}^\\ell$"


def embedding_with_citation(d):
    d["three_point_structures"][0]["embedding"] = "V_{3,12}^\\ell [@costa2011, Eq. (4.10)]"


def order_not_a_permutation(d):
    d["three_point_functions"][4]["values"][1]["order"] = ["\\sigma", "\\sigma", "T_{\\mu\\nu}"]


def order_redundant(d):
    d["three_point_functions"][4]["values"][1]["order"] = ["\\sigma", "\\epsilon", "T_{\\mu\\nu}"]


def value_of_unknown(d):
    d["three_point_functions"][0]["values"][0]["value_of"] = "cube"


def old_key(d):
    d["ope_coefficients"] = d.pop("three_point_functions")


def standard_citation_missing(d):
    d["references"] = [r for r in d["references"] if r["key"] != "costa2011"]


broken(unknown_operator, "no operator named")
broken(unknown_structure, "unknown structure 'unit'")
broken(shadows_standard, "is a standard structure")
broken(duplicate_structure, "duplicate id 'a-blocks'")
broken(unused_structure, "not used by any value")
broken(unknown_structure_ref, "unknown reference key 'c2022'")
broken(unknown_value_ref, "unknown reference key 'c2022'")
broken(same_triplet_twice, "the same three operators")
broken(duplicate_claim, "the same value, structure, method and refs")
broken(scalar_structure_on_spinning, "needs spin 0")
broken(wrong_dimension, "is defined in d = 3")
broken(no_label_or_ref, "is not valid under any of the given schemas", schema=True)
broken(two_operators, "is too short", schema=True)
broken(value_without_structure, "'structure' is a required property", schema=True)
broken(embedding_not_a_string, "is not of type 'string'", schema=True)
broken(embedding_with_dollars, "without $...$")
broken(embedding_with_citation, "put its citations in the description")
broken(standard_citation_missing, "cites [@costa2011]")
broken(order_not_a_permutation, "order must list the three operators")
broken(order_redundant, "order is the order of `operators`")
broken(value_of_unknown, "is not one of", schema=True)
broken(old_key, "Additional properties are not allowed", schema=True)
expect("embedding" in std["structures"][0], "the standard scalar structure gives its embedding-space form")

if FAILS:
    print(f"✗ {len(FAILS)} failure(s):")
    for f in FAILS:
        print("  •", f)
    sys.exit(1)
print("✓ three-point function tests passed")
