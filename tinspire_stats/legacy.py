"""Not-quite-TI names, labelled honestly.

Five groups live here.  They are **not** interchangeable, and the whole point of
this module is that it says which is which -- a single "these are aliases" bucket
would be a lie, because the aliases have completely different standing.

``DOCUMENTED_VARIANTS``  (exempt from quarantine)
    Spellings that the reference guide itself prints.  ``χ2Pdf``'s entry prints
    *both* ``χ2Pdf(XVal,df)`` and ``chi2Pdf(XVal,df)``, so ``chi2Pdf`` is a real
    TI-Nspire name, not a convenience.  These are listed here for documentation;
    they are also reachable from the package root.

``KEYBOARD``
    Typographic near-misses of a real name that the guide never prints --
    ``invT`` for ``invt``, ``Fpdf`` for ``FPdf``.  Convenient, but not TI's.

``RETIRED``
    Names that are not TI-Nspire at all.  ``stdev(`` is not a Nspire catalog
    name (the Nspire spells it ``stDevSamp(``); it is kept because it is the
    spelling a reader reaches for first.

``MENU``
    Words the calculator itself puts on screen -- the Confidence Intervals and
    Stat Tests menus read "2-Sample t Test" -- even though the *catalog* name
    behind that label is ``tTest_2Samp``.  Faithful to the screen, not to the
    catalog.

``EXTENSION``
    Additions this package makes that have no TI counterpart at all.
    ``SortA_inplace`` exists because TI's ``SortA`` rebinds the caller's
    variables while Python cannot.

Everything in ``KEYBOARD``, ``RETIRED``, ``MENU`` and ``EXTENSION`` is
quarantined: it is reachable as an attribute of this module and nowhere else.
``DOCUMENTED_VARIANTS`` is not quarantined, because those names are TI's::

    >>> from tinspire_stats import legacy
    >>> legacy.stdev.__name__          # which real function answers
    'stDevSamp'
    >>> legacy.kind_of("stdev")
    'not a TI-Nspire name'
    >>> legacy.kind_of("chi2Pdf")
    'documented variant'
    >>> legacy.counts()["not a TI-Nspire name"]
    4
"""

from __future__ import annotations

from . import distributions as _dist
from . import inference as _inf
from . import listmath as _list
from . import regress as _reg

__all__ = [
    "BINDINGS",
    "DOCUMENTED_VARIANTS",
    "EVIDENCE",
    "KINDS",
    "NAMES",
    "NOTES",
    "counts",
    "evidence",
    "evidence_table",
    "kind_of",
    "notes",
    "table",
]


class Kind:
    """The five standings a non-primary spelling can have.

    The strings are what gets printed, so they read as sentences rather than as
    database codes -- this table ends up in the README.
    """

    DOCUMENTED = "documented variant"
    KEYBOARD = "keyboard spelling, not in the guide"
    RETIRED = "not a TI-Nspire name"
    MENU = "TI-Nspire menu label, not the catalog name"
    EXTENSION = "package extension"


#: Every kind, in the order the README table uses.
KINDS = (
    Kind.DOCUMENTED,
    Kind.KEYBOARD,
    Kind.RETIRED,
    Kind.MENU,
    Kind.EXTENSION,
)

#: Kinds that are quarantined: not reachable from the package root.
QUARANTINED = frozenset({Kind.KEYBOARD, Kind.RETIRED, Kind.MENU, Kind.EXTENSION})


# --------------------------------------------------------------------------
# DOCUMENTED_VARIANTS -- the guide prints these spellings itself
# --------------------------------------------------------------------------
#: ``name -> (primary name, evidence)``.  These are **TI-Nspire names**, so they
#: are deliberately *not* in :data:`BINDINGS` and not quarantined.
DOCUMENTED_VARIANTS: dict = {}


def _documented(name, primary, evidence, module, target):
    DOCUMENTED_VARIANTS[name] = {
        "kind": Kind.DOCUMENTED,
        "primary": primary,
        "module": module,
        "target": target,
        "evidence": evidence,
    }


# The C page's χ2Pdf and χ2Cdf entries each print two signature lines, the
# second one in ASCII.  Verified against the guide's own HTML.
_documented(
    "chi2Pdf", "χ2Pdf",
    "Reference guide, page C: the χ2Pdf entry prints both "
    "‘χ2Pdf(XVal,df)’ and ‘chi2Pdf(XVal,df)’.",
    _dist, "χ2Pdf",
)
_documented(
    "chi2Cdf", "χ2Cdf",
    "Reference guide, page C: the χ2Cdf entry prints both "
    "‘χ2Cdf(lowBound,upBound,df)’ and ‘chi2Cdf(lowBound,upBound,df)’.",
    _dist, "χ2Cdf",
)
_documented(
    "invChi2", "invχ2",
    "Reference guide, page I: the invχ2 entry prints ‘invχ2(Area,df)’ and "
    "‘invChi2(Area,df)’ together.",
    _dist, "invχ2",
)
_documented(
    "χ2GOF", "χ²GOF",
    "Reference guide, page C: the entry is listed as ‘χ2GOF’ with the two "
    "superscripted, i.e. χ²GOF; the same entry adds the columns of the "
    "observed and expected lists.",
    _inf, "chi2GOF",
)
_documented(
    "χ22way", "χ²2way",
    "Reference guide, page C: listed as ‘χ22way’, i.e. χ²2way.",
    _inf, "chi22way",
)
_documented(
    "deltaList", "ΔList",
    "Reference guide, page D: ‘deltaList() See ΔList(), here.’ -- so the guide "
    "documents the ASCII spelling as a lower-case-d cross reference.",
    _list, "ΔList",
)


# --------------------------------------------------------------------------
# BINDINGS -- everything that is *not* a TI-Nspire name
# --------------------------------------------------------------------------
#: ``name -> {kind, module, target, note, evidence}``.  The callable itself is
#: resolved lazily by ``__getattr__`` so this module never duplicates an
#: implementation.
BINDINGS: dict = {}


def _bind(name, kind, target_module, target_name, note, evidence):
    BINDINGS[name] = {
        "kind": kind,
        "module": target_module,
        "target": target_name,
        "note": note,
        "evidence": evidence,
    }


_NOT_IN_GUIDE = (
    "Not printed anywhere in the TI-Nspire reference guide; verified by "
    "searching the guide's full function list."
)

# -- keyboard spellings of a real name, which the guide never prints ---------
_bind("invT", Kind.KEYBOARD, _dist, "invt",
      "The guide prints invt() with a lower-case t; invT is the camel-case twin.",
      _NOT_IN_GUIDE)
_bind("Fpdf", Kind.KEYBOARD, _dist, "FPdf",
      "The guide prints FPdf with a capital F only.", _NOT_IN_GUIDE)
_bind("Fcdf", Kind.KEYBOARD, _dist, "FCdf",
      "The guide prints FCdf with a capital F only.", _NOT_IN_GUIDE)
_bind("poissonPdf", Kind.KEYBOARD, _dist, "poissPdf",
      "The guide's name is poissPdf; poissonPdf is the long spelling.",
      _NOT_IN_GUIDE)
_bind("poissonCdf", Kind.KEYBOARD, _dist, "poissCdf",
      "The guide's name is poissCdf; poissonCdf is the long spelling.",
      _NOT_IN_GUIDE)
_bind("DeltaList", Kind.KEYBOARD, _list, "ΔList",
      "The guide prints ΔList() and cross-references deltaList(); DeltaList is "
      "the camel-case variant.",
      "Reference guide, page D: ‘deltaList() See ΔList(), here.’ -- DeltaList "
      "is neither spelling.")
_bind("freqTable_at_list", Kind.KEYBOARD, _list, "freqTable_to_list",
      "How the guide tells you to type freqTable►list() on a computer "
      "keyboard; '@' cannot appear in a Python identifier, so '_at_' stands in.",
      "Reference guide, page F: ‘You can insert this function from the computer "
      "keyboard by typing freqTable@>list(...).’")

# -- not TI-Nspire names at all --------------------------------------------
_bind("stdev", Kind.RETIRED, _list, "stDevSamp",
      "The TI-Nspire catalog name is stDevSamp; stdev is the spelling most "
      "people type first.", _NOT_IN_GUIDE)
_bind("stdDev", Kind.RETIRED, _list, "stDevPop",
      "The TI-Nspire catalog name is stDevPop; stdDev is the spelling most "
      "people type first.", _NOT_IN_GUIDE)
_bind("variance", Kind.RETIRED, _list, "varSamp",
      "The TI-Nspire catalog names are varSamp and varPop; a bare ‘variance’ "
      "has to pick one, and it picks the sample variance.", _NOT_IN_GUIDE)
_bind("PwrReg", Kind.RETIRED, _reg, "PowerReg",
      "The TI-Nspire catalog name is PowerReg.", _NOT_IN_GUIDE)

# -- what the menus say, versus what the catalog calls it -------------------
_bind("TwoSampleTInt", Kind.MENU, _inf, "tInterval_2Samp",
      'The menu label reads "2-Sample t Interval"; the catalog function is '
      "tInterval_2Samp.",
      "Reference guide, page T/I: the entry is tInterval_2Samp(List1,List2,...); "
      "no TwoSample* spelling appears.")
_bind("TwoSampleInt", Kind.MENU, _inf, "tInterval_2Samp",
      "Alternative spelling of the same menu label -- forwards to "
      "tInterval_2Samp.",
      "Reference guide, page T/I: not a guide name.")
_bind("TwoSampleZInt", Kind.MENU, _inf, "zInterval_2Samp",
      'The menu label reads "2-Sample z Interval"; the catalog function is '
      "zInterval_2Samp.", "Reference guide, page Z: not a guide name.")
_bind("TwoSampleTTest", Kind.MENU, _inf, "tTest_2Samp",
      'The menu label reads "2-Sample t Test"; the catalog function is '
      "tTest_2Samp.", "Reference guide, page T: the entry is tTest_2Samp(...).")
_bind("TwoSampleZTest", Kind.MENU, _inf, "zTest_2Samp",
      'The menu label reads "2-Sample z Test"; the catalog function is '
      "zTest_2Samp.", "Reference guide, page Z: the entry is zTest_2Samp(...).")
_bind("TwoSampleFTest", Kind.MENU, _inf, "FTest_2Samp",
      'The menu label reads "2-Sample F Test"; the catalog function is '
      "FTest_2Samp.", "Reference guide, page F: not a guide name.")
_bind("OnePropZInt", Kind.MENU, _inf, "zInterval_1Prop",
      'The menu label reads "z Interval (1-Prop)"; the catalog function is '
      "zInterval_1Prop.", "Reference guide, page Z: not a guide name.")
_bind("TwoPropZInt", Kind.MENU, _inf, "zInterval_2Prop",
      'The menu label reads "z Interval (2-Prop)"; the catalog function is '
      "zInterval_2Prop.", "Reference guide, page Z: not a guide name.")
_bind("OnePropZTest", Kind.MENU, _inf, "zTest_1Prop",
      'The menu label reads "z Test (1-Prop)"; the catalog function is '
      "zTest_1Prop.", "Reference guide, page Z: not a guide name.")
_bind("TwoPropZTest", Kind.MENU, _inf, "zTest_2Prop",
      'The menu label reads "z Test (2-Prop)"; the catalog function is '
      "zTest_2Prop.", "Reference guide, page Z: not a guide name.")

# -- this package's own extensions ----------------------------------------
_bind("SortA_inplace", Kind.EXTENSION, _list, "SortA_inplace",
      "TI's SortA rebinds the caller's variables; Python cannot, so this writes "
      "the sorted values back into the list objects you pass in.",
      "Nothing on the handheld does this.")
_bind("SortD_inplace", Kind.EXTENSION, _list, "SortD_inplace",
      "Descending twin of SortA_inplace.",
      "Nothing on the handheld does this.")


#: Every *quarantined* name this module answers to.  ``DOCUMENTED_VARIANTS`` is
#: excluded on purpose: those spellings really are TI's.
NAMES = frozenset(BINDINGS)

#: ``name -> note`` for the quarantined names.
NOTES = {name: info["note"] for name, info in BINDINGS.items()}

#: ``name -> evidence`` for every non-primary spelling, quarantined or not.
EVIDENCE = {
    name: info["evidence"]
    for name, info in list(BINDINGS.items()) + list(DOCUMENTED_VARIANTS.items())
}


def kind_of(name: str) -> str:
    """Which of the five standings ``name`` has.

    Raises :class:`KeyError` for a name this module does not know about, so a
    typo in a test cannot silently pass.
    """
    if name in DOCUMENTED_VARIANTS:
        return Kind.DOCUMENTED
    return BINDINGS[name]["kind"]


def evidence(name: str) -> str:
    """Why we say what we say about ``name``."""
    return EVIDENCE[name]


def counts() -> dict:
    """``kind -> how many names``, over everything this module knows."""
    out = {k: 0 for k in KINDS}
    for name in list(BINDINGS) + list(DOCUMENTED_VARIANTS):
        out[kind_of(name)] += 1
    return {k: v for k, v in out.items() if v}


def notes() -> dict:
    """``name -> human-readable caveat`` for the quarantined names."""
    return dict(NOTES)


def __getattr__(name):
    info = BINDINGS.get(name) or DOCUMENTED_VARIANTS.get(name)
    if info is None:
        raise AttributeError(
            f"legacy has no binding for {name!r}; known names: "
            + ", ".join(sorted(list(BINDINGS) + list(DOCUMENTED_VARIANTS)))
        )
    fn = getattr(info["module"], info["target"])
    if info["kind"] == Kind.EXTENSION:
        return fn
    return _Forwarder(fn, name, info)


class _Forwarder:
    """A thin wrapper so ``__name__`` shows the real implementation.

    ``legacy.stdev`` must *behave* exactly like ``stDevSamp`` while still being
    recognisable as a non-Nspire spelling.  Calling one of these is identical to
    calling the target -- only introspection differs.
    """

    __slots__ = ("_fn", "_alias", "_info")

    def __init__(self, fn, alias, info):
        self._fn = fn
        self._alias = alias
        self._info = info

    @property
    def __name__(self):
        return self._fn.__name__

    @property
    def __doc__(self):
        return (
            f"``{self._alias}`` -- {self._info['kind']}.\n\n"
            f"{self._info['note']}\n\n"
            f"Forwards to ``{self._fn.__name__}``:\n{self._fn.__doc__}"
        )

    @property
    def real(self):
        """The faithful TI-Nspire function this alias forwards to."""
        return self._fn

    def __call__(self, *args, **kwargs):
        return self._fn(*args, **kwargs)

    def __repr__(self):
        return f"<legacy {self._alias} -> {self._fn.__name__}>"


def table() -> str:
    """A printable table of every quarantined name and where it points."""
    width = max(len(n) for n in BINDINGS)
    kind_width = max(len(k) for k in KINDS)
    lines = [f"{'alias'.ljust(width)}  {'kind'.ljust(kind_width)}  target"]
    for name in sorted(BINDINGS):
        info = BINDINGS[name]
        lines.append(
            f"{name.ljust(width)}  {info['kind'].ljust(kind_width)}  "
            f"{info['target']}"
        )
    return "\n".join(lines)


def evidence_table() -> str:
    """``table()`` plus the reason each name is filed where it is."""
    width = max(len(n) for n in BINDINGS)
    lines = []
    for name in sorted(BINDINGS):
        info = BINDINGS[name]
        lines.append(f"{name.ljust(width)}  {info['kind']}")
        lines.append(f"{' ' * width}  {info['evidence']}")
        lines.append(f"{' ' * width}  -> {info['target']}")
        lines.append("")
    lines.append("-- not quarantined: the guide prints these itself --")
    for name in sorted(DOCUMENTED_VARIANTS):
        info = DOCUMENTED_VARIANTS[name]
        lines.append(f"{name.ljust(width)}  {Kind.DOCUMENTED}")
        lines.append(f"{' ' * width}  {info['evidence']}")
    return "\n".join(lines)
