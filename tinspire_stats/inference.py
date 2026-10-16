"""Inference -- ``menu > Statistics > Confidence Intervals`` and ``Stat Tests``.

Every function here mirrors the two input forms the handheld offers:

* **Data** -- you hand it the raw list(s) plus an optional frequency list;
* **Stats** -- you hand it the summary statistics (mean, s, n) directly.

The two are told apart the way the calculator's wizard does it: by whether the
list-shaped argument is a list.  ``tInterval([1,2,3], None, 0.9)`` is Data;
``tInterval(2.0, 1.0, 3, 0.9)`` is Stats.

Name fidelity
-------------
Output names come from each function's own table in the TI-Nspire Reference
Guide.  Where two editions of the guide disagree the module publishes **both**
spellings and records the pair in ``NAME_SUPERSETS`` below, so
``stat.σx`` *and* ``stat.sx`` both answer after ``tInterval`` no matter which
edition you are reading.  See ``README.md`` for the full fidelity table.

    >>> from tinspire_stats import zInterval, stat
    >>> zInterval(2, [3, 4, 5, 6, 7], None, 0.95)
    StatGroup(CLower, CUpper, x, ME, sx, n, σ, σx)
    >>> round(stat.CLower, 4), round(stat.CUpper, 4)
    (3.247, 6.753)
"""

from __future__ import annotations

from math import sqrt

from ._core import (
    _float,
    _int,
    _isinstance,
    _len,
    _list,
    _max,
    _min,
    _range,
    _sum,
    _zip,
    ArgumentError,
    DimensionMismatchError,
    DomainError,
    check_integer_freq,
    is_void,
    pair_up,
    weighted_mean,
    weighted_ss,
)
from .distributions import (
    FCdf,
    invNorm,
    invt,
    normCdf,
    tCdf,
    χ2Cdf,
)
from .statvar import publish

# --------------------------------------------------------------------------
# Name supersets: the reference guide prints these names two ways.
# --------------------------------------------------------------------------
#: ``{canonical emitted name: [alternate spelling also emitted]}``.
#: Driven by: (a) the *printed* Reference Guide being older than the online one,
#: and (b) the online guide's tInterval table saying ``σx`` where its own
#: description says "sample standard deviation".
NAME_SUPERSETS = {
    "sx": ["σx"],
    "sx1": ["σx1"],
    "sx2": ["σx2"],
    "v": ["x"],
    "v1": ["x1"],
    "v2": ["x2"],
}


def _supersede(d: dict) -> dict:
    """Add the alternate spellings listed in ``NAME_SUPERSETS``."""
    extra = {}
    for key, alts in NAME_SUPERSETS.items():
        if key in d:
            for alt in alts:
                extra.setdefault(alt, d[key])
    # the alternate of v1-v2 rides along with v1/v2
    if "v1" in d and "v2" in d:
        extra.setdefault("x1-x2", d["v1"] - d["v2"])
    d.update(extra)
    return d


# --------------------------------------------------------------------------
# shared plumbing
# --------------------------------------------------------------------------
def _number(x) -> float:
    if _isinstance(x, (list, tuple)):
        raise ArgumentError("expected a number")
    return _float(x)


def _stat_int(x):
    """TI prints whole sample sizes as integers, not 3.0."""
    f = _float(x)
    return _int(f) if f == _int(f) else f


def _is_seq(x) -> bool:
    return _isinstance(x, (list, tuple, range))


def _sample(data, freq=None):
    """Summary statistics of a raw data list, honouring a frequency list.

    Frequencies must be non-negative integers -- the same restriction the
    calculator puts on every ``Freq`` argument in the statistics wizards.
    """
    vals, w = pair_up(data, freq, integer_freq=True, expand=False)
    n = _sum(w)
    if n < 2:
        raise DomainError("need at least two observations")
    m = weighted_mean(vals, w)
    ss = weighted_ss(vals, w, m)
    return {"n": n, "mean": m, "ss": ss, "s": sqrt(ss / (n - 1))}


def _hypoth_sign(h) -> int:
    v = _number(h)
    if v > 0:
        return 1
    if v < 0:
        return -1
    return 0


def _tail_p(left_cdf, stat, hypoth, *, two_sided_via_abs=True):
    """P-value from a symmetric sampling distribution.

    ``left_cdf(t)`` must return ``P(T ≤ t)``.  ``Hypoth`` is TI's switch:
    ``<0`` → lower tail, ``0`` → two tails, ``>0`` → upper tail.
    """
    h = _hypoth_sign(hypoth)
    if h < 0:
        p = left_cdf(stat)
    elif h > 0:
        p = 1.0 - left_cdf(stat)
    else:
        a = abs(stat) if two_sided_via_abs else stat
        p = 2.0 * left_cdf(-a)
    return 0.0 if p < 0 else (1.0 if p > 1 else p)


def _z_left(z):
    return normCdf(-9e999, z)


def _t_left(t, df):
    return tCdf(-9e999, t, df)


def _crit_z(clev):
    return invNorm(1 - (1 - _float(clev)) / 2)


def _crit_t(clev, df):
    return invt(1 - (1 - _float(clev)) / 2, df)


# ==========================================================================
# z intervals
# ==========================================================================
def zInterval(σ, *args, **kwargs):
    """``zInterval σ,List[,Freq[,CLevel]]`` / ``zInterval σ,v,n[,CLevel]``.

    Publishes ``stat.CLower``/``stat.CUpper``, ``stat.x``, ``stat.ME``,
    ``stat.sx``, ``stat.n`` and ``stat.σ``.  Note that the z procedures park the
    sample mean in ``stat.x`` while the t procedures use ``stat.v`` -- that is
    the guide's doing, not a slip.
    """
    clev = _float(kwargs.pop("CLevel", 0.95))
    sigma = _number(σ)
    if not args:
        raise ArgumentError("zInterval needs a list or summary statistics")
    first = args[0]
    if _is_seq(first):
        freq = args[1] if _len(args) > 1 else kwargs.pop("Freq", None)
        if _len(args) > 2:
            clev = _float(args[2])
        st = _sample(first, freq)
        mean, n, sx = st["mean"], st["n"], st["s"]
    else:
        mean = _number(first)
        n = _number(args[1]) if _len(args) > 1 else kwargs.pop("n")
        sx = _number(args[2]) if _len(args) > 2 else kwargs.pop("sx", float("nan"))
        if _len(args) > 3:
            clev = _float(args[3])
    me = _crit_z(clev) * sigma / sqrt(n)
    return publish(
        _supersede({
            "CLower": mean - me,
            "CUpper": mean + me,
            "x": mean,
            "ME": me,
            "sx": sx,
            "n": _stat_int(n),
            "σ": sigma,
        })
    )


def zInterval_2Samp(σ1, σ2, *args, **kwargs):
    """``zInterval_2Samp σ1,σ2,List1,List2[,Freq1[,Freq2[,CLevel]]]``.

    Stats form: ``zInterval_2Samp σ1,σ2,v1,n1,v2,n2[,CLevel]``.
    """
    clev = _float(kwargs.pop("CLevel", 0.95))
    s1, s2 = _number(σ1), _number(σ2)
    if not args:
        raise ArgumentError("zInterval_2Samp needs data or summary statistics")
    if _is_seq(args[0]):
        l1, l2 = args[0], args[1]
        f1 = args[2] if _len(args) > 2 else kwargs.pop("Freq1", None)
        f2 = args[3] if _len(args) > 3 else kwargs.pop("Freq2", None)
        if _len(args) > 4:
            clev = _float(args[4])
        a = _sample(l1, f1)
        b = _sample(l2, f2)
        v1, v2, n1, n2 = a["mean"], b["mean"], a["n"], b["n"]
    else:
        v1, v2 = _number(args[0]), _number(args[2])
        n1, n2 = _number(args[1]), _number(args[3])
        if _len(args) > 4:
            clev = _float(args[4])
    se = sqrt(s1 * s1 / n1 + s2 * s2 / n2)
    diff = v1 - v2
    me = _crit_z(clev) * se
    return publish(
        _supersede({
            "CLower": diff - me,
            "CUpper": diff + me,
            "x1-x2": diff,
            "ME": me,
            "x1": v1,
            "x2": v2,
            "σx1": s1,
            "σx2": s2,
            "n1": _stat_int(n1),
            "n2": _stat_int(n2),
            "r1": s1,
            "r2": s2,
        })
    )


def zInterval_1Prop(x, n, CLevel=0.95):
    """``zInterval_1Prop x,n[,CLevel]`` -- one-proportion z interval.

    ``x`` is the number of successes, ``n`` the number of trials.  The interval
    is the ordinary Wald interval, as on TI's calculators.
    """
    k, N = _number(x), _number(n)
    if k < 0 or N <= 0 or k > N:
        raise DomainError("need 0 ≤ x ≤ n and n > 0")
    p = k / N
    me = _crit_z(CLevel) * sqrt(p * (1 - p) / N)
    return publish({
        "CLower": p - me,
        "CUpper": p + me,
        "Ç": p,
        "ME": me,
        "n": _stat_int(N),
    })


def zInterval_2Prop(x1, n1, x2, n2, CLevel=0.95):
    """``zInterval_2Prop x1,n1,x2,n2[,CLevel]`` -- two-proportion z interval."""
    k1, N1, k2, N2 = (_number(v) for v in (x1, n1, x2, n2))
    if not (0 <= k1 <= N1 and 0 <= k2 <= N2 and N1 > 0 and N2 > 0):
        raise DomainError("need 0 ≤ x ≤ n and n > 0 for both samples")
    p1, p2 = k1 / N1, k2 / N2
    me = _crit_z(CLevel) * sqrt(p1 * (1 - p1) / N1 + p2 * (1 - p2) / N2)
    return publish({
        "CLower": (p1 - p2) - me,
        "CUpper": (p1 - p2) + me,
        "ÇDiff": p1 - p2,
        "ME": me,
        "Ç1": p1,
        "Ç2": p2,
        "n1": _stat_int(N1),
        "n2": _stat_int(N2),
    })


# ==========================================================================
# t intervals
# ==========================================================================
def tInterval(*args, **kwargs):
    """``tInterval List[,Freq[,CLevel]]`` / ``tInterval v,sx,n[,CLevel]``.

    Publishes ``stat.CLower``/``stat.CUpper``, ``stat.v``, ``stat.ME``,
    ``stat.df``, ``stat.sx``, ``stat.n``.  ``stat.σx`` answers as well -- the
    online guide's tInterval table prints it.
    """
    clev = _float(kwargs.pop("CLevel", 0.95))
    if not args:
        raise ArgumentError("tInterval needs a list or summary statistics")
    if _is_seq(args[0]):
        freq = args[1] if _len(args) > 1 else kwargs.pop("Freq", None)
        if _len(args) > 2:
            clev = _float(args[2])
        st = _sample(args[0], freq)
        mean, sx, n = st["mean"], st["s"], st["n"]
    else:
        mean = _number(args[0])
        sx = _number(args[1]) if _len(args) > 1 else kwargs.pop("sx")
        n = _number(args[2]) if _len(args) > 2 else kwargs.pop("n")
        if _len(args) > 3:
            clev = _float(args[3])
    df = n - 1
    if df <= 0:
        raise DomainError("need at least two observations")
    me = _crit_t(clev, df) * sx / sqrt(n)
    return publish(
        _supersede({
            "CLower": mean - me,
            "CUpper": mean + me,
            "v": mean,
            "ME": me,
            "df": _stat_int(df),
            "sx": sx,
            "n": _stat_int(n),
        })
    )


def tInterval_2Samp(*args, **kwargs):
    """``tInterval_2Samp List1,List2[,Freq1[,Freq2[,CLevel[,Pooled]]]]``.

    Stats form: ``tInterval_2Samp v1,sx1,n1,v2,sx2,n2[,CLevel[,Pooled]]``.
    ``Pooled=1`` pools the variances, ``Pooled=0`` (default) is Welch.
    ``stat.sp`` is published only when pooled, exactly as the guide says.
    """
    clev = _float(kwargs.pop("CLevel", 0.95))
    pooled = kwargs.pop("Pooled", None)
    if not args:
        raise ArgumentError("tInterval_2Samp needs data or summary statistics")
    if _is_seq(args[0]):
        l1, l2 = args[0], args[1]
        f1 = args[2] if _len(args) > 2 else kwargs.pop("Freq1", None)
        f2 = args[3] if _len(args) > 3 else kwargs.pop("Freq2", None)
        if _len(args) > 4:
            clev = _float(args[4])
        if _len(args) > 5:
            pooled = _number(args[5])
        a = _sample(l1, f1)
        b = _sample(l2, f2)
        v1, sx1, n1 = a["mean"], a["s"], a["n"]
        v2, sx2, n2 = b["mean"], b["s"], b["n"]
    else:
        v1, sx1, n1 = _number(args[0]), _number(args[1]), _number(args[2])
        v2, sx2, n2 = _number(args[3]), _number(args[4]), _number(args[5])
        if _len(args) > 6:
            clev = _float(args[6])
        if _len(args) > 7:
            pooled = _number(args[7])
    is_pooled = bool(_int(pooled)) if pooled is not None else False
    if is_pooled:
        df = n1 + n2 - 2
        sp = sqrt(((n1 - 1) * sx1 ** 2 + (n2 - 1) * sx2 ** 2) / df)
        se = sp * sqrt(1 / n1 + 1 / n2)
    else:
        a1, a2 = sx1 * sx1 / n1, sx2 * sx2 / n2
        se = sqrt(a1 + a2)
        df = (a1 + a2) ** 2 / (a1 * a1 / (n1 - 1) + a2 * a2 / (n2 - 1))
    diff = v1 - v2
    me = _crit_t(clev, df) * se
    out = {
        "CLower": diff - me,
        "CUpper": diff + me,
        "v1-v2": diff,
        "ME": me,
        "df": _stat_int(df),
        "v1": v1,
        "v2": v2,
        "sx1": sx1,
        "sx2": sx2,
        "n1": _stat_int(n1),
        "n2": _stat_int(n2),
    }
    if is_pooled:
        out["sp"] = sp
    return publish(_supersede(out))


# ==========================================================================
# z tests
# ==========================================================================
def zTest(μ0, σ, *args, **kwargs):
    """``zTest μ0,σ,List[,Freq[,Hypoth]]`` / ``zTest μ0,σ,v,n[,Hypoth]``.

    Publishes ``stat.z``, ``stat.PVal``, ``stat.x``, ``stat.sx`` (Data input
    only) and ``stat.n``.
    """
    hypoth = kwargs.pop("Hypoth", 0)
    mu0, sigma = _number(μ0), _number(σ)
    if not args:
        raise ArgumentError("zTest needs a list or summary statistics")
    if _is_seq(args[0]):
        freq = args[1] if _len(args) > 1 else kwargs.pop("Freq", None)
        if _len(args) > 2:
            hypoth = args[2]
        st = _sample(args[0], freq)
        mean, n, sx = st["mean"], st["n"], st["s"]
        have_sx = True
    else:
        mean = _number(args[0])
        n = _number(args[1]) if _len(args) > 1 else kwargs.pop("n")
        if _len(args) > 2:
            hypoth = args[2]
        sx, have_sx = None, False
    z = (mean - mu0) / (sigma / sqrt(n))
    out = {
        "z": z,
        "PVal": _tail_p(_z_left, z, hypoth),
        "x": mean,
        "n": _stat_int(n),
    }
    if have_sx:
        out["sx"] = sx
    return publish(out)


def zTest_2Samp(σ1, σ2, *args, **kwargs):
    """``zTest_2Samp σ1,σ2,List1,List2[,Freq1[,Freq2[,Hypoth]]]``.

    Stats form: ``zTest_2Samp σ1,σ2,v1,n1,v2,n2[,Hypoth]``.
    """
    hypoth = kwargs.pop("Hypoth", 0)
    s1, s2 = _number(σ1), _number(σ2)
    if not args:
        raise ArgumentError("zTest_2Samp needs data or summary statistics")
    if _is_seq(args[0]):
        f1 = args[2] if _len(args) > 2 else kwargs.pop("Freq1", None)
        f2 = args[3] if _len(args) > 3 else kwargs.pop("Freq2", None)
        if _len(args) > 4:
            hypoth = args[4]
        a = _sample(args[0], f1)
        b = _sample(args[1], f2)
        m1, m2, n1, n2 = a["mean"], b["mean"], a["n"], b["n"]
        sx1, sx2 = a["s"], b["s"]
    else:
        m1, n1, m2, n2 = (_number(v) for v in args[:4])
        if _len(args) > 4:
            hypoth = args[4]
        sx1 = sx2 = float("nan")
    z = (m1 - m2) / sqrt(s1 * s1 / n1 + s2 * s2 / n2)
    return publish({
        "z": z,
        "PVal": _tail_p(_z_left, z, hypoth),
        "x1": m1,
        "x2": m2,
        "sx1": sx1,
        "sx2": sx2,
        "n1": _stat_int(n1),
        "n2": _stat_int(n2),
    })


def zTest_1Prop(p0, x, n, Hypoth=0):
    """``zTest_1Prop p0,x,n[,Hypoth]`` -- one-proportion z test.

    Publishes ``stat.p0``, ``stat.z``, ``stat.PVal``, ``stat.Ç`` and ``stat.n``.
    """
    p_0, k, N = _number(p0), _number(x), _number(n)
    if not 0 < p_0 < 1:
        raise DomainError("p0 must be strictly between 0 and 1")
    if N <= 0 or not 0 <= k <= N:
        raise DomainError("need 0 ≤ x ≤ n and n > 0")
    phat = k / N
    z = (phat - p_0) / sqrt(p_0 * (1 - p_0) / N)
    return publish({
        "p0": p_0,
        "z": z,
        "PVal": _tail_p(_z_left, z, Hypoth),
        "Ç": phat,
        "n": _stat_int(N),
    })


def zTest_2Prop(x1, n1, x2, n2, Hypoth=0):
    """``zTest_2Prop x1,n1,x2,n2[,Hypoth]`` -- two-proportion z test.

    Uses the pooled proportion ``stat.Ç`` in the standard error, as TI does.
    """
    k1, N1, k2, N2 = (_number(v) for v in (x1, n1, x2, n2))
    if not (0 <= k1 <= N1 and 0 <= k2 <= N2 and N1 > 0 and N2 > 0):
        raise DomainError("need 0 ≤ x ≤ n and n > 0 for both samples")
    p1, p2 = k1 / N1, k2 / N2
    pbar = (k1 + k2) / (N1 + N2)
    z = (p1 - p2) / sqrt(pbar * (1 - pbar) * (1 / N1 + 1 / N2))
    return publish({
        "z": z,
        "PVal": _tail_p(_z_left, z, Hypoth),
        "Ç1": p1,
        "Ç2": p2,
        "Ç": pbar,
        "n1": _stat_int(N1),
        "n2": _stat_int(N2),
    })


# ==========================================================================
# t tests
# ==========================================================================
def tTest(μ0, *args, **kwargs):
    """``tTest μ0,List[,Freq[,Hypoth]]`` / ``tTest μ0,v,sx,n[,Hypoth]``.

    Publishes ``stat.t``, ``stat.PVal``, ``stat.df``, ``stat.v``, ``stat.sx``,
    ``stat.n``.  The printed Reference Guide calls the sample mean ``stat.x``;
    both spellings are published (``NAME_SUPERSETS``).
    """
    hypoth = kwargs.pop("Hypoth", 0)
    mu0 = _number(μ0)
    if not args:
        raise ArgumentError("tTest needs a list or summary statistics")
    if _is_seq(args[0]):
        freq = args[1] if _len(args) > 1 else kwargs.pop("Freq", None)
        if _len(args) > 2:
            hypoth = args[2]
        st = _sample(args[0], freq)
        mean, sx, n = st["mean"], st["s"], st["n"]
    else:
        mean = _number(args[0])
        sx = _number(args[1]) if _len(args) > 1 else kwargs.pop("sx")
        n = _number(args[2]) if _len(args) > 2 else kwargs.pop("n")
        if _len(args) > 3:
            hypoth = args[3]
    df = n - 1
    if df <= 0:
        raise DomainError("need at least two observations")
    t = (mean - mu0) / (sx / sqrt(n))
    return publish(
        _supersede({
            "t": t,
            "PVal": _tail_p(lambda v: _t_left(v, df), t, hypoth),
            "df": _stat_int(df),
            "v": mean,
            "sx": sx,
            "n": _stat_int(n),
        })
    )


def tTest_2Samp(*args, **kwargs):
    """``tTest_2Samp List1,List2[,Freq1[,Freq2[,Hypoth[,Pooled]]]]``.

    Stats form: ``tTest_2Samp v1,sx1,n1,v2,sx2,n2[,Hypoth[,Pooled]]``.
    ``Pooled=1`` uses the pooled-variance t; ``Pooled=0`` (default) uses Welch,
    which is why ``stat.df`` is usually fractional -- the handheld shows the
    fractional df too.
    """
    hypoth = kwargs.pop("Hypoth", 0)
    pooled = kwargs.pop("Pooled", None)
    if not args:
        raise ArgumentError("tTest_2Samp needs data or summary statistics")
    if _is_seq(args[0]):
        f1 = args[2] if _len(args) > 2 else kwargs.pop("Freq1", None)
        f2 = args[3] if _len(args) > 3 else kwargs.pop("Freq2", None)
        if _len(args) > 4:
            hypoth = args[4]
        if _len(args) > 5:
            pooled = args[5]
        a = _sample(args[0], f1)
        b = _sample(args[1], f2)
        v1, sx1, n1 = a["mean"], a["s"], a["n"]
        v2, sx2, n2 = b["mean"], b["s"], b["n"]
    else:
        v1, sx1, n1 = _number(args[0]), _number(args[1]), _number(args[2])
        v2, sx2, n2 = _number(args[3]), _number(args[4]), _number(args[5])
        if _len(args) > 6:
            hypoth = args[6]
        if _len(args) > 7:
            pooled = args[7]
    is_pooled = bool(_int(pooled)) if pooled is not None else False
    if is_pooled:
        df = n1 + n2 - 2
        sp = sqrt(((n1 - 1) * sx1 ** 2 + (n2 - 1) * sx2 ** 2) / df)
        se = sp * sqrt(1 / n1 + 1 / n2)
    else:
        a1, a2 = sx1 * sx1 / n1, sx2 * sx2 / n2
        se = sqrt(a1 + a2)
        df = (a1 + a2) ** 2 / (a1 * a1 / (n1 - 1) + a2 * a2 / (n2 - 1))
    t = (v1 - v2) / se
    out = {
        "t": t,
        "PVal": _tail_p(lambda v: _t_left(v, df), t, hypoth),
        "df": _stat_int(df),
        "v1": v1,
        "v2": v2,
        "sx1": sx1,
        "sx2": sx2,
        "n1": _stat_int(n1),
        "n2": _stat_int(n2),
    }
    if is_pooled:
        out["sp"] = sp
    return publish(_supersede(out))


# ==========================================================================
# F test
# ==========================================================================
def FTest_2Samp(*args, **kwargs):
    """``FTest_2Samp List1,List2[,Freq1[,Freq2[,Hypoth]]]``.

    Stats form: ``FTest_2Samp sx1,n1,sx2,n2[,Hypoth]``.  Publishes ``stat.F``,
    ``stat.PVal``, ``stat.dfNumer``, ``stat.dfDenom``, ``stat.sx1``,
    ``stat.sx2``, ``stat.x1_bar``, ``stat.x2_bar``, ``stat.n1``, ``stat.n2``.
    """
    hypoth = kwargs.pop("Hypoth", 0)
    if not args:
        raise ArgumentError("FTest_2Samp needs data or summary statistics")
    if _is_seq(args[0]):
        f1 = args[2] if _len(args) > 2 else kwargs.pop("Freq1", None)
        f2 = args[3] if _len(args) > 3 else kwargs.pop("Freq2", None)
        if _len(args) > 4:
            hypoth = args[4]
        a = _sample(args[0], f1)
        b = _sample(args[1], f2)
        sx1, n1, m1 = a["s"], a["n"], a["mean"]
        sx2, n2, m2 = b["s"], b["n"], b["mean"]
    else:
        sx1, n1, sx2, n2 = (_number(v) for v in args[:4])
        m1 = m2 = float("nan")
        if _len(args) > 4:
            hypoth = args[4]
    if n1 < 2 or n2 < 2:
        raise DomainError("each sample needs at least two observations")
    d1, d2 = n1 - 1, n2 - 1
    f = (sx1 * sx1) / (sx2 * sx2)
    h = _hypoth_sign(hypoth)
    if h > 0:
        p = 1.0 - FCdf(0, f, d1, d2)
    elif h < 0:
        p = FCdf(0, f, d1, d2)
    else:
        lo = FCdf(0, f, d1, d2)
        p = min(1.0, 2 * min(lo, 1.0 - lo))
    return publish({
        "F": f,
        "PVal": p,
        "dfNumer": _stat_int(d1),
        "dfDenom": _stat_int(d2),
        "sx1": sx1,
        "sx2": sx2,
        "x1_bar": m1,
        "x2_bar": m2,
        "n1": _stat_int(n1),
        "n2": _stat_int(n2),
    })


# ==========================================================================
# chi-square
# ==========================================================================
def chi2GOF(obsList, expList, df):
    """``χ2GOF obsList,expList,df`` -- goodness of fit.

    ``obsList`` must contain integer counts.  Publishes ``stat.χ²``,
    ``stat.PVal``, ``stat.df`` and the per-cell contributions ``stat.CompList``.
    """
    obs = [_float(v) for v in _list(obsList) if not is_void(v)]
    exp = [_float(v) for v in _list(expList) if not is_void(v)]
    if _len(obs) != _len(exp):
        raise DimensionMismatchError()
    if any(v != _int(v) for v in obs):
        raise DomainError("observed counts must be integers")
    if any(v <= 0 for v in exp):
        raise DomainError("expected counts must be positive")
    comp = [(o - e) ** 2 / e for o, e in _zip(obs, exp)]
    chi2 = _sum(comp)
    d = _stat_int(_number(df))
    if d <= 0:
        raise DomainError("df must be positive")
    return publish({
        "χ²": chi2,
        "PVal": 1.0 - χ2Cdf(0, chi2, d),
        "df": d,
        "CompList": comp,
    })


def chi22way(obsMatrix):
    """``χ²2way obsMatrix`` (ASCII: ``chi22way``) -- test for association.

    Publishes ``stat.χ²``, ``stat.PVal``, ``stat.df``, ``stat.ExpMatrix`` and
    ``stat.CompMatrix``; ``stat.ExpMat``/``stat.CompMat`` resolve too.
    """
    rows = _list(obsMatrix)
    if not rows or not _is_seq(rows[0]):
        raise ArgumentError("chi22way needs a matrix of counts")
    m = [[_float(v) for v in _list(r) if not is_void(v)] for r in rows]
    ncols = _len(m[0])
    if any(_len(r) != ncols for r in m):
        raise DimensionMismatchError()
    if any(v != _int(v) or v < 0 for r in m for v in r):
        raise DomainError("counts must be non-negative integers")
    nrows = _len(m)
    row_tot = [_sum(r) for r in m]
    col_tot = [_sum(m[i][j] for i in _range(nrows)) for j in _range(ncols)]
    total = _sum(row_tot)
    if total == 0:
        raise DomainError()
    exp = [[row_tot[i] * col_tot[j] / total for j in _range(ncols)] for i in _range(nrows)]
    comp = [
        [(m[i][j] - exp[i][j]) ** 2 / exp[i][j] for j in _range(ncols)]
        for i in _range(nrows)
    ]
    chi2 = _sum(_sum(r) for r in comp)
    df = (nrows - 1) * (ncols - 1)
    if df <= 0:
        raise DomainError("the table needs at least two rows and two columns")
    return publish({
        "χ²": chi2,
        "PVal": 1.0 - χ2Cdf(0, chi2, df),
        "df": df,
        "ExpMatrix": exp,
        "CompMatrix": comp,
    })


def chi2GOFTest(*args, **kwargs):
    """The menus label it "Chi-2 GOF Test"; this forwards to ``chi2GOF``."""
    return chi2GOF(*args, **kwargs)


# ==========================================================================
# ANOVA
# ==========================================================================
def ANOVA(*args, **kwargs):
    """``ANOVA List1,List2[,...,List20][,Flag]`` -- one-way analysis of variance.

    ``Flag=0`` (default) means the arguments are raw data lists.  ``Flag=1`` is
    the handheld's *Stats* method; here the three lists are read as
    ``(means, standard deviations, sample sizes)`` -- an explicit, unambiguous
    spelling of the triplets the wizard packs into one line.

    Publishes ``stat.F``, ``stat.PVal``, ``stat.df``, ``stat.SS``, ``stat.MS``,
    ``stat.dfError``, ``stat.SSError``, ``stat.MSError``, ``stat.sp``,
    ``stat.xbarlist`` and the per-group ``stat.CLowerList``/``stat.CUpperList``.
    The guide fixes those intervals at 95%; ``CLevel`` can override them.
    """
    flag = kwargs.pop("Flag", None)
    clev = _float(kwargs.pop("CLevel", 0.95))
    groups = [a for a in args if _is_seq(a)]
    scalars = [a for a in args if not _is_seq(a)]
    if flag is None:
        flag = scalars[0] if scalars else 0
    if kwargs:
        raise ArgumentError(f"unexpected keyword(s): {', '.join(kwargs)}")
    if _int(flag) == 1:
        if _len(groups) != 3:
            raise ArgumentError("Flag=1 expects three lists: means, sds, sizes")
        means, sds, sizes = ([_float(v) for v in g] for g in groups)
        if not (_len(means) == _len(sds) == _len(sizes)):
            raise DimensionMismatchError()
        if _len(means) < 2:
            raise DomainError("ANOVA needs at least two populations")
        n_i = [_float(v) for v in sizes]
        if any(v < 2 for v in n_i):
            raise DomainError("each population needs at least two observations")
        ss_w = _sum((v - 1) * s * s for v, s in _zip(n_i, sds))
        sums = [_float(means[i]) * n_i[i] for i in _range(_len(means))]
        counts = [_int(v) for v in n_i]
    else:
        if _len(groups) < 2:
            raise DomainError("ANOVA needs at least two populations")
        cleaned = [[_float(v) for v in g if not is_void(v)] for g in groups]
        if any(_len(g) < 2 for g in cleaned):
            raise DomainError("each population needs at least two observations")
        counts = [_len(g) for g in cleaned]
        n_i = [_float(c) for c in counts]
        sums = [_sum(g) for g in cleaned]
        means = [s / n for s, n in _zip(sums, n_i)]
        ss_w = _sum(_sum((v - m) ** 2 for v in g) for g, m in _zip(cleaned, means))
    N = _sum(n_i)
    k = _len(means)
    if N - k <= 0:
        raise DomainError("no degrees of freedom left for the error term")
    grand = _sum(sums) / N
    ss_b = _sum(n * (m - grand) ** 2 for n, m in _zip(n_i, means))
    df_b, df_w = k - 1, _int(N - k)
    ms_b, ms_w = ss_b / df_b, ss_w / df_w
    f = ms_b / ms_w if ms_w else float("inf")
    tcrit = _crit_t(clev, df_w)
    half = [tcrit * sqrt(ms_w / n) for n in n_i]
    return publish({
        "F": f,
        "PVal": 1.0 - FCdf(0, f, df_b, df_w),
        "df": df_b,
        "SS": ss_b,
        "MS": ms_b,
        "dfError": df_w,
        "SSError": ss_w,
        "MSError": ms_w,
        "sp": sqrt(ms_w),
        "xbarlist": means,
        "CLowerList": [m - h for m, h in _zip(means, half)],
        "CUpperList": [m + h for m, h in _zip(means, half)],
    })


def ANOVA2way(*args, **kwargs):
    """``ANOVA2way List1,List2[,...,List10][,levRow]`` -- two-way analysis of variance.

    Each list is one level of the **column** factor and every list has the same
    length.  ``levRow`` says how many levels the **row** factor has; the elements
    of each list are taken in blocks of ``length / levRow`` consecutive
    observations, one block per row level.  ``levRow=0`` (default) is the
    **Block** design: no replication, every list index is its own block.

    Publishes the Block set (``stat.F``, ``stat.PVal``, ``stat.df``, ``stat.SS``,
    ``stat.MS``, ``stat.FBlock``, ``stat.PValBlock``, ``stat.dfBlock``,
    ``stat.SSBlock``, ``stat.MSBlock``) or the two-factor set (``Fcol``,
    ``FRow``, ``FInteract`` and their ``PVal``/``df``/``SS``/``MS`` companions),
    plus ``stat.dfError``, ``stat.SSError``, ``stat.MSError`` and the error
    standard deviation ``stat.s``.
    """
    lev_row = kwargs.pop("levRow", None)
    groups = [a for a in args if _is_seq(a)]
    scalars = [a for a in args if not _is_seq(a)]
    if lev_row is None:
        lev_row = scalars[0] if scalars else 0
    if kwargs:
        raise ArgumentError(f"unexpected keyword(s): {', '.join(kwargs)}")
    if _len(groups) < 2:
        raise DomainError("ANOVA2way needs at least two column levels")
    cols = [[_float(v) for v in g if not is_void(v)] for g in groups]
    k = _len(cols)
    length = _len(cols[0])
    if any(_len(c) != length for c in cols):
        raise DimensionMismatchError()
    if length < 2:
        raise DomainError()
    lr = _int(lev_row)
    grand = _sum(_sum(c) for c in cols) / (k * length)

    # ``cell_means`` is only meaningful for the replicated two-factor layout;
    # the Block design has a single observation per cell.
    cell_means = None
    if lr == 0:
        # Block design: one observation per cell, blocks == list indices.
        r, n = length, 1
        row_means = [_sum(cols[j][i] for j in _range(k)) / k for i in _range(r)]
        cell_means = None
    else:
        if lr < 2 or length % lr:
            raise DomainError("len / levRow must be an integer ≥ 2")
        r, n = lr, length // lr
        if n < 2:
            raise DomainError("len / levRow must be ≥ 2 for a two-factor design")
        row_means = [
            _sum(cols[j][i * n + l] for j in _range(k) for l in _range(n)) / (k * n)
            for i in _range(r)
        ]
        cell_means = [
            [_sum(cols[j][i * n: i * n + n]) / n for j in _range(k)]
            for i in _range(r)
        ]

    col_means = [_sum(c) / length for c in cols]
    ss_col = r * n * _sum((m - grand) ** 2 for m in col_means)
    df_col = k - 1

    if lr == 0:
        ss_row = k * n * _sum((m - grand) ** 2 for m in row_means)
        df_row = r - 1
        ss_int = 0.0
        df_int = 0
        ss_err = _sum(
            (cols[j][i] - col_means[j] - row_means[i] + grand) ** 2
            for i in _range(r) for j in _range(k)
        )
        df_err = (r - 1) * (k - 1)
    else:
        ss_row = k * n * _sum((m - grand) ** 2 for m in row_means)
        df_row = r - 1
        ss_int = n * _sum(
            (cell_means[i][j] - row_means[i] - col_means[j] + grand) ** 2
            for i in _range(r) for j in _range(k)
        )
        df_int = (r - 1) * (k - 1)
        ss_err = _sum(
            (cols[j][i * n + l] - cell_means[i][j]) ** 2
            for i in _range(r) for j in _range(k) for l in _range(n)
        )
        df_err = k * r * (n - 1)

    if df_err <= 0:
        raise DomainError("no degrees of freedom left for the error term")
    ms_col = ss_col / df_col
    ms_row = ss_row / df_row if df_row else float("nan")
    ms_int = ss_int / df_int if df_int else float("nan")
    ms_err = ss_err / df_err

    out = {"dfError": df_err, "SSError": ss_err, "MSError": ms_err, "s": sqrt(ms_err)}
    if lr == 0:
        out.update({
            "F": ms_col / ms_err,
            "PVal": 1.0 - FCdf(0, ms_col / ms_err, df_col, df_err),
            "df": df_col,
            "SS": ss_col,
            "MS": ms_col,
            "FBlock": ms_row / ms_err,
            "PValBlock": 1.0 - FCdf(0, ms_row / ms_err, df_row, df_err),
            "dfBlock": df_row,
            "SSBlock": ss_row,
            "MSBlock": ms_row,
        })
    else:
        f_col, f_row, f_int = ms_col / ms_err, ms_row / ms_err, ms_int / ms_err
        out.update({
            "Fcol": f_col,
            "PValCol": 1.0 - FCdf(0, f_col, df_col, df_err),
            "dfCol": df_col,
            "SSCol": ss_col,
            "MSCol": ms_col,
            "FRow": f_row,
            "PValRow": 1.0 - FCdf(0, f_row, df_row, df_err),
            "dfRow": df_row,
            "SSRow": ss_row,
            "MSRow": ms_row,
            "FInteract": f_int,
            "PValInteract": 1.0 - FCdf(0, f_int, df_int, df_err),
            "dfInteract": df_int,
            "SSInteract": ss_int,
            "MSInteract": ms_int,
        })
    return publish(out)

# ==========================================================================
# menu labels are *not* defined here
# ==========================================================================
# The Confidence Intervals / Stat Tests menus read "2-Sample t Test", but the
# catalog function behind that label is ``tTest_2Samp`` -- and the reference
# guide never prints a ``TwoSample*`` spelling.  So those names are not
# Nspire names, and they live in exactly one place: ``legacy.BINDINGS``.
# Defining them here as well would give the package two answers to "what is
# TwoSampleTTest", which is the drift this project exists to avoid.
