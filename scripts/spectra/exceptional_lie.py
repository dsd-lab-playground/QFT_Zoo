"""Lie-algebra machinery for the exceptional coset spectra.

* `Lie`: a simple Lie algebra from its Cartan matrix (Dynkin labels, roots,
  inner products with long roots of length^2 2, Weyl dimensions, integrable
  weights, conformal weights).
* `fkw_characters`: Frenkel-Kac-Wakimoto characters of the W(g) minimal model
  at (p, p') for simply-laced g, summed over the affine Weyl orbit by
  enumerating weight-lattice points in a ball and folding them into the
  fundamental alcove (no sum over the finite Weyl group, so E_8 is cheap).
* `AffineStrings`: Weyl-Kac characters of an untwisted affine algebra, stored
  as "strings" {grade n: {finite highest weight: multiplicity}}, and the
  decomposition of a product of two of them into a third level, i.e. coset
  branching functions. Written for any rank but meant for small rank (G_2).

All results are exact integers; floating point is only used to bound the
lattice-point search, and every point is then re-checked exactly.
"""

from __future__ import annotations

import math
from collections import Counter
from fractions import Fraction as F

import numpy as np


# ------------------------------------------------------------- root systems

def _chain_cartan(n, edges):
    C = [[0] * n for _ in range(n)]
    for i in range(n):
        C[i][i] = 2
    for a, b in edges:
        C[a - 1][b - 1] = C[b - 1][a - 1] = -1
    return C


def _inverse(C):
    """Exact inverse of an integer matrix (list of lists of Fractions)."""
    n = len(C)
    M = [[F(C[i][j]) for j in range(n)] + [F(int(i == j)) for j in range(n)] for i in range(n)]
    for col in range(n):
        piv = next(r for r in range(col, n) if M[r][col] != 0)
        M[col], M[piv] = M[piv], M[col]
        pv = M[col][col]
        M[col] = [x / pv for x in M[col]]
        for r in range(n):
            if r != col and M[r][col] != 0:
                f = M[r][col]
                M[r] = [x - f * y for x, y in zip(M[r], M[col])]
    return [row[n:] for row in M]


class Lie:
    """Simple Lie algebra. Cartan matrix C[i][j] = (alpha_i^vee, alpha_j); d[i] = |alpha_i|^2 / 2
    (long roots have length^2 2). Weights are integer tuples of Dynkin labels."""

    def __init__(self, name, C, d=None):
        self.name = name
        self.r = r = len(C)
        self.C = [list(map(int, row)) for row in C]
        self.d = [F(x) for x in (d or [1] * r)]
        Cinv = _inverse(self.C)
        self.Cinv = Cinv
        # (omega_i, omega_j) = (D C^{-1})_{ij}
        self.Fm = [[self.d[i] * Cinv[i][j] for j in range(r)] for i in range(r)]
        self.den = math.lcm(*[x.denominator for row in self.Fm for x in row])
        self.Fint = np.array([[int(x * self.den) for x in row] for row in self.Fm], dtype=np.int64)
        self.Ffloat = np.array([[float(x) for x in row] for row in self.Fm])
        # simple roots in Dynkin labels: alpha_j = column j of C
        self.simple = [tuple(self.C[i][j] for i in range(r)) for j in range(r)]
        # coroots alpha_j^vee = alpha_j / d_j
        self.cosimple = []
        for j in range(r):
            v = [F(self.C[i][j]) / self.d[j] for i in range(r)]
            assert all(x.denominator == 1 for x in v)
            self.cosimple.append(tuple(int(x) for x in v))
        self._roots()
        self.rho = (1,) * r
        self.comarks = tuple(int(x) for x in self.ip_vec(self.theta))   # (omega_i, theta^vee), |theta|^2 = 2
        assert self.ip(self.theta, self.theta) == 2
        self.hv = sum(self.comarks) + 1

    # -- inner products
    def ip(self, a, b) -> F:
        return sum((self.Fm[i][j] * a[i] * b[j] for i in range(self.r) for j in range(self.r)), F(0))

    def ip_vec(self, a):
        return [sum((self.Fm[i][j] * a[j] for j in range(self.r)), F(0)) for i in range(self.r)]

    def root_coords(self, a):
        return tuple(sum((self.Cinv[i][j] * a[j] for j in range(self.r)), F(0)) for i in range(self.r))

    def reflect(self, a, i):
        ai = a[i]
        return tuple(a[k] - ai * self.simple[i][k] for k in range(self.r))

    def _roots(self):
        seen = set(self.simple)
        todo = list(self.simple)
        while todo:
            a = todo.pop()
            for i in range(self.r):
                b = self.reflect(a, i)
                if b not in seen:
                    seen.add(b)
                    todo.append(b)
        self.roots = sorted(seen)
        self.positive = [a for a in self.roots if all(x >= 0 for x in self.root_coords(a))]
        assert 2 * len(self.positive) == len(self.roots)
        self.theta = max(self.positive, key=lambda a: (sum(self.root_coords(a)), self.ip(a, a)))

    # -- representations
    def dim(self, lam) -> int:
        num, den = F(1), F(1)
        lr = tuple(x + 1 for x in lam)
        for a in self.positive:
            num *= self.ip(lr, a)
            den *= self.ip(self.rho, a)
        v = num / den
        assert v.denominator == 1
        return int(v)

    def casimir(self, lam) -> F:
        return self.ip(lam, tuple(x + 2 for x in lam))

    def h(self, k, lam) -> F:
        return self.casimir(lam) / (2 * (k + self.hv))

    def c_wzw(self, k) -> F:
        return F(k * (self.r + len(self.roots)), k + self.hv)

    def level_of(self, lam) -> int:
        return sum(m * a for m, a in zip(self.comarks, lam))

    def integrable(self, k):
        """Dominant weights of level <= k, in a fixed (sorted) order."""
        out = []

        def rec(i, cur, left):
            if i == self.r:
                out.append(tuple(cur))
                return
            m = self.comarks[i]
            for a in range(left // m + 1):
                rec(i + 1, cur + [a], left - a * m)

        rec(0, [], k)
        return sorted(out, key=lambda w: (self.level_of(w), w))

    def dominant_sign(self, x):
        """Reflect x into the dominant chamber with the finite Weyl group: (sign, x')
        with sign 0 if x lies on a wall."""
        x = tuple(x)
        s = 1
        while True:
            neg = [i for i in range(self.r) if x[i] < 0]
            if not neg:
                break
            x = self.reflect(x, neg[0])
            s = -s
        if any(v == 0 for v in x):
            return 0, x
        return s, x

    def weyl_group(self):
        """All Weyl group elements as (integer matrix acting on Dynkin labels, sign)."""
        r = self.r
        gens = []
        for i in range(r):
            # s_i(a)_k = a_k - a_i alpha_i[k]
            S = np.array([[int(k == j) - (j == i) * self.simple[i][k] for j in range(r)]
                          for k in range(r)], dtype=np.int64)
            gens.append(S)
        I = np.eye(r, dtype=np.int64)
        seen = {I.tobytes(): (I, 1)}
        todo = [(I, 1)]
        while todo:
            M, s = todo.pop()
            for S in gens:
                N = S @ M
                key = N.tobytes()
                if key not in seen:
                    seen[key] = (N, -s)
                    todo.append((N, -s))
        return list(seen.values())

    def finite_character(self, lam) -> dict:
        """All weights of the irreducible module L(lam) with multiplicities (Freudenthal)."""
        lam = tuple(lam)
        rc = self.root_coords(lam)
        bound = [int(math.floor(x)) for x in rc]
        doms = []
        for c in np.ndindex(*[b + 1 for b in bound]):
            mu = tuple(lam[i] - sum(c[j] * self.simple[j][i] for j in range(self.r)) for i in range(self.r))
            if all(x >= 0 for x in mu):
                doms.append((sum(c), mu))
        doms.sort()
        lr = tuple(x + 1 for x in lam)
        n_lr = self.ip(lr, lr)
        mult = {lam: 1}

        def m_of(w):
            s, d = self.dominant_sign_nonstrict(w)
            return mult.get(d, 0)

        for _, mu in doms[1:]:
            tot = F(0)
            for a in self.positive:
                k = 1
                while True:
                    w = tuple(mu[i] + k * a[i] for i in range(self.r))
                    mw = m_of(w)
                    if mw == 0:
                        break
                    tot += mw * self.ip(w, a)
                    k += 1
            mr = tuple(x + 1 for x in mu)
            v = 2 * tot / (n_lr - self.ip(mr, mr))
            assert v.denominator == 1 and v >= 0
            if v:
                mult[mu] = int(v)
        out = {}
        for mu, m in mult.items():
            for w in self.orbit(mu):
                out[w] = m
        return out

    def dominant_sign_nonstrict(self, x):
        x = tuple(x)
        s = 1
        while True:
            neg = [i for i in range(self.r) if x[i] < 0]
            if not neg:
                return s, x
            x = self.reflect(x, neg[0])
            s = -s

    def orbit(self, mu):
        mu = tuple(mu)
        seen = {mu}
        todo = [mu]
        while todo:
            a = todo.pop()
            for i in range(self.r):
                if a[i]:
                    b = self.reflect(a, i)
                    if b not in seen:
                        seen.add(b)
                        todo.append(b)
        return seen


def E8():
    return Lie("E8", _chain_cartan(8, [(1, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (2, 4)]))


def E7():
    return Lie("E7", _chain_cartan(7, [(1, 3), (3, 4), (4, 5), (5, 6), (6, 7), (2, 4)]))


def A(n):
    return Lie(f"A{n}", _chain_cartan(n, [(i, i + 1) for i in range(1, n)]))


def G2():
    """Node 1 short (|alpha_1|^2 = 2/3), node 2 long."""
    return Lie("G2", [[2, -3], [-1, 2]], d=[F(1, 3), 1])


# E_7 extended Dynkin diagram 0-1-3-4-5-6-7 (2 on 4): its Z_2 symmetry
E7_OUTER = {0: 7, 7: 0, 1: 6, 6: 1, 3: 5, 5: 3, 2: 2, 4: 4}


def outer_action(L: Lie, perm: dict, k: int, lam):
    """Simple current J: permute affine Dynkin labels (a_0, a_1, ..., a_r) by perm (node i -> perm[i])."""
    a = [k - L.level_of(lam)] + list(lam)
    b = [0] * (L.r + 1)
    for i, x in enumerate(a):
        b[perm[i]] = x
    return tuple(b[1:])


# ------------------------------------------------------------- FKW characters

def ball_points(Fgram: np.ndarray, center: np.ndarray, R2: float) -> np.ndarray:
    """All integer vectors y with (y-center)^T Fgram (y-center) <= R2 (Fincke-Pohst, vectorised)."""
    U = np.linalg.cholesky(Fgram).T          # Fgram = U^T U, U upper triangular
    r = len(center)
    Ys = np.zeros((1, 0), dtype=np.int64)
    S = np.zeros(1)
    eps = 1e-9 * (1 + R2)
    for i in reversed(range(r)):
        if Ys.shape[1]:
            t = (Ys - center[i + 1:]) @ U[i, i + 1:]
        else:
            t = np.zeros(len(Ys))
        rem = np.maximum(R2 - S, 0.0)
        rad = np.sqrt(rem + eps) / U[i, i]
        mid = center[i] - t / U[i, i]
        lo = np.ceil(mid - rad).astype(np.int64)
        hi = np.floor(mid + rad).astype(np.int64)
        cnt = np.maximum(hi - lo + 1, 0)
        idx = np.repeat(np.arange(len(Ys)), cnt)
        offs = np.arange(int(cnt.sum())) - np.repeat(np.cumsum(cnt) - cnt, cnt)
        yi = lo[idx] + offs
        S = S[idx] + (U[i, i] * (yi - center[i]) + t[idx]) ** 2
        Ys = np.column_stack([yi, Ys[idx]])
    return Ys


def fold_to_alcove(L: Lie, Y: np.ndarray, level: int, max_iter=100000):
    """Fold weights Y (rows of Dynkin labels) into the fundamental alcove of W x level*Q^vee
    (simply-laced: affine reflection y -> y - ((y, theta) - level) theta).
    Returns (folded Y, sign, regular mask); non-regular points (fixed by a reflection) get mask False."""
    Y = Y.copy()
    n = len(Y)
    sign = np.ones(n, dtype=np.int64)
    regular = np.zeros(n, dtype=bool)
    alpha = np.array(L.simple, dtype=np.int64)       # row i = alpha_i in Dynkin labels
    m = np.array(L.comarks, dtype=np.int64)
    theta = np.array(L.theta, dtype=np.int64)
    active = np.arange(n)
    it = 0
    while active.size:
        it += 1
        if it > max_iter:
            raise RuntimeError("alcove folding did not terminate")
        A = Y[active]
        lev = A @ m
        wall = (A == 0).any(axis=1) | (lev == level)
        keep = ~wall
        active, A, lev = active[keep], A[keep], lev[keep]
        if not active.size:
            break
        i = A.argmin(axis=1)
        mn = A[np.arange(len(A)), i]
        neg = mn < 0
        rows = active[neg]
        Y[rows] -= mn[neg][:, None] * alpha[i[neg]]
        sign[rows] *= -1
        dom = ~neg
        over = dom & (lev > level)
        rows2 = active[over]
        Y[rows2] -= (lev[over] - level)[:, None] * theta
        sign[rows2] *= -1
        done = dom & (lev < level)
        regular[active[done]] = True
        active = active[neg | over]
    return Y, sign, regular


def _inv_phi_power(r: int, N: int) -> list[int]:
    """Coefficients of prod_n (1-q^n)^{-r} up to q^N."""
    out = [1] + [0] * N
    for _ in range(r):
        for n in range(1, N + 1):
            for m in range(n, N + 1):
                out[m] += out[m - n]
    return out


def fkw_characters(L: Lie, p: int, pp: int, H, verbose=False):
    """W(g) minimal-model characters at (p, p') for simply-laced g:
        chi_{lam,mu} = eta^{-r} sum_{w in W} eps(w) sum_{alpha in Q}
                       q^{|p'(lam+rho) - p w(mu+rho) + p p' alpha|^2 / (2 p p')},
    lam of level p - h^vee, mu of level p' - h^vee. Returns {(lam, mu): (h, coeffs)} with
    coeffs[n] the multiplicity at weight h + n, for all h + n <= H."""
    H = F(H)
    r = L.r
    rho = np.ones(r, dtype=np.int64)
    rho2 = (pp - p) ** 2 * L.ip(L.rho, L.rho)    # (p'-p)^2 |rho|^2: h = (|p'(lam+rho) - p(mu+rho)|^2 - rho2) / 2pp'
    pp2 = 2 * p * pp * L.den                     # exponent = Qint / pp2
    Qmax = int(math.floor((H + rho2 / (2 * p * pp)) * pp2))
    lams = L.integrable(p - L.hv)
    mus = L.integrable(pp - L.hv)
    mu_index = {mu: j for j, mu in enumerate(mus)}
    out = {}
    for lam in lams:
        x0 = pp * (np.array(lam, dtype=np.int64) + rho)
        R2 = Qmax / (L.den * p * p)
        Y = ball_points(L.Ffloat, x0 / p, R2 * (1 + 1e-9))
        Z = p * Y - x0
        Q = np.einsum("ij,jk,ik->i", Z, L.Fint, Z)
        Y, Q = Y[Q <= Qmax], Q[Q <= Qmax]
        Yf, sgn, reg = fold_to_alcove(L, Y, pp)
        mu_rows = Yf[reg] - 1
        js = np.array([mu_index[tuple(int(v) for v in row)] for row in mu_rows], dtype=np.int64)
        num: dict[int, Counter] = {}
        for j, qv, s in zip(js.tolist(), Q[reg].tolist(), sgn[reg].tolist()):
            num.setdefault(j, Counter())[qv] += s
        if verbose:
            print(f"    lambda = {lam}: {len(Y)} lattice points, {int(reg.sum())} regular")
        for j, mu in enumerate(mus):
            terms = {qv: a for qv, a in num.get(j, {}).items() if a}
            if not terms:
                raise ValueError(f"field ({lam}; {mu}) has h > H = {H}; raise H")
            lr = np.array(lam) + 1
            mr = np.array(mu) + 1
            v = pp * lr - p * mr
            h = (F(int(v @ L.Fint @ v), L.den) - rho2) / (2 * p * pp)
            q0 = min(terms)
            assert F(q0, pp2) - rho2 / (2 * p * pp) == h, (lam, mu)
            assert terms[q0] == 1
            K = int(math.floor(H - h))
            numer = [0] * (K + 1)
            for qv, a in terms.items():
                assert (qv - q0) % pp2 == 0, "exponents not congruent mod 1"
                k = (qv - q0) // pp2
                if k <= K:
                    numer[k] += a
            ip = _inv_phi_power(r, K)
            coeffs = [sum(numer[i] * ip[n - i] for i in range(n + 1)) for n in range(K + 1)]
            out[(lam, mu)] = (h, coeffs)
    return out


# ------------------------------------------------------------- affine characters and branching

class AffineStrings:
    """Weyl-Kac characters of the untwisted affine algebra of L, up to grade N, as strings
    S[n] = {nu: multiplicity of the finite irrep nu at grade n}:

        ch L(lam) = q^{h - c/24} sum_n q^n sum_nu S[n][nu] chi_nu.

    S is read off from the anti-invariant numerator
        sum_{beta in Q^vee} q^{(lam+rho, beta) + K|beta|^2/2} sum_{w} eps(w) e^{w(lam + rho + K beta)}
    times 1/prod_{n>=1} (1-q^n)^r prod_{alpha} (1 - q^n e^alpha), at strictly dominant weights."""

    def __init__(self, L: Lie, N: int):
        self.L, self.N = L, N
        r = L.r
        self.Wg = L.weyl_group()
        maxlab = max(abs(x) for a in L.roots for x in a)
        self.B = B = maxlab * N + 4
        shape = (N + 1,) + (2 * B + 1,) * r
        D = np.zeros(shape, dtype=np.int64)
        D[(0,) + (B,) * r] = 1
        axes = tuple(range(r))
        for n in range(1, N + 1):
            for _ in range(r):
                for m in range(n, N + 1):
                    D[m] += D[m - n]
            for a in L.roots:
                for m in range(n, N + 1):
                    D[m] += np.roll(D[m - n], shift=a, axis=axes)
        # nothing may have wrapped around: the support is within maxlab * N of the origin
        edge = np.zeros((2 * B + 1,) * r, dtype=bool)
        for ax in range(r):
            sl = [slice(None)] * r
            sl[ax] = slice(0, 3)
            edge[tuple(sl)] = True
            sl[ax] = slice(2 * B - 2, 2 * B + 1)
            edge[tuple(sl)] = True
        assert not D[:, edge].any()
        assert np.abs(D).max() < 2 ** 62
        self.D = D
        self._cache = {}

    def string(self, k: int, lam) -> list[dict]:
        key = (k, tuple(lam))
        if key in self._cache:
            return self._cache[key]
        L, N, B, r = self.L, self.N, self.B, self.L.r
        K = k + L.hv
        lr = np.array(lam, dtype=np.int64) + 1
        cos = np.array(L.cosimple, dtype=np.int64)
        # beta = sum b_i alpha_i^vee with grade (lam+rho, beta) + K |beta|^2 / 2 <= N
        bmax = 4 + int(math.isqrt(2 * N + 2))
        Bv = np.array(list(np.ndindex(*(2 * bmax + 1,) * r)), dtype=np.int64) - bmax
        beta = Bv @ cos
        g2 = 2 * (beta @ L.Fint @ lr) + K * np.einsum("ij,jk,ik->i", beta, L.Fint, beta)
        assert (g2 % (2 * L.den) == 0).all()
        g = g2 // (2 * L.den)
        sel = g <= N
        assert (g[sel] >= 0).all()
        assert (np.abs(Bv[sel]).max() < bmax), "enlarge the beta box"
        terms = []
        for gb, bt in zip(g[sel].tolist(), beta[sel]):
            y0 = lr + K * bt
            for M, sg in self.Wg:
                terms.append((gb, M @ y0, sg))
        # targets: strictly dominant x = nu + rho. Every weight mu of L(lam) at grade n obeys
        # |mu|^2 <= |lam|^2 + 2 k n (|w mu^|^2 = |mu^|^2 <= |lam^|^2 for the dominant Weyl image),
        # so this ball holds every string entry.
        R2 = float(L.ip(tuple(lam), tuple(lam)) + 2 * k * N)
        X = ball_points(L.Ffloat, np.ones(r), R2 * (1 + 1e-9) + 1e-9)
        X = X[(X >= 1).all(axis=1)]
        Acc = np.zeros((N + 1, len(X)), dtype=np.int64)
        for g, y, s in terms:
            idx = X - y + B
            ok = ((idx >= 0) & (idx <= 2 * B)).all(axis=1)
            if not ok.any():
                continue
            sub = tuple(idx[ok].T)
            for n in range(g, N + 1):
                Acc[n, ok] += s * self.D[n - g][sub]
        S = []
        for n in range(N + 1):
            nz = np.nonzero(Acc[n])[0]
            S.append({tuple(int(v) - 1 for v in X[j]): int(Acc[n, j]) for j in nz})
        assert S[0] == {tuple(lam): 1}, S[0]
        assert all(v > 0 for row in S for v in row.values()), "negative string multiplicity"
        self._cache[key] = S
        return S


class Tensor:
    """Finite tensor products chi_a chi_b = sum_c N_ab^c chi_c (Brauer-Klimyk), cached."""

    def __init__(self, L: Lie):
        self.L = L
        self.chars = {}
        self.cache = {}

    def char(self, a):
        if a not in self.chars:
            self.chars[a] = self.L.finite_character(a)
        return self.chars[a]

    def __call__(self, a, b) -> dict:
        key = (a, b)
        if key not in self.cache:
            L = self.L
            if L.dim(a) > L.dim(b):
                a, b = b, a
            out = Counter()
            for g, m in self.char(a).items():
                s, d = L.dominant_sign(tuple(b[i] + g[i] + 1 for i in range(L.r)))
                if s:
                    out[tuple(x - 1 for x in d)] += s * m
            self.cache[key] = {c: v for c, v in out.items() if v}
            assert all(v > 0 for v in self.cache[key].values())
        return self.cache[key]


def branching(aff: AffineStrings, tens: Tensor, k1: int, k2: int, N: int | None = None):
    """Branching functions of L_{k1} x L_{k2} / L_{k1+k2}: {(nu, lam, mu): [m_0, m_1, ...]} where
    ch_nu^{(k1)} ch_lam^{(k2)} = sum_mu b_{nu,lam;mu} ch_mu^{(k1+k2)} and b = q^{h_nu + h_lam - h_mu - c/24}
    sum_n m_n q^n (m_n exact for n <= N)."""
    L = aff.L
    N = aff.N if N is None else N
    k3 = k1 + k2
    out = {}
    for nu in L.integrable(k1):
        S1 = aff.string(k1, nu)
        for lam in L.integrable(k2):
            S2 = aff.string(k2, lam)
            R = [Counter() for _ in range(N + 1)]
            for n1 in range(N + 1):
                for a, x in S1[n1].items():
                    for n2 in range(N + 1 - n1):
                        for b, y in S2[n2].items():
                            for cc, z in tens(a, b).items():
                                R[n1 + n2][cc] += x * y * z
            res = {}
            for n in range(N + 1):
                for mu, mlt in list(R[n].items()):
                    if mlt == 0:
                        continue
                    if mlt < 0 or L.level_of(mu) > k3:
                        raise RuntimeError(f"decomposition failed at grade {n}: {mu} x {mlt}")
                    res.setdefault(mu, [0] * (N + 1))[n] = mlt
                    S3 = aff.string(k3, mu)
                    for j in range(N + 1 - n):
                        for c2, w in S3[j].items():
                            R[n + j][c2] -= mlt * w
                assert not any(R[n].values()), f"residual at grade {n}"
            for mu in L.integrable(k3):
                out[(nu, lam, mu)] = res.get(mu, [0] * (N + 1))
    return out
