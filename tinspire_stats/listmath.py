"""List Math -- the TI-Nspire ``menu 5: Statistics > 3: List Math`` family.

Names are copied character-for-character from the reference guide, Unicode and
all (``ΔList``, ``freqTable►list``).  Where a name cannot be a Python
identifier because of a symbol, an ASCII twin is provided and the TI spelling is
registered as an alias -- see ``catalog.py``.
"""

from __future__ import annotations

from builtins import all as _builtin_all
from builtins import any as _builtin_any
from math import sqrt

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
    _str,
    _sum,
    _tuple,
    _zip,
    ArgumentError,
    DataTypeError,
    DimensionMismatchError,
    DomainError,
    is_void,
    pair_up,
    strip_void,
    weighted_mean,
    weighted_ss,
)
from ._core import _sum as _b_sum  # noqa: F401  (used for the matrix branch of sum())


# --------------------------------------------------------------------------
# matrix helpers
# --------------------------------------------------------------------------
def _is_matrix(x) -> bool:
    return (
        _isinstance(x, (list, _tuple))
        and _len(x) > 0
        and _isinstance(x[0], (list, _tuple))
    )


def _columns(m):
    if not _is_matrix(m):
        raise DataTypeError("expected a matrix")
    nrows = _len(m)
    ncols = _len(m[0])
    if _any_len_mismatch(m, ncols):
        raise DimensionMismatchError()
    return [[_float(row[j]) for row in m] for j in _range(ncols)]


def _any_len_mismatch(m, ncols) -> bool:
    return any(_len(row) != ncols for row in m)


def _clean(values):
    return [_float(v) for v in values if not is_void(v)]


# --------------------------------------------------------------------------
# criteria (for countif / sumIf)
# --------------------------------------------------------------------------
#: Comparison operators, longest spelling first so ``<=`` beats ``<``.
#: Both the ASCII and the calculator's own Unicode spellings are accepted.
_OPS = [
    ("<=", lambda a, b: a <= b),
    ("≤", lambda a, b: a <= b),
    (">=", lambda a, b: a >= b),
    ("≥", lambda a, b: a >= b),
    ("!=", lambda a, b: a != b),
    ("≠", lambda a, b: a != b),
    ("==", lambda a, b: a == b),
    ("=", lambda a, b: a == b),
    ("<", lambda a, b: a < b),
    (">", lambda a, b: a > b),
]

#: The guide's placeholder standing for "each element" of the list.
_PLACEHOLDER = "?"


def _tokens(expr: str):
    """Split ``expr`` into ``[operand, op, operand, op, ...]``.

    Longest-first operator matching is what makes ``<=`` win over ``<`` and is
    why ``2≤?≤8`` yields two operators rather than one.
    """
    out, buf, i = [], "", 0
    while i < _len(expr):
        for spelling, fn in _OPS:
            if expr.startswith(spelling, i):
                out.append(buf)
                out.append(fn)
                buf = ""
                i += _len(spelling)
                break
        else:
            buf += expr[i]
            i += 1
    out.append(buf)
    return out


def _has_comparison(expr: str) -> bool:
    return _len(_tokens(expr)) > 1


def _const(text: str):
    text = text.strip().strip('"').strip("'")
    try:
        return _float(text)
    except ValueError:
        return text


def _loose_eq(a, b) -> bool:
    """TI compares a number to a number and a string to a string."""
    if _isinstance(a, (int, float)) and _isinstance(b, (int, float)):
        return a == b
    return _str(a) == _str(b)


def _split_logical(text: str, keyword: str):
    """Split on a *space-delimited* ``and`` / ``or``.

    Requiring the whitespace keeps ``or`` inside an identifier (or inside a
    string criterion) from being mistaken for the boolean keyword.
    """
    parts, buf = [], []
    for word in text.split():
        if word.lower() == keyword:
            parts.append(" ".join(buf))
            buf = []
        else:
            buf.append(word)
    parts.append(" ".join(buf))
    return [p for p in parts if p.strip()]


def _chain_predicate(expr: str):
    """A predicate for one comparison, chained if the user wrote a chain.

    ``?<5``, ``5>?`` and ``2≤?≤8`` all work, because an empty operand next to
    an operator is read as the placeholder -- which is also what makes the
    bare ``">4"`` shorthand behave like TI's ``"?>4"``.
    """
    parts = _tokens(expr)
    if _len(parts) == 1:
        value = _const(parts[0])
        return lambda x: _loose_eq(x, value)
    operands, ops = parts[0::2], parts[1::2]
    consts = []
    for text in operands:
        text = text.strip()
        consts.append(None if text in ("", _PLACEHOLDER) else _const(text))

    def predicate(x):
        vals = [x if c is None else c for c in consts]
        return _builtin_all(fn(a, b) for fn, a, b in _zip(ops, vals, vals[1:]))

    return predicate


def make_criteria(criteria):
    """Turn TI's criteria syntax into a predicate.

    The reference guide defines ``Criteria`` as either

    * "a value, expression, or string" -- ``countif(List,3)`` counts the
      elements that simplify to 3; or
    * "a Boolean expression containing the symbol ``?`` as a placeholder for
      each element" -- ``?<5``, ``2≤?≤8``, ``?<5 or ?>9``.

    Both spellings are accepted, plus the bare relational shorthand ``">4"``
    (equivalent to ``"?>4"``), which the guide does not print but which is the
    obvious thing to type in Python.  A callable is passed straight through.
    """
    if callable(criteria):
        return criteria
    if _isinstance(criteria, _str):
        text = criteria.strip()
        for keyword, combiner in (("or", _builtin_any), ("and", _builtin_all)):
            parts = _split_logical(text, keyword)
            if _len(parts) > 1:
                subs = [make_criteria(p) for p in parts]
                return lambda x, subs=subs, f=combiner: f(g(x) for g in subs)
        if not _has_comparison(text):
            value = _const(text)
            return lambda x, value=value: _loose_eq(x, value)
        return _chain_predicate(text)
    if _isinstance(criteria, (list, _tuple, set, frozenset, range)):
        pool = [_list(criteria)]
        return lambda x, pool=pool: _builtin_any(_loose_eq(x, v) for v in pool[0])
    return lambda x, value=criteria: _loose_eq(x, value)


# --------------------------------------------------------------------------
# centre / spread
# --------------------------------------------------------------------------
def mean(List, freqList=None):
    """``mean(List[, freqList])`` -- arithmetic (or frequency-weighted) mean.

    With a frequency list, ``mean`` accepts **fractional** frequencies -- this
    is exactly what the handheld does (``mean(x,px)`` works with
    ``px={.25,.25,.25,.25}`` whereas ``stDevSamp(x,px)`` raises a Domain
    error).  Matrices give a row vector of the column means.
    """
    if _is_matrix(List):
        return [mean(col, freqList) for col in _columns(List)]
    vals, w = pair_up(List, freqList, integer_freq=False, expand=False)
    if not vals:
        raise DomainError()
    return weighted_mean(vals, w)


def median(List, freqList=None):
    """``median(List[, freqList])`` -- middle value of the ordered list."""
    if _is_matrix(List):
        return [median(col, freqList) for col in _columns(List)]
    vals, _ = pair_up(List, freqList, integer_freq=True, expand=True)
    return _median_of_sorted(_sorted(vals))


def _median_of_sorted(sorted_vals):
    n = _len(sorted_vals)
    if n == 0:
        raise DomainError()
    if n % 2:
        return sorted_vals[n // 2]
    return (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0


def product(List):
    """``product(List[, Start[, End]])`` -- multiply every element."""
    out = 1.0
    for v in _clean(List):
        out *= v
    return out


def min(*args):
    """``min(a,b)`` / ``min(List)`` / ``min(Matrix)``."""
    return _extremum(args, _min)


def max(*args):
    """``max(a,b)`` / ``max(List)`` / ``max(Matrix)``."""
    return _extremum(args, _max)


def _extremum(args, pick):
    if _len(args) == 1:
        a = args[0]
        if _is_matrix(a):
            return [pick(col) for col in _columns(a)]
        if _isinstance(a, (list, _tuple, _range)):
            vals = _clean(a)
            if not vals:
                raise DomainError()
            return pick(vals)
        return a
    if _len(args) == 2:
        a, b = args
        if _is_matrix(a) and _is_matrix(b):
            return [[pick(p) for p in _zip(ra, rb)] for ra, rb in _zip(a, b)]
        if _isinstance(a, (list, _tuple)) and _isinstance(b, (list, _tuple)):
            if _len(a) != _len(b):
                raise DimensionMismatchError()
            return [pick(p) for p in _zip(a, b)]
        return pick((a, b))
    raise ArgumentError("max() takes one list or two arguments")


def sum(List, Start=None, End=None):  # noqa: A001  (TI name is `sum`)
    """``sum(List[, Start[, End]])`` -- 1-based inclusive element range."""
    if _is_matrix(List):
        return [_b_sum(col[(Start - 1 if Start else 0):(End if End else None)]) for col in _columns(List)]
    vals = _list(List)
    if Start is not None or End is not None:
        s = (_int(Start) - 1) if Start is not None else 0
        e = _int(End) if End is not None else _len(vals)
        vals = vals[s:e]
    return _sum(_clean(vals))


def count(*args):
    """``count(Value1orList1[, Value2orList2[,...]])`` -- how many numbers."""
    total = 0
    for a in args:
        if _isinstance(a, bool):
            continue
        if _isinstance(a, (int, float)):
            total += 0 if is_void(a) else 1
        elif _isinstance(a, (list, _tuple, _range)) or _is_matrix(a):
            for v in _flatten(a):
                if _isinstance(v, (int, float)) and not _isinstance(v, bool) and not is_void(v):
                    total += 1
    return total


def _flatten(a):
    if _is_matrix(a):
        return [v for row in a for v in row]
    return _list(a)


def countif(List, Criteria):
    """``countif(List,Criteria)`` -- count elements matching the criteria.

    Numbers *and* strings are counted: the guide's own worked example counts the
    elements equal to ``"def"`` as well as those equal to ``3``.  Void elements
    are ignored, as always.
    """
    pred = make_criteria(Criteria)
    return _sum(1 for v in _flatten(List) if not is_void(v) and pred(v))


def sumIf(List, Criteria, SumList=None):
    """``sumIf(List,Criteria[,SumList])`` -- TI spells it ``sumIf``."""
    pred = make_criteria(Criteria)
    src = _flatten(List) if not SumList else _flatten(SumList)
    flat = _flatten(List)
    if SumList is not None and _len(src) != _len(flat):
        raise DimensionMismatchError()
    return _sum(v for v, keep in _zip(src, flat) if pred(keep))


# --------------------------------------------------------------------------
# standard deviations and variances
# --------------------------------------------------------------------------
def _spread(List, freqList, integer_freq, ddof):
    vals, w = pair_up(List, freqList, integer_freq=integer_freq, expand=False)
    n = _sum(w)
    if n - ddof <= 0:
        raise DomainError()
    m = weighted_mean(vals, w)
    return weighted_ss(vals, w, m) / (n - ddof)


def varSamp(List, freqList=None):
    """``varSamp(List[, freqList])`` -- sample variance (÷ n−1)."""
    if _is_matrix(List):
        return [varSamp(col, freqList) for col in _columns(List)]
    return _spread(List, freqList, True, 1)


def varPop(List, freqList=None):
    """``varPop(List[, freqList])`` -- population variance (÷ n)."""
    if _is_matrix(List):
        return [varPop(col, freqList) for col in _columns(List)]
    return _spread(List, freqList, True, 0)


def stDevSamp(List, freqList=None):
    """``stDevSamp(List[, freqList])`` -- sample standard deviation (sx)."""
    return sqrt(varSamp(List, freqList))


def stDevPop(List, freqList=None):
    """``stDevPop(List[, freqList])`` -- population standard deviation (σx)."""
    return sqrt(varPop(List, freqList))


# --------------------------------------------------------------------------
# ordering / differences
# --------------------------------------------------------------------------
def SortA(List1, *more):
    """``SortA List1[, List2, ...]`` -- ascending sort.

    TI's ``SortA`` sorts *variables in place* (the syntax has no return value).
    Python cannot rebind the caller's names, so this returns the sorted lists
    and ``SortA_inplace`` writes the result back when you pass a list object.
    """
    return _sort_impl(List1, more, reverse=False)


def SortD(List1, *more):
    """``SortD List1[, List2, ...]`` -- descending sort (see ``SortA``)."""
    return _sort_impl(List1, more, reverse=True)


def _sort_impl(first, more, reverse):
    lists = [first] + _list(more)
    key = _list(lists[0])
    for other in lists[1:]:
        if _len(other) != _len(key):
            raise DimensionMismatchError()
    # voids travel to the bottom in both directions (documented TI behaviour)
    order = _sorted(
        _range(_len(key)),
        key=lambda i: (is_void(key[i]), 0 if is_void(key[i]) else key[i]),
    )
    real = [i for i in order if not is_void(key[i])]
    void = [i for i in order if is_void(key[i])]
    if reverse:
        real = real[::-1]
    idx = real + void
    out = _tuple([other[i] for i in idx] for other in lists)
    return out if _len(lists) > 1 else out[0]


def SortA_inplace(List1, *more):
    """Ascending sort written back into the caller's list objects."""
    res = SortA(List1, *more)
    res = res if _isinstance(res, _tuple) else (res,)
    for target, values in _zip((List1,) + more, res):
        target[:] = _list(values)
    return res[0] if _len(res) == 1 else res


def SortD_inplace(List1, *more):
    """Descending sort written back into the caller's list objects."""
    res = SortD(List1, *more)
    res = res if _isinstance(res, _tuple) else (res,)
    for target, values in _zip((List1,) + more, res):
        target[:] = _list(values)
    return res[0] if _len(res) == 1 else res


def cumulativeSum(List):
    """``cumulativeSum(List)`` -- running totals."""
    if _is_matrix(List):
        out = []
        for col in _columns(List):
            run, acc = [], 0.0
            for v in col:
                acc += v
                run.append(acc)
            out.append(run)
        return _transpose(out)
    run, acc = [], 0.0
    for v in _clean(List):
        acc += v
        run.append(acc)
    return run


def _transpose(cols):
    return [[c[i] for c in cols] for i in _range(_len(cols[0]))] if cols else []


def ΔList(List):
    """``ΔList(List)`` -- successive differences (TI's delta-list operator)."""
    vals = _list(List)
    return [_float(vals[i + 1]) - _float(vals[i]) for i in _range(_len(vals) - 1)]


#: ASCII twin, because ``►`` cannot appear in a Python identifier.
def freqTable_to_list(List, freqIntegerList):
    """``freqTable►list(List,freqIntegerList)`` -- expand a frequency table."""
    vals, freqs = strip_void(List, freqIntegerList)
    if _len(vals) != _len(freqs):
        raise DimensionMismatchError()
    out = []
    for v, f in _zip(vals, freqs):
        fi = _int(f)
        if fi != f or fi < 0:
            raise DomainError("frequency list must contain non-negative integers")
        out.extend([_float(v)] * fi)
    return out


def frequency(List, binsList):
    """``frequency(List,binsList)`` -- counts in ``len(binsList)+1`` bins."""
    vals = _clean(List)
    bins = _clean(binsList)
    out = []
    below = _sum(1 for v in vals if v <= bins[0]) if bins else 0
    out.append(below)
    for lo, hi in _zip(bins, bins[1:]):
        out.append(_sum(1 for v in vals if lo < v <= hi))
    if bins:
        out.append(_sum(1 for v in vals if v > bins[-1]))
    return out


def corrMat(*lists):
    """``corrMat(List1,List2,...)`` -- correlation matrix of the columns."""
    cols = [_clean(c) for c in lists]
    if _len(cols) < 2:
        raise ArgumentError("corrMat needs at least two lists")
    n = _len(cols[0])
    if any(_len(c) != n for c in cols):
        raise DimensionMismatchError()
    out = []
    for a in cols:
        row = []
        for b in cols:
            ma, mb = weighted_mean(a, [1] * n), weighted_mean(b, [1] * n)
            sab = _sum((x - ma) * (y - mb) for x, y in _zip(a, b))
            saa = _sum((x - ma) ** 2 for x in a)
            sbb = _sum((y - mb) ** 2 for y in b)
            row.append(sab / sqrt(saa * sbb))
        out.append(row)
    return out


# ``stdev`` / ``stdDev`` / ``variance`` deliberately do *not* live here.
# They are not TI-Nspire names, so they belong in exactly one place --
# ``legacy.BINDINGS`` -- and defining them here as well is how a package ends up
# with two answers to "what does ``stdev`` do".  ``legacy.stdev`` forwards to
# :func:`stDevSamp`.

