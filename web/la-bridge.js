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
 * Three CDNs are tried in order.  fastly.jsdelivr.net is first because it is the
 * one that consistently answers from mainland China.
 */
window.LA = { ready: false, error: null, dispatch: null, cdn: null, loadMs: null };

(function () {
  const PYODIDE_VERSION = "v0.26.2";
  const CDNS = [
    "https://fastly.jsdelivr.net/pyodide/",
    "https://cdn.jsdelivr.net/pyodide/",
    "https://unpkg.com/pyodide@",
  ].map(function (base) { return base + PYODIDE_VERSION + "/full/"; });

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
    const t0 = Date.now();
    const tick = setInterval(function () {
      const s = Math.round((Date.now() - t0) / 1000);
      note("Downloading the Python runtime (~11 MB) \u2014 " + s +
           "s so far. First visit only; your browser caches it.");
    }, 1000);
    try {
      for (let i = 0; i < CDNS.length; i++) {
        const indexURL = CDNS[i];
        try {
          note("Loading Python runtime from " + new URL(indexURL).host + " \u2026");
          await injectScript(indexURL + "pyodide.js");
          if (typeof window.loadPyodide !== "function") {
            throw new Error("pyodide.js did not define loadPyodide");
          }
          const pyodide = await window.loadPyodide({ indexURL: indexURL });
          window.LA.cdn = new URL(indexURL).host;
          return pyodide;
        } catch (err) {
          failures.push(new URL(indexURL).host + ": " + err.message);
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
        "Engine ready \u00b7 " + count + " Python files \u00b7 " +
        "Pyodide " + PYODIDE_VERSION + " via " + window.LA.cdn +
        " \u00b7 " + (window.LA.loadMs / 1000).toFixed(1) + "s"
      );
      document.body.classList.add("engine-ready");
    } catch (err) {
      window.LA.error = String(err && err.message ? err.message : err);
      noteHTML("Engine failed to load \u2014 check your connection, then reload. (" +
               window.LA.error + ")");
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
