"""Where the tests find the browser engine.

``web/`` is not a package.  The bundler copies ``engine.py`` into the root of
Pyodide's virtual filesystem alongside the ``tinspire_stats`` package, and in
there it is an ordinary top-level module -- so the tests import it the same way
the browser does, rather than inventing a package layout the shipped code does
not have.
"""

from __future__ import annotations

import sys
from pathlib import Path

_WEB = Path(__file__).resolve().parent.parent / "web"
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
