"""``tinspire_stats`` -- the TI-Nspire statistics suite, in Python.

Names are copied character-for-character from the TI-Nspire Reference Guide, so
that a calculation typed here reads like the same calculation typed on the
handheld:

.. code-block:: text

    OneVar {1,2,3,4}          ->  stat.v, stat.Σx, stat.Σx², stat.sx, stat.σx,
                                  stat.n, stat.MinX, stat.Q1X, stat.MedianX,
                                  stat.Q3X, stat.MaxX, stat.SSX
    LinRegMx x,y              ->  stat.m, stat.b, stat.r, stat.r², stat.RegEqn
    tInterval v,sx,n,0.95     ->  stat.CLower, stat.CUpper, stat.v, stat.ME,
                                  stat.df, stat.sx, stat.n

The results group is the module-level singleton ``stat``, exactly as on the
calculator, and ``stat.results`` prints the same name/value pairs the screen
shows::

    >>> from tinspire_stats import OneVar, stat
    >>> OneVar([1, 2, 4, 8, 16])
    StatGroup(v, Σx, Σx², sx, σx, n, MinX, Q1X, MedianX, Q3X, MaxX, SSX)
    >>> stat.v
    6.2
    >>> stat.Q1X
    2.0

Quick index
-----------
===========================  ==================================================
``Statistics > List Math``   :func:`mean` :func:`median` :func:`stDevSamp`
                             :func:`stDevPop` :func:`varSamp` :func:`varPop`
                             :func:`SortA` :func:`SortD` :func:`cumulativeSum`
                             :func:`ΔList` :func:`frequency` :func:`corrMat`
``Stat Calculations``        :func:`OneVar` :func:`TwoVar`
                             :func:`FiveNumSummary` :func:`LinRegMx`
                             :func:`LinRegBx` :func:`QuadReg` :func:`CubicReg`
                             :func:`QuartReg` :func:`LnReg` :func:`ExpReg`
                             :func:`PowerReg` :func:`MedMed` :func:`Logistic`
                             :func:`LogisticD` :func:`SinReg` :func:`MultReg`
``Distributions``            :func:`normPdf` :func:`normCdf` :func:`invNorm`
                             :func:`tPdf` :func:`tCdf` :func:`invt`
                             :func:`χ2Pdf` :func:`χ2Cdf` :func:`invχ2`
                             :func:`FPdf` :func:`FCdf` :func:`invF`
                             :func:`binomPdf` :func:`binomCdf` :func:`invBinom`
                             :func:`poissPdf` :func:`poissCdf` :func:`geomPdf`
                             :func:`geomCdf`
``Confidence Intervals``     :func:`zInterval` :func:`tInterval`
                             :func:`zInterval_2Samp` :func:`tInterval_2Samp`
                             :func:`zInterval_1Prop` :func:`zInterval_2Prop`
``Stat Tests``               :func:`zTest` :func:`tTest` :func:`zTest_2Samp`
                             :func:`tTest_2Samp` :func:`FTest_2Samp`
                             :func:`zTest_1Prop` :func:`zTest_2Prop`
                             :func:`chi2GOF` :func:`chi22way` :func:`ANOVA`
                             :func:`ANOVA2way`
``Random``                   :func:`RandSeed` :func:`rand` :func:`randInt`
                             :func:`randNorm` :func:`randBin` :func:`randSamp`
===========================  ==================================================

Names the guide prints with symbols that Python identifiers cannot carry get a
usable twin, and the guide's spelling still works through the catalogue:

======================  ==========================
Reference guide         Python identifier here
======================  ==========================
``freqTable►list(``     ``freqTable_to_list(``
``χ²Pdf(``              ``χ2Pdf(`` / ``chi2Pdf(``
``invχ²(``              ``invχ2(`` / ``invChi2(``
``χ²GOF``               ``chi2GOF(`` / ``χ2GOF(``
``χ²2way``              ``chi22way(`` / ``χ22way(``
``ΔList``               ``ΔList(`` / ``deltaList(``
======================  ==========================

Two of those -- ``chi2Pdf`` and ``invChi2`` -- are not just our transliterations:
the reference guide prints them itself, next to ``χ2Pdf`` and ``invχ2`` on the
same entries.  See :mod:`tinspire_stats.legacy` for the page each claim came off.

Names that are **not** TI-Nspire names -- the spellings people borrow from other
calculators, the words the menus put on screen, and this package's own
extensions -- live only in :mod:`tinspire_stats.legacy`, which records for each
one *how* it differs and on what evidence.  ``legacy.table()`` prints them.  The
few extra spellings that are exported here as well are declared in
:data:`ROOT_ALIASES`, each with its standing, so the root's contents are a
checkable claim rather than a matter of reading the source.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# errors and the results machinery
# --------------------------------------------------------------------------
from ._core import (
    ArgumentError,
    DataTypeError,
    DimensionMismatchError,
    DomainError,
    StatError,
    TIError,
    VOID,
    is_void,
)
from .statvar import (
    CopyVar,
    RegEqn,
    StatGroup,
    StatResults,
    VarStore,
    canonical,
    copy_to_stat_group,
    publish,
    stat,
)

# --------------------------------------------------------------------------
# List Math
# --------------------------------------------------------------------------
from .listmath import (
    SortA,
    SortD,
    count,
    countif,
    cumulativeSum,
    frequency,
    make_criteria,
    mean,
    median,
    product,
    corrMat,
    freqTable_to_list,
    max,
    min,
    stDevPop,
    stDevSamp,
    sum,
    sumIf,
    varPop,
    varSamp,
    ΔList,
)

# --------------------------------------------------------------------------
# Stat Calculations
# --------------------------------------------------------------------------
from .summary import (
    FiveNumSummary,
    OneVar,
    TwoVar,
    five_numbers,
    get_quartile_method,
    set_quartile_method,
)
from .regress import (
    CubicReg,
    ExpReg,
    LinRegBx,
    LinRegMx,
    LinRegtIntervals,
    LinRegtTest,
    LnReg,
    Logistic,
    LogisticD,
    MedMed,
    MultReg,
    MultRegIntervals,
    MultRegTests,
    PowerReg,
    QuadReg,
    QuartReg,
    SinReg,
)

# --------------------------------------------------------------------------
# Distributions
# --------------------------------------------------------------------------
from .distributions import (
    FCdf,
    FPdf,
    RandSeed,
    binomCdf,
    binomPdf,
    geomCdf,
    geomPdf,
    invBinom,
    invBinomN,
    invF,
    invNorm,
    invt,
    normCdf,
    normPdf,
    poissCdf,
    poissPdf,
    rand,
    randBin,
    randInt,
    randNorm,
    randSamp,
    tCdf,
    tPdf,
    χ2Cdf,
    χ2Pdf,
    invχ2,
)

# --------------------------------------------------------------------------
# Inference
# --------------------------------------------------------------------------
from .inference import (
    ANOVA,
    ANOVA2way,
    FTest_2Samp,
    NAME_SUPERSETS,
    chi2GOF,
    chi22way,
    tInterval,
    tInterval_2Samp,
    tTest,
    tTest_2Samp,
    zInterval,
    zInterval_1Prop,
    zInterval_2Prop,
    zInterval_2Samp,
    zTest,
    zTest_1Prop,
    zTest_2Prop,
    zTest_2Samp,
)

# --------------------------------------------------------------------------
# catalogue helpers
# --------------------------------------------------------------------------
from .catalog import (
    MENU,
    OFF_MENU,
    ascii_name,
    catalog,
    lookup,
    menu_tree,
    pretty_catalog,
    ti_spelling,
)

#: Submodule holding every name that is *not* a faithful TI-Nspire name.
from . import legacy  # noqa: E402  (imported last: it pulls in every module)
from . import menu  # noqa: E402  (the keypad's maps, not the catalogue's)

__version__ = "1.0.0"

# --------------------------------------------------------------------------
# Root-level alias table
# --------------------------------------------------------------------------
# Each entry is a second spelling of something already imported above.  The
# *standing* of every one is declared here rather than left to a comment, and
# ``tests/test_tinspire_stats.py`` checks the declaration against ``legacy``'s
# registry.  That check exists because the labelling had already gone wrong
# once: ``chi2Pdf`` -- which the reference guide prints itself -- was filed
# under "TI-83/84 spelling" alongside ``stdev``, which the guide has never
# heard of.  A comment cannot catch that; a table plus a test can.
#
#: ``alias -> (target, standing)``; ``standing`` is a :class:`legacy.Kind`.
ROOT_ALIASES = {
    # Spellings the guide prints itself.  legacy.DOCUMENTED_VARIANTS records the
    # page each one was read off.
    "χ2GOF": (chi2GOF, legacy.Kind.DOCUMENTED),
    "χ22way": (chi22way, legacy.Kind.DOCUMENTED),
    "chi2Pdf": (χ2Pdf, legacy.Kind.DOCUMENTED),
    "chi2Cdf": (χ2Cdf, legacy.Kind.DOCUMENTED),
    "invChi2": (invχ2, legacy.Kind.DOCUMENTED),
    "deltaList": (ΔList, legacy.Kind.DOCUMENTED),
    # Typographic near-misses the guide never prints: convenient to type, but
    # not TI's names, and labelled as such wherever they are reported.
    "invT": (invt, legacy.Kind.KEYBOARD),
    "Fpdf": (FPdf, legacy.Kind.KEYBOARD),
    "Fcdf": (FCdf, legacy.Kind.KEYBOARD),
    "poissonPdf": (poissPdf, legacy.Kind.KEYBOARD),
    "poissonCdf": (poissCdf, legacy.Kind.KEYBOARD),
    "DeltaList": (ΔList, legacy.Kind.KEYBOARD),
    "freqTable_at_list": (freqTable_to_list, legacy.Kind.KEYBOARD),
}

for _alias, (_target, _standing) in ROOT_ALIASES.items():
    globals()[_alias] = _target
del _alias, _target, _standing


__all__ = [
    # errors / plumbing
    "TIError", "DomainError", "DimensionMismatchError", "ArgumentError",
    "DataTypeError", "StatError", "VOID", "is_void",
    # results group
    "stat", "StatGroup", "StatResults", "RegEqn", "CopyVar", "VarStore",
    "copy_to_stat_group", "publish", "canonical",
    "set_quartile_method", "get_quartile_method", "five_numbers",
    # list math
    "mean", "median", "product", "min", "max", "sum", "count", "countif",
    "sumIf", "stDevSamp", "stDevPop", "varSamp", "varPop", "SortA", "SortD",
    "cumulativeSum", "ΔList", "DeltaList", "deltaList",
    "freqTable_to_list", "freqTable_at_list",
    "frequency", "corrMat", "make_criteria",
    # stat calculations
    "OneVar", "TwoVar", "FiveNumSummary",
    "LinRegMx", "LinRegBx", "QuadReg", "CubicReg", "QuartReg", "LnReg",
    "ExpReg", "PowerReg", "MedMed", "Logistic", "LogisticD", "SinReg",
    "MultReg", "MultRegTests", "MultRegIntervals", "LinRegtIntervals",
    "LinRegtTest",
    # distributions
    "normPdf", "normCdf", "invNorm", "tPdf", "tCdf", "invt", "invT",
    "χ2Pdf", "chi2Pdf", "χ2Cdf", "chi2Cdf", "invχ2", "invChi2",
    "FPdf", "Fpdf", "FCdf", "Fcdf", "invF",
    "binomPdf", "binomCdf", "invBinom", "invBinomN",
    "poissPdf", "poissonPdf", "poissCdf", "poissonCdf", "geomPdf", "geomCdf",
    "RandSeed", "rand", "randInt", "randNorm", "randBin", "randSamp",
    # inference
    "zInterval", "tInterval", "zInterval_2Samp", "tInterval_2Samp",
    "zInterval_1Prop", "zInterval_2Prop",
    "zTest", "tTest", "zTest_2Samp", "tTest_2Samp", "FTest_2Samp",
    "zTest_1Prop", "zTest_2Prop",
    "chi2GOF", "χ2GOF", "chi22way", "χ22way", "ANOVA", "ANOVA2way",
    "NAME_SUPERSETS",
    # catalogue
    "MENU", "OFF_MENU",
    "ascii_name", "ti_spelling", "catalog", "lookup", "menu_tree",
    "pretty_catalog", "legacy", "ROOT_ALIASES",
    # the keypad's menus
    "menu",
]
