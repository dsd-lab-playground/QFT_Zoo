"""Operator families: one operators-table row for a tower of operators whose data is known as a function of a parameter.

A family row gives `family: {id, parameters: [{symbol, from?, to?, step?, except?}]}` and writes Δ, spin, weights,
degeneracy and global labels as expressions in its parameters (and the entry's parameters): the half-BPS operators
O_k of N=4 SYM, Δ = k in [0,k,0] of SU(4)_R, k = 2, ..., N. A row that records one member separately (because it
carries something of its own, e.g. it is the stress-tensor multiplet's primary) gives `member_of: <family id>` and
`at: {k: 2}`; the site lists it under its family, never as a separate operator. This module checks families and
members and adds the display data the site uses (`family_view`, `member_view`, and `irrep` for family rows of
structured entries). Format and policy: docs/REPRESENTATIONS.md, section 1.7 and 2.7.
"""

from __future__ import annotations

import math
import re
from fractions import Fraction

from reps import BIG, UNKNOWN, RepError, label, norm_sym, parse_factor, spin_value

# TeX commands an expression may use besides its symbols: arithmetic, spacing, grouping, constants.
_ARITH = {"frac": "frac", "tfrac": "frac", "dfrac": "frac", "cdot": "*", "times": "*", "sqrt": "sqrt",
          "left": "", "right": "", "pi": "pi"}
_TEXT = {"text", "mathrm", "rm"}          # their argument is words, not symbols
_SYM = re.compile(r"(\\[A-Za-z]+|[A-Za-z])(_(?:\{[^{}]*\}|\\[A-Za-z]+|[A-Za-z0-9]))?")
# Fields of a family row that may be expressions in its parameters (name and multiplet are free text).
EXPR_FIELDS = ("Delta", "spin", "weights", "degeneracy", "lorentz")


class FamError(ValueError):
    pass


def _group_end(s: str, i: int) -> int:
    """Index after the {...} group starting at s[i] == '{'."""
    depth = 0
    for j in range(i, len(s)):
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return j + 1
    raise FamError(f"unbalanced braces in '{s}'")


def tokens(expr, symbols: set[str]) -> list[tuple[str, str]]:
    """TeX arithmetic -> [(kind, text)], kind in num, sym, op, (, ), frac, sqrt, pi, order. Raises FamError on a
    symbol that is not declared (`symbols` holds norm_sym forms) or a command that is not arithmetic."""
    s = str(expr)
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c.isspace() or c == "$":
            i += 1
        elif c.isdigit() or (c == "." and i + 1 < len(s) and s[i + 1].isdigit()):
            m = re.match(r"\d*\.?\d+", s[i:])
            out.append(("num", m.group(0)))
            i += len(m.group(0))
        elif c in "+-*/^":
            out.append(("op", c))
            i += 1
        elif c in "({[":
            out.append(("(", c))
            i += 1
        elif c in ")}]":
            out.append((")", c))
            i += 1
        elif c == "\\" and i + 1 < len(s) and not s[i + 1].isalpha():
            i += 2                                  # \, \; \! \  (spacing) and \{ \}
        else:
            m = _SYM.match(s, i)
            if not m:
                raise FamError(f"unexpected '{c}' in '{s}'")
            base, sub = m.group(1), m.group(2) or ""
            cmd = base[1:] if base.startswith("\\") else None
            if norm_sym(base + sub) in symbols:
                out.append(("sym", norm_sym(base + sub)))
                i = m.end()
            elif not sub and norm_sym(base) in symbols:
                out.append(("sym", norm_sym(base)))
                i = m.end()
            elif cmd in _TEXT:
                j = m.start(1) + len(base)
                while j < len(s) and s[j] == " ":
                    j += 1
                i = _group_end(s, j) if j < len(s) and s[j] == "{" else j
            elif cmd in _ARITH and not sub:
                if _ARITH[cmd]:
                    out.append((_ARITH[cmd], _ARITH[cmd]) if _ARITH[cmd] in ("frac", "sqrt", "pi") else ("op", "*"))
                i = m.start(1) + len(base)
            elif base == "O" and not sub and s[m.end():].lstrip().startswith("("):
                out.append(("order", "O"))           # O(1/N): an order symbol, not a parameter
                i = m.end()
            else:
                raise FamError(f"'{base + sub}' is neither a family parameter nor a parameter of the entry")
    return out


def symbols_used(expr, symbols: set[str]) -> set[str]:
    return {t for k, t in tokens(expr, symbols) if k == "sym"}


def evaluate(expr, symbols: set[str], env: dict[str, Fraction]):
    """Exact value (Fraction, or float with sqrt/pi) of a TeX arithmetic expression with every symbol in `env`; None
    when a symbol has no value (an entry parameter) or the expression has an order symbol O(...)."""
    toks = tokens(expr, symbols)
    if any(k == "order" for k, _ in toks) or any(k == "sym" and t not in env for k, t in toks):
        return None
    pos = 0

    def peek():
        return toks[pos] if pos < len(toks) else ("end", "")

    def take():
        nonlocal pos
        pos += 1
        return toks[pos - 1]

    def atom_start(t):
        return t[0] in ("num", "sym", "(", "frac", "sqrt", "pi")

    def primary():
        k, t = take()
        if k == "num":
            v = Fraction(t)
        elif k == "sym":
            v = env[t]
        elif k == "pi":
            v = math.pi
        elif k == "(":
            v = expr_()
            if take()[0] != ")":
                raise FamError(f"unbalanced parentheses in '{expr}'")
        elif k == "frac":
            a, b = primary(), primary()
            v = a / b
        elif k == "sqrt":
            v = math.sqrt(primary())
        elif (k, t) == ("op", "-"):
            return -power()
        else:
            raise FamError(f"cannot read '{expr}'")
        return v

    def power():
        v = primary()
        if peek() == ("op", "^"):
            take()
            e = primary()
            v = v ** (int(e) if isinstance(e, Fraction) and e.denominator == 1 else float(e))
        return v

    def term():
        v = power()
        while True:
            t = peek()
            if t in (("op", "*"), ("op", "/")):
                take()
                w = power()
                v = v * w if t[1] == "*" else v / w
            elif atom_start(t):                       # implicit product: 2k, nw, k(N-k)
                v = v * power()
            else:
                return v

    def expr_():
        v = -term() if peek() == ("op", "-") and take() else term()
        while peek() in (("op", "+"), ("op", "-")):
            sign = take()[1]
            w = term()
            v = v + w if sign == "+" else v - w
        return v

    try:
        v = expr_()
    except (ZeroDivisionError, IndexError, KeyError, TypeError, ValueError, OverflowError):
        return None
    if pos != len(toks):
        raise FamError(f"cannot read '{expr}'")
    return v


def number(v):
    """An at-value or range bound written as a number: 2, -1, '1/2', '\\frac{1}{2}' -> Fraction; else None."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return Fraction(v)
    try:
        r = evaluate(v, set(), {})
    except FamError:
        return None
    return Fraction(r).limit_denominator(10**6) if isinstance(r, (Fraction, float)) and r is not None else None


def _tex(v) -> str:
    if isinstance(v, Fraction):
        return str(v.numerator) if v.denominator == 1 else f"\\tfrac{{{v.numerator}}}{{{v.denominator}}}"
    return str(v)


# ------------------------------------------------------------------ ranges

def check_range(p: dict, symbols: set[str], earlier: set[str]) -> list[str]:
    """A parameter's range: from/to numbers or expressions in the entry's and earlier family parameters."""
    errs = []
    for k in ("from", "to"):
        if k in p and number(p[k]) is None:
            try:
                tokens(p[k], symbols | earlier)
            except FamError as exc:
                errs.append(f"`{k}`: {exc}")
    step = number(p.get("step", 1))
    if step is None or step <= 0:
        errs.append(f"`step` must be a positive number, not {p.get('step')!r}")
    if "step" in p and "from" not in p:
        errs.append("give `from` with `step` (the values are from, from + step, ...)")
    a, b = number(p.get("from")), number(p.get("to"))
    if a is not None and b is not None:
        if a > b:
            errs.append(f"empty range: from {p['from']} > to {p['to']}")
        elif step and (b - a) / step != int((b - a) / step):
            errs.append(f"`to` = {p['to']} is not reached from {p['from']} in steps of {p.get('step', 1)}")
    for x in p.get("except", []) or []:
        if number(x) is None:
            errs.append(f"`except` value {x!r} is not a number")
    return errs


def in_range(p: dict, v: Fraction, symbols: set[str], env: dict) -> str:
    """'' if v is an allowed value of parameter p (bounds that depend on entry parameters are not checked), else why."""
    a = evaluate(p["from"], symbols, env) if "from" in p else None
    b = evaluate(p["to"], symbols, env) if "to" in p else None
    step = number(p.get("step", 1))
    if a is not None and v < a:
        return f"below the range start {p['from']}"
    if b is not None and v > b:
        return f"above the range end {p['to']}"
    if a is not None and ((v - Fraction(a)) / step).denominator != 1:
        return f"not of the form {p['from']} + n·{p.get('step', 1)}"
    if a is None and "from" not in p and v.denominator != 1 and step == 1:
        return "not an integer"
    if any(number(x) == v for x in p.get("except", []) or []):
        return "excluded by `except`"
    return ""


def range_tex(ps: list[dict]) -> str:
    """'k = 2, 3, \\dots, N'; '\\ell = 2, 4, 6, \\dots'; 'n, w \\in \\mathbb{Z}' (TeX, no $)."""
    parts, i = [], 0
    while i < len(ps):
        p = ps[i]
        if "from" not in p and "to" not in p:
            j = i
            while j + 1 < len(ps) and "from" not in ps[j + 1] and "to" not in ps[j + 1] and not ps[j + 1].get("except"):
                j += 1
            if p.get("except"):
                j = i
            parts.append(", ".join(q["symbol"] for q in ps[i:j + 1]) + " \\in \\mathbb{Z}" + _except(p))
            i = j + 1
            continue
        s, step = p["symbol"], number(p.get("step", 1))
        a, b = number(p.get("from")), number(p.get("to"))
        if "from" not in p:
            body = f"\\dots, {_tex(b) if b is not None else p['to']} - 1, {_tex(b) if b is not None else p['to']}"
        else:
            A = a if a is not None else None
            first = _tex(a) if a is not None else str(p["from"])
            if A is not None:
                seq = [A + n * step for n in range(3)]
                if b is not None:
                    seq = [x for x in seq if x <= b]
                    if b - A <= 3 * step:
                        seq = [A + n * step for n in range(int((b - A) / step) + 1)]
                        body = ", ".join(_tex(x) for x in seq)
                        parts.append(f"{s} = {body}{_except(p)}")
                        i += 1
                        continue
                shown = ", ".join(_tex(x) for x in seq[:2 if "to" in p else 3])
            else:
                shown = first if step != 1 else f"{first}, {first} + 1"
            body = f"{shown}, \\dots" + (f", {_tex(b) if b is not None else p['to']}" if "to" in p else "")
        parts.append(f"{s} = {body}{_except(p)}")
        i += 1
    return ";\\ ".join(parts)


def _except(p):
    ex = p.get("except") or []
    return "".join(f",\\ {p['symbol']} \\neq {_tex(number(x))}" for x in ex)


def lowest(ps: list[dict], symbols: set[str]) -> dict | None:
    """The family's first member, {symbol: value}: each parameter at its start (0 for an unbounded parameter, or the
    nearest allowed value); None when a start depends on an entry parameter."""
    env = {}
    for p in ps:
        sym = norm_sym(p["symbol"])
        if "from" in p:
            a = evaluate(p["from"], symbols, env)
            if a is None:
                return None
            v = Fraction(a)
        elif "to" in p:
            b = evaluate(p["to"], symbols, env)
            if b is None:
                return None
            v = min(Fraction(0), Fraction(b))
        else:
            v = Fraction(0)
        step = number(p.get("step", 1)) or 1
        for _ in range(10):
            if not any(number(x) == v for x in p.get("except", []) or []):
                break
            v += step
        env[sym] = v
    return env


# ------------------------------------------------------------------ labels

def substitute(s: str, symbols: set[str], env: dict) -> str | None:
    """'Dynkin(0,k,0)' at k = 2 -> 'Dynkin(0,2,0)'; 'sym(k)' -> 'sym(2)'; '2k' -> '4'. None if not evaluable."""
    try:
        return _substitute(str(s), symbols, env)
    except FamError:
        return None


def _substitute(s: str, symbols: set[str], env: dict) -> str | None:
    m = re.fullmatch(r"\s*([A-Za-z]+)\((.*)\)(bar)?\s*", s)
    if m and m.group(1) in ("Dynkin", "sym", "anti", "Y"):
        args = []
        for a in m.group(2).split(","):
            v = evaluate(a, symbols, env)
            if v is None or Fraction(v).denominator != 1:
                return None
            args.append(str(int(v)))
        return f"{m.group(1)}({','.join(args)}){m.group(3) or ''}"
    pm = s.strip().startswith("±")
    v = evaluate(s.strip().lstrip("±"), symbols, env)
    if v is None:
        return None
    v = Fraction(v)
    return ("±" if pm else "") + (str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}")


def family_label(g: dict, value, params: set[str], fparams: set[str], first: dict | None) -> dict:
    """The label of a family row for factor g: like reps.label, but it may depend on the family parameters. It sorts
    with its first member (just after an operator in that irrep), and is never trivial when it depends on them."""
    allp = params | fparams
    if isinstance(value, list):
        raise RepError("a family row gives one irrep per factor, not a direct sum")
    s = str(value).strip()
    try:
        used = symbols_used(re.sub(r"^(?:Dynkin|sym|anti|Y)\((.*)\)(?:bar)?$", r"\1", s).replace(",", " ").lstrip("±"), allp) \
            if s != UNKNOWN and not _is_word(s, allp) else set()
    except FamError as exc:
        raise RepError(str(exc)) from None
    if not used & fparams:
        return label(g, value, params)
    at_first = substitute(s, allp, first) if first is not None else None
    base = None
    if at_first is not None:
        base = label(g, at_first, params)            # raises if the first member is not an irrep
    G = f"${g['tex']}$"
    m = re.fullmatch(r"(Dynkin|sym|anti|Y)\((.*)\)(bar)?", s)
    if m and m.group(1) == "Dynkin":
        args = [a.strip() for a in m.group(2).split(",")]
        rank = (g["N"] - 1 if g["type"] == "SU" else g["N"] // 2) if isinstance(g.get("N"), int) else None
        if g["type"] not in ("SU", "Sp") or rank is None:
            raise RepError(f"Dynkin labels are for SU(N) or Sp(N) with numeric N")
        if len(args) != rank:
            raise RepError(f"{g['type']}({g['N']}) has {rank} Dynkin labels; got '{s}'")
        short = f"$[{','.join(args)}]$"
        canon = "Dynkin(" + ",".join(re.sub(r"\s", "", a) for a in args) + ")"
    elif m:
        try:
            out = label(g, s, allp)                   # sym(k), anti(k) with symbolic rank
            short, canon = out["short"], out["canon"]
        except RepError:
            canon = f"{m.group(1)}({re.sub(r'\s', '', m.group(2))}){m.group(3) or ''}"
            short = f"{'rank-$' + m.group(2) + '$ ' + ('symmetric' if m.group(1) == 'sym' else 'antisymmetric') if m.group(1) != 'Y' else 'Young diagram $(' + m.group(2) + ')$'}"
    elif g["type"] in ("U1", "Zn"):
        canon = re.sub(r"\s", "", s)
        short = f"charge ${s}$"
    else:
        raise RepError(f"a {g['type']} label cannot depend on a family parameter ('{s}')")
    return {"canon": canon, "short": short, "text": f"{G} {short}", "trivial": False,
            "sort": (base["sort"] if base else [BIG]) + [0.5], "family": True}


# ------------------------------------------------------------------ entry check

def check_families(data: dict, rel: str) -> list[str]:
    """Check the family and member rows of one entry and attach their display data."""
    errs: list[str] = []
    ops = data.get("operators") or []
    params = {norm_sym(p["symbol"]) for p in data.get("parameters", []) or []}
    sym = data.get("symmetry") or {}
    structured = "global_group" in sym
    factors = []
    if structured:
        try:
            factors = [parse_factor(f, params) for f in sym["global_group"]]
        except RepError:
            return errs                               # reported by check_entry_reps
    families: dict[str, tuple[int, dict]] = {}

    for i, o in enumerate(ops):
        if "family" not in o:
            continue
        where = f"{rel}: operators/{i}/family"
        if "member_of" in o:
            errs.append(f"{where}: a row is a family or a member of one, not both")
        fam = o["family"]
        fid = str(fam["id"])
        if fid in families:
            errs.append(f"{where}: family id '{fid}' is used twice")
        ps = fam["parameters"]
        fsyms: list[str] = []
        ok = True
        for j, p in enumerate(ps):
            s = norm_sym(p["symbol"])
            if not _SYM.fullmatch(str(p["symbol"]).strip()):
                errs.append(f"{where}/parameters/{j}: '{p['symbol']}' is not a symbol (a letter or \\command, "
                            f"optionally with a subscript)")
                ok = False
            elif s in params:
                errs.append(f"{where}/parameters/{j}: '{p['symbol']}' is already a parameter of the entry")
                ok = False
            elif s in fsyms:
                errs.append(f"{where}/parameters/{j}: '{p['symbol']}' is declared twice")
                ok = False
            bad_range = check_range(p, params, set(fsyms))
            errs += [f"{where}/parameters/{j}: {e}" for e in bad_range]
            ok = ok and not bad_range
            fsyms.append(s)
        allp = params | set(fsyms)
        used: set[str] = set()
        for k in EXPR_FIELDS:
            if k in o and not isinstance(o[k], (int, float)):
                try:
                    if k == "lorentz" or k == "weights":
                        used |= symbols_used(re.sub(r"[(),\[\]]", " ", str(o[k])), allp)
                    else:
                        used |= symbols_used(o[k], allp)
                except FamError as exc:
                    errs.append(f"{rel}: operators/{i}/{k}: {exc}")
        for f, v in (o.get("global") or {}).items():
            vs = v if isinstance(v, list) else [v]
            for x in vs:
                x = str(x)
                if x == UNKNOWN or _is_word(x, allp):
                    continue
                inner = re.sub(r"^(?:Dynkin|sym|anti|Y)\((.*)\)(?:bar)?$", r"\1", x).replace(",", " ").lstrip("±")
                try:
                    used |= symbols_used(inner, allp)
                except FamError as exc:
                    errs.append(f"{rel}: operators/{i}/global/{f}: {exc}")
        text = " ".join(str(x) for x in (o["name"], *(o.get("multiplet") or {}).values()))
        used |= {norm_sym(p["symbol"]) for p in ps if _mentions(text, p["symbol"])}
        for s in fsyms:
            if s not in used:
                errs.append(f"{where}: parameter '{s}' appears in none of the row's name, {', '.join(EXPR_FIELDS)} or "
                            f"global labels")
        if isinstance(o.get("degeneracy"), str) and not o["degeneracy"].strip():
            errs.append(f"{rel}: operators/{i}/degeneracy: empty")
        first = lowest(ps, params) if ok else None
        sort = {}
        if first is not None:
            for k in ("Delta", "spin"):
                try:
                    v = evaluate(o[k], allp, first) if k in o and not isinstance(o[k], (int, float)) else o.get(k)
                except FamError:
                    v = None
                sort[k] = float(v) if isinstance(v, (int, float, Fraction)) else None
        families[fid] = (i, {"ps": ps, "fsyms": fsyms, "allp": allp, "ok": ok})
        o["family_view"] = {"id": fid, "range": range_tex(ps) if ok else "", "first": {k: str(v) for k, v in (first or {}).items()},
                            "sort": sort, "members": 0}
        if structured and factors:
            view, bad = [], False
            g = o.get("global") or {}
            for f in factors:
                if f["id"] not in g:
                    continue
                try:
                    view.append({"factor": f["id"], **family_label(f, g[f["id"]], params, set(fsyms) if ok else set(), first)})
                except RepError as exc:
                    errs.append(f"{rel}: operators/{i}/global/{f['id']}: {exc}")
                    bad = True
            if not bad:
                o["irrep"] = {"global": view, "key": "|".join(f"{v['factor']}={v['canon']}" for v in view)}
        elif structured:
            o["irrep"] = {"global": [], "key": ""}

    for i, o in enumerate(ops):
        if "family" not in o and isinstance(o.get("degeneracy"), str):
            errs.append(f"{rel}: operators/{i}/degeneracy: an expression is for family rows; give an integer")
        if "member_of" not in o:
            continue
        where = f"{rel}: operators/{i}"
        fid = str(o["member_of"])
        if fid not in families:
            errs.append(f"{where}/member_of: no family '{fid}' in this entry "
                        f"(families: {', '.join(families) or 'none'})")
            continue
        fi, F = families[fid]
        fam = ops[fi]
        at = {norm_sym(k): v for k, v in (o.get("at") or {}).items()}
        if set(at) != set(F["fsyms"]):
            errs.append(f"{where}/at: give a value for each parameter of family '{fid}' "
                        f"({', '.join(F['fsyms'])}), and nothing else; got {', '.join(at) or 'none'}")
            continue
        env, bad = {}, False
        for p in F["ps"]:
            s = norm_sym(p["symbol"])
            v = number(at[s])
            if v is None:
                errs.append(f"{where}/at/{p['symbol']}: {at[s]!r} is not a number")
                bad = True
                continue
            why = in_range(p, v, F["allp"], env) if F["ok"] else ""
            if why:
                errs.append(f"{where}/at/{p['symbol']}: {at[s]} is {why} of family '{fid}'")
                bad = True
            env[s] = v
        if bad:
            continue
        fam["family_view"]["members"] += 1
        o["member_view"] = {"family": fid, "index": fi,
                            "at": ",\\ ".join(f"{p['symbol']} = {_tex(env[norm_sym(p['symbol'])])}" for p in F["ps"]),
                            "sort": [float(env[norm_sym(p["symbol"])]) for p in F["ps"]]}
        # The member's data must be the family's at these values, wherever both are definite.
        for k in ("Delta", "spin"):
            if k not in fam or k not in o:
                continue
            try:
                fv = evaluate(fam[k], F["allp"], env) if not isinstance(fam[k], (int, float)) else Fraction(fam[k])
            except FamError:
                fv = None
            mv = spin_value(o[k]) if k == "spin" else number(o[k])
            if fv is not None and mv is not None and abs(float(fv) - float(mv)) > 1e-12 * max(1, abs(float(fv))):
                errs.append(f"{where}/{k}: {o[k]} differs from family '{fid}' at {o['member_view']['at']} "
                            f"(its {k} {fam[k]} gives {_tex(Fraction(fv).limit_denominator(10**6))})")
        if "parity" in fam and fam["parity"] != UNKNOWN and o.get("parity") not in (None, fam["parity"]):
            errs.append(f"{where}/parity: {o['parity']}, but family '{fid}' is {fam['parity']}")
        if structured and "irrep" in o and "irrep" in fam:
            fg = fam.get("global") or {}
            for f, v in zip(factors, [fg.get(f["id"]) for f in factors]):
                mine = next((x for x in o["irrep"]["global"] if x["factor"] == f["id"]), None)
                if v is None or mine is None or str(v) == UNKNOWN or mine["canon"] == UNKNOWN:
                    continue
                at_v = substitute(str(v), F["allp"], env) if not isinstance(v, list) else None
                if at_v is None:
                    continue
                try:
                    want = label(f, at_v, params)["canon"]
                except RepError as exc:
                    errs.append(f"{where}/global/{f['id']}: family '{fid}' at {o['member_view']['at']} gives '{at_v}': {exc}")
                    continue
                if want != mine["canon"]:
                    errs.append(f"{where}/global/{f['id']}: {mine['canon']}, but family '{fid}' at "
                                f"{o['member_view']['at']} is {want}")
        for k in ("type", "cdi"):   # the family's label with the parameters set to the member's values
            mt, ft = (o.get("multiplet") or {}).get(k), (fam.get("multiplet") or {}).get(k)
            if mt and ft and _squash(mt) != _squash(_at_values(ft, F["ps"], env)):
                errs.append(f"{where}/multiplet/{k}: '{mt}', but family '{fid}' is '{ft}'")
    return errs


def _is_word(x: str, symbols: set[str]) -> bool:
    """A vocabulary word ('singlet', 'even', 'adjoint'), as opposed to an expression in parameters ('k', 'nw')."""
    if not re.fullmatch(r"[A-Za-z]+", x):
        return False
    try:
        return not symbols_used(x, symbols)
    except FamError:
        return True


def _at_values(text: str, ps: list[dict], env: dict) -> str:
    """TeX text with each plain parameter symbol replaced by its value: '[0,k,0]' at k = 2 gives '[0,2,0]'."""
    for p in ps:
        sym = str(p["symbol"]).strip()
        if re.fullmatch(r"[A-Za-z]+", sym):
            text = re.sub(r"(?<![A-Za-z\\])" + re.escape(sym) + r"(?![A-Za-z])", lambda _m, v=_tex(env[norm_sym(sym)]): v, text)
    return text


def _squash(text: str) -> str:
    return re.sub(r"\s+", "", str(text))


def _mentions(text: str, symbol) -> bool:
    """Whether TeX text mentions a symbol: k in 'O_k' or '\\mathcal{O}_{[0,k,0]}', \\ell in 'J_\\ell'."""
    m = _SYM.fullmatch(str(symbol).strip())
    if not m:
        return False
    base, sub = m.group(1), (m.group(2) or "").lstrip("_").strip("{}")
    pat = ("" if base.startswith("\\") else r"(?<![A-Za-z\\])") + re.escape(base) + r"(?![A-Za-z])"
    if sub:
        pat += r"_\{?" + re.escape(sub) + r"\}?"
    return re.search(pat, text) is not None


def count(entries: list[dict]) -> tuple[int, int]:
    """(family rows, member rows) over all entries."""
    ops = [o for e in entries for o in e.get("operators", []) or []]
    return sum("family" in o for o in ops), sum("member_of" in o for o in ops)
