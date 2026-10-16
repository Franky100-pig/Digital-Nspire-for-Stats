"""Distributions -- ``menu > Statistics > Distributions``.

``normPdf``/``normCdf``/``invNorm``, ``tPdf``/``tCdf``/``invt``,
``χ2Pdf``/``χ2Cdf``/``invχ2``, ``FPdf``/``FCdf``/``invF``, the discrete
``binom*``/``poiss*``/``geom*`` families, ``invBinom``/``invBinomN`` and the
random-number commands that share the same menu.

Everything is implemented on the standard library alone -- the regularised
incomplete beta and incomplete gamma functions are the classic continued-fraction
forms, so the package has no numpy/scipy dependency.  ``tools/checks_vs_scipy``
verifies the numbers against scipy.

Notes on names the guide prints two ways:
``χ2Pdf``/``chi2Pdf``, ``χ2Cdf``/``chi2Cdf`` and ``invχ2``/``invChi2`` are all
defined, plus ``invT`` as an alias of the guide's lowercase ``invt``.
"""

from __future__ import annotations

import random as _random
from math import (
    erf,
    exp,
    inf,
    lgamma,
    log,
    pi,
    sqrt,
)

from ._core import (
    _abs,
    _float,
    _int,
    _isinstance,
    _len,
    _list,
    _range,
    _sum,
    _zip,
    DomainError,
)

INF = 9e999  # what the calculator's -9E999 actually is: negative infinity


# ==========================================================================
# special functions
# ==========================================================================
def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta (Lentz's method)."""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if _abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in _range(1, 500):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if _abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if _abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if _abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if _abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if _abs(delta - 1.0) < 3e-16:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    """Regularised incomplete beta ``I_x(a,b)``."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    front = exp(lgamma(a + b) - lgamma(a) - lgamma(b)
                + a * log(x) + b * log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def gammainc(a: float, x: float) -> float:
    """Regularised lower incomplete gamma ``P(a,x)``."""
    if x < 0 or a <= 0:
        raise DomainError()
    if x == 0:
        return 0.0
    if x < a + 1.0:
        ap = a
        total = 1.0 / a
        delta = total
        for _ in _range(500):
            ap += 1
            delta *= x / ap
            total += delta
            if _abs(delta) < _abs(total) * 3e-16:
                break
        return total * exp(-x + a * log(x) - lgamma(a))
    return 1.0 - gammainc_upper_cf(a, x)


def gammainc_upper_cf(a: float, x: float) -> float:
    """Continued fraction for ``Q(a,x) = 1 - P(a,x)``."""
    tiny = 1e-300
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b if _abs(b) > tiny else 1.0 / tiny
    h = d
    for i in _range(1, 500):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if _abs(d) < tiny:
            d = tiny
        c = b + an / c
        if _abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if _abs(delta - 1.0) < 3e-16:
            break
    return exp(-x + a * log(x) - lgamma(a)) * h


def _acklam_invnorm(p: float) -> float:
    """Inverse standard normal, Peter Acklam's rational approximation.

    Acklam's piecewise form is defined for ``p`` in ``(0, 1)`` -- the low branch
    evaluates ``log(p)`` and the high branch ``log(1 - p)``, so neither branch
    survives being handed a negative argument.  ``_erfinv`` maps into this
    domain before calling.
    """
    if p <= 0.0:
        return -inf
    if p >= 1.0:
        return inf
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = sqrt(-2 * log(p))
        x = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    elif p <= phigh:
        q = p - 0.5
        r = q * q
        x = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
            (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
    else:
        q = sqrt(-2 * log(1 - p))
        x = -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    # one Newton step quadruples the accuracy, at 1 erf() per call
    err = erf(x / sqrt(2)) - (2 * p - 1)
    return x - err * sqrt(2 * pi) * exp(x * x / 2) / 2


def _erfinv(y: float) -> float:
    """Inverse error function for ``y`` in ``[-1, 1]``.

    Acklam's coefficients describe the *normal* quantile function, so the
    two-sided argument of ``erf`` is moved into ``(0, 1)`` first::

        erfinv(y) = invnorm((1 + y) / 2) / sqrt(2)

    Feeding ``2a - 1`` straight into the rational approximation -- the obvious
    reading of Acklam's paper -- breaks for every ``y < 0``, because the low
    branch takes ``log`` of a negative number.
    """
    if y <= -1.0:
        return -inf
    if y >= 1.0:
        return inf
    return _acklam_invnorm((1.0 + y) / 2.0) / sqrt(2)


def _bisect_inverse(cdf, target, lo, hi, iters=200):
    if target <= 0:
        return lo
    if target >= 1:
        return hi
    for _ in _range(iters):
        mid = (lo + hi) / 2
        if cdf(mid) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ==========================================================================
# Normal
# ==========================================================================
def normPdf(XVal, μ=0, σ=1):
    """``normPdf(XVal[,μ[,σ]])`` -- normal density (μ=0, σ=1 by default)."""
    if σ <= 0:
        raise DomainError()
    if _isinstance(XVal, (list, tuple)):
        return [normPdf(v, μ, σ) for v in XVal]
    z = (_float(XVal) - μ) / σ
    return exp(-z * z / 2) / (σ * sqrt(2 * pi))


def normCdf(lowBound, upBound, μ=0, σ=1):
    """``normCdf(lowBound,upBound[,μ[,σ]])`` -- P(lowBound ≤ X ≤ upBound).

    ``lowBound = -9E999`` is the calculator's idiom for −∞; Python's ``-inf``
    works too.
    """
    if σ <= 0:
        raise DomainError()
    lo, hi = _as_float(lowBound), _as_float(upBound)
    if _isinstance(lowBound, (list, tuple)) or _isinstance(upBound, (list, tuple)):
        pairs = _zip(*[_as_seq(lowBound), _as_seq(upBound)])
        return [normCdf(a, b, μ, σ) for a, b in pairs]
    if lo > hi:
        lo, hi = hi, lo
    return _phi((hi - μ) / σ) - _phi((lo - μ) / σ)


def _phi(z):
    if z == inf:
        return 1.0
    if z == -inf:
        return 0.0
    return 0.5 * (1 + erf(z / sqrt(2)))


def invNorm(Area, μ=0, σ=1):
    """``invNorm(Area[,μ[,σ]])`` -- the inverse cumulative normal."""
    if σ <= 0:
        raise DomainError()
    a = _float(Area)
    if a <= 0 or a >= 1:
        raise DomainError("Area must be strictly between 0 and 1")
    return μ + σ * _acklam_invnorm(a)


# ==========================================================================
# Student t
# ==========================================================================
def tPdf(XVal, df):
    """``tPdf(XVal,df)`` -- Student-t density."""
    if df <= 0:
        raise DomainError()
    if _isinstance(XVal, (list, tuple)):
        return [tPdf(v, df) for v in XVal]
    x = _float(XVal)
    return exp(lgamma((df + 1) / 2) - lgamma(df / 2)) / sqrt(df * pi) * (
        1 + x * x / df
    ) ** (-(df + 1) / 2)


def _t_cdf(t, df):
    if t == 0:
        return 0.5
    x = df / (df + t * t)
    tail = 0.5 * betainc(df / 2, 0.5, x)
    return 1 - tail if t > 0 else tail


def tCdf(lowBound, upBound, df):
    """``tCdf(lowBound,upBound,df)`` -- P(lowBound ≤ T ≤ upBound)."""
    if df <= 0:
        raise DomainError()
    if _isinstance(lowBound, (list, tuple)) or _isinstance(upBound, (list, tuple)):
        return [
            tCdf(a, b, df) for a, b in _zip(*[_as_seq(lowBound), _as_seq(upBound)])
        ]
    lo, hi = _as_float(lowBound), _as_float(upBound)
    if lo > hi:
        lo, hi = hi, lo
    return _t_cdf(hi, df) - _t_cdf(lo, df)


def invt(Area, df):
    """``invt(Area,df)`` -- inverse cumulative Student-t.

    The guide spells it lowercase; ``invT`` is provided as an alias because most
    people type it capitalised.
    """
    if df <= 0:
        raise DomainError()
    a = _float(Area)
    if a <= 0 or a >= 1:
        raise DomainError("Area must be strictly between 0 and 1")
    # 200 bisections give far more precision than the 10 digits TI displays
    return _bisect_inverse(lambda t: _t_cdf(t, df), a, -1e8, 1e8)


# ==========================================================================
# Chi-square
# ==========================================================================
def χ2Pdf(XVal, df):
    """``χ2Pdf(XVal,df)`` (a.k.a. ``chi2Pdf``) -- chi-square density."""
    if df <= 0:
        raise DomainError()
    if _isinstance(XVal, (list, tuple)):
        return [χ2Pdf(v, df) for v in XVal]
    x = _float(XVal)
    if x < 0:
        return 0.0
    if x == 0:
        # x^(df/2-1) limits: +inf for df<2, 1 for df=2, 0 for df>2,
        # times the normalising constant 1/(2^(df/2)·Γ(df/2))
        if df < 2:
            return inf
        if df == 2:
            return 0.5
        return 0.0
    return exp((df / 2 - 1) * log(x) - x / 2 - lgamma(df / 2) - (df / 2) * log(2))


def χ2Cdf(lowBound, upBound, df):
    """``χ2Cdf(lowBound,upBound,df)`` -- P(lowBound ≤ X² ≤ upBound)."""
    if df <= 0:
        raise DomainError()
    if _isinstance(lowBound, (list, tuple)) or _isinstance(upBound, (list, tuple)):
        return [
            χ2Cdf(a, b, df) for a, b in _zip(*[_as_seq(lowBound), _as_seq(upBound)])
        ]
    lo, hi = _as_float(lowBound), _as_float(upBound)
    if lo > hi:
        lo, hi = hi, lo
    lo = 0.0 if lo < 0 else lo
    hi = 0.0 if hi < 0 else hi
    return gammainc(df / 2, hi / 2) - gammainc(df / 2, lo / 2)


def invχ2(Area, df):
    """``invχ2(Area,df)`` (a.k.a. ``invChi2``) -- inverse cumulative chi-square."""
    if df <= 0:
        raise DomainError()
    a = _float(Area)
    if a <= 0 or a >= 1:
        raise DomainError("Area must be strictly between 0 and 1")
    return _bisect_inverse(lambda x: gammainc(df / 2, x / 2), a, 0.0, 1e12)


# ==========================================================================
# F
# ==========================================================================
def FPdf(XVal, dfNumer, dfDenom):
    """``FPdf(XVal,dfNumer,dfDenom)`` -- F density.

    The guide prints it ``FPdf`` (capital F); ``Fpdf`` is accepted as well.
    """
    if dfNumer <= 0 or dfDenom <= 0:
        raise DomainError()
    if _isinstance(XVal, (list, tuple)):
        return [FPdf(v, dfNumer, dfDenom) for v in XVal]
    x = _float(XVal)
    if x < 0:
        return 0.0
    if x == 0:
        return 0.0 if dfNumer > 2 else (1.0 if dfNumer == 2 else inf)
    d1, d2 = dfNumer, dfDenom
    return exp(
        (d1 / 2) * log(d1) + (d2 / 2) * log(d2)
        + (d1 / 2 - 1) * log(x)
        - ((d1 + d2) / 2) * log(d2 + d1 * x)
        - lgamma(d1 / 2) - lgamma(d2 / 2) + lgamma((d1 + d2) / 2)
    )


def _f_cdf(x, d1, d2):
    if x <= 0:
        return 0.0
    return betainc(d1 / 2, d2 / 2, d1 * x / (d1 * x + d2))


def FCdf(lowBound, upBound, dfNumer, dfDenom):
    """``FCdf(lowBound,upBound,dfNumer,dfDenom)`` -- P(lowBound ≤ F ≤ upBound)."""
    if dfNumer <= 0 or dfDenom <= 0:
        raise DomainError()
    if _isinstance(lowBound, (list, tuple)) or _isinstance(upBound, (list, tuple)):
        return [
            FCdf(a, b, dfNumer, dfDenom)
            for a, b in _zip(*[_as_seq(lowBound), _as_seq(upBound)])
        ]
    lo, hi = _as_float(lowBound), _as_float(upBound)
    if lo > hi:
        lo, hi = hi, lo
    return _f_cdf(hi, dfNumer, dfDenom) - _f_cdf(max(lo, 0.0), dfNumer, dfDenom)


def invF(Area, dfNumer, dfDenom):
    """``invF(Area,dfNumer,dfDenom)`` -- inverse cumulative F."""
    if dfNumer <= 0 or dfDenom <= 0:
        raise DomainError()
    a = _float(Area)
    if a <= 0 or a >= 1:
        raise DomainError("Area must be strictly between 0 and 1")
    return _bisect_inverse(lambda x: _f_cdf(x, dfNumer, dfDenom), a, 0.0, 1e12)


# ==========================================================================
# Binomial
# ==========================================================================
def _binomial_pmf(n, p, k):
    if k < 0 or k > n:
        return 0.0
    if p == 0:
        return 1.0 if k == 0 else 0.0
    if p == 1:
        return 1.0 if k == n else 0.0
    return exp(
        lgamma(n + 1) - lgamma(k + 1) - lgamma(n - k + 1)
        + k * log(p) + (n - k) * log(1 - p)
    )


def binomPdf(n, p, XVal=None):
    """``binomPdf(n,p)`` -- every probability; ``binomPdf(n,p,XVal)`` -- one."""
    n = _int(n)
    if n < 0 or not 0 <= p <= 1:
        raise DomainError()
    if XVal is None:
        return [_binomial_pmf(n, p, k) for k in _range(n + 1)]
    if _isinstance(XVal, (list, tuple)):
        return [binomPdf(n, p, k) for k in XVal]
    return _binomial_pmf(n, p, _int(XVal))


def binomCdf(n, p, lowBound, upBound=None):
    """``binomCdf(n,p,upBound)`` -- P(0 ≤ X ≤ upBound); with four arguments,
    ``binomCdf(n,p,lowBound,upBound)`` -- P(lowBound ≤ X ≤ upBound)."""
    n = _int(n)
    if n < 0 or not 0 <= p <= 1:
        raise DomainError()
    if upBound is None:
        lo, hi = 0, _int(lowBound)
    else:
        lo, hi = _int(lowBound), _int(upBound)
    if lo > hi:
        lo, hi = hi, lo
    lo, hi = max(lo, 0), min(hi, n)
    if lo > hi:
        return 0.0
    # exact via the incomplete beta, which is stable for large n
    if lo == 0:
        return betainc(n - hi, hi + 1, 1 - p) if hi < n else 1.0
    if lo == hi:
        return _binomial_pmf(n, p, lo)
    return betainc(n - hi, hi + 1, 1 - p) - betainc(n - lo + 1, lo, 1 - p)


def invBinom(CumulativeProb, NumTrials, Prob, OutputForm=0):
    """``invBinom(CumulativeProb,NumTrials,Prob,OutputForm)``.

    The minimum number of successes ``k`` with ``P(X ≤ k) ≥ CumulativeProb``.
    ``OutputForm=0`` gives a scalar (the default); ``OutputForm=1`` a 1×1 matrix.
    """
    target = _float(CumulativeProb)
    n, p = _int(NumTrials), _float(Prob)
    if not 0 <= target <= 1:
        raise DomainError()
    k = 0
    while k < n and binomCdf(n, p, k) < target:
        k += 1
    return [[k]] if _int(OutputForm) == 1 else k


def invBinomN(CumulativeProb, Prob, NumSuccess, OutputForm=0):
    """``invBinomN(CumulativeProb,Prob,NumSuccess,OutputForm)``.

    The minimum number of trials ``N`` such that the chance of reaching at least
    ``NumSuccess`` successes is ≥ ``CumulativeProb`` -- the ballgame question
    from the guide: 70% shooting, 50 goals, how many attempts to be 0.99 sure?
    """
    target = _float(CumulativeProb)
    p, k = _float(Prob), _int(NumSuccess)
    if not 0 <= target <= 1 or not 0 <= p <= 1:
        raise DomainError()
    n = k
    while n < 10_000_000:
        if 1.0 - binomCdf(n, p, k - 1) >= target:
            break
        n += 1
    return [[n]] if _int(OutputForm) == 1 else n


# ==========================================================================
# Poisson and geometric
# ==========================================================================
def poissPdf(λ, XVal):
    """``poissPdf(λ,XVal)`` -- Poisson probability mass."""
    if λ < 0:
        raise DomainError()
    if _isinstance(XVal, (list, tuple)):
        return [poissPdf(λ, k) for k in XVal]
    k = _int(XVal)
    if k < 0:
        return 0.0
    return exp(-λ + k * log(λ) - lgamma(k + 1)) if λ > 0 else (1.0 if k == 0 else 0.0)


def poissCdf(λ, lowBound, upBound=None):
    """``poissCdf(λ,upBound)`` -- P(0 ≤ X ≤ upBound); four-way form gives a range."""
    if λ < 0:
        raise DomainError()
    if upBound is None:
        lo, hi = 0, _int(lowBound)
    else:
        lo, hi = _int(lowBound), _int(upBound)
    if lo > hi:
        lo, hi = hi, lo

    # P(X <= k) = Q(k+1, λ) = 1 - P(k+1, λ)  (regularised incomplete gamma)
    def cdf(k):
        if k < 0:
            return 0.0
        return 1.0 - gammainc(k + 1, λ)

    return cdf(hi) - cdf(lo - 1)


def geomPdf(p, XVal):
    """``geomPdf(p,XVal)`` -- probability the first success lands on trial XVal."""
    if not 0 < p <= 1:
        raise DomainError()
    if _isinstance(XVal, (list, tuple)):
        return [geomPdf(p, k) for k in XVal]
    k = _int(XVal)
    if k < 1:
        return 0.0
    return (1 - p) ** (k - 1) * p


def geomCdf(p, lowBound, upBound=None):
    """``geomCdf(p,upBound)`` -- P(1 ≤ X ≤ upBound); four-way form gives a range."""
    if not 0 < p <= 1:
        raise DomainError()
    if upBound is None:
        lo, hi = 1, _int(lowBound)
    else:
        lo, hi = _int(lowBound), _int(upBound)
    if lo > hi:
        lo, hi = hi, lo

    def cdf(k):
        if k < 1:
            return 0.0
        return 1.0 - (1 - p) ** k

    return cdf(hi) - cdf(lo - 1)


# ==========================================================================
# random numbers (same menu as the distributions)
# ==========================================================================
_rng = _random.Random()


def RandSeed(Number):
    """``RandSeed Number`` -- 0 restores the factory seeds, otherwise reseed."""
    n = _int(Number)
    if n == 0:
        _rng.seed(None)
    else:
        _rng.seed(n & 0xFFFFFFFF)
    return None


def rand(*args):
    """``rand()`` -- one value in [0,1); ``rand(#Trials)`` -- a list."""
    if args and args[0]:
        return [_rng.random() for _ in _range(_int(args[0]))]
    return _rng.random()


def randInt(lowBound, upBound, *args):
    """``randInt(lowBound,upBound[,#Trials])``."""
    lo, hi = _int(lowBound), _int(upBound)
    if lo > hi:
        lo, hi = hi, lo
    if args and args[0]:
        return [_rng.randint(lo, hi) for _ in _range(_int(args[0]))]
    return _rng.randint(lo, hi)


def randNorm(μ, σ, *args):
    """``randNorm(μ,σ[,#Trials])`` -- normally distributed draws."""
    if args and args[0]:
        return [_rng.gauss(μ, σ) for _ in _range(_int(args[0]))]
    return _rng.gauss(μ, σ)


def randBin(n, p, *args):
    """``randBin(n,p[,#Trials])`` -- draws from Binomial(n, p)."""
    nn = _int(n)
    if not 0 <= p <= 1:
        raise DomainError()

    def one():
        return _sum(1 for _ in _range(nn) if _rng.random() < p)

    if args and args[0]:
        return [one() for _ in _range(_int(args[0]))]
    return one()


def randSamp(List, num, noRepl=0):
    """``randSamp(List,#Trials[,noRepl])`` -- sample with (0) or without (1) replacement."""
    pool = _list(List)
    k = _int(num)
    if k < 0:
        raise DomainError()
    if _int(noRepl):
        if k > _len(pool):
            raise DomainError("cannot sample more than the list holds")
        return _rng.sample(pool, k)
    return [_rng.choice(pool) for _ in _range(k)]


# ==========================================================================
# small argument helpers
# ==========================================================================
def _as_float(v):
    """Fold the calculator's ±9E999 idiom onto Python's ±inf."""
    f = _float(v)
    if f != f:  # nan passes straight through
        return f
    if f == inf or f == -inf:
        return f
    return f


def _as_seq(v):
    return _list(v) if _isinstance(v, (list, tuple)) else [v]


