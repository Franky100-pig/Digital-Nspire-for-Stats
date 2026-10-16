"""The TI-name catalogue: spellings, ASCII twins, and a machine-readable function list.

Two jobs:

1. ``ascii_name`` -- turn a name full of calculator typography (``Σx²``, ``ÇDiff``,
   ``χ²``) into something you can type on a US keyboard.  ``stat.as_ascii()``
   uses it.
2. ``catalog()`` -- walk the package and produce one record per TI function,
   taking the signature line straight out of the function's own docstring so the
   catalogue can never drift from the code.

Nothing in here is part of the calculator's behaviour; it is the map.
"""

from __future__ import annotations

import importlib
import inspect
from builtins import sorted as _sorted

from . import legacy as _legacy
from . import menu as _menu
from .statvar import ASCII_ALIASES

#: The quarantined names, re-exported from :mod:`legacy` rather than kept as a
#: second hand-maintained list.
LEGACY_TI84_NAMES = _legacy.NAMES

__all__ = [
    "ASCII_ONLY",
    "LEGACY_KINDS",
    "LEGACY_TI84_NAMES",
    "MENU",
    "NOT_NSPIRE",
    "NOT_TI",
    "OFF_MENU",
    "TI_SPELLING_OVERRIDES",
    "ascii_name",
    "catalog",
    "lookup",
    "menu_tree",
    "pretty_catalog",
]

#: Transliteration used when a name has no hand-written ASCII twin.
_TRANSLIT = {
    "Σ": "Sigma",
    "σ": "sigma",
    "χ": "chi",
    "Δ": "Delta",
    "Ç": "pbar",
    "μ": "mu",
    "λ": "lambda",
    "π": "pi",
    "θ": "theta",
    "ρ": "rho",
    "α": "alpha",
    "β": "beta",
    "ω": "omega",
    "²": "2",
    "³": "3",
    "⁴": "4",
    "ˣ": "x",
    "ᵇ": "b",
    "·": "*",
    "×": "*",
    "►": "_to_",
    "→": "->",
    "≠": "!=",
    "≤": "<=",
    "≥": ">=",
    "√": "sqrt",
    "∞": "inf",
}

#: Reverse of ``statvar.ASCII_ALIASES``: preferred ASCII twin for a TI name.
_ASCII_TWIN = {}
for _alias, _target in ASCII_ALIASES.items():
    _ASCII_TWIN.setdefault(_target, _alias)

#: Names where mechanical transliteration would invent a spelling that does not
#: exist.  ``χ`` -> ``chi`` would turn ``invχ²`` into ``invchi2``, but the name
#: this package actually exports is ``invChi2``.  Anything listed here is
#: guaranteed to come out as something you can import.
_ASCII_TWIN.update({
    "χ²Pdf": "chi2Pdf",
    "χ²Cdf": "chi2Cdf",
    "invχ²": "invChi2",
    "invχ2": "invChi2",
    "χ²": "chi2",
    "χ²GOF": "chi2GOF",
    "χ²2way": "chi22way",
    "freqTable►list": "freqTable_to_list",
})

#: Names whose Python identifier differs from what the document prints.
TI_SPELLING_OVERRIDES = {
    "chi2GOF": "χ²GOF",
    "chi22way": "χ²2way",
    "chi2GOFTest": "χ²GOF",
    "χ2Pdf": "χ²Pdf",
    "χ2Cdf": "χ²Cdf",
    "invχ2": "invχ²",
    "freqTable_to_list": "freqTable►list",
    "ΔList": "ΔList",
    "poissPdf": "poissPdf",
}

#: Public callables in the package that are *not* TI-Nspire functions at all
#: (numerical machinery, plus a few genuinely useful extras).  Every entry here
#: is something the package needs internally -- none of them is a name you can
#: type on the handheld.
NOT_TI = frozenset("""
    ascii_name betainc catalog gammainc gammainc_upper_cf get_quartile_method
    lookup make_criteria menu_tree pretty_catalog set_quartile_method
    five_numbers chi2GOFTest ti_spelling canonical copy_to_stat_group publish
    is_void strip_void as_list check_integer_freq pair_up weighted_mean
    weighted_ss solve solve_normal_equations norm_sf floor_int safe_sqrt
""".split())

#: Everything that is not a plain TI-Nspire catalog name.  Built from
#: :mod:`legacy`'s registry instead of from a second hand-kept list, so the two
#: cannot drift apart.
#:
#: Note what is deliberately *absent*: ``legacy.DOCUMENTED_VARIANTS`` --
#: ``chi2Pdf``, ``chi2Cdf``, ``invChi2``.  The reference guide prints those
#: spellings itself, so they are TI-Nspire names, and extra labelling does not
#: make them not-TI names.
NOT_NSPIRE = NOT_TI | LEGACY_TI84_NAMES

#: The standings a name can have, most faithful first.  ``catalog()`` only ever
#: emits the three coarse kinds; ``legacy_kind`` carries the precise one.
LEGACY_KINDS = _legacy.KINDS

#: The device's menus, by breadcrumb path.  Built from
#: :mod:`tinspire_stats.menu` rather than written out a second time, because a
#: second copy is a second thing to be wrong.  The hand-written version this
#: replaces filed ``countif`` under List Math and split Distributions into
#: Continuous and Discrete; the handheld does neither.
MENU: dict = {}
for _path, _crumb, _item in _menu.menu_paths("calculator"):
    if not _item.function or _item.function == _menu.STAT_RESULTS:
        continue  # categories outside statistics, and the stat.results variable
    MENU.setdefault(" > ".join(_crumb[1:]), []).append(_item.function)
del _path, _crumb, _item

#: Names with no entry in the menus above: reached by typing them, or living in
#: a branch of the handheld this package does not cover.  Kept out of ``MENU``
#: on purpose -- filing a name under a menu it is not on is the mistake this
#: split exists to prevent.
OFF_MENU = {
    # Probability > Random is a real submenu.  The package's own menu marks the
    # whole Probability branch unsupported, so these have no front door here.
    "Probability > Random": [
        "RandSeed", "rand", "randInt", "randNorm", "randBin", "randSamp",
    ],
    "Typed, no menu item of their own": [
        "FiveNumSummary", "invBinom", "invBinomN",
        "count", "countif", "sumIf", "frequency", "freqTable_to_list",
    ],
    "Catalog": ["CopyVar", "copy_to_stat_group"],
}

_MODULES = [
    ("_core", None),
    ("statvar", None),
    ("listmath", "Statistics > List Math"),
    ("summary", "Statistics > Stat Calculations"),
    ("regress", "Statistics > Stat Calculations"),
    ("distributions", "Statistics > Distributions"),
    ("inference", "Statistics > Confidence Intervals / Stat Tests"),
]

#: Models whose fit is iterative on the real handheld -- see README's fidelity
#: table.  The names are honest about it.
ITERATIVE = frozenset({"Logistic", "LogisticD", "SinReg"})


def ascii_name(name: str) -> str:
    """ASCII-only twin of a TI name.

    >>> ascii_name("Σx²"), ascii_name("ÇDiff"), ascii_name("χ²")
    ('Sigmax2', 'pbarDiff', 'chi2')
    >>> ascii_name("invχ2"), ascii_name("freqTable►list")
    ('invChi2', 'freqTable_to_list')
    """
    if name in _ASCII_TWIN:
        return _ASCII_TWIN[name]
    out = name
    for src, dst in _TRANSLIT.items():
        out = out.replace(src, dst)
    return "".join(ch if ch.isascii() else f"_u{ord(ch):04x}" for ch in out)


def ti_spelling(name: str) -> str:
    """How the reference guide prints this name (Unicode where it matters)."""
    return TI_SPELLING_OVERRIDES.get(name, name)


def _callables(module):
    for attr, obj in vars(module).items():
        if attr.startswith("_"):
            continue
        if not inspect.isroutine(obj):
            continue  # skips classes, the stat group instance, constants
        if getattr(obj, "__module__", None) != module.__name__:
            continue  # re-export or alias defined elsewhere
        yield attr, obj


def _signature_of(fn) -> str:
    """The first line of a function's docstring, which is its TI signature."""
    doc = (fn.__doc__ or "").strip()
    return doc.splitlines()[0].strip() if doc else ""


def _row(name, module_name, kind, signature, *, legacy_kind=None, evidence=""):
    return {
        "name": name,
        "ti": ti_spelling(name),
        "ascii": ascii_name(name),
        "signature": signature,
        "module": module_name,
        "kind": kind,
        #: Set only when ``kind == "legacy"``: which of the five standings the
        #: name actually has.  A bare "legacy" would lump ``chi2Pdf`` (a name TI
        #: prints) in with ``stdev`` (a name TI does not have).
        "legacy_kind": legacy_kind,
        #: Why the classification is what it is -- a quote from the guide, or an
        #: explicit admission that the name is ours.
        "evidence": evidence,
        "fidelity": (
            "iterative" if name in ITERATIVE
            else "exact" if kind == "ti"
            else "n/a"
        ),
    }


def catalog():
    """Every public callable, with its signature line and provenance.

    Returns a list of dicts sorted by module and name::

        [{'name': 'OneVar', 'ti': 'OneVar', 'ascii': 'OneVar',
          'signature': 'OneVar X[,[Freq][,Category,Include]] ...',
          'module': 'tinspire_stats.summary',
          'kind': 'ti' | 'legacy' | 'internal',
          'legacy_kind': None | 'not a TI-Nspire name' | ...,
          'evidence': '',
          'fidelity': 'exact' | 'iterative' | 'n/a'}, ...]

    Every quarantined name gets exactly one row.  Some are defined in the
    implementation modules and some are built on demand by ``legacy``; filing
    only the first group used to mean ``Fpdf`` and ``PwrReg`` were missing from
    the catalogue while ``stdev`` was present, which is a difference with no
    meaning behind it.
    """
    rows: list = []
    seen: set = set()

    def emit(name, module_name, kind, signature, **kw):
        if name in seen:
            return
        seen.add(name)
        rows.append(_row(name, module_name, kind, signature, **kw))

    for modname, _menu in _MODULES:
        mod = importlib.import_module(f".{modname}", __package__)
        for attr, obj in _callables(mod):
            where = f"{__package__}.{modname}"
            if attr in NOT_TI:
                emit(attr, where, "internal", _signature_of(obj))
            elif attr in LEGACY_TI84_NAMES:
                info = _legacy.BINDINGS[attr]
                emit(attr, where, "legacy", _signature_of(obj),
                     legacy_kind=info["kind"], evidence=info["evidence"])
            else:
                emit(attr, where, "ti", _signature_of(obj))

    for name in _sorted(LEGACY_TI84_NAMES):
        info = _legacy.BINDINGS[name]
        target = getattr(info["module"], info["target"])
        emit(name, f"{__package__}.legacy", "legacy", _signature_of(target),
             legacy_kind=info["kind"], evidence=info["evidence"])

    return _sorted(rows, key=lambda r: (r["module"], r["name"].lower()))


def lookup(name: str):
    """Find the function behind a TI name, an ASCII twin, or a Python name.

    Falls back to :mod:`legacy`, so ``lookup("stdev")`` finds ``stDevSamp``
    while still reporting that ``stdev`` is not the name TI uses::

        >>> lookup("OneVar").__name__
        'OneVar'
        >>> lookup("stdev").__name__
        'stDevSamp'
    """
    for modname, _m in _MODULES:
        mod = importlib.import_module(f".{modname}", __package__)
        for attr, obj in _callables(mod):
            if attr == name or ti_spelling(attr) == name or ascii_name(attr) == name:
                return obj
    try:
        return getattr(_legacy, name)
    except AttributeError:
        raise KeyError(name) from None



def menu_tree():
    """``MENU`` with every entry resolved to the live function object.

    The paths are the device's own, and the order is the order the menu prints,
    so this doubles as an answer to "what would I press to get to X" -- see
    :func:`tinspire_stats.menu.resolve` for the numbered walk.
    """
    return {path: [lookup(n) for n in names] for path, names in MENU.items()}


def pretty_catalog(*, kind="ti") -> str:
    """A readable catalogue, suitable for pasting into a README.

    ``kind="ti"`` is the default view -- the names you can find on the handheld.
    ``kind="legacy"`` groups by how far each spelling is from the guide, most
    faithful first, instead of flattening everything into one bucket::

        >>> heads = [l for l in pretty_catalog(kind="legacy").splitlines()
        ...          if l.startswith("--")]
        >>> heads[0]
        '-- keyboard spelling, not in the guide --'
        >>> heads[-1]
        '-- package extension --'
    """
    rows = [r for r in catalog() if kind == "all" or r["kind"] == kind]
    if not rows:
        return ""
    width = max(len(r["ti"]) for r in rows)
    lines: list = []

    if kind == "legacy":
        # Group by *standing*, not by whichever module the name happens to be
        # filed in.  Filing them by module is what made ``Fpdf`` look like a
        # different kind of thing from ``stdev``.
        for standing in LEGACY_KINDS:
            group = [r for r in rows if r["legacy_kind"] == standing]
            if not group:
                continue
            lines.append(f"\n-- {standing} --")
            for r in group:
                lines.append(f"{r['ti'].ljust(width)}  {r['signature']}")
        return "\n".join(lines).lstrip("\n")

    module = None
    for r in rows:
        short = r["module"].rsplit(".", 1)[-1]
        if short != module:
            module = short
            lines.append(f"\n-- {short} --")
        mark = "  (iterative fit)" if r["fidelity"] == "iterative" else ""
        lines.append(f"{r['ti'].ljust(width)}  {r['signature']}{mark}")
    return "\n".join(lines).lstrip("\n")


