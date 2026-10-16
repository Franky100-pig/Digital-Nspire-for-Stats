"""A guided tour through ``tinspire_stats``, written as a calculator session.

Every call here is the same call you would type on a TI-Nspire, including the
function names, the argument order, the ``stat.`` result names and the way the
results are read back.  Run it::

    python examples/tour.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tinspire_stats as ts  # noqa: E402
from tinspire_stats import stat  # noqa: E402


def banner(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def show() -> None:
    print(stat.results)


# --------------------------------------------------------------------------
banner("1. Stat Calculations > One-Variable Statistics  ->  OneVar")
# Name the list, request OneVar, read the results off stat.
data = [23, 25, 27, 29, 31, 33, 35]
ts.OneVar(data)
show()
print()
print("the mean, read the way you read it on the handheld:")
print("   stat.v            =", stat.v)
print("   stat.σx           =", stat["σx"])
print("   stat.Q1X          =", stat.Q1X, " (median-inclusive, the Nspire rule)")
print("   stat['Σx²']        =", stat["Σx²"])


# --------------------------------------------------------------------------
banner("2. The quartile question: Nspire vs TI-84")
for label, method in (("TI-Nspire (default)", "inclusive"), ("TI-83/84", "exclusive")):
    ts.set_quartile_method(method)
    r = ts.OneVar([1, 2, 3, 4, 5])
    print(f"   {label:22} Q1 = {r.Q1X:<4} Q3 = {r.Q3X}")
ts.set_quartile_method("inclusive")
print()
print("   Same numbers, two defensible conventions. This package ships the")
print("   Nspire one; switch with set_quartile_method('exclusive').")


# --------------------------------------------------------------------------
banner("3. Regressions  ->  LinRegMx, and the equation as a function")
x = [1, 2, 3, 4, 5]
y = [5, 8, 11, 14, 17]
ts.LinRegMx(x, y)
show()
print()
print("   stat.RegEqn is the fitted line, and it is callable:")
print("       stat.RegEqn(6)      =", stat.RegEqn(6))
print("       str(stat.RegEqn)    =", str(stat.RegEqn))
print("       stat.RegEqn.symbolic=", stat.RegEqn.symbolic)


# --------------------------------------------------------------------------
banner("4. Distributions  ->  normCdf, invNorm, tCdf, binomCdf")
print("   normCdf(-9E999, 1.96)  =", ts.normCdf(-9e999, 1.96))
print("   invNorm(0.975)         =", ts.invNorm(0.975))
print("   tCdf(-9E999, 2.086, 20)=", ts.tCdf(-9e999, 2.086, 20))
print("   binomCdf(10, 0.4, 3)   =", ts.binomCdf(10, 0.4, 3))
print()
print("   Note -9E999: on the calculator that literal *is* minus infinity,")
print("   and it works here too.")


# --------------------------------------------------------------------------
banner("5. Confidence Intervals  ->  tInterval (Data form and Stats form)")
sample = [180, 185, 165, 178, 190, 188]
ts.tInterval(sample, None, 0.95)
print("Data form: tInterval(List, Freq, CLevel)")
show()
lo, hi, mean, s, n = stat.CLower, stat.CUpper, stat.v, stat.σx, stat.n

ts.tInterval(mean, s, n, 0.95)
print()
print("Stats form: tInterval(v, sx, n, CLevel) -- identical answer.")
print("The argument is sx; the result is stat.σx.  That asymmetry is TI's.")
show()


# --------------------------------------------------------------------------
banner("6. Stat Tests  ->  tTest_2Samp, pooled and Welch")
a = [180, 185, 165, 178, 190, 188]
b = [173, 180, 178, 160, 169, 173, 181, 163]
ts.tTest_2Samp(a, b, None, None, 0, 0)
print("Welch (Pooled=0, the default) -- note the fractional stat.df:")
show()
ts.tTest_2Samp(a, b, None, None, 0, 1)
print()
print("Pooled (Pooled=1) -- now stat.sp is published too:")
show()


# --------------------------------------------------------------------------
banner("7. ANOVA, χ² and the tests you reach for in a stats course")
ts.ANOVA([1, 2, 3, 4, 5], [3, 4, 5, 6, 7], [5, 6, 7, 8, 9])
print("ANOVA -- a one-way layout of three groups:")
show()

ts.chi2GOF([10, 20, 30, 40], [25, 25, 25, 25], 3)
print()
print("χ²GOF -- goodness of fit:")
show()


# --------------------------------------------------------------------------
banner("8. List Math  ->  criteria, sorting and summaries")
print("   mean                 =", ts.mean(data))
print("   stDevSamp            =", ts.stDevSamp(data))
print("   SortD                =", ts.SortD(data))
print("   ΔList                =", ts.ΔList(data))
print("   cumulativeSum        =", ts.cumulativeSum(data))
print()
print("   countif / sumIf use TI's '?' placeholder:")
print("       countif(data, '?>28')      =", ts.countif(data, "?>28"))
print("       countif(data, '25≤?≤31')   =", ts.countif(data, "25≤?≤31"))
print("       sumIf(data, '?>28')        =", ts.sumIf(data, "?>28"))


# --------------------------------------------------------------------------
banner("9. void -- the calculator's empty element")
rows = [1, 2, None, 4, 5]
print("   list with a void in the middle:", rows)
ts.OneVar(rows)
print("   OneVar drops that index from every input list:")
print("       stat.n  =", stat.n, " (five entries, four usable)")
print("       stat.v  =", stat.v)


# --------------------------------------------------------------------------
banner("10. CopyVar and the saved stat groups")
ts.OneVar(data)
ts.CopyVar(stat.v, "myMean")
print("   CopyVar stat.v,myMean  ->  VarStore['myMean'] =", ts.VarStore["myMean"])
saved = ts.copy_to_stat_group()
ts.LinRegMx(x, y)
print("   copy_to_stat_group() kept the earlier result:")
print("       saved.Q1X =", saved.Q1X, " while stat.m =", stat.m)


# --------------------------------------------------------------------------
banner("11. Discovery -- what else is in here")
print("   This package replicates", sum(1 for r in ts.catalog() if r["kind"] == "ti"),
      "TI-Nspire catalog functions.")
print("   Look one up by any of its spellings -- including the ones TI does not use:")
for spelling in ("OneVar", "freqTable►list", "χ²Pdf", "invChi2", "stdev"):
    fn = ts.lookup(spelling)
    print(f"       lookup({spelling!r:22}) -> {fn.__module__.split('.')[-1]}.{fn.__name__}")
print()
print("   Every spelling that is not the primary one has to say which it is:")
for standing, n in ts.legacy.counts().items():
    print(f"       {n:2d}  {standing}")
print()
print("   Where each of those spellings stands:")
for alias in ("stdev", "invT", "chi2Pdf"):
    print(f"       legacy.{alias:<10} -> {ts.legacy.kind_of(alias)}")
print("   ...and the reason is recorded next to the name, not asserted:")
print("      ", ts.legacy.evidence("stdev"))
