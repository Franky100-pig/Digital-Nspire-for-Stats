"""Run every ``>>>`` example in README.md, so the docs cannot rot.

A README full of plausible-looking but unchecked examples is worse than no
README: it is a set of claims that *look* verified.  This extracts each fenced
``python`` block, feeds it to doctest, and fails if anything disagrees.

Run it::

    /Users/franky100/.workbuddy/binaries/python/envs/default/bin/python \
        tools/check_readme.py
"""

from __future__ import annotations

import doctest
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

README = ROOT / "README.md"

# Blocks that are illustrative rather than executable (a session counter, a
# shell prompt) are labelled in the file with this marker.
SKIP_MARKER = "<!-- doctest: skip -->"

#: Names the README uses in its examples.  Executed into the namespace handed to
#: doctest, so the snippets can stay short without being wrong.  (Putting these
#: lines in the text instead would not work: doctest ignores anything that is
#: not ``>>>``-prefixed.)
PREAMBLE = """
from tinspire_stats import (
    OneVar, TwoVar, LinRegMx, LinRegBx, tInterval, tTest, zInterval,
    frequency, countif, sumIf, stat, set_quartile_method, lookup,
    freqTable_to_list, copy_to_stat_group, catalog,
)
from tinspire_stats import χ2Pdf, legacy
import tinspire_stats
"""


def base_namespace() -> dict:
    namespace: dict = {}
    exec(PREAMBLE, namespace)
    return namespace


def python_blocks(text: str):
    """Every ```python ... ``` fence that contains a doctest."""
    for match in re.finditer(r"```python\n(.*?)```", text, re.DOTALL):
        block = match.group(1)
        if ">>>" not in block:
            continue
        if block.lstrip().startswith(SKIP_MARKER):
            continue
        yield block


def main() -> int:
    text = README.read_text(encoding="utf-8")
    parser = doctest.DocTestParser()
    runner = doctest.DocTestRunner(
        optionflags=doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE,
        verbose=False,
    )
    total_attempted = total_failed = blocks = 0

    for i, block in enumerate(python_blocks(text), start=1):
        blocks += 1
        # A fresh copy of the namespace per block, so one block cannot leak
        # state (or the quartile setting) into the next.
        globs = base_namespace()
        test = parser.get_doctest(block, globs, f"README block {i}", "README.md", 0)
        # Collect into a buffer rather than writing straight to sys.stdout:
        # doctest rebinds sys.stdout while the examples run, so a
        # ``lambda s: sys.stdout.write(s)`` would send the reports into the
        # fake capture stream and we would never see them.
        reports: list[str] = []
        result = runner.run(test, out=reports.append)
        if result.failed:
            sys.stdout.write("".join(reports))
        total_attempted += result.attempted
        total_failed += result.failed

    print("=" * 62)
    print(f"README: {blocks} blocks, {total_attempted} examples, {total_failed} failed")
    return 1 if total_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
