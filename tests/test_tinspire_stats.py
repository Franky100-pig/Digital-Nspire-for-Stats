"""The test suite for ``tinspire_stats``.

Two kinds of test live here, and it is worth keeping them apart:

* **Fidelity tests** -- do the *names* match the TI-Nspire Reference Guide, do
  the documented quirks (void elements, integer frequencies, the inclusive
  quartile, the ``Data`` vs ``Stats`` input forms) behave the way the handheld
  behaves?
* **Regression tests** -- pinned values, so a future edit cannot silently move
  an answer.

Numerical agreement with an independent implementation (SciPy / NumPy) is *not*
checked here; that is what ``tools/checks_vs_scipy.py`` is for, because SciPy is
not a dependency of this package.
"""

from __future__ import annotations

import doctest
import math

import pytest

import tinspire_stats as ts
from tinspire_stats import (
    ArgumentError,
    DimensionMismatchError,
    DomainError,
    legacy,
    stat,
)
from tinspire_stats.catalog import ascii_name, catalog, lookup
from tinspire_stats.summary import five_numbers


@pytest.fixture(autouse=True)
def _reset_quartile_method():
    """Every test starts on the documented TI-Nspire convention."""
    ts.set_quartile_method("inclusive")
    yield
    ts.set_quartile_method("inclusive")


# ==========================================================================
# 1. name fidelity: the stat.* tables, function by function
# ==========================================================================
#: {function call: the exact ordered stat.* names the reference guide lists}.
DOCUMENTED_OUTPUTS = [
    ("OneVar([1,2,3,4])", lambda: ts.OneVar([1, 2, 3, 4]), "v Σx Σx² sx σx n "
     "MinX Q1X MedianX Q3X MaxX SSX"),
    ("TwoVar([1,2,3],[4,5,6])", lambda: ts.TwoVar([1, 2, 3], [4, 5, 6]),
     "v Σx Σx² sx σx w Σy Σy² sy σy Σxy r MinX Q1X MedianX Q3X MaxX "
     "MinY Q1Y MedianY Q3Y MaxY Σ(x-v)2 Σ(y-w)2 n"),
    ("FiveNumSummary([1,2,3,4])", lambda: ts.FiveNumSummary([1, 2, 3, 4]),
     "MinX Q1X MedianX Q3X MaxX"),
    ("LinRegMx", lambda: ts.LinRegMx([1, 2, 3, 4, 5], [2, 4, 6, 8, 10]),
     "RegEqn m b r² r Resid XReg YReg FreqReg"),
    ("LinRegBx", lambda: ts.LinRegBx([1, 2, 3, 4, 5], [2, 4, 6, 8, 10]),
     "RegEqn a b r² r Resid XReg YReg FreqReg"),
    ("QuadReg", lambda: ts.QuadReg([1, 2, 3, 4, 5], [1, 4, 9, 16, 25]),
     "RegEqn a b c R2 r² Resid XReg YReg FreqReg"),
    ("LnReg", lambda: ts.LnReg([1, 2, 3, 4, 5], [1, 2, 3, 4, 5]),
     "RegEqn a b r² r ResidTrans Resid XReg YReg FreqReg"),
    ("zInterval", lambda: ts.zInterval(2, 5.0, 25, 0.95),
     "CLower CUpper x ME sx n σ"),
    ("tInterval", lambda: ts.tInterval(5.0, 2.0, 25, 0.95),
     "CLower CUpper v ME df sx n σx x"),
    ("zTest", lambda: ts.zTest(5.0, 2.0, [3, 4, 5, 6, 7], None, 0),
     "z PVal x n sx"),
    ("tTest", lambda: ts.tTest(5.0, [3, 4, 5, 6, 7], None, 0),
     "t PVal df v sx n x"),
    ("tTest_2Samp", lambda: ts.tTest_2Samp(3.0, 1.0, 5, 4.0, 2.0, 6, 0, 0),
     "t PVal df v1 v2 sx1 sx2 n1 n2 x1 x2 x1-x2"),
    ("FTest_2Samp", lambda: ts.FTest_2Samp(1.5, 10, 2.5, 12, 0),
     "F PVal dfNumer dfDenom sx1 sx2 x1_bar x2_bar n1 n2"),
    ("chi2GOF", lambda: ts.chi2GOF([10, 20, 30], [20, 20, 20], 2),
     "χ² PVal df CompList"),
    ("chi22way", lambda: ts.chi22way([[10, 20], [30, 40]]),
     "χ² PVal df ExpMatrix CompMatrix"),
    ("ANOVA", lambda: ts.ANOVA([1, 2, 3, 4], [2, 3, 4, 5], [3, 4, 5, 6]),
     "F PVal df SS MS dfError SSError MSError sp xbarlist CLowerList CUpperList"),
    ("zInterval_1Prop", lambda: ts.zInterval_1Prop(42, 100),
     "CLower CUpper Ç ME n"),
    ("zTest_1Prop", lambda: ts.zTest_1Prop(0.5, 42, 100),
     "p0 z PVal Ç n"),
]


@pytest.mark.parametrize("label,call,want", DOCUMENTED_OUTPUTS,
                         ids=[c[0] for c in DOCUMENTED_OUTPUTS])
def test_documented_stat_names_are_present(label, call, want):
    """Every name in the guide's table for that function answers."""
    call()
    missing = [n for n in want.split() if n not in stat]
    assert not missing, f"{label}: stat has no {missing} (has {stat.keys()})"


@pytest.mark.parametrize("label,call,want", DOCUMENTED_OUTPUTS,
                         ids=[c[0] for c in DOCUMENTED_OUTPUTS])
def test_documented_stat_names_are_exhaustive(label, call, want):
    """...and nothing extra is published that the guide does not list.

    ``NAME_SUPERSETS`` deliberately publishes a second spelling for a handful of
    names, because two editions of the guide print them differently.  Those
    alternates are allowed here; anything *else* leaking into the group is not.
    """
    call()
    listed = set(want.split())
    allowed = set(listed)
    for key, alternates in ts.NAME_SUPERSETS.items():
        if key in listed:
            allowed.update(alternates)
    if {"v1", "v2"} <= listed:
        allowed.add("x1-x2")
    extra = [n for n in stat.keys() if n not in allowed]
    assert not extra, f"{label}: publishes undocumented {extra}"


def test_nothing_is_published_before_a_calculation():
    fresh = ts.StatGroup()
    assert fresh.keys() == []
    assert str(fresh.results) == "stat.results (empty)"


def test_stat_is_a_singleton_that_is_replaced_not_merged():
    ts.OneVar([1, 2, 3, 4])
    assert "Q1X" in stat
    ts.LinRegMx([1, 2, 3], [2, 4, 6])
    assert "Q1X" not in stat, "a new calculation must clear the old results"
    assert "m" in stat


# ==========================================================================
# 2. documented alternative spellings
# ==========================================================================
@pytest.mark.parametrize("typed,equal_to", [
    ("Σx2", "Σx²"),      # the HTML tables lose the superscript
    ("r2", "r²"),
    ("AdjR2", "AdjR²"),
    ("chi2", "χ²"),
    ("P Value", "PVal"),
    ("MedY", "MedianY"),
    ("ExpMat", "ExpMatrix"),
    ("CompMat", "CompMatrix"),
    ("Sigmax", "Σx"),    # ASCII convenience twins
    ("xbar", "v"),
    ("pbar", "Ç"),
])
def test_alternative_spellings_resolve(typed, equal_to):
    from tinspire_stats.statvar import canonical

    assert canonical(typed) == equal_to


def test_two_var_publishes_the_medy_spelling():
    ts.TwoVar([1, 2, 3], [10, 20, 30])
    assert stat.MedY == stat.MedianY


def test_bracket_and_attribute_access_agree():
    ts.OneVar([1, 2, 3, 4])
    assert stat["σx"] == stat.σx
    assert getattr(stat, "Σx²") == stat["Σx²"]


def test_missing_name_raises_attribute_error():
    ts.OneVar([1, 2, 3, 4])
    with pytest.raises(AttributeError):
        stat.definitely_not_a_stat


def test_as_ascii_gives_typeable_keys():
    ts.OneVar([1, 2, 3, 4])
    d = stat.as_ascii()
    assert "Sigmax" in d and "Σx" not in d
    assert d["Sigmax"] == stat["Σx"]


# ==========================================================================
# 3. the quartile convention -- Nspire (inclusive) vs TI-83/84 (exclusive)
# ==========================================================================
def test_inclusive_is_the_nspire_default():
    """OneVar on {1,2,3,4,5}: Nspire says Q1=2, TI-84 says Q1=1.5."""
    assert ts.get_quartile_method() == "inclusive"
    assert ts.OneVar([1, 2, 3, 4, 5]).Q1X == 2.0
    assert ts.OneVar([1, 2, 3, 4, 5]).Q3X == 4.0


def test_exclusive_reproduces_the_ti84_answer():
    ts.set_quartile_method("exclusive")
    assert ts.OneVar([1, 2, 3, 4, 5]).Q1X == 1.5
    assert ts.OneVar([1, 2, 3, 4, 5]).Q3X == 4.5


def test_the_two_conventions_agree_when_n_is_even():
    data = [3, 1, 4, 1, 5, 9]
    inclusive = five_numbers(data, "inclusive")
    exclusive = five_numbers(data, "exclusive")
    assert inclusive == exclusive


def test_the_nine_point_worked_example_from_ti_own_activity():
    """TI's Five Figure Summary activity: {1..9} -> Q1 = 3, the inclusive rule."""
    lo, q1, med, q3, hi = five_numbers([1, 2, 3, 4, 5, 6, 7, 8, 9])
    assert (lo, q1, med, q3, hi) == (1, 3, 5, 7, 9)


def test_bad_quartile_method_is_an_argument_error():
    with pytest.raises(ArgumentError):
        ts.set_quartile_method("moore-and-mccabe")


# ==========================================================================
# 4. void (empty) elements
# ==========================================================================
def test_void_is_none_or_the_sentinel():
    assert ts.is_void(None)
    assert ts.is_void(ts.VOID)
    assert not ts.is_void(0)
    assert not ts.is_void(float("nan")), "TI keeps nan and void distinct"


def test_a_void_anywhere_drops_that_index_everywhere():
    """The guide's rule: void in any list -> void in all of them, for that item."""
    ts.OneVar([1, 2, None, 4])
    assert stat.n == 3
    assert stat.v == pytest.approx(7 / 3)
    assert stat.MaxX == 4


def test_void_in_the_frequency_list_drops_the_matching_value():
    ts.OneVar([1, 2, 3, 4], [1, None, 1, 1])
    assert stat.n == 3
    assert "Σx" in stat


def test_void_pairs_drop_the_whole_row_in_a_regression():
    r = ts.LinRegMx([1, 2, 3, 4], [2, None, 6, 8])
    assert r.m == pytest.approx(2.0)
    assert r.b == pytest.approx(0.0)
    assert len(r.XReg) == 3


# ==========================================================================
# 5. the integer-frequency rule
# ==========================================================================
def test_spread_functions_insist_on_integer_frequencies():
    for fn in (ts.stDevSamp, ts.stDevPop, ts.varSamp, ts.varPop):
        with pytest.raises(DomainError):
            fn([1, 2, 3], [0.5, 0.5, 2.0])


def test_mean_accepts_fractional_frequencies():
    """A documented asymmetry: mean(x,px) works with px = {.25,.25,.25,.25}."""
    assert ts.mean([1, 2, 3, 4], [0.25, 0.25, 0.25, 0.25]) == pytest.approx(2.5)


def test_zero_and_negative_frequencies():
    ts.OneVar([1, 2, 3], [0, 2, 1])
    assert stat.n == 3
    with pytest.raises(DomainError):
        ts.OneVar([1, 2, 3], [1, -1, 2])


# ==========================================================================
# 6. Data form vs Stats form
# ==========================================================================
def test_t_interval_data_and_stats_forms_agree():
    data = [3.0, 4.0, 5.0, 6.0, 7.0]
    ts.tInterval(data, None, 0.95)
    from_data = stat.as_dict()
    ts.tInterval(stat.v, stat.sx, int(stat.n), 0.95)
    from_stats = stat.as_dict()
    for key in ("CLower", "CUpper", "ME", "df"):
        assert from_data[key] == pytest.approx(from_stats[key]), key


def test_z_interval_parks_the_mean_in_stat_x_not_stat_v():
    """The guide's own quirk: z procedures use x, t procedures use v."""
    ts.zInterval(2, [3, 4, 5, 6, 7], None, 0.95)
    assert "x" in stat and "v" not in stat
    ts.tInterval([3, 4, 5, 6, 7], None, 0.95)
    assert "v" in stat


def test_one_var_multi_list_suffixes_the_names():
    ts.OneVar(2, [1, 2, 3], [10, 20, 30])
    assert stat.v1 == pytest.approx(2.0)
    assert stat.v2 == pytest.approx(20.0)
    assert stat.v == pytest.approx(2.0), "list 1 mirrors into the plain names"


def test_category_and_include_restrict_the_data():
    # codes {1,1,2,2}; only category 2 takes part
    ts.OneVar([1, 2, 3, 4], None, [1, 1, 2, 2], [2])
    assert stat.n == 2
    assert stat.v == pytest.approx(3.5)


# ==========================================================================
# 7. RegEqn
# ==========================================================================
def test_reg_eqn_is_callable_and_stringifies_like_the_calculator():
    ts.LinRegMx([1, 2, 3, 4, 5], [5, 8, 11, 14, 17])
    assert stat.RegEqn(6) == pytest.approx(20.0)
    assert str(stat.RegEqn) == "y=3.·x+2."
    assert stat.RegEqn.symbolic == "y = m·x+b"


def test_reg_eqn_model_forms():
    ts.LinRegMx([1, 2, 3], [1, 2, 3])
    assert stat.RegEqn.symbolic == "y = m·x+b"
    ts.LinRegBx([1, 2, 3], [1, 2, 3])
    assert stat.RegEqn.symbolic == "y = a+b·x"


# ==========================================================================
# 8. CopyVar
# ==========================================================================
def test_copy_var_moves_a_value_into_a_named_variable():
    ts.OneVar([1, 2, 3, 4])
    ts.CopyVar(stat.v, "myMean")
    assert ts.VarStore["myMean"] == pytest.approx(2.5)


def test_copy_var_moves_a_whole_group():
    ts.OneVar([1, 2, 3, 4])
    ts.CopyVar(stat, "saveit.")
    copied = ts.VarStore["saveit."]
    assert copied.as_dict() == stat.as_dict()


def test_copy_to_stat_group_keeps_earlier_results_alive():
    ts.OneVar([1, 2, 3, 4])
    saved = ts.copy_to_stat_group()
    ts.LinRegMx([1, 2, 3], [2, 4, 6])
    assert "Q1X" in saved
    assert "Q1X" not in stat


# ==========================================================================
# 9. error surface
# ==========================================================================
def test_ti_error_messages_match_the_handheld_strings():
    assert DomainError.ti_message == "Domain error"
    assert DimensionMismatchError.ti_message == "Dimension mismatch"
    assert ArgumentError.ti_message == "Argument error"


def test_all_errors_derive_from_ti_error():
    for exc in (DomainError, DimensionMismatchError, ArgumentError, ts.DataTypeError):
        assert issubclass(exc, ts.TIError)


@pytest.mark.parametrize("fn,args", [
    (ts.mean, ([],)),
    (ts.median, ([],)),
    (ts.OneVar, ([],)),
    (ts.stDevSamp, ([5],)),
])
def test_degenerate_input_raises_a_domain_error(fn, args):
    with pytest.raises(DomainError):
        fn(*args)


def test_unequal_lengths_raise_dimension_mismatch():
    with pytest.raises(DimensionMismatchError):
        ts.TwoVar([1, 2, 3], [1, 2])
    with pytest.raises(DimensionMismatchError):
        ts.OneVar([1, 2, 3], [1, 2])


# ==========================================================================
# 10. list math regression pins
# ==========================================================================
def test_sort_leaves_void_at_the_bottom_in_both_directions():
    assert ts.SortA([3, 1, None, 2]) == [1, 2, 3, None]
    assert ts.SortD([3, 1, None, 2]) == [3, 2, 1, None]


def test_sort_carries_the_companion_lists_along():
    xs, ys = ts.SortA([3, 1, 2], [30, 10, 20])
    assert xs == [1, 2, 3]
    assert ys == [10, 20, 30]


def test_dlist_is_one_shorter_than_its_input():
    assert ts.ΔList([1, 4, 9, 16]) == [3, 5, 7]


def test_cumulative_sum():
    assert ts.cumulativeSum([1, 2, 3, 4]) == [1, 3, 6, 10]


def test_freq_table_to_list_rejects_fractional_frequencies():
    assert ts.freqTable_to_list([1, 2], [2, 3]) == [1, 1, 2, 2, 2]
    with pytest.raises(DomainError):
        ts.freqTable_to_list([1, 2], [1.5, 2])


def test_frequency_returns_one_more_bin_than_the_bin_list():
    """Guide: bins are {?≤b1, b1<?≤b2, ..., b(n-1)<?≤b(n), b(n)>?}."""
    out = ts.frequency([1, 2, 3, 4, 5], [2, 4])
    assert out == [2, 2, 1]          # ≤2 | 2<x≤4 | >4
    assert len(out) == 2 + 1


def test_sum_uses_one_based_inclusive_bounds():
    assert ts.sum([1, 2, 3, 4, 5], 2, 4) == 9


def test_corr_mat_is_symmetric_with_unit_diagonal():
    m = ts.corrMat([1, 2, 3, 4], [2, 4, 6, 8], [4, 3, 2, 1])
    assert m[0][0] == pytest.approx(1.0)
    assert m[0][1] == pytest.approx(1.0)
    assert m[0][2] == pytest.approx(-1.0)


# ==========================================================================
# 11. criteria parsing (countif / sumIf)
# ==========================================================================
@pytest.mark.parametrize("criteria,expected", [
    ("?>4", 5),
    ("> 4", 5),           # bare shorthand
    ("?≤3", 3),
    ("3≥?", 3),           # placeholder on the right
    (2, 1),               # a bare value means equality
    ("2≤?≤4", 3),         # chained
    ("?<2 or ?>6", 4),
    ("?>2 and ?<7", 4),
    ([1, 5, 9], 3),       # membership
])
def test_countif_criteria(criteria, expected):
    assert ts.countif([1, 2, 3, 4, 5, 6, 7, 8, 9], criteria) == expected


def test_sumif_second_list_follows_the_criteria_of_the_first():
    assert ts.sumIf([1, 2, 3, 4], "?>2", [10, 20, 30, 40]) == 70


def test_a_non_relational_string_is_compared_for_equality():
    """The guide: Criteria may be "a value, expression, or string"."""
    assert ts.countif([1, 2, 3], "abc") == 0
    assert ts.countif(["a", "b", "a"], "a") == 2


# ==========================================================================
# 12. distributions: pinned values and inverse round-trips
# ==========================================================================
@pytest.mark.parametrize("fn,pdf,cdf", [
    (("norm",), ts.normPdf, ts.normCdf),
])
def test_placeholder(fn, pdf, cdf):  # pragma: no cover - keeps pytest quiet
    pass


def test_normal_functions_round_trip():
    assert ts.invNorm(0.975) == pytest.approx(1.959963985, abs=1e-8)
    assert ts.normCdf(-9e999, ts.invNorm(0.3)) == pytest.approx(0.3, abs=1e-10)
    assert ts.normCdf(-9e999, 0.0) == pytest.approx(0.5)
    assert ts.normPdf(0) == pytest.approx(1 / math.sqrt(2 * math.pi))


def test_normal_interval_and_scale():
    assert ts.normCdf(70, 79, 75, 3) == pytest.approx(
        ts.normCdf(-9e999, 79, 75, 3) - ts.normCdf(-9e999, 70, 75, 3)
    )


def test_t_distribution_round_trip():
    assert ts.invt(0.975, 20) == pytest.approx(2.085963447, abs=1e-7)
    assert ts.tCdf(-9e999, ts.invt(0.4, 7), 7) == pytest.approx(0.4, abs=1e-10)
    assert ts.tCdf(-9e999, 0.0, 5) == pytest.approx(0.5, abs=1e-9)


def test_chi_square_round_trip():
    assert ts.invχ2(0.95, 5) == pytest.approx(11.07049769, abs=1e-6)
    assert ts.χ2Cdf(0, ts.invχ2(0.3, 9), 9) == pytest.approx(0.3, abs=1e-9)


def test_f_distribution_round_trip():
    assert ts.invF(0.95, 3, 7) == pytest.approx(4.346831, abs=1e-5)
    assert ts.FCdf(0, ts.invF(0.4, 4, 11), 4, 11) == pytest.approx(0.4, abs=1e-9)


def test_binomial_cdf_matches_cumulative_pdf():
    total = sum(ts.binomPdf(12, 0.3, k) for k in range(13))
    assert total == pytest.approx(1.0)
    assert ts.binomCdf(12, 0.3, 5) == pytest.approx(
        sum(ts.binomPdf(12, 0.3, k) for k in range(6))
    )


def test_binomial_range_and_inverse():
    assert ts.binomCdf(10, 0.4, 3, 7) == pytest.approx(
        sum(ts.binomPdf(10, 0.4, k) for k in range(3, 8))
    )
    k = ts.invBinom(0.5, 20, 0.4)
    assert ts.binomCdf(20, 0.4, k) >= 0.5
    assert ts.binomCdf(20, 0.4, k - 1) < 0.5


def test_inv_binom_output_form_gives_a_matrix():
    assert ts.invBinom(0.5, 20, 0.4, 1) == [[ts.invBinom(0.5, 20, 0.4)]]


def test_inv_binom_n_answers_the_guide_free_throw_question():
    n = ts.invBinomN(0.99, 0.7, 50)
    assert 1 - ts.binomCdf(n, 0.7, 49) >= 0.99
    assert 1 - ts.binomCdf(n - 1, 0.7, 49) < 0.99


def test_poisson_and_geometric():
    assert ts.poissPdf(3, 0) == pytest.approx(math.exp(-3))
    assert ts.poissCdf(3, 100) == pytest.approx(1.0, abs=1e-12)
    assert ts.geomPdf(0.25, 1) == pytest.approx(0.25)
    assert ts.geomCdf(0.25, 4) == pytest.approx(1 - 0.75 ** 4)
    assert ts.geomPdf(0.5, 0) == 0.0, "no probability before the first trial"


def test_continuous_pdf_accepts_a_list():
    got = ts.normPdf([0, 1, 2])
    assert got == [pytest.approx(ts.normPdf(v)) for v in (0, 1, 2)]


def test_domain_errors_in_distributions():
    with pytest.raises(DomainError):
        ts.normPdf(0, 0, 0)
    with pytest.raises(DomainError):
        ts.invNorm(0)
    with pytest.raises(DomainError):
        ts.tPdf(1, 0)
    with pytest.raises(DomainError):
        ts.binomPdf(5, 1.5)


# ==========================================================================
# 13. random functions
# ==========================================================================
def test_rand_seed_makes_output_reproducible():
    ts.RandSeed(42)
    a = ts.rand(5)
    ts.RandSeed(42)
    b = ts.rand(5)
    assert a == b
    assert all(0 <= v < 1 for v in a)


def test_rand_int_respects_bounds():
    ts.RandSeed(1)
    vals = ts.randInt(1, 6, 200)
    assert all(1 <= v <= 6 for v in vals)
    assert all(v == int(v) for v in vals)


def test_rand_samp_replacement_is_the_default():
    ts.RandSeed(99)
    with_repl = ts.randSamp([1, 2, 3, 4, 5], 5)
    ts.RandSeed(99)
    with_repl_explicit = ts.randSamp([1, 2, 3, 4, 5], 5, 0)
    assert with_repl == with_repl_explicit
    assert len(with_repl) == 5


def test_rand_samp_without_replacement_does_not_repeat():
    ts.RandSeed(99)
    out = ts.randSamp([1, 2, 3, 4, 5], 5, 1)
    assert sorted(out) == [1, 2, 3, 4, 5]
    with pytest.raises(DomainError):
        ts.randSamp([1, 2, 3], 4, 1)


# ==========================================================================
# 14. catalog integrity
# ==========================================================================
def test_every_ti_function_has_a_docstring_signature():
    for row in catalog():
        if row["kind"] == "ti":
            assert row["signature"], f"{row['name']} has no signature line"


def test_catalog_kinds_are_partitioned():
    kinds = {r["kind"] for r in catalog()}
    assert kinds <= {"ti", "legacy", "internal"}


def test_catalog_names_are_unique():
    names = [r["name"] for r in catalog()]
    assert len(names) == len(set(names))


def test_registry_finds_functions_by_every_spelling():
    assert lookup("OneVar") is ts.OneVar
    assert lookup("freqTable►list") is ts.freqTable_to_list
    assert lookup("χ²Pdf") is ts.χ2Pdf


def test_ascii_names_needed_by_stat_as_ascii_all_exist():
    for row in catalog():
        assert ascii_name(row["ti"]).isascii(), row["ti"]


def test_every_ti_function_has_an_importable_ascii_twin():
    """``ascii_name`` must not invent a spelling that does not exist.

    ``χ`` transliterates to ``chi``, which would have turned ``invχ²`` into the
    non-existent ``invchi2``; the package exports ``invChi2``.
    """
    for row in catalog():
        if row["kind"] != "ti":
            continue
        twin = ascii_name(row["ti"])
        assert twin.isidentifier(), f"{row['ti']} -> {twin} is not an identifier"
        assert hasattr(ts, twin), (
            f"{row['ti']} maps to {twin!r}, which the package does not export"
        )


def test_public_api_is_importable_and_callable():
    for name in ts.__all__:
        assert hasattr(ts, name), name


# ==========================================================================
# 15. the legacy shim is honest about not being TI-Nspire
# ==========================================================================
def test_legacy_names_are_not_in_the_nspire_catalogue():
    nspire = {r["name"] for r in catalog() if r["kind"] == "ti"}
    assert not (legacy.NAMES & nspire & {"stdev", "stdDev", "variance"})


def test_legacy_forwards_to_the_real_implementation():
    assert legacy.stdev.__name__ == "stDevSamp"
    assert legacy.stdev([1, 2, 3, 4]) == pytest.approx(ts.stDevSamp([1, 2, 3, 4]))


def test_legacy_notes_explain_the_rename():
    notes = legacy.notes()
    assert "stDevSamp" in notes["stdev"]
    assert "PwrReg" in notes


def test_legacy_table_is_printable():
    text = legacy.table()
    assert "alias" in text and "stDevSamp" in text


def test_unknown_legacy_name_gives_a_helpful_error():
    with pytest.raises(AttributeError) as err:
        legacy.no_such_alias
    message = str(err.value)
    assert "no_such_alias" in message
    assert "stdev" in message, "the error should list the names that do exist"


# ==========================================================================
# 15b. every non-primary name says which kind of non-primary it is
# ==========================================================================
def test_legacy_kinds_are_exactly_the_declared_five():
    assert set(legacy.KINDS) == {
        legacy.Kind.DOCUMENTED,
        legacy.Kind.KEYBOARD,
        legacy.Kind.RETIRED,
        legacy.Kind.MENU,
        legacy.Kind.EXTENSION,
    }


def test_every_registered_name_has_a_kind_and_evidence():
    for name in list(legacy.BINDINGS) + list(legacy.DOCUMENTED_VARIANTS):
        assert legacy.kind_of(name) in legacy.KINDS, name
        assert legacy.evidence(name).strip(), f"{name} has no recorded evidence"


def test_documented_variants_are_the_only_ones_exempt_from_quarantine():
    """``chi2Pdf`` is a name TI prints; ``stdev`` is not.

    The first version of this package filed both under "TI-83/84 spelling",
    which is false for ``chi2Pdf`` -- the guide's χ2Pdf entry prints
    ``chi2Pdf(XVal,df)`` as its second signature line.  Keeping the two apart is
    the point of the split, so it gets a test.
    """
    documented = {n for n in legacy.DOCUMENTED_VARIANTS}
    assert {"chi2Pdf", "chi2Cdf", "invChi2"} <= documented
    assert documented.isdisjoint(legacy.NAMES), (
        "a documented spelling must not also be filed as quarantined"
    )
    for name in documented:
        assert legacy.kind_of(name) == legacy.Kind.DOCUMENTED


def test_keyboard_spellings_are_not_claimed_to_be_guide_names():
    for name in ("invT", "Fpdf", "Fcdf", "poissonPdf", "poissonCdf"):
        assert legacy.kind_of(name) == legacy.Kind.KEYBOARD
    for name in ("stdev", "stdDev", "variance", "PwrReg"):
        assert legacy.kind_of(name) == legacy.Kind.RETIRED


def test_root_alias_standings_match_the_registry():
    """The root's extra spellings are declared, and the declaration is checked.

    Without this, an alias can be exported at the root under one label and
    described in ``legacy`` under another -- which is exactly how ``chi2Pdf``
    ended up described two contradictory ways.
    """
    for alias, (target, standing) in ts.ROOT_ALIASES.items():
        assert getattr(ts, alias) is target, alias
        assert legacy.kind_of(alias) == standing, (
            f"{alias} is exported as {standing!r} but legacy calls it "
            f"{legacy.kind_of(alias)!r}"
        )


def test_catalog_reports_every_quarantined_name_exactly_once():
    rows = catalog()
    reported = [r["name"] for r in rows if r["kind"] == "legacy"]
    assert sorted(reported) == sorted(legacy.NAMES)
    assert len(reported) == len(set(reported))


def test_catalog_legacy_rows_carry_their_precise_kind():
    for row in catalog():
        if row["kind"] != "legacy":
            assert row["legacy_kind"] is None and row["evidence"] == ""
            continue
        assert row["legacy_kind"] in legacy.KINDS, row["name"]
        assert row["evidence"].strip(), row["name"]


def test_lookup_finds_legacy_names_but_does_not_disguise_them():
    assert lookup("stdev").__name__ == "stDevSamp"
    assert lookup("PwrReg").__name__ == "PowerReg"
    assert lookup("TwoSampleTTest").__name__ == "tTest_2Samp"


def test_no_non_nspire_name_is_defined_in_an_implementation_module():
    """There is one registry, not three.

    ``stdev``, the ``TwoSample*`` labels and ``invT`` used to be defined in
    ``listmath``, ``inference`` and ``distributions`` respectively *as well as*
    in ``legacy``.  Two definitions of one alias means two answers waiting to
    disagree, and it silently changed how ``catalog()`` classified them.

    ``EXTENSION`` names are exempt: the implementation of ``SortA_inplace``
    belongs in ``listmath`` next to ``SortA``.  What must not be duplicated is a
    *renaming* -- a second name for a function that already has one.
    """
    import importlib
    import inspect

    renames = {n for n in legacy.NAMES if legacy.kind_of(n) != legacy.Kind.EXTENSION}
    assert renames, "the registry should hold renaming aliases, not only extensions"

    for module_name in ("listmath", "summary", "regress", "distributions",
                        "inference", "statvar", "_core"):
        module = importlib.import_module(f"tinspire_stats.{module_name}")
        for attr, obj in vars(module).items():
            if attr.startswith("_") or not inspect.isroutine(obj):
                continue
            assert attr not in renames, (
                f"{attr} is a legacy renaming but is defined in {module_name}; "
                "it belongs in legacy.BINDINGS only"
            )


def test_catalog_ti_rows_are_never_legacy_names():
    ti = {r["name"] for r in catalog() if r["kind"] == "ti"}
    assert ti.isdisjoint(legacy.NAMES)


# ==========================================================================
# 16. doctests
# ==========================================================================
MODULES_WITH_DOCTESTS = [
    "tinspire_stats",
    "tinspire_stats._core",
    "tinspire_stats.statvar",
    "tinspire_stats.listmath",
    "tinspire_stats.summary",
    "tinspire_stats.regress",
    "tinspire_stats.distributions",
    "tinspire_stats.inference",
    "tinspire_stats.catalog",
    "tinspire_stats.legacy",
]


@pytest.mark.parametrize("module_name", MODULES_WITH_DOCTESTS)
def test_doctests_in_every_module_pass(module_name):
    """Every example in every docstring is a real, checked claim.

    Without this the docstrings drift: the ``RegEqn`` example claimed
    ``'y=3.·x+2.'`` for a while before the formatter actually printed that.
    """
    import importlib

    module = importlib.import_module(module_name)
    result = doctest.testmod(module, verbose=False, optionflags=doctest.ELLIPSIS)
    assert result.failed == 0, f"{module_name}: {result.failed} doctest failures"


def test_doctests_actually_ran():
    """A guard against the parametrisation silently covering nothing."""
    import importlib

    total = 0
    for name in MODULES_WITH_DOCTESTS:
        result = doctest.testmod(
            importlib.import_module(name), verbose=False, optionflags=doctest.ELLIPSIS
        )
        total += result.attempted
    assert total > 10, f"only {total} doctest examples ran -- did the docstrings vanish?"
