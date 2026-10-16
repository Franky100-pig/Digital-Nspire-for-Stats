"""The Lists & Spreadsheet application: columns, cells and list variables.

The point of this page -- for a statistics package -- is its top row.  Naming a
column turns it into a *list variable*, and the Calculator page can then hand
that name to any statistics function, exactly as the handheld does:

    menu > Statistics > Stat Calculations > One-Variable Statistics
        X1 List: footlength

TI's own description of the grid (First Steps with TI-Nspire, Tutorial 6):

    Notice the two areas coloured white and grey at the top of each column.
    The white area is for list names.  The grey area is for formulas that will
    apply to all items in the list below.

So the grid is::

         A          B          C
    +----------+----------+----------+  name row    -- white.  What you type here
    |footlength|  mshoe   |          |                becomes a list variable.
    +----------+----------+----------+  formula row -- grey.  Applies to every
    |          |          |          |                cell below it.
    +----------+----------+----------+
   1|   27.5   |    11    |          |
   2|   26.0   |     8    |          |

Cell references
---------------
The syntax exists to keep a column apart from a variable that shares its name,
and TI states the rule as a table (Getting Started with the TI-Nspire Handheld,
"Preventing name conflicts")::

    A      The shared variable A.  This syntax never refers to column A.
    A[]    Column A of the current table.
    A1     The table cell at column A, row 1 -- never the variable A1.
    'A1    The shared variable A1 -- never the table cell A1.

So ``a[]`` is the **whole column**, and it is the only way to name a column
whose letter is also a variable.  A bare ``a`` is a variable, which is why the
handheld pops up a "Column or Variable?" box when it cannot tell -- and why
naming columns with two or more characters avoids the question entirely.

A whole column makes a formula column-wide.  One formula in the grey row defines
every row below it, so ``=b[]/a[]`` divides two lists element by element.  That
is how TI's own worked example reaches ``D1 = B1/A1`` (27/11) -- and it reaches
``D2 = B2/A2`` as well, which is the part a per-row reading cannot explain.

One cell is ``a1``; ``$a$1`` pins it.  Filling a formula down shifts the
relative row numbers, which is how a recurrence is built: ``=a1*1.05`` typed in
A2 and filled down becomes ``=a2*1.05`` in A3.
"""

from __future__ import annotations

import ast
import math
import re

__all__ = [
    "Sheet",
    "Column",
    "TiList",
    "SheetError",
    "MAX_COLUMNS",
    "MAX_ROWS",
    "RESERVED_NAMES",
    "VOID_GLYPH",
    "letter_of",
    "index_of",
    "valid_column_letter",
    "valid_list_name",
    "reserved_names",
    "statistics_functions",
    "display",
    "shift_for_fill",
    "evaluate",
]

#: The replica's screen is 320x240; 26 columns keeps every name one letter and
#: the letter row readable.
MAX_COLUMNS = 26
#: Rows 1..n.  More than the screen shows, and enough for classroom data.
MAX_ROWS = 50


class SheetError(ValueError):
    """An edit the grid cannot make, phrased for the entry line."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.ti_message = message


def letter_of(index: int) -> str:
    """0 -> ``A``.  Only the single-letter columns exist here."""
    if not 0 <= index < MAX_COLUMNS:
        raise SheetError(f"there is no column {index + 1}")
    return chr(ord("A") + index)


def index_of(letter: str) -> int:
    """``a`` -> 0.  Case-insensitive, as the keypad is."""
    text = str(letter).strip().upper()
    if len(text) != 1 or not ("A" <= text <= "Z"):
        raise SheetError(f"{letter!r} is not a column letter")
    return ord(text) - ord("A")


def valid_column_letter(letter: str) -> bool:
    try:
        index_of(letter)
        return True
    except SheetError:
        return False


def valid_list_name(name: str) -> bool:
    """Whether a column name can become a list variable.

    The rule the calculator puts on any variable: a letter, then letters,
    digits or underscores.  Nothing is accepted here that the Calculator page
    would refuse, so the page cannot promise a name the other page rejects.
    """
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", str(name).strip()))


#: Names the Calculator page owns before the user arrives.  TI refuses to let a
#: variable be called one of these -- "You cannot use a preassigned variable or
#: function name, such as ans or min" -- and the reason matters here: a column
#: named ``mean`` would be a column the Calculator page could never reach,
#: because ``mean`` resolves to the function first.  Refusing the name at the
#: point of typing it is the only place the problem is visible.
RESERVED_NAMES = frozenset({
    "ans", "stat", "math", "e", "\u03c0", "pi", "\u221e", "inf",
    "true", "false",
})


def reserved_names() -> frozenset:
    """``RESERVED_NAMES`` plus every function the Calculator page already has.

    Taken from the package's own namespace rather than from a second hand-kept
    list: the set that matters is whatever the Calculator page will look a name
    up in, and that is this same namespace.
    """
    return RESERVED_NAMES | frozenset(statistics_functions())


# --------------------------------------------------------------------------
# grid syntax -> Python
# --------------------------------------------------------------------------
#: The guard both reference patterns share: a reference may not begin or end in
#: the middle of a word.  Without it a list variable called ``die1`` is read as
#: the cell ``e1``.  That is not hypothetical -- TI's own dice example names its
#: columns ``die1`` and ``die2`` (Getting Started with TI-Nspire, 5.10).
_NOT_IN_WORD = r"(?<![A-Za-z0-9_])"
_NOT_IN_WORD_END = r"(?![A-Za-z0-9_])"

#: A whole column: ``a[]``.
_COLUMN_REF = re.compile(_NOT_IN_WORD + r"([A-Za-z])\s*\[\s*\]")
#: One cell: ``a1``, or ``$a$1`` when the row is pinned.
_CELL_REF = re.compile(
    _NOT_IN_WORD + r"(\$?)([A-Za-z])(\$?)([0-9]+)" + _NOT_IN_WORD_END
)
#: The apostrophe escape.  A formula has no string literals -- TI quotes those
#: with ``"`` -- so an apostrophe in one can only be the escape, and ``'a1`` is
#: the variable ``a1``.  It has to exist: a list really can be named ``a1``, and
#: bare ``a1`` is always the cell, so without it that list is unreachable.
_QUOTED_VAR = re.compile(_NOT_IN_WORD + r"'([A-Za-z_][A-Za-z0-9_]*)")
#: The placeholder used while filling, so ``a[]`` is not mistaken for a cell.
_PIN = "\x00"
#: And the one used to put a pinned column reference back the way it was.
_COLUMN_PIN = re.compile(re.escape(_PIN) + r"([A-Za-z])" + re.escape(_PIN))


def _ref_name(letter: str, row: int) -> str:
    """The identifier a cell reference is rewritten to."""
    return f"__cell_{letter.upper()}_{row}"


def _col_name(letter: str) -> str:
    """The identifier a whole-column reference is rewritten to."""
    return f"__col_{letter.upper()}"


def _var_name(name: str) -> str:
    """The identifier an apostrophe-escaped variable is rewritten to."""
    return f"__var_{name}"


def _rewrite(text: str) -> str:
    """Turn grid syntax into Python, leaving the arithmetic alone.

    ``a[]`` becomes ``__col_A`` and ``a1`` becomes ``__cell_A_1``, because what
    comes out of here is parsed as Python and neither spelling is Python.  The
    substituted names cannot be mistaken for a reference on a later pass: the
    digits a cell reference needs are always preceded by a letter, and these all
    have an underscore there instead.  That is also why the escape runs first --
    ``'a1`` must be out of reach before the cell pattern is applied.
    """
    out = _QUOTED_VAR.sub(lambda m: _var_name(m.group(1)), text)
    out = _COLUMN_REF.sub(lambda m: _col_name(m.group(1)), out)
    return _CELL_REF.sub(lambda m: _ref_name(m.group(2), int(m.group(4))), out)


def shift_for_fill(formula: str, anchor_row: int, target_row: int) -> str:
    """Point a formula at ``target_row``, the way filling down does.

    Relative row numbers move with the fill; ``$``-pinned ones do not.  A whole
    column already means "every row", so ``a[]`` never shifts -- it is only
    pinned out of the way while the cell references are being bumped, and then
    put back exactly as it was.
    """
    delta = int(target_row) - int(anchor_row)
    if not delta:
        return formula
    marked = _COLUMN_REF.sub(lambda m: f"{_PIN}{m.group(1)}{_PIN}", formula)

    def bump(match: re.Match) -> str:
        col_dollar, letter, row_dollar, digits = match.groups()
        row = int(digits)
        if not row_dollar:
            shifted = row + delta
            # Filling up past row 1 would name a cell that does not exist.  The
            # handheld leaves the reference where it is rather than refusing.
            row = shifted if shifted >= 1 else row
        return f"{col_dollar}{letter}{row_dollar}{row}"

    shifted = _CELL_REF.sub(bump, marked)
    # Stripping the pins instead would leave a bare `b/a`, which is a pair of
    # *variables* -- a different quantity from the two columns.
    return _COLUMN_PIN.sub(lambda m: f"{m.group(1)}[]", shifted)


#: The only shapes a cell formula may take.  A formula is arithmetic over cells,
#: literals and named values -- not a program, and not a way to reach the host.
_ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Name, ast.Call,
    ast.Load,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv,
    ast.USub, ast.UAdd,
)


def _check(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise SheetError(f"a formula may not use {type(node).__name__.lower()}")
        if isinstance(node, ast.Call) and not isinstance(node.func, ast.Name):
            raise SheetError("a formula may only call a function by name")


def _as_number(value):
    """Normalise an arithmetic result: whole numbers stay whole."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            return value
        if value == int(value) and abs(value) < 1e15:
            return int(value)
        return value
    return value


def _literal_value(text: str):
    """What a cell that is not a formula holds."""
    if text.startswith("="):
        return None                     # goes through the evaluator instead
    try:
        number = float(text)
    except ValueError:
        return None                     # words are not list elements
    if not math.isfinite(number):
        return None
    return _as_number(number)


def _short_float(value) -> str:
    """Six significant digits, and no trailing ``.0`` -- as the screen shows."""
    if isinstance(value, float):
        if not math.isfinite(value):
            return str(value)
        if value == int(value) and abs(value) < 1e15:
            return str(int(value))
        return f"{value:.6g}"
    return str(value)


# --------------------------------------------------------------------------
# a column of data, and the arithmetic TI gives one
# --------------------------------------------------------------------------
class TiList(list):
    """A column's values, with the arithmetic the handheld gives lists.

    ``b[]/a[]`` has to be element-wise, because one formula in the grey row
    defines every row of the column: element *i* of the answer is what row *i*
    shows.  Python would refuse to divide two lists at all, so the operations
    live here.

    A void propagates rather than raising.  A hole in the data makes the
    corresponding result a hole -- ``{1,,3}*2`` is ``{2,,6}`` -- because a
    missing observation is not an error, it is a missing observation.
    """

    __slots__ = ()

    @staticmethod
    def _zip(left: list, right, op):
        if isinstance(right, (list, tuple)):
            if len(right) != len(left):
                raise SheetError(
                    f"these lists have different lengths, {len(left)} and "
                    f"{len(right)}"
                )
            pairs = zip(left, right)
        else:
            pairs = ((a, right) for a in left)
        return type(left)(None if a is None or b is None else op(a, b)
                          for a, b in pairs)

    def __add__(self, other):
        return self._zip(self, other, lambda a, b: a + b)

    __radd__ = __add__

    def __sub__(self, other):
        return self._zip(self, other, lambda a, b: a - b)

    def __rsub__(self, other):
        return self._zip(self, other, lambda a, b: b - a)

    def __mul__(self, other):
        return self._zip(self, other, lambda a, b: a * b)

    __rmul__ = __mul__

    def __truediv__(self, other):
        return self._zip(self, other, lambda a, b: a / b)

    def __rtruediv__(self, other):
        return self._zip(self, other, lambda a, b: b / a)

    def __pow__(self, other):
        return self._zip(self, other, lambda a, b: a ** b)

    def __rpow__(self, other):
        return self._zip(self, other, lambda a, b: b ** a)

    def __neg__(self):
        return type(self)(None if v is None else -v for v in self)

    def __pos__(self):
        return type(self)(self)


# --------------------------------------------------------------------------
# one column
# --------------------------------------------------------------------------
class Column:
    """A column: its name, its formula, and the cells typed into it."""

    __slots__ = ("letter", "name", "formula", "cells", "_cache", "_sheet")

    def __init__(self, letter: str, sheet: "Sheet") -> None:
        self.letter = letter
        self.name = ""
        self.formula = ""
        self.cells: dict = {}        # 1-based row -> the text typed in it
        self._cache: dict = {}       # 1-based row -> evaluated value
        self._sheet = sheet

    # -- reading -----------------------------------------------------------
    def raw_at(self, row: int) -> str:
        """What the cell holds as text: its own entry, else the column formula."""
        text = self.cells.get(row, "")
        return text if text != "" else self.formula

    def is_formula_at(self, row: int) -> bool:
        return self.raw_at(row).startswith("=")

    def value_at(self, row: int):
        """The evaluated value of one cell: a number, an int, or ``None``.

        A formula's answer may be a whole column -- ``=b[]/a[]`` is one -- and
        then this cell shows the element that belongs to it.  ``row`` is 1-based
        and the list is not, which is the whole of the off-by-one.
        """
        row = int(row)
        if row in self._cache:
            return self._cache[row]
        # A formula that reaches back into the cell it is working out -- `=a[]`
        # in column A's formula row -- is a circular definition.  The handheld
        # reports it rather than recursing, so this does too.
        if (self.letter, row) in self._sheet._resolving:
            raise SheetError(f"{self.letter}{row} refers to itself")
        text = self.raw_at(row)
        if text == "":
            self._cache[row] = None
            return None
        if text.startswith("="):
            self._sheet._resolving.add((self.letter, row))
            try:
                value = evaluate(text, self._sheet)
            finally:
                self._sheet._resolving.discard((self.letter, row))
            if isinstance(value, list):
                value = value[row - 1] if 1 <= row <= len(value) else None
        else:
            value = _literal_value(text)
        self._cache[row] = value
        return value

    def values(self, rows: int) -> list:
        """The column as a list, ``None`` where a cell is void.

        This is what a named column hands to the statistics functions, so the
        order is the device's, and a hole stays a hole: ``OneVar`` on a list
        with a void in the middle must see the void, because that is what makes
        the rest of that row void too.  Trailing voids are not part of the list.

        A plain ``list``, deliberately: this is the *variable*, and a variable
        is a list.  Only a formula's own ``a[]`` needs the arithmetic, and it
        wraps this in a :class:`TiList` where it binds it.
        """
        out = [self.value_at(row) for row in range(1, rows + 1)]
        while out and out[-1] is None:
            out.pop()
        return out

    # -- editing -----------------------------------------------------------
    def set_cell(self, row: int, text) -> None:
        # `text` may arrive as a number -- the page reads a bare `2` off the
        # keypad.  `str(text or "")` would be the tempting one-liner and would
        # silently turn the number 0 into an empty cell.
        text = "" if text is None else str(text).strip()
        if text == "":
            self.cells.pop(row, None)
        else:
            self.cells[row] = text
            # Typing a plain value into a column that has a formula drops the
            # formula: the grey cell and the data cannot both own every cell,
            # and the handheld resolves it the same way.
            if self.formula and not text.startswith("="):
                self.formula = ""
        self.clear_cache()

    def drop(self) -> None:
        self.name = ""
        self.formula = ""
        self.cells.clear()
        self.clear_cache()

    def clear_cache(self) -> None:
        self._cache.clear()


# --------------------------------------------------------------------------
# the sheet
# --------------------------------------------------------------------------
def statistics_functions() -> dict:
    """This package's own functions, as a formula environment.

    A cell formula may call anything the Calculator page can, so ``=mean(a[])``
    works.  Resolved lazily because ``sheet`` is imported by the package itself.
    """
    import tinspire_stats as pkg

    return {name: getattr(pkg, name) for name in dir(pkg)
            if not name.startswith("_") and callable(getattr(pkg, name, None))}


class Sheet:
    """The grid, and the list variables it defines.

    ``environment`` is the namespace a formula may call into.  It defaults to
    this package's own functions, and the page adds its session's variables on
    top so a formula can use them too.
    """

    def __init__(self, rows: int = 20, environment: "dict | None" = None) -> None:
        self.rows = max(1, min(int(rows), MAX_ROWS))
        self.environment: dict = (statistics_functions() if environment is None
                                  else dict(environment))
        self._resolving: set = set()
        self.columns: dict = {letter_of(i): Column(letter_of(i), self)
                              for i in range(MAX_COLUMNS)}

    def _touch(self) -> None:
        """Every cached cell value is suspect after an edit.

        Editing A1 has to invalidate B1's formula when B1 reads A1, so an edit
        clears the whole grid rather than the one column that was touched.
        Twenty-six small dicts are cheaper than tracking dependencies, and the
        device recalculates the sheet on an edit too.
        """
        for column in self.columns.values():
            column.clear_cache()

    # -- the list variables ------------------------------------------------
    def bindings(self) -> dict:
        """``{list name: values}`` for every named column that holds data.

        A name on an empty column defines nothing, which is what the device
        does: naming a column and leaving it blank does not put an empty list
        into the variable list.

        A column whose formula cannot be worked out defines nothing either.  The
        error is the cell's to report, and a variable list that refused to be
        read because one cell was broken would take the whole session with it.
        """
        out = {}
        for column in self.columns.values():
            if not column.name:
                continue
            try:
                values = column.values(self.rows)
            except SheetError:
                continue
            if any(v is not None for v in values):
                out[column.name] = values
        return out

    def names(self) -> dict:
        """``{list name: column letter}`` -- the reverse lookup."""
        return {c.name: c.letter for c in self.columns.values() if c.name}

    # -- reading -----------------------------------------------------------
    def value_at(self, letter: str, row: int):
        return self.columns[letter_of(index_of(letter))].value_at(row)

    def raw_at(self, letter: str, row: int) -> str:
        return self.columns[letter_of(index_of(letter))].raw_at(row)

    # -- editing -----------------------------------------------------------
    def set_name(self, letter: str, name: str) -> None:
        letter = letter_of(index_of(letter))
        name = (name or "").strip()
        if name:
            if not valid_list_name(name):
                raise SheetError(
                    f"{name!r} cannot be a list name -- a letter first, "
                    "then letters, digits or _"
                )
            if name in reserved_names():
                raise SheetError(
                    f"{name} is a name the calculator already uses"
                )
            owner = self.names().get(name)
            if owner and owner != letter:
                raise SheetError(f"{name} is already column {owner}")
        self.columns[letter].name = name

    def set_formula(self, letter: str, text: str) -> None:
        column = self.columns[letter_of(index_of(letter))]
        column.formula = (text or "").strip()
        self._touch()

    def set_cell(self, letter: str, row: int, text: str) -> None:
        row = int(row)
        if not 1 <= row <= MAX_ROWS:
            raise SheetError(f"there is no row {row}")
        if row > self.rows:
            self.rows = row                # typing below the last row grows it
        self.columns[letter_of(index_of(letter))].set_cell(row, text)
        self._touch()

    def clear_all(self) -> None:
        for column in self.columns.values():
            column.drop()
        self.rows = 20

    # -- the Actions and Data menus ---------------------------------------
    def fill_down(self, letter: str, from_row: int, to_row: "int | None" = None) -> int:
        """Repeat a cell's value or formula down its column.

        Relative row references shift, so ``=a1*1.05`` in row 2 becomes
        ``=a2*1.05`` in row 3.  Returns how many cells were written.
        """
        column = self.columns[letter_of(index_of(letter))]
        from_row = int(from_row)
        if not 1 <= from_row <= MAX_ROWS:
            raise SheetError(f"there is no row {from_row}")
        last = self.rows if to_row is None else min(int(to_row), MAX_ROWS)
        text = column.raw_at(from_row)
        if text == "":
            raise SheetError(
                f"{column.letter}{from_row} is empty -- there is nothing to fill"
            )
        written = 0
        for row in range(from_row + 1, last + 1):
            column.cells[row] = (shift_for_fill(text, from_row, row)
                                 if text.startswith("=") else text)
            written += 1
        if last > self.rows:
            self.rows = min(last, MAX_ROWS)
        self._touch()
        return written

    def sort_by(self, letter: str, ascending: bool = True) -> None:
        """Sort the data rows by one column, carrying the others along.

        The *row* is the unit, as on the device: sorting column A reorders every
        column, because otherwise a row would stop being one observation.

        Voids and text go last in **either** direction.  Reversing the whole sort
        would put them first when descending, which is not what "last" means --
        a blank row is not the largest observation, it is the absence of one.

        The sort covers the rows that hold data, not the whole grid: rows below
        the last entry are empty, and letting them into the ordering is how a
        descending sort lands its answer at the bottom of the screen.
        """
        column = self.columns[letter_of(index_of(letter))]
        extent = self._extent()
        if extent < 1:
            return
        data, voids = [], []
        for row in range(1, extent + 1):
            value = column.value_at(row)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                voids.append(row)
            else:
                data.append((float(value), row))
        data.sort(key=lambda pair: pair[0], reverse=not bool(ascending))
        order = [row for _, row in data] + voids

        moved = {c.letter: [c.raw_at(row) for row in order]
                 for c in self.columns.values()}
        for c in self.columns.values():
            c.cells.clear()
            for position, text in enumerate(moved[c.letter], start=1):
                if text != "":
                    c.cells[position] = text
        self._touch()

    def _extent(self) -> int:
        """The last row that holds anything, in any column.

        A column with a formula but no cells it owns reaches every row, because
        the grey row applies to all of them.
        """
        last = 0
        for column in self.columns.values():
            if column.cells:
                last = max(last, max(column.cells))
            elif column.formula:
                last = max(last, self.rows)
        return min(last, self.rows)

    def move_column(self, source: str, target: str) -> None:
        """Move a column into another column's place, shifting the rest along.

        Names travel with the data, because a name *is* the column's identity.
        """
        source, target = letter_of(index_of(source)), letter_of(index_of(target))
        if source == target:
            return
        letters = list(self.columns)
        # Both positions are read before anything moves: the target's index is
        # the slot the source should occupy in the *original* order, so
        # A -> C gives B, C, A rather than B, A, C.
        source_at, target_at = letters.index(source), letters.index(target)
        letters.pop(source_at)
        letters.insert(target_at, source)
        moved = {letter: self.columns[letter] for letter in letters}
        for position, letter in enumerate(moved):
            column = moved[letter]
            column.letter = letter_of(position)
            self.columns[letter_of(position)] = column
        self._touch()

    def resize(self, rows: int) -> None:
        rows = int(rows)
        if not 1 <= rows <= MAX_ROWS:
            raise SheetError(f"the grid holds between 1 and {MAX_ROWS} rows")
        for column in self.columns.values():
            for row in [r for r in column.cells if r > rows]:
                del column.cells[row]
        self.rows = rows
        self._touch()

    def recalculate(self) -> None:
        """Drop every cached value, so the next read recomputes from scratch."""
        self._touch()

    # -- the screen --------------------------------------------------------
    def snapshot(self) -> dict:
        """Everything the page needs to draw the grid and the variable list.

        A cell is filled while it is inside the column's list and blank past
        the end of it.  That distinction is the device's: the eGuide says "any
        empty (void) element in a list is displayed as an underscore", and the
        underscores stop where the list stops -- they do not run to the bottom
        of the screen.
        """
        return {
            "rows": self.rows,
            "columns": [
                {
                    "letter": letter,
                    "name": self.columns[letter].name,
                    "formula": self.columns[letter].formula,
                    "cells": self._screen_column(self.columns[letter]),
                }
                for letter in self.columns
            ],
            "bindings": self.bindings(),
        }

    def _screen_column(self, column: "Column") -> dict:
        """One column as the screen shows it: values, voids, and errors.

        The extent of the list is what decides where the underscores stop, and
        that is ``values()``.  A column where something cannot be worked out
        goes the other way round -- see below.
        """
        try:
            values = column.values(self.rows)
        except SheetError:
            return self._screen_column_showing_errors(column)
        return {str(row): (display(values[row - 1]) if row <= len(values) else "")
                for row in range(1, self.rows + 1)}

    def _screen_column_showing_errors(self, column: "Column") -> dict:
        """The same, row by row, so one unworkable cell does not blank the sheet.

        A formula with a mistake in it applies to every row of its column, so
        this is usually every row -- which is what the device does too.  The
        point is that the message lands *in the cell*.  A grid that could not be
        drawn at all because one cell was wrong would turn a mistake the user
        can see and fix into a blank page.
        """
        texts, last = {}, 0
        for row in range(1, self.rows + 1):
            if column.raw_at(row) == "":
                continue                     # nothing here: past the end
            try:
                texts[row] = display(column.value_at(row))
            except SheetError as exc:
                texts[row] = f"Error: {exc.ti_message}"
            last = row
        return {str(row): (texts[row] if row <= last else "")
                for row in range(1, self.rows + 1)}


#: What the device prints in a cell whose element is void.
VOID_GLYPH = "_"


def display(value) -> str:
    """One cell value as the screen shows it.

    A void is an underscore, not a blank: the device uses the blank for a cell
    outside the list and the underscore for an element the list has but cannot
    show a value for.
    """
    if value is None:
        return VOID_GLYPH
    if isinstance(value, bool):
        return "1" if value else "0"
    return _short_float(value)


# --------------------------------------------------------------------------
# evaluation
# --------------------------------------------------------------------------
def evaluate(text: str, sheet: Sheet):
    """Work out one formula cell.

    ``text`` is what the cell holds, starting with ``=``.  Cell references are
    rewritten to identifiers and bound before the expression runs, so what is
    evaluated is ordinary arithmetic over numbers -- and a formula can call any
    function in the sheet's ``environment``.

    A whole-column reference (``a[]``) binds the entire column as a
    :class:`TiList`, which is what makes ``=mean(a[])`` work and what makes
    ``=b[]/a[]`` element-wise.  A bare name binds the list variable of that name,
    as TI's syntax table says it does.

    The answer may be a list.  That is a column-wide result -- the caller's job
    is to pick out the element belonging to the row it is displaying.
    """
    body = text[1:] if text.startswith("=") else text
    if body.strip() == "":
        return None
    try:
        tree = ast.parse(_rewrite(body), mode="eval")
    except SyntaxError as exc:
        raise SheetError(f"{text} is not a formula I can read") from exc
    _check(tree)

    scope = dict(sheet.environment)
    # Only what the formula actually mentions is resolved, so a sheet full of
    # formulas does not evaluate every column to work out any one of them --
    # and a column that cannot be evaluated at all stays out of the way of a
    # formula that never asked for it.
    for name, letter in sheet.names().items():
        if re.search(_NOT_IN_WORD + re.escape(name) + _NOT_IN_WORD_END, body):
            scope[name] = sheet.columns[letter].values(sheet.rows)
            scope[_var_name(name)] = scope[name]
    # `a1` -- one cell, whichever column it is in.
    for match in _CELL_REF.finditer(body):
        letter, ref_row = match.group(2).upper(), int(match.group(4))
        if valid_column_letter(letter):
            scope[_ref_name(letter, ref_row)] = sheet.columns[letter].value_at(ref_row)
    # `a[]` -- the whole column.  Left as a TiList so that dividing one column
    # by another divides them element by element, as the device does.
    for match in _COLUMN_REF.finditer(body):
        letter = match.group(1).upper()
        if valid_column_letter(letter):
            scope[_col_name(letter)] = TiList(
                sheet.columns[letter].values(sheet.rows))

    try:
        value = eval(compile(tree, "<cell>", "eval"),  # noqa: S307 - names only
                     {"__builtins__": {}}, scope)
    except ZeroDivisionError as exc:
        raise SheetError("a formula divided by zero") from exc
    except SheetError:
        raise
    except Exception as exc:
        raise SheetError(f"{text} did not work out: {exc}") from exc
    if isinstance(value, list):
        return value                     # a column-wide answer; see the caller
    if isinstance(value, bool):
        return value
    if not isinstance(value, (int, float)):
        # A formula is arithmetic; anything else is a mistake, and a void cell
        # is a better answer than a string in a list of numbers.
        return None
    return _as_number(value)
