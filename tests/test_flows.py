#!/usr/bin/env python3
"""Tests of structured flows_to relations (flow details, composite targets, flow pages).

    python tests/test_flows.py

Builds the synthetic fixtures in tests/flows/valid/ (invented theories, not physics), checks
what build.py makes of them, then breaks them in one way at a time and checks that each
break is rejected with the expected message. Needs only the build's requirements.
"""

from __future__ import annotations

import copy
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build  # noqa: E402

VALID = ROOT / "tests" / "flows" / "valid"


def load(data_dir: Path):
    build.THEORIES, build.OPERATIONS = data_dir / "theories", data_dir / "operations"
    entries, errors = build.load_all()
    operations = build.load_operations(errors)
    return entries, operations, errors


def fixture_data() -> dict[str, dict]:
    return {p.stem: yaml.safe_load(p.read_text(encoding="utf-8")) for p in sorted((VALID / "theories").glob("*.yaml"))}


def rel(data, entry, rid):
    return next(r for r in data[entry]["relations"] if r.get("id") == rid)


def check_valid() -> list[str]:
    fails = []
    entries, operations, errors = load(VALID)
    if errors:
        return [f"valid fixtures should pass, got: {errors}"]
    by_id = {e["id"]: e for e in entries}
    flows = [r for e in entries for r in e.get("relations", []) if r["type"] == "flows_to"]
    keys = [r["flow_key"] for r in flows]
    want = {"fixture-uv#positive-g", "fixture-uv#negative-g", "fixture-uv@2", "fixture-uv#two-vacua",
            "fixture-uv#branch", "fixture-ir#mixed", "fixture-ir@1", "fixture-both@0"}
    if set(keys) != want or len(keys) != len(set(keys)):
        fails.append(f"flow keys {sorted(keys)} != {sorted(want)}")
    back = [b for b in by_id["fixture-ir"]["backlinks"] if b["type"] == "flows_from"]
    if sorted(b["flow_key"] for b in back) != ["fixture-uv#negative-g", "fixture-uv#positive-g"]:
        fails.append(f"fixture-ir should get exactly the two parallel backlinks, got {back}")
    for b in back:
        if b["source_entry"] != "fixture-uv" or "flow" not in b or b["target"] != "fixture-uv":
            fails.append(f"backlink lost its origin or data: {b}")
    if [b for b in back if b["flow_key"] == "fixture-uv#positive-g"][0].get("note") is None:
        fails.append("legacy note not copied to the backlink")
    # A composite IR makes no reverse link on its pieces.
    for piece in ("fixture-tqft", "fixture-both", "fixture-family"):
        bad = [b for b in by_id[piece]["backlinks"] if b.get("flow_key", "").endswith(("two-vacua", "branch"))]
        if bad:
            fails.append(f"{piece} got a reverse link from a composite IR: {bad}")
    # The non-flow relation keeps its old reverse link and gets no flow fields.
    rt = [b for b in by_id["fixture-neither"]["backlinks"] if b["type"] == "related_to"]
    if rt != [{"type": "related_to", "target": "fixture-uv", "note": "An ordinary relation, unchanged."}]:
        fails.append(f"related_to backlink changed: {rt}")
    if [o["id"] for o in operations] != ["direct-sum"]:
        fails.append(f"operations: {operations}")
    return fails


def mutate(data, ops, f):
    data = copy.deepcopy(data)
    ops = copy.deepcopy(ops)
    f(data, ops)
    return data, ops


def flow_of(entry, rid):
    return lambda d: rel(d, entry, rid)["flow"]


P = flow_of("fixture-uv", "positive-g")
N = flow_of("fixture-uv", "negative-g")
M = flow_of("fixture-ir", "mixed")


def _set(getter, key, value):
    return lambda d, o: getter(d).__setitem__(key, value)


def _del(getter, key):
    return lambda d, o: getter(d).pop(key)


def _composite(d):
    return rel(d, "fixture-uv", "two-vacua")


def _branch(d):
    return rel(d, "fixture-uv", "branch")


# (name, mutation, expected text in some error message)
CASES = [
    ("duplicate local ids", lambda d, o: rel(d, "fixture-uv", "negative-g").__setitem__("id", "positive-g"),
     "ids must be unique"),
    ("flow without id", lambda d, o: rel(d, "fixture-uv", "negative-g").pop("id"), "needs an `id`"),
    ("flow without identification", _del(P, "identification"), "'identification' is a required property"),
    ("identification without refs", lambda d, o: P(d)["identification"].pop("refs"), "'refs' is a required property"),
    ("identification with empty refs", lambda d, o: P(d)["identification"].__setitem__("refs", []), "should be non-empty"),
    ("identification without method", lambda d, o: P(d)["identification"].pop("method"), "'method' is a required property"),
    ("unknown identification status", lambda d, o: P(d)["identification"].__setitem__("status", "likely"), "is not one of"),
    ("disputed without competing refs", lambda d, o: _composite(d)["flow"]["identification"].pop("competing_refs"),
     "a disputed identification needs `competing_refs`"),
    ("unknown competing ref key", lambda d, o: N(d)["identification"].__setitem__("competing_refs", ["nope"]),
     "flow/identification/competing_refs: unknown reference key 'nope'"),
    ("flow-level refs no longer exist", _set(P, "refs", ["review"]), "Additional properties are not allowed"),
    ("deformation without refs or standard", lambda d, o: P(d)["deformations"][0].pop("refs"),
     "flow/deformations/0: needs `refs`"),
    ("tuning without refs or standard", lambda d, o: P(d)["tuned"][0].pop("standard"), "flow/tuned/0: needs `refs`"),
    ("symmetry change without refs or standard", lambda d, o: N(d)["symmetry_changes"][0].pop("refs"),
     "flow/symmetry_changes/0: needs `refs`"),
    ("vev without refs or standard", lambda d, o: _branch(d)["flow"]["vevs"][0].pop("refs"), "flow/vevs/0: needs `refs`"),
    ("sign without convention", lambda d, o: P(d)["deformations"][0].pop("sign_convention"), "needs a `sign_convention`"),
    ("blank sign convention", lambda d, o: P(d)["deformations"][0].__setitem__("sign_convention", "  "),
     "needs a `sign_convention`"),
    ("unknown sign", lambda d, o: P(d)["deformations"][0].__setitem__("sign", "plus"), "is not one of"),
    ("either without note", lambda d, o: M(d)["deformations"][0].pop("note"), "sign `either` needs a `note`"),
    ("unknown field in deformation", lambda d, o: P(d)["deformations"][0].__setitem__("strength", 1),
     "Additional properties are not allowed"),
    ("unknown field in flow", _set(P, "direction", "down"), "Additional properties are not allowed"),
    ("no deformations or vevs", lambda d, o: (P(d).pop("deformations"),), "give `deformations`, `vevs` or both"),
    ("unknown symmetry kind", lambda d, o: P(d)["symmetry_changes"][0].__setitem__("kind", "anomalous"),
     "is not one of"),
    ("vacua zero", lambda d, o: N(d)["symmetry_changes"][0].__setitem__("vacua", 0), "less than the minimum"),
    ("dangling target", lambda d, o: rel(d, "fixture-uv", "positive-g").__setitem__("target", "no-such-theory"),
     "unknown target 'no-such-theory'"),
    ("missing nested ref key", lambda d, o: N(d)["deformations"][0].__setitem__("refs", ["nope"]),
     "flow/deformations/0/refs: unknown reference key 'nope'"),
    ("IR-only ref key is not the UV's", lambda d, o: d["fixture-ir"]["references"].append(
        {"key": "ir-only", "title": "x", "url": "https://example.org/x"}) or P(d)["identification"]["refs"].append("ir-only"),
     "unknown reference key 'ir-only'"),
    ("flow on a non-flow relation", lambda d, o: d["fixture-uv"]["relations"][-1].__setitem__("flow", copy.deepcopy(P(d))),
     "only allowed on flows_to"),
    ("id on a non-flow relation", lambda d, o: d["fixture-uv"]["relations"][-1].__setitem__("id", "x"),
     "only allowed on flows_to"),
    ("flows_from as input", lambda d, o: d["fixture-uv"]["relations"][-1].__setitem__("type", "flows_from"),
     "is not one of"),
    ("non-flow relation without target", lambda d, o: d["fixture-uv"]["relations"][-1].pop("target"),
     "`target` is required"),
    ("spectrum particle without method", lambda d, o: M(d)["spectrum"]["particles"][0].pop("method"),
     "'method' is a required property"),
    ("spectrum particle without refs", lambda d, o: M(d)["spectrum"]["particles"][0].pop("refs"),
     "'refs' is a required property"),
    ("spectrum without refs or standard", lambda d, o: _composite(d)["flow"]["spectrum"].pop("refs"),
     "flow/spectrum: needs `refs`"),
    ("empty spectrum", lambda d, o: P(d).__setitem__("spectrum", {"note": "x"}), "give at least one of"),
    ("integrability without refs or standard", lambda d, o: P(d)["integrability"].pop("refs"), "flow/integrability: needs `refs`"),
    ("integrable without evidence", lambda d, o: N(d)["integrability"].pop("note"), "needs a `note` naming the evidence"),
    ("unknown integrability status", lambda d, o: P(d)["integrability"].__setitem__("status", "maybe"), "is not one of"),
    ("page missing", _set(N, "page", "no-such-page"), "flow/page: unknown entry 'no-such-page'"),
    ("page without RG flow tag", _set(N, "page", "fixture-tqft"), "is not tagged 'RG flow'"),
    ("target and target_expr", lambda d, o: _composite(d).__setitem__("target", "fixture-ir"),
     "exactly one of `target` and `target_expr`"),
    ("neither target nor target_expr", lambda d, o: rel(d, "fixture-uv", "positive-g").pop("target"),
     "exactly one of `target` and `target_expr`"),
    ("target_expr without flow", lambda d, o: _composite(d).pop("flow"), "needs a `flow` block"),
    ("target_expr without id", lambda d, o: _composite(d).pop("id"), "needs an `id`"),
    ("at beside target_expr", lambda d, o: _composite(d).__setitem__("at", 2), "put it on the entry inside"),
    ("unknown leaf", lambda d, o: _composite(d)["target_expr"]["terms"][0]["expr"].__setitem__("entry", "nobody"),
     "target_expr/terms/0/expr: unknown entry 'nobody'"),
    ("unknown operation", lambda d, o: _composite(d)["target_expr"].__setitem__("operation", "gauging"),
     "target_expr/operation: 'gauging' is not one of"),
    ("multiplicity zero", lambda d, o: _composite(d)["target_expr"]["terms"][0].__setitem__("multiplicity", 0),
     "multiplicity: 0 is less than the minimum of 1"),
    ("leaf with an extra field", lambda d, o: _composite(d)["target_expr"]["terms"][0]["expr"].__setitem__("name", "x"),
     "Additional properties are not allowed ('name' was unexpected)"),
    ("one-term sum", lambda d, o: _composite(d)["target_expr"]["terms"][0].pop("multiplicity"),
     "needs at least two terms"),
    ("nested one-term sum", lambda d, o: _branch(d)["target_expr"]["terms"][1]["expr"]["terms"].pop(),
     "terms/1/expr: direct_sum needs at least two terms"),
    ("leaf member missing", lambda d, o: _branch(d)["target_expr"]["terms"][1]["expr"]["terms"][1]["expr"].__setitem__("at", 7),
     "'fixture-family' has no member at 7"),
    ("leaf at on a non-family", lambda d, o: _branch(d)["target_expr"]["terms"][0]["expr"].__setitem__("at", 1),
     "is not a family"),
    ("operation id mismatch", lambda d, o: o["direct-sum"].__setitem__("id", "sum"), "must match the filename"),
    ("operation without references", lambda d, o: o["direct-sum"].pop("references"), "'references' is a required property"),
]


def run_case(tmp: Path, data, ops, expected) -> str | None:
    if tmp.exists():
        shutil.rmtree(tmp)
    (tmp / "theories").mkdir(parents=True)
    (tmp / "operations").mkdir()
    for name, d in data.items():
        (tmp / "theories" / f"{name}.yaml").write_text(yaml.safe_dump(d, allow_unicode=True), encoding="utf-8")
    for name, d in ops.items():
        (tmp / "operations" / f"{name}.yaml").write_text(yaml.safe_dump(d, allow_unicode=True), encoding="utf-8")
    _, _, errors = load(tmp)
    if not any(expected in e for e in errors):
        return f"expected an error containing {expected!r}, got {errors or 'no errors'}"
    return None


def main() -> int:
    fails = [f"valid: {m}" for m in check_valid()]
    data = fixture_data()
    ops = {p.stem: yaml.safe_load(p.read_text(encoding="utf-8")) for p in sorted((VALID / "operations").glob("*.yaml"))}
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "data"
        # The fixtures survive a dump and reload unchanged (so the cases below test only their break).
        if (msg := run_case(tmp, data, ops, "")) is not None and "no errors" not in msg:
            fails.append(f"round trip: {msg}")
        _, _, errs = load(tmp)
        if errs:
            fails.append(f"round trip of the valid fixtures fails: {errs}")
        for name, f, expected in CASES:
            d, o = mutate(data, ops, f)
            if (msg := run_case(tmp, d, o, expected)) is not None:
                fails.append(f"{name}: {msg}")
    for m in fails:
        print(f"✗ {m}")
    print(f"{'✗' if fails else '✓'} structured flows: valid fixtures + {len(CASES)} rejected variants, {len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
