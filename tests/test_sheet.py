"""The Lists & Spreadsheet page's grid and its list variables.

The page exists, in a statistics package, for one reason: naming a column must
make ``OneVar <name>`` work on the Calculator page.  So the tests here are
mostly about that promise -- the name becomes a variable, the values arrive in
row order, a void stays void, and the Actions/Data menu items do what the
handheld does.
"""

from __future__ import annotations

import pytest

import tinspire_stats as ts
from tinspire_stats import sheet as sh


@pytest.fixture()
def s():
    return sh.Sheet(rows=10)


# ==========================================================================
# 1. the grid
# ==========================================================================
def test_a_fresh_sheet_is_26_columns_of_nothing(s):
    assert len(s.columns) == 26
    assert list(s.columns)[:3] == ["A", "B", "C"]
    assert s.value_at("A", 1) is None
    assert s.bindings() == {}


def test_typing_a_number_into_a_cell(s):
    s.set_cell("A", 1, "27.5")
    s.set_cell("A", 2, "26")
    assert s.value_at("A", 1) == 27.5
    assert s.value_at("A", 2) == 26


def test_words_are_not_list_elements(s):
    """A column is a list of numbers; text in it is void, not an error."""
    s.set_cell("A", 1, "height")
    s.set_cell("A", 2, "27.5")
    assert s.value_at("A", 1) is None
    # the hole stays a hole -- it is not closed up
    assert s.columns["A"].values(10) == [None, 27.5]


def test_an_empty_cell_can_be_made_again(s):
    s.set_cell("A", 1, "5")
    s.set_cell("A", 1, "")
    assert s.value_at("A", 1) is None


def test_typing_below_the_grid_grows_it(s):
    assert s.rows == 10
    s.set_cell("A", 14, "3")
    assert s.rows == 14


# ==========================================================================
# 2. naming a column -- the whole point of the page
# ==========================================================================
def test_naming_a_column_defines_a_list_variable(s):
    s.set_cell("A", 1, "27.5")
    s.set_cell("A", 2, "26")
    s.set_name("A", "footlength")
    assert s.bindings() == {"footlength": [27.5, 26]}


def test_the_named_list_drives_the_statistics_functions(s):
    """The handbook's own example: mshoe, mhand, fshoe."""
    for row, value in enumerate([11, 8, 7, 12, 9.5], start=1):
        s.set_cell("A", row, str(value))
    s.set_name("A", "mshoe")
    values = s.bindings()["mshoe"]

    result = ts.OneVar(values)
    assert list(result.keys()) == list(ts.OneVar([11, 8, 7, 12, 9.5]).keys())
    assert result.v == pytest.approx(sum([11, 8, 7, 12, 9.5]) / 5)
    assert result.n == 5
    assert result.MinX == 7 and result.MaxX == 12


def test_two_named_columns_pair_up(s):
    for row, (a, b) in enumerate([(11, 27), (8, 21), (7, 20)], start=1):
        s.set_cell("A", row, str(a))
        s.set_cell("B", row, str(b))
    s.set_name("A", "mshoe")
    s.set_name("B", "mhand")
    values = s.bindings()
    r = ts.LinRegBx(values["mshoe"], values["mhand"])
    assert r.a is not None and r.b is not None
    assert "r²" in ts.stat


def test_a_name_that_is_not_a_variable_name_is_refused(s):
    with pytest.raises(sh.SheetError):
        s.set_name("A", "2fast")
    with pytest.raises(sh.SheetError):
        s.set_name("A", "two words")


def test_a_name_the_calculator_already_uses_is_refused(s):
    """TI: "You cannot use a preassigned variable or function name".

    The refusal has to happen at the point of typing the name.  A column
    called `mean` would otherwise look named and be unreachable from the
    Calculator page, which resolves `mean` to the function first.
    """
    for taken in ("mean", "min", "OneVar", "stat", "pi", "e", "ans"):
        with pytest.raises(sh.SheetError, match="already uses"):
            s.set_name("A", taken)
    # and the name is not left behind by the refusal
    assert s.names() == {}


def test_the_reserved_names_are_the_calculators_own(s):
    """Derived from the namespace, not from a second list to keep in step."""
    reserved = sh.reserved_names()
    assert "mean" in reserved and "stat" in reserved and "e" in reserved
    assert "mshoe" not in reserved and "die1" not in reserved


def test_two_columns_cannot_share_a_name(s):
    s.set_name("A", "data")
    with pytest.raises(sh.SheetError):
        s.set_name("B", "data")
    s.set_name("A", "data")          # renaming itself is fine


def test_an_empty_named_column_defines_nothing(s):
    s.set_name("A", "nothing")
    assert s.bindings() == {}


def test_a_void_in_the_middle_stays_a_void(s):
    """OneVar must see the hole: that is what voids the rest of the row."""
    for row, value in enumerate(["1", "", "3", "4", "5"], start=1):
        s.set_cell("A", row, value)
    s.set_name("A", "gappy")
    assert s.bindings()["gappy"] == [1, None, 3, 4, 5]
    ts.OneVar(s.bindings()["gappy"])
    assert ts.stat.n == 4


def test_trailing_voids_are_not_part_of_the_list(s):
    for row, value in enumerate(["1", "2", "3"], start=1):
        s.set_cell("A", row, value)
    s.set_name("A", "short")
    assert s.bindings()["short"] == [1, 2, 3]


# ==========================================================================
# 3. formulas
# ==========================================================================
def test_a_column_reference_is_the_same_row(s):
    """TI's own example: column D holds =b[]/a[] and D1 is B1/A1."""
    s.set_cell("A", 1, "11")
    s.set_cell("B", 1, "27")
    s.set_formula("D", "=b[]/a[]")
    assert s.value_at("D", 1) == pytest.approx(27 / 11)


def test_arithmetic_in_a_cell(s):
    s.set_cell("A", 1, "=2+3*4")
    assert s.value_at("A", 1) == 14


def test_a_formula_can_call_a_function(s):
    for row, value in enumerate(["1", "2", "3"], start=1):
        s.set_cell("A", row, value)
    s.set_formula("B", "=mean(a[])")
    assert s.value_at("B", 1) == pytest.approx(2.0)


def test_a_list_named_like_a_cell_reference_survives(s):
    """die1 must not be read as the cell e1 -- TI's own dice example.

    The rewrite is checked directly, because the failure mode is a silently
    wrong `e1` rather than an error.
    """
    assert sh._rewrite("=die1+die2") == "=die1+die2"
    assert sh._rewrite("=a1+b2") == "=__cell_A_1+__cell_B_2"
    # a column is not a cell: `a[]` binds the whole thing, not row 0 of it
    assert sh._rewrite("=b[]/a[]") == "=__col_B/__col_A"

    # and a named column works whole, as a list
    for row, value in enumerate(["1", "2", "3"], start=1):
        s.set_cell("A", row, value)
    s.set_name("A", "die1")
    s.set_formula("B", "=sum(die1)")
    assert s.value_at("B", 1) == 6


def test_a_whole_column_is_element_wise(s):
    """TI's own worked example, continued to the row it is usually quoted without.

    The guide shows the formula row of column D holding ``=b[]/a[]`` and D1
    coming out as ``B1/A1`` (27/11).  A whole-column reference has to mean the
    whole column, or D2 is not ``B2/A2`` -- and if it were read as "the cell in
    this row", ``mean(a[])`` would be the mean of one number.
    """
    s.set_cell("A", 1, "11")
    s.set_cell("A", 2, "16")
    s.set_cell("B", 1, "27")
    s.set_cell("B", 2, "40")
    s.set_formula("D", "=b[]/a[]")
    assert s.value_at("D", 1) == pytest.approx(27 / 11)
    assert s.value_at("D", 2) == pytest.approx(40 / 16)


def test_a_bare_letter_is_a_variable_and_only_brackets_name_a_column(s):
    """TI's syntax table: "A -- this syntax never refers to column A".

    Column A holds data but is named `a`, so the bare `a` in the formula is the
    variable; the column is reachable only as `a[]`.
    """
    for row, value in enumerate(["10", "20"], start=1):
        s.set_cell("A", row, value)
    s.set_name("A", "a")
    s.set_formula("C", "=sum(a)")
    assert s.value_at("C", 1) == 30
    s.set_formula("C", "=sum(a[])")
    assert s.value_at("C", 1) == 30
    # the difference shows up when the variable and the column are not the same
    s.set_formula("C", "=a[]*2")
    assert [s.value_at("C", r) for r in (1, 2)] == [20, 40]


def test_the_apostrophe_names_the_variable_not_the_cell(s):
    """`'a1` is the variable `a1`; `a1` is always the cell.

    Without the escape a list named `a1` would be unreachable, because the cell
    pattern claims that spelling first.  Column A holds 1, 2, 3 and is named
    `a1`, so the variable is the whole list and the cell is just its first item.
    """
    for row, value in enumerate(["1", "2", "3"], start=1):
        s.set_cell("A", row, value)
    s.set_name("A", "a1")

    s.set_formula("C", "=sum('a1)")        # the variable: 1 + 2 + 3
    assert s.value_at("C", 1) == 6
    s.set_formula("C", "=a1")              # the cell A1
    assert s.value_at("C", 1) == 1


def test_a_void_propagates_through_a_formula(s):
    """A hole in the data is a hole in the answer, not an error."""
    s.set_cell("A", 1, "2")
    s.set_cell("A", 3, "4")
    s.set_formula("B", "=a[]*10")
    assert s.value_at("B", 1) == 20
    assert s.value_at("B", 2) is None
    assert s.value_at("B", 3) == 40


def test_columns_of_different_lengths_are_an_error(s):
    s.set_cell("A", 1, "1")
    s.set_cell("A", 2, "2")
    s.set_cell("B", 1, "1")
    s.set_formula("C", "=b[]/a[]")
    with pytest.raises(sh.SheetError):
        s.value_at("C", 1)


def test_an_absolute_reference_does_not_shift(s):
    s.set_cell("A", 1, "100")
    s.set_cell("A", 2, "=2*$a$1")
    assert s.value_at("A", 2) == 200


def test_a_circular_formula_is_reported(s):
    s.set_formula("A", "=a[]")
    with pytest.raises(sh.SheetError):
        s.value_at("A", 1)


def test_dividing_by_zero_is_reported(s):
    s.set_cell("A", 1, "0")
    s.set_formula("B", "=1/a[]")
    with pytest.raises(sh.SheetError):
        s.value_at("B", 1)


def test_a_formula_may_not_reach_the_host(s):
    s.set_cell("A", 1, "=__import__('os').getcwd()")
    with pytest.raises(sh.SheetError):
        s.value_at("A", 1)


def test_typing_a_value_over_a_formula_drops_the_formula(s):
    s.set_formula("B", "=a[]*2")
    s.set_cell("A", 1, "3")
    assert s.value_at("B", 1) == 6
    s.set_cell("B", 1, "99")
    assert s.columns["B"].formula == ""
    assert s.value_at("B", 1) == 99


# ==========================================================================
# 4. Fill Down -- and the recurrence it exists for
# ==========================================================================
def test_fill_down_copies_a_plain_value(s):
    s.set_cell("A", 1, "7")
    assert s.fill_down("A", 1, 4) == 3
    assert s.columns["A"].values(10) == [7, 7, 7, 7]


def test_fill_down_shifts_relative_row_references(s):
    """The compound-interest recipe: =a1*1.05 in A2, filled down."""
    s.set_cell("A", 1, "1000")
    s.set_cell("A", 2, "=a1*1.05")
    s.fill_down("A", 2, 4)
    assert s.columns["A"].values(10)[:4] == pytest.approx(
        [1000, 1050, 1102.5, 1157.625])


def test_fill_down_leaves_pinned_references_alone(s):
    s.set_cell("A", 1, "1000")
    s.set_cell("A", 2, "=a1+$a$1")          # A2 = 1000 + 1000
    s.fill_down("A", 2, 3)                  # A3 = a2 + $a$1 = 2000 + 1000
    assert s.columns["A"].values(10)[:3] == [1000, 2000, 3000]


def test_shift_for_fill_is_the_documented_rule():
    assert sh.shift_for_fill("=a1*2", 1, 3) == "=a3*2"
    assert sh.shift_for_fill("=a$1*2", 1, 3) == "=a$1*2"
    assert sh.shift_for_fill("=a1+b2", 1, 2) == "=a2+b3"
    # a whole-column reference is already relative to the row it runs in
    assert sh.shift_for_fill("=b[]/a[]", 1, 5) == "=b[]/a[]"


def test_filling_up_past_row_one_leaves_the_reference_alone():
    assert sh.shift_for_fill("=a1", 3, 1) == "=a1"


def test_fill_down_from_an_empty_cell_says_so(s):
    with pytest.raises(sh.SheetError):
        s.fill_down("A", 3, 6)


# ==========================================================================
# 5. the other Actions and Data menu items
# ==========================================================================
def test_sort_by_a_column_carries_the_rows(s):
    for row, (a, b) in enumerate([(3, "c"), (1, "a"), (2, "b")], start=1):
        s.set_cell("A", row, str(a))
        s.set_cell("B", row, b)
    s.sort_by("A")
    assert s.columns["A"].values(3) == [1, 2, 3]
    # the row moved as a unit, so B's raw text follows A
    assert [s.raw_at("B", r) for r in (1, 2, 3)] == ["a", "b", "c"]


def test_sort_descending(s):
    for row, value in enumerate([3, 1, 2], start=1):
        s.set_cell("A", row, str(value))
    s.sort_by("A", ascending=False)
    assert s.columns["A"].values(3) == [3, 2, 1]


def test_voids_sort_last_either_way(s):
    for row, value in enumerate([2, "", 1], start=1):
        s.set_cell("A", row, value)
    s.sort_by("A")
    assert s.columns["A"].values(3) == [1, 2]
    s.sort_by("A", ascending=False)
    assert s.columns["A"].values(3) == [2, 1]


def test_move_column_takes_the_name_with_it(s):
    s.set_cell("A", 1, "1")
    s.set_cell("C", 1, "3")
    s.set_name("A", "first")
    s.set_name("C", "third")
    s.move_column("A", "C")
    # A moves into C's slot and B slides left, so the order becomes B, C, A
    assert s.raw_at("B", 1) == "3"
    assert s.raw_at("C", 1) == "1"
    assert s.names()["first"] == "C"
    assert s.names()["third"] == "B"


def test_resize_drops_rows_past_the_end(s):
    s.set_cell("A", 5, "9")
    s.resize(3)
    assert s.rows == 3
    assert s.value_at("A", 5) is None
    with pytest.raises(sh.SheetError):
        s.resize(0)


def test_recalculate_recomputes(s):
    s.set_cell("A", 1, "2")
    s.set_formula("B", "=a[]*10")
    assert s.value_at("B", 1) == 20
    s.set_cell("A", 1, "5")                # a new edit clears the cache anyway
    assert s.value_at("B", 1) == 50
    s.recalculate()
    assert s.value_at("B", 1) == 50


# ==========================================================================
# 6. the screen's snapshot
# ==========================================================================
def test_the_snapshot_lists_every_column_and_the_bindings(s):
    s.set_cell("A", 1, "27.5")
    s.set_name("A", "footlength")
    snap = s.snapshot()
    assert snap["rows"] == 10 and len(snap["columns"]) == 26
    first = snap["columns"][0]
    assert first["letter"] == "A" and first["name"] == "footlength"
    assert first["cells"]["1"] == "27.5"
    assert snap["bindings"] == {"footlength": [27.5]}


def test_the_snapshot_shows_whole_numbers_without_a_decimal_tail(s):
    s.set_cell("A", 1, "4")
    s.set_cell("A", 2, "4.25")
    cells = s.snapshot()["columns"][0]["cells"]
    assert cells["1"] == "4"
    assert cells["2"] == "4.25"


def test_a_void_inside_the_list_is_an_underscore(s):
    """"Any empty (void) element in a list is displayed as an underscore".

    Only inside the list, though: past the end of the data the cell is blank,
    because there is no element there to be void.
    """
    for row, value in enumerate(["1", "", "3"], start=1):
        s.set_cell("A", row, value)
    cells = s.snapshot()["columns"][0]["cells"]
    assert cells["1"] == "1"
    assert cells["2"] == "_"
    assert cells["3"] == "3"
    assert cells["4"] == ""          # past the end of the list
    assert cells[str(s.rows)] == ""


def test_display_of_a_void_is_the_glyph():
    assert sh.display(None) == sh.VOID_GLYPH == "_"
    assert sh.display(7) == "7"
    assert sh.display(7.5) == "7.5"


def test_clear_all_empties_the_grid(s):
    s.set_cell("A", 1, "1")
    s.set_name("A", "gone")
    s.clear_all()
    assert s.bindings() == {}
    assert s.rows == 20


# ==========================================================================
# 7. the letters
# ==========================================================================
def test_column_letters_round_trip():
    for index in range(sh.MAX_COLUMNS):
        assert sh.index_of(sh.letter_of(index)) == index
    assert sh.letter_of(0) == "A" and sh.letter_of(25) == "Z"


def test_an_impossible_column_letter_is_refused():
    for bad in ("AA", "1", "", "!"):
        assert not sh.valid_column_letter(bad)
        with pytest.raises(sh.SheetError):
            sh.index_of(bad)


def test_list_name_rules():
    for good in ("mshoe", "die1", "a", "x_2", "Freq"):
        assert sh.valid_list_name(good), good
    for bad in ("2fast", "two words", "", "_leading", "a-b"):
        assert not sh.valid_list_name(bad), bad
