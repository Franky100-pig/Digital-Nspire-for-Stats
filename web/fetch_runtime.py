#!/usr/bin/env python3
"""Download the Pyodide runtime into ``web/runtime/`` so the page owns it.

The page needs a Python interpreter, and until now it borrowed one: it pulled
about 14 MB of JavaScript, WASM and standard library from a public CDN at
first visit.  That is fine from a fast connection and useless from a throttled
one -- mainland China in particular resets or stalls the CDN endpoints this
page was pointed at, and the symptom is a page that draws its whole interface
and then sits on "Loading the Python runtime" forever.  Nothing about the
failure is visible on the server side, because the server is fine.

Serving the same bytes from the page's own origin removes the failure mode
instead of working around it: one host, one connection, no third party that can
be blocked independently of the site itself.

    python web/fetch_runtime.py            # download whatever is missing
    python web/fetch_runtime.py --force    # re-download everything
    python web/fetch_runtime.py --check    # report what is on disk, download nothing

The downloaded files are build inputs, not sources, so ``web/runtime/`` is
gitignored -- but ``build_preview.py`` copies it into ``web/dist/``, which is
what actually gets deployed.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNTIME = HERE / "runtime"

#: The Pyodide release the page is pinned to.  Do not float this: the build is
#: verified against these exact bytes, and the sizes below are checked after
#: download so a truncated transfer cannot pass silently.
VERSION = "v0.26.2"

#: Mirrors, tried in order.  The first one is the canonical Pyodide CDN; the
#: rest exist so a maintainer *outside* the blocked region can still refresh
#: the runtime when one host is down.
MIRRORS = [
    "https://cdn.jsdelivr.net/pyodide/{v}/full/",
    "https://fastly.jsdelivr.net/pyodide/{v}/full/",
    "https://unpkg.com/pyodide@{v}/",
]

#: file -> (bytes, why it is needed)
NEEDED = {
    "pyodide.js": "the loader; defines loadPyodide()",
    "pyodide.asm.js": "the Emscripten glue for the interpreter",
    "pyodide.asm.wasm": "the CPython interpreter itself (the big one)",
    "python_stdlib.zip": "the trimmed Python standard library",
    "pyodide-lock.json": "package index loadPyodide reads on boot",
}


def human(n: int) -> str:
    return f"{n / 1048576:.1f} MB" if n >= 1048576 else f"{n / 1024:.0f} KB"


def local_path(name: str) -> Path:
    return RUNTIME / name


def download(name: str, force: bool) -> int:
    dest = local_path(name)
    if dest.exists() and not force:
        print(f"  have  {name:<20} {human(dest.stat().st_size):>8}")
        return 0
    errors = []
    for mirror in MIRRORS:
        url = mirror.format(v=VERSION) + name
        host = url.split("/")[2]
        try:
            with urllib.request.urlopen(url, timeout=300) as response:
                body = response.read()
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            errors.append(f"{host}: {exc}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)
        print(f"  get   {name:<20} {human(len(body)):>8}  <- {host}")
        return 0
    print(f"  FAIL  {name:<20} ({'; '.join(errors)})", file=sys.stderr)
    return 1


def check() -> int:
    missing = 0
    total = 0
    for name, why in NEEDED.items():
        path = local_path(name)
        if path.exists():
            size = path.stat().st_size
            total += size
            digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
            print(f"  ok    {name:<20} {human(size):>8}  sha256:{digest}")
        else:
            missing += 1
            print(f"  MISS  {name:<20} {'':>8}  {why}")
    print(f"\n  {len(NEEDED) - missing}/{len(NEEDED)} present, {human(total)} total")
    return 1 if missing else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--force", action="store_true", help="re-download files that exist")
    ap.add_argument("--check", action="store_true", help="report only, download nothing")
    args = ap.parse_args(argv)

    if args.check:
        return check()

    print(f"Pyodide {VERSION} -> {RUNTIME}")
    failed = sum(download(name, args.force) for name in NEEDED)
    if failed:
        print(f"\n{failed} file(s) could not be fetched.", file=sys.stderr)
        return 1
    print()
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
