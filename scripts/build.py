#!/usr/bin/env python3
"""Validate the QFT Zoo data and build the static website into _site/.

    python scripts/build.py            # validate + build
    python scripts/build.py --check    # validate only (what CI runs on pull requests)
    python scripts/build.py --serve    # build, then preview at http://localhost:8000

Requires: pyyaml, jsonschema  (pip install -r requirements.txt)
"""

from __future__ import annotations

import argparse
import datetime as dt
import functools
import http.server
import json
import os
import shutil
import sys
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
INVERSE = {"flows_to": "flows_from", "dual_to": "dual_to", "related_to": "related_to"}


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
    return errs


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
            errs.append(f"{rel}: id '{data.get('id')}' must match the filename "
                        f"('{path.stem}')")
        if not errs:
            errs += check_entry(data, rel)
        if errs:
            errors += errs
            continue
        data["source"] = rel
        entries.append(data)

    # Cross-entry checks: relation targets exist; add reverse links.
    by_id = {e["id"]: e for e in entries}
    for e in entries:
        e.setdefault("backlinks", [])
    for e in entries:
        for i, rel in enumerate(e.get("relations", [])):
            tgt = rel["target"]
            if tgt == e["id"]:
                errors.append(f"{e['source']}: relations/{i}: a theory cannot relate to itself")
                continue
            if tgt not in by_id:
                errors.append(f"{e['source']}: relations/{i}: unknown target '{tgt}' "
                              f"(no file data/theories/{tgt}.yaml)")
                continue
            inv = INVERSE[rel["type"]]
            target = by_id[tgt]
            already = any(r["type"] == inv and r["target"] == e["id"]
                          for r in target.get("relations", []))
            if not already:
                target["backlinks"].append(
                    {"type": inv, "target": e["id"], **({"note": rel["note"]} if "note" in rel else {})})

    entries.sort(key=lambda e: (e["d"], e["id"]))
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
    print(f"✓ {len(entries)} theories valid")

    if args.check:
        return 0
    build(entries)
    print(f"✓ site built in {OUT.relative_to(ROOT)}/")
    if args.serve:
        serve(args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
