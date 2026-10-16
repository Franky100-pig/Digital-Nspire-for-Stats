"""What each statistics procedure leaves in ``stat.results``, per TI's guide.

A procedure's output variables are part of its interface: after ``OneVar`` the
device shows twelve lines, and a reader who then types ``stat.Q1X`` expects it
to be there.  So each procedure's list is pinned to the reference guide rather
than to whatever the implementation happens to compute.

``OUTPUTS`` maps a procedure to the ordered names it publishes -- ordered,
because ``stat.results`` displays them in that order.  A procedure whose
invocation forms publish different variables has one tuple per form, and the
form order is the one used below (and in ``tests/test_statresults.py``).

Source
------
TI-Nspire™ CX Reference Guide (the eGuide shipped with OS 5.4, which is the
current release -- `education.ti.com <https://education.ti.com/en-ph/product-resources/whats-new>`_
lists 5.4 as latest, and its notes are "various bug fixes and Test Mode
functionality improvements", so no statistics surface changed).  Each entry
below is the "Output variable" table of that procedure's catalog page, at
``education.ti.com/html/webhelp/EG_TINspire/EN/Subsystems/EG_RefGuide/``.

The guide's own webhelp has several damaged cells in exactly these tables.  Each
one is listed here with the correction and the evidence for it, so the table
above is auditable rather than merely asserted:

===============================  =================  =========================================
printed in the guide             read as            why
===============================  =================  =========================================
``stat.P Value``                 ``stat.PVal``      ``zTest_2Prop`` and four other entries print ``PVal``
``stat.UpperrPred``              ``stat.UpperPred`` the same row pairs ``LowerPred`` with it
``stat.x1_barstat.x2_bar``       two names          two names with the separating comma lost
``stat.Σx2`` (TwoVar only)       ``stat.Σx²``       OneVar's identical cell keeps the superscript
``stat.σ `` (trailing space)     ``stat.σ``         stray whitespace only; see below, this one is real
``stat.MedY`` (TwoVar only)      ``stat.MedianY``   the stat.results name list prints ``MedianY``
``stat.ExpMat``/``CompMat``      ``…Matrix``        the stat.results name list prints the long form
``stat.χ2``                      ``stat.χ²``        the same entry prints ``χ²`` in its syntax line
``stat.Ç``/``Ç1``/``Ç2``         ``stat.p̂…``        ``Ç`` is the p-hat glyph of the TI-84 key font
===============================  =================  =========================================

``zInterval`` publishes ``stat.σ`` and not ``stat.σx``, which looks like the
``x`` of a sibling name having gone missing.  It is not: it is the known
population standard deviation, the ``σ`` that ``zInterval σ,List`` takes as its
*first argument* and echoes back, sitting beside ``stat.sx``, the sample
standard deviation.  The guide spells the two names differently on purpose.  The
tell is mechanical -- the same pages write every other sigma variable as
``σ`` inside its Greek-entity span *followed by a literal* ``x``
(``stat.σx`` ×4, ``stat.σx1`` ×3, ``stat.σx2`` ×3, ``stat.σy`` ×2, i.e. eleven
times), and write the bare span with nothing after it exactly once, here.

Related, and equally real: the four procedures that report a sample standard
deviation do not agree on its name.  ``zInterval`` and ``tTest`` say
``stat.sx``; ``tInterval`` says ``stat.σx``; and the two-sample versions split
the same way -- ``tInterval_2Samp`` prints ``stat.σx1``/``stat.σx2`` while
``tTest_2Samp`` prints ``stat.sx1``/``stat.sx2``.  Each name below is that
procedure's own, and no procedure publishes an unrequested twin.

Deliberately *not* corrected: the polynomial and multiple regressions publish
``stat.R²`` with a capital R, while the linear, exponential, logarithmic and
power ones publish ``stat.r²``.  That asymmetry is printed in five separate
procedures' tables, and ``stat.AdjR²`` agrees with it, so it is read as real.
The stat.results catalog entry lists only ``r²``, but that entry is a list of
names to avoid redefining rather than an exhaustive inventory -- it does not
list ``stat.df`` either, and eight procedures publish it.
"""

from __future__ import annotations

__all__ = ["OUTPUTS", "MULTREG_COEFFICIENT", "publishes", "check"]

#: ``MultReg`` publishes one coefficient per predictor rather than a fixed
#: number, so its entry carries this marker where the run of ``b0`` .. ``bk``
#: goes.  ``publishes("MultReg", predictors=2)`` expands it.
MULTREG_COEFFICIENT = "b*"

#: procedure -> the ordered names it publishes.  One tuple per invocation form
#: where the forms publish different variables.
OUTPUTS: dict = {
    # ---- statistics ------------------------------------------------------
    "OneVar": ("v", "Σx", "Σx²", "sx", "σx", "n", "MinX", "Q1X", "MedianX", "Q3X", "MaxX", "SSX"),
    "TwoVar": ("v", "Σx", "Σx²", "sx", "σx", "n",
               "w", "Σy", "Σy²", "sy", "σy", "Σxy", "r",
               "MinX", "Q1X", "MedianX", "Q3X", "MaxX",
               "MinY", "Q1Y", "MedianY", "Q3Y", "MaxY",
               "Σ(x-v)²", "Σ(y-w)²"),
    "FiveNumSummary": ("MinX", "Q1X", "MedianX", "Q3X", "MaxX"),

    # ---- regressions -----------------------------------------------------
    "LinRegMx": ("RegEqn", "m", "b", "r²", "r", "Resid", "XReg", "YReg", "FreqReg"),
    "LinRegBx": ("RegEqn", "a", "b", "r²", "r", "Resid", "XReg", "YReg", "FreqReg"),
    "MedMed": ("RegEqn", "m", "b", "Resid", "XReg", "YReg", "FreqReg"),
    "QuadReg": ("RegEqn", "a", "b", "c", "R²", "Resid", "XReg", "YReg", "FreqReg"),
    "CubicReg": ("RegEqn", "a", "b", "c", "d", "R²", "Resid", "XReg", "YReg", "FreqReg"),
    "QuartReg": ("RegEqn", "a", "b", "c", "d", "e", "R²", "Resid", "XReg", "YReg", "FreqReg"),
    "PowerReg": ("RegEqn", "a", "b", "r²", "r", "Resid", "ResidTrans", "XReg", "YReg", "FreqReg"),
    "ExpReg": ("RegEqn", "a", "b", "r²", "r", "Resid", "ResidTrans", "XReg", "YReg", "FreqReg"),
    "LnReg": ("RegEqn", "a", "b", "r²", "r", "Resid", "ResidTrans", "XReg", "YReg", "FreqReg"),
    "SinReg": ("RegEqn", "a", "b", "c", "d", "Resid", "XReg", "YReg", "FreqReg"),
    "Logistic": ("RegEqn", "a", "b", "c", "Resid", "XReg", "YReg", "FreqReg"),
    "LogisticD": ("RegEqn", "a", "b", "c", "d", "Resid", "XReg", "YReg", "FreqReg"),
    "MultReg": ("RegEqn", MULTREG_COEFFICIENT, "R²", "yList", "Resid"),
    "LinRegtTest": ("RegEqn", "t", "PVal", "df", "a", "b", "s", "SESlope", "r²", "r", "Resid"),
    "MultRegTests": ("RegEqn", "F", "PVal", "R²", "AdjR²", "s", "DW",
                     "dfReg", "SSReg", "MSReg", "dfError", "SSError", "MSError",
                     "bList", "tList", "PList", "SEList", "yList", "Resid",
                     "sResid", "CookDist", "Leverage"),

    # ---- intervals -------------------------------------------------------
    #: stat.σ is the *known population* σ (the first argument), not a typo for
    #: stat.σx -- see the note above.
    "zInterval": ("CLower", "CUpper", "x", "ME", "sx", "n", "σ"),
    "tInterval": ("CLower", "CUpper", "v", "ME", "df", "σx", "n"),
    "zInterval_2Samp": ("CLower", "CUpper", "x1-x2", "ME", "x1", "x2",
                        "σx1", "σx2", "n1", "n2", "r1", "r2"),
    #: form 0 = Pooled NO, form 1 = Pooled YES.  stat.sp is described as
    #: "Calculated when Pooled = YES", so the pooled form adds it.
    "tInterval_2Samp": (
        ("CLower", "CUpper", "v1-v2", "ME", "df", "v1", "v2",
         "σx1", "σx2", "n1", "n2"),
        ("CLower", "CUpper", "v1-v2", "ME", "df", "v1", "v2",
         "σx1", "σx2", "n1", "n2", "sp"),
    ),
    "zInterval_1Prop": ("CLower", "CUpper", "p̂", "ME", "n"),
    "zInterval_2Prop": ("CLower", "CUpper", "p̂Diff", "ME", "p̂1", "p̂2", "n1", "n2"),
    #: Without Xval the interval is for the slope; with Xval it also predicts.
    "LinRegtIntervals": (
        ("RegEqn", "a", "b", "df", "r²", "r", "Resid",
         "CLower", "CUpper", "ME", "SESlope", "s"),
        ("RegEqn", "a", "b", "df", "r²", "r", "Resid",
         "CLower", "CUpper", "ME", "SE", "LowerPred", "UpperPred", "MEPred", "SEPred", "y"),
    ),
    "MultRegIntervals": ("RegEqn", "y", "dfError", "CLower", "CUpper", "ME", "SE",
                         "LowerPred", "UpperPred", "MEPred", "SEPred", "bList", "Resid"),

    # ---- tests -----------------------------------------------------------
    #: form 0 = Data input, form 1 = summary-statistics input.  The guide
    #: qualifies stat.sx with "Only returned for Data input."
    "zTest": (
        ("z", "PVal", "x", "sx", "n"),
        ("z", "PVal", "x", "n"),
    ),
    "tTest": ("t", "PVal", "df", "v", "sx", "n"),
    "zTest_2Samp": ("z", "PVal", "x1", "x2", "sx1", "sx2", "n1", "n2"),
    #: form 0 = Pooled NO, form 1 = Pooled YES (as tInterval_2Samp above).
    "tTest_2Samp": (
        ("t", "PVal", "df", "v1", "v2", "sx1", "sx2", "n1", "n2"),
        ("t", "PVal", "df", "v1", "v2", "sx1", "sx2", "n1", "n2", "sp"),
    ),
    "zTest_1Prop": ("p0", "z", "PVal", "p̂", "n"),
    "zTest_2Prop": ("z", "PVal", "p̂1", "p̂2", "p̂", "n1", "n2"),
    "FTest_2Samp": ("F", "PVal", "dfNumer", "dfDenom", "sx1", "sx2",
                    "x1_bar", "x2_bar", "n1", "n2"),
    "χ²GOF": ("χ²", "PVal", "df", "CompList"),
    "χ²2way": ("χ²", "PVal", "df", "ExpMatrix", "CompMatrix"),
    "ANOVA": ("F", "PVal", "df", "SS", "MS", "dfError", "SSError", "MSError",
              "sp", "xbarlist", "CLowerList", "CUpperList"),
    #: form 0 = the Block design (levRow = 0, the guide's "LevRow=0 for Block"):
    #: one observation per cell, so the second factor is called Block throughout.
    #: form 1 = the replicated two-factor design (levRow = 2..Len-1), which must
    #: have Len/levRow >= 2.  The two are alternative designs, not one listing:
    #: the guide prints the Block table, then retitles and prints COLUMN FACTOR /
    #: ROW FACTOR / INTERACTION / ERROR Outputs.  So the two-factor run does not
    #: define stat.F or stat.FBlock, and the Block run does not define the
    #: Col/Row/Interact names.
    "ANOVA2way": (
        ("F", "PVal", "df", "SS", "MS",
         "FBlock", "PValBlock", "dfBlock", "SSBlock", "MSBlock",
         "dfError", "SSError", "MSError", "s"),
        ("Fcol", "PValCol", "dfCol", "SSCol", "MSCol",
         "FRow", "PValRow", "dfRow", "SSRow", "MSRow",
         "FInteract", "PValInteract", "dfInteract", "SSInteract", "MSInteract",
         "dfError", "SSError", "MSError", "s"),
    ),
}


def publishes(name: str, form: int = 0, predictors: "int | None" = None) -> tuple:
    """The names a procedure publishes, in order, for one invocation form.

    ``predictors`` is only needed by ``MultReg``, whose coefficient run grows
    with the number of predictor variables.
    """
    entry = OUTPUTS[name]
    if entry and isinstance(entry[0], tuple):
        entry = entry[form]
    if MULTREG_COEFFICIENT in entry:
        count = 1 if predictors is None else predictors + 1
        run = tuple(f"b{i}" for i in range(count))
        expanded = []
        for n in entry:
            # splice the run in, rather than nesting it: b0, b1, b2 -- not (b0, b1, b2)
            expanded.extend(run if n == MULTREG_COEFFICIENT else (n,))
        entry = tuple(expanded)
    return entry


def check() -> list:
    """Every name pinned above, checked against the two name tables.

    Returns the names that are in neither, in the order they were pinned.  An
    empty list is the invariant: every variable this package publishes is either
    one TI's ``stat.results`` entry lists, or one the per-procedure tables use
    and ``EXTRA_STAT_NAMES`` accounts for.  A new name that appears in neither
    is a typo, and the suite refuses it.
    """
    from .statvar import DOCUMENTED_STAT_NAMES, EXTRA_STAT_NAMES

    known = set(DOCUMENTED_STAT_NAMES) | set(EXTRA_STAT_NAMES)
    out = []
    for entry in OUTPUTS.values():
        forms = entry if entry and isinstance(entry[0], tuple) else (entry,)
        for names in forms:
            out += [n for n in names
                    if n != MULTREG_COEFFICIENT and n not in known]
    return out
