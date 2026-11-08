#!/usr/bin/env python3
"""Validate the QFT Zoo data and build the static website into _site/.

    python scripts/build.py            # validate + build
    python scripts/build.py --check    # validate only (what CI runs on pull requests)
    python scripts/build.py --serve    # build, then preview at http://localhost:8000
    python scripts/build.py --data tests/flows/valid --out /tmp/site   # another data folder (test fixtures)

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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from zoo_spectrum import SPECTRA, SPECTRUM_SCHEMA, check as check_spectrum, expected_path  # noqa: E402
from reps import check_entry_reps, direct_sums, legacy_reps  # noqa: E402
from ope import STANDARD, check_entry_ope, labelled_operators, set_standard  # noqa: E402
from opfam import check_families, count as count_families  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
THEORIES = ROOT / "data" / "theories"
OPERATIONS = ROOT / "data" / "operations"
TEMPLATE = ROOT / "data" / "TEMPLATE.yaml"
SCHEMA = ROOT / "schema" / "theory.schema.json"
METHODS = ROOT / "data" / "methods.yaml"
METHODS_SCHEMA = ROOT / "schema" / "methods.schema.json"
OPE_STRUCTURES = ROOT / "data" / "three_point_structures.yaml"
OPE_SCHEMA = ROOT / "schema" / "three_point_structures.schema.json"
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

# Fields a flows_to relation may carry beyond those of other relations.
FLOW_ONLY = ("id", "flow", "target_expr")


def show_path(p: Path) -> str:
    """A path for messages: relative to the repository when it is inside it."""
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def flow_key(uv: str, rel: dict, index: int) -> str:
    """Identity of a flow: its UV entry plus the relation's `id`, or else its position
    among the UV entry's relations (stable within one build only)."""
    return f"{uv}#{rel['id']}" if "id" in rel else f"{uv}@{index}"


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


# The quantity that decreases along RG flows in each dimension (c-, F-, a-theorems; F~ in odd d).
MONOTONE = {2: ["c"], 3: ["F"], 4: ["a", "a = c"], 5: ["\\tilde F", "F"], 6: ["a", "\\tilde F"]}
_APPROX = re.compile(r"\\approx\s*(-?\d+(?:\.\d+)?)\s*$")


def monotone_value(e: dict, exact: bool = False):
    """The entry's recorded c / F / a as a number, if one of its quantities states it numerically;
    with exact=True, the pair (number, whether the value is exact: a rational with no uncertainty)."""
    syms = MONOTONE.get(e["d"], [])
    for q in e.get("quantities", []):
        if q.get("key") in syms or q.get("symbol", "").strip() in syms:
            v = str(q.get("value", "")).strip()
            num = parse_value(v)
            is_exact = isinstance(num, Fraction) and "(" not in v
            if num is None and (m := _APPROX.search(v)):
                num = float(m.group(1))
            if num is not None:
                return (float(num), is_exact) if exact else float(num)
    return (None, False) if exact else None


def flow_heights(entries: list[dict]) -> None:
    """flow_height: where a theory sits in RG-flow diagrams. Its c / F / a when recorded, otherwise its
    uv_dof (free-scalar units) times the free scalar's value in that dimension: a rough ordering only."""
    scalar = {e["d"]: monotone_value(e) for e in entries if e["id"].startswith("free-scalar-")}
    for e in entries:
        v, is_exact = monotone_value(e, exact=True)
        if v is not None:
            e["flow_height"] = {"value": v, "estimated": False, "exact": is_exact}
        elif "uv_dof" in e and scalar.get(e["d"]) is not None:
            e["flow_height"] = {"value": e["uv_dof"] * scalar[e["d"]], "estimated": True}


def fmt(x: Fraction) -> str:
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


# --------------------------------------------------------------- loading

def load_yaml(path: Path, errors: list[str]):
    """Return the parsed mapping, or None (after recording an error)."""
    rel = show_path(path)
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
        while err.validator == "oneOf" and err.context:
            # A target_expr matching neither form: report the alternative it got furthest into.
            err = max(err.context, key=lambda e: len(e.absolute_path))
        where = "/".join(str(p) for p in err.absolute_path) or "(top level)"
        out.append(f"{rel}: {where}: {err.message}")
    return out


def ref_key(k: str) -> str:
    """'kos2016, Table 2' -> 'kos2016': a refs item is a reference key, optionally with a locator after a comma."""
    return str(k).split(",", 1)[0].strip()


# Citations in prose: [@key], [@key, Sec. 4.1.1], [@key1; @key2, Eq. (3)]. See CONTRIBUTING.md, "Citations".
_CITE = re.compile(r"\[(@[^\]]*)\]")
_CITE_PART = re.compile(r"^\s*@([A-Za-z0-9_:-]+)(?:\s*,\s*(\S.*?))?\s*$")
_LEGACY = re.compile(r"\]\(https?://(?:arxiv\.org|doi\.org|dx\.doi\.org)[^)]*\)")


def prose_strings(x, path=""):
    """(path, string) for every string in an entry outside its references list and identifier fields."""
    if isinstance(x, dict):
        for k, v in x.items():
            if k in ("references", "id", "target", "refs", "competing_refs", "key", "page", "entry", "source"):
                continue
            yield from prose_strings(v, f"{path}/{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from prose_strings(v, f"{path}/{i}")
    elif isinstance(x, str):
        yield path, x


def check_citations(data: dict, rel: str, keys: list[str]) -> list[str]:
    errs = []
    for path, s in prose_strings(data):
        for m in _CITE.finditer(s):
            for part in m.group(1).split(";"):
                pm = _CITE_PART.match(part)
                if not pm:
                    errs.append(f"{rel}: {path}: malformed citation '[{m.group(1)}]' "
                                f"(write [@key] or [@key, Sec. 2]; several: [@a; @b])")
                elif pm.group(1) not in keys:
                    errs.append(f"{rel}: {path}: citation of unknown reference key '{pm.group(1)}'")
    return errs


def qualify_citations(x, eid: str):
    """Prefix each prose citation key with its entry's id ([@kos2016] -> [@ising-3d/kos2016]), so a note
    shown on another page (e.g. a flow from this entry) still finds its reference."""
    fix = lambda s: _CITE.sub(lambda m: "[" + re.sub(r"@([A-Za-z0-9_:-]+)", lambda k: f"@{eid}/{k.group(1)}", m.group(1)) + "]", s)
    if isinstance(x, dict):
        return {k: (v if k == "references" else qualify_citations(v, eid)) for k, v in x.items()}
    if isinstance(x, list):
        return [qualify_citations(v, eid) for v in x]
    return fix(x) if isinstance(x, str) else x


def legacy_citations(entries: list[dict]) -> int:
    """Prose that still cites by a direct arXiv/DOI link instead of [@key] (counted, not an error yet)."""
    return sum(len(_LEGACY.findall(s)) for e in entries for _, s in prose_strings(e))


# ---------------------------------------------------------------- methods
# A row's `method` is an abbreviation from data/methods.yaml, optionally followed by ", qualifier"
# ('CB', 'MC-BC, isotropic'). Text with a space before the first comma is legacy free text
# ('Monte Carlo (pivot algorithm)'): accepted and counted until it is migrated. See CONTRIBUTING.md, "Methods".
METHOD_INDEX: dict[str, dict] = {}
METHOD_LIST: list[dict] = []


def load_methods(errors: list[str]) -> list[dict]:
    """The methods list, validated; fills METHOD_LIST and METHOD_INDEX (abbr -> method)."""
    METHOD_LIST.clear()
    METHOD_INDEX.clear()
    rel = show_path(METHODS)
    data = load_yaml(METHODS, errors)
    if data is None:
        return []
    validator = Draft202012Validator(json.loads(METHODS_SCHEMA.read_text(encoding="utf-8")))
    errs = schema_errors(validator, data, rel)
    if errs:
        errors += errs
        return []
    methods = data["methods"]
    METHOD_LIST.extend(methods)
    for i, m in enumerate(methods):
        if m["abbr"] in METHOD_INDEX:
            errs.append(f"{rel}: methods/{i}: duplicate abbr '{m['abbr']}'")
        METHOD_INDEX[m["abbr"]] = m
    for i, m in enumerate(methods):
        seen, p = {m["abbr"]}, m.get("parent")
        while p is not None:
            if p not in METHOD_INDEX:
                errs.append(f"{rel}: methods/{i}: parent '{p}' of '{m['abbr']}' is not in the list")
                break
            if p in seen:
                errs.append(f"{rel}: methods/{i}: parents of '{m['abbr']}' form a cycle")
                break
            seen.add(p)
            p = METHOD_INDEX[p].get("parent")
    errors += errs
    return methods


def method_abbr(value: str) -> str | None:
    """'MC-BC, isotropic' -> 'MC-BC'; None for legacy free text (a space before the first comma)."""
    label = str(value).split(",", 1)[0].strip()
    return None if re.search(r"\s", label) else label


def method_rows(data: dict):
    """(location, method) of every quantity, operator and three-point value row that has a method."""
    for section in ("quantities", "operators"):
        for i, item in enumerate(data.get(section, []) or []):
            if "method" in item:
                yield f"{section}/{i}", item["method"]
    for i, item in enumerate(data.get("three_point_functions", []) or []):
        for k, v in enumerate(item["values"]):
            if "method" in v:
                yield f"three_point_functions/{i}/values/{k}", v["method"]


def check_methods(data: dict, rel: str) -> list[str]:
    errs = []
    for where, value in method_rows(data):
        abbr = method_abbr(value)
        if abbr is None:
            continue
        if abbr not in METHOD_INDEX:
            errs.append(f"{rel}: {where}: unknown method '{abbr}' (use an abbreviation from data/methods.yaml, "
                        f"e.g. 'CB' or 'MC, pivot algorithm', or add the method there)")
        elif "," in value and not value.split(",", 1)[1].strip():
            errs.append(f"{rel}: {where}: empty qualifier after '{abbr},'")
    return errs


def method_usage(entries: list[dict], methods: list[dict]) -> tuple[list[dict], int]:
    """The methods list for the site, each with the rows and entries that use it; and the number of legacy rows."""
    out = {m["abbr"]: {**m, "rows": 0, "entries": []} for m in methods}
    legacy = 0
    for e in entries:
        for _, value in method_rows(e):
            abbr = method_abbr(value)
            if abbr is None:
                legacy += 1
                continue
            m = out[abbr]
            m["rows"] += 1
            if e["id"] not in m["entries"]:
                m["entries"].append(e["id"])
    return list(out.values()), legacy


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
                if ref_key(k) not in keys:
                    errs.append(f"{rel}: {section}/{i}: unknown reference key '{k}' "
                                f"(add it to the references list)")
    qkeys = [q["key"] for q in data.get("quantities", []) if "key" in q]
    if len(qkeys) != len(set(qkeys)):
        errs.append(f"{rel}: quantities: each `key` may appear only once")
    errs += check_flows(data, rel, keys)
    errs += check_citations(data, rel, keys)
    errs += check_methods(data, rel)
    errs += check_entry_reps(data, rel)
    errs += check_entry_ope(data, rel)
    errs += check_families(data, rel)
    return errs


def flow_ref_keys(flow: dict) -> list[tuple[str, str]]:
    """Every (location, reference key) used inside a relation's `flow` block."""
    ident = flow.get("identification", {})
    out = [("flow/identification/refs", k) for k in ident.get("refs", [])]
    out += [("flow/identification/competing_refs", k) for k in ident.get("competing_refs", [])]
    for sec in ("deformations", "vevs", "tuned", "symmetry_changes"):
        for j, item in enumerate(flow.get(sec, [])):
            out += [(f"flow/{sec}/{j}/refs", k) for k in item.get("refs", [])]
    spec = flow.get("spectrum", {})
    out += [("flow/spectrum/refs", k) for k in spec.get("refs", [])]
    for j, p in enumerate(spec.get("particles", [])):
        out += [(f"flow/spectrum/particles/{j}/refs", k) for k in p.get("refs", [])]
    out += [("flow/integrability/refs", k) for k in flow.get("integrability", {}).get("refs", [])]
    return out


def expr_leaves(expr: dict, where: str):
    """(location, leaf) for every entry leaf of a target_expr, in order."""
    if "entry" in expr:
        yield where, expr
        return
    for j, term in enumerate(expr["terms"]):
        yield from expr_leaves(term["expr"], f"{where}/terms/{j}/expr")


def check_expr(expr: dict, where: str) -> list[str]:
    if "entry" in expr:
        return []
    errs = []
    if sum(t.get("multiplicity", 1) for t in expr["terms"]) < 2:
        errs.append(f"{where}: {expr['operation']} needs at least two terms (counting multiplicity)")
    for j, term in enumerate(expr["terms"]):
        errs += check_expr(term["expr"], f"{where}/terms/{j}/expr")
    return errs


def check_flows(data: dict, rel: str, keys: list[str]) -> list[str]:
    """Relation checks within one entry, mostly for structured flows_to relations."""
    errs, ids = [], []
    for i, r in enumerate(data.get("relations", [])):
        where = f"{rel}: relations/{i}"
        is_flow = r["type"] == "flows_to"
        for k in FLOW_ONLY:
            if k in r and not is_flow:
                errs.append(f"{where}: `{k}` is only allowed on flows_to relations")
        if not is_flow:
            if "target" not in r:
                errs.append(f"{where}: `target` is required")
            continue
        if ("target" in r) == ("target_expr" in r):
            errs.append(f"{where}: give exactly one of `target` and `target_expr`")
        if "id" in r:
            ids.append(r["id"])
        elif "flow" in r or "target_expr" in r:
            errs.append(f"{where}: a flow with `flow` or `target_expr` needs an `id` (a slug, unique in this entry)")
        if "target_expr" in r:
            if "flow" not in r:
                errs.append(f"{where}: a `target_expr` flow needs a `flow` block with its sources")
            for k in ("at", "variant"):
                if k in r:
                    errs.append(f"{where}: `{k}` selects a member of a plain `target`; "
                                f"put it on the entry inside `target_expr`")
            errs += check_expr(r["target_expr"], f"{where}/target_expr")
        f = r.get("flow")
        if f is None:
            continue
        if not f.get("deformations") and not f.get("vevs"):
            errs.append(f"{where}/flow: give `deformations`, `vevs` or both")
        if f["identification"]["status"] == "disputed" and not f["identification"].get("competing_refs"):
            errs.append(f"{where}/flow/identification: a disputed identification needs `competing_refs`")
        # Every statement has its own sources, unless it is standard.
        items = [(f"{sec}/{j}", x) for sec in ("deformations", "vevs", "tuned", "symmetry_changes")
                 for j, x in enumerate(f.get(sec, []))]
        items += [(k, f[k]) for k in ("spectrum", "integrability") if k in f]
        for loc, x in items:
            if not x.get("refs") and not x.get("standard"):
                errs.append(f"{where}/flow/{loc}: needs `refs` (or `standard: true` for a textbook statement)")
        for j, dfm in enumerate(f.get("deformations", [])):
            if "sign" in dfm and not str(dfm.get("sign_convention", "")).strip():
                errs.append(f"{where}/flow/deformations/{j}: `sign` needs a `sign_convention` "
                            f"(the action and normalization that fix it)")
            if dfm.get("sign") == "either" and not str(dfm.get("note", "")).strip():
                errs.append(f"{where}/flow/deformations/{j}: sign `either` needs a `note` "
                            f"saying why both signs give this flow")
        spec = f.get("spectrum")
        if spec is not None:
            if not any(k in spec for k in ("summary", "particles", "vacua", "kinks")):
                errs.append(f"{where}/flow/spectrum: give at least one of summary, particles, vacua, kinks")
        integ = f.get("integrability")
        if integ and integ["status"] != "open" and not integ.get("standard") and not str(integ.get("note", "")).strip():
            errs.append(f"{where}/flow/integrability: status `{integ['status']}` needs a `note` "
                        f"naming the evidence")
        for loc, k in flow_ref_keys(f):
            if ref_key(k) not in keys:
                errs.append(f"{where}/{loc}: unknown reference key '{k}' "
                            f"(flow references are those of this, the UV, entry)")
    dupes = sorted({x for x in ids if ids.count(x) > 1})
    if dupes:
        errs.append(f"{rel}: relations: flows_to ids must be unique in an entry: {dupes}")
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

def check_flow_links(rel: dict, where: str, by_id: dict[str, dict]) -> list[str]:
    """Cross-entry checks of a flows_to relation: composite pieces and the flow page exist."""
    errs = []
    for loc, leaf in expr_leaves(rel["target_expr"], f"{where}/target_expr") if "target_expr" in rel else ():
        ent = by_id.get(leaf["entry"])
        if ent is None:
            errs.append(f"{loc}: unknown entry '{leaf['entry']}' (no file data/theories/{leaf['entry']}.yaml)")
            continue
        if "at" in leaf or "variant" in leaf:
            if "family" not in ent:
                errs.append(f"{loc}: '{leaf['entry']}' is not a family, so `at`/`variant` cannot select a member")
            elif ent["members"] and not any(
                    str(m["at"]) == str(leaf.get("at")) and ("variant" not in leaf or m.get("variant") == leaf["variant"])
                    for m in ent["members"]):
                errs.append(f"{loc}: '{leaf['entry']}' has no member at {leaf.get('at')!r}"
                            f"{' variant ' + leaf['variant'] if 'variant' in leaf else ''}")
    page = rel.get("flow", {}).get("page")
    if page is not None:
        if page not in by_id:
            errs.append(f"{where}/flow/page: unknown entry '{page}' (no file data/theories/{page}.yaml)")
        elif "RG flow" not in by_id[page]["tags"]:
            errs.append(f"{where}/flow/page: '{page}' is not tagged 'RG flow'")
    return errs


def load_operations(errors: list[str]) -> list[dict]:
    """Pages explaining how composite theories are built (direct sum, tensor product, ...)."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator({"$ref": "#/$defs/operationPage", "$defs": schema["$defs"]})
    out = []
    for path in sorted(OPERATIONS.glob("*.yaml")) if OPERATIONS.is_dir() else []:
        rel = show_path(path)
        data = load_yaml(path, errors)
        if data is None:
            continue
        errs = schema_errors(validator, data, rel)
        if data.get("id") != path.stem:
            errs.append(f"{rel}: id '{data.get('id')}' must match the filename ('{path.stem}')")
        if not errs:
            keys = [r["key"] for r in data["references"]]
            if len(keys) != len(set(keys)):
                errs.append(f"{rel}: duplicate reference keys")
        if errs:
            errors += errs
            continue
        data["source"] = rel
        out.append(data)
    return out


def load_three_point_structures(errors: list[str]) -> list[dict]:
    """The standard three-point structures (data/three_point_structures.yaml), validated and installed for the entry checks."""
    data = load_yaml(OPE_STRUCTURES, errors)
    if data is None:
        set_standard([])
        return []
    validator = Draft202012Validator(json.loads(OPE_SCHEMA.read_text(encoding="utf-8")))
    errs = schema_errors(validator, data, show_path(OPE_STRUCTURES))
    if errs:
        errors += errs
        set_standard([])
        return []
    errors += set_standard(data["structures"])
    return data["structures"]


def load_all() -> tuple[list[dict], list[str]]:
    errors: list[str] = []
    load_methods(errors)  # before any entry: check_entry resolves method abbreviations
    load_three_point_structures(errors)  # before any entry: values may name a standard structure
    validator = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))

    for stray in sorted(THEORIES.glob("*.yml")):
        errors.append(f"{show_path(stray)}: use the .yaml extension, not .yml")

    # The template must stay valid so that copying it gives a working entry.
    tmpl = load_yaml(TEMPLATE, errors)
    if tmpl is not None:
        errors += schema_errors(validator, tmpl, show_path(TEMPLATE))
        errors += check_methods(tmpl, show_path(TEMPLATE))
        errors += check_entry_reps(tmpl, show_path(TEMPLATE))
        errors += check_entry_ope(tmpl, show_path(TEMPLATE))

    entries = []
    for path in sorted(THEORIES.glob("*.yaml")):
        rel = show_path(path)
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
        data = qualify_citations(data, data["id"])
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
            if rel["type"] == "flows_to":
                rel["flow_key"] = flow_key(e["id"], rel, i)
                errors += check_flow_links(rel, where, by_id)
            if "target_expr" in rel:
                continue  # a composite IR: no reverse link (the flow does not end at any one piece)
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
            already = any(r["type"] == inv and r.get("target") == e["id"]
                          for r in target.get("relations", []))
            if not already:
                back = {"type": inv, "target": e["id"]}
                for k in ("note", "at", "variant"):
                    if k in rel:
                        back[k] = rel[k]
                if rel["type"] == "flows_to":
                    # The flow's identity and data, with the UV entry whose references its keys name.
                    back.update({"flow_key": rel["flow_key"], "source_entry": e["id"]})
                    for k in ("id", "flow"):
                        if k in rel:
                            back[k] = rel[k]
                target["backlinks"].append(back)

    def sort_key(e):
        c = e.get("c_num")
        if c is None and e.get("members"):
            c = e["members"][0].get("c_num")
        return (e["d"], c if c is not None else 99, e["id"])

    entries.sort(key=sort_key)
    flow_heights(entries)
    return entries, errors


# --------------------------------------------------------------- spectra

def load_spectra(entries: list[dict], errors: list[str]) -> dict[str, dict]:
    """Check every data/spectra/**/*.json against its theory; attach an index
    (entry["spectra"]) and return {relative path: summary for the site}."""
    validator = Draft202012Validator(json.loads(SPECTRUM_SCHEMA.read_text(encoding="utf-8")))
    by_id = {e["id"]: e for e in entries}
    out: dict[str, dict] = {}
    for path in sorted(SPECTRA.rglob("*")) if SPECTRA.is_dir() else []:
        if path.is_dir():
            continue
        rel = show_path(path)
        if path.suffix != ".json":
            errors.append(f"{rel}: spectrum files must be .json")
            continue
        try:
            spec = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{rel}: invalid JSON: {exc}")
            continue
        errs = schema_errors(validator, spec, rel)
        if errs:
            errors += errs
            continue
        e = by_id.get(spec["theory"])
        if e is None:
            errors.append(f"{rel}: unknown theory '{spec['theory']}' (no data/theories/{spec['theory']}.yaml)")
            continue
        want = expected_path(spec["theory"], spec.get("member"))
        if rel != want:
            errors.append(f"{rel}: should be at {want}")
            continue
        if "member" in spec:
            if "family" not in e:
                errors.append(f"{rel}: '{e['id']}' is not a family, so the spectrum cannot name a member")
                continue
            at, var = str(spec["member"]["at"]), spec["member"].get("variant")
            hits = [m for m in e["members"] if str(m["at"]) == at and m.get("variant") == var]
            if not hits:
                errors.append(f"{rel}: '{e['id']}' has no member at {at}{' variant ' + var if var else ''}")
                continue
            vals = {q: hits[0].get(q) for q in ("c", "gap")}
        else:
            if "family" in e:
                errors.append(f"{rel}: '{e['id']}' is a family; say which member with \"member\"")
                continue
            vals = {q["key"]: q["value"] for q in e.get("quantities", []) if q.get("key") in ("c", "gap")}
        exact = {}
        for q in ("c", "gap"):
            v = parse_value(vals[q]) if vals.get(q) is not None else None
            exact[q] = v if isinstance(v, Fraction) else None
        summary, errs = check_spectrum(spec, exact["c"], exact["gap"])
        if errs:
            errors += [f"{rel}: {m}" for m in errs]
            continue
        summary["source"] = rel
        out[rel] = summary
        row = {"path": rel, "gap": summary["gap"], "n_blocks": summary["n_blocks"]}
        if "member" in spec:
            row.update({k: v for k, v in spec["member"].items()})
        e.setdefault("spectra", []).append(row)
    for e in entries:
        if "spectra" in e and e.get("members"):
            order = {(str(m["at"]), m.get("variant")): i for i, m in enumerate(e["members"])}
            e["spectra"].sort(key=lambda r: order.get((str(r.get("at")), r.get("variant")), 1e9))
    return out


def build(entries: list[dict], spectra: dict[str, dict], operations: list[dict], methods: list[dict]) -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SITE_SRC, OUT)
    # Cache busting: stamp the page's script and stylesheet with a hash of their contents, so that browsers fetch
    # the new ones after every change instead of serving a stale copy.
    import hashlib
    idx = OUT / "index.html"
    html = idx.read_text(encoding="utf-8")
    for asset in ("app.js", "style.css"):
        v = hashlib.sha256((OUT / asset).read_bytes()).hexdigest()[:10]
        html = html.replace(f'"{asset}"', f'"{asset}?v={v}"')
    idx.write_text(html, encoding="utf-8")
    (OUT / "data").mkdir(exist_ok=True)
    payload = {
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "repo": REPO,
        "branch": BRANCH,
        "template": TEMPLATE.read_text(encoding="utf-8"),
        "theories": entries,
        "operations": operations,
        "methods": methods,
        "three_point_structures": list(STANDARD.values()),
    }
    (OUT / "data" / "theories.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    shutil.copy(SCHEMA, OUT / "data" / "theory.schema.json")
    shutil.copy(METHODS_SCHEMA, OUT / "data" / "methods.schema.json")
    shutil.copy(OPE_SCHEMA, OUT / "data" / "three_point_structures.schema.json")
    shutil.copy(SPECTRUM_SCHEMA, OUT / "data" / "spectrum.schema.json")
    for rel, summary in spectra.items():
        dest = OUT / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(summary, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def serve(port: int) -> None:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(OUT))
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as httpd:
        print(f"Serving {show_path(OUT)}/ at http://localhost:{port}  (Ctrl-C to stop)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="validate only; do not write _site/")
    ap.add_argument("--serve", action="store_true", help="build, then serve _site/ locally")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--data", type=Path, help="data folder with theories/ (and operations/, spectra/); default data/")
    ap.add_argument("--out", type=Path, help="where to build the site; default _site/")
    args = ap.parse_args()
    global THEORIES, OPERATIONS, TEMPLATE, SPECTRA, OUT, METHODS, OPE_STRUCTURES
    if args.data:
        data = args.data.resolve()
        THEORIES, OPERATIONS, SPECTRA = data / "theories", data / "operations", data / "spectra"
        if (data / "TEMPLATE.yaml").exists():
            TEMPLATE = data / "TEMPLATE.yaml"
        if (data / "methods.yaml").exists():
            METHODS = data / "methods.yaml"
        if (data / "three_point_structures.yaml").exists():
            OPE_STRUCTURES = data / "three_point_structures.yaml"
    if args.out:
        OUT = args.out.resolve()

    entries, errors = load_all()
    operations = load_operations(errors)
    spectra = load_spectra(entries, errors) if not errors else {}
    if errors:
        print(f"✗ {len(errors)} problem(s) found:\n", file=sys.stderr)
        for e in errors:
            print(f"  • {e}", file=sys.stderr)
        return 1
    n_fam = sum("family" in e for e in entries)
    print(f"✓ {len(entries)} entries valid ({n_fam} families)")
    if operations:
        print(f"✓ {len(operations)} operation pages valid")
    print(f"✓ {len(spectra)} spectra checked (modular invariance, integrality, gaps)")
    if (n := legacy_citations(entries)):
        print(f"! {n} prose citation(s) still link to a paper directly instead of [@key] (CONTRIBUTING.md, Citations)")
    methods, n_legacy = method_usage(entries, METHOD_LIST)
    print(f"✓ {len(methods)} methods listed; {sum(m['rows'] for m in methods)} rows name one by abbreviation")
    if n_legacy:
        print(f"! {n_legacy} method(s) still free text instead of an abbreviation from data/methods.yaml (CONTRIBUTING.md, Methods)")
    n_struct = sum("global_group" in (e.get("symmetry") or {}) for e in entries)
    n_rep, n_rep_entries = legacy_reps(entries)
    print(f"✓ {n_struct} entries give structured operator representations (docs/REPRESENTATIONS.md)")
    if n_rep:
        print(f"! {n_rep} operator rep(s) in {n_rep_entries} entries still free text instead of structured "
              f"`global` / `parity` (docs/REPRESENTATIONS.md)")
    n_fn = sum(len(e.get("three_point_functions", []) or []) for e in entries)
    n_ope = sum(len(it["values"]) for e in entries for it in e.get("three_point_functions", []) or [])
    n_ope_e = sum(bool(e.get("three_point_functions")) for e in entries)
    print(f"✓ {n_fn} three-point functions in {n_ope_e} entries, {n_ope} values, each the coefficient of a named structure "
          f"({len(STANDARD)} standard structures; docs/THREE_POINT.md)")
    own_st = [s for e in entries for s in e.get("three_point_structures", []) or []]
    n_emb = sum("embedding" in s for s in [*STANDARD.values(), *own_st])
    print(f"✓ {n_emb} of {len(STANDARD) + len(own_st)} three-point structures give their embedding-space form (notation of Costa et al. 2011; docs/THREE_POINT.md 1.4)")
    if (n := labelled_operators(entries)):
        print(f"! {n} operator(s) of three-point functions named by a label instead of an operator of the entry's table (docs/THREE_POINT.md)")
    n_opfam, n_mem = count_families(entries)
    if n_opfam:
        print(f"✓ {n_opfam} operator famil{'y' if n_opfam == 1 else 'ies'} (one row for a tower of operators), "
              f"{n_mem} member row(s) listed under them (docs/REPRESENTATIONS.md, 1.7)")
    if (n := direct_sums(entries)):
        print(f"! {n} operator row(s) list several irreps at once (a direct sum); one row per irrep is clearer")

    if args.check:
        return 0
    build(entries, spectra, operations, methods)
    print(f"✓ site built in {show_path(OUT)}/")
    if args.serve:
        serve(args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
