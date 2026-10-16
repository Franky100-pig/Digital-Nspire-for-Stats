"""Stat Calculations -- ``OneVar``, ``TwoVar`` and ``FiveNumSummary``.

These are the functions behind ``menu > Statistics > Stat Calculations``.  Each
one publishes its answer into the global ``stat.`` group with the exact variable
names the reference guide lists (``stat.v``, ``stat.Σx²``, ``stat.Q1X`` ...).

Quartile convention
-------------------
TI-Nspire and TI-83/84 do **not** agree when n is odd, and TI's own
documentation contradicts itself about which one the Nspire uses:

* TI activity *Five Figure Summary* (2017), footnote 1, on data
  ``{1,2,3,4,5,6,7,8,9}``::

      Method 1: {1, 2, 3, 4, 5, 6, 7, 8, 9} -> Q1 = 3.
      TI-Nspire uses the first calculation method where the median is not
      included.

  ``Q1 = 3`` is the *median-included* (Tukey hinge) answer; the trailing clause
  says the opposite.
* IREM Lyon, describing what the calculator actually displays: "Pour la
  calculatrice, Q1 est la mediane des valeurs comprises entre minX et Med ..." --
  again the median-included rule, and the authors complain it differs from the
  French curriculum.

Weight of evidence points at **inclusive (Tukey hinges)** as the Nspire default,
so that is what this module ships.  If you are matching a TI-83/84, an AP
Statistics answer key, or a textbook using Moore & McCabe, call
``set_quartile_method("exclusive")``.  When n is even the two rules agree, so
this choice only ever bites on odd-sized data.
"""

from __future__ import annotations

from math import isnan, sqrt

from ._core import (
    _float,
    _int,
    _isinstance,
    _len,
    _list,
    _range,
    _sorted,
    _str,
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
from .statvar import publish, stat

# --------------------------------------------------------------------------
# quartile convention
# --------------------------------------------------------------------------
INCLUSIVE = "inclusive"  # Tukey hinges -- median in both halves (TI-Nspire)
EXCLUSIVE = "exclusive"  # Moore & McCabe  -- median in neither half (TI-83/84)

_quartile_method = INCLUSIVE


def set_quartile_method(method: str) -> str:
    """Choose ``"inclusive"`` (default, TI-Nspire) or ``"exclusive"`` (TI-83/84).

    >>> from tinspire_stats import OneVar, set_quartile_method
    >>> set_quartile_method("exclusive"), OneVar([1, 2, 3, 4, 5]).Q1X
    ('exclusive', 1.5)
    >>> set_quartile_method("inclusive"), OneVar([1, 2, 3, 4, 5]).Q1X
    ('inclusive', 2.0)
    """
    global _quartile_method
    if method not in (INCLUSIVE, EXCLUSIVE):
        raise ArgumentError("quartile method must be 'inclusive' or 'exclusive'")
    _quartile_method = method
    return method


def get_quartile_method() -> str:
    """The convention currently in force."""
    return _quartile_method


def _median_of(sorted_vals):
    n = _len(sorted_vals)
    if n == 0:
        raise DomainError()
    if n % 2:
        return sorted_vals[n // 2]
    return (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0


def five_numbers(values, method: str | None = None):
    """Return ``(min, Q1, median, Q3, max)`` under the selected convention."""
    method = method or _quartile_method
    if method not in (INCLUSIVE, EXCLUSIVE):
        raise ArgumentError("quartile method must be 'inclusive' or 'exclusive'")
    vals = _sorted(_float(v) for v in values)
    n = _len(vals)
    if n == 0:
        raise DomainError()
    med = _median_of(vals)
    if n % 2:
        mid = n // 2
        low = vals[: mid + 1] if method == INCLUSIVE else vals[:mid]
        high = vals[mid:] if method == INCLUSIVE else vals[mid + 1:]
    else:
        low, high = vals[: n // 2], vals[n // 2:]
    q1 = _median_of(low) if low else vals[0]
    q3 = _median_of(high) if high else vals[-1]
    return vals[0], q1, med, q3, vals[-1]


# --------------------------------------------------------------------------
# OneVar
# --------------------------------------------------------------------------
def OneVar(*args, **kwargs):
    """``OneVar X[,[Freq][,Category,Include]]`` or ``OneVar n,X1,X2,...,Xn``.

    Publishes ``stat.v`` (mean), ``stat.Σx``, ``stat.Σx²``, ``stat.sx``,
    ``stat.σx``, ``stat.n``, ``stat.MinX``, ``stat.Q1X``, ``stat.MedianX``,
    ``stat.Q3X``, ``stat.MaxX`` and ``stat.SSX``, and returns the same group so
    ``OneVar(data).Q1X`` reads like ``stat.Q1X``.

    ``Category``/``Include`` restrict which items take part, exactly as on the
    handheld: only items whose category code is listed in ``Include`` are used.
    With two or more lists (``OneVar(n, X1, X2, ...)``) the names are suffixed --
    ``stat.v1``, ``stat.σx2``, ... -- and the unsuffixed names hold list 1.
    """
    if args and _isinstance(args[0], int) and not _isinstance(args[0], bool):
        count_n = _int(args[0])
        lists = args[1:]
        if count_n > 0 and _len(lists) == count_n:
            return _onevar_multi(lists)
    x = args[0] if args else kwargs.pop("X")
    freq = args[1] if _len(args) > 1 else kwargs.pop("freq", None)
    category = args[2] if _len(args) > 2 else kwargs.pop("category", None)
    include = args[3] if _len(args) > 3 else kwargs.pop("include", None)
    x, freq = _apply_category(x, freq, category, include)
    return publish(_onevar_core(x, freq))


def _onevar_multi(lists):
    out = {}
    for i, lst in enumerate(lists, start=1):
        res = _onevar_core(lst)
        for k, v in res.items():
            if k == "n":
                out["n"] = v
                continue
            out[k + _str(i)] = v
            if i == 1:
                out[k] = v  # unsuffixed names mirror list 1, as on the handheld
    return publish(out)


def _apply_category(x, freq, category, include):
    if category is None:
        return x, freq
    if include is None:
        raise ArgumentError("Category given without Include")
    cat = _list(category)
    if _len(cat) != _len(x):
        raise DimensionMismatchError()
    allowed = _list(include)
    keep = [i for i, c in enumerate(cat) if c in allowed]
    nx = [x[i] for i in keep]
    nf = None if freq is None else [freq[i] for i in keep]
    return nx, nf


def _onevar_core(x, freq=None, method=None):
    vals, w = pair_up(x, freq, integer_freq=True, expand=False)
    n = _sum(w)
    if n <= 0:
        raise DomainError()
    m = weighted_mean(vals, w)
    ssx = weighted_ss(vals, w, m)
    expanded, _ = pair_up(x, freq, integer_freq=True, expand=True)
    lo, q1, med, q3, hi = five_numbers(expanded, method)
    sx = sqrt(ssx / (n - 1)) if n > 1 else float("nan")
    return {
        "v": m,
        "Σx": _sum(v * ww for v, ww in _zip(vals, w)),
        "Σx²": _sum(v * v * ww for v, ww in _zip(vals, w)),
        "sx": sx,
        "σx": sqrt(ssx / n),
        "n": _int(n) if n == _int(n) else n,
        "MinX": lo,
        "Q1X": q1,
        "MedianX": med,
        "Q3X": q3,
        "MaxX": hi,
        "SSX": ssx,
    }


# --------------------------------------------------------------------------
# TwoVar
# --------------------------------------------------------------------------
def TwoVar(*args, **kwargs):
    """``TwoVar X,Y[,[Freq][,Category,Include]]``.

    Publishes both one-variable tables plus ``stat.Σxy``, the correlation
    ``stat.r`` and the deviation sums ``stat.Σ(x-v)²`` / ``stat.Σ(y-w)²``.
    ``stat.MedianY`` is also reachable under the guide's alternate spelling
    ``stat.MedY``.
    """
    if args and _isinstance(args[0], int) and not _isinstance(args[0], bool):
        count_n = _int(args[0])
        rest = args[1:]
        if count_n > 0 and _len(rest) == 2 * count_n:
            out = {}
            for i in _range(count_n):
                out.update(_twovar_core(rest[2 * i], rest[2 * i + 1], index=i + 1))
            return publish(out)
    x = args[0] if args else kwargs.pop("X")
    y = args[1] if _len(args) > 1 else kwargs.pop("Y")
    freq = args[2] if _len(args) > 2 else kwargs.pop("freq", None)
    category = args[3] if _len(args) > 3 else kwargs.pop("category", None)
    include = args[4] if _len(args) > 4 else kwargs.pop("include", None)
    x, freq = _apply_category(x, freq, category, include)
    return publish(_twovar_core(x, y, freq))


def _twovar_core(x, y, freq=None, index=None):
    xs, ys = _list(x), _list(y)
    if _len(xs) != _len(ys):
        raise DimensionMismatchError()
    if freq is not None and _len(freq) != _len(xs):
        raise DimensionMismatchError()
    keep, px, py, pf = [], [], [], []
    for i in _range(_len(xs)):
        if is_void(xs[i]) or is_void(ys[i]):
            continue
        keep.append(i)
        px.append(xs[i])
        py.append(ys[i])
        if freq is not None:
            pf.append(freq[i])
    if freq is not None:
        check_integer_freq(pf)
    one_x = _onevar_core(px, pf or None)
    one_y = _onevar_core(py, pf or None)
    weights = pf or [1] * _len(px)
    n = _sum(weights)
    mx, my = one_x["v"], one_y["v"]
    # The guide describes stat.Σxy as the plain "Sum of x•y values", so that is
    # what is published.  The correlation needs the *corrected* sum of products
    # instead, and that stays internal.
    sum_xy = _sum(w * a * b for a, b, w in _zip(px, py, weights))
    sxy = _sum(w * (a - mx) * (b - my) for a, b, w in _zip(px, py, weights))
    sxx = _sum(w * (a - mx) ** 2 for a, w in _zip(px, weights))
    syy = _sum(w * (b - my) ** 2 for b, w in _zip(py, weights))
    denom = sqrt(sxx * syy)
    r = sxy / denom if denom else float("nan")
    if isnan(r) and sxx == 0 and syy == 0:
        r = 0.0

    # The order is part of the interface: the handheld's stat.results screen
    # scrolls in *this* order, so the guide's table is reproduced positionally
    # rather than assembled out of _onevar_core's own order.  Note that TwoVar
    # publishes stat.Σxy and stat.r between the two five-number blocks, and the
    # two sums of squared deviations last of all -- and that neither block
    # carries stat.SSX or its own stat.n.
    sfx = _str(index) if index else ""
    return {
        "v" + sfx: mx,
        "Σx" + sfx: one_x["Σx"],
        "Σx²" + sfx: one_x["Σx²"],
        "sx" + sfx: one_x["sx"],
        "σx" + sfx: one_x["σx"],
        "n" + sfx: _int(n) if n == _int(n) else n,
        "w" + sfx: my,
        "Σy" + sfx: one_y["Σx"],
        "Σy²" + sfx: one_y["Σx²"],
        "sy" + sfx: one_y["sx"],
        "σy" + sfx: one_y["σx"],
        "Σxy" + sfx: sum_xy,
        "r" + sfx: r,
        "MinX" + sfx: one_x["MinX"],
        "Q1X" + sfx: one_x["Q1X"],
        "MedianX" + sfx: one_x["MedianX"],
        "Q3X" + sfx: one_x["Q3X"],
        "MaxX" + sfx: one_x["MaxX"],
        "MinY" + sfx: one_y["MinX"],
        "Q1Y" + sfx: one_y["Q1X"],
        "MedianY" + sfx: one_y["MedianX"],
        "Q3Y" + sfx: one_y["Q3X"],
        "MaxY" + sfx: one_y["MaxX"],
        "Σ(x-v)²" + sfx: one_x["SSX"],
        "Σ(y-w)²" + sfx: one_y["SSX"],
    }


# --------------------------------------------------------------------------
# FiveNumSummary
# --------------------------------------------------------------------------
def FiveNumSummary(X, freq=None, category=None, include=None):
    """``FiveNumSummary X[,[Freq][,Category,Include]]`` -- the five numbers only.

    ``stat.MinX``, ``stat.Q1X``, ``stat.MedianX``, ``stat.Q3X``, ``stat.MaxX``.
    """
    X, freq = _apply_category(X, freq, category, include)
    expanded, _ = pair_up(X, freq, integer_freq=True, expand=True)
    lo, q1, med, q3, hi = five_numbers(expanded)
    return publish(
        {"MinX": lo, "Q1X": q1, "MedianX": med, "Q3X": q3, "MaxX": hi}
    )
