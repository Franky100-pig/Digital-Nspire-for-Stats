"""Browser entry point for the TI-Nspire statistics web app.

``la-bridge.js`` writes this file -- plus the whole ``tinspire_stats`` package --
into Pyodide's virtual filesystem, imports this module, and then calls
``_la_dispatch(payload)`` once per interaction.

The point of this layer is to let someone type what they would type on the
handheld and get back the handheld's own output, so the parser speaks TI:

    OneVar {1,2,4,8,16}          curly braces are lists, as on the calculator
    tInterval 2,1.5,25,.95       omitted optional arguments are empty fields
    tInterval {3,4,5},,0.95      ...which is how you skip one in the middle
    LinRegMx {1,2,3},{5,8,11}

A command that is not a function call is evaluated as an expression instead,
and the session persists between commands -- so ``stat.Q1X * 2`` works as the
very next thing you type, exactly as it would on the calculator.  ``stat``
still holds the results of the previous command.
"""

from __future__ import annotations

import importlib
import json
import math
import re
import traceback

from tinspire_stats import legacy, menu, stat
from tinspire_stats.catalog import catalog as _catalog
from tinspire_stats.statvar import StatGroup

#: Expression evaluation is sandboxed down to the handful of builtins that are
#: useful in a calculator expression, so ``__import__`` is not reachable from
#: the command box.
_SAFE_BUILTINS = {
    "abs": abs, "min": min, "max": max, "sum": sum, "round": round, "len": len,
    "int": int, "float": float, "bool": bool, "list": list, "tuple": tuple,
    "dict": dict, "set": set, "sorted": sorted, "range": range, "str": str,
    "None": None, "True": True, "False": False,
}


# ==========================================================================
# JSON-safety
# ==========================================================================
# The bridge does JSON.parse on whatever we return, and JSON.parse rejects
# bare NaN/Infinity, so no non-finite float may survive this function.
def _jsonable(value, depth=0):
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        return value
    if depth > 8:
        return str(value)
    if isinstance(value, dict):
        return {str(k): _jsonable(v, depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(v, depth + 1) for v in value]
    if hasattr(value, "symbolic"):
        return {
            "symbolic": str(value.symbolic),
            "evaluated": str(value),
            "callable": callable(value),
        }
    return str(value)


# ==========================================================================
# Display formatting
# ==========================================================================
def _num_text(v: float) -> str:
    """A number the way the handheld writes it.

    Ten significant digits, a decimal point on whole numbers, and -- where the
    value is too big or too small to write out -- TI's own exponent notation,
    ``1.2E20`` and ``1.E-7``.  Python would say ``1.2e+20`` and ``1e-07``: an
    extra ``+``, a padded exponent, and a lowercase marker, none of which the
    calculator prints.
    """
    if v != v:
        return "NaN"
    if v == math.inf:
        return "\u221e"
    if v == -math.inf:
        return "-\u221e"
    if v.is_integer() and abs(v) < 1e16:
        return f"{v:.1f}"
    text = f"{v:.10g}"
    if "e" in text:
        mantissa, _, exponent = text.partition("e")
        if "." not in mantissa:
            mantissa += "."
        return f"{mantissa}E{int(exponent)}"
    return text


#: A list longer than this is cut off for display.  The real length still
#: travels to the UI in the ``length`` field, so nothing is silently hidden.
_LIST_CAP = 12


def _scalar_text(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return _num_text(value)
    if hasattr(value, "symbolic"):
        return str(value)
    return str(value)


def _list_text(seq, depth=0) -> str:
    """A list the way the handheld writes it: ``{1,2,3}``.

    Braces, commas, and **no spaces** -- exactly what ``{1,2,3}`` on the entry
    line turns into, and what the package's own ``stat.results`` prints.
    """
    items = list(seq)
    parts = []
    for item in items[:_LIST_CAP]:
        if isinstance(item, (list, tuple)):
            parts.append(_list_text(item, depth + 1) if depth < 3 else "{\u2026}")
        else:
            parts.append(_scalar_text(item))
    body = ",".join(parts)
    if len(items) > _LIST_CAP:
        body += ",\u2026"
    return "{" + body + "}"


def _describe(value, _depth=0):
    """Return ``(text, kind, length)`` for one result value."""
    if isinstance(value, bool):
        return ("true" if value else "false", "bool", None)
    if isinstance(value, float):
        return (_num_text(value), "number", None)
    if isinstance(value, int):
        return (str(value), "number", None)
    if isinstance(value, str):
        return (value, "text", None)
    if isinstance(value, (list, tuple, set, frozenset)):
        seq = list(value)
        nested = bool(seq) and isinstance(seq[0], (list, tuple))
        return (_list_text(seq), "matrix" if nested else "list", len(seq))
    if hasattr(value, "symbolic"):
        return (str(value), "equation", None)
    return (str(value), "text", None)


def _row(name, value):
    text, kind, length = _describe(value)
    return {
        "name": str(name),
        "text": text,
        "kind": kind,
        "length": length,
        "raw": _jsonable(value),
    }


# ==========================================================================
# Function registry
# ==========================================================================
_FUNCS = None
_NS = {}


def _funcs():
    """TI-Nspire functions, keyed by every spelling we accept for them."""
    global _FUNCS
    if _FUNCS is not None:
        return _FUNCS
    table = {}
    for row in _catalog():
        if row["kind"] != "ti":
            continue
        try:
            module = importlib.import_module(row["module"])
            fn = getattr(module, row["name"])
        except Exception:  # pragma: no cover - a broken export is not fatal here
            continue
        table[row["name"]] = fn
        if row["ti"] != row["name"]:
            table.setdefault(row["ti"], fn)
        if row["ascii"] not in table:
            table[row["ascii"]] = fn
    _FUNCS = table
    return table


def _registry():
    """The catalogue, restricted to real TI functions, with a display group."""
    groups = {
        "summary": ("summary", "Summary statistics"),
        "listmath": ("lists", "List math"),
        "regress": ("regress", "Regression"),
        "distributions": ("distributions", "Distributions"),
        "inference": ("inference", "Intervals & tests"),
        "statvar": ("session", "Session & variables"),
    }
    random_names = {"rand", "randInt", "randNorm", "randBin", "randSamp", "RandSeed"}
    out = []
    for row in _catalog():
        if row["kind"] != "ti":
            continue
        module = row["module"].rsplit(".", 1)[-1]
        if row["name"] in random_names:
            key, label = "random", "Random numbers"
        else:
            key, label = groups.get(module, (module, module))
        doc = ""
        try:
            module_obj = importlib.import_module(row["module"])
            doc = (getattr(module_obj, row["name"]).__doc__ or "").strip()
        except Exception:
            doc = ""
        out.append({
            "name": row["ti"],
            "ascii": row["ascii"],
            "call": row["name"],
            "signature": row["signature"],
            "group": key,
            "groupLabel": label,
            "fidelity": row["fidelity"],
            "doc": doc,
        })
    out.sort(key=lambda r: (r["groupLabel"], r["name"].lower()))
    return out


def _signature_line(fn):
    """First line of a function's docstring -- which is its TI call form."""
    doc = (getattr(fn, "__doc__", "") or "").strip()
    if not doc:
        return ""
    first = doc.splitlines()[0].strip().replace("``", "").rstrip(".")
    # The guide writes a call form as either name(...) or name arg,arg -- both
    # count; anything else on line one is prose, not a signature.
    return first if ("(" in first or "," in first) else ""


def _seed(ns):
    """The names every fresh session starts with."""
    ns.update({"stat": stat, "math": math})
    # Calculator-level conveniences.  Real TI functions win: they are added
    # afterwards with setdefault, by which point they are already present.
    ns.update({
        "sqrt": math.sqrt, "abs": abs, "floor": math.floor, "ceil": math.ceil,
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "ln": lambda x: math.log(x) if x > 0 else float("-inf"),
        "log": lambda x: math.log10(x) if x > 0 else float("-inf"),
        "exp": math.exp, "pi": math.pi, "\u03c0": math.pi, "e": math.e,
        "inf": math.inf, "\u221e": math.inf,
        "sqrt": math.sqrt, "cbrt": lambda x: math.copysign(abs(x) ** (1 / 3), x),
        "sign": lambda x: (x > 0) - (x < 0),
    })


def _namespace():
    if not _NS:
        _seed(_NS)
    for key, fn in _funcs().items():
        _NS.setdefault(key, fn)
    return _NS


def _eval(text):
    scope = {"__builtins__": _SAFE_BUILTINS}
    scope.update(_namespace())
    return eval(_to_python(text), scope)  # noqa: S307 - sandboxed builtins


def _stat_sig():
    """Fingerprint of the ``stat`` group, to tell a fresh result from a carried-over one.

    ``repr`` rather than ``id``: identical values have to compare *equal*, because
    the question is "did this command change ``stat``", not "is this a new object".
    """
    try:
        return tuple((k, repr(stat[k])) for k in stat.keys())
    except Exception:  # pragma: no cover
        return None


#: Remembers the last command, so re-running the same one is not mislabelled as
#: "carried over" purely because it produced byte-identical results.
_STATE = {"last_input": None}

#: Functions observed to actually write the ``stat`` group.  Learned at runtime
#: rather than hard-coded, because the catalogue does not record which
#: calculations park a result and which just return a number (``invNorm`` does
#: not touch ``stat``; ``OneVar`` does).
_STAT_WRITERS: set = set()


def _legacy_hint(text):
    """If ``text`` starts with a name that is *not* a TI-Nspire name, say so.

    This is the whole point of the project's legacy registry: someone typing
    ``stdev`` (a TI-84 spelling) or ``TwoSampleTTest`` (a menu label) should be
    told the catalog name, not handed a Python syntax error.
    """
    head = re.split(r"[\s(\[{]", text.strip(), maxsplit=1)[0]
    if not head or head in _NS:
        return None
    try:
        target = getattr(legacy, head)
    except Exception:
        return None
    real = getattr(target, "__name__", None)
    if not real or real == head:
        return None
    note = ""
    try:
        note = legacy.notes().get(head, "")
    except Exception:
        note = ""
    standing = ""
    try:
        standing = legacy.kind_of(head)
    except Exception:
        standing = ""
    where = f" ({standing})" if standing else ""
    why = f" {note}" if note else ""
    return {
        "ok": False,
        "error": {
            "kind": "NotATINspireName",
            "message": f"`{head}` is not a TI-Nspire name{where}.{why} "
                       f"On the calculator this is `{real}` -- type `{real}` instead.",
            "detail": f"legacy alias {head} -> {real}",
            "ti": False,
            "suggest": real,
            "suggestInput": real + text.strip()[len(head):],
        },
    }


# ==========================================================================
# TI-flavoured argument parsing
# ==========================================================================
_NUMBER = re.compile(r"^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$")
_INTEGER = re.compile(r"^[+-]?\d+$")

#: Characters the calculator prints but Python does not understand.
#:
#: Two of these are more than cosmetic:
#:
#: * ``^`` is a power sign on every calculator ever made and *bitwise xor* in
#:   Python, so ``2^3`` silently evaluates to 1.  Silently is the problem -- a
#:   wrong answer beats an error only in how hard it is to notice.
#: * ``√`` binds to the next number or bracketed group (``√16``, ``√(2+2)``),
#:   which is not an infix operator and so needs its own pass.
#:
#: The rest -- ``×``, ``÷``, ``·``, the Unicode minus, ``≤``, ``≥``, ``≠``,
#: ``π``, ``²`` -- are what the keypad above actually prints on its keys, and
#: typing them should work for the same reason the function names do: what you
#: type should be what the handheld would accept.
_TI_GLYPHS = (
    ("\u00d7", "*"),    # multiplication sign
    ("\u22c5", "*"),    # dot operator
    ("\u00b7", "*"),    # middle dot
    ("\u00f7", "/"),    # division sign
    ("\u2212", "-"),    # minus sign (not hyphen)
    ("\u2013", "-"),    # en dash
    ("\u2264", "<="),   # less-than-or-equal
    ("\u2265", ">="),   # greater-than-or-equal
    ("\u2260", "!="),   # not equal
    ("\u221e", "inf"),  # infinity
    ("\u03c0", "pi"),   # pi
    ("\u221a", "sqrt"),  # radical, after its operand has been bracketed
)

#: Superscript digits, which the handheld writes as ``x²``.
_SUPERSCRIPT = {
    "\u00b2": "2", "\u00b3": "3", "\u2074": "4",
    "\u2075": "5", "\u2076": "6", "\u2077": "7",
}


def _to_python(text: str) -> str:
    """Rewrite calculator notation as the Python it means.

    Applied only on the way to ``eval``: tokens that are handed to a function as
    text (criteria such as ``?<5``, quoted strings) never come through here, so
    ``≤`` still reaches ``make_criteria`` as itself.
    """
    # √ swallows the following group or number, so bracket it first.
    text = re.sub(r"\u221a\s*\(([^()]*)\)", r"sqrt(\1)", text)
    text = re.sub(r"\u221a\s*(\d+(?:\.\d+)?)", r"sqrt(\1)", text)
    # Implicit multiplication, as on the handheld: 2π and 3(4+1) both mean a
    # product.  Kept deliberately narrow -- a digit or a closing bracket before
    # π, ∞ or an opening bracket -- because a general rule would start eating
    # function names.
    text = re.sub(r"(\d)\s*(?=[\u03c0\u221e])", r"\1*", text)
    text = re.sub(r"(\d|\))\s*\(", r"\1*(", text)
    for glyph, plain in _TI_GLYPHS:
        text = text.replace(glyph, plain)
    # ^ is power here, not xor.  Leave an existing ** alone.
    text = re.sub(r"(?<!\*)\^(?!\*)", "**", text)
    for glyph, digit in _SUPERSCRIPT.items():
        text = re.sub(r"([A-Za-z0-9_)\]])\s*" + glyph, r"\1**" + digit, text)
    return text


def _split_top(text, sep=","):
    """Split on ``sep`` at depth zero, ignoring separators inside {}/[]/()/quotes."""
    parts, depth, buf, quote = [], 0, [], None
    for ch in text:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            buf.append(ch)
            continue
        if ch in "{[(":
            depth += 1
        elif ch in "}])":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    parts.append("".join(buf))
    return parts


def _split_assignment(text):
    """Find a top-level ``=`` that is not part of ==, !=, <= or >=."""
    depth, quote = 0, None
    for i, ch in enumerate(text):
        if quote:
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            continue
        if ch in "{[(":
            depth += 1
            continue
        if ch in "}])":
            depth -= 1
            continue
        if ch == "=" and depth == 0:
            if (i and text[i - 1] in "=!<>") or (i + 1 < len(text) and text[i + 1] == "="):
                continue
            return text[:i], text[i + 1:]
    return None, None


def _literal(token):
    """One argument: list, number, bool, string, variable or expression."""
    text = token.strip().replace("\u2212", "-").replace("\u2013", "-")
    if text == "":
        return None  # an omitted optional argument, as on the calculator
    if len(text) >= 2 and text[0] == "{" and text[-1] == "}":
        inner = text[1:-1]
        return [_literal(p) for p in _split_top(inner)] if inner.strip() else []
    if len(text) >= 2 and text[0] == "[" and text[-1] == "]":
        inner = text[1:-1]
        return [_literal(p) for p in _split_top(inner)] if inner.strip() else []
    if len(text) >= 2 and text[0] == "(" and text[-1] == ")" and "," in text:
        return [_literal(p) for p in _split_top(text[1:-1])]
    if text in ("\u221e", "inf", "Infinity", "+inf"):
        return math.inf
    if text in ("-\u221e", "-inf", "-Infinity"):
        return -math.inf
    if text in ("\u03c0", "pi"):
        return math.pi
    if text.lower() in ("true", "yes"):
        return True
    if text.lower() in ("false", "no"):
        return False
    if _NUMBER.match(text):
        return int(text) if _INTEGER.match(text) else float(text)
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    # TI's criteria syntax.  The guide writes countif(List,?<5) -- the '?' is a
    # placeholder for each element, which is not Python, so the token has to be
    # handed to make_criteria as text rather than evaluated.
    if "?" in text and re.search(r"[<>\u2264\u2265\u2260=]", text):
        return text
    if re.match(r"^(<=|>=|!=|[<>\u2264\u2265\u2260])", text):
        return text  # the guide's bare relational shorthand, e.g. '>4'
    return eval(_to_python(text), dict(_namespace()))  # noqa: S307 - the user's own browser


def _find_call(text):
    """Split ``text`` into (function name, argument text) if it is a call."""
    table = _funcs()
    for name in sorted(table, key=len, reverse=True):
        if text == name:
            return name, ""
        if text.startswith(name):
            rest = text[len(name):]
            if rest[0] in " \t({[":
                return name, rest.strip()
    return None, None


def _balanced_parens(text):
    depth = 0
    quote = None
    for i, ch in enumerate(text):
        if quote:
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i == len(text) - 1
    return False


# ==========================================================================
# Errors
# ==========================================================================
def _error(exc, signature=None):
    kind = type(exc).__name__
    if hasattr(exc, "ti_message"):
        payload = {
            "ok": False,
            "error": {
                "kind": kind,
                "message": exc.ti_message,
                "detail": str(exc),
                "ti": True,
            },
        }
    else:
        detail = str(exc) or kind
        message = detail
        if isinstance(exc, NameError):
            message = f"{detail} -- a bare name has to be a function, or something you defined earlier."
        elif isinstance(exc, SyntaxError):
            message = f"{detail} -- check the commas; a list is {{1,2,3}}."
        payload = {"ok": False, "error": {"kind": kind, "message": message, "detail": detail, "ti": False}}
    if signature:
        payload["error"]["signature"] = signature
    return payload


# ==========================================================================
# Operations
# ==========================================================================
def _result_payload(value, label, doc, input_text, before=None):
    rows = []
    try:
        keys = list(stat.keys())
    except Exception:  # pragma: no cover - stat is always a group here
        keys = []
    after = _stat_sig()
    # "carried over" means: this command produced no new stat block, so what is
    # on screen belongs to an earlier command.  A function already known to write
    # stat is exempt -- re-running OneVar legitimately reproduces the same
    # numbers, and calling that "carried over" would be a lie.
    carry = bool(keys) and before is not None and before == after \
        and label not in _STAT_WRITERS
    for key in keys:
        rows.append(_row(key, stat[key]))
    if value is None or isinstance(value, StatGroup):
        summary = None  # the variable table *is* the answer
    else:
        summary = _describe(value)[0]
    return {
        "ok": True,
        "label": label,
        "doc": doc,
        "input": input_text,
        "summary": summary,
        "carry": carry,
        "vars": rows,
    }


def _op_run(payload):
    text = str(payload.get("input", "")).strip()
    if not text:
        return {
            "ok": False,
            "error": {"kind": "EmptyInput", "message": "Type a command first.", "ti": False},
        }
    _namespace()  # so _legacy_hint can tell a typo from a variable you defined
    before = _stat_sig()

    # 0. stat.results -- the variable the Statistics menu's own second line
    #    inserts.  It asks for the block that is already there, so it is not
    #    "carried over": it was requested by name.
    if text == menu.STAT_RESULTS:
        rows = [_row(k, stat[k]) for k in stat.keys()]
        return {
            "ok": True,
            "label": menu.STAT_RESULTS,
            "doc": "",
            "input": text,
            "summary": None,
            "carry": False,
            "vars": rows,
        }

    # 1. assignment -- keeps a value for the rest of the session
    target, rhs = _split_assignment(text)
    if target is not None and re.fullmatch(r"\s*[A-Za-z_][A-Za-z0-9_]*\s*", target):
        name = target.strip()
        if name not in _funcs():
            try:
                value = _literal(rhs)
            except Exception as exc:
                return _error(exc)
            _namespace()[name] = value
            text_value, kind, length = _describe(value)
            return {
                "ok": True,
                # only the value: the command line above already shows the name
                "label": text_value,
                "doc": "Stored for the rest of this session. Use it as an argument, e.g. "
                       f"OneVar {name}",
                "input": text,
                "summary": None,
                "assign": True,
                "assignName": name,
                "vars": [],
            }

    # 2. a spelling that is deliberately *not* a TI-Nspire name
    hint = _legacy_hint(text)
    if hint is not None:
        hint["input"] = text
        return hint

    # 3. a call to a TI-Nspire function
    name, rest = _find_call(text)
    if name is not None:
        args_text = rest
        if args_text.startswith("(") and _balanced_parens(args_text):
            args_text = args_text[1:-1]
        try:
            if args_text.strip():
                args = [_literal(part) for part in _split_top(args_text)]
            else:
                args = []
            result = _funcs()[name](*args)
        except Exception as exc:
            # "Argument error" on its own is useless; show the call form the
            # reference guide documents for this function.
            return _error(exc, _signature_line(_funcs()[name]))
        if before != _stat_sig():
            _STAT_WRITERS.add(name)
        doc = ""
        try:
            doc = (getattr(_funcs()[name], "__doc__", "") or "").strip()
        except Exception:
            doc = ""
        return _result_payload(result, name, doc, text, before)

    # 4. anything else is an expression, evaluated against the live session
    try:
        value = eval(_to_python(text), dict(_namespace()))  # noqa: S307
    except Exception as exc:
        return _error(exc)
    return _result_payload(value, text, "", text, before)


def _menu_apps():
    return [
        {"key": key, "label": label, "statisticsKey": _statistics_key(key)}
        for key, (label, _tree) in sorted(menu.APPS.items())
    ]


def _statistics_key(app):
    """Which top-level key opens Statistics in this application's menu."""
    _label, tree = menu.APPS[app]
    for position, item in enumerate(tree):
        if item.label == "Statistics":
            return menu.KEYS[position]
    return None


def _op_menu(payload):
    """Resolve a menu path.

    The screen asks this every time a key is pressed.  A key the menu does not
    offer comes back as an error rather than as a wrong answer, because the
    handheld's own response is to ignore it -- the menu stays where it is.
    """
    payload = payload or {}
    path = payload.get("path", [])
    if isinstance(path, str):
        path = list(path)
    try:
        found = menu.resolve(payload.get("app", "calculator"), path)
    except menu.MenuError as exc:
        return {
            "ok": False,
            "error": {
                "kind": "MenuKey",
                "message": f"There is no {exc.key} on this menu.",
                "detail": str(exc),
                "key": exc.key,
                "where": exc.where,
                "ti": False,
            },
        }

    app_key = menu.app_key(payload.get("app", "calculator"))
    out = {
        "ok": True,
        "kind": found.kind,
        "app": app_key,
        "appLabel": menu.APPS[app_key][0],
        "title": found.title,
        "path": list(found.path),
        "breadcrumb": list(found.breadcrumb),
        "label": found.label,
        "function": found.function,
    }
    if found.kind == "menu":
        out["items"] = [
            {"key": c.key, "label": c.label, "kind": c.kind} for c in found.choices
        ]
    return out


def _op_catalog(_payload):
    return {
        "ok": True,
        "functions": _registry(),
        "apps": _menu_apps(),
        #: The function the menu reaches for stat.results, so the screen can
        #: tell that leaf apart from a callable without hard-coding a string.
        "statResults": menu.STAT_RESULTS,
    }


def _op_reset(_payload):
    """Back to a blank calculator: no stored variables, no leftover results."""
    _NS.clear()
    _seed(_NS)
    stat.publish({})
    return {"ok": True, "message": "Session cleared."}


def _la_dispatch(payload):
    """The entry point the Python-side tests call, with a plain dict."""
    payload = payload or {}
    op = str(payload.get("op", "run"))
    try:
        if op == "run":
            result = _op_run(payload)
            _STATE["last_input"] = str(payload.get("input", "")).strip()
            return result
        if op == "catalog":
            return _op_catalog(payload)
        if op == "menu":
            return _op_menu(payload)
        if op == "reset":
            result = _op_reset(payload)
            _STATE["last_input"] = None
            return result
        return {"ok": False, "error": {"kind": "UnknownOp", "message": f"Unknown op {op!r}"}}
    except Exception as exc:  # last-resort net: never let the UI see a traceback
        return {
            "ok": False,
            "error": {
                "kind": type(exc).__name__,
                "message": "Internal error in the engine.",
                "detail": traceback.format_exc(limit=3),
                "ti": False,
            },
        }


def _la_dispatch_json(text):
    """String in, JSON string out -- the form the browser bridge calls.

    Going through JSON on both sides keeps the boundary explicit: no PyProxy has
    to cross into JavaScript, and no non-finite float can slip past ``_jsonable``.
    """
    try:
        payload = json.loads(text) if text else {}
    except Exception as exc:
        return json.dumps({
            "ok": False,
            "error": {"kind": "BadRequest", "message": f"Malformed request: {exc}", "ti": False},
        })
    if not isinstance(payload, dict):
        payload = {"op": "run", "input": str(payload)}
    return json.dumps(_la_dispatch(payload), ensure_ascii=False)
