"""OPE coefficients: the standard structures (data/ope_structures.yaml) and the checks of an entry's
`ope_structures` and `ope_coefficients` that JSON Schema cannot express. See docs/OPE.md.

An OPE coefficient item names its three operators (by their `name` in the entry's operators table, or by an
explicit `label` for one that is not in the table) and lists values, each of which names the structure it
multiplies: a standard one, or one the entry defines by a citation of the formula that defines it. A structure may
also give its `embedding`: the three-point function in the embedding-space notation of Costa, Penedones, Poland and
Rychkov (arXiv:1107.3554), as a LaTeX formula.
"""

from __future__ import annotations

import re
from fractions import Fraction

STANDARD: dict[str, dict] = {}  # id -> standard structure (filled by build.py from data/ope_structures.yaml)

_CITE_KEYS = re.compile(r"\[(@[^\]]*)\]")


def _cited_keys(s: dict) -> list[str]:
    """Reference keys cited ([@key, ...]) in a structure's prose fields, in order, without repeats."""
    out: list[str] = []
    for f in ("name", "description", "relation", "embedding"):
        for m in _CITE_KEYS.finditer(str(s.get(f, ""))):
            for k in re.findall(r"@([A-Za-z0-9_:-]+)", m.group(1)):
                if k not in out:
                    out.append(k)
    return out


def _embedding_errs(s: dict, where: str) -> list[str]:
    """`embedding` is a LaTeX formula shown in display math: no $...$ delimiters, no citation inside it."""
    e = s.get("embedding")
    if e is None:
        return []
    errs = []
    if "$" in e:
        errs.append(f"{where}: embedding is a LaTeX formula, shown in display math: write it without $...$")
    if _CITE_KEYS.search(e):
        errs.append(f"{where}: embedding is a formula: put its citations in the description")
    return errs


def set_standard(structures: list[dict]) -> list[str]:
    """Install the standard structures; returns problems (duplicate ids)."""
    STANDARD.clear()
    errs = []
    for i, s in enumerate(structures):
        if s["id"] in STANDARD:
            errs.append(f"data/ope_structures.yaml: structures/{i}: duplicate id '{s['id']}'")
        errs += _embedding_errs(s, f"data/ope_structures.yaml: structures/{i}")
        STANDARD[s["id"]] = s
    return errs


def _ref_key(k: str) -> str:
    return str(k).split(",", 1)[0].strip()


def _spin(s) -> int | None:
    """An operator's spin as an integer, if it is one ('2', 2); else None (fermions, '(h,hbar)', unknown)."""
    try:
        f = Fraction(str(s).strip())
    except (ValueError, ZeroDivisionError):
        return None
    return int(f) if f.denominator == 1 else None


def op_key(o) -> tuple[str, str]:
    """('name', n) for an operator of the table, ('label', l) for one named by label."""
    return ("label", o["label"]) if isinstance(o, dict) else ("name", o)


def structures_of(data: dict) -> dict[str, dict]:
    """All structures an entry's values may name: the standard ones and the entry's own."""
    return {**STANDARD, **{s["id"]: s for s in data.get("ope_structures", []) or []}}


def check_entry_ope(data: dict, rel: str) -> list[str]:
    errs: list[str] = []
    own = data.get("ope_structures", []) or []
    items = data.get("ope_coefficients", []) or []
    keys = {r["key"] for r in data.get("references", [])}
    names: dict[str, list[dict]] = {}
    for o in data.get("operators", []) or []:
        names.setdefault(o["name"], []).append(o)

    seen_ids: set[str] = set()
    for i, s in enumerate(own):
        where = f"{rel}: ope_structures/{i}"
        if s["id"] in STANDARD:
            errs.append(f"{where}: id '{s['id']}' is a standard structure (data/ope_structures.yaml); use it, or pick another id")
        if s["id"] in seen_ids:
            errs.append(f"{where}: duplicate id '{s['id']}'")
        seen_ids.add(s["id"])
        if "ref" in s and _ref_key(s["ref"]) not in keys:
            errs.append(f"{where}: unknown reference key '{_ref_key(s['ref'])}' in ref (add it to the references list)")
        errs += _embedding_errs(s, where)
    allst = structures_of(data)

    used: set[str] = set()
    triplets: dict[tuple, int] = {}
    claims: dict[tuple, str] = {}
    for i, it in enumerate(items):
        where = f"{rel}: ope_coefficients/{i}"
        ops = it["operators"]
        for j, o in enumerate(ops):
            if not isinstance(o, dict) and o not in names:
                errs.append(f"{where}: operators/{j}: no operator named '{o}' in the operators table "
                            f"(write its `name` exactly, or {{label: '...'}} for an operator that is not in the table)")
        trip = tuple(sorted(op_key(o) for o in ops))
        if trip in triplets:
            errs.append(f"{where}: the same three operators as ope_coefficients/{triplets[trip]}: "
                        f"put all values of one three-point function in one item")
        triplets.setdefault(trip, i)
        for k, v in enumerate(it["values"]):
            w = f"{where}: values/{k}"
            sid = v["structure"]
            st = allst.get(sid)
            if st is None:
                errs.append(f"{w}: unknown structure '{sid}' (define it in ope_structures, or use one of "
                            f"data/ope_structures.yaml: {', '.join(STANDARD)})")
                continue
            used.add(sid)
            if "d" in st and st["d"] != data.get("d"):
                errs.append(f"{w}: structure '{sid}' is defined in d = {st['d']}, not d = {data.get('d')}")
            if "spins" in st:
                for j, (o, want) in enumerate(zip(ops, st["spins"])):
                    if isinstance(o, dict) or o not in names:
                        continue
                    got = {_spin(r["spin"]) for r in names[o] if "spin" in r}
                    if got and got != {want}:
                        errs.append(f"{w}: structure '{sid}' needs spin {want} for operator {j + 1}, "
                                    f"but '{o}' has spin {', '.join(str(r['spin']) for r in names[o] if 'spin' in r)}")
            for r in v.get("refs", []) or []:
                if _ref_key(r) not in keys:
                    errs.append(f"{w}: unknown reference key '{r}' (add it to the references list)")
            claim = (trip, sid, str(v.get("method", "")), tuple(sorted(map(str, v.get("refs", []) or []))),
                     re.sub(r"\s+", "", str(v["value"])))
            if claim in claims:
                errs.append(f"{w}: the same value, structure, method and refs as {claims[claim]}")
            claims.setdefault(claim, w.split(": ", 1)[1])
    # A standard structure's citations are read against the references of the entry that shows it.
    own_ids = {s["id"] for s in own}
    for sid in sorted(used - own_ids):
        for k in _cited_keys(STANDARD[sid]):
            if k not in keys:
                errs.append(f"{rel}: the standard structure '{sid}' (data/ope_structures.yaml) cites [@{k}]: "
                            f"add the reference '{k}' to the references list")
    for i, s in enumerate(own):
        if s["id"] not in used:
            errs.append(f"{rel}: ope_structures/{i}: structure '{s['id']}' is not used by any value")
    return errs


def labelled_operators(entries: list[dict]) -> int:
    """OPE operators named by an explicit label instead of the operators table (counted, not an error)."""
    return sum(isinstance(o, dict) for e in entries for it in e.get("ope_coefficients", []) or [] for o in it["operators"])
