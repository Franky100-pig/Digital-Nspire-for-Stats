"""Internal plumbing shared by every tinspire_stats module.

Nothing in here is part of the TI-Nspire function surface -- these are the
mechanics that let the replicated functions behave the way the real
calculator behaves:

* ``TIError`` hierarchy reproducing the calculator's error strings
  ("Domain error", "Dimension mismatch", ...).
* ``VOID`` -- the Nspire's *empty (void) element*.  TI's rule: if element *i*
  of any input list is void, element *i* of **all** the input lists is
  discarded before the calculation runs.
* frequency (``Freq``) list handling, including the quirk that
  ``stDevSamp``/``stDevPop``/``varSamp``/``varPop`` demand **integer**
  frequencies while ``mean`` accepts fractional ones.
* smallest-possible weighted moments.

The module captures references to the builtins it needs *before* any module
defines functions named ``sum``/``min``/``max``, because the public API has to
carry those exact names.
"""

from __future__ import annotations

import builtins as _builtins
from math import isnan, sqrt

# Captured before shadowing.  Every module that defines a TI function named
# after a builtin imports these aliases instead of the builtin.
_sum = _builtins.sum
_min = _builtins.min
_max = _builtins.max
_abs = _builtins.abs
_round = _builtins.round
_len = _builtins.len
_sorted = _builtins.sorted
_list = _builtins.list
_tuple = _builtins.tuple
_float = _builtins.float
_int = _builtins.int
_range = _builtins.range
_enumerate = _builtins.enumerate
_zip = _builtins.zip
_any = _builtins.any
_all = _builtins.all
_isinstance = _builtins.isinstance
_issubclass = _builtins.issubclass
_str = _builtins.str
_type = _builtins.type
_print = _builtins.print


# --------------------------------------------------------------------------
# TI error surface
# --------------------------------------------------------------------------
class TIError(Exception):
    """Base class for every error the Nspire would report.

    ``ti_message`` is the string the handheld actually shows so that a caller
    can pattern-match on calculator behaviour rather than Python behaviour.
    """

    ti_message = "Error"

    def __init__(self, message: str | None = None):
        self.detail = message
        super().__init__(message or self.ti_message)


class DomainError(TIError):
    """e.g. square root of a negative, empty list, zero denominator."""

    ti_message = "Domain error"


class DimensionMismatchError(TIError):
    """The Nspire's "Error: Dimension mismatch" -- unequal list lengths."""

    ti_message = "Dimension mismatch"


class ArgumentError(TIError):
    ti_message = "Argument error"


class DataTypeError(TIError):
    ti_message = "Data type"


class StatError(TIError):
    ti_message = "Stat error"


# --------------------------------------------------------------------------
# void (empty) elements
# --------------------------------------------------------------------------
class _Void:
    """The Nspire's empty element.  Prints as ``void``."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "void"

    __str__ = __repr__

    def __bool__(self) -> bool:  # a void element is not usable as a number
        return False


VOID = _Void()


def is_void(value) -> bool:
    """True for the Nspire's empty element.

    ``None`` is accepted as a spelling of void because that is the natural
    Python idiom; ``nan`` is *not* void (TI keeps nan and void distinct).
    """
    return value is VOID or value is None


def strip_void(*lists):
    """Drop index *i* from **every** list when any list has a void at *i*.

    This is TI's documented rule: "An empty (void) element in any of the lists
    X, Freq, or Category results in a void for the corresponding element of all
    those lists."
    """
    lists = [_list(x) for x in lists]
    if not lists:
        return lists
    n = _len(lists[0])
    if _any(_len(x) != n for x in lists):
        raise DimensionMismatchError()
    keep = [
        i
        for i in _range(n)
        if not _any(is_void(x[i]) for x in lists)
    ]
    return [[x[i] for i in keep] for x in lists]


def as_list(value, name: str = "argument"):
    """Coerce a scalar/list argument to a list; reject non-numeric entries."""
    if _isinstance(value, (list, _tuple, _range)):
        return [_float(v) for v in value if not is_void(v)]
    if _isinstance(value, (int, float)) and not _isinstance(value, bool):
        return [_float(value)]
    raise DataTypeError(f"{name} must be a list or a number, got {_type(value).__name__}")


# --------------------------------------------------------------------------
# frequency handling
# --------------------------------------------------------------------------
def check_integer_freq(freq) -> None:
    """``stDevSamp``/``varPop`` & friends only accept integer frequencies.

    Verified on hardware and reported on the TI forums (2008): ``mean(x, px)``
    happily takes ``px = {0.25, 0.25, 0.25, 0.25}`` while ``stDevSamp(x, px)``
    raises a *Domain error* -- "Both stdevsamp and stdevpop only accept integer
    frequencies."
    """
    for f in freq:
        if is_void(f):
            continue
        if float(f) != int(float(f)) or float(f) < 0:
            raise DomainError("frequency list must contain non-negative integers")


def pair_up(values, freq=None, *, integer_freq: bool, expand: bool):
    """Expand ``values`` by an optional frequency list.

    Returns ``(expanded_values, weights)``.  With ``expand=True`` the returned
    list has one entry per observation (needed for order statistics such as the
    median/quartiles); otherwise the (value, weight) pairs are returned as-is.

    Void elements are removed *by index* across both lists -- dropping them from
    each list independently would silently re-pair the survivors and turn a
    ``{1,void,3}`` / ``{1,2,void}`` call into a scrambled ``{1,3}`` / ``{2}``.
    """
    if freq is None:
        values = [_float(v) for v in values if not is_void(v)]
        return values, [1.0] * _len(values)
    values, freq = strip_void(values, freq)
    values = [_float(v) for v in values]
    freq = [_float(f) for f in freq]
    if integer_freq:
        check_integer_freq(freq)
    if expand:
        out = []
        for v, f in _zip(values, freq):
            out.extend([v] * _int(f))
        return out, [1.0] * _len(out)
    return values, freq


def weighted_mean(values, weights) -> float:
    total = _sum(weights)
    if total == 0:
        raise DomainError()
    return _sum(v * w for v, w in _zip(values, weights)) / total


def weighted_ss(values, weights, mean: float) -> float:
    """Sum of squares of deviations from the weighted mean."""
    return _sum(w * (v - mean) ** 2 for v, w in _zip(values, weights))


# --------------------------------------------------------------------------
# tiny linear algebra (keeps the package free of numpy)
# --------------------------------------------------------------------------
def solve(a, b):
    """Solve ``a @ x = b`` by Gauss-Jordan with partial pivoting."""
    n = _len(a)
    if n == 0:
        raise DomainError()
    m = _len(a[0])
    if m != n:
        raise DomainError("system is not square")
    aug = [[_float(a[i][j]) for j in _range(m)] + [_float(b[i])] for i in _range(n)]
    for col in _range(n):
        piv = _max(_range(col, n), key=lambda r: _abs(aug[r][col]))
        if _abs(aug[piv][col]) < 1e-300:
            raise DomainError("singular system")
        if piv != col:
            aug[col], aug[piv] = aug[piv], aug[col]
        p = aug[col][col]
        aug[col] = [v / p for v in aug[col]]
        for r in _range(n):
            if r == col:
                continue
            f = aug[r][col]
            if f:
                aug[r] = [x - f * y for x, y in _zip(aug[r], aug[col])]
    return [aug[i][n] for i in _range(n)]


def solve_normal_equations(design, y, weights=None):
    """Weighted least squares: minimise ``sum w_i (design_i . beta - y_i)**2``."""
    n = _len(design)
    p = _len(design[0]) if n else 0
    w = weights or [1.0] * n
    ata = [[0.0] * p for _ in _range(p)]
    atb = [0.0] * p
    for i in _range(n):
        wi = w[i]
        row = design[i]
        for j in _range(p):
            atb[j] += wi * row[j] * y[i]
            for k in _range(p):
                ata[j][k] += wi * row[j] * row[k]
    return solve(ata, atb)


def norm_sf(z: float) -> float:
    """P(Z > z) for the standard normal -- used by the test statistics."""
    from .distributions import normCdf

    return 1.0 - normCdf(-9e999, z)


def floor_int(x) -> int:
    return _int(x)


def safe_sqrt(x: float) -> float:
    if x < 0 and not isnan(x):
        raise DomainError()
    return sqrt(x)
