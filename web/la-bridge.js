"use strict";
/*
 * Pyodide bridge for the TI-Nspire statistics page.
 *
 *   index.html  ->  core_bundle.js    sets window.LA_CORE_FILES = {path: source}
 *               ->  la-bridge.js      (this file) boots Pyodide, writes those
 *                                     files into the virtual FS, imports the
 *                                     entry module and exposes LA.dispatch().
 *
 * The whole Python package is pure standard library, so nothing has to be
 * installed at runtime -- no micropip, no sympy.  Boot is one wasm download.
 *
 *
 * WHERE THE RUNTIME COMES FROM
 * ----------------------------
 * "./runtime/" first, and that is not a preference -- it is the fix for a real
 * failure.  The first version of this page fetched the interpreter from a
 * public CDN, which is fine from a fast connection and useless from a throttled
 * one: mainland China resets or stalls those endpoints, so the page drew its
 * entire interface and then sat on "Loading the Python runtime" forever, with
 * nothing wrong on our own server.  Shipping the runtime as part of the site
 * means one origin, one connection, and no third party that can be blocked
 * independently of the page itself.
 *
 * The CDN list is kept as a fallback for one case only: someone who clones the
 * repository and serves web/ without running fetch_runtime.py.  If ./runtime/
 * answers, no third party is ever contacted.
 */
window.LA = { ready: false, error: null, dispatch: null, origin: null, loadMs: null };

(function () {
  const PYODIDE_VERSION = "v0.26.2";

  //: Where the interpreter is looked for, in order.  entries are
  //: [indexURL, label]; the label is what the status line calls it.
  const SOURCES = [
    ["./runtime/", "this site"],
    ["https://fastly.jsdelivr.net/pyodide/" + PYODIDE_VERSION + "/full/", "fastly.jsdelivr.net"],
    ["https://cdn.jsdelivr.net/pyodide/" + PYODIDE_VERSION + "/full/", "cdn.jsdelivr.net"],
    ["https://unpkg.com/pyodide@" + PYODIDE_VERSION + "/", "unpkg.com"],
  ];

  const statusEl = function () { return document.getElementById("engineStatus"); };
  const note = function (text) { const el = statusEl(); if (el) el.textContent = text; };
  const noteHTML = function (html) { const el = statusEl(); if (el) el.innerHTML = html; };

  function injectScript(src) {
    return new Promise(function (resolve, reject) {
      const s = document.createElement("script");
      s.src = src;
      s.async = true;
      s.onload = function () { resolve(src); };
      s.onerror = function () { reject(new Error("failed to load " + src)); };
      document.head.appendChild(s);
    });
  }

  async function loadRuntime() {
    const failures = [];
    const started = Date.now();
    const tick = setInterval(function () {
      const s = Math.round((Date.now() - started) / 1000);
      note("Loading Python \u2014 " + s + "s. One download; the browser keeps it.");
    }, 1000);
    try {
      for (let i = 0; i < SOURCES.length; i++) {
        const indexURL = SOURCES[i][0];
        const label = SOURCES[i][1];
        try {
          note(label === "this site"
            ? "Loading the Python runtime from this site \u2026"
            : "Loading Python from " + label + " \u2026");
          await injectScript(indexURL + "pyodide.js");
          // A static host that does not have runtime/ answers with an HTML 404
          // page, and a <script> tag pointed at HTML still fires onload.  So the
          // real test is whether the loader appeared, not whether the tag loaded.
          if (typeof window.loadPyodide !== "function") {
            throw new Error("pyodide.js did not define loadPyodide");
          }
          const pyodide = await window.loadPyodide({ indexURL: indexURL });
          window.LA.origin = label;
          return pyodide;
        } catch (err) {
          failures.push(label + ": " + err.message);
          delete window.loadPyodide;
        }
      }
      throw new Error(failures.join(" | "));
    } finally {
      clearInterval(tick);
    }
  }

  function writeFiles(pyodide) {
    const files = window.LA_CORE_FILES || {};
    const FS = pyodide.FS;
    try { FS.mkdir("/la"); } catch (e) { /* already there */ }
    const names = Object.keys(files);
    for (let i = 0; i < names.length; i++) {
      const name = names[i];
      const dir = "/la/" + name.replace(/[^/]*$/, "");
      try { FS.mkdirTree(dir); } catch (e) { /* already there */ }
      FS.writeFile("/la/" + name, files[name]);
    }
    return names.length;
  }

  async function boot() {
    const started = Date.now();
    try {
      const pyodide = await loadRuntime();
      window.__pyodide = pyodide;

      note("Installing the calculator package \u2026");
      const count = writeFiles(pyodide);
      const entryModule = (function () {
        const meta = document.querySelector('meta[name="la-entry-module"]');
        return meta ? meta.content : "engine";
      })();

      // Keep a handle on the entry module: the dispatch function lives on it,
      // not in the interpreter's global namespace.
      window.__laEntry = pyodide.runPython(
        "import sys\n" +
        "if '/la' not in sys.path:\n" +
        "    sys.path.insert(0, '/la')\n" +
        "import " + entryModule + "\n" +
        entryModule + "\n"
      );

      window.LA.ready = true;
      window.LA.loadMs = Date.now() - started;
      noteHTML(
        "Ready \u00b7 " + count + " Python files \u00b7 Pyodide " + PYODIDE_VERSION +
        " from " + window.LA.origin + " \u00b7 " + (window.LA.loadMs / 1000).toFixed(1) + "s"
      );
      document.body.classList.add("engine-ready");
    } catch (err) {
      window.LA.error = String(err && err.message ? err.message : err);
      noteHTML("Engine failed to load \u2014 reload the page. (" + window.LA.error + ")");
      document.body.classList.add("engine-failed");
    }
  }

  window.LA.dispatch = function (payload) {
    if (!window.LA.ready) throw new Error("The Python engine is still starting.");
    return JSON.parse(window.__laEntry._la_dispatch_json(JSON.stringify(payload)));
  };

  window.LA.readyPromise = (document.readyState === "loading")
    ? new Promise(function (r) { document.addEventListener("DOMContentLoaded", function () { boot().then(r); }); })
    : boot();
})();
