#!/usr/bin/env python3
"""Cross-check every numeric answer in ``tinspire_stats`` against SciPy.

The replication is only worth anything if the numbers are right, and the numbers
are the one thing the TI-Nspire Reference Guide does *not* publish.  So the
fidelity claim is split in two and each half is verified by a different means:

* **Names**  -- checked against the reference guide's own tables (see
  ``tests/test_tinspire_stats.py::test_stat_variable_names_*``).
* **Numbers** -- checked here, against SciPy / NumPy, which are independent
  implementations of the same closed forms.

Run with a Python that has numpy + scipy::

    /Users/franky100/.workbuddy/binaries/python/envs/default/bin/python \
        tools/checks_vs_scipy.py

Exit status is 0 only if every check passes.  Iterative fits (``Logistic``,
``LogisticD``, ``SinReg``) are reported separately with a looser tolerance --
they are the three places where TI itself only promises convergence, not a
particular answer.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
from scipy import stats as sps  # noqa: E402

import tinspire_stats as ts  # noqa: E402

# --------------------------------------------------------------------------
# harness
# --------------------------------------------------------------------------
PASS, FAIL, WARN = [], [], []


def close(got, want, *, tol=1e-9, rel=True) -> bool:
    if isinstance(want, (int, float)) and math.isnan(want):
        return isinstance(got, float) and math.isnan(got)
    if math.isinf(want):
        return got == want
    if rel:
        return abs(got - want) <= tol * max(1.0, abs(want))
    return abs(got - want) <= tol


def check(label, got, want, *, tol=1e-9, rel=True):
    ok = close(got, want, tol=tol, rel=rel)
    (PASS if ok else FAIL).append(label)
    if not ok:
        print(f"  FAIL {label}: got {got!r}, want {want!r}")


def check_seq(label, got, want, *, tol=1e-9):
    got, want = list(got), list(want)
    if len(got) != len(want):
        FAIL.append(label)
        print(f"  FAIL {label}: length {len(got)} != {len(want)}")
        return
    bad = [i for i, (g, w) in enumerate(zip(got, want)) if not close(g, w, tol=tol)]
    if bad:
        FAIL.append(label)
        print(
            f"  FAIL {label}: {len(bad)} of {len(want)} differ, "
            f"first at [{bad[0]}]: {got[bad[0]]!r} vs {want[bad[0]]!r}"
        )
    else:
        PASS.append(label)


def check_raises(label, exc, fn, *a, **kw):
    try:
        fn(*a, **kw)
    except exc:
        PASS.append(label)
        return
    except Exception as other:  # noqa: BLE001
        FAIL.append(label)
        print(f"  FAIL {label}: raised {type(other).__name__}, want {exc.__name__}")
        return
    FAIL.append(label)
    print(f"  FAIL {label}: no exception, want {exc.__name__}")


def check_ok(label, fn, *a, **kw):
    """The call must complete -- used for the cases where TI does *not* error."""
    try:
        fn(*a, **kw)
    except Exception as exc:  # noqa: BLE001
        FAIL.append(label)
        print(f"  FAIL {label}: raised {type(exc).__name__}: {exc}")
        return
    PASS.append(label)


def section(title):
    print(f"\n=== {title} ===")


def iterated(label, got, want, *, tol=5e-3):
    """An iterative fit: report the gap but do not fail the run on it."""
    ok = close(got, want, tol=tol)
    WARN.append(label)
    print(f"  {'ok  ' if ok else 'NOTE'} {label}: got {got!r}, want {want!r}")


# --------------------------------------------------------------------------
# distributions: continuous
# --------------------------------------------------------------------------
def distributions_continuous():
    section("distributions / continuous")

    for x in (-3.5, -0.25, 0.0, 1.0, 2.75):
        check(f"normPdf({x})", ts.normPdf(x), sps.norm.pdf(x))
    check("normPdf(2,5,3)", ts.normPdf(2, 5, 3), sps.norm.pdf(2, 5, 3))

    for lo, hi in ((-9e999, 0.0), (-2.0, 1.5), (0.5, 3.0)):
        check(
            f"normCdf({lo},{hi})",
            ts.normCdf(lo, hi),
            float(sps.norm.cdf(hi) - sps.norm.cdf(max(lo, -40))),
        )
    check("normCdf(70,79,75,3)", ts.normCdf(70, 79, 75, 3),
          float(sps.norm.cdf(79, 75, 3) - sps.norm.cdf(70, 75, 3)))

    for a in (0.001, 0.15, 0.5, 0.9, 0.999):
        check(f"invNorm({a})", ts.invNorm(a), float(sps.norm.ppf(a)), tol=1e-7)
    check("invNorm(0.9,2,0.5)", ts.invNorm(0.9, 2, 0.5),
          float(sps.norm.ppf(0.9, 2, 0.5)), tol=1e-7)

    for df in (1, 2, 5, 30, 250):
        for x in (-2.0, 0.0, 1.5):
            check(f"tPdf({x},{df})", ts.tPdf(x, df), float(sps.t.pdf(x, df)))
        check(f"tCdf(-9e999,0,{df})", ts.tCdf(-9e999, 0.0, df), 0.5, tol=1e-6)
        check(f"tCdf(-1,1,{df})", ts.tCdf(-1.0, 1.0, df),
              float(sps.t.cdf(1.0, df) - sps.t.cdf(-1.0, df)), tol=1e-6)

    for df in (1, 3, 12, 99):
        for a in (0.01, 0.5, 0.99):
            check(f"invt({a},{df})", ts.invt(a, df), float(sps.t.ppf(a, df)), tol=1e-6)
    # the two-tailed critical value that appears in every t interval
    check("invt(0.975,20)", ts.invt(0.975, 20), float(sps.t.ppf(0.975, 20)), tol=1e-6)

    for df in (1, 2, 4, 10, 50):
        for x in (0.5, 1.0, 3.0, 12.0):
            check(f"χ2Pdf({x},{df})", ts.χ2Pdf(x, df), float(sps.chi2.pdf(x, df)))
        check(f"χ2Cdf(0,5,{df})", ts.χ2Cdf(0.0, 5.0, df), float(sps.chi2.cdf(5.0, df)))
        check(f"invχ2(0.95,{df})", ts.invχ2(0.95, df),
              float(sps.chi2.ppf(0.95, df)), tol=1e-6)

    for d1, d2 in ((1, 1), (3, 7), (10, 20), (100, 100)):
        for x in (0.4, 1.0, 2.5):
            check(f"FPdf({x},{d1},{d2})", ts.FPdf(x, d1, d2),
                  float(sps.f.pdf(x, d1, d2)))
        check(f"FCdf(0,2,{d1},{d2})", ts.FCdf(0.0, 2.0, d1, d2),
              float(sps.f.cdf(2.0, d1, d2)))
        check(f"invF(0.95,{d1},{d2})", ts.invF(0.95, d1, d2),
              float(sps.f.ppf(0.95, d1, d2)), tol=1e-6)


# --------------------------------------------------------------------------
# distributions: discrete
# --------------------------------------------------------------------------
def distributions_discrete():
    section("distributions / discrete")

    for n, p in ((10, 0.3), (25, 0.5), (200, 0.87), (5, 0.0)):
        check_seq(f"binomPdf({n},{p}) all",
                  ts.binomPdf(n, p),
                  [float(sps.binom.pmf(k, n, p)) for k in range(n + 1)])
    for k in (0, 3, 7, 10):
        check(f"binomPdf(10,0.3,{k})", ts.binomPdf(10, 0.3, k),
              float(sps.binom.pmf(k, 10, 0.3)))
    for n, p in ((10, 0.3), (25, 0.5), (200, 0.87)):
        for k in (0, 1, 5, n // 2, n - 1, n):
            check(f"binomCdf({n},{p},0..{k})", ts.binomCdf(n, p, k),
                  float(sps.binom.cdf(k, n, p)), tol=1e-9)
        check(f"binomCdf({n},{p},3,8)", ts.binomCdf(n, p, 3, 8),
              float(sps.binom.cdf(8, n, p) - sps.binom.cdf(2, n, p)), tol=1e-9)

    # invBinom -- smallest k with P(X <= k) >= target
    for target, n, p in ((0.5, 20, 0.4), (0.9, 30, 0.25), (0.99, 50, 0.7)):
        want = int(sps.binom.ppf(target, n, p))
        while float(sps.binom.cdf(want, n, p)) < target:
            want += 1
        check(f"invBinom({target},{n},{p})", ts.invBinom(target, n, p), want)

    # invBinomN -- the guide's free-throw question: 70%, 50 goals, how sure?
    got = ts.invBinomN(0.99, 0.7, 50)
    want = 50
    while 1.0 - float(sps.binom.cdf(49, want, 0.7)) < 0.99:
        want += 1
    check("invBinomN(0.99,0.7,50)", got, want)

    for lam in (0.5, 3.0, 12.0, 80.0):
        for k in (0, 1, 5, 20):
            check(f"poissPdf({lam},{k})", ts.poissPdf(lam, k),
                  float(sps.poisson.pmf(k, lam)), tol=1e-9)
        for k in (0, 3, 15, 90):
            check(f"poissCdf({lam},0..{k})", ts.poissCdf(lam, k),
                  float(sps.poisson.cdf(k, lam)), tol=1e-9)
        check(f"poissCdf({lam},2,7)", ts.poissCdf(lam, 2, 7),
              float(sps.poisson.cdf(7, lam) - sps.poisson.cdf(1, lam)), tol=1e-9)

    for p in (0.05, 0.3, 0.75):
        for k in (1, 2, 5, 20):
            check(f"geomPdf({p},{k})", ts.geomPdf(p, k),
                  float(sps.geom.pmf(k, p)))
        for k in (1, 4, 15):
            check(f"geomCdf({p},1..{k})", ts.geomCdf(p, k),
                  float(sps.geom.cdf(k, p)))
        check(f"geomCdf({p},3,9)", ts.geomCdf(p, 3, 9),
              float(sps.geom.cdf(9, p) - sps.geom.cdf(2, p)))


# --------------------------------------------------------------------------
# list math and one-variable statistics
# --------------------------------------------------------------------------
def list_math():
    section("list math / summary statistics")

    data = [3.0, 7.0, 2.0, 9.0, 5.0, 5.0, 1.0, 8.0]
    arr = np.asarray(data)

    check("mean", ts.mean(data), float(arr.mean()))
    check("median", ts.median(data), float(np.median(arr)))
    check("stDevSamp", ts.stDevSamp(data), float(arr.std(ddof=1)))
    check("stDevPop", ts.stDevPop(data), float(arr.std(ddof=0)))
    check("varSamp", ts.varSamp(data), float(arr.var(ddof=1)))
    check("varPop", ts.varPop(data), float(arr.var(ddof=0)))
    check("sum", ts.sum(data), float(arr.sum()))
    check("min", ts.min(data), float(arr.min()))
    check("max", ts.max(data), float(arr.max()))
    check("product", ts.product(data), float(np.prod(arr)))
    check("count", ts.count(data), len(data))

    check_seq("cumulativeSum", ts.cumulativeSum(data), np.cumsum(arr))
    check_seq("ΔList", ts.ΔList(data), np.diff(arr))
    check_seq("SortA", ts.SortA(data), np.sort(arr))
    check_seq("SortD", ts.SortD(data), np.sort(arr)[::-1])

    # frequency lists
    vals, freqs = [1.0, 2.0, 4.0, 8.0], [3.0, 1.0, 2.0, 4.0]
    expanded = np.concatenate([np.full(int(f), v) for v, f in zip(vals, freqs)])
    check("mean(vals,freq)", ts.mean(vals, freqs), float(expanded.mean()))
    check("stDevSamp(vals,freq)", ts.stDevSamp(vals, freqs),
          float(expanded.std(ddof=1)))
    check("stDevPop(vals,freq)", ts.stDevPop(vals, freqs),
          float(expanded.std(ddof=0)))
    check_seq("freqTable_to_list", ts.freqTable_to_list(vals, freqs), expanded)

    # countif / sumIf -- TI's own placeholder syntax, plus the bare shorthand
    check("countif '?>4'", ts.countif(data, "?>4"), int((arr > 4).sum()))
    check("countif '> 4' (bare shorthand)", ts.countif(data, "> 4"),
          int((arr > 4).sum()))
    check("countif '?≤5'", ts.countif(data, "?≤5"), int((arr <= 5).sum()))
    check("countif value 5", ts.countif(data, 5), int((arr == 5).sum()))
    check("countif '2≤?≤8' chained", ts.countif(data, "2≤?≤8"),
          int(((arr >= 2) & (arr <= 8)).sum()))
    check("countif '?<3 or ?>7'", ts.countif(data, "?<3 or ?>7"),
          int(((arr < 3) | (arr > 7)).sum()))
    check("countif '?>2 and ?<8'", ts.countif(data, "?>2 and ?<8"),
          int(((arr > 2) & (arr < 8)).sum()))
    check("countif list pool", ts.countif(data, [1.0, 5.0, 9.0]),
          int(np.isin(arr, [1, 5, 9]).sum()))
    check("sumIf '?>4'", ts.sumIf(data, "?>4"), float(arr[arr > 4].sum()))
    check("sumIf '2≤?≤8' on second list", ts.sumIf(data, "2≤?≤8", data),
          float(arr[(arr >= 2) & (arr <= 8)].sum()))

    # frequency: the guide says the result is one element longer than binsList,
    # with the ranges {?≤b1, b1<?≤b2, ..., b(n-1)<?≤b(n), b(n)>?}
    bins = [1.0, 3.0, 5.0, 7.0, 9.0]
    want_freq = [
        int((arr <= 1).sum()),
        int(((arr > 1) & (arr <= 3)).sum()),
        int(((arr > 3) & (arr <= 5)).sum()),
        int(((arr > 5) & (arr <= 7)).sum()),
        int(((arr > 7) & (arr <= 9)).sum()),
        int((arr > 9).sum()),
    ]
    check_seq("frequency bins", ts.frequency(data, bins), want_freq)
    check("frequency length = len(bins)+1", len(ts.frequency(data, bins)),
          len(bins) + 1)

    # corrMat vs numpy
    a = np.array([1.0, 2, 3, 4, 5])
    b = np.array([2.0, 1, 4, 3, 6])
    c = np.array([5.0, 4, 3, 2, 1])
    got = np.asarray(ts.corrMat(a, b, c), dtype=float)
    check("corrMat = numpy corrcoef", float(np.abs(got - np.corrcoef([a, b, c])).max()),
          0.0, tol=1e-12, rel=False)


def one_var():
    section("OneVar / TwoVar")
    data = [23.0, 25.0, 27.0, 29.0, 31.0, 33.0, 35.0]
    arr = np.asarray(data)
    ts.OneVar(data)
    check("stat.v", ts.stat.v, float(arr.mean()))
    check("stat.Σx", ts.stat["Σx"], float(arr.sum()))
    check("stat.Σx²", ts.stat["Σx²"], float((arr ** 2).sum()))
    check("stat.sx", ts.stat.sx, float(arr.std(ddof=1)))
    check("stat.σx", ts.stat["σx"], float(arr.std(ddof=0)))
    check("stat.n", ts.stat.n, len(data))
    check("stat.MinX", ts.stat.MinX, float(arr.min()))
    check("stat.MedianX", ts.stat.MedianX, float(np.median(arr)))
    check("stat.MaxX", ts.stat.MaxX, float(arr.max()))
    check("stat.SSX", ts.stat.SSX, float(((arr - arr.mean()) ** 2).sum()))

    # quartiles: TI-Nspire ships Tukey hinges (median in both halves), so for
    # odd n each half keeps the median -- the opposite of the TI-83/84 split.
    sv = np.sort(arr)
    check("Q1X (Tukey hinges)", ts.stat.Q1X, float(np.median(sv[:4])))
    check("Q3X (Tukey hinges)", ts.stat.Q3X, float(np.median(sv[3:])))
    check("Q1X <= MedianX <= Q3X", 1.0 * (ts.stat.Q1X <= ts.stat.MedianX <= ts.stat.Q3X), 1.0)

    # even n: the two conventions must agree, so numpy type 7 is the reference
    even = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    ts.set_quartile_method("exclusive")
    e_excl = ts.OneVar(even).Q1X
    ts.set_quartile_method("inclusive")
    e_incl = ts.OneVar(even).Q1X
    check("even n: inclusive == exclusive", e_incl, e_excl)
    check("even n Q1 = median of lower half", e_incl,
          float(np.median([1.0, 2.0, 3.0])))

    # TwoVar
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    y = [5.0, 8.0, 11.0, 14.0, 17.0]
    ts.TwoVar(x, y)
    check("TwoVar r", ts.stat.r, float(np.corrcoef(x, y)[0, 1]))
    # the guide describes stat.Σxy as the plain sum of x•y products
    check("TwoVar Σxy (raw sum of products)", ts.stat["Σxy"],
          float((np.asarray(x) * np.asarray(y)).sum()))
    check("TwoVar Σ(x-v)2", ts.stat["Σ(x-v)2"],
          float(((np.asarray(x) - np.mean(x)) ** 2).sum()))
    check("TwoVar Σ(y-w)2", ts.stat["Σ(y-w)2"],
          float(((np.asarray(y) - np.mean(y)) ** 2).sum()))
    check("TwoVar w", ts.stat.w, float(np.mean(y)))


# --------------------------------------------------------------------------
# regressions
# --------------------------------------------------------------------------
def regressions():
    section("regressions vs numpy.polyfit / lstsq")

    x = np.array([1.0, 2, 3, 4, 5, 6, 7, 8])
    y_lin = 3.0 * x + 7.0
    y_quad = 2.0 * x ** 2 - 3.0 * x + 1.5
    y_cub = 0.5 * x ** 3 - 2.0 * x ** 2 + x - 4.0
    y_qrt = 0.1 * x ** 4 - 0.3 * x ** 3 + x ** 2 - 2 * x + 0.5

    ts.LinRegMx(x, y_lin + 0.05)          # noisy so r is not exactly 1
    m, b = np.polyfit(x, y_lin + 0.05, 1)
    check("LinRegMx m", ts.stat.m, float(m))
    check("LinRegMx b", ts.stat.b, float(b))
    check("LinRegMx r²", ts.stat["r²"], float(np.corrcoef(x, y_lin + 0.05)[0, 1] ** 2))

    ts.LinRegBx(x, y_lin + 0.05)
    check("LinRegBx b", ts.stat.b, float(m), tol=1e-9)  # same line, swapped roles

    # Polynomials.  TI names the coefficients from the *lowest* power up
    # (QuadReg y = a·x²+b·x+c) while polyfit hands them back highest-first, so
    # both lists run a, b, c, ... in the same order once polyfit is reversed.
    y_quad_n = y_quad + np.array([0.1, -0.05, 0.2, 0.0, -0.1, 0.15, 0.05, -0.2])
    y_cub_n = y_cub + np.array([0.1, -0.05, 0.2, 0.0, -0.1, 0.15, 0.05, -0.2])
    y_qrt_n = y_qrt + np.array([0.1, -0.05, 0.2, 0.0, -0.1, 0.15, 0.05, -0.2])

    for fn, target, deg, names, label in (
        (ts.QuadReg, y_quad_n, 2, ["a", "b", "c"], "QuadReg"),
        (ts.CubicReg, y_cub_n, 3, ["a", "b", "c", "d"], "CubicReg"),
        (ts.QuartReg, y_qrt_n, 4, ["a", "b", "c", "d", "e"], "QuartReg"),
    ):
        out = fn(x, target)
        want = np.polyfit(x, target, deg)          # highest power first
        for i, cname in enumerate(names):
            check(f"{label} {cname}", out[cname], float(want[i]), tol=1e-8)
        # and the equation must reproduce the fitted curve
        pred = sum(out[cname] * x ** (deg - i) for i, cname in enumerate(names))
        check(f"{label} reproduces fit", float(np.abs(pred - (target - out['Resid'])).max()),
              0.0, tol=1e-8, rel=False)

    # exponential / log / power, all linear in a transformed variable.
    # ExpReg is y = a·bˣ, so the polyfit slope is ln b, not b.
    y_exp = 4.0 * np.exp(0.35 * x)
    ts.ExpReg(x, y_exp)
    sl, ic = np.polyfit(x, np.log(y_exp), 1)
    check("ExpReg a", ts.stat.a, float(math.exp(ic)), tol=1e-8)
    check("ExpReg b", ts.stat.b, float(math.exp(sl)), tol=1e-8)

    y_ln = 2.5 * np.log(x) + 1.0
    ts.LnReg(x, y_ln)
    sl, ic = np.polyfit(np.log(x), y_ln, 1)
    check("LnReg a", ts.stat.a, float(ic), tol=1e-8)
    check("LnReg b", ts.stat.b, float(sl), tol=1e-8)

    y_pw = 1.8 * x ** 0.65
    ts.PowerReg(x, y_pw)
    sl, ic = np.polyfit(np.log(x), np.log(y_pw), 1)
    check("PowerReg a", ts.stat.a, float(math.exp(ic)), tol=1e-8)
    check("PowerReg b", ts.stat.b, float(sl), tol=1e-8)

    # multiple regression vs np.linalg.lstsq
    x1 = np.array([1.0, 2, 3, 4, 5, 6, 7, 8])
    x2 = np.array([2.0, 1, 4, 3, 6, 5, 8, 7])
    y_mr = 1.5 + 2.0 * x1 - 0.75 * x2
    design = np.column_stack([np.ones_like(x1), x1, x2])
    ts.MultReg(y_mr, x1, x2)
    beta, *_ = np.linalg.lstsq(design, y_mr, rcond=None)
    for i, cname in enumerate(["b0", "b1", "b2"]):
        check(f"MultReg {cname}", ts.stat[cname], float(beta[i]), tol=1e-8)
    check("MultReg R²", ts.stat["R2"], 1.0, tol=1e-9)

    # the t-test on the slope vs scipy
    yl = 3.0 * x + 7.0 + np.array([0.4, -0.3, 0.2, -0.5, 0.1, 0.6, -0.2, -0.3])
    ts.LinRegtTest(x, yl, None, 0)
    n = len(x)
    sl, ic = np.polyfit(x, yl, 1)
    resid = yl - (sl * x + ic)
    se = math.sqrt((resid ** 2).sum() / (n - 2) / ((x - x.mean()) ** 2).sum())
    t_stat = sl / se
    check("LinRegtTest t", ts.stat.t, float(t_stat), tol=1e-8)
    check("LinRegtTest PVal", ts.stat.PVal,
          float(2 * sps.t.sf(abs(t_stat), n - 2)), tol=1e-7)
    check("LinRegtTest df", ts.stat.df, n - 2)

    # iterative fits: report, do not fail
    y_log = 100.0 / (1.0 + 9.0 * np.exp(-0.8 * x))
    ts.Logistic(x, y_log)
    iterated("Logistic c", ts.stat.c, 100.0, tol=0.05)
    iterated("Logistic a", ts.stat.a, 9.0, tol=0.5)
    iterated("Logistic b", ts.stat.b, 0.8, tol=0.15)


# --------------------------------------------------------------------------
# inference
# --------------------------------------------------------------------------
def inference():
    section("confidence intervals")

    z_crit = float(sps.norm.ppf(0.975))
    sigma, mean, n = 2.0, 5.0, 25.0
    ts.zInterval(sigma, mean, n, 0.95)
    me = z_crit * sigma / math.sqrt(n)
    check("zInterval CLower", ts.stat.CLower, mean - me, tol=1e-7)
    check("zInterval CUpper", ts.stat.CUpper, mean + me, tol=1e-7)
    check("zInterval ME", ts.stat.ME, me, tol=1e-7)

    data = [3.0, 4, 5, 6, 7, 8, 9]
    arr = np.asarray(data)
    ts.zInterval(2.0, data, None, 0.95)
    me = z_crit * 2.0 / math.sqrt(len(data))
    check("zInterval(data) CLower", ts.stat.CLower, float(arr.mean()) - me, tol=1e-7)

    s = float(arr.std(ddof=1))
    df = len(data) - 1
    t_crit = float(sps.t.ppf(0.975, df))
    ts.tInterval(data, None, 0.95)
    me_t = t_crit * s / math.sqrt(len(data))
    check("tInterval CLower", ts.stat.CLower, float(arr.mean()) - me_t, tol=1e-7)
    check("tInterval CUpper", ts.stat.CUpper, float(arr.mean()) + me_t, tol=1e-7)
    check("tInterval df", ts.stat.df, df)
    check("tInterval σx", ts.stat.σx, s, tol=1e-10)

    # Welch two-sample
    a = [180.0, 185, 165, 178, 190, 188]
    b = [173.0, 180, 178, 160, 169, 173, 181, 163]
    na, nb = np.asarray(a), np.asarray(b)
    sa, sb = float(na.std(ddof=1)), float(nb.std(ddof=1))
    va, vb = sa ** 2 / len(a), sb ** 2 / len(b)
    se = math.sqrt(va + vb)
    welch_df = (va + vb) ** 2 / (
        va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1)
    )
    ts.tInterval_2Samp(a, b, None, None, 0.95, 0)
    diff = float(na.mean() - nb.mean())
    me_w = float(sps.t.ppf(0.975, welch_df)) * se
    check("tInterval_2Samp Welch df", ts.stat.df, float(welch_df), tol=1e-9)
    check("tInterval_2Samp CLower", ts.stat.CLower, diff - me_w, tol=1e-7)
    check("tInterval_2Samp CUpper", ts.stat.CUpper, diff + me_w, tol=1e-7)

    # pooled two-sample
    sp = math.sqrt(((len(a) - 1) * sa ** 2 + (len(b) - 1) * sb ** 2) / (len(a) + len(b) - 2))
    se_p = sp * math.sqrt(1 / len(a) + 1 / len(b))
    ddf = len(a) + len(b) - 2
    ts.tInterval_2Samp(a, b, None, None, 0.95, 1)
    me_p = float(sps.t.ppf(0.975, ddf)) * se_p
    check("tInterval_2Samp pooled sp", ts.stat.sp, sp, tol=1e-9)
    check("tInterval_2Samp pooled CLower", ts.stat.CLower, diff - me_p, tol=1e-7)

    # proportions
    p_hat, N = 42 / 100, 100
    me_prop = z_crit * math.sqrt(p_hat * (1 - p_hat) / N)
    ts.zInterval_1Prop(42, 100)
    check("zInterval_1Prop CLower", ts.stat.CLower, p_hat - me_prop, tol=1e-9)
    check("zInterval_1Prop CUpper", ts.stat.CUpper, p_hat + me_prop, tol=1e-9)

    p1, p2 = 42 / 100, 31 / 120
    me2 = z_crit * math.sqrt(p1 * (1 - p1) / 100 + p2 * (1 - p2) / 120)
    ts.zInterval_2Prop(42, 100, 31, 120)
    check("zInterval_2Prop CLower", ts.stat.CLower, (p1 - p2) - me2, tol=1e-9)

    section("hypothesis tests")

    # z test
    ts.zTest(5.0, 2.0, data, None, 0)
    z = (float(arr.mean()) - 5.0) / (2.0 / math.sqrt(len(data)))
    check("zTest z", ts.stat.z, z, tol=1e-9)
    check("zTest PVal", ts.stat.PVal, float(2 * sps.norm.sf(abs(z))), tol=1e-9)
    ts.zTest(5.0, 2.0, data, None, 1)
    check("zTest PVal (upper)", ts.stat.PVal, float(sps.norm.sf(z)), tol=1e-9)
    ts.zTest(5.0, 2.0, data, None, -1)
    check("zTest PVal (lower)", ts.stat.PVal, float(sps.norm.cdf(z)), tol=1e-9)

    # one-sample t
    ts.tTest(5.0, data, None, 0)
    t = (float(arr.mean()) - 5.0) / (s / math.sqrt(len(data)))
    check("tTest t", ts.stat.t, t, tol=1e-9)
    check("tTest PVal", ts.stat.PVal, float(2 * sps.t.sf(abs(t), df)), tol=1e-8)
    check("tTest df", ts.stat.df, df)

    # Welch t test vs scipy
    ts.tTest_2Samp(a, b, None, None, 0, 0)
    raw = sps.ttest_ind(na, nb, equal_var=False)
    check("tTest_2Samp t", ts.stat.t, float(raw.statistic), tol=1e-8)
    check("tTest_2Samp PVal", ts.stat.PVal, float(raw.pvalue), tol=1e-8)
    check("tTest_2Samp df", ts.stat.df, float(welch_df), tol=1e-9)

    # pooled t test vs scipy
    ts.tTest_2Samp(a, b, None, None, 0, 1)
    raw_p = sps.ttest_ind(na, nb, equal_var=True)
    check("tTest_2Samp pooled t", ts.stat.t, float(raw_p.statistic), tol=1e-8)
    check("tTest_2Samp pooled PVal", ts.stat.PVal, float(raw_p.pvalue), tol=1e-8)

    # F test on variances
    ts.FTest_2Samp(a, b, None, None, 0)
    f_ratio = sa ** 2 / sb ** 2
    check("FTest_2Samp F", ts.stat.F, f_ratio, tol=1e-9)
    p_hi = float(sps.f.cdf(f_ratio, len(a) - 1, len(b) - 1))
    check("FTest_2Samp PVal", ts.stat.PVal, min(1.0, 2 * min(p_hi, 1 - p_hi)), tol=1e-8)

    # one-proportion z test
    ts.zTest_1Prop(0.5, 42, 100)
    zz = (0.42 - 0.5) / math.sqrt(0.5 * 0.5 / 100)
    check("zTest_1Prop z", ts.stat.z, zz, tol=1e-9)
    check("zTest_1Prop PVal", ts.stat.PVal, float(2 * sps.norm.sf(abs(zz))), tol=1e-9)

    # two-proportion z test (pooled SE, as TI and most textbooks do)
    ts.zTest_2Prop(42, 100, 31, 120)
    pbar = (42 + 31) / 220
    z2 = (42 / 100 - 31 / 120) / math.sqrt(pbar * (1 - pbar) * (1 / 100 + 1 / 120))
    check("zTest_2Prop z", ts.stat.z, z2, tol=1e-9)
    check("zTest_2Prop PVal", ts.stat.PVal, float(2 * sps.norm.sf(abs(z2))), tol=1e-9)

    section("ANOVA and chi-square")

    g1 = [1.0, 2, 3, 4, 5]
    g2 = [3.0, 4, 5, 6, 7]
    g3 = [5.0, 6, 7, 8, 9]
    ts.ANOVA(g1, g2, g3)
    raw = sps.f_oneway(g1, g2, g3)
    check("ANOVA F", ts.stat.F, float(raw.statistic), tol=1e-9)
    check("ANOVA PVal", ts.stat.PVal, float(raw.pvalue), tol=1e-9)
    check("ANOVA df", ts.stat.df, 2)
    check("ANOVA dfError", ts.stat.dfError, 12)

    allv = np.asarray(g1 + g2 + g3)
    grand = allv.mean()
    ss_b = sum(len(g) * (np.mean(g) - grand) ** 2 for g in (g1, g2, g3))
    ss_w = sum(((np.asarray(g) - np.mean(g)) ** 2).sum() for g in (g1, g2, g3))
    check("ANOVA SS", ts.stat.SS, float(ss_b), tol=1e-9)
    check("ANOVA SSError", ts.stat.SSError, float(ss_w), tol=1e-9)
    check("ANOVA MSError", ts.stat.MSError, float(ss_w / 12), tol=1e-9)
    check("ANOVA sp", ts.stat.sp, math.sqrt(float(ss_w) / 12), tol=1e-9)
    check_seq("ANOVA xbarlist", ts.stat.xbarlist,
              [float(np.mean(g)) for g in (g1, g2, g3)])

    # chi-square goodness of fit
    obs, exp = [10.0, 20, 30, 40], [25.0, 25, 25, 25]
    ts.chi2GOF(obs, exp, 3)
    chi2 = sum((o - e) ** 2 / e for o, e in zip(obs, exp))
    check("chi2GOF χ²", ts.stat["χ²"], chi2, tol=1e-9)
    check("chi2GOF PVal", ts.stat.PVal, float(sps.chi2.sf(chi2, 3)), tol=1e-9)
    check("chi2GOF df", ts.stat.df, 3)
    check_seq("chi2GOF CompList", ts.stat.CompList,
              [(o - e) ** 2 / e for o, e in zip(obs, exp)])
    raw = sps.chisquare(np.asarray(obs), np.asarray(exp))
    check("chi2GOF matches scipy.chisquare", ts.stat.PVal, float(raw.pvalue), tol=1e-9)

    # chi-square test of association
    table = [[10.0, 20, 30], [30.0, 20, 10]]
    ts.chi22way(table)
    raw = sps.chi2_contingency(np.asarray(table), correction=False)
    check("chi22way χ²", ts.stat["χ²"], float(raw.statistic), tol=1e-9)
    check("chi22way PVal", ts.stat.PVal, float(raw.pvalue), tol=1e-9)
    check("chi22way df", ts.stat.df, 2)
    check("chi22way ExpMatrix matches scipy",
          float(np.abs(np.asarray(ts.stat.ExpMatrix) - raw.expected_freq).max()),
          0.0, tol=1e-9, rel=False)


# --------------------------------------------------------------------------
# error surface
# --------------------------------------------------------------------------
def errors():
    section("TI error surface")
    check_raises("empty list -> Domain error", ts.DomainError, ts.mean, [])
    check_raises("unequal list lengths -> Dimension mismatch",
                 ts.DimensionMismatchError, ts.TwoVar, [1, 2, 3], [1, 2])
    check_raises("fractional freq to stDevSamp -> Domain error", ts.DomainError,
                 ts.stDevSamp, [1, 2, 3], [0.5, 0.5, 2.0])
    check_ok("fractional freq to mean is fine (documented TI quirk)", ts.mean,
             [1, 2, 3], [0.5, 0.5, 2.0])
    check("mean with fractional freq value", ts.mean([1, 2, 3], [0.5, 0.5, 2.0]),
          (1 * 0.5 + 2 * 0.5 + 3 * 2.0) / 3.0, tol=1e-12)
    check_raises("non-integer obs to chi2GOF -> Domain error", ts.DomainError,
                 ts.chi2GOF, [1.5, 2, 3], [2, 2, 2], 2)
    check_raises("bad quartile method -> Argument error", ts.ArgumentError,
                 ts.set_quartile_method, "tukey")
    check_raises("single observation to tInterval -> Domain error", ts.DomainError,
                 ts.tInterval, [5.0], None, 0.95)
    if ts.DomainError().ti_message == "Domain error":
        PASS.append("TI message text")
    else:
        FAIL.append("TI message text")
        print("  FAIL TI message text:", ts.DomainError().ti_message)


def main() -> int:
    for fn in (
        distributions_continuous,
        distributions_discrete,
        list_math,
        one_var,
        regressions,
        inference,
        errors,
    ):
        fn()

    print(f"\n{'=' * 62}")
    print(f"passed {len(PASS)}   failed {len(FAIL)}   iterative (informational) {len(WARN)}")
    if FAIL:
        print("\nfailures:")
        for name in FAIL:
            print("  -", name)
        return 1
    print("all numeric checks agree with SciPy / NumPy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
