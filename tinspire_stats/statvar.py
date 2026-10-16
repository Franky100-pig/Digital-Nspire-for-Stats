"""The ``stat.`` variable group and the ``RegEqn`` object.

On a TI-Nspire every statistics calculation parks its answer in one global
*results variable* called ``stat.results``.  You then read the pieces with
dotted names -- ``stat.Q1X``, ``stat.Σx``, ``stat.σx``, ``stat.r²`` -- and
``CopyVar stat.RegEqn,f1`` promotes the fitted equation into a real function.

This module reproduces that exactly:

    >>> from tinspire_stats import OneVar, stat
    >>> _ = OneVar([1, 2, 3, 4])
    >>> stat.v
    2.5
    >>> stat.Σx
    10.0
    >>> getattr(stat, "Σx²")
    30.0
    >>> len(stat.results)
    12
    >>> stat.results.name_value_pairs()[0]
    ('v', 2.5)
"""

from __future__ import annotations

from ._core import (
    _float,
    _int,
    _isinstance,
    _len,
    _list,
    _max,
    _print,
    _str,
    _sum,
    _tuple,
    _type,
    ArgumentError,
    TIError,
)

# --------------------------------------------------------------------------
# The names TI documents for the stat. group.
# Source: reference-guide page "S" -> stat.results (the table of variable names
# used for statistical analysis).
# --------------------------------------------------------------------------
DOCUMENTED_STAT_NAMES = frozenset(
    """
    a AdjR² b b0 b1 b2 b3 b4 b5 b6 b7 b8 b9 b10 bList χ² c CLowerList CompList
    CompMatrix CookDist CLower CUpper d dfDenom dfBlock dfCol dfError dfInteract
    dfReg dfNumer dfRow DW e ExpMatrix F FBlock Fcol FInteract FreqReg Frow
    Leverage LowerPred LowerVal m MaxX MaxY ME MedianX MedianY MEPred MinX MinY MS
    MSBlock MSCol MSError MSInteract MSReg MSRow n Ç Ç1 Ç2 ÇDiff PList PVal
    PValBlock PValCol PValInteract PValRow Q1X Q1Y Q3X Q3Y r r² RegEqn Resid
    ResidTrans σx σy σx1 σx2 Σx Σx² Σxy Σy Σy² s SE SEList SEPred sResid SEslope
    sp SS SSBlock SSCol SSX SSY SSError SSInteract SSReg SSRow tList UpperPred
    UpperVal v v1 v2 vDiff vList XReg XVal XValList w y yList YReg
    """.split()
)

#: The reference guide prints the same variable two ways on different pages.
#: Both spellings are resolved here; the value on the right is what we emit.
#:
#: Three distinct causes, all real:
#:
#: 1. **Web-rendered superscripts.**  ``stat.Σx²`` is printed ``stat.Σx2`` in the
#:    per-function tables because the HTML table lost the superscript.  Same for
#:    ``Σy²``, ``χ²``, ``AdjR²``.
#: 2. **Typographic twins.**  ``stat.r²`` vs ``stat.r2``, ``stat.P Value`` vs
#:    ``stat.PVal``, ``stat.ExpMat`` vs ``stat.ExpMatrix``.
#: 3. **Reference-guide edition drift.**  The printed Reference Guide says
#:    ``stat.MedY`` where the current online guide says ``stat.MedianY``, and
#:    ``stat.Frow`` where the online guide says ``stat.FRow``.
DUPLICATE_SPELLINGS = {
    "ExpMat": "ExpMatrix",
    "CompMat": "CompMatrix",
    "MedY": "MedianY",
    "P Value": "PVal",
    "LowerrPred": "LowerPred",
    "Sigmax": "Σx",
    "x2": "Σx²",
    "Σx2": "Σx²",
    "Sigmay2": "Σy²",
    "Σy2": "Σy²",
    "r2": "r²",
    "AdjR2": "AdjR²",
    "χ2": "χ²",
    "Frow": "FRow",
    "p-value": "PVal",
}

#: Extra names the guide's output tables use that are not in the master list
#: above (per-function tables occasionally disagree with the master table).
EXTRA_STAT_NAMES = frozenset(
    """
    sx sy sx1 sx2 σx1 σx2 σ x1_bar x2_bar x1 x2 x1-x2 v1-v2 Sp SpList yList1
    xbarlist CLowerList CUpperList df df_slope z x r1 r2 p0 R2 AdjR2
    Σ(x-v)2 Σ(y-w)2 yhat
    """.split()
)

#: ASCII accessor names -- a convenience extension, *not* a TI-Nspire name.
#: ``stat["Sigmax"]`` == ``stat["Σx"]``.  Handy when a Unicode identifier is
#: awkward in the surrounding code.
ASCII_ALIASES = {
    "xbar": "v",
    "ybar": "w",
    "Sigmax": "Σx",
    "Sigmax2": "Σx²",
    "Sigmay": "Σy",
    "Sigmay2": "Σy²",
    "Sigmaxy": "Σxy",
    "Sigmaxv2": "Σ(x-v)2",
    "Sigmayw2": "Σ(y-w)2",
    "sigmax": "σx",
    "sigmay": "σy",
    "pbar": "Ç",
    "pbar1": "Ç1",
    "pbar2": "Ç2",
    "pbarDiff": "ÇDiff",
    "chi2": "χ²",
    "R2": "R2",
}


def canonical(name: str) -> str:
    """Resolve a user-typed spelling to the name we actually store."""
    if name in DUPLICATE_SPELLINGS:
        return DUPLICATE_SPELLINGS[name]
    if name in ASCII_ALIASES:
        return ASCII_ALIASES[name]
    # lenient fallback: ignore case and internal spaces
    flat = name.replace(" ", "").lower()
    for known in list(DOCUMENTED_STAT_NAMES) + list(EXTRA_STAT_NAMES):
        if known.replace(" ", "").lower() == flat:
            return known
    return name


def _tifmt(v) -> str:
    """A number the way the calculator writes it inside a regression equation.

    Ten significant digits, and a decimal point even for a whole number -- which
    is why ``LinRegMx([1,2,3,4,5],[5,8,11,14,17])`` prints ``y=3.·x+2.`` rather
    than ``y=3·x+2``.
    """
    text = f"{v:.10g}"
    if "e" in text or "E" in text or "." in text:
        return text
    return text + "."


class RegEqn:
    """A regression equation, like the one ``stat.RegEqn`` holds.

    ``str()`` gives the *evaluated* equation in TI's notation -- ten significant
    digits, and a trailing decimal point on a whole number, which is how the
    calculator prints it.  ``.symbolic`` gives the template the reference guide
    shows (``y = m·x+b``); ``.coeffs`` / ``to_dict()`` hold the plain numbers.
    Calling the object evaluates it::

        >>> from tinspire_stats import LinRegMx, stat
        >>> _ = LinRegMx([1,2,3,4,5],[5,8,11,14,17])
        >>> stat.RegEqn(6)
        20.0
        >>> str(stat.RegEqn)
        'y=3.·x+2.'
        >>> stat.RegEqn.symbolic
        'y = m·x+b'
    """

    __slots__ = ("kind", "coeffs", "symbolic", "freq_names", "_f")

    def __init__(self, kind: str, coeffs: dict, symbolic: str, freq_names=None):
        self.kind = kind
        self.coeffs = dict(coeffs)
        self.symbolic = symbolic
        self.freq_names = freq_names or {}
        self._f = self._make()

    def _make(self):
        k = self.kind
        c = self.coeffs
        if k == "LinRegMx":
            return lambda x: c["m"] * x + c["b"]
        if k == "LinRegBx":
            return lambda x: c["a"] + c["b"] * x
        if k == "QuadReg":
            return lambda x: c["a"] * x * x + c["b"] * x + c["c"]
        if k == "CubicReg":
            return lambda x: c["a"] * x**3 + c["b"] * x * x + c["c"] * x + c["d"]
        if k == "QuartReg":
            return lambda x: (
                c["a"] * x**4 + c["b"] * x**3 + c["c"] * x * x + c["d"] * x + c["e"]
            )
        if k == "LnReg":
            from math import log

            return lambda x: c["a"] + c["b"] * log(x)
        if k == "ExpReg":
            return lambda x: c["a"] * c["b"] ** x
        if k == "PowerReg":
            return lambda x: c["a"] * x ** c["b"]
        if k == "MedMed":
            return lambda x: c["m"] * x + c["b"]
        if k == "Logistic":
            from math import exp

            return lambda x: c["c"] / (1 + c["a"] * exp(-c["b"] * x))
        if k == "LogisticD":
            from math import exp

            return lambda x: c["c"] / (1 + c["a"] * exp(-c["b"] * x)) + c["d"]
        if k == "SinReg":
            from math import sin

            return lambda x: c["a"] * sin(c["b"] * x + c["c"]) + c["d"]
        if k == "MultReg":
            names = [n for n in c if n.startswith("b")]
            names.sort(key=lambda s: int(s[1:]))
            return lambda *xs: c["b0"] + _sum(
                c[n] * x for n, x in zip(names[1:], xs)
            )
        raise ArgumentError(f"no evaluator for {k}")

    def __call__(self, *args):
        if _len(args) == 1:
            return self._f(args[0])
        return self._f(*args)

    def _evaluated(self) -> str:
        k = self.kind
        c = self.coeffs

        def f(v):
            return _tifmt(v)

        if k == "LinRegMx":
            return f"y={f(c['m'])}·x+{f(c['b'])}"
        if k == "LinRegBx":
            return f"y={f(c['a'])}+{f(c['b'])}·x"
        if k == "QuadReg":
            return f"y={f(c['a'])}·x²+{f(c['b'])}·x+{f(c['c'])}"
        if k == "CubicReg":
            return f"y={f(c['a'])}·x³+{f(c['b'])}·x²+{f(c['c'])}·x+{f(c['d'])}"
        if k == "QuartReg":
            return (
                f"y={f(c['a'])}·x⁴+{f(c['b'])}·x³+{f(c['c'])}·x²"
                f"+{f(c['d'])}·x+{f(c['e'])}"
            )
        if k == "LnReg":
            return f"y={f(c['a'])}+{f(c['b'])}·ln(x)"
        if k == "ExpReg":
            return f"y={f(c['a'])}·({f(c['b'])})^x"
        if k == "PowerReg":
            return f"y={f(c['a'])}·(x)^{f(c['b'])}"
        if k == "MedMed":
            return f"y={f(c['m'])}·x+{f(c['b'])}"
        if k == "Logistic":
            return f"y=({f(c['c'])})/(1+{f(c['a'])}·e^(-{f(c['b'])}x))"
        if k == "LogisticD":
            return (
                f"y=({f(c['c'])})/(1+{f(c['a'])}·e^(-{f(c['b'])}x))+{f(c['d'])}"
            )
        if k == "SinReg":
            return (
                f"y={f(c['a'])}·sin({f(c['b'])}x+{f(c['c'])})+{f(c['d'])}"
            )
        if k == "MultReg":
            names = _list(c)
            names.sort(key=lambda s: int(s[1:]))
            parts = [f(c["b0"])]
            for i, n in enumerate(names[1:], start=1):
                parts.append(f"{f(c[n])}·x{i}")
            return "y=" + "+".join(parts)
        return self.symbolic

    def __str__(self) -> str:
        return self._evaluated()

    def __repr__(self) -> str:
        return f"RegEqn({self.symbolic!r}, {self._evaluated()})"

    def to_dict(self) -> dict:
        return dict(self.coeffs)


class StatResults:
    """What ``stat.results`` is: a list of name/value pairs."""

    def __init__(self, items):
        self.items = _list(items)

    def name_value_pairs(self):
        return _list(self.items)

    def __len__(self):
        return _len(self.items)

    def __iter__(self):
        return iter(self.items)

    def __str__(self) -> str:
        if not self.items:
            return "stat.results (empty)"
        width = _max(_len(f"stat.{k}") for k, _ in self.items)
        lines = ["stat.results"]
        for k, v in self.items:
            lines.append(f"  {('stat.' + k).ljust(width)}  {_fmt(v)}")
        return "\n".join(lines)

    __repr__ = __str__


def _fmt(v) -> str:
    if _isinstance(v, float):
        return f"{v:.6f}".rstrip("0").rstrip(".") if v != int(v) else f"{int(v)}.0"
    if _isinstance(v, list):
        return "{" + ",".join(_fmt(x) for x in v) + "}"
    if _isinstance(v, RegEqn):
        return str(v)
    return _str(v)


class StatGroup:
    """The global ``stat.`` variable group.

    Attribute access mirrors the calculator (``stat.Q1X``).  ``stat.results``
    and ``stat.values`` are attributes rather than methods, exactly as on the
    handheld, where both are *variables* you type by name.
    """

    def __init__(self):
        object.__setattr__(self, "_d", {})
        object.__setattr__(self, "_order", [])
        object.__setattr__(self, "results", StatResults([]))
        object.__setattr__(self, "values", [])

    # -- population --------------------------------------------------------
    def publish(self, mapping: dict) -> "StatGroup":
        """Replace the group with the results of the latest calculation."""
        self._d.clear()
        self._order.clear()
        for k, v in mapping.items():
            self._d[k] = v
            self._order.append(k)
        object.__setattr__(self, "results", StatResults([(k, self._d[k]) for k in self._order]))
        # stat.values: the same numbers, names stripped off
        vals = []
        for k in self._order:
            v = self._d[k]
            if _isinstance(v, (int, float)) and not _isinstance(v, bool):
                vals.append(_float(v))
        object.__setattr__(self, "values", vals)
        return self

    def update(self, mapping: dict) -> "StatGroup":
        """Add results without clearing (used by the multi-list forms)."""
        for k, v in mapping.items():
            if k not in self._d:
                self._order.append(k)
            self._d[k] = v
        object.__setattr__(self, "results", StatResults([(k, self._d[k]) for k in self._order]))
        object.__setattr__(
            self,
            "values",
            [_float(self._d[k]) for k in self._order if _isinstance(self._d[k], float)],
        )
        return self

    # -- reading -----------------------------------------------------------
    def __getattr__(self, name):
        d = object.__getattribute__(self, "_d")
        if name in d:
            return d[name]
        c = canonical(name)
        if c in d:
            return d[c]
        raise AttributeError(
            f"'stat' has no result '{name}' (current results: "
            + ", ".join(d) + ")"
        )

    def __getitem__(self, name):
        return getattr(self, name)

    def __contains__(self, name):
        return name in self._d or canonical(name) in self._d

    def __iter__(self):
        return iter(self._order)

    def keys(self):
        return _list(self._order)

    def items(self):
        return [(k, self._d[k]) for k in self._order]

    def get(self, name, default=None):
        try:
            return self[name]
        except AttributeError:
            return default

    def as_dict(self) -> dict:
        """Plain dict with TI names as keys (Unicode kept)."""
        return {k: self._d[k] for k in self._order}

    def as_ascii(self) -> dict:
        """Plain dict with ASCII-only keys -- see ``ASCII_ALIASES``."""
        from .catalog import ascii_name

        return {ascii_name(k): self._d[k] for k in self._order}

    def __repr__(self) -> str:
        return f"StatGroup({', '.join(self._order)})"


#: The one and only results group, just like on the calculator.
stat = StatGroup()

#: ``stat1.``, ``stat2.``, ... -- the Lists & Spreadsheet app copies the group
#: after every calculation so earlier results survive.  ``copy_to_stat_group``
#: reproduces that.
_stat_groups: dict = {}


def copy_to_stat_group(n: int | None = None) -> StatGroup:
    n = (n if n is not None else _len(_stat_groups) + 1)
    g = StatGroup().publish(stat.as_dict())
    _stat_groups[n] = g
    return g


#: Variables created with CopyVar (``CopyVar stat.RegEqn,f1``).
VarStore: dict = {}


def CopyVar(source, target: str):
    """``CopyVar Var1,Var2`` -- copy a value or a whole variable group."""
    if _isinstance(source, StatGroup):
        g = StatGroup().publish(source.as_dict())
        VarStore[target.rstrip(".") + "."] = g
        return g
    if _isinstance(target, _str):
        VarStore[target] = source
    else:  # CopyVar Var1.,Var2.
        VarStore[target] = source
    return source


def publish(mapping: dict) -> StatGroup:
    """Internal: hand a result dict to the global ``stat`` group."""
    return stat.publish(mapping)
