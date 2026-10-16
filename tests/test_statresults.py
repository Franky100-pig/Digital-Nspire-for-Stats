"""Every procedure publishes exactly what TI's guide says it publishes.

``stat.results`` is part of the interface: a reader who runs ``OneVar`` and then
types ``stat.Q1X`` is relying on the guide's twelve names, in the guide's order,
and nothing else.  So each procedure's output list is asserted against
:mod:`tinspire_stats._refguide` name for name and position for position.

This is deliberately an equality test rather than a subset test.  A procedure
that publishes one variable too many is as wrong as one that publishes one too
few -- the handheld's ``stat.results`` screen would show a line the device does
not, and a name that happens to collide with something else would silently
overwrite it.
"""

from __future__ import annotations

import pytest

import tinspire_stats as ts
from tinspire_stats import _refguide, stat

X = [1, 2, 3, 4, 5]
Y = [5, 8, 11, 14, 17]
#: positive, so PowerReg / LnReg / Logistic all converge
POS = [1, 2, 4, 8, 16]
#: the second predictor for the multiple regressions.  It must not be an affine
#: function of X (X+1 would make the design matrix singular and the fit would
#: have no unique answer), and it must be the same length as Y.
X2 = [2, 1, 4, 3, 6]
XVALS = [3, 4]
#: two column levels for ANOVA2way, six observations each.  They must not be
#: perfectly additive: if ``(col1[i] - col2[i])`` were constant the residual
#: would be exactly zero in the Block design and the F ratio would divide by it.
A2_COL1 = [1, 2, 3, 4, 5, 9]
A2_COL2 = [2, 3, 4, 5, 6, 7]

#: (reference name, invocation form, call, extra kwargs for publishes()).
#: One row per invocation form that publishes a different set of variables.
CASES = [
    ("OneVar", 0, lambda: ts.OneVar([1, 2, 4, 8, 16]), {}),
    ("TwoVar", 0, lambda: ts.TwoVar(X, Y), {}),
    ("FiveNumSummary", 0, lambda: ts.FiveNumSummary([3, 1, 4, 1, 5]), {}),

    ("LinRegMx", 0, lambda: ts.LinRegMx(X, Y), {}),
    ("LinRegBx", 0, lambda: ts.LinRegBx(X, Y), {}),
    ("MedMed", 0, lambda: ts.MedMed(X, Y), {}),
    ("QuadReg", 0, lambda: ts.QuadReg(X, Y), {}),
    ("CubicReg", 0, lambda: ts.CubicReg(X, Y), {}),
    ("QuartReg", 0, lambda: ts.QuartReg(X, Y), {}),
    ("PowerReg", 0, lambda: ts.PowerReg(X, POS), {}),
    ("ExpReg", 0, lambda: ts.ExpReg(X, POS), {}),
    ("LnReg", 0, lambda: ts.LnReg(X, POS), {}),
    ("SinReg", 0, lambda: ts.SinReg(X, [5, 8, 11, 14, 17], 1, 4), {}),
    ("Logistic", 0, lambda: ts.Logistic(X, [1, 2, 4, 8, 15]), {}),
    ("LogisticD", 0, lambda: ts.LogisticD(X, POS), {}),
    # MultReg / MultRegTests / MultRegIntervals are variadic: `Y, X1[, X2…]`,
    # so the predictors are separate arguments, not one list of lists.
    ("MultReg", 0, lambda: ts.MultReg(Y, X, X2), {"predictors": 2}),
    ("LinRegtTest", 0, lambda: ts.LinRegtTest(X, Y), {}),
    ("MultRegTests", 0, lambda: ts.MultRegTests(Y, X, X2), {}),

    ("zInterval", 0, lambda: ts.zInterval(2.0, [3, 4, 5, 6, 7], None, 0.95), {}),
    ("tInterval", 0, lambda: ts.tInterval([3, 4, 5, 6, 7], None, 0.95), {}),
    ("zInterval_2Samp", 0, lambda: ts.zInterval_2Samp(
        1.0, 1.5, [3, 4, 5, 6, 7], [4, 5, 6, 7, 8], None, None, 0.95), {}),
    #: tInterval_2Samp / tTest_2Samp: form 0 is Pooled = NO (no stat.sp),
    #: form 1 is Pooled = YES.
    ("tInterval_2Samp", 0, lambda: ts.tInterval_2Samp(
        [3, 4, 5, 6, 7], [4, 6, 7, 9, 10], None, None, 0.95), {}),
    ("tInterval_2Samp", 1, lambda: ts.tInterval_2Samp(
        [3, 4, 5, 6, 7], [4, 6, 7, 9, 10], None, None, 0.95, 1), {}),
    ("zInterval_1Prop", 0, lambda: ts.zInterval_1Prop(40, 100, 0.95), {}),
    ("zInterval_2Prop", 0, lambda: ts.zInterval_2Prop(40, 100, 50, 120, 0.95), {}),
    ("LinRegtIntervals", 0, lambda: ts.LinRegtIntervals(X, Y, None, 0, 0.95), {}),
    ("LinRegtIntervals", 1, lambda: ts.LinRegtIntervals(X, Y, None, 1, 3, 0.95), {}),
    ("MultRegIntervals", 0, lambda: ts.MultRegIntervals(
        Y, X, X2, XVALS), {}),

    #: zTest: form 0 is Data input (defines stat.sx), form 1 is the
    #: summary-statistics input, where the guide says sx is not returned.
    ("zTest", 0, lambda: ts.zTest(5, 2.0, [3, 4, 5, 6, 7]), {}),
    ("zTest", 1, lambda: ts.zTest(5, 2.0, 5.0, 5), {}),
    ("tTest", 0, lambda: ts.tTest(5, [3, 4, 5, 6, 7]), {}),
    ("zTest_2Samp", 0, lambda: ts.zTest_2Samp(
        1.0, 1.5, [3, 4, 5, 6, 7], [4, 5, 6, 7, 8]), {}),
    ("tTest_2Samp", 0, lambda: ts.tTest_2Samp([3, 4, 5, 6, 7], [4, 6, 7, 9, 10]), {}),
    ("tTest_2Samp", 1, lambda: ts.tTest_2Samp(
        [3, 4, 5, 6, 7], [4, 6, 7, 9, 10], None, None, 0, 1), {}),
    ("zTest_1Prop", 0, lambda: ts.zTest_1Prop(0.5, 40, 100), {}),
    ("zTest_2Prop", 0, lambda: ts.zTest_2Prop(40, 100, 50, 120), {}),
    ("FTest_2Samp", 0, lambda: ts.FTest_2Samp([3, 4, 5, 6, 7], [4, 6, 7, 9, 10]), {}),
    ("χ²GOF", 0, lambda: ts.chi2GOF([10, 20, 30], [15, 20, 25], 2), {}),
    ("χ²2way", 0, lambda: ts.chi22way([[10, 20], [30, 40]]), {}),
    ("ANOVA", 0, lambda: ts.ANOVA([1, 2, 3], [4, 5, 6], [7, 8, 9]), {}),
    #: ANOVA2way: form 0 is the Block design (levRow omitted / 0), form 1 the
    #: replicated two-factor design (levRow = 2, so 6 observations = 2 rows x 3).
    ("ANOVA2way", 0, lambda: ts.ANOVA2way(A2_COL1, A2_COL2), {}),
    ("ANOVA2way", 1, lambda: ts.ANOVA2way(A2_COL1, A2_COL2, 2), {}),
]

IDS = [f"{name}-form{form}" for name, form, _call, _kw in CASES]


@pytest.fixture(autouse=True)
def _clean():
    stat.publish({})
    yield
    stat.publish({})


@pytest.mark.parametrize("name, form, call, kwargs", CASES, ids=IDS)
def test_publishes_exactly_the_reference_guide_names(name, form, call, kwargs):
    call()
    expected = list(_refguide.publishes(name, form, **kwargs))
    assert list(stat.keys()) == expected, (
        f"{name} form {form}\n"
        f"  extra   : {[k for k in stat.keys() if k not in expected]}\n"
        f"  missing : {[k for k in expected if k not in stat.keys()]}\n"
        f"  order   : expected {expected}\n"
        f"            got      {list(stat.keys())}"
    )


def test_every_reference_entry_is_a_real_function():
    """A name in the table that the package does not export is a typo."""
    missing = [n for n in _refguide.OUTPUTS if not hasattr(ts, n) and n not in ("χ²GOF", "χ²2way")]
    assert missing == []


def test_the_reference_table_is_checked_against_tis_own_name_list():
    """Every pin is either a documented name or a known extra, never a guess."""
    from tinspire_stats.statvar import DOCUMENTED_STAT_NAMES

    unknown = [n for n in _refguide.check()]
    assert unknown == [], (
        "these names are in the guide's per-procedure tables but not in TI's "
        f"stat.results name list, so each needs a note in statvar: {unknown}"
    )
    assert len(DOCUMENTED_STAT_NAMES) == 120


def test_a_run_leaves_no_internal_bookkeeping_in_the_group():
    """Nothing private may leak: no leading underscore, no helper names."""
    ts.OneVar([1, 2, 3])
    ts.MedMed(X, Y)
    ts.QuadReg(X, Y)
    leaked = [k for k in stat.keys() if k.startswith("_")]
    assert leaked == []


def test_list_valued_results_do_not_break_the_group():
    """bList, Resid and the chi-square matrices are lists; stat.values is not."""
    ts.MultRegTests(Y, X, X2)
    assert stat.bList is not None
    assert all(isinstance(v, float) for v in stat.values)

    ts.chi22way([[10, 20], [30, 40]])
    assert all(isinstance(v, float) for v in stat.values)


def test_each_result_is_readable_by_name_after_its_procedure():
    """The point of publishing a name is that the name works afterwards."""
    ts.OneVar([1, 2, 4, 8, 16])
    assert stat.Q1X == 2.0
    assert stat.MedianX == 4.0

    ts.TwoVar(X, Y)
    assert stat.MedY == stat.MedianY      # the guide prints the short spelling
