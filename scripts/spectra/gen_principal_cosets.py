#!/usr/bin/env python3
"""Spectra of cosets G_k / SU(2)_K by the principal SU(2) (the defining
representation of G is irreducible under it):

    su5-1-su2-20      SU(5)_1 / SU(2)_20, diagonal                c = 14/11
    su5-1-su2-20-z5   its Z_5 simple-current orbifold by J = (1, 0)
    so5-2-su2-20      SO(5)_2 / SU(2)_20, diagonal                c = 14/11
    sp6-1-su2-35      Sp(6)_1 / SU(2)_35, diagonal                c = 252/185

Method: Weyl-Kac characters of G_k specialised along the principal grading
(principal.py), decomposed into SU(2)_K characters (su2.decompose). Field
identification pairs (Lambda; j) with (J Lambda; K/2 - j), J the simple current
of G_k that corresponds to -1 in SU(2) (trivial for SU(5), whose principal
subgroup is SO(3)). The c = 14/11 cosets have identification fixed points at
j = 5; they are resolved with twining characters that are Lee-Yang characters.

Cross-checks run every time (assertions): SU(5)_1 against A_4 lattice theta
functions; SO(5)_2 inside SU(5)_1 (conformal embedding); Sp(6)_1 x SU(2)_3 inside
SO(12)_1 free fermions; Kac-Peterson S on the G characters; S covariance of the
branching functions; identification and conjugation symmetries; integrality,
positivity and Virasoro positivity of the resolved characters; the resolved
(Schellekens-Yankielowicz) S matrix is unitary, has non-negative integer Verlinde
fusion coefficients and transforms the computed resolved characters correctly;
the Z_5 orbifold invariant (Kreuzer-Schellekens) commutes with it.

    python scripts/spectra/gen_principal_cosets.py
"""

from __future__ import annotations

import cmath
import itertools
import math
from fractions import Fraction as F

import numpy as np

import su2
from common import ROOT, Series, block, frac_str, phi, qpoch, write_spectrum
from principal import A, B2, C, kac_peterson_S, principal_character
from rcft import minimal_char

GEN = "scripts/spectra/gen_principal_cosets.py"
N = 11            # grades of the G characters
TOP = F(8)        # blocks are written up to this conformal weight
TAUS = (complex(0.1, 1.1), complex(-0.23, 0.95))


# ------------------------------------------------------------- generic helpers

def series_of(X: su2.Graded) -> Series:
    """Unrefined character (z = 1) as a Series."""
    tot = X.a.sum(axis=1)
    return Series({X.E + n: int(v) for n, v in enumerate(tot) if v}, X.E + X.N)


def num(s: Series, tau: complex) -> complex:
    return sum(a * cmath.exp(2j * math.pi * tau * float(e)) for e, a in s.c.items())


def same(s1: Series, s2: Series) -> bool:
    top = min(s1.top, s2.top)
    return s1.truncate(top).c == s2.truncate(top).c


def su2_S(K: int) -> np.ndarray:
    return np.array([[math.sqrt(2 / (K + 2)) * math.sin(math.pi * (l + 1) * (m + 1) / (K + 2))
                      for m in range(K + 1)] for l in range(K + 1)])


def check_S_G(L, k, chars):
    """chi_lam(-1/tau) = sum S chi_mu(tau) for the unrefined characters."""
    wts = L.integrable(k)
    S = kac_peterson_S(L, k, wts)
    ser = [series_of(chars[w]) for w in wts]
    for tau in TAUS:
        v, vS = np.array([num(s, tau) for s in ser]), np.array([num(s, -1 / tau) for s in ser])
        err = np.abs(vS - S @ v).max() / np.abs(vS).max()
        assert err < 1e-9, f"{L.name} level {k}: S check failed ({err:.1e})"
    return S, wts


def branching(L, k, chars, K):
    """{(lam, l): b} for every lam and every SU(2)_K label l that occurs."""
    out = {}
    for lam, X in chars.items():
        for l, b in su2.decompose(X, K).items():
            out[(lam, l)] = b
    return out


def check_branching_S(b, S, wts, K, rep):
    """b_{lam,l}(-1/tau) = sum S^G_{lam,mu} S^{SU(2)}_{l,m} b_{mu,m}(tau) (every b replaced by
    the longest series in its identification class)."""
    Ssu2 = su2_S(K)
    keys = [(lam, l) for lam in wts for l in range(K + 1)]
    full = {key: b[rep[key]] if key in rep else None for key in keys}
    for tau in TAUS:
        val = {key: (num(s, tau) if s is not None else 0) for key, s in full.items()}
        diffs, scale = [], 0.0
        for (lam, l) in keys:
            if full[(lam, l)] is None:
                continue
            lhs = num(full[(lam, l)], -1 / tau)
            rhs = sum(S[wts.index(lam), j] * Ssu2[l, m] * val[(mu, m)]
                      for j, mu in enumerate(wts) for m in range(K + 1) if full[(mu, m)] is not None)
            diffs.append(abs(lhs - rhs))
            scale = max(scale, abs(lhs))
        worst = max(diffs) / scale       # relative to the largest component of the vector
        assert worst < 1e-10, f"branching functions are not S covariant ({worst:.1e})"
        print(f"    S covariance of the branching functions at tau = {tau}: {worst:.1e}")
    return worst


def lee_yang(top):
    """Lee-Yang characters (absolute exponents) from Rogers-Ramanujan products, checked
    against the Rocha-Caridi formula: q^{11/60} H(q) (h = 0) and q^{-1/60} G(q) (h = -1/5)."""
    G = qpoch(1, 5, top + 1, inverse=True) * qpoch(4, 5, top + 1, inverse=True)
    H = qpoch(2, 5, top + 1, inverse=True) * qpoch(3, 5, top + 1, inverse=True)
    vac, phi_ = H.shift(F(11, 60)), G.shift(F(-1, 60))
    c_ly = F(-22, 5)
    rc_vac = minimal_char(2, 5, 1, 1, top + 1 + c_ly / 24)
    rc_phi = minimal_char(2, 5, 1, 2, top + 1 + c_ly / 24)
    assert same(vac, rc_vac) and same(phi_, rc_phi), "Rogers-Ramanujan != Rocha-Caridi"
    return vac.truncate(top), phi_.truncate(top)


def virasoro_positive(ch: Series, c) -> bool:
    """A non-vacuum module of c > 1 Virasoro: ch * prod(1-q^n) must have non-negative coefficients."""
    top = ch.top
    x = ch * phi(top + c / 24 + 1)
    return all(a >= 0 for e, a in x.c.items() if e <= top)


def resolve(b: Series, d: Series, c):
    """(b + d)/2, (b - d)/2 for a fixed point with twining character d."""
    top = min(b.top, d.top)
    plus, minus = (b + d).truncate(top), (b - d).truncate(top)
    out = []
    for s in (plus, minus):
        assert all(a % 2 == 0 for a in s.c.values()), "fixed-point resolution: odd coefficient"
        h = Series({e: a // 2 for e, a in s.c.items()}, top)
        assert all(a >= 0 for a in h.c.values()), "fixed-point resolution: negative coefficient"
        assert virasoro_positive(h, c), "resolved character is not Virasoro-positive"
        out.append(h)
    return out


def resolved_S(fields, SG, SJ, K):
    """Schellekens-Yankielowicz S matrix of a coset with a Z_2 identification current, in the
    basis `fields` = [((lam, l), sign or None, label, series)]:
        S_{x,y} = 2 S^G S^{SU(2)}      both off the fixed points,
                = S^G S^{SU(2)}        one of them a resolved fixed point,
                = (S^G S^{SU(2)} + s t S^J) / 2   both resolved, components s, t = +-1.
    SG(lam, mu), SJ(lam, mu) give the numerator and fixed-point matrices. Checks unitarity,
    symmetry, Verlinde fusion coefficients in Z_{>=0}, and chi(-1/tau) = S chi(tau)."""
    S2 = su2_S(K)
    n = len(fields)
    M = np.zeros((n, n), dtype=complex)
    for i, ((la, l), x, _, _) in enumerate(fields):
        for j, ((lb, m), y, _, _) in enumerate(fields):
            base = SG(la, lb) * S2[l, m]
            if x is None and y is None:
                M[i, j] = 2 * base
            elif x is None or y is None:
                M[i, j] = base
            else:
                st = (1 if x == "+" else -1) * (1 if y == "+" else -1)
                M[i, j] = (base + st * SJ(la, lb)) / 2
    assert np.abs(M @ M.conj().T - np.eye(n)).max() < 1e-12, "resolved S is not unitary"
    assert np.abs(M - M.T).max() < 1e-12, "resolved S is not symmetric"
    Nf = np.einsum("xw,yw,zw->xyz", M, M, M.conj() / M[0])
    assert np.abs(Nf - np.round(Nf.real)).max() < 1e-9 and Nf.real.min() > -1e-9, "Verlinde fails"
    for tau in TAUS:
        v = np.array([num(s, tau) for *_, s in fields])
        vS = np.array([num(s, -1 / tau) for *_, s in fields])
        err = np.abs(vS - M @ v).max() / np.abs(vS).max()
        assert err < 1e-12, f"resolved characters are not S covariant ({err:.1e})"
        print(f"    resolved characters: chi(-1/tau) = S chi(tau) at tau = {tau}: {err:.1e}")
    return M


def lowest(spec_blocks, Z, c):
    """{(h, hbar): multiplicity} of the primaries (ground states of the blocks) in Z."""
    out = {}
    for i, j, m in Z:
        key = (F(spec_blocks[i]["h"]), F(spec_blocks[j]["h"]))
        out[key] = out.get(key, 0) + int(m)
    return dict(sorted(out.items(), key=lambda kv: (kv[0][0] + kv[0][1], kv[0][0])))


def write(theory, c, blocks, Z, **meta):
    spec = {"theory": theory, "c": str(c), **meta, "generator": GEN, "blocks": blocks,
            "Z": [[i, j, frac_str(m)] for i, j, m in Z]}
    p = write_spectrum(spec)
    low = [(f"{h}", f"{hb}", m) for (h, hb), m in list(lowest(blocks, Z, c).items())[:5]]
    print(f"wrote {p.relative_to(ROOT)}: {len(blocks)} blocks; lowest primaries {low}")


def j_tex(l: int) -> str:
    return str(l // 2) if l % 2 == 0 else f"{l}/2"


# ------------------------------------------------------------- G characters with cross-checks

def su5_chars():
    L = A(4)
    dyn = {0: (0, 0, 0, 0), 1: (1, 0, 0, 0), 2: (0, 1, 0, 0), 3: (0, 0, 1, 0), 4: (0, 0, 0, 1)}
    chars = {dyn[a]: principal_character(L, 1, dyn[a], N) for a in range(5)}
    # A_4 lattice: chi_a = sum_{y in Z^5, sum y = a} q^{|y - a/5|^2/2} z^{<y, 2 rho>} / eta^4
    W, rho = su2.W, (2, 1, 0, -1, -2)
    inv4 = [1] + [0] * N
    from zoo_spectrum import partitions
    p = partitions(N)
    for _ in range(4):
        inv4 = [sum(inv4[i] * p[n - i] for i in range(n + 1)) for n in range(N + 1)]
    for a in range(5):
        ha = F(a * (5 - a), 10)
        th = np.zeros((N + 1, 2 * W + 1), dtype=object)
        th[:] = 0
        for y in itertools.product(range(-6, 7), repeat=4):
            yy = list(y) + [a - sum(y)]
            e = sum((F(v) - F(a, 5)) ** 2 for v in yy) / 2 - ha
            if e <= N:
                th[int(e), W + 2 * sum(r * v for r, v in zip(rho, yy))] += 1
        full = np.zeros_like(th)
        full[:] = 0
        for n in range(N + 1):
            for m in range(N + 1 - n):
                full[n + m] += inv4[m] * th[n]
        assert (full == chars[dyn[a]].a).all(), "SU(5)_1: Weyl-Kac != lattice theta"
    S, wts = check_S_G(L, 1, chars)
    return L, dyn, chars, S, wts


def so5_chars(su5):
    L = B2()
    chars = {lam: principal_character(L, 2, lam, N) for lam in L.integrable(2)}
    # conformal embedding SO(5)_2 in SU(5)_1: 1 = (0,0)+(2,0), 5 = (1,0), 10 = (0,2)
    v, s14 = chars[(0, 0)], chars[(2, 0)]
    assert s14.E - v.E == 1
    vac = v.a.copy()
    vac[1:] += s14.a[:-1]
    assert (vac == su5[(0, 0, 0, 0)].a).all()
    assert (chars[(1, 0)].a == su5[(1, 0, 0, 0)].a).all() and chars[(1, 0)].E == su5[(1, 0, 0, 0)].E
    assert (chars[(0, 2)].a == su5[(0, 1, 0, 0)].a).all() and chars[(0, 2)].E == su5[(0, 1, 0, 0)].E
    S, wts = check_S_G(L, 2, chars)
    return L, chars, S, wts


def sp6_chars():
    L = C(3)
    lab = {0: (0, 0, 0), 1: (1, 0, 0), 2: (0, 1, 0), 3: (0, 0, 1)}
    chars = {lab[i]: principal_character(L, 1, lab[i], N) for i in range(4)}
    # Sp(6)_1 x SU(2)_3 in SO(12)_1:  NS = sum_i chi^{Sp(6)}_{Lambda_i}(q, z) chi^{SU(2)_3}_i(q)
    W = su2.W
    lhs = {}
    top = min(chars[lab[i]].E + su2.su2_char(3, i, N).E for i in range(4)) + N
    for i in range(4):
        X, Y = chars[lab[i]], su2.su2_char(3, i, N)
        yu = Y.a.sum(axis=1)
        for n1 in range(N + 1):
            for w in np.nonzero(X.a[n1])[0]:
                for n2 in range(N + 1 - n1):
                    key = (X.E + Y.E + n1 + n2, int(w) - W)
                    lhs[key] = lhs.get(key, 0) + int(X.a[n1, w]) * int(yu[n2])
    rhs = {(F(-1, 4), 0): 1}
    n = 1
    while F(2 * n - 1, 2) - F(1, 4) <= top:
        e = F(2 * n - 1, 2)
        for w in (-5, -3, -1, 1, 3, 5):
            for _ in range(2):
                new = dict(rhs)
                for (ee, ww), cc in rhs.items():
                    if ee + e <= top:
                        new[(ee + e, ww + w)] = new.get((ee + e, ww + w), 0) + cc
                rhs = new
        n += 1
    keys = {k for k in set(lhs) | set(rhs) if k[0] <= top}
    assert all(lhs.get(k, 0) == rhs.get(k, 0) for k in keys), "Sp(6)_1 x SU(2)_3 != SO(12)_1"
    S, wts = check_S_G(L, 1, chars)
    return L, lab, chars, S, wts


# ------------------------------------------------------------- the cosets

def coset_tables(L, k, chars, S, wts, J, K, parity):
    """Branching functions, identification classes and checks.
    J: simple current on weights (dict); parity(lam) = allowed l mod 2."""
    b = branching(L, k, chars, K)
    for (lam, l) in b:
        assert l % 2 == parity(lam), f"selection rule violated by {(lam, l)}"
    allowed = [(lam, l) for lam in wts for l in range(K + 1) if l % 2 == parity(lam)]
    rep, classes = {}, []
    c = L.central_charge(k) - F(3 * K, K + 2)
    for (lam, l) in allowed:
        twin = (J[lam], K - l)
        present = [t for t in ((lam, l), twin) if t in b]
        # a class may be reached only through one member (the other starts above grade N)
        assert present, f"branching functions not reached: {(lam, l)}"
        if len(present) == 2:
            assert same(b[(lam, l)], b[twin]), f"field identification fails for {(lam, l)}"
        if twin in rep:
            rep[(lam, l)] = rep[twin]
        else:
            # representative: smallest l (then numerator order) among members known beyond TOP
            ok = sorted((t for t in present if b[t].top >= TOP - c / 24), key=lambda t: (t[1], wts.index(t[0])))
            assert ok, f"N too small for {(lam, l)}"
            r = ok[0]
            rep[(lam, l)] = r
            classes.append(r)
    check_branching_S(b, S, wts, K, rep)
    return b, rep, sorted(set(classes), key=lambda t: (wts.index(t[0]), t[1]))


def c14_11(L, chars, S, wts, names, J, k, *, fixed_d):
    """Fields [((lam, l), sign or None, label, series)] of a c = 14/11 coset (K = 20); the fixed
    points of identification are resolved with twining character fixed_d(lam) (None: b/2 twice)."""
    K = 20
    c = L.central_charge(k) - F(3 * K, K + 2)
    assert c == F(14, 11)
    b, rep, classes = coset_tables(L, k, chars, S, wts, J, K, lambda lam: L.grading(lam) % 2)
    fields = []          # (key, sign or None, label, series)
    for (lam, l) in classes:
        name = names[lam]
        if (J[lam], K - l) == (lam, l):
            d = fixed_d(lam)
            if d is None:
                assert all(a % 2 == 0 for a in b[(lam, l)].c.values())
                half = Series({e: a // 2 for e, a in b[(lam, l)].c.items()}, b[(lam, l)].top)
                hp = hm = half
            else:
                hp, hm = resolve(b[(lam, l)], d, c)
            for sg, s in (("+", hp), ("-", hm)):
                fields.append(((lam, l), sg, f"\\chi^{{{sg}}}_{{({name};\\,{j_tex(l)})}}", s))
        else:
            fields.append(((lam, l), None, f"\\chi_{{({name};\\,{j_tex(l)})}}", b[(lam, l)]))
    return c, b, fields


def build_su5():
    L, dyn, chars, S, wts = su5_chars()
    a_of = {d: a for a, d in dyn.items()}
    names = {dyn[0]: "\\mathbf{1}", dyn[1]: "\\mathbf{5}", dyn[2]: "\\mathbf{10}",
             dyn[3]: "\\overline{\\mathbf{10}}", dyn[4]: "\\overline{\\mathbf{5}}"}
    vac, ly_phi = lee_yang(TOP)
    J = {d: d for d in wts}          # principal SU(2) is SO(3) in SU(5): trivial numerator current
    fixed_d = lambda lam: {0: None, 1: ly_phi, 4: ly_phi, 2: vac, 3: vac}[a_of[lam]]
    c, b, fields = c14_11(L, chars, S, wts, names, J, 1, fixed_d=fixed_d)
    for (lam, l) in b:               # conjugation a -> -a
        assert same(b[(lam, l)], b[(dyn[(-a_of[lam]) % 5], l)])
    # Resolved S matrix. S^{SU(5)_1}_{ab} = e^{-2 pi i ab/5}/sqrt5; on the fixed points the twining
    # characters d_a = sigma_a delta_a (sigma = +,+,+,-,- for a = 0..4) transform with
    # S^J = i S^{SU(5)_1} (= the Lee-Yang S matrix on d_1, d_2); this is the convention in which
    # the simple current J = (1, 0) preserves the fixed-point label.
    S5 = lambda la, lb: cmath.exp(-2j * math.pi * a_of[la] * a_of[lb] / 5) / math.sqrt(5)
    sigma = {0: 1, 1: 1, 2: 1, 3: -1, 4: -1}
    SJ = lambda la, lb: 1j * S5(la, lb) * sigma[a_of[la]] * sigma[a_of[lb]]
    M = resolved_S(fields, S5, SJ, 20)
    blocks = [block(s, c, lab, TOP) for _, _, lab, s in fields]
    hs = [F(bl["h"]) for bl in blocks]
    idx = {(key, sg): n for n, (key, sg, _, _) in enumerate(fields)}
    diag = [[n, n, 1] for n in range(len(fields))]
    # Z_5 orbifold by J = (1, 0) (h_J = 12/5): Kreuzer-Schellekens invariant
    #   M_{x, J^n x} = 1  iff  Q_J(x) + n r / (2N) in Z,  N = 5, r = 6 (r even for odd N),
    # with J acting on resolved fields by a -> a+1 at fixed sigma-twisted label.
    def Jx(n):
        (lam, l), sg, _, _ = fields[n]
        a = a_of[lam]
        b_ = (a + 1) % 5
        if sg is None:
            return idx[((dyn[b_], l), None)]
        sJ = (1 if sg == "+" else -1) * sigma[a]
        return idx[((dyn[b_], l), "+" if sJ * sigma[b_] == 1 else "-")]
    hJ = hs[idx[((dyn[1], 0), None)]]
    assert hJ == F(12, 5)
    Ppow = [list(range(len(fields)))]
    for _ in range(4):
        Ppow.append([Jx(x) for x in Ppow[-1]])
    assert [Jx(x) for x in Ppow[4]] == Ppow[0]
    orb = []
    for x in range(len(fields)):
        Q = (hJ + hs[x] - hs[Jx(x)]) % 1
        assert Q == F(a_of[fields[x][0][0]], 5)
        for n_ in range(5):
            if (Q + F(6 * n_, 10)).denominator == 1:
                orb.append([x, Ppow[n_][x], 1])
    assert len(orb) == len(fields)
    P = np.zeros((len(fields), len(fields)))
    for x, y, _ in orb:
        P[x, y] = 1
        assert (hs[x] - hs[y]).denominator == 1
        (lam, l), sg, _, _ = fields[x]
        (lam2, l2), sg2, _, _ = fields[y]
        a = a_of[lam]
        assert a_of[lam2] == (-a) % 5 and l2 == l           # (a; j) -> (-a; j)
        if sg is not None and a != 0:
            assert sg2 != sg                                 # light pairs with heavy
    assert np.abs(P @ M - M @ P).max() < 1e-12, "orbifold invariant does not commute with S"
    char_tex = ("$b_{(a;\\,j)}$ are the branching functions of $SU(5)_1$ into the principal $SU(2)_{20}$: "
                "$\\chi^{SU(5)_1}_{a}(q, z^{2\\rho^\\vee}) = \\sum_{j} b_{(a;\\,j)}(q)\\, \\chi^{SU(2)_{20}}_{j}(q, z)$, "
                "$a\\in\\mathbb{Z}_5$ labelling $\\mathbf{1},\\mathbf{5},\\mathbf{10},\\overline{\\mathbf{10}},"
                "\\overline{\\mathbf{5}}$ and $j\\in\\{0,1,\\dots,10\\}$, with $b_{(a;\\,j)} = b_{(a;\\,10-j)}$. "
                "Blocks: $\\chi_{(a;\\,j)} = b_{(a;\\,j)}$ for $j\\le4$, and for the fixed points "
                "$\\chi^{\\pm}_{(a;\\,5)} = \\tfrac12\\big(b_{(a;\\,5)} \\pm \\delta_a\\big)$ with Lee–Yang "
                "characters $\\delta_{\\pm1} = q^{-1/60}G(q)$, $\\delta_{\\pm2} = q^{11/60}H(q)$ and $\\delta_0 = 0$, "
                "where $G = \\prod_{n\\ge0}[(1-q^{5n+1})(1-q^{5n+4})]^{-1}$ and "
                "$H = \\prod_{n\\ge0}[(1-q^{5n+2})(1-q^{5n+3})]^{-1}$ (Rogers–Ramanujan).")
    desc_common = ("Weyl–Kac characters of $SU(5)_1$ specialised along the principal grading "
                   "$e^{\\beta}\\to z^{\\langle\\beta,2\\rho^\\vee\\rangle}$ (checked against the $A_4$ lattice theta "
                   "functions) are decomposed exactly into $SU(2)_{20}$ characters. The principal subgroup is "
                   "$SO(3)$, so only integer $j$ occur and field identification is $(a;j)\\sim(a;10-j)$. Its fixed "
                   "points $(a;5)$ are resolved (Schellekens–Yankielowicz 1990): the twining characters transform "
                   "with $i$ times the $SU(5)_1$ $S$-matrix, are odd under $a\\to-a$, and are therefore Lee–Yang "
                   "characters; the resulting 35 characters are non-negative integer series and transform "
                   "correctly under the resolved $S$-matrix, which has non-negative integer fusion rules.")
    write("su5-1-su2-20", c, blocks, diag,
          chiral_algebra="SU(5)_1/SU(2)_{20}", irreducible=True,
          Z_tex=("Z = \\sum_{a\\in\\mathbb{Z}_5}\\Big(\\sum_{j=0}^{4}|\\chi_{(a;\\,j)}|^2 + "
                 "|\\chi^{+}_{(a;\\,5)}|^2 + |\\chi^{-}_{(a;\\,5)}|^2\\Big)"),
          character_tex=char_tex,
          description=desc_common + " Diagonal invariant.")
    write("su5-1-su2-20-z5", c, blocks, orb,
          chiral_algebra="SU(5)_1/SU(2)_{20}", irreducible=True,
          Z_tex=("Z = \\sum_{a\\in\\mathbb{Z}_5}\\sum_{j=0}^{4}\\chi_{(a;\\,j)}\\overline{\\chi_{(-a;\\,j)}} + "
                 "\\sum_{\\pm}|\\chi^{\\pm}_{(\\mathbf{1};\\,5)}|^2 + \\sum_{a\\neq0}\\Big(\\chi^{+}_{(a;\\,5)}"
                 "\\overline{\\chi^{-}_{(-a;\\,5)}} + \\chi^{-}_{(a;\\,5)}\\overline{\\chi^{+}_{(-a;\\,5)}}\\Big)"),
          character_tex=char_tex,
          description=(desc_common + " The $\\mathbb{Z}_5$ orbifold by the numerator simple current "
                       "$J=(\\mathbf{5};0)$ ($h_J = 12/5$, monodromy charge $a/5$) gives the Kreuzer–Schellekens "
                       "(1993) invariant $(a;j)\\to(-a;j)$, which on the fixed points pairs the light component of "
                       "$(a;5)$ with the heavy one of $(-a;5)$."))
    return chars


def build_so5(su5_characters):
    L, chars, S, wts = so5_chars(su5_characters)
    names = {(0, 0): "\\mathbf{1}", (2, 0): "\\mathbf{14}", (1, 0): "\\mathbf{5}", (0, 2): "\\mathbf{10}",
             (0, 1): "\\mathbf{4}", (1, 1): "\\mathbf{16}"}
    J = {(l1, l2): (2 - l1 - l2, l2) for (l1, l2) in wts}
    vac, ly_phi = lee_yang(TOP)
    fixed_d = lambda lam: {(1, 0): ly_phi, (0, 2): vac}[lam]
    c, b, fields = c14_11(L, chars, S, wts, names, J, 2, fixed_d=fixed_d)
    # resolved S matrix: Kac-Peterson S of SO(5)_2, and on the fixed points (5; 5), (10; 5) the
    # Lee-Yang S matrix acting on (delta_5, delta_10) = (chi^LY_{-1/5}, chi^LY_0)
    pos = {w: i for i, w in enumerate(wts)}
    s1, s2 = math.sin(2 * math.pi / 5), math.sin(4 * math.pi / 5)
    LY = {((1, 0), (1, 0)): s1, ((1, 0), (0, 2)): s2, ((0, 2), (1, 0)): s2, ((0, 2), (0, 2)): -s1}
    resolved_S(fields, lambda la, lb: S[pos[la], pos[lb]],
               lambda la, lb: 2 / math.sqrt(5) * LY[(la, lb)], 20)
    blocks = [block(s, c, lab, TOP) for _, _, lab, s in fields]
    diag = [[n, n, 1] for n in range(len(fields))]
    write("so5-2-su2-20", c, blocks, diag,
          chiral_algebra="SO(5)_2/SU(2)_{20}", irreducible=True,
          Z_tex=("Z = \\sum_{j=0}^{4}\\big(|\\chi_{(\\mathbf{1};\\,j)}|^2 + |\\chi_{(\\mathbf{14};\\,j)}|^2 + "
                 "|\\chi_{(\\mathbf{5};\\,j)}|^2 + |\\chi_{(\\mathbf{10};\\,j)}|^2\\big) + "
                 "|\\chi_{(\\mathbf{1};\\,5)}|^2 + \\sum_{j=1/2}^{9/2}\\big(|\\chi_{(\\mathbf{4};\\,j)}|^2 + "
                 "|\\chi_{(\\mathbf{16};\\,j)}|^2\\big) + \\sum_{\\lambda=\\mathbf{5},\\mathbf{10}}\\sum_{\\pm}"
                 "|\\chi^{\\pm}_{(\\lambda;\\,5)}|^2"),
          character_tex=("$b_{(\\lambda;\\,j)}$ are the branching functions of $SO(5)_2$ into the principal "
                         "$SU(2)_{20}$, $\\chi^{SO(5)_2}_{\\lambda}(q, z^{2\\rho^\\vee}) = \\sum_j b_{(\\lambda;\\,j)}(q)"
                         "\\,\\chi^{SU(2)_{20}}_j(q,z)$, for $\\lambda\\in\\{\\mathbf{1},\\mathbf{5},\\mathbf{10},"
                         "\\mathbf{14}\\}$ with integer $j$ and $\\lambda\\in\\{\\mathbf{4},\\mathbf{16}\\}$ with "
                         "half-integer $j$; $(\\lambda;\\,j)\\sim(J\\lambda;\\,10-j)$ with $J$ exchanging "
                         "$\\mathbf{1}\\leftrightarrow\\mathbf{14}$, $\\mathbf{4}\\leftrightarrow\\mathbf{16}$. Blocks: "
                         "$\\chi_{(\\lambda;\\,j)} = b_{(\\lambda;\\,j)}$, and $\\chi^{\\pm}_{(\\lambda;\\,5)} = "
                         "\\tfrac12(b_{(\\lambda;\\,5)}\\pm\\delta_\\lambda)$ at the fixed points with Lee–Yang "
                         "characters $\\delta_{\\mathbf{5}} = q^{-1/60}G(q)$, $\\delta_{\\mathbf{10}} = q^{11/60}H(q)$ "
                         "(Rogers–Ramanujan functions $G$, $H$)."),
          description=("Weyl–Kac characters of $SO(5)_2$ in the principal grading are decomposed exactly into "
                       "$SU(2)_{20}$ characters; $-1$ in the principal $SU(2)$ is the non-trivial centre element "
                       "of $Spin(5)$, so spinors carry half-integer $j$ and field identification combines the "
                       "$SO(5)_2$ simple current with $j\\to10-j$. Through the conformal embedding "
                       "$SO(5)_2\\subset SU(5)_1$ (verified on the characters) the fixed points $(\\mathbf{5};5)$ "
                       "and $(\\mathbf{10};5)$ have the branching functions of $SU(5)_1/SU(2)_{20}$, and they are "
                       "resolved with the same Lee–Yang twining characters, checked against the resolved "
                       "(Schellekens–Yankielowicz 1990) $S$-matrix and its fusion rules. Diagonal invariant."))


def build_sp6():
    L, lab, chars, S, wts = sp6_chars()
    K = 35
    assert L.index == K
    c = L.central_charge(1) - F(3 * K, K + 2)
    assert c == F(252, 185)
    names = {lab[0]: "\\mathbf{1}", lab[1]: "\\mathbf{6}", lab[2]: "\\mathbf{14}", lab[3]: "\\mathbf{14}'"}
    J = {lab[i]: lab[3 - i] for i in range(4)}
    b, rep, classes = coset_tables(L, 1, chars, S, wts, J, K, lambda lam: L.grading(lam) % 2)
    assert len(classes) == 36
    blocks = [block(b[t], c, f"\\chi_{{({names[t[0]]};\\,{j_tex(t[1])})}}", TOP) for t in classes]
    diag = [[n, n, 1] for n in range(len(classes))]
    write("sp6-1-su2-35", c, blocks, diag,
          chiral_algebra="Sp(6)_1/SU(2)_{35}", irreducible=True,
          Z_tex=("Z = \\sum_{\\Lambda=\\mathbf{1},\\mathbf{14}}\\ \\sum_{j=0}^{8}|\\chi_{(\\Lambda;\\,j)}|^2 + "
                 "\\sum_{\\Lambda=\\mathbf{6},\\mathbf{14}'}\\ \\sum_{j=1/2}^{17/2}|\\chi_{(\\Lambda;\\,j)}|^2"),
          character_tex=("$\\chi_{(\\Lambda;\\,j)}$ are the branching functions of $Sp(6)_1$ into the principal "
                         "$SU(2)_{35}$: $\\chi^{Sp(6)_1}_{\\Lambda}(q, z^{2\\rho^\\vee}) = \\sum_j "
                         "\\chi_{(\\Lambda;\\,j)}(q)\\,\\chi^{SU(2)_{35}}_j(q,z)$, with $j$ integer for "
                         "$\\Lambda = \\mathbf{1},\\mathbf{14}$ and half-integer for $\\mathbf{6},\\mathbf{14}'$, and "
                         "$(\\Lambda;\\,j)\\sim(J\\Lambda;\\,35/2-j)$, $J:\\mathbf{1}\\leftrightarrow\\mathbf{14}',\\ "
                         "\\mathbf{6}\\leftrightarrow\\mathbf{14}$ (no fixed points)."),
          description=("Weyl–Kac characters of $Sp(6)_1$ in the principal grading (checked through the conformal "
                       "embedding $Sp(6)_1\\times SU(2)_3\\subset SO(12)_1$ against free fermions) are decomposed "
                       "exactly into $SU(2)_{35}$ characters; field identification pairs the $Sp(6)_1$ simple "
                       "current with $j\\to35/2-j$ and has no fixed points. Diagonal invariant of the 36 modules."))


def main():
    su5 = build_su5()
    build_so5(su5)
    build_sp6()


if __name__ == "__main__":
    main()
