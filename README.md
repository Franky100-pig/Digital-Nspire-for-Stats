# tinspire-stats

The TI-Nspire statistics suite, in pure Python — with the calculator's own
**function names** and its own **`stat.` variable names**.

If you can type it on the handheld, you can type it here:

```python
>>> from tinspire_stats import OneVar, LinRegMx, tInterval, stat

>>> OneVar([1, 2, 4, 8, 16])
StatGroup(v, Σx, Σx², sx, σx, n, MinX, Q1X, MedianX, Q3X, MaxX, SSX)
>>> stat.v
6.2
>>> stat["Σx²"]
341.0
>>> stat.σx
5.455272678794342

>>> LinRegMx([1, 2, 3, 4, 5], [5, 8, 11, 14, 17])
StatGroup(RegEqn, m, b, r², r, Resid, XReg, YReg, FreqReg)
>>> stat.RegEqn(6)          # stat.RegEqn is callable, as after CopyVar
20.0
>>> str(stat.RegEqn)
'y=3.·x+2.'

>>> tInterval(2.0, 1.5, 25, 0.95)
StatGroup(CLower, CUpper, v, ME, df, σx, n)
>>> round(stat.ME, 4)
0.6192
```

No dependencies. The whole package runs on the standard library, on Python 3.9
through 3.13 — the older end checked against the stock system interpreter on
macOS, not just by reading the classifier.

---

## Use it in the browser

`web/` builds a page that draws the handheld's front panel — chassis, screen,
touchpad, keypad — and runs the *real* `tinspire_stats` modules inside Pyodide
behind it, with nothing to install and nothing uploaded.

```console
$ python web/fetch_runtime.py          # once: download the interpreter (~13 MB)
$ python web/build_preview.py          # writes web/dist/
$ python web/build_preview.py --serve  # ...then serve it on http://127.0.0.1:8000
```

`web/dist/` is a plain static folder — any web server or GitHub Pages branch
will do. It has to be served over HTTP (not opened as a file), because the
browser fetches the interpreter from `runtime/`.

**The interpreter ships with the page, not from a CDN.** The first version
fetched Pyodide from a public CDN, which worked from a fast connection and did
not work at all from a throttled one: the endpoints mainland China resets are
exactly the ones the page was pointed at, so the page drew its whole interface
and then sat on "Loading the Python runtime" forever with nothing wrong on our
own server. `web/fetch_runtime.py` puts the interpreter next to the page instead
— one origin, one connection, no third party that can be blocked independently
of the site. `la-bridge.js` still knows the CDN addresses, but only as a
fallback for a checkout that has not run `fetch_runtime.py`; if `./runtime/`
answers, no third party is contacted.

What the panel adds on top of the library, because a calculator is not the same
thing as an import:

- `{1,2,3}` is a list, and an argument you skip stays an empty field —
  `tInterval {3,4,5,6,7},,0.95` means "Freq omitted, CLevel 0.95".
- `A = {3,1,4}` names a value for the rest of the session; `stat.Q1X * 2` reads
  the previous result back, exactly as on the handheld.
- `countif A,?<3` passes TI's `?` placeholder straight through to
  `make_criteria`.
- **Arithmetic is the calculator's, not Python's.** `2^3` is 8 — `^` is a power
  sign here, and in Python it is exclusive-or, which would have answered 1.
  `6×7`, `10÷4`, `√16`, `3²`, `2π` and `3(4+1)` all mean what the keys say;
  answers print TI's way too (`1.2E20`, not `1.2e+20`).
- A command that is deliberately *not* a TI-Nspire name gets told so: type
  `stdev` and the panel answers with the catalog spelling, a one-click
  "run `stDevSamp` instead", and the reason the name is filed where it is.
- The `stat.results` block is labelled **carried over** when the command you
  just ran did not write it — so a bare `2+2` is never mistaken for a fresh
  computation.
- The `menu` key opens the handheld's own menus, numbering and all: press
  `menu`, then `4 1 1`, and the entry line holds `OneVar ` — that is the path
  on a Lists & Spreadsheet page. The same function is `6 1 1` on a Calculator
  page, and both menus are modelled, so either habit works. Distributions runs
  to `I` (item 10 is `A`), the touchpad walks a menu line by line, `esc` closes
  it, `◂` backs up a level, and a key the menu does not offer is refused the
  way the handheld refuses it — the menu stays put. Categories outside
  statistics are real entries with their real numbers and say **not supported
  yet** when pressed.
- The keypad is laid out as the CX II has it: the touchpad and the esc / ctrl /
  tab / del cluster, `doc` `menu` `var` and the scratchpad key, the alphabet
  keys in their alphabetical grid with the Greek letter printed above each one
  (hold **ctrl** and the next letter types as that Greek letter, which is the
  handheld's own modifier behaviour), then the symbol row and the numeric pad.
  A physical keyboard works everywhere instead.
- **The theme button cycles three states** — follow the system, light, dark —
  and the choice is remembered, so a light page stays light on the next visit
  even on a machine set to dark. The chassis does not change colour in either
  theme: it is a photograph of an object.
- **The handheld boots to its home screen, and so does this.** The screen you
  land on is the application picker: *Calculate* and *Lists & Spreadsheet* are
  live, and the rest of the handheld's home is there as decoration that says
  **not supported yet**. Nothing opens until you pick — no default page.
  The `Home` chip beside the page chips is the on/home key's stand-in, and it
  takes you back whenever you want.
- **There are two pages, and the second one is a spreadsheet.** The chips above
  the panel switch between *Calculator* and *Lists & Spreadsheet*; the grid is
  the real thing — name a column and it becomes a list variable the Calculator
  page can use. See below.

---

## The Lists & Spreadsheet page

The device's second application is a grid, and on the handheld it is the normal
way to get data into a statistics function: type the column, name the column,
switch to Calculator, run `OneVar` on the name. That whole path works here.

```console
A1..A5   11   8   7   12   9.5      typed on the keypad
A name   mshoe                      tab to the naming band, type the name
menu 6 1 1                          from the Calculator page: One-Variable Statistics
OneVar mshoe
        stat.v = 9.5   stat.Σx = 47.5   stat.sx = 2.061552813   stat.n = 5
```

The grid draws the four bands the eGuide names — the **column reference
letter**, the **column name**, the **column formula**, and the **row reference
number** — with the data under them. `enter` writes into the cell the cursor is
on, the touchpad and the arrow keys move the cursor, `tab` crosses between the
data band and the naming band, and the window follows the cursor so four columns
are on screen at a time.

What it reproduces, and why:

- **`a[]` is the whole column, `a1` is a cell, `'a1` is the variable `a1`.**
  This is TI's own syntax table, printed in *Getting Started with the TI-Nspire
  Handheld* under "Preventing name conflicts" and repeated in the CAS edition,
  the software manual and the Chinese manual. So `D1 = B1/A1` divides two
  element-wise lists rather than two cells, which is why TI's *First Steps with
  TI-Nspire CX* prints `D1=27/11, D2=21/8, D3=20/7, D4=2.375` for exactly that
  formula filled down — and this does the same.
- **`Fill Down` shifts relative row references and leaves `$`-pinned ones
  alone.** `=a1*1.05` in `B1`, filled to `B5`, gives `11.55, 8.4, 7.35, 12.6,
  9.975`; the formula each cell holds is the one you would get by hand.
- **A void is an underscore inside the list and blank past the end.** eGuide:
  "Any empty (void) element in a list is displayed as an underscore (`_`)." A
  void also propagates through a formula rather than being read as zero.
- **A cell that cannot be computed says so, in the cell.** `Error: …` is printed
  where the value would be, in red, and the rest of the column still draws — one
  bad formula must not be able to blank the page.
- **A name the calculator already uses is refused when you type it.** TI: "You
  cannot use a preassigned variable or function name, such as `ans` or `min`."
  A column called `mean` would be unreachable, because the function wins, so the
  refusal happens at the naming band.
- **The grid's own menus are real.** `Data ▸ Fill Down` is `menu 3 3` and asks
  for its arguments in a dialog pre-filled from the cursor; `Actions` carries
  Move Column, Resize, Select, Go To, Recalculate and Sort, of which Move
  Column, Recalculate and Sort act on the model.

---

## Why this exists

Porting a calculator's statistics suite is mostly a *naming* problem. The
formulas are in every textbook; the difficulty is that TI's names are specific,
inconsistent between pages of the same manual, and occasionally carry a
convention that no other tool uses. Getting `tTest` right matters much less than
getting `stat.SESlope` right, because the second one is what you copy into your
work.

So the fidelity claim here is split in two, and each half is verified by a
different mechanism:

| Claim | How it is verified |
| --- | --- |
| The **names** — functions, arguments, and every `stat.*` variable | Checked against the TI-Nspire Reference Guide's own tables, one function at a time, in `tests/test_tinspire_stats.py` |
| The **numbers** | Checked against SciPy / NumPy, independent implementations of the same closed forms, in `tools/checks_vs_scipy.py` |
| The **labels** on names that are *not* TI's | Every spelling that is not the primary one declares its standing and the evidence for it; `legacy.table()` prints them, and a test forbids an unlabelled entry |
| The **README you are reading** | Every `>>>` example in this file is executed by `tools/check_readme.py` |

```console
$ python -m pytest tests/            # 150 tests
150 passed

$ python tools/checks_vs_scipy.py    # needs numpy + scipy
passed 342   failed 0   iterative (informational) 3
all numeric checks agree with SciPy / NumPy

$ python tools/check_readme.py       # every example in this file
README: 10 blocks, 34 examples, 0 failed
```

---

## Contents

84 TI-Nspire catalog functions across the four menus that matter, plus the
`stat.` results group:

| Menu | Module | Functions |
| --- | --- | --- |
| `Statistics > List Math` | `listmath` | 20 — `mean`, `median`, `stDevSamp`, `SortA`, `frequency`, `countif`… |
| `Statistics > Stat Calculations` | `summary`, `regress` | 21 — `OneVar`, `TwoVar`, `LinRegMx`, `QuadReg`, `Logistic`, `MultReg`… |
| `Statistics > Distributions` | `distributions` | 26 — `normCdf`, `invNorm`, `tCdf`, `binomCdf`, `poissPdf`, `randSamp`… |
| `Statistics > Confidence Intervals` / `Stat Tests` | `inference` | 17 — `zInterval`, `tTest`, `ANOVA`, `χ²GOF`, `FTest_2Samp`… |

The full signature list is in `pretty_catalog()` (or `python -c
"import tinspire_stats as t; print(t.pretty_catalog())"`).
`examples/tour.py` walks through all of it as a printable session.

The group names above are the handheld's menu labels, not invented headings:
`tinspire_stats.menu` holds both application menus the `menu` key walks — the
Calculator page's `1 Actions … 8 Finance` and the Lists & Spreadsheet page's
`1 Actions … 6 Hints`, which is why the remembered path `4 1 1` is that page's
and not the Calculator's. `catalog.MENU` is generated from it, so the grouping
and the menu cannot drift apart, and `catalog.OFF_MENU` files the names with no
menu entry of their own (`randSamp` and friends live under **Probability**, and
`FiveNumSummary` is typed, not chosen).

---

## Behaviours that are intentional, not bugs

These are the places where the Nspire disagrees with a textbook, with Excel, or
with its own predecessor. Each one is reproduced deliberately.

### Quartiles: the Nspire includes the median in both halves

This is the single most common "my calculator is wrong" complaint about the
Nspire. For the five values `{1,2,3,4,5}` the two TI families disagree:

| | Q1 | Q3 |
| --- | --- | --- |
| **TI-Nspire** (Tukey hinges) | **2** | **4** |
| TI-83 / TI-84 (Moore & McCabe) | 1.5 | 4.5 |

TI's own activity *Five Figure Summary* states for `{1,…,9}` that `Q1 = 3` —
which is the inclusive answer — while the sentence that follows says the median
is *not* included. The IREM Lyon teaching notes describing what the calculator
actually displays settle it: *"Pour la calculatrice, Q1 est la médiane des
valeurs comprises entre minX et Med"* — median included, and the authors note it
disagrees with the French curriculum.

This package ships the **inclusive** rule, and lets you switch:

```python
>>> OneVar([1, 2, 3, 4, 5]).Q1X
2.0
>>> set_quartile_method("exclusive")     # AP Statistics answer keys, TI-84
'exclusive'
>>> OneVar([1, 2, 3, 4, 5]).Q1X
1.5
```

When `n` is even the two rules always agree, so this only ever bites on
odd-sized samples.

### `-9E999` is minus infinity

The calculator has no `∞` key in this context, so TI's own examples write
`normCdf(-9E999, 1.96)`. Python's `-inf` works too; both are accepted.

### `void` is a value, and it kills that index everywhere

An empty element in *any* input list makes that index void in *all* of them:

```python
>>> OneVar([1, 2, None, 4, 5]).n
4
```

`nan` is **not** void — TI keeps the two distinct, and so does this.

### `stDevSamp` demands integer frequencies, `mean` does not

Verified on hardware and reported on the TI forums: `mean(x, {.25,.25,.25,.25})`
works, while `stDevSamp(x, {.25,.25,.25,.25})` raises a *Domain error*. The
asymmetry is reproduced exactly.

### `z` procedures park the mean in `stat.x`, `t` procedures in `stat.v`

One of TI's own inconsistencies, preserved rather than tidied:

```python
>>> zInterval(2, [3, 4, 5, 6, 7], None, 0.95)   # mean lands in stat.x
StatGroup(CLower, CUpper, x, ME, sx, n, σ)
>>> tInterval([3, 4, 5, 6, 7], None, 0.95)      # mean lands in stat.v
StatGroup(CLower, CUpper, v, ME, df, σx, n)
```

### The siblings do not agree on what to call the sample standard deviation

This one looks like a typo in the guide and is not. Four of these functions
report the same quantity under two different names, and `zInterval` reports a
*second*, different quantity under a name one character away from `σx`:

| procedure | sample SD | mean | notes |
| --- | --- | --- | --- |
| `zInterval` | `stat.sx` | `stat.x` | also `stat.σ`, the known **population** σ the caller passed in |
| `zTest` | `stat.sx` | `stat.x` | `stat.sx` only for Data input; a Stats run leaves it undefined |
| `tInterval` | `stat.σx` | `stat.v` | |
| `tTest` | `stat.sx` | `stat.v` | |
| `tInterval_2Samp` | `stat.σx1`, `stat.σx2` | `stat.v1`, `stat.v2` | |
| `tTest_2Samp` | `stat.sx1`, `stat.sx2` | `stat.v1`, `stat.v2` | |

`stat.σ` at `zInterval` is the tell that these are deliberate: the same pages
write every other sigma variable as a Greek-entity span *followed by a literal*
`x` — `σx`, `σx1`, `σx2`, `σy`, eleven times over — and write the bare span with
nothing after it exactly once, here, next to `stat.sx` "Sample standard
deviation" and described as "Known population standard deviation". So the names
are published as printed, one per quantity: nothing is doubled up, and nothing
is quietly renamed to match its neighbour.

### Every family has a `Data` form and a `Stats` form

Told apart the way the wizard tells them apart — by whether the first argument
is a list:

```python
tInterval([3, 4, 5, 6, 7], None, 0.95)   # Data
tInterval(5.0, 1.581, 5, 0.95)           # Stats
```

### `frequency` returns one more bin than you gave it

The guide defines the bins as `{?≤b₁, b₁<?≤b₂, …, bₙ₋₁<?≤bₙ, bₙ>?}`: closed on
the right, with an unbounded bin at each end.

```python
>>> frequency([1, 2, 3, 4, 5], [2, 4])   # ≤2 | 2<x≤4 | >4
[2, 2, 1]
```

### `countif` / `sumIf` use `?` as the placeholder

```python
>>> data = [23, 25, 27, 29, 31, 33, 35]
>>> countif(data, "?>28")
4
>>> countif(data, "25≤?≤31")     # chained comparisons work
4
>>> countif(data, "?<26 or ?>32")
4
```

A bare relational shorthand (`">28"`) is also accepted, since that is the
obvious thing to type in Python. The guide's other form — "a value, expression,
or string" — works as equality, and strings really are counted.

---

## Name discrepancies, resolved explicitly

The reference guide is not internally consistent. Where two editions disagree,
**both spellings resolve** and the guide's printed form is what gets emitted.
The pairs live in `statvar.DUPLICATE_SPELLINGS`:

| Cause | Printed as | Resolves to |
| --- | --- | --- |
| Superscripts lost in the HTML tables | `stat.Σx2`, `stat.r2`, `stat.AdjR2`, `stat.chi2` | `stat.Σx²`, `stat.r²`, `stat.AdjR²`, `stat.χ²` |
| Two names for one variable | `stat.P Value`, `stat.ExpMat`, `stat.CompMat` | `stat.PVal`, `stat.ExpMatrix`, `stat.CompMatrix` |
| Edition drift | `stat.MedY`, `stat.Frow` | `stat.MedianY`, `stat.FRow` |

Those are *input* aliases: they let you type a name the guide prints badly. They
do not add anything to `stat.results`, which carries one name per quantity — see
the σ-table above for the case where that distinction matters most.

### Python identifier problems

Four TI names cannot be Python identifiers:

| Reference guide | Here |
| --- | --- |
| `χ²Pdf(` / `χ²Cdf(` | `χ2Pdf` / `χ2Cdf`, plus `chi2Pdf` / `chi2Cdf` |
| `invχ²(` | `invχ2`, plus `invChi2` |
| `χ²GOF` / `χ²2way` | `chi2GOF` / `chi22way` (and `χ2GOF` / `χ22way`) |
| `freqTable►list(` | `freqTable_to_list`, plus the guide's keyboard form `freqTable_at_list` |

Note that `chi2Pdf`, `chi2Cdf`, `invChi2`, `χ2GOF`, `χ22way` and `deltaList` are
not inventions of this package: the reference guide prints every one of them
itself. `lookup()` finds a function by *any* of these spellings — including the
ones in `legacy`:

```python
>>> lookup("freqTable►list") is freqTable_to_list
True
>>> lookup("χ²Pdf") is χ2Pdf
True
>>> lookup("stdev").__name__          # found, and not disguised
'stDevSamp'
```

---

## Fidelity table

| Function group | Fidelity | Note |
| --- | --- | --- |
| List math, `OneVar`, `TwoVar`, `FiveNumSummary` | Closed form | exact |
| Linear, polynomial, `LnReg`, `ExpReg`, `PowerReg`, `MedMed` | Closed form | least squares, exact |
| `MultReg`, `MultRegTests`, `MultRegIntervals`, `LinRegtTest`, `LinRegtIntervals` | Closed form | normal equations + Student-t |
| All continuous and discrete distributions | Closed form | regularised incomplete beta / gamma, Acklam + Newton |
| `z`/`t` intervals and tests, `FTest_2Samp`, 1-/2-proportion | Closed form | exact |
| `ANOVA`, `ANOVA2way`, `χ²GOF`, `χ²2way` | Closed form | exact |
| `Logistic`, `LogisticD`, `SinReg` | **Iterative** | Gauss–Newton with restarts. TI also only promises convergence here, so agreement is to ~3–4 significant figures rather than to the last digit. |

`Logistic`, `LogisticD` and `SinReg` are labelled `fidelity: "iterative"` in the
catalogue so the distinction is machine-readable, not just a sentence in a
README.

### Known deviations

* `SinReg` takes `Iterations` and an optional `Period`, matching the guide's
  `SinReg X,Y[,[Iterations],[Period][,Category,Include]]`; the initial guess is
  heuristic, as it is on the handheld.
* `ANOVA` with `Flag=1` (the *Stats* method) reads its three lists as
  `(means, standard deviations, sample sizes)` rather than unpacking the
  wizard's packed triplets — an explicit choice, documented in the docstring.
* `RegEqn`'s `str()` is a rendering convenience. The numbers are authoritative;
  the string matches the calculator's notation to ten significant digits.

---

## The non-TI names are quarantined

Nothing that is not a TI-Nspire name is reachable from the package root without
being declared. The spellings people borrow from other calculators, the words
the menus put on screen, and this package's own extensions all live in
`tinspire_stats.legacy`, each with a note explaining how it differs:

```python
>>> from tinspire_stats import legacy
>>> legacy.stdev.__name__        # which real function answers
'stDevSamp'
>>> legacy.kind_of("stdev")      # and why it is filed where it is
'not a TI-Nspire name'
>>> legacy.kind_of("chi2Pdf")    # this one really is TI's own spelling
'documented variant'
>>> len(legacy.NAMES)            # every non-TI name, each labelled
23
>>> legacy.table().splitlines()[0].startswith("alias")
True
```

Each entry carries the evidence for its label, so the table can be audited
rather than believed:

```python
>>> print(legacy.evidence("chi2Pdf"))
Reference guide, page C: the χ2Pdf entry prints both ‘χ2Pdf(XVal,df)’ and ‘chi2Pdf(XVal,df)’.
>>> print(legacy.evidence("stdev"))
Not printed anywhere in the TI-Nspire reference guide; verified by searching the guide's full function list.
```

### Five standings, not one bucket

The obvious design is one bucket called "aliases". It is wrong in both
directions, and this package shipped that mistake into its own first draft: it
filed `chi2Pdf` as a "TI-83/84 spelling" (the guide prints `chi2Pdf(XVal,df)` as
the second signature line of the χ²Pdf entry — it is TI's name, not an
impostor), and it left `Fpdf`, `PwrReg` and `invT` in a list with no label at
all. Any spelling that is not the primary one now has to declare exactly which of
five standings it has:

| Standing | Count | Examples | Where it stands |
| --- | --- | --- | --- |
| `documented variant` | 6 | `chi2Pdf`, `chi2Cdf`, `invChi2`, `χ2GOF`, `χ22way`, `deltaList` | The guide prints it. **Not** quarantined, and also exported at the root. |
| `keyboard spelling, not in the guide` | 7 | `invT`, `Fpdf`, `Fcdf`, `poissonPdf`, `poissonCdf`, `DeltaList`, `freqTable_at_list` | Guessable from the real name; the guide never prints it. |
| `not a TI-Nspire name` | 4 | `stdev`, `stdDev`, `variance`, `PwrReg` | The Nspire spells these `stDevSamp`, `stDevPop`, `varSamp`, `PowerReg`. |
| `TI-Nspire menu label, not the catalog name` | 10 | `TwoSampleTTest`, `OnePropZInt` | The menu shows "2-Sample t Test"; the catalog function is `tTest_2Samp`. |
| `package extension` | 2 | `SortA_inplace`, `SortD_inplace` | No TI counterpart at all. |

`legacy.counts()` returns that table, and `legacy.evidence(name)` returns the
page a claim was read off. A test checks that no name's label is left blank.

The root's own extra spellings are declared in `ROOT_ALIASES`, each with its
standing, and the declaration is checked against `legacy` — so a name cannot be
exported under one label and described under another.

`catalog()` classifies every public callable as `ti`, `legacy`, or `internal`,
so the distinction survives contact with tooling, and adds a `legacy_kind` field
carrying the precise standing:

```python
>>> row = next(r for r in catalog() if r["name"] == "stdev")
>>> row["kind"], row["legacy_kind"], row["signature"].split("(")[0]
('legacy', 'not a TI-Nspire name', '``stDevSamp')
```

---

## Layout

```
tinspire_stats/
  _core.py          TI error types, void handling, frequency rules, tiny linalg
  statvar.py        the `stat` group, RegEqn, CopyVar, spelling resolution
  listmath.py       Statistics > List Math
  summary.py        OneVar, TwoVar, FiveNumSummary (+ the quartile convention)
  regress.py        every regression and the multivariate models
  distributions.py  continuous + discrete distributions, rand*
  inference.py      intervals, hypothesis tests, ANOVA, chi-square
  catalog.py        name registry, ASCII twins, the generated function list
  menu.py           the handheld's menus and the paths that walk them -- the
                    two application layouts, the letter numbering, and what
                    each path lands on
  legacy.py         every name that is *not* TI-Nspire, with its standing and
                    the evidence for it -- the only place such names are defined
tests/              172 tests: name fidelity, the menu tree, quirks, pinned
                    values, doctests
tools/              checks_vs_scipy.py -- the numerical cross-check
                    check_readme.py -- runs every example in this file
examples/tour.py    a printable calculator session
web/                the browser version, drawn as the handheld (see "Use it in
                    the browser")
  engine.py         command parser: TI argument syntax, session, stat block
  index.template.html  the page itself -- front panel, light + dark, no framework
  la-bridge.js      Pyodide loader; the interpreter from ./runtime/ first
  fetch_runtime.py  downloads the interpreter into web/runtime/ (gitignored)
  build_preview.py  bundles the package + page + interpreter into web/dist/
```

## Running the checks

```console
$ python examples/tour.py                    # no dependencies at all
$ python -m pytest tests/                    # needs pytest
$ pip install numpy scipy
$ python tools/checks_vs_scipy.py            # 342 numeric cross-checks
$ python tools/check_readme.py               # this README's own examples
```

## Licence

MIT.

TI-Nspire and Texas Instruments are trademarks of Texas Instruments
Incorporated. This is an independent educational reimplementation and is not
affiliated with or endorsed by TI.
