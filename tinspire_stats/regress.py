"""Regressions -- ``menu > Statistics > Stat Calculations``.

Name-for-name with the reference guide, including the guide's own
inconsistencies: ``stat.r2`` on the linear models but ``stat.R2`` on the
polynomial and multiple models, ``stat.m``/``stat.b`` for ``LinRegMx`` versus
``stat.a``/``stat.b`` for ``LinRegBx``.  Where the guide prints one variable two
ways (``stat.r²`` *vs* ``stat.r2``, ``stat.ExpMat`` *vs* ``stat.ExpMatrix``) both
spellings resolve.

Fidelity tiers
--------------
* **Closed form, exact** -- ``LinRegMx``, ``LinRegBx``, ``QuadReg``,
  ``CubicReg``, ``QuartReg``, ``LnReg``, ``ExpReg``, ``PowerReg``, ``MedMed``,
  ``MultReg``, ``MultRegIntervals``, ``MultRegTests``, ``LinRegtTest``,
  ``LinRegtIntervals``.  Weighted least squares and documented arithmetic, so
  they agree with the calculator to the last displayed digit.
* **Iterative, best-effort** -- ``Logistic``, ``LogisticD``, ``SinReg``.  The
  Nspire drives these with undocumented iterative solvers and fixed iteration
  defaults (``SinReg`` tries at most 8 times, ``Logistic`` starts from its own
  seed).  Damped Gauss-Newton with multi-start converges to the same
  least-squares optimum -- matching TI wherever the problem is well posed, but
  not claimed to be bit-identical on pathological data.
"""

from __future__ import annotations

from math import cos, exp, isfinite, log, pi, sin, sqrt

from ._core import (
    _abs,
    _float,
    _int,
    _isinstance,
    _len,
    _list,
    _max,
    _min,
    _range,
    _sorted,
    _sum,
    _zip,
    ArgumentError,
    DimensionMismatchError,
    DomainError,
    check_integer_freq,
    is_void,
    solve,
    solve_normal_equations,
)
from .statvar import RegEqn, publish


# --------------------------------------------------------------------------
# shared plumbing
# --------------------------------------------------------------------------
def _filter(x, y, freq=None, category=None, include=None):
    """Drop void pairs first, then apply Category/Include, keeping Freq aligned."""
    xs, ys = _list(x), _list(y)
    if _len(xs) != _len(ys):
        raise DimensionMismatchError()
    if freq is not None and _len(freq) != _len(xs):
        raise DimensionMismatchError()
    px, py, pf = [], [], []
    for i in _range(_len(xs)):
        if is_void(xs[i]) or is_void(ys[i]):
            continue
        px.append(_float(xs[i]))
        py.append(_float(ys[i]))
        if freq is not None:
            pf.append(_float(freq[i]))
    if category is not None:
        cat = _list(category)
        if _len(cat) != _len(xs):
            raise DimensionMismatchError()
        allowed = _list(include or [])
        keep = [i for i, c in enumerate(cat) if c in allowed]
        px = [px[i] for i in keep]
        py = [py[i] for i in keep]
        pf = [pf[i] for i in keep] if freq is not None else []
    if freq is not None:
        check_integer_freq(pf)
    if not px:
        raise DomainError()
    w = pf if freq is not None else [1.0] * _len(px)
    return px, py, w


def _common(px, py, w):
    n = _sum(w)
    mx = _sum(a * wi for a, wi in _zip(px, w)) / n
    my = _sum(b * wi for b, wi in _zip(py, w)) / n
    return n, mx, my


def _finish(d, resid, px, py, w, after_resid=None):
    """Attach the tail every regression publishes.

    ``stat.Resid`` always; then ``after_resid``, if the model has further
    residual-style outputs -- the transformed fits publish ``stat.ResidTrans``
    directly *behind* ``stat.Resid``, not in front of it; then
    ``stat.XReg``/``stat.YReg``/``stat.FreqReg`` for the curve fits -- the guide
    does not list those for ``MultReg`` and friends.
    """
    d["Resid"] = _list(resid)
    if after_resid:
        d.update(after_resid)
    if px is not None:
        d["XReg"] = _list(px)
        d["YReg"] = _list(py)
        d["FreqReg"] = _list(w)
    return d


# --------------------------------------------------------------------------
# lines
# --------------------------------------------------------------------------
def LinRegMx(X, Y, Freq=None, Category=None, Include=None):
    """``LinRegMx X,Y[,[Freq][,Category,Include]]`` -- y = m·x+b.

    Publishes ``stat.m``, ``stat.b``, ``stat.r``, ``stat.r2``, ``stat.Resid``,
    ``stat.RegEqn``, ``stat.XReg``, ``stat.YReg``, ``stat.FreqReg``.  This is
    the ``mx+b`` form; ``LinRegBx`` fits the identical line but names the
    coefficients ``a``+``b·x``.
    """
    px, py, w = _filter(X, Y, Freq, Category, Include)
    n, mx, my = _common(px, py, w)
    sxx = _sum(wi * (a - mx) ** 2 for a, wi in _zip(px, w))
    if sxx == 0:
        raise DomainError("all x values are identical")
    sxy = _sum(wi * (a - mx) * (b - my) for a, b, wi in _zip(px, py, w))
    m = sxy / sxx
    b = my - m * mx
    syy = _sum(wi * (bb - my) ** 2 for bb, wi in _zip(py, w))
    denom = sqrt(sxx * syy)
    r = sxy / denom if denom else 0.0
    resid = [yy - (m * xx + b) for xx, yy in _zip(px, py)]
    d = {
        "RegEqn": RegEqn("LinRegMx", {"m": m, "b": b}, "y = m·x+b"),
        "m": m,
        "b": b,
        "r²": r * r,
        "r": r,
    }
    return publish(_finish(d, resid, px, py, w))


def LinRegBx(X, Y, Freq=None, Category=None, Include=None):
    """``LinRegBx X,Y[,[Freq][,Category,Include]]`` -- y = a+b·x.

    Same line as ``LinRegMx``, different coefficient names: ``stat.a`` is the
    intercept and ``stat.b`` the slope.
    """
    px, py, w = _filter(X, Y, Freq, Category, Include)
    n, mx, my = _common(px, py, w)
    sxx = _sum(wi * (a - mx) ** 2 for a, wi in _zip(px, w))
    if sxx == 0:
        raise DomainError("all x values are identical")
    sxy = _sum(wi * (a - mx) * (b - my) for a, b, wi in _zip(px, py, w))
    slope = sxy / sxx
    inter = my - slope * mx
    syy = _sum(wi * (bb - my) ** 2 for bb, wi in _zip(py, w))
    denom = sqrt(sxx * syy)
    r = sxy / denom if denom else 0.0
    resid = [yy - (inter + slope * xx) for xx, yy in _zip(px, py)]
    d = {
        "RegEqn": RegEqn("LinRegBx", {"a": inter, "b": slope}, "y = a+b·x"),
        "a": inter,
        "b": slope,
        "r²": r * r,
        "r": r,
    }
    return publish(_finish(d, resid, px, py, w))


def _poly(X, Y, degree, kind, names, symbolic, Freq, Category, Include):
    px, py, w = _filter(X, Y, Freq, Category, Include)
    n = _sum(w)
    if n <= degree:
        raise DomainError("not enough data points for this model")
    design = [[xx ** (degree - j) for j in _range(degree + 1)] for xx in px]
    beta = solve_normal_equations(design, py, w)
    fit = [_sum(b * c for b, c in _zip(beta, row)) for row in design]
    resid = [yy - f for yy, f in _zip(py, fit)]
    sse = _sum(wi * e * e for e, wi in _zip(resid, w))
    my = _sum(b * wi for b, wi in _zip(py, w)) / n
    sst = _sum(wi * (b - my) ** 2 for b, wi in _zip(py, w))
    r2 = 1.0 - sse / sst if sst else 0.0
    coeffs = {names[j]: beta[j] for j in _range(degree + 1)}
    # The polynomial fits are the family that prints a capital stat.R², and it
    # comes after the coefficients -- not in front of them, and with no
    # lower-case twin.  (Verified against the guide's QuadReg, CubicReg and
    # QuartReg tables; the capital/lower-case split is real, not a typo.)
    d = {"RegEqn": RegEqn(kind, coeffs, symbolic)}
    d.update(coeffs)
    d["R²"] = r2
    return publish(_finish(d, resid, px, py, w))


def QuadReg(X, Y, Freq=None, Category=None, Include=None):
    """``QuadReg`` -- y=a·x²+b·x+c (``stat.a``..``stat.c``, ``stat.R2``)."""
    return _poly(X, Y, 2, "QuadReg", ["a", "b", "c"], "y = a·x²+b·x+c",
                 Freq, Category, Include)


def CubicReg(X, Y, Freq=None, Category=None, Include=None):
    """``CubicReg`` -- y=a·x³+b·x²+c·x+d."""
    return _poly(X, Y, 3, "CubicReg", ["a", "b", "c", "d"],
                 "y = a·x³+b·x²+c·x+d", Freq, Category, Include)


def QuartReg(X, Y, Freq=None, Category=None, Include=None):
    """``QuartReg`` -- y=a·x⁴+b·x³+c·x²+d·x+e."""
    return _poly(X, Y, 4, "QuartReg", ["a", "b", "c", "d", "e"],
                 "y = a·x⁴+b·x³+c·x²+d·x+e", Freq, Category, Include)


# --------------------------------------------------------------------------
# transformed linear forms
# --------------------------------------------------------------------------
def LnReg(X, Y, Freq=None, Category=None, Include=None):
    """``LnReg`` -- y=a+b·ln(x).

    ``stat.r``/``stat.r2`` describe the fit of y on ln(x) -- the guide calls
    this "correlation coefficient for transformed data (ln(x), y)".
    ``stat.ResidTrans`` holds the residuals in those transformed coordinates,
    which for this particular model coincide with ``stat.Resid``.
    """
    px, py, w = _filter(X, Y, Freq, Category, Include)
    tx = []
    for v in px:
        if v <= 0:
            raise DomainError("ln(x) requires x > 0")
        tx.append(log(v))
    n, mx, my = _common(tx, py, w)
    sxx = _sum(wi * (a - mx) ** 2 for a, wi in _zip(tx, w))
    if sxx == 0:
        raise DomainError()
    sxy = _sum(wi * (a - mx) * (b - my) for a, b, wi in _zip(tx, py, w))
    b = sxy / sxx
    a = my - b * mx
    syy = _sum(wi * (bb - my) ** 2 for bb, wi in _zip(py, w))
    denom = sqrt(sxx * syy)
    r = sxy / denom if denom else 0.0
    resid = [yy - (a + b * t) for t, yy in _zip(tx, py)]
    d = {
        "RegEqn": RegEqn("LnReg", {"a": a, "b": b}, "y = a+b·ln(x)"),
        "a": a,
        "b": b,
        "r²": r * r,
        "r": r,
    }
    return publish(_finish(d, resid, px, py, w,
                           after_resid={"ResidTrans": _list(resid)}))


def ExpReg(X, Y, Freq=None, Category=None, Include=None):
    """``ExpReg`` -- y=a·bˣ, fitted as ln y = ln a + (ln b)·x."""
    px, py, w = _filter(X, Y, Freq, Category, Include)
    ty = []
    for v in py:
        if v <= 0:
            raise DomainError("exponential regression requires y > 0")
        ty.append(log(v))
    n, mx, my = _common(px, ty, w)
    sxx = _sum(wi * (a - mx) ** 2 for a, wi in _zip(px, w))
    if sxx == 0:
        raise DomainError()
    sxy = _sum(wi * (a - mx) * (b - my) for a, b, wi in _zip(px, ty, w))
    slope = sxy / sxx
    inter = my - slope * mx
    syy = _sum(wi * (bb - my) ** 2 for bb, wi in _zip(ty, w))
    denom = sqrt(sxx * syy)
    r = sxy / denom if denom else 0.0
    a, b = exp(inter), exp(slope)
    resid = [yy - a * b ** xx for xx, yy in _zip(px, py)]
    res_t = [t - (inter + slope * xx) for xx, t in _zip(px, ty)]
    d = {
        "RegEqn": RegEqn("ExpReg", {"a": a, "b": b}, "y = a·(b)ˣ"),
        "a": a,
        "b": b,
        "r²": r * r,
        "r": r,
    }
    return publish(_finish(d, resid, px, py, w,
                           after_resid={"ResidTrans": _list(res_t)}))


def PowerReg(X, Y, Freq=None, Category=None, Include=None):
    """``PowerReg`` -- y=a·xᵇ, fitted as ln y = ln a + b·ln x.

    (The older TI catalog also spells this ``PwrReg``; see ``legacy.py``.)
    """
    px, py, w = _filter(X, Y, Freq, Category, Include)
    tx, ty = [], []
    for xx, yy in _zip(px, py):
        if xx <= 0 or yy <= 0:
            raise DomainError("power regression requires x > 0 and y > 0")
        tx.append(log(xx))
        ty.append(log(yy))
    n, mx, my = _common(tx, ty, w)
    sxx = _sum(wi * (a - mx) ** 2 for a, wi in _zip(tx, w))
    if sxx == 0:
        raise DomainError()
    sxy = _sum(wi * (a - mx) * (b - my) for a, b, wi in _zip(tx, ty, w))
    b = sxy / sxx
    inter = my - b * mx
    syy = _sum(wi * (bb - my) ** 2 for bb, wi in _zip(ty, w))
    denom = sqrt(sxx * syy)
    r = sxy / denom if denom else 0.0
    a = exp(inter)
    resid = [yy - a * xx ** b for xx, yy in _zip(px, py)]
    res_t = [t - (inter + b * xx) for xx, t in _zip(tx, ty)]
    d = {
        "RegEqn": RegEqn("PowerReg", {"a": a, "b": b}, "y = a·(x)ᵇ"),
        "a": a,
        "b": b,
        "r²": r * r,
        "r": r,
    }
    return publish(_finish(d, resid, px, py, w,
                           after_resid={"ResidTrans": _list(res_t)}))


# --------------------------------------------------------------------------
# median-median line
# --------------------------------------------------------------------------
def _three_group_sizes(n):
    """Split n points into three groups.

    ``n = 3q``   -> ``(q, q, q)``
    ``n = 3q+1`` -> ``(q, q+1, q)``    the middle group absorbs the extra point
    ``n = 3q+2`` -> ``(q+1, q, q+1)``  the outer groups absorb the extra points
    """
    q, r = divmod(n, 3)
    if r == 0:
        return q, q, q
    if r == 1:
        return q, q + 1, q
    return q + 1, q, q + 1


def _median(seq):
    vals = _sorted(seq)
    n = _len(vals)
    if n % 2:
        return _float(vals[n // 2])
    return (vals[n // 2 - 1] + vals[n // 2]) / 2.0


def MedMed(X, Y, Freq=None, Category=None, Include=None):
    """``MedMed`` -- the resistant median-median line y=m·x+b.

    Points are ordered by x and cut into three groups (``_three_group_sizes``),
    each group collapses to its median point, and then::

        m = (M3y - M1y) / (M3x - M1x)
        b = [(M1y - m·M1x) + (M2y - m·M2x) + (M3y - m·M3x)] / 3

    The third group's median point gets a full third of the weight rather than a
    half, which is what pulls the line off the simple two-point fit.  The guide
    lists only ``stat.m``, ``stat.b`` and ``stat.Resid`` -- there is deliberately
    no r² for a resistant line.
    """
    px, py, w = _filter(X, Y, Freq, Category, Include)
    pts = _sorted(_zip(px, py), key=lambda p: p[0])
    s1, s2, s3 = _three_group_sizes(_len(pts))
    groups = [pts[:s1], pts[s1:s1 + s2], pts[s1 + s2:]]
    (x1, y1), (x2, y2), (x3, y3) = (
        (_median(p[0] for p in g), _median(p[1] for p in g)) for g in groups
    )
    if x3 == x1:
        raise DomainError("degenerate median-median line")
    m = (y3 - y1) / (x3 - x1)
    b = ((y1 - m * x1) + (y2 - m * x2) + (y3 - m * x3)) / 3.0
    resid = [yy - (m * xx + b) for xx, yy in _zip(px, py)]
    d = {
        "RegEqn": RegEqn("MedMed", {"m": m, "b": b}, "y = m·x+b"),
        "m": m,
        "b": b,
        "_summary": [(x1, y1), (x2, y2), (x3, y3)],
    }
    return publish(_finish(d, resid, px, py, w))


# --------------------------------------------------------------------------
# iterative nonlinear fits
# --------------------------------------------------------------------------
def _gauss_newton(func, theta0, xs, ys, w, *, iters=64, restarts=6,
                  bounds=None, rng_seed=1):
    """Damped Gauss-Newton with a numeric Jacobian and a small multi-start.

    The Nspire's own solvers are undocumented, so this cannot promise
    bit-identical iterates; it does promise the same least-squares optimum for
    the well-posed problems these models are used on.
    """
    import random

    rng = random.Random(rng_seed)
    best = None

    def sse(theta):
        try:
            r = [_float(func(theta, x)) for x in xs]
        except (ValueError, OverflowError, ZeroDivisionError):
            return float("inf")
        if any((v != v) or not isfinite(v) for v in r):
            return float("inf")
        return _sum(wi * (a - b) ** 2 for a, b, wi in _zip(r, ys, w))

    for attempt in _range(restarts):
        theta = _list(theta0)
        if attempt:
            theta = [t * (1 + 0.35 * rng.uniform(-1, 1)) + 1e-9 for t in theta]
        cur = sse(theta)
        lam = 1e-3
        for _ in _range(iters):
            p = _len(theta)
            jac = []
            for i in _range(_len(xs)):
                row = []
                for j in _range(p):
                    h = 1e-6 * max(1.0, _abs(theta[j]))
                    tp = _list(theta)
                    tm = _list(theta)
                    tp[j] += h
                    tm[j] -= h
                    fp = func(tp, xs[i])
                    fm = func(tm, xs[i])
                    row.append((fp - fm) / (2 * h))
                jac.append(row)
            resid = [ys[i] - func(theta, xs[i]) for i in _range(_len(xs))]
            ata = [[0.0] * p for _ in _range(p)]
            atb = [0.0] * p
            for i in _range(_len(xs)):
                wi = w[i]
                for j in _range(p):
                    atb[j] += wi * jac[i][j] * resid[i]
                    for k in _range(p):
                        ata[j][k] += wi * jac[i][j] * jac[i][k]
            improved = False
            for _ in _range(24):
                damped = [
                    [ata[j][k] + (lam * ata[j][j] if j == k else 0.0)
                     for k in _range(p)]
                    for j in _range(p)
                ]
                try:
                    step = solve(damped, atb)
                except DomainError:
                    lam *= 10
                    continue
                cand = [theta[j] + step[j] for j in _range(p)]
                if bounds is not None:
                    cand = [bounds[j](cand[j]) for j in _range(p)]
                val = sse(cand)
                if val < cur:
                    theta, cur, lam, improved = cand, val, max(lam * 0.4, 1e-12), True
                    break
                lam *= 8
            if not improved:
                break
        if best is None or cur < best[1]:
            best = (_list(theta), cur)
    return best[0], best[1]


_POSITIVE = lambda v: max(v, 1e-12)  # noqa: E731


def _logistic_f(theta, x):
    a, b, c = theta
    return c / (1 + a * exp(-b * x))


def _logisticd_f(theta, x):
    a, b, c, d = theta
    return c / (1 + a * exp(-b * x)) + d


def _sin_f(theta, x):
    a, b, c, d = theta
    return a * sin(b * x + c) + d


def Logistic(X, Y, Freq=None, Category=None, Include=None, *, Iterations=None):
    """``Logistic X,Y[,[Freq][,Category,Include]]`` -- y = c/(1+a·e^(-bx)).

    The reference guide gives ``Logistic`` no ``Iterations`` argument (that is
    ``LogisticD``'s); the keyword here is an extension for callers who want to
    trade speed for convergence.  Publishes ``stat.a``, ``stat.b``, ``stat.c``,
    ``stat.Resid``, ``stat.RegEqn`` and the ``*Reg`` echo lists.
    """
    px, py, w = _filter(X, Y, Freq, Category, Include)
    hi, lo = _max(py), _min(py)
    c0 = hi * 1.05 if lo > 0 else hi - lo
    a0 = max(c0 / py[0] - 1.0, 1e-3) if py[0] else 1.0
    span = (_max(px) - _min(px)) or 1.0
    b0 = 1.0 / span
    theta, _ = _gauss_newton(
        _logistic_f, [a0, b0, c0], px, py, w,
        iters=Iterations or 96,
        bounds=[_POSITIVE, lambda v: v, lambda v: v],
    )
    a, b, c = theta
    resid = [yy - c / (1 + a * exp(-b * xx)) for xx, yy in _zip(px, py)]
    d = {
        "RegEqn": RegEqn("Logistic", {"a": a, "b": b, "c": c}, "y = c/(1+a·e⁻ᵇˣ)"),
        "a": a,
        "b": b,
        "c": c,
    }
    return publish(_finish(d, resid, px, py, w))


def LogisticD(X, Y, Iterations=None, Freq=None, Category=None, Include=None):
    """``LogisticD X,Y[,[Iterations][,Freq][,Category,Include]]``.

    y = c/(1+a·e^(-bx)) + d.  ``Iterations`` caps the solver exactly as the
    handheld's argument of the same name does; ``d`` is the extra asymptote that
    distinguishes this model from ``Logistic``.
    """
    px, py, w = _filter(X, Y, Freq, Category, Include)
    c0 = (_max(py) - _min(py)) or 1.0
    span = (_max(px) - _min(px)) or 1.0
    d0 = _min(py)
    theta, _ = _gauss_newton(
        _logisticd_f, [1.0, 1.0 / span, c0, d0], px, py, w,
        iters=Iterations or 96,
        bounds=[_POSITIVE, lambda v: v, lambda v: v, lambda v: v],
    )
    a, b, c, dd = theta
    resid = [yy - (c / (1 + a * exp(-b * xx)) + dd) for xx, yy in _zip(px, py)]
    d = {
        "RegEqn": RegEqn("LogisticD", {"a": a, "b": b, "c": c, "d": dd},
                          "y = c/(1+a·e⁻ᵇˣ)+d"),
        "a": a,
        "b": b,
        "c": c,
        "d": dd,
    }
    return publish(_finish(d, resid, px, py, w))


def _estimate_angular_frequency(xs, ys):
    """Periodogram sweep for a starting b, in radians per x-unit."""
    span = _max(xs) - _min(xs)
    if span == 0:
        raise DomainError()
    n = _len(xs)
    mx = _sum(xs) / n
    my = _sum(ys) / n
    best_b, best_power = 2 * pi / span, -1.0
    for k in _range(1, 401):
        b = 2 * pi * k / (4 * span)
        re = _sum((yy - my) * cos(b * xx) for xx, yy in _zip(xs, ys))
        im = _sum((yy - my) * sin(b * xx) for xx, yy in _zip(xs, ys))
        power = re * re + im * im
        if power > best_power:
            best_b, best_power = b, power
    return best_b


def SinReg(X, Y, Iterations=None, Period=None, Category=None, Include=None):
    """``SinReg X,Y[,[Iterations],[Period][,Category,Include]]``.

    y = a·sin(b·x+c)+d, always in radians regardless of the angle mode -- the
    guide is explicit about that.  ``Period`` pins b to 2π/Period; otherwise b
    comes from a periodogram sweep and is then refined together with a, c and d.
    The handheld defaults to 8 attempts and accepts 1–16; pass ``Iterations`` to
    match, or leave it out for a more patient search.
    """
    px, py, w = _filter(X, Y, None, Category, Include)
    if _len(px) < 4:
        raise DomainError("SinReg needs at least four points")
    if Period is not None:
        if Period == 0:
            raise DomainError()
        b0 = 2 * pi / Period
    else:
        b0 = _estimate_angular_frequency(px, py)
    amp = (_max(py) - _min(py)) / 2 or 1.0
    mid = (_max(py) + _min(py)) / 2
    iters = 8 if Iterations is None else _int(Iterations)
    if not 1 <= iters <= 16:
        raise ArgumentError("Iterations must be between 1 and 16")
    theta, _ = _gauss_newton(
        _sin_f, [amp, b0, 0.0, mid], px, py, w,
        iters=max(iters * 4, 32), restarts=4,
        bounds=[lambda v: v, _POSITIVE, lambda v: v, lambda v: v],
    )
    a, b, c, d = theta
    resid = [yy - (a * sin(b * xx + c) + d) for xx, yy in _zip(px, py)]
    out = {
        "RegEqn": RegEqn("SinReg", {"a": a, "b": b, "c": c, "d": d},
                          "y = a·sin(bx+c)+d"),
        "a": a,
        "b": b,
        "c": c,
        "d": d,
    }
    return publish(_finish(out, resid, px, py, w))


# --------------------------------------------------------------------------
# multiple regression
# --------------------------------------------------------------------------
def _invert(m):
    n = _len(m)
    aug = [
        [_float(m[i][j]) for j in _range(n)] + [1.0 if i == j else 0.0 for j in _range(n)]
        for i in _range(n)
    ]
    for col in _range(n):
        piv = _max(_range(col, n), key=lambda r: _abs(aug[r][col]))
        if _abs(aug[piv][col]) < 1e-300:
            raise DomainError("singular matrix")
        if piv != col:
            aug[col], aug[piv] = aug[piv], aug[col]
        pv = aug[col][col]
        aug[col] = [v / pv for v in aug[col]]
        for r in _range(n):
            if r == col:
                continue
            f = aug[r][col]
            if f:
                aug[r] = [x - f * y for x, y in _zip(aug[r], aug[col])]
    return [row[n:] for row in aug]


def _ols_stats(py, columns):
    n = _len(py)
    for c in columns:
        if _len(c) != n:
            raise DimensionMismatchError()
    p = 1 + _len(columns)
    if n <= p:
        raise DomainError("not enough data points for this model")
    design = [[1.0] + [_float(c[i]) for c in columns] for i in _range(n)]
    beta = solve_normal_equations(design, py)
    fit = [_sum(b * c for b, c in _zip(beta, row)) for row in design]
    resid = [a - b for a, b in _zip(py, fit)]
    sse = _sum(e * e for e in resid)
    df_err = n - p
    mse = sse / df_err
    my = _sum(py) / n
    sst = _sum((a - my) ** 2 for a in py)
    r2 = 1.0 - sse / sst if sst else 0.0
    adj = 1 - (1 - r2) * (n - 1) / df_err
    xtx = [[0.0] * p for _ in _range(p)]
    for row in design:
        for j in _range(p):
            for k in _range(p):
                xtx[j][k] += row[j] * row[k]
    inv = _invert(xtx)
    se = [sqrt(mse * inv[j][j]) for j in _range(p)]
    tvals = [beta[j] / se[j] if se[j] else float("nan") for j in _range(p)]
    lev = [
        _sum(row[j] * inv[j][k] * row[k] for j in _range(p) for k in _range(p))
        for row in design
    ]
    return {
        "design": design, "beta": beta, "fit": fit, "resid": resid,
        "n": n, "p": p, "sse": sse, "mse": mse, "df_err": df_err,
        "sst": sst, "r2": r2, "adj_r2": adj, "inv": inv, "se": se,
        "t": tvals, "leverage": lev, "s": sqrt(mse),
    }


def _multi_reg_eqn(beta):
    coeffs = {"b" + str(i): beta[i] for i in _range(_len(beta))}
    return RegEqn("MultReg", coeffs, "y = b0+b1·x1+b2·x2+..."), coeffs


def MultReg(Y, *X, **kwargs):
    """``MultReg Y,X1[,X2,...,X10]`` -- y = b0+b1·x1+b2·x2+...

    Publishes ``stat.b0``..``stat.b10``, ``stat.R²``, ``stat.yList`` (fitted
    values) and ``stat.Resid``.  The guide lists only those -- no ``*Reg`` echo
    lists for the multiple models, and the coefficients are published bare here
    (``stat.b0``), unlike ``MultRegTests``, which collects them into
    ``stat.bList`` instead.
    """
    py = [v for v in _list(Y) if not is_void(v)]
    columns = [_list(c) for c in X]
    st = _ols_stats(py, columns)
    eqn, coeffs = _multi_reg_eqn(st["beta"])
    d = {"RegEqn": eqn}
    d.update(coeffs)
    d["R²"] = st["r2"]
    d["yList"] = st["fit"]
    return publish(_finish(d, st["resid"], None, py, None))


def _durbin_watson(resid):
    denom = _sum(e * e for e in resid)
    if not denom:
        return float("nan")
    return _sum((resid[i] - resid[i - 1]) ** 2 for i in _range(1, _len(resid))) / denom


def MultRegTests(Y, *X, **kwargs):
    """``MultRegTests Y,X1[,...,X10]`` -- global F test plus per-coefficient t tests.

    The whole report: ``stat.F``, ``stat.PVal``, ``stat.R²``, ``stat.AdjR²``,
    ``stat.s``, ``stat.DW`` (Durbin-Watson), the SS/MS/df ANOVA table,
    ``stat.bList``/``stat.tList``/``stat.PList``/``stat.SEList``, standardised
    residuals ``stat.sResid``, ``stat.CookDist`` and ``stat.Leverage``.

    Note that the coefficients are published *as a list* (``stat.bList``) and
    not as bare ``stat.b0``/``stat.b1``: unlike ``MultReg``, this procedure
    never defines the individual names.  And ``stat.Resid`` sits in the middle
    of the run, between ``stat.yList`` and ``stat.sResid``, so the report is
    assembled here rather than through ``_finish``.
    """
    from .distributions import FCdf, tCdf

    py = [v for v in _list(Y) if not is_void(v)]
    columns = [_list(c) for c in X]
    st = _ols_stats(py, columns)
    p, df_err = st["p"], st["df_err"]
    k = p - 1
    ssr = st["sst"] - st["sse"]
    msr = ssr / k
    f = msr / st["mse"] if st["mse"] else float("nan")
    pval = 1.0 - FCdf(0, f, k, df_err)
    s = st["s"]
    sresid = [
        e / (s * sqrt(1 - h)) if s and 0 < h < 1 else float("nan")
        for e, h in _zip(st["resid"], st["leverage"])
    ]
    cooks = [
        (e * e) / (p * st["mse"]) * (h / (1 - h) ** 2) if st["mse"] and h < 1 else float("nan")
        for e, h in _zip(st["resid"], st["leverage"])
    ]
    # two-tailed p for a symmetric t: 2·P(T ≤ -|t|).  Note that
    # 2·(1 - tCdf(0, |t|, df)) is *not* the same number -- tCdf(0, x, df) is
    # the area from 0 to x, so subtracting it from 1 also picks up the whole
    # lower half and the result saturates at 1.
    plist = [
        2 * tCdf(-9e999, -_abs(t), df_err) if t == t else float("nan")
        for t in st["t"]
    ]
    eqn, _coeffs = _multi_reg_eqn(st["beta"])
    return publish({
        "RegEqn": eqn,
        "F": f,
        "PVal": pval,
        "R²": st["r2"],
        "AdjR²": st["adj_r2"],
        "s": s,
        "DW": _durbin_watson(st["resid"]),
        "dfReg": k,
        "SSReg": ssr,
        "MSReg": msr,
        "dfError": df_err,
        "SSError": st["sse"],
        "MSError": st["mse"],
        "bList": _list(st["beta"]),
        "tList": _list(st["t"]),
        "PList": plist,
        "SEList": _list(st["se"]),
        "yList": st["fit"],
        "Resid": _list(st["resid"]),
        "sResid": sresid,
        "CookDist": cooks,
        "Leverage": _list(st["leverage"]),
    })


def MultRegIntervals(Y, *args, CLevel=0.95):
    """``MultRegIntervals Y,X1,...,Xk,XValList[,CLevel]``.

    ``XValList`` carries the predictor values of one new observation.  Publishes
    the point estimate ``stat.y``; the mean-response interval
    ``stat.CLower``/``stat.CUpper`` with ``stat.SE``/``stat.ME``; the
    single-observation interval ``stat.LowerPred``/``stat.UpperPred`` with
    ``stat.SEPred``/``stat.MEPred``; plus ``stat.dfError``, ``stat.bList`` and
    ``stat.Resid``.

    The split between "predictor columns" and "XValList" is inferred from the
    data: every predictor column has the same length as ``Y``, ``XValList`` does
    not, exactly as the handheld's variadic syntax implies.
    """
    from .distributions import invt

    py = [v for v in _list(Y) if not is_void(v)]
    n = _len(py)
    k = 0
    rest = _list(args)
    while k < _len(rest) and _isinstance(rest[k], (list, tuple)) and _len(rest[k]) == n:
        k += 1
    columns = [_list(c) for c in rest[:k]]
    tail = rest[k:]
    if not tail:
        raise ArgumentError("MultRegIntervals needs an XValList")
    xval_list = _list(tail[0])
    if _len(tail) > 1:
        CLevel = _float(tail[1])
    st = _ols_stats(py, columns)
    p, df_err = st["p"], st["df_err"]
    v = [1.0] + [_float(x) for x in xval_list]
    if _len(v) != p:
        raise DimensionMismatchError(
            f"XValList has {_len(v) - 1} values but the model needs {p - 1}"
        )
    yhat = _sum(b * c for b, c in _zip(st["beta"], v))
    quad = _sum(v[j] * st["inv"][j][k2] * v[k2] for j in _range(p) for k2 in _range(p))
    se = sqrt(st["mse"] * quad)
    sepred = sqrt(st["mse"] * (1 + quad))
    tcrit = invt(1 - (1 - CLevel) / 2, df_err)
    eqn, _coeffs = _multi_reg_eqn(st["beta"])
    # The XValList is an *input*, not a result: the guide's table starts at
    # stat.RegEqn and lists no such variable.  The coefficients likewise appear
    # only as stat.bList here, never as bare stat.b0/stat.b1.
    return publish({
        "RegEqn": eqn,
        "y": yhat,
        "dfError": df_err,
        "CLower": yhat - tcrit * se,
        "CUpper": yhat + tcrit * se,
        "ME": tcrit * se,
        "SE": se,
        "LowerPred": yhat - tcrit * sepred,
        "UpperPred": yhat + tcrit * sepred,
        "MEPred": tcrit * sepred,
        "SEPred": sepred,
        "bList": _list(st["beta"]),
        "Resid": _list(st["resid"]),
    })


# --------------------------------------------------------------------------
# linear regression inference
# --------------------------------------------------------------------------
def LinRegtIntervals(X, Y, F=None, kind=0, Xval=None, CLev=None):
    """``LinRegtIntervals X,Y[,F[,0[,CLev]]]`` and ``...,1,Xval[,CLev]]``.

    ``kind=0`` (the default, "For Slope") gives ``stat.CLower``/``stat.CUpper``
    for the slope plus ``stat.SESlope``, ``stat.ME``, ``stat.s`` and ``stat.df``.
    ``kind=1`` ("For Response") gives the predicted ``stat.y`` with
    ``stat.SE``/``stat.ME`` for the mean response and ``stat.SEPred``/
    ``stat.MEPred`` with ``stat.LowerPred``/``stat.UpperPred`` for one future
    observation.

    The guide publishes this through two tables that run together: the common
    head (``stat.RegEqn`` … ``stat.Resid``) followed by the tail for the
    selected ``kind``.  So ``stat.Resid`` lands in the *middle* of the run, not
    at the end, and the two kinds differ in more than their interval names --
    ``kind=0`` ends with ``stat.SESlope``/``stat.s``, while ``kind=1`` has
    neither and ends with ``stat.y``.  There are no ``*Reg`` echo lists here at
    all; that is the same omission the guide makes for the multiple models.
    """
    from .distributions import invt

    px, py, w = _filter(X, Y, F)
    n, mx, my = _common(px, py, w)
    sxx = _sum(wi * (a - mx) ** 2 for a, wi in _zip(px, w))
    if sxx == 0:
        raise DomainError()
    sxy = _sum(wi * (a - mx) * (b - my) for a, b, wi in _zip(px, py, w))
    b = sxy / sxx
    a = my - b * mx
    resid = [yy - (a + b * xx) for xx, yy in _zip(px, py)]
    df = n - 2
    if df <= 0:
        raise DomainError()
    s = sqrt(_sum(wi * e * e for e, wi in _zip(resid, w)) / df)
    se_slope = s / sqrt(sxx)
    syy = _sum(wi * (bb - my) ** 2 for bb, wi in _zip(py, w))
    denom = sqrt(sxx * syy)
    r = sxy / denom if denom else 0.0
    clev = 0.95 if CLev is None else CLev
    tcrit = invt(1 - (1 - clev) / 2, df)
    d = {
        "RegEqn": RegEqn("LinRegBx", {"a": a, "b": b}, "y = a+b·x"),
        "a": a,
        "b": b,
        "df": df,
        "r²": r * r,
        "r": r,
        "Resid": _list(resid),
    }
    if _int(kind) == 0:
        d.update({
            "CLower": b - tcrit * se_slope,
            "CUpper": b + tcrit * se_slope,
            "ME": tcrit * se_slope,
            "SESlope": se_slope,
            "s": s,
        })
    else:
        if Xval is None:
            raise ArgumentError("response intervals need Xval")
        xv = _float(Xval)
        yhat = a + b * xv
        se = s * sqrt(1.0 / n + (xv - mx) ** 2 / sxx)
        sepred = s * sqrt(1.0 + 1.0 / n + (xv - mx) ** 2 / sxx)
        d.update({
            "CLower": yhat - tcrit * se,
            "CUpper": yhat + tcrit * se,
            "ME": tcrit * se,
            "SE": se,
            "LowerPred": yhat - tcrit * sepred,
            "UpperPred": yhat + tcrit * sepred,
            "MEPred": tcrit * sepred,
            "SEPred": sepred,
            "y": yhat,
        })
    return publish(d)


def LinRegtTest(X, Y, Freq=None, Hypoth=0):
    """``LinRegtTest X,Y[,Freq[,Hypoth]]`` -- t test on the slope β (and ρ).

    ``Hypoth=0`` tests β≠0 (two-tailed, the default), ``Hypoth<0`` tests β<0 and
    ``Hypoth>0`` tests β>0.  Publishes ``stat.t``, ``stat.PVal``, ``stat.df``,
    ``stat.a``, ``stat.b``, ``stat.s``, ``stat.SESlope``, ``stat.r2``,
    ``stat.r`` and ``stat.Resid``.
    """
    from .distributions import tCdf

    px, py, w = _filter(X, Y, Freq)
    n, mx, my = _common(px, py, w)
    sxx = _sum(wi * (a - mx) ** 2 for a, wi in _zip(px, w))
    sxy = _sum(wi * (a - mx) * (b - my) for a, b, wi in _zip(px, py, w))
    if sxx == 0:
        raise DomainError()
    b = sxy / sxx
    a = my - b * mx
    resid = [yy - (a + b * xx) for xx, yy in _zip(px, py)]
    df = n - 2
    s = sqrt(_sum(wi * e * e for e, wi in _zip(resid, w)) / df)
    se_slope = s / sqrt(sxx)
    t = b / se_slope if se_slope else float("nan")
    h = _int(Hypoth)
    if h == 0:
        # 2·P(T ≤ -|t|); see the note in MultRegTests above
        pval = 2 * tCdf(-9e999, -_abs(t), df)
    elif h < 0:
        pval = tCdf(-9e999, t, df)
    else:
        pval = 1 - tCdf(-9e999, t, df)
    syy = _sum(wi * (bb - my) ** 2 for bb, wi in _zip(py, w))
    denom = sqrt(sxx * syy)
    r = sxy / denom if denom else 0.0
    d = {
        "RegEqn": RegEqn("LinRegBx", {"a": a, "b": b}, "y = a+b·x"),
        "t": t,
        "PVal": pval,
        "df": df,
        "a": a,
        "b": b,
        "s": s,
        "SESlope": se_slope,
        # lower case here, unlike QuadReg's stat.R² -- the guide's LinRegtTest
        # table prints stat.r², the twin of the stat.r right below it.
        "r²": r * r,
        "r": r,
    }
    # No stat.XReg/stat.YReg/stat.FreqReg echo lists: the guide's LinRegtTest
    # table stops at stat.Resid, so the echo tail is suppressed.
    return publish(_finish(d, resid, None, py, None))
