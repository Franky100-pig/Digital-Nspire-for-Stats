"""The browser engine's spreadsheet, and the promise it keeps.

The grid exists in a statistics package for one reason: naming a column has to
make the Calculator page able to use it.  These tests drive the engine the way
the browser bridge does -- a dict in, a dict out -- so that promise is checked
without a browser anywhere near it, and so a change to the grid cannot quietly
break the page it was built for.
"""

from __future__ import annotations

import pytest

import engine


@pytest.fixture(autouse=True)
def fresh_session():
    """Each test starts with a blank calculator and a blank grid."""
    engine._la_dispatch({"op": "reset"})
    yield
    engine._la_dispatch({"op": "reset"})


def sheet(**payload):
    return engine._la_dispatch({"op": "sheet", **payload})


def run(text):
    return engine._la_dispatch({"op": "run", "input": text})


def var(result, name):
    """One stat.results row, by its TI name."""
    for row in result.get("vars") or []:
        if row["name"] == name:
            return row
    raise AssertionError(
        f"no {name!r} among {[r['name'] for r in result.get('vars') or []]}")


def type_column(column, values, start=1):
    for offset, value in enumerate(values):
        sheet(action="cell", column=column, row=start + offset, text=str(value))


# ==========================================================================
# 1. the grid, through the engine
# ==========================================================================
def test_a_new_session_opens_the_sheet_the_catalog_reports():
    c = engine._la_dispatch({"op": "catalog"})
    assert c["sheetPrefix"] == "sheet."
    assert c["sheet"]["rows"] == 20
    assert len(c["sheet"]["columns"]) == 26
    assert c["sheet"]["bindings"] == {}


def test_typing_a_cell_comes_back_as_the_whole_grid():
    r = sheet(action="cell", column="A", row=1, text="27.5")
    assert r["ok"] is True
    column = r["sheet"]["columns"][0]
    assert column["letter"] == "A" and column["cells"]["1"] == "27.5"


def test_a_void_is_shown_as_an_underscore():
    type_column("A", ["1", "", "3"])
    cells = sheet()["sheet"]["columns"][0]["cells"]
    assert cells["2"] == "_"


# ==========================================================================
# 2. the promise: a named column is a list variable
# ==========================================================================
def test_naming_a_column_makes_it_a_list_variable():
    """The booklet's own example, driven the way the page drives it."""
    type_column("A", [11, 8, 7, 12, 9.5])
    assert sheet(action="name", column="A", text="mshoe")["ok"] is True

    assert run("mshoe")["summary"] == "{11,8,7,12,9.5}"


def test_the_named_list_drives_one_variable_statistics():
    type_column("A", [11, 8, 7, 12, 9.5])
    sheet(action="name", column="A", text="mshoe")

    result = run("OneVar mshoe")
    assert result["ok"] is True
    assert var(result, "n")["raw"] == 5
    assert var(result, "MinX")["raw"] == 7
    assert var(result, "MaxX")["raw"] == 12
    assert var(result, "v")["raw"] == pytest.approx(9.5)


def test_the_named_list_pairs_with_another_for_regression():
    type_column("A", [11, 8, 7, 12, 9.5])
    type_column("B", [27, 21, 20, 28.5, 19])
    sheet(action="name", column="A", text="mshoe")
    sheet(action="name", column="B", text="mhand")

    result = run("LinRegBx mshoe,mhand")
    assert result["ok"] is True
    assert var(result, "b")["raw"] is not None
    assert var(result, "r")["raw"] is not None


def test_a_formula_column_is_a_variable_too():
    """The D column of TI's worked example, as a list the calculator can use.

    The values are the booklet's own: 27/11, 21/8, 20/7 and then 2.375, which
    is 28.5/12.  The grid shows six significant digits because a column is only
    so wide; the Calculator page, with a whole line, shows more.
    """
    type_column("A", [11, 8, 7, 12, 9.5])
    type_column("B", [27, 21, 20, 28.5, 19])
    assert sheet(action="formula", column="C", text="=b[]/a[]")["ok"] is True
    sheet(action="name", column="A", text="mshoe")
    sheet(action="name", column="B", text="mhand")
    sheet(action="name", column="C", text="ratio")

    cells = sheet()["sheet"]["columns"][2]["cells"]
    assert [cells[str(i)] for i in range(1, 6)] == [
        "2.45455", "2.625", "2.85714", "2.375", "2"]

    assert run("ratio")["summary"] == (
        "{2.454545455,2.625,2.857142857,2.375,2.0}")
    result = run("OneVar ratio")
    assert result["ok"] is True
    assert var(result, "n")["raw"] == 5
    assert var(result, "MinX")["raw"] == pytest.approx(2.0)
    assert var(result, "MaxX")["raw"] == pytest.approx(20 / 7)


def test_linking_goes_both_ways():
    """A variable stored on the Calculator page is usable in a cell formula."""
    engine._la_dispatch({"op": "run", "input": "k=4"})
    assert engine._NS.get("k") == 4
    assert sheet(action="formula", column="A", text="=k*3")["ok"] is True
    assert sheet()["sheet"]["columns"][0]["cells"]["1"] == "12"


# ==========================================================================
# 3. the menu reaches the grid
# ==========================================================================
def test_the_menu_key_that_fills_down_runs_the_grid():
    """``menu 3 3`` -- TI's own path, from the key to the cells.

    The recipe is TI's too: the booklet's compound-interest example, ``=a1*1.05``
    in A2 filled down.
    """
    found = engine._la_dispatch({"op": "menu", "app": "listssheet", "path": "33"})
    assert found["kind"] == "sheet"
    assert found["function"] == "sheet.fill_down"

    sheet(action="cell", column="A", row=1, text="1000")
    sheet(action="cell", column="A", row=2, text="=a1*1.05")
    r = sheet(action="action", name=found["function"], args=["A", 2, 4])
    assert r["ok"] is True
    # Six significant digits: 1157.625 does not fit a column, so the cell shows
    # 1157.62 -- the device truncates too ("143489...").  The value behind it is
    # exact, and the Calculator page prints all of it.
    assert [r["sheet"]["columns"][0]["cells"][str(i)] for i in range(1, 5)] == [
        "1000", "1050", "1102.5", "1157.62"]
    assert r["sheet"]["bindings"] == {}
    sheet(action="name", column="A", text="balance")
    assert sheet()["sheet"]["bindings"]["balance"] == pytest.approx(
        [1000, 1050, 1102.5, 1157.625])


def test_recalculate_and_move_and_sort_are_reachable_by_name():
    type_column("A", [3, 1, 2])
    sheet(action="name", column="A", text="data")

    assert sheet(action="action", name="sheet.sort_by",
                 args=["A"], kwargs={"ascending": True})["ok"] is True
    assert sheet()["sheet"]["bindings"]["data"] == [1, 2, 3]

    # A moves into C's slot, so B and C slide left and the data -- and its
    # name -- end up in the third column.
    assert sheet(action="action", name="sheet.move_column",
                 args=["A", "C"])["ok"] is True
    after = sheet()["sheet"]
    assert after["bindings"]["data"] == [1, 2, 3]
    assert [after["columns"][2]["cells"][str(i)] for i in (1, 2, 3)] == [
        "1", "2", "3"]
    assert after["columns"][0]["cells"]["1"] == ""

    assert sheet(action="action", name="sheet.recalculate")["ok"] is True


# ==========================================================================
# 4. what the grid refuses
# ==========================================================================
def test_a_name_the_calculator_already_uses_is_refused_as_a_ti_error():
    r = sheet(action="name", column="A", text="mean")
    assert r["ok"] is False
    assert r["error"]["ti"] is True
    assert "already uses" in r["error"]["message"]
    assert r["sheet"]["bindings"] == {}


def test_a_name_that_is_not_a_variable_name_is_refused():
    r = sheet(action="name", column="A", text="2fast")
    assert r["ok"] is False and r["error"]["kind"] == "SheetError"


def test_only_a_sheet_action_may_be_run():
    for bad in ("OneVar", "sheet._resolving", "sheet.nope", "", "os.system"):
        r = sheet(action="action", name=bad)
        assert r["ok"] is False, bad
        assert "not a spreadsheet action" in r["error"]["message"], bad


def test_an_unknown_sheet_action_is_refused():
    r = sheet(action="teleport")
    assert r["ok"] is False
    assert r["error"]["kind"] == "UnknownSheetAction"


def test_a_missing_field_is_refused_rather_than_guessed():
    r = sheet(action="cell", column="A")           # no row
    assert r["ok"] is False


def test_a_broken_cell_says_so_in_the_cell_and_leaves_the_rest_alone():
    """The message lands in the cell, as it does on the device.

    A dividing-by-zero formula applies to every row of its column, so every row
    says so -- and the page still draws.  A grid that could not be rendered at
    all because one cell was wrong would turn a mistake the user can see and
    fix into a blank screen.
    """
    type_column("A", [1, 2])
    sheet(action="name", column="A", text="good")
    assert sheet(action="formula", column="B", text="=a[]*2")["ok"] is True
    assert sheet(action="name", column="B", text="twice")["ok"] is True
    assert sheet()["sheet"]["bindings"]["twice"] == [2, 4]

    # now nothing in B can be worked out: the grid still draws, and says why
    assert sheet(action="formula", column="B", text="=1/0")["ok"] is True
    drawn = sheet()["sheet"]
    assert drawn["columns"][1]["cells"]["1"] == "Error: a formula divided by zero"
    assert drawn["columns"][1]["cells"]["2"] == "Error: a formula divided by zero"
    # a column that cannot be read defines no variable, but the others are fine
    assert "twice" not in drawn["bindings"]
    assert drawn["bindings"]["good"] == [1, 2]
    assert drawn["columns"][0]["cells"]["1"] == "1"


# ==========================================================================
# 5. reset
# ==========================================================================
def test_reset_closes_the_grid_as_well_as_the_calculator():
    type_column("A", [1, 2, 3])
    sheet(action="name", column="A", text="gone")
    r = engine._la_dispatch({"op": "reset"})
    assert r["ok"] is True
    assert r["sheet"]["bindings"] == {}
    assert r["sheet"]["rows"] == 20
    assert engine._la_dispatch({"op": "catalog"})["sheet"]["bindings"] == {}
