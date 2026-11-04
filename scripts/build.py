#!/usr/bin/env python3
"""Validate the QFT Zoo data and build the static website into _site/.

    python scripts/build.py            # validate + build
    python scripts/build.py --check    # validate only (what CI runs on pull requests)
    python scripts/build.py --serve    # build, then preview at http://localhost:8000

Requires: pyyaml, jsonschema  (pip install -r requirements.txt)
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import functools
import http.server
import json
import operator
import os
import re
import shutil
import sys
from fractions import Fraction
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
THEORIES = ROOT / "data" / "theories"
TEMPLATE = ROOT / "data" / "TEMPLATE.yaml"
SCHEMA = ROOT / "schema" / "theory.schema.json"
SITE_SRC = ROOT / "site"
OUT = ROOT / "_site"

REPO = os.environ.get("GITHUB_REPOSITORY", "nathansbenjamin/QFT_Zoo")
BRANCH = "main"

# How a relation listed on theory A appears on its target B.
INVERSE = {
    "flows_to": "flows_from",
    "dual_to": "dual_to",
    "related_to": "related_to",
    "member_of": "has_member",
    "orbifold_of": "has_orbifold",
    "product_of": "factor_of",
    "same_partition_function": "same_partition_function",
}

# Family members computed per family for plots (the page lists `show` of them).
FAMILY_MEMBERS = 40


# --------------------------------------------------------------- numbers

class FormulaError(ValueError):
    pass


_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow}


def eval_formula(expr: str, env: dict[str, Fraction]) -> Fraction:
    """Exactly evaluate plain arithmetic (+ - * / **, parentheses, integers,
    parameter names) with Fractions. Nothing else is allowed."""
    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return Fraction(node.value)
        if isinstance(node, ast.Name) and node.id in env:
            return env[node.id]
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            left, right = ev(node.left), ev(node.right)
            if isinstance(node.op, ast.Pow):
                if right.denominator != 1:
                    raise FormulaError("only integer powers are allowed")
                return left ** int(right)
            return _OPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            v = ev(node.operand)
            return -v if isinstance(node.op, ast.USub) else v
        raise FormulaError(f"unsupported syntax: {ast.dump(node)[:60]}")
    try:
        return ev(ast.parse(expr, mode="eval"))
    except SyntaxError as exc:
        raise FormulaError(f"cannot parse '{expr}': {exc.msg}") from None
    except ZeroDivisionError:
        raise FormulaError(f"division by zero in '{expr}'") from None


_FRAC = re.compile(r"^\\[dt]?frac\{(-?\d+)\}\{(\d+)\}$")
_RAT = re.compile(r"^(-?\d+)\s*/\s*(\d+)$")
_DEC = re.compile(r"^-?\d+(\.\d+)?(\(\d+\))?$")


def parse_value(v) -> Fraction | float | None:
    """Numeric value of a simple exact or measured value, else None."""
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return Fraction(v)
    if isinstance(v, float):
        return v
    s = str(v).strip()
    if m := _FRAC.match(s) or _RAT.match(s):
        return Fraction(int(m.group(1)), int(m.group(2)))
    if _DEC.match(s):
        core = s.split("(")[0]
        return Fraction(core) if "." not in core else float(core)
    return None


def fmt(x: Fraction) -> str:
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


# --------------------------------------------------------------- loading

def load_yaml(path: Path, errors: list[str]):
    """Return the parsed mapping, or None (after recording an error)."""
    rel = path.relative_to(ROOT)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        errors.append(f"{rel}: YAML syntax error:\n    {exc}")
        return None
    if not isinstance(data, dict):
        errors.append(f"{rel}: expected a YAML mapping of fields (is the file empty?)")
        return None
    return data


def schema_errors(validator, data, rel) -> list[str]:
    out = []
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        where = "/".join(str(p) for p in err.absolute_path) or "(top level)"
        out.append(f"{rel}: {where}: {err.message}")
    return out


def check_entry(data: dict, rel: str) -> list[str]:
    """Consistency checks that JSON Schema cannot express (within one entry)."""
    errs = []
    keys = [r["key"] for r in data.get("references", [])]
    dupes = {k for k in keys if keys.count(k) > 1}
    if dupes:
        errs.append(f"{rel}: duplicate reference keys: {sorted(dupes)}")
    for section in ("quantities", "operators"):
        for i, item in enumerate(data.get(section, [])):
            for k in item.get("refs", []):
                if k not in keys:
                    errs.append(f"{rel}: {section}/{i}: unknown reference key '{k}' "
                                f"(add it to the references list)")
    qkeys = [q["key"] for q in data.get("quantities", []) if "key" in q]
    if len(qkeys) != len(set(qkeys)):
        errs.append(f"{rel}: quantities: each `key` may appear only once")
    return errs


# --------------------------------------------------------------- families

def expand_family(e: dict) -> list[str]:
    """Compute e['members'] from the family block. Returns error messages."""
    fam, rel, errs = e["family"], e["source"], []
    var_list = fam.get("variants") or [None]
    members = []

    if "members" in fam:
        if "formulas" in fam or "start" in fam:
            return [f"{rel}: family: give either `members` or `start`+`formulas`, not both"]
        for m in fam["members"]:
            row = {k: m[k] for k in ("at", "label", "note") if k in m}
            for q in ("c", "gap"):
                if q in m:
                    row[q] = str(m[q])
                    num = parse_value(m[q])
                    if num is None:
                        errs.append(f"{rel}: family/members at={m['at']}: {q} '{m[q]}' is not a number like 8/7")
                    else:
                        row[q + "_num"] = float(num)
            members.append(row)
    elif "start" in fam:
        name = fam.get("parameter", "m")
        formulas = fam.get("formulas", {})
        overrides = {(o["at"], o.get("variant")): o for o in fam.get("overrides", [])}
        values = [fam["start"] + i * fam.get("step", 1) for i in range(FAMILY_MEMBERS)]
        for (at, var) in overrides:
            if at not in values:
                errs.append(f"{rel}: family/overrides: {name}={at} is not a member of the family")
            if var is not None and var not in var_list:
                errs.append(f"{rel}: family/overrides: unknown variant '{var}'")
        for v in values:
            for var in var_list:
                row = {"at": v}
                if var is not None:
                    row["variant"] = var
                ov = overrides.get((v, var)) or overrides.get((v, None)) or {}
                for q in ("c", "gap"):
                    try:
                        if q in ov:
                            x = parse_value(ov[q])
                            if x is None:
                                raise FormulaError(f"override value '{ov[q]}' is not a number like 8/7")
                        elif q in formulas:
                            x = eval_formula(formulas[q], {name: Fraction(v)})
                        else:
                            continue
                    except FormulaError as exc:
                        errs.append(f"{rel}: family/formulas/{q}: {exc}")
                        return errs
                    row[q] = fmt(x) if isinstance(x, Fraction) else str(x)
                    row[q + "_num"] = float(x)
                if "note" in ov:
                    row["note"] = ov["note"]
                members.append(row)
    elif "span" not in fam:
        errs.append(f"{rel}: family: needs `members`, `start`+`formulas`, or `span`")

    if "span" in fam:
        sp = fam["span"]
        try:
            e["span_num"] = {"c": float(parse_value(sp["c"])), "gap": [float(parse_value(g)) for g in sp["gap"]]}
        except (TypeError, KeyError):
            errs.append(f"{rel}: family/span: c and gap must be numbers like 1 or 1/2")
    e["members"] = members
    return errs


# --------------------------------------------------------------- main load

def load_all() -> tuple[list[dict], list[str]]:
    errors: list[str] = []
    validator = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))

    for stray in sorted(THEORIES.glob("*.yml")):
        errors.append(f"{stray.relative_to(ROOT)}: use the .yaml extension, not .yml")

    # The template must stay valid so that copying it gives a working entry.
    tmpl = load_yaml(TEMPLATE, errors)
    if tmpl is not None:
        errors += schema_errors(validator, tmpl, str(TEMPLATE.relative_to(ROOT)))

    entries = []
    for path in sorted(THEORIES.glob("*.yaml")):
        rel = str(path.relative_to(ROOT))
        data = load_yaml(path, errors)
        if data is None:
            continue
        errs = schema_errors(validator, data, rel)
        if data.get("id") != path.stem:
            errs.append(f"{rel}: id '{data.get('id')}' must match the filename ('{path.stem}')")
        if not errs:
            errs += check_entry(data, rel)
        if errs:
            errors += errs
            continue
        data["source"] = rel
        if "family" in data:
            errors += expand_family(data)
            if "family" not in data["tags"]:
                data["tags"].append("family")
        for q in data.get("quantities", []):
            if q.get("key") in ("c", "gap"):
                num = parse_value(q["value"])
                if num is not None:
                    data[f"{q['key']}_num"] = float(num)
        entries.append(data)

    # Cross-entry checks: relation targets exist; add reverse links; link members.
    by_id = {e["id"]: e for e in entries}
    for e in entries:
        e.setdefault("backlinks", [])
    for e in entries:
        for i, rel in enumerate(e.get("relations", [])):
            where = f"{e['source']}: relations/{i}"
            tgt = rel["target"]
            if tgt == e["id"]:
                errors.append(f"{where}: a theory cannot relate to itself")
                continue
            if tgt not in by_id:
                errors.append(f"{where}: unknown target '{tgt}' (no file data/theories/{tgt}.yaml)")
                continue
            target = by_id[tgt]
            if rel["type"] == "member_of":
                if "family" not in target:
                    errors.append(f"{where}: member_of target '{tgt}' is not a family entry")
                    continue
                if target["members"]:
                    hits = [m for m in target["members"]
                            if str(m["at"]) == str(rel.get("at"))
                            and ("variant" not in rel or m.get("variant") == rel["variant"])]
                    if not hits:
                        errors.append(f"{where}: '{tgt}' has no member at {rel.get('at')!r}"
                                      f"{' variant ' + rel['variant'] if 'variant' in rel else ''}")
                    for m in hits:
                        m.setdefault("entries", []).append(e["id"])
            inv = INVERSE[rel["type"]]
            already = any(r["type"] == inv and r["target"] == e["id"]
                          for r in target.get("relations", []))
            if not already:
                back = {"type": inv, "target": e["id"]}
                for k in ("note", "at", "variant"):
                    if k in rel:
                        back[k] = rel[k]
                target["backlinks"].append(back)

    def sort_key(e):
        c = e.get("c_num")
        if c is None and e.get("members"):
            c = e["members"][0].get("c_num")
        return (e["d"], c if c is not None else 99, e["id"])

    entries.sort(key=sort_key)
    return entries, errors


def build(entries: list[dict]) -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SITE_SRC, OUT)
    (OUT / "data").mkdir(exist_ok=True)
    payload = {
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "repo": REPO,
        "branch": BRANCH,
        "template": TEMPLATE.read_text(encoding="utf-8"),
        "theories": entries,
    }
    (OUT / "data" / "theories.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    shutil.copy(SCHEMA, OUT / "data" / "theory.schema.json")


def serve(port: int) -> None:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(OUT))
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as httpd:
        print(f"Serving {OUT.relative_to(ROOT)}/ at http://localhost:{port}  (Ctrl-C to stop)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="validate only; do not write _site/")
    ap.add_argument("--serve", action="store_true", help="build, then serve _site/ locally")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()

    entries, errors = load_all()
    if errors:
        print(f"✗ {len(errors)} problem(s) found:\n", file=sys.stderr)
        for e in errors:
            print(f"  • {e}", file=sys.stderr)
        return 1
    n_fam = sum("family" in e for e in entries)
    print(f"✓ {len(entries)} entries valid ({n_fam} families)")

    if args.check:
        return 0
    build(entries)
    print(f"✓ site built in {OUT.relative_to(ROOT)}/")
    if args.serve:
        serve(args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
