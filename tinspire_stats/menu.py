"""The handheld's menus, and the paths that walk them.

The ``menu`` key does not open *a* menu.  It opens the menu of whichever
application is on the page, and the two applications that hold statistics lay
them out differently:

======================  ==========================  ====================
application              menu                     path to 1-var stats
======================  ==========================  ====================
Calculator               1 Actions .. 8 Finance    ``6 1 1``
Lists & Spreadsheet      1 Actions .. 6 Hints      ``4 1 1``
======================  ==========================  ====================

Statistics is ``6`` on the Calculator page and ``4`` on the Lists & Spreadsheet
page, which is why the path people remember is not the path the Calculator page
takes.  Both trees are here, so either habit works.

The two pages do not only renumber Statistics -- they lay its contents out
differently, and the Lists & Spreadsheet page's own branches (Actions, Insert,
Data, Table) hold the grid operations the Calculator page has no equivalent of.
See the note above ``SHEET_ACTIONS``.

Only statistics leads to a function of the package.  The categories outside it
are real menu entries with real numbers -- pressing them is what the handheld
would do -- and resolve to ``unsupported``, or to ``sheet`` where the line is an
action on the open spreadsheet.

Sources for the item order and the numbering: the TI-Nspire eGuide pages for
Stat Tests, Confidence Intervals and Distributions (which document the items
in menu order), the Lists & Spreadsheet eGuide chapter (for the grid branches
and for where List Math sits on that page), the Lists & Spreadsheet menu table
in TI's user manual and the "Data > Fill Down" path in TI's own *First Steps
with TI-Nspire CX*, and the List Math screenshot in TI's statistics activity
sheet.
"""

from __future__ import annotations

from typing import Iterable, NamedTuple, Sequence

__all__ = [
    "Item",
    "Choice",
    "Resolution",
    "MenuError",
    "APPS",
    "KEYS",
    "STAT_RESULTS",
    "SHEET_PREFIX",
    "SHEET_ACTIONS",
    "SHEET_INSERT",
    "SHEET_DATA",
    "SHEET_STATISTICS",
    "SHEET_TABLE",
    "sheet_op",
    "is_sheet_op",
    "resolve",
    "menu_paths",
]

#: How a menu numbers itself: the digits first, then the letters.  Item 10 is
#: ``A``, item 18 is ``I`` -- the menu shows the letter, and the letter key
#: picks it.
KEYS = "123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


class Item(NamedTuple):
    """One line of a menu.

    A line is one of three things: a submenu (``children``), a function
    (``function``, spelled the way this package spells it), or neither --
    which is what a category outside statistics looks like here.
    """

    label: str
    function: "str | None" = None
    children: "tuple[Item, ...] | None" = None


class Choice(NamedTuple):
    """An item in a menu that is on screen, with the key that picks it."""

    key: str
    label: str
    #: "submenu" | "function" | "sheet" | "unsupported"
    kind: str
    function: "str | None"


class Resolution(NamedTuple):
    """What a menu path lands on.

    ``kind`` is ``"menu"`` when more keys are expected (the submenu is open and
    waiting), ``"function"`` when the path reached a statistics function this
    package can run, ``"sheet"`` when it reached an action on the open
    spreadsheet, and ``"unsupported"`` when it reached a real menu entry that
    belongs to a category the package does not cover.
    """

    kind: str
    title: str
    path: "tuple[str, ...]"
    breadcrumb: "tuple[str, ...]"
    choices: "tuple[Choice, ...]"
    label: str = ""
    function: "str | None" = None


class MenuError(ValueError):
    """A key that the menu on screen does not offer.

    The handheld's own behaviour is to ignore the key -- the menu stays put --
    so this is a signal to whoever is drawing the screen, not a crash.
    """

    def __init__(self, key: str, where: str) -> None:
        super().__init__(f"no menu key {key!r} in {where!r}")
        self.key = key
        self.where = where


# --------------------------------------------------------------------------
# Statistics.  This is the whole subject of the package, so it is the one
# branch with every item spelled out.
# --------------------------------------------------------------------------

STAT_CALCULATIONS = (
    Item("One-Variable Statistics", "OneVar"),
    Item("Two-Variable Statistics", "TwoVar"),
    Item("Linear Regression (mx+b)", "LinRegMx"),
    Item("Linear Regression (a+bx)", "LinRegBx"),
    Item("Median-Median Line", "MedMed"),
    Item("Quadratic Regression", "QuadReg"),
    Item("Cubic Regression", "CubicReg"),
    Item("Quartic Regression", "QuartReg"),
    Item("Power Regression", "PowerReg"),
    Item("Exponential Regression", "ExpReg"),
    Item("Logarithmic Regression", "LnReg"),
    Item("Sinusoidal Regression", "SinReg"),
    Item("Logistic Regression (d=0)", "Logistic"),
    Item("Logistic Regression (d\u22600)", "LogisticD"),
    Item("Multiple Linear Regression", "MultReg"),
    Item("Correlation Matrix", "corrMat"),
)

LIST_MATH = (
    Item("Minimum", "min"),
    Item("Maximum", "max"),
    Item("Mean", "mean"),
    Item("Median", "median"),
    Item("Sum of Elements", "sum"),
    Item("Product of Elements", "product"),
    Item("Sample Standard Deviation", "stDevSamp"),
    Item("Sample Variance", "varSamp"),
    Item("Population Standard Deviation", "stDevPop"),
    Item("Population Variance", "varPop"),
)

#: The three list operations this package has no function for keep their real
#: labels and numbers, and resolve to ``unsupported`` -- the menu is a map of
#: the handheld, and a map that quietly omits streets is worse than one that
#: says "no entry".
LIST_OPERATIONS = (
    Item("Sort Ascending", "SortA"),
    Item("Sort Descending", "SortD"),
    Item("Cumulative Sum List", "cumulativeSum"),
    Item("Fill"),
    Item("Sequence"),
    Item("Difference List", "\u0394List"),
    Item("Augment"),
    Item("Convert List to Matrix"),
    Item("Convert Matrix to List"),
    Item("Left"),
    Item("Mid"),
    Item("Right"),
)

DISTRIBUTIONS = (
    Item("Normal Pdf", "normPdf"),
    Item("Normal Cdf", "normCdf"),
    Item("Inverse Normal", "invNorm"),
    Item("t Pdf", "tPdf"),
    Item("t Cdf", "tCdf"),
    Item("Inverse t", "invt"),
    # The label is what the menu prints (the squared sign is a real glyph).
    # The function name is the package's, which spells it ``2`` -- a name is
    # typed, and the handheld's own ASCII form for these is chi2.
    Item("\u03c7\u00b2 Pdf", "\u03c72Pdf"),
    Item("\u03c7\u00b2 Cdf", "\u03c72Cdf"),
    Item("Inverse \u03c7\u00b2", "inv\u03c72"),
    Item("F Pdf", "FPdf"),
    Item("F Cdf", "FCdf"),
    Item("Inverse F", "invF"),
    Item("Binomial Pdf", "binomPdf"),
    Item("Binomial Cdf", "binomCdf"),
    Item("Geometric Pdf", "geomPdf"),
    Item("Geometric Cdf", "geomCdf"),
    Item("Poisson Pdf", "poissPdf"),
    Item("Poisson Cdf", "poissCdf"),
)

CONFIDENCE_INTERVALS = (
    Item("z Interval", "zInterval"),
    Item("t Interval", "tInterval"),
    Item("2-Sample z Interval", "zInterval_2Samp"),
    Item("2-Sample t Interval", "tInterval_2Samp"),
    Item("1-Prop z Interval", "zInterval_1Prop"),
    Item("2-Prop z Interval", "zInterval_2Prop"),
    Item("Linear Reg t Intervals", "LinRegtIntervals"),
    Item("Multiple Reg Intervals", "MultRegIntervals"),
)

STAT_TESTS = (
    Item("z Test", "zTest"),
    Item("t Test", "tTest"),
    Item("2-Sample z Test", "zTest_2Samp"),
    Item("2-Sample t Test", "tTest_2Samp"),
    Item("1-Prop z Test", "zTest_1Prop"),
    Item("2-Prop z Test", "zTest_2Prop"),
    Item("\u03c7\u00b2 GOF", "chi2GOF"),
    Item("\u03c7\u00b2 2-way Test", "chi22way"),
    Item("2-Sample F Test", "FTest_2Samp"),
    Item("Linear Reg t Test", "LinRegtTest"),
    Item("Multiple Reg Tests", "MultRegTests"),
    Item("ANOVA", "ANOVA"),
    Item("ANOVA 2-Way", "ANOVA2way"),
)

#: ``stat.results`` is a variable on the handheld, not a function, so the
#: engine gets it under its own name and prints the same block the calculator
#: would.
STAT_RESULTS = "stat.results"

STATISTICS = (
    Item("Stat Calculations", children=STAT_CALCULATIONS),
    Item("Stat Results", STAT_RESULTS),
    Item("List Math", children=LIST_MATH),
    Item("List Operations", children=LIST_OPERATIONS),
    Item("Distributions", children=DISTRIBUTIONS),
    Item("Confidence Intervals", children=CONFIDENCE_INTERVALS),
    Item("Stat Tests", children=STAT_TESTS),
)

# --------------------------------------------------------------------------
# The Lists & Spreadsheet page's own branches.
#
# The two pages do not merely number Statistics differently: the *contents*
# differ, and the Lists & Spreadsheet menu is where that is visible.
#
# TI's Lists & Spreadsheet menu lists four entries under Statistics, not the
# Calculator's seven:
#
#     1: Stat Calculations   2: Distributions
#     3: Confidence Intervals   4: Stat Tests
#
# "Stat Results" is absent because it means something else on this page.  The
# eGuide, describing the statistics wizards, says they "store the results in
# two columns: one for the result names, and one for the corresponding
# values" -- so there is no stat.results variable here to display; the answers
# land in the grid.  List Math and List Operations are on the *Data* menu
# instead, which is where the work is ("From the Data menu, click
# List Math > Mean", eGuide, Creating Spreadsheet Data).
#
# This is the one claim in this module I cannot fully pin.  The four-item list
# is from the TI-Nspire user manual's Lists & Spreadsheet menu table, which is
# an older revision than the eGuide; the eGuide confirms only that Stat Results
# and List Math are not where the Calculator page puts them, not what the
# surviving four are in order.  Stat Calculations first is safe -- it is what
# ``menu 4 1 1`` depends on.
#
# The grid operations below are the one place a menu line does not name a
# statistics function.  They are spelled ``sheet.<method>`` and resolved
# against the open spreadsheet, so the menu still cannot promise a function
# that does not exist.
# --------------------------------------------------------------------------

#: The prefix that marks a menu line as a spreadsheet action rather than a
#: statistics function.
SHEET_PREFIX = "sheet."


def sheet_op(method: str) -> str:
    """The menu spelling of a :class:`~tinspire_stats.sheet.Sheet` method."""
    return SHEET_PREFIX + method


def is_sheet_op(name: "str | None") -> bool:
    return bool(name) and name.startswith(SHEET_PREFIX)


#: Actions.  The six lines and their order are the user manual's table; the
#: Resize and Select submenus are the eGuide's ("From the Actions menu, select
#: Resize, and then select an option").  Only Move Column, Recalculate and Sort
#: touch the data -- the rest rearrange or size the display.
SHEET_ACTIONS = (
    Item("Move Column", sheet_op("move_column")),
    Item("Resize", children=(
        Item("Resize Column Width"),
        Item("Maximize Column Width"),
        Item("Minimize Column Width"),
        Item("Resize Row Height"),
    )),
    Item("Select", children=(
        Item("Select Formula Range"),
    )),
    Item("Go To"),
    Item("Recalculate", sheet_op("recalculate")),
    Item("Sort", sheet_op("sort_by")),
)

#: Insert.  The user manual's order is Cell, Row, Column; TI's getting-started
#: guide for the CX lists the two that matter here as "select either Row or
#: Column", which does not order them.  None of the three is implemented yet.
SHEET_INSERT = (
    Item("Insert Cell"),
    Item("Insert Row"),
    Item("Insert Column"),
)

#: Data.  The first four lines and their order are the user manual's table, and
#: Fill Down is independently pinned to the third slot by TI's own *First Steps
#: with TI-Nspire CX*: "choosing the options 3: Data and 3: Fill Down".  Fill
#: Down is also the one line here the package can run.
#:
#: List Math and List Operations are here rather than under Statistics (see the
#: note above) and follow the four the manual orders.  Data > Random > Integer
#: is on the map with its real number but resolves to nothing: ``randInt`` is a
#: Probability function, and this package files it under OFF_MENU on the
#: Calculator side.
SHEET_DATA = (
    Item("Generate Sequence"),
    Item("Data Capture", children=(
        Item("Auto"),
        Item("Ask"),
        Item("Manual"),
        Item("Clear Data"),
        Item("Display On"),
    )),
    Item("Fill Down", sheet_op("fill_down")),
    Item("Quick Graph"),
    Item("List Math", children=LIST_MATH),
    Item("List Operations", children=LIST_OPERATIONS),
    Item("Random", children=(
        Item("Integer"),
    )),
)

#: Statistics, four entries (see the note above).
SHEET_STATISTICS = (
    Item("Stat Calculations", children=STAT_CALCULATIONS),
    Item("Distributions", children=DISTRIBUTIONS),
    Item("Confidence Intervals", children=CONFIDENCE_INTERVALS),
    Item("Stat Tests", children=STAT_TESTS),
)

#: Table.  Five lines in the user manual's order.  The names are the eGuide's,
#: which is the live documentation: it calls "Select Function" simply Choose,
#: and drops the word Function from the settings and expression lines.
#:
#: None of these is a spreadsheet column operation -- Delete Column here
#: removes a column of a *function* table -- so none of them is wired to the
#: sheet, and none should be.
SHEET_TABLE = (
    Item("Switch to Table"),
    Item("Select Function"),
    Item("Edit Table Settings"),
    Item("Delete Column"),
    Item("Edit Expression"),
)

# --------------------------------------------------------------------------
# The two application menus.  Everything outside Statistics is a real entry
# with no function behind it.
# --------------------------------------------------------------------------

CALCULATOR_MENU = (
    Item("Actions"),
    Item("Number"),
    Item("Algebra"),
    Item("Calculus"),
    Item("Probability"),
    Item("Statistics", children=STATISTICS),
    Item("Matrix & Vector"),
    Item("Finance"),
)

LISTS_SHEET_MENU = (
    Item("Actions", children=SHEET_ACTIONS),
    Item("Insert", children=SHEET_INSERT),
    Item("Data", children=SHEET_DATA),
    Item("Statistics", children=SHEET_STATISTICS),
    Item("Table", children=SHEET_TABLE),
    Item("Hints"),
)

#: Application name -> (label, top-level menu).
APPS = {
    "calculator": ("Calculator", CALCULATOR_MENU),
    "listssheet": ("Lists & Spreadsheet", LISTS_SHEET_MENU),
}

#: Spellings accepted for each application, so callers can be casual.
_APP_ALIASES = {
    "calculator": "calculator",
    "calc": "calculator",
    "listssheet": "listssheet",
    "lists": "listssheet",
    "list": "listssheet",
    "listsheet": "listssheet",
    "lists & spreadsheet": "listssheet",
    "spreadsheet": "listssheet",
}


def app_key(name: "str | None") -> str:
    """Canonical application key, defaulting to the Calculator page."""
    if name is None:
        return "calculator"
    key = _APP_ALIASES.get(str(name).strip().lower())
    if key is None:
        raise MenuError(str(name), "applications")
    return key


def _find(children: Sequence[Item], key: str) -> "tuple[int, Item] | None":
    """The item a key picks, or ``None`` if the menu offers no such key."""
    key = str(key).strip().upper()
    for position, item in enumerate(children):
        if position < len(KEYS) and KEYS[position] == key:
            return position, item
    return None


def _kind_of(item: Item) -> str:
    if item.children is not None:
        return "submenu"
    if not item.function:
        return "unsupported"
    return "sheet" if is_sheet_op(item.function) else "function"


def _choices(children: Sequence[Item]) -> "tuple[Choice, ...]":
    out = []
    for position, item in enumerate(children):
        if position >= len(KEYS):
            break
        out.append(Choice(KEYS[position], item.label, _kind_of(item),
                          item.function))
    return tuple(out)


def resolve(app: "str | None" = "calculator", path: Iterable[str] = ()) -> Resolution:
    """Walk a menu path and say what it lands on.

    ``resolve("calculator", "611")`` reaches One-Variable Statistics;
    ``resolve("listssheet", "411")`` reaches the same function from the other
    menu.  A path that stops on a submenu comes back with ``kind="menu"`` and
    that submenu's items, which is what the screen should draw next.

    A string path is read as individual keystrokes -- the keypad has no
    separator, so ``"6 1 1"`` is four keys and the space does not exist.  Pass
    a list when the keys are already separate.

    Raises :class:`MenuError` for a key the menu on screen does not offer.
    """
    key = app_key(app)
    app_label, tree = APPS[key]
    keys = tuple(str(part).strip().upper() for part in path)

    children: Sequence[Item] = tree
    trail: list = []
    step = 0
    while step < len(keys):
        found = _find(children, keys[step])
        if found is None:
            raise MenuError(keys[step], trail[-1] if trail else app_label)
        _, item = found
        if item.children is None and step != len(keys) - 1:
            # Keys past a leaf.  The handheld would ignore them; so do we, but
            # say so rather than silently reinterpreting the path.
            raise MenuError(keys[step + 1], item.label)
        if item.children is not None:
            trail.append(item.label)
            children = item.children
            step += 1
            continue
        return Resolution(
            kind=_kind_of(item),
            title=trail[-1] if trail else app_label,
            path=keys,
            breadcrumb=tuple([app_label] + trail),
            choices=(),
            label=item.label,
            function=item.function,
        )

    return Resolution(
        kind="menu",
        title=trail[-1] if trail else app_label,
        path=keys,
        breadcrumb=tuple([app_label] + trail),
        choices=_choices(children),
    )


def menu_paths(app: "str | None" = "calculator", _tree=None, _prefix=(), _trail=()):
    """Every path from the top menu down to a leaf.

    Yields ``(path, breadcrumb, item)``: the keys to press, the menu labels
    walked (the application name first), and the line arrived at.  The
    catalogue builds its own menu map from this, so the map and the menu key
    cannot drift apart.
    """
    key = app_key(app)
    app_label, tree = APPS[key]
    if _tree is None:
        _tree = tree
    for position, item in enumerate(_tree):
        if position >= len(KEYS):
            break
        path = _prefix + (KEYS[position],)
        trail = _trail + (item.label,)
        if item.children is not None:
            yield from menu_paths(key, item.children, path, trail)
        else:
            yield path, (app_label,) + _trail, item
