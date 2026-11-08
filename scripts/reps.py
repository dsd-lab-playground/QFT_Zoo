"""Operator representations: the controlled vocabulary of irrep labels and its checks.

An entry declares its global symmetry group as a list of factors (`symmetry.global_group`), and each operator
gives a label for every factor (`global: {Z2: odd}`), its parity (`parity: even`) and, where needed, a Lorentz
representation other than symmetric traceless spin (`lorentz`). This module parses the factors and the labels,
rejects labels that are not valid for the group, and computes for each label its display text (Markdown with
$...$ math), whether it is the trivial representation, and a sort key. The site groups and orders operators with
these (site/app.js, "structured representations"). Format and policy: docs/REPRESENTATIONS.md.
"""

from __future__ import annotations

import re
from fractions import Fraction
from math import factorial

UNKNOWN = "unknown"
BIG = 10**6          # sort position of a parameter-dependent size (after every numeric one)
LAST = 10**9         # sort position of `unknown`
PARITY = ("even", "odd", "pair", "unknown")


class RepError(ValueError):
    pass


def norm_sym(s) -> str:
    """'N_{f}' and 'N_f' and ' N_f ' are the same parameter."""
    return re.sub(r"[\s{}$]", "", str(s))


# ------------------------------------------------------------------ groups

_GROUP = [
    (re.compile(r"^(?:Z_?2|\\mathbb\{Z\}_\{?2\}?)$"), lambda m: {"type": "Z2", "n": 2}),
    (re.compile(r"^(?:Z_?|\\mathbb\{Z\}_)\{?(\d+)\}?$"), lambda m: {"type": "Zn", "n": int(m.group(1))}),
    (re.compile(r"^U\(1\)$"), lambda m: {"type": "U1"}),
    (re.compile(r"^(O|SO|SU|Sp)\((.+)\)$"), lambda m: {"type": m.group(1), "N": m.group(2).strip()}),
    (re.compile(r"^S_?\{?(\d+)\}?$"), lambda m: {"type": "S", "n": int(m.group(1))}),
    (re.compile(r"^D_?\{?(\d+)\}?$"), lambda m: {"type": "D", "n": int(m.group(1))}),
    (re.compile(r"^finite$"), lambda m: {"type": "finite"}),
]


def default_tex(group: str, g: dict) -> str:
    t = g["type"]
    if t in ("Z2", "Zn"):
        return f"\\mathbb{{Z}}_{{{g['n']}}}" if g["n"] >= 10 else f"\\mathbb{{Z}}_{g['n']}"
    if t == "S" or t == "D":
        return f"{t}_{{{g['n']}}}" if g["n"] >= 10 else f"{t}_{g['n']}"
    if t == "U1":
        return "U(1)"
    if t in ("O", "SO", "SU", "Sp"):
        return f"{t}({g['N']})"
    return group


def parse_factor(f: dict, params: set[str]) -> dict:
    """A declared factor {id, group, tex?, irreps?} -> {id, type, n/N, tex, irreps}."""
    group = str(f["group"]).strip()
    for rx, mk in _GROUP:
        if m := rx.match(group):
            g = mk(m)
            break
    else:
        raise RepError(f"unknown group '{group}' (use Z2, Z_n, U(1), O(N), SO(N), SU(N), Sp(N), S_n, D_n or finite)")
    if g["type"] == "Zn" and g["n"] == 2:
        g = {"type": "Z2", "n": 2}
    if "N" in g:
        N = g["N"]
        if re.fullmatch(r"\d+", N):
            g["N"] = int(N)
            if g["type"] == "Sp" and g["N"] % 2:
                raise RepError(f"Sp(N) is written with N even, the dimension of the fundamental (Sp(2) = SU(2))")
        elif norm_sym(N) not in params:
            raise RepError(f"group size '{N}' is neither an integer nor a parameter of the entry")
    if g["type"] == "finite":
        irr = f.get("irreps") or []
        if not irr:
            raise RepError("a `finite` group needs `irreps` (the first one listed is the trivial representation)")
        labels = [str(i["label"]) for i in irr]
        if len(set(labels)) != len(labels):
            raise RepError("duplicate irrep labels")
        g["irreps"] = irr
    elif "irreps" in f:
        raise RepError("`irreps` is only for `group: finite`")
    g["id"] = str(f["id"])
    g["tex"] = f.get("tex") or default_tex(group, g)
    return g

# --- extension (2d batch a): `listed` groups -------------------------------------------------------------------------
# `group: listed` is any group outside the vocabulary that is not finite, or not a group of fixed size: a non-compact
# group with continuous series (SL(2,C) of H3+), the shift group R of a non-compact boson, U(1)^d with vector charges,
# S_Q or O(n) at non-integer Q or n. The entry gives `tex` (the group's name) and lists the irreps it uses, the trivial
# one first, exactly as for `finite`; labels are checked against that list.

_parse_factor_base = parse_factor


def parse_factor(f: dict, params: set[str]) -> dict:  # noqa: F811 (extends the definition above)
    if str(f.get("group", "")).strip() == "listed":
        if not f.get("tex"):
            raise RepError("a `listed` group needs `tex`, its display name")
        g = _parse_factor_base({**f, "group": "finite"}, params)
        g["type"] = "listed"
        return g
    return _parse_factor_base(f, params)


# --- extension (4d-and-up batch): exceptional groups E6, E7, E8, and a parameter-dependent Lie group `Lie(G)` -------
# `E_6`, `E_7`, `E_8` (or E6, E7, E8): flavor symmetries of Minahan–Nemeschansky, E-string and Seiberg theories.
# `Lie(G)`: a continuous group that differs between the members of a family and has no single type, e.g. G_L x G_R of
# conformal matter, E_n of Seiberg's 5d theories, the flavor group of each Argyres–Douglas theory; G is its display
# name. Only labels valid for every member are offered (singlet, adjoint: the adjoint of its Lie algebra, reducible
# when a member's group is not simple). Labels: see the matching block in the labels section.

_GROUP.extend([
    (re.compile(r"^E_?\{?([678])\}?$"), lambda m: {"type": "E", "n": int(m.group(1))}),
    (re.compile(r"^Lie\((.+)\)$"), lambda m: {"type": "Lie", "name": m.group(1).strip()}),
])

_default_tex_core = default_tex


def default_tex(group: str, g: dict) -> str:  # noqa: F811 (extends the definition above)
    if g["type"] == "E":
        return f"E_{g['n']}"
    if g["type"] == "Lie":
        return g["name"]
    return _default_tex_core(group, g)


# ------------------------------------------------------------------ labels

def _num(s: str, params: set[str]):
    """An integer, or a parameter expression such as 'N_f/2' (returned as a string)."""
    s = s.strip()
    if re.fullmatch(r"\d+", s):
        return int(s)
    names = re.findall(r"[A-Za-z]+(?:_\{?[A-Za-z0-9]+\}?)?", s)
    if names and all(norm_sym(n) in params for n in names) and re.fullmatch(r"[A-Za-z0-9_{}+\-*/() ]+", s):
        return s
    raise RepError(f"'{s}' is neither an integer nor an expression in the entry's parameters")


def _tuple(s: str) -> list[int]:
    s = s.strip()
    return [int(x) for x in s.split(",")] if s else []


def _ktex(k) -> str:
    return str(k) if isinstance(k, int) else k


def charge(v, n: int | None = None):
    """U(1) or Z_n charge: 1, -2, '1/2', '±1' -> (Fraction |q|, sign 0 for ±, 1 for +, 2 for -, 0 for q = 0)."""
    s = str(v).strip().replace("+-", "±")
    pm = s.startswith("±")
    s = s.lstrip("±")
    m = re.fullmatch(r"(-?\d+)(?:/(\d+))?", s)
    if not m:
        raise RepError(f"charge '{v}' is not an integer, a fraction a/b or ±q")
    q = Fraction(int(m.group(1)), int(m.group(2) or 1))
    if n is not None:
        if q.denominator != 1:
            raise RepError(f"a Z_{n} charge is an integer")
        r = int(q) % n
        q = Fraction(r - n if r > n / 2 else r)
    if pm and q == 0:
        raise RepError("±0 is not a charge")
    return abs(q), (0 if pm else (0 if q == 0 else (1 if q > 0 else 2))), pm


def qtex(a: Fraction, pm: bool, neg: bool) -> str:
    s = str(a.numerator) if a.denominator == 1 else f"\\tfrac{{{a.numerator}}}{{{a.denominator}}}"
    return ("\\pm" if pm else "-" if neg else "") + s


def su_dim(a: list[int]) -> int:
    """Weyl dimension formula for SU(N), Dynkin labels a (length N-1)."""
    N = len(a) + 1
    num, den = 1, 1
    for i in range(N):
        for j in range(i + 1, N):
            num *= sum(a[i:j]) + (j - i)
            den *= (j - i)
    return num // den


# Conventional names of small SU(3) and SU(4) irreps (the primes distinguish irreps of equal dimension).
SU_NAMES = {
    (1, 0): "3", (0, 1): "3b", (1, 1): "8", (2, 0): "6", (0, 2): "6b", (3, 0): "10", (0, 3): "10b", (2, 2): "27",
    (1, 0, 0): "4", (0, 0, 1): "4b", (0, 1, 0): "6", (1, 0, 1): "15", (2, 0, 0): "10", (0, 0, 2): "10b",
    (0, 2, 0): "20'", (1, 1, 0): "20", (0, 1, 1): "20b", (2, 0, 2): "84", (0, 3, 0): "50", (0, 4, 0): "105", (1, 2, 1): "175",
}


def bold_dim(name) -> str:
    """Bold dimension label: "20'" -> \\mathbf{20}', "4b" (conjugate) -> \\overline{\\mathbf{4}}, 15 -> \\mathbf{15}."""
    s = str(name)
    primes = len(s) - len(s.rstrip("'"))
    s = s.rstrip("'")
    core = f"\\overline{{\\mathbf{{{s[:-1]}}}}}" if s.endswith("b") else f"\\mathbf{{{s}}}"
    return core + "'" * primes


def hook_dim(p: list[int]) -> int:
    n = sum(p)
    cols = [sum(1 for r in p if r > j) for j in range(p[0])] if p else []
    h = 1
    for i, r in enumerate(p):
        for j in range(r):
            h *= (r - j - 1) + (cols[j] - i - 1) + 1
    return factorial(n) // h


def young_of(kind: str, k) -> list:
    """sym(k) -> [k]; anti(k) -> [1]*k; symbolic k stays symbolic."""
    if kind == "sym":
        return [k]
    return [1] * k if isinstance(k, int) else ["anti", k]


def label(g: dict, value, params: set[str]) -> dict:
    """Parse one factor's label -> {canon, text, trivial, sort}. A list is a direct sum."""
    G = f"${g['tex']}$"
    if isinstance(value, list):
        if len(value) < 2:
            raise RepError("a direct sum lists at least two irreps")
        parts = [label(g, v, params) for v in value]
        if any(p["canon"] == UNKNOWN for p in parts):
            raise RepError("`unknown` cannot be part of a direct sum")
        parts.sort(key=lambda p: p["sort"])
        short = " $\\oplus$ ".join(p["short"] for p in parts)
        return {"canon": "+".join(p["canon"] for p in parts), "short": short, "text": f"{G} {short}",
                "trivial": False, "sort": parts[0]["sort"] + [0.5], "sum": True}
    if isinstance(value, bool) or value is None:
        raise RepError(f"label {value!r} is not valid")
    s = str(value).strip()
    if s == UNKNOWN:
        return {"canon": UNKNOWN, "short": "representation not recorded", "text": f"{G} representation not recorded",
                "trivial": False, "sort": [LAST]}
    t = g["type"]
    out = _label(g, t, s, params, G)
    out.setdefault("text", f"{G} {out['short']}")
    return out


def _label(g, t, s, params, G):
    if (ext := _label_ext(g, t, s, params, G)) is not None:   # separate blocks of added labels, below
        return ext
    if t == "Z2":
        if s not in ("even", "odd"):
            raise RepError(f"a Z2 label is `even` or `odd`, not '{s}'")
        return {"canon": s, "short": f"{s}", "text": f"{G}-{s}", "trivial": s == "even", "sort": [0 if s == "even" else 1]}

    if t in ("Zn", "U1"):
        a, sg, pm = charge(s, g["n"] if t == "Zn" else None)
        neg = sg == 2
        canon = ("±" if pm else "-" if neg else "") + str(a)
        if a == 0:
            return {"canon": "0", "short": "neutral", "text": f"{G}-neutral", "trivial": True, "sort": [0, 0]}
        return {"canon": canon, "short": f"charge ${qtex(a, pm, neg)}$", "trivial": False, "sort": [float(a), sg]}

    if t in ("O", "SO"):
        N = g["N"]
        m = re.fullmatch(r"(sym|anti)\((.+)\)", s)
        if s == "singlet":
            rows = []
        elif s == "vector":
            rows = [1]
        elif s == "adjoint":
            rows = [1, 1]
        elif s == "spinor":
            if t != "SO":
                raise RepError("`spinor` is a label of SO(N) (declare the factor as SO(N) or Spin(N))")
            return {"canon": "spinor", "short": "spinor", "trivial": False, "sort": [BIG // 2, 0, 0]}
        elif m:
            k = _num(m.group(2), params)
            if isinstance(k, int) and k < 1:
                raise RepError(f"rank must be at least 1 in '{s}'")
            rows = young_of(m.group(1), k)
        elif (m := re.fullmatch(r"Y\(([\d,\s]*)\)", s)):
            rows = _tuple(m.group(1))
            if any(r < 1 for r in rows) or rows != sorted(rows, reverse=True):
                raise RepError(f"Young diagram rows must be positive and non-increasing in '{s}'")
        else:
            raise RepError(f"an {t}(N) label is singlet, vector, adjoint, sym(k), anti(k), Y(r1,r2,...)"
                           f"{' or spinor' if t == 'SO' else ''}; not '{s}'")
        symbolic = rows and rows[0] == "anti" or any(not isinstance(r, int) for r in rows)
        if symbolic:
            kind = "anti" if rows[0] == "anti" else "sym"
            k = rows[1] if kind == "anti" else rows[0]
            name = f"rank-${_ktex(k)}$ {'antisymmetric' if kind == 'anti' else 'symmetric traceless'}"
            return {"canon": f"{kind}({k})", "short": name, "trivial": False, "sort": [BIG, -BIG if kind == "sym" else -1, 0]}
        if isinstance(N, int):
            cols = [sum(1 for r in rows if r > j) for j in range(rows[0])] if rows else []
            c1, c2 = (cols + [0, 0])[:2]
            if t == "O" and c1 + c2 > N:
                raise RepError(f"Young diagram {tuple(rows)} is not an O({N}) irrep (first two columns longer than {N})")
            if t == "SO" and 2 * c1 > N:
                raise RepError(f"Young diagram {tuple(rows)} is not an SO({N}) irrep in this labelling (more than {N // 2} rows)")
        canon = "Y(" + ",".join(map(str, rows)) + ")"
        if not rows:
            short = "singlet"
        elif rows == [1]:
            short = "vector"
        elif rows == [1, 1]:
            short = "adjoint (rank-2 antisymmetric)"
        elif len(rows) == 1:
            short = f"rank-{rows[0]} symmetric traceless"
        elif set(rows) == {1}:
            short = f"rank-{len(rows)} antisymmetric"
        else:
            short = f"Young diagram $({','.join(map(str, rows))})$"
        return {"canon": canon, "short": short, "trivial": not rows,
                "sort": [sum(rows), *(-r for r in rows[:3]), *([0] * (3 - len(rows[:3])))]}

    if t in ("SU", "Sp"):
        N = g["N"]
        m = re.fullmatch(r"(sym|anti)\((.+)\)(bar)?", s)
        dm = re.fullmatch(r"Dynkin\(([\d,\s]*)\)", s)
        names = ["singlet", "fundamental", "antifundamental", "adjoint"] if t == "SU" else ["singlet", "fundamental", "adjoint"]
        if not (s in names or m or dm):
            raise RepError(f"an {t}(N) label is {', '.join(names)}, sym(k), anti(k){', sym(k)bar, anti(k)bar' if t == 'SU' else ''} "
                           f"or Dynkin(a1,...); not '{s}'")
        if m and m.group(3) and t != "SU":
            raise RepError("conjugate (bar) labels are for SU(N)")
        if not isinstance(N, int):
            if dm:
                raise RepError(f"Dynkin labels need a numeric N; {t}({N}) depends on a parameter")
            if s in names:
                idx, typ, conj = {"singlet": (0, 0, 0), "fundamental": (1, 0, 0), "antifundamental": (1, 0, 1), "adjoint": (2, 1, 0)}[s]
                return {"canon": s, "short": s, "trivial": s == "singlet", "sort": [idx, typ, conj]}
            k = _num(m.group(2), params)
            kind, conj = m.group(1), bool(m.group(3))
            short = f"rank-${_ktex(k)}$ {'antisymmetric' if kind == 'anti' else 'symmetric'}{' (conjugate)' if conj else ''}"
            return {"canon": f"{kind}({k}){'bar' if conj else ''}", "short": short, "trivial": False,
                    "sort": [k if isinstance(k, int) else BIG, 2 if kind == "sym" else 3, int(conj)]}
        # numeric N: everything becomes Dynkin labels
        r = N - 1 if t == "SU" else N // 2
        e = lambda i: [1 if j == i else 0 for j in range(r)]
        if s == "singlet":
            a = [0] * r
        elif s == "fundamental":
            a = e(0)
        elif s == "antifundamental":
            a = e(r - 1)
        elif s == "adjoint":
            a = [x + y for x, y in zip(e(0), e(r - 1))] if t == "SU" else [2] + [0] * (r - 1)
        elif m:
            k = _num(m.group(2), params)
            if not isinstance(k, int):
                raise RepError(f"'{s}': with numeric N give a numeric rank")
            if m.group(1) == "sym":
                a = [k] + [0] * (r - 1)
            else:
                if not 1 <= k <= r:
                    raise RepError(f"anti({k}) is not an {t}({N}) irrep")
                a = e(k - 1)
            if m.group(3):
                a = a[::-1]
        else:
            a = _tuple(dm.group(1))
            if len(a) != r or any(x < 0 for x in a):
                raise RepError(f"{t}({N}) has {r} Dynkin labels, non-negative; got '{s}'")
        dynk = f"$[{','.join(map(str, a))}]$"
        if t == "SU":
            dim = su_dim(a)
            name = SU_NAMES.get(tuple(a))
            word = {tuple([0] * r): "singlet", tuple(e(0)): "fundamental", tuple(e(r - 1)): "antifundamental",
                    tuple(x + y for x, y in zip(e(0), e(r - 1))): "adjoint"}.get(tuple(a), "")
            if N == 2:
                word = {(0,): "singlet", (1,): "doublet", (2,): "triplet (adjoint)"}.get(tuple(a), "")
            bold = f"${bold_dim(name or dim)}$"
            short = "singlet" if not any(a) else " ".join(x for x in (word, bold, "" if word else dynk) if x)
            conj = a[::-1]
            sort = [dim] + min(a, conj) + [0 if a <= conj else 1]
        else:
            short = "singlet" if not any(a) else f"{'fundamental ' if a == e(0) else 'adjoint ' if s == 'adjoint' else ''}{dynk}"
            sort = [sum(a), *a]
        return {"canon": "Dynkin(" + ",".join(map(str, a)) + ")", "short": short, "trivial": not any(a), "sort": sort}

    if t == "S":
        n = g["n"]
        if s == "trivial":
            p = [n]
        elif s == "sign":
            p = [1] * n
        elif s == "standard":
            p = [n - 1, 1]
        elif (m := re.fullmatch(r"Y\(([\d,\s]*)\)", s)):
            p = _tuple(m.group(1))
            if sum(p) != n or any(x < 1 for x in p) or p != sorted(p, reverse=True):
                raise RepError(f"'{s}' is not a partition of {n}")
        else:
            raise RepError(f"an S_n label is trivial, sign, standard or Y(partition); not '{s}'")
        dim = hook_dim(p)
        name = {(n,): "trivial", tuple([1] * n): "sign", (n - 1, 1): "standard"}.get(tuple(p))
        short = (f"{name} ({dim}-dimensional)" if name == "standard" else name) if name else f"irrep $({','.join(map(str, p))})$, dimension {dim}"
        return {"canon": "Y(" + ",".join(map(str, p)) + ")", "short": short, "trivial": p == [n], "sort": [dim, -p[0]]}

    if t == "D":
        n = g["n"]
        names = ["A1", "A2"] + (["B1", "B2"] if n % 2 == 0 else []) + [f"E{k}" for k in range(1, (n - 1) // 2 + 1)]
        if s not in names:
            raise RepError(f"a D_{n} label is one of {', '.join(names)}; not '{s}'")
        return {"canon": s, "short": f"${s[0]}_{{{s[1:]}}}$", "trivial": s == "A1", "sort": [names.index(s)]}

    if t == "finite":
        labels = [str(i["label"]) for i in g["irreps"]]
        if s not in labels:
            raise RepError(f"'{s}' is not among the declared irreps ({', '.join(labels)})")
        i = labels.index(s)
        irr = g["irreps"][i]
        short = f"${irr['tex']}$" if irr.get("tex") else s
        return {"canon": s, "short": short, "trivial": i == 0, "sort": [i]}
    raise RepError(f"unsupported group type {t}")

# --- extension (2d batch a): symbolic U(1) charges; labels of `listed` groups ----------------------------------------
# A U(1) charge may be a symbol or expression, for a row that stands for a family of operators labelled by their charge
# (momentum n of a compact boson, l/(k+2) for N=2 chiral primaries): 'n', '-n', 'l/(k+2)'. It is shown as
# "U(1) charge $n$" and sorted after every numeric charge. A `listed` group's labels are those it declares.

SYMBOLIC_CHARGE = re.compile(r"^[±-]?\(?[A-Za-z\\][A-Za-z0-9_{}\\+\-*/() ]*$")
_label_base = _label


def _label(g, t, s, params, G):  # noqa: F811 (extends the definition above)
    if t == "U1" and SYMBOLIC_CHARGE.fullmatch(s) and re.search(r"[A-Za-z]", s):
        return {"canon": f"q({s})", "short": f"charge ${s}$", "trivial": False, "sort": [BIG, 0]}
    if t == "listed":
        return _label_base(g, "finite", s, params, G)
    return _label_base(g, t, s, params, G)


# ------------------------------------------------------------------ labels: additions (3d migration batch)
# Two self-contained additions, reached through the hook at the top of _label. Each returns None for labels it does
# not handle, so the core vocabulary above is unchanged.
#
# (a) SO(8) triality names: 8v, 8s, 8c, 35v, 35s, 35c (also 28 = adjoint, 1 = singlet). They refer to a triality frame
#     in which the supercharges of a 3d N=8 SCFT are in 8v, as in Cordova-Dumitrescu-Intriligator (arXiv:1612.00809,
#     sec. 2.1.7: 8v = (1,0,0,0), 8s = (0,0,1,0), 8c = (0,0,0,1)) and in the N=8 bootstrap literature, where the
#     stress-tensor multiplet's primary is a 35c. Which of the two spinors is called s and which c is a convention:
#     use the source's name. 8v, 35v and 28 are the same irreps as vector, sym(2) and adjoint (same canonical form).
# (b) SU(N), Sp(N) with numeric N: sym(k), anti(k) with k a parameter expression, e.g. the SU(2)_C spin N_f/2 of a
#     Coulomb-branch operator of dimension N_f/2 in 3d N=4 SQED is sym(N_f) of SU(2).

SO8_TENSOR_ALIAS = {"1": "singlet", "8v": "vector", "28": "adjoint", "35v": "sym(2)"}
SO8_SPINORIAL = {"8s": ((0, 0, 1, 0), [BIG // 2, 0, 0, 0]), "8c": ((0, 0, 0, 1), [BIG // 2, 0, 0, 1]),
                 "35s": ((0, 0, 2, 0), [4, -1, -1, -1, 0]), "35c": ((0, 0, 0, 2), [4, -1, -1, -1, 1])}


def _so8_bold(name: str) -> str:
    m = re.fullmatch(r"(\d+)([vsc]?)", name)
    return f"\\mathbf{{{m.group(1)}}}" + (f"_{m.group(2)}" if m.group(2) else "")


def _label_ext(g, t, s, params, G):
    if t == "SO" and g.get("N") == 8:
        name = s.replace("_", "")
        if name in SO8_TENSOR_ALIAS:
            out = _label(g, t, SO8_TENSOR_ALIAS[name], params, G)
            out["short"] = f"{out['short']} ${_so8_bold(name)}$" if name != "1" else out["short"]
            out.pop("text", None)
            return out
        if name in SO8_SPINORIAL:
            dyn, sort = SO8_SPINORIAL[name]
            return {"canon": "D4(" + ",".join(map(str, dyn)) + ")", "short": f"${_so8_bold(name)}$", "trivial": False,
                    "sort": list(sort)}
        return None
    if t in ("SU", "Sp") and isinstance(g.get("N"), int):
        m = re.fullmatch(r"(sym|anti)\((.+)\)(bar)?", s)
        if not m or re.fullmatch(r"\s*\d+\s*", m.group(2)):
            return None
        if m.group(3) and t != "SU":
            raise RepError("conjugate (bar) labels are for SU(N)")
        k = _num(m.group(2), params)
        kind, conj = m.group(1), bool(m.group(3))
        if g["N"] == 2 and kind == "sym":
            short = f"spin ${_ktex(k)}/2$ (rank-${_ktex(k)}$ symmetric)"
        else:
            short = f"rank-${_ktex(k)}$ {'antisymmetric' if kind == 'anti' else 'symmetric'}{' (conjugate)' if conj else ''}"
        return {"canon": f"{kind}({k}){'bar' if conj else ''}", "short": short, "trivial": False,
                "sort": [BIG, 2 if kind == "sym" else 3, int(conj)]}
    return None


# --- extension (4d-and-up batch): labels of E_n and Lie(G); U(1) charges that depend on parameters ------------------
# E_6, E_7, E_8: `singlet`, `adjoint` (78, 133, 248), and for E_6 `fundamental` (27) and `antifundamental` (27bar),
# for E_7 `fundamental` (56). Lie(G): `singlet`, `adjoint`.
# U(1): besides numbers, a charge may be an expression in the entry's parameters, optionally with a sign or ±:
# '2(N_f-N_c)/N_f', '±N_c', '-N'. It sorts after every numeric charge.

E_IRREPS = {
    6: {"singlet": (1, ""), "fundamental": (27, "27"), "antifundamental": (27, "27b"), "adjoint": (78, "78")},
    7: {"singlet": (1, ""), "fundamental": (56, "56"), "adjoint": (133, "133")},
    8: {"singlet": (1, ""), "adjoint": (248, "248")},
}

_label_core = _label


def _label(g, t, s, params, G):  # noqa: F811 (extends the definition above)
    if t == "E":
        irr = E_IRREPS[g["n"]]
        if s not in irr:
            raise RepError(f"an E_{g['n']} label is {', '.join(irr)}; not '{s}'")
        dim, name = irr[s]
        if s == "singlet":
            return {"canon": s, "short": "singlet", "trivial": True, "sort": [1, 0]}
        return {"canon": s, "short": f"{s} ${bold_dim(name)}$", "trivial": False, "sort": [dim, int(name.endswith("b"))]}
    if t == "Lie":
        if s not in ("singlet", "adjoint"):
            raise RepError(f"a Lie(G) label (a group that depends on the family member) is singlet or adjoint; not '{s}'")
        return {"canon": s, "short": s, "trivial": s == "singlet", "sort": [0 if s == "singlet" else 1]}
    if t == "U1":
        try:
            charge(s)
        except RepError:
            v = s.replace("+-", "±").strip()
            sign = v[0] if v[:1] in ("±", "-", "+") else ""
            body = v[len(sign):].strip()
            try:
                e = _num(body, params)
            except RepError:
                # Not an expression in the entry's parameters: leave it to the symbolic-charge rule of the 2d batch
                # (a row standing for a family labelled by its charge, e.g. 'n'), which rejects anything else.
                return _label_core(g, t, s, params, G)
            if isinstance(e, int):
                return _label_core(g, t, s, params, G)
            pre = {"±": "\\pm ", "-": "-", "+": ""}.get(sign, "")
            canon = ("±" if sign == "±" else "-" if sign == "-" else "") + norm_sym(e)
            return {"canon": canon, "short": f"charge ${pre}{e}$", "trivial": False,
                    "sort": [BIG, {"±": 0, "": 1, "+": 1, "-": 2}[sign]]}
    return _label_core(g, t, s, params, G)


# ------------------------------------------------------------------ extension: index symbols, SU(2) spins, parametric
# S_n and D_n, SL(2,R), a generic simple group G (added with the migration of 2d entries, batch b)
#
# - A factor may declare `symbols`: names, other than the entry's parameters, that its labels may use: a running index
#   of a family of operators listed in one row (`j` in Phi_j, `L` in the L-leg operator), or a formal group size
#   (`n` in O(n) at n -> 0). They count as parameters for that factor only.
# - SU(2) (and Sp(2)): `spin(j)`, j a half-integer (the same label as Dynkin(2j)) or an expression in the parameters
#   and symbols (`spin(j)`, `spin(k/2)`).
# - S_n with n a parameter (S_Q, for Q continued in the sense of Deligne's category Rep(S_t)): `trivial`, `standard`,
#   `Y(l1,l2,...)` for the irrep [n - |l|, l1, l2, ...].
# - D_n with n a parameter (dihedral of order 2n): A1, A2, B1, B2 (n even), E1, E2, ... (E_j: the rotation acts as
#   e^{+-2 pi i j/n}).
# - `SL(2,R)`: the universal cover of SL(2,R), with the unitary irreps that occur in the SL(2,R) WZW model and the
#   adjoint: `trivial`, `adjoint`, `D+(j)`, `D-(j)`, `D±(j)` (discrete series, lowest/highest weight j; ± is a
#   conjugate pair in one row, as for charges), `C(j, alpha)` (continuous series, Casimir -j(j-1), J^3_0 in alpha + Z).
# - A group named by a parameter of the entry (`group: G`): a generic compact simple Lie group, with labels
#   `singlet`, `adjoint`, `hw(lambda)` (highest weight lambda, a parameter or symbol) and `hw(lambda)bar` (its
#   conjugate lambda^*).

_parse_factor_2db, _label_dispatch_2db, _label_public_2db = parse_factor, _label, label


def _symbols(f: dict) -> set[str]:
    return {norm_sym(s) for s in (f.get("symbols") or [])}


def _expr(s: str, params: set[str]):
    """A number or an expression in parameters and symbols (TeX names such as '\\alpha' allowed, `i` the imaginary
    unit), returned as written. Raises RepError."""
    s = s.strip()
    if re.fullmatch(r"-?\d+(?:/\d+)?", s):
        return Fraction(s)
    names = re.findall(r"\\?[A-Za-z]+(?:_\{?[A-Za-z0-9]+\}?)?", s)
    bad = [n for n in names if n != "i" and norm_sym(n) not in params]
    if not names or bad or not re.fullmatch(r"[\\A-Za-z0-9_{}+\-*/() ]+", s):
        raise RepError(f"'{s}' is neither a number nor an expression in the entry's parameters"
                       f"{' (unknown: ' + ', '.join(bad) + ')' if bad else ''}; a running index goes in the factor's `symbols`")
    return s


def parse_factor(f: dict, params: set[str]) -> dict:
    params = set(params) | _symbols(f)
    group = norm_sym(f.get("group", ""))
    base = {k: v for k, v in f.items() if k != "symbols"}
    if (m := re.fullmatch(r"(S|D)_?([A-Za-z]\w*)", group)) and norm_sym(m.group(2)) in params:
        g = {"type": m.group(1), "n": m.group(2), "id": str(f["id"])}
        g["tex"] = f.get("tex") or f"{m.group(1)}_{{{m.group(2)}}}"
    elif group in ("SL(2,R)", "SL(2,\\mathbbR)"):
        g = {"type": "SL2R", "id": str(f["id"]), "tex": f.get("tex") or "SL(2,\\mathbb{R})"}
    elif group in params and re.fullmatch(r"\\?[A-Za-z]+", group):
        g = {"type": "LieParam", "G": group, "id": str(f["id"]), "tex": f.get("tex") or group}
    else:
        g = _parse_factor_2db(base, params)
    if "irreps" in f and g["type"] not in ("finite", "listed"):
        raise RepError("`irreps` is only for `group: finite` or `group: listed`")
    g["symbols"] = _symbols(f)
    return g


def label(g: dict, value, params: set[str]) -> dict:
    return _label_public_2db(g, value, set(params) | g.get("symbols", set()))


def _label(g, t, s, params, G):
    if t in ("SU", "Sp") and g["N"] == 2 and (m := re.fullmatch(r"spin\((.+)\)", s)):
        j = _expr(m.group(1), params)
        if isinstance(j, Fraction):
            if j < 0 or (2 * j).denominator != 1:
                raise RepError(f"'{s}': the spin is a non-negative half-integer")
            return _label_dispatch_2db(g, t, f"Dynkin({int(2 * j)})", params, G)
        return {"canon": f"spin({norm_sym(j)})", "short": f"spin ${j}$", "trivial": False, "sort": [BIG, 0]}
    if t == "S" and not isinstance(g["n"], int):
        n = g["n"]
        if s == "trivial":
            lam = []
        elif s == "standard":
            lam = [1]
        elif (m := re.fullmatch(r"Y\(([\d,\s]*)\)", s)):
            lam = _tuple(m.group(1))
            if any(x < 1 for x in lam) or lam != sorted(lam, reverse=True):
                raise RepError(f"'{s}': the rows below the first are positive and non-increasing")
        else:
            raise RepError(f"an S_{n} label (n a parameter) is trivial, standard or Y(l1,l2,...) for the irrep "
                           f"[{n} - |l|, l1, l2, ...]; not '{s}'")
        rows = ",".join(map(str, lam))
        short = {(): "trivial", (1,): f"standard (${n}-1$-dimensional)"}.get(tuple(lam), f"irrep $[{n}-{sum(lam)},{rows}]$")
        return {"canon": f"Y({rows})", "short": short, "trivial": not lam, "sort": [sum(lam), *(-x for x in lam)]}
    if t == "D" and not isinstance(g["n"], int):
        m = re.fullmatch(r"(A1|A2|B1|B2)|E(\d+)", s)
        if not m or (m.group(2) and int(m.group(2)) < 1):
            raise RepError(f"a D_{g['n']} label is A1, A2, B1, B2 (n even) or E1, E2, ...; not '{s}'")
        order = ["A1", "A2", "B1", "B2"].index(s) if m.group(1) else 3 + int(m.group(2))
        return {"canon": s, "short": f"${s[0]}_{{{s[1:]}}}$", "trivial": s == "A1", "sort": [order]}
    if t == "SL2R":
        if s in ("trivial", "adjoint"):
            return {"canon": s, "short": s, "trivial": s == "trivial", "sort": [0 if s == "trivial" else 1]}
        if (m := re.fullmatch(r"D(\+|-|±|\+-)\((.+)\)", s)):
            sign = "±" if m.group(1) in ("±", "+-") else m.group(1)
            j = _expr(m.group(2), params)
            return {"canon": f"D{sign}({norm_sym(j)})", "short": f"discrete series $\\mathcal{{D}}^{{{sign}}}_{{{j}}}$",
                    "trivial": False, "sort": [2, {"±": 0, "+": 1, "-": 2}[sign]]}
        if (m := re.fullmatch(r"C\((.+),(.+)\)", s)):
            j, a = _expr(m.group(1), params), _expr(m.group(2), params)
            return {"canon": f"C({norm_sym(j)},{norm_sym(a)})", "short": f"continuous series $\\mathcal{{C}}^{{{a}}}_{{{j}}}$",
                    "trivial": False, "sort": [3, 0]}
        raise RepError(f"an SL(2,R) label is trivial, adjoint, D+(j), D-(j), D±(j) or C(j, alpha); not '{s}'")
    if t == "LieParam":
        if s in ("singlet", "adjoint"):
            return {"canon": s, "short": s, "trivial": s == "singlet", "sort": [0 if s == "singlet" else 1, 0]}
        if (m := re.fullmatch(r"hw\((.+)\)(bar)?", s)):
            lam = m.group(1).strip()
            if norm_sym(lam) not in params:
                raise RepError(f"'{s}': the highest weight '{lam}' is not a parameter or symbol of the entry")
            conj = bool(m.group(2))
            short = f"conjugate of highest weight ${lam}$ (${lam}^*$)" if conj else f"highest weight ${lam}$"
            return {"canon": f"hw({norm_sym(lam)}){'bar' if conj else ''}", "short": short, "trivial": False,
                    "sort": [2, int(conj)]}
        raise RepError(f"a label of a generic group {g['G']} is singlet, adjoint, hw(lambda) or hw(lambda)bar; not '{s}'")
    return _label_dispatch_2db(g, t, s, params, G)


# ------------------------------------------------------------------ spacetime

def spin_value(v):
    """Spin as a Fraction (0, 2, '1/2', '3/2'), or None if it is not a number."""
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return Fraction(v)
    m = re.fullmatch(r"\s*(-?\d+)(?:\s*/\s*(\d+))?\s*", str(v))
    return Fraction(int(m.group(1)), int(m.group(2) or 1)) if m else None


def parse_lorentz(d: int, s: str):
    """4d: '(j, jbar)' -> (j, jbar); d >= 5: '[l1, l2, ...]' (SO(d) highest weight) -> tuple. Raises RepError."""
    s = str(s).strip()
    half = lambda x: Fraction(x.strip())
    if d == 4:
        m = re.fullmatch(r"\(\s*([\d/]+)\s*,\s*([\d/]+)\s*\)", s)
        if not m:
            raise RepError(f"a 4d Lorentz label is '(j, jbar)' with j, jbar in {{0, 1/2, 1, ...}}; not '{s}'")
        j, jb = half(m.group(1)), half(m.group(2))
        if (2 * j).denominator != 1 or (2 * jb).denominator != 1:
            raise RepError(f"j and jbar are half-integers in '{s}'")
        return (j, jb)
    if d >= 5:
        m = re.fullmatch(r"\[([\d/,\s-]+)\]", s)
        if not m:
            raise RepError(f"a {d}d Lorentz label is an SO({d}) highest weight '[l1, l2, ...]'; not '{s}'")
        w = [half(x) for x in m.group(1).split(",")]
        if len(w) > d // 2:
            raise RepError(f"SO({d}) has rank {d // 2}; '{s}' has {len(w)} entries")
        if len({(2 * x).denominator for x in w}) != 1 or any((2 * x).denominator != 1 for x in w):
            raise RepError(f"the entries of '{s}' must be all integers or all half-odd-integers")
        return tuple(w)
    raise RepError(f"`lorentz` is not used in {d}d: give `spin`{' and `weights`' if d == 2 else ''}")


def parity_is_label(d: int, o: dict) -> bool | None:
    """Whether parity can have an eigenvalue for this Lorentz representation: False for a chiral 4d irrep (j != jbar)
    and a 2d operator of non-zero spin (parity maps it to its partner), True when it can, None if unknown."""
    if d == 4 and "lorentz" in o:
        j, jb = parse_lorentz(4, o["lorentz"])
        return j == jb
    if d == 2:
        s = spin_value(o.get("spin", 0))
        return None if s is None else s == 0
    return True


# ------------------------------------------------------------------ entry check

STRUCTURED = ("global", "parity", "T")


def check_multiplets(data: dict, rel: str) -> list[str]:
    """`multiplet` (docs/REPRESENTATIONS.md 1.5): supersymmetric theories only; the CDI label in d >= 3, none in 2d."""
    errs = []
    susy = (data.get("symmetry") or {}).get("supercharges")
    for i, o in enumerate(data.get("operators") or []):
        m, where = o.get("multiplet"), f"{rel}: operators/{i}"
        if m is None:
            continue
        if not susy:
            errs.append(f"{where}: `multiplet` is for supersymmetric theories (symmetry.supercharges > 0)")
        elif data.get("d") == 2 and "cdi" in m:
            errs.append(f"{where}/multiplet/cdi: the Cordova–Dumitrescu–Intriligator classification is for d >= 3")
        elif data.get("d") != 2 and not str(m.get("cdi", "")).strip():
            errs.append(f"{where}/multiplet: give `cdi`, the Cordova–Dumitrescu–Intriligator label "
                        f"(`unknown` if it cannot be determined; docs/REPRESENTATIONS.md 1.5)")
    return errs


def check_entry_reps(data: dict, rel: str) -> list[str]:
    """Check the structured representation fields of one entry and attach `irrep` (display data) to each operator."""
    return check_multiplets(data, rel) + _check_symmetry_labels(data, rel)


def _check_symmetry_labels(data: dict, rel: str) -> list[str]:
    errs: list[str] = []
    sym = data.get("symmetry") or {}
    ops = data.get("operators") or []
    params = {norm_sym(p["symbol"]) for p in data.get("parameters", []) or []}
    d = data.get("d")
    migrated = "global_group" in sym
    if not migrated:
        for i, o in enumerate(ops):
            for k in STRUCTURED:
                if k in o:
                    errs.append(f"{rel}: operators/{i}: `{k}` needs the structured symmetry declaration "
                                f"(symmetry.global_group and symmetry.parity; docs/REPRESENTATIONS.md)")
            if "lorentz" in o:
                try:
                    parse_lorentz(d, o["lorentz"])
                except RepError as exc:
                    errs.append(f"{rel}: operators/{i}/lorentz: {exc}")
        if "parity" in sym or "time_reversal" in sym:
            errs.append(f"{rel}: symmetry: `parity` / `time_reversal` come with `global_group` (use [] for no global symmetry)")
        return errs

    factors = []
    for j, f in enumerate(sym["global_group"]):
        try:
            factors.append(parse_factor(f, params))
        except RepError as exc:
            errs.append(f"{rel}: symmetry/global_group/{j}: {exc}")
    ids = [f["id"] for f in factors]
    if len(set(ids)) != len(ids):
        errs.append(f"{rel}: symmetry/global_group: factor ids must be unique")
    if "parity" not in sym:
        errs.append(f"{rel}: symmetry: a structured entry states `parity` (true, false or conditional)")
    has_p = sym.get("parity") in (True, "conditional")
    has_t = sym.get("time_reversal") == "independent"
    if errs:
        return errs
    data["global_factors"] = [{"id": f["id"], "type": f["type"], "tex": f["tex"]} for f in factors]
    for i, o in enumerate(ops):
        where = f"{rel}: operators/{i}"
        if "rep" in o:
            errs.append(f"{where}: a structured entry gives `global` and `parity`, not the free-text `rep`")
        g = o.get("global") or {}
        if factors and "global" not in o:
            errs.append(f"{where}: give `global` with a label for each factor ({', '.join(ids)}), or `unknown`")
        extra = [k for k in g if str(k) not in ids]
        if extra:
            errs.append(f"{where}/global: unknown factor(s) {extra} (declared: {ids or 'none'})")
        missing = [k for k in ids if k not in {str(x) for x in g}] if "global" in o else []
        if missing:
            errs.append(f"{where}/global: no label for {missing} (write `unknown` if it is not known)")
        view = []
        family = "family" in o     # a family row's labels may be expressions in its parameters: scripts/opfam.py
        for f in factors:
            if f["id"] not in g or family:
                continue
            try:
                view.append({"factor": f["id"], **label(f, g[f["id"]], params)})
            except RepError as exc:
                errs.append(f"{where}/global/{f['id']}: {exc}")
        # parity
        try:
            if "lorentz" in o:
                parse_lorentz(d, o["lorentz"])
            plabel = parity_is_label(d, o)
        except RepError as exc:
            errs.append(f"{where}/lorentz: {exc}")
            plabel = None
        if has_p:
            p = o.get("parity")
            if p is None:
                errs.append(f"{where}: the theory has parity, so give `parity` (even, odd, pair or unknown)")
            elif plabel is False and p not in ("pair", "unknown"):
                errs.append(f"{where}/parity: parity maps this Lorentz representation to its partner "
                            f"({'j and jbar exchanged' if d == 4 else 'spin s to -s'}), so it has no eigenvalue: write `pair`")
        elif "parity" in o:
            errs.append(f"{where}: `parity` is given, but symmetry.parity is {sym.get('parity')!r}")
        if "T" in o and not has_t:
            errs.append(f"{where}: `T` (time reversal) is recorded only when symmetry.time_reversal is `independent`")
        if not family:
            o["irrep"] = {"global": view, "key": "|".join(f"{v['factor']}={v['canon']}" for v in view)}
    return errs


def legacy_reps(entries: list[dict]) -> tuple[int, int]:
    """(operators with a free-text rep, entries that have them)."""
    n = [sum("rep" in o for o in e.get("operators", []) or []) for e in entries]
    return sum(n), sum(1 for x in n if x)


def direct_sums(entries: list[dict]) -> int:
    return sum(any(v.get("sum") for v in o.get("irrep", {}).get("global", [])) for e in entries for o in e.get("operators", []) or [])
