"""The menu key, and the paths that walk it.

The point of these is not that the tree is pretty.  It is that the tree and the
package cannot disagree: every line of the Statistics menu has to land on a
function that exists, every function has to be reachable from somewhere, and
the numbering has to be the device's rather than something that merely looks
plausible.
"""

from __future__ import annotations

import pytest

import tinspire_stats as ts
from tinspire_stats import menu
from tinspire_stats.catalog import MENU, OFF_MENU, catalog


# ==========================================================================
# 1. the two menu layouts, and the path people actually remember
# ==========================================================================
def test_both_menus_reach_one_variable_statistics():
    """Statistics is 6 on the Calculator page and 4 on Lists & Spreadsheet.

    Both are the device's own numbering; the difference is why ``menu 4 1 1``
    works on one page and not the other.
    """
    calc = menu.resolve("calculator", "611")
    sheet = menu.resolve("listssheet", "411")
    assert calc.kind == sheet.kind == "function"
    assert calc.function == sheet.function == "OneVar"
    assert calc.label == "One-Variable Statistics"


def test_the_wrong_path_is_a_wrong_path():
    """``411`` on the Calculator page is Calculus, which is not statistics."""
    with pytest.raises(menu.MenuError):
        menu.resolve("calculator", "411")
    assert menu.resolve("calculator", "4").kind == "unsupported"
    assert menu.resolve("calculator", "4").label == "Calculus"


def test_the_calculator_menu_is_the_documented_eight():
    r = menu.resolve("calculator")
    assert [c.label for c in r.choices] == [
        "Actions", "Number", "Algebra", "Calculus", "Probability",
        "Statistics", "Matrix & Vector", "Finance",
    ]
    assert [c.key for c in r.choices] == list("12345678")


def test_the_lists_and_spreadsheet_menu_is_the_documented_six():
    r = menu.resolve("listssheet")
    assert [c.label for c in r.choices] == [
        "Actions", "Insert", "Data", "Statistics", "Table", "Hints",
    ]
    assert menu.resolve("listssheet", "4").title == "Statistics"


def test_app_names_are_casual_tolerant():
    for spelling in ("calculator", "Calc", "CALCULATOR"):
        assert menu.resolve(spelling).title == "Calculator"
    for spelling in ("listssheet", "lists", "Lists & Spreadsheet"):
        assert menu.resolve(spelling, "4").title == "Statistics"
    with pytest.raises(menu.MenuError):
        menu.resolve("graphs")


# ==========================================================================
# 2. the Statistics branch, item by item
# ==========================================================================
def test_statistics_has_the_documented_seven():
    r = menu.resolve("calculator", "6")
    assert [c.label for c in r.choices] == [
        "Stat Calculations", "Stat Results", "List Math", "List Operations",
        "Distributions", "Confidence Intervals", "Stat Tests",
    ]
    assert [c.kind for c in r.choices] == [
        "submenu", "function", "submenu", "submenu", "submenu", "submenu",
        "submenu",
    ]


def test_list_math_is_the_order_the_handheld_prints():
    r = menu.resolve("calculator", "63")
    assert [c.key for c in r.choices] == list("123456789A")
    assert [c.label for c in r.choices] == [
        "Minimum", "Maximum", "Mean", "Median", "Sum of Elements",
        "Product of Elements", "Sample Standard Deviation", "Sample Variance",
        "Population Standard Deviation", "Population Variance",
    ]
    assert [c.function for c in r.choices] == [
        "min", "max", "mean", "median", "sum", "product",
        "stDevSamp", "varSamp", "stDevPop", "varPop",
    ]


def test_stat_calculations_runs_to_g():
    r = menu.resolve("calculator", "61")
    assert len(r.choices) == 16
    assert [c.key for c in r.choices] == list("123456789ABCDEFG")
    assert r.choices[0].function == "OneVar"
    assert r.choices[15].label == "Correlation Matrix"


def test_distributions_runs_to_i_and_keeps_the_f_family_before_binomial():
    r = menu.resolve("calculator", "65")
    assert len(r.choices) == 18
    assert [c.key for c in r.choices] == list("123456789ABCDEFGHI")
    by_key = {c.key: c.label for c in r.choices}
    assert by_key["2"] == "Normal Cdf"
    assert by_key["3"] == "Inverse Normal"
    assert by_key["7"] == "\u03c7\u00b2 Pdf"
    assert by_key["A"] == "F Pdf"
    assert by_key["C"] == "Inverse F"
    assert by_key["D"] == "Binomial Pdf"
    assert by_key["I"] == "Poisson Cdf"


def test_intervals_and_tests_are_the_documented_sets():
    assert [c.label for c in menu.resolve("calculator", "66").choices] == [
        "z Interval", "t Interval", "2-Sample z Interval",
        "2-Sample t Interval", "1-Prop z Interval", "2-Prop z Interval",
        "Linear Reg t Intervals", "Multiple Reg Intervals",
    ]
    tests = menu.resolve("calculator", "67").choices
    assert [c.key for c in tests] == list("123456789ABCD")
    assert [c.label for c in tests] == [
        "z Test", "t Test", "2-Sample z Test", "2-Sample t Test",
        "1-Prop z Test", "2-Prop z Test", "\u03c7\u00b2 GOF",
        "\u03c7\u00b2 2-way Test", "2-Sample F Test", "Linear Reg t Test",
        "Multiple Reg Tests", "ANOVA", "ANOVA 2-Way",
    ]


# ==========================================================================
# 3. outside statistics
# ==========================================================================
def test_categories_outside_statistics_say_so_rather_than_pretending():
    for app, key in (("calculator", "1"), ("calculator", "2"),
                     ("calculator", "3"), ("calculator", "4"),
                     ("calculator", "5"), ("calculator", "7"),
                     ("calculator", "8"), ("listssheet", "1"),
                     ("listssheet", "2"), ("listssheet", "3"),
                     ("listssheet", "5"), ("listssheet", "6")):
        r = menu.resolve(app, key)
        assert r.kind == "unsupported", (app, key)
        assert r.function is None
        assert r.label  # it still names the line the user pressed


def test_list_operations_keeps_its_unsupported_lines():
    """A map that drops the streets it cannot route is worse than one that says
    so: the keys stay where the handheld puts them."""
    r = menu.resolve("calculator", "64")
    assert [c.key for c in r.choices] == list("123456789ABC")
    kinds = {c.key: c.kind for c in r.choices}
    assert kinds == {
        "1": "function", "2": "function", "3": "function", "4": "unsupported",
        "5": "unsupported", "6": "function", "7": "unsupported",
        "8": "unsupported", "9": "unsupported", "A": "unsupported",
        "B": "unsupported", "C": "unsupported",
    }


def test_stat_results_is_the_variable_not_a_function():
    r = menu.resolve("calculator", "62")
    assert r.kind == "function"
    assert r.function == menu.STAT_RESULTS


# ==========================================================================
# 4. the tree and the package must agree
# ==========================================================================
def test_every_menu_function_exists_and_is_callable():
    for app in menu.APPS:
        for path, _crumb, item in menu.menu_paths(app):
            if not item.function or item.function == menu.STAT_RESULTS:
                continue
            target = getattr(ts, item.function, None)
            assert target is not None, (
                f"{' '.join(path)} promises {item.function}, which the package "
                f"does not export"
            )
            assert callable(target), item.function


def test_every_ti_function_has_a_front_door_or_is_filed_off_menu():
    """No name may go missing between the menu and the catalogue."""
    reachable = set()
    for app in menu.APPS:
        for _path, _crumb, item in menu.menu_paths(app):
            if item.function and item.function != menu.STAT_RESULTS:
                reachable.add(item.function)
    filed = set()
    for names in list(MENU.values()) + list(OFF_MENU.values()):
        filed |= set(names)
    assert reachable <= filed, sorted(reachable - filed)

    for row in catalog():
        if row["kind"] != "ti":
            continue
        assert row["name"] in filed, (
            f"{row['name']} is in the catalogue but on no menu and in no "
            f"off-menu list, so nothing records where it comes from"
        )


def test_the_menu_map_is_generated_from_the_menu_itself():
    """``MENU`` is derived, so it cannot describe a menu the keypad does not.

    The hand-written version it replaced put ``countif`` under List Math and
    split Distributions into Continuous and Discrete.
    """
    assert "Statistics > List Math" in MENU
    assert "countif" not in MENU["Statistics > List Math"]
    assert MENU["Statistics > List Math"] == [
        "min", "max", "mean", "median", "sum", "product",
        "stDevSamp", "varSamp", "stDevPop", "varPop",
    ]
    assert "Statistics > Distributions" in MENU
    assert not any("Continuous" in path or "Discrete" in path for path in MENU)
    assert "AB" not in "".join(MENU)


def test_menu_tree_still_resolves_to_objects():
    tree = ts.menu_tree()
    assert tree["Statistics > Stat Calculations"][0] is ts.OneVar


# ==========================================================================
# 5. walking badly
# ==========================================================================
def test_a_key_the_menu_does_not_offer_is_a_menu_error():
    """The handheld ignores the key and leaves the menu up; we say so and let
    the screen decide."""
    with pytest.raises(menu.MenuError) as info:
        menu.resolve("calculator", "9")          # only eight top-level items
    assert info.value.key == "9"
    assert info.value.where == "Calculator"

    with pytest.raises(menu.MenuError):
        menu.resolve("calculator", "6B")         # Statistics has no B


def test_keys_past_a_leaf_are_refused_rather_than_reinterpreted():
    with pytest.raises(menu.MenuError) as info:
        menu.resolve("calculator", "6111")
    assert info.value.where == "One-Variable Statistics"


def test_a_path_that_stops_on_a_submenu_reports_the_submenu():
    r = menu.resolve("calculator", "61")
    assert r.kind == "menu"
    assert r.title == "Stat Calculations"
    assert r.breadcrumb == ("Calculator", "Statistics", "Stat Calculations")
    assert len(r.choices) == 16

    top = menu.resolve("calculator")
    assert top.kind == "menu"
    assert top.breadcrumb == ("Calculator",)
    assert top.path == ()


def test_keys_are_accepted_in_any_case():
    # A is the tenth line, so it is Exponential Regression; Quadratic is 6.
    assert menu.resolve("calculator", ["6", "1", "a"]).function == "ExpReg"
    assert menu.resolve("calculator", "61A").function == "ExpReg"
    assert menu.resolve("calculator", "616").function == "QuadReg"


def test_a_string_path_is_keys_not_tokens():
    """``"611"`` means the three keys 6, 1, 1 -- the keypad has no spaces, so a
    space is not a separator, it is a key that does not exist."""
    assert menu.resolve("calculator", "611").function == "OneVar"
    assert menu.resolve("calculator", ["6", "1", "1"]).function == "OneVar"
    with pytest.raises(menu.MenuError):
        menu.resolve("calculator", "6 1 1")
