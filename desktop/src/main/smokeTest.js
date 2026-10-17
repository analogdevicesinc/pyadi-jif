"use strict";

// Installed-app smoke test used by CI (scripts/smoke-test.mjs). When
// PYADI_JIF_SMOKE_RESULT names a file, the app waits for the Streamlit UI to
// actually render, writes {ok, detail} JSON to that file, and quits -
// instead of running interactively. Unset in normal use, so this is inert.

const { writeFileSync } = require("node:fs");
const { app } = require("electron");

const RESULT_PATH = process.env.PYADI_JIF_SMOKE_RESULT;
const UI_TIMEOUT_MS = 120_000;
const POLL_MS = 1_000;

// The explorer's sidebar title (adijif/tools/explorer/main.py) only appears
// once the Streamlit script has run; stException is Streamlit's rendered
// traceback element.
const PROBE = `(() => ({
  rendered: document.body.innerText.includes("Tools Explorer"),
  exceptions: Array.from(document.querySelectorAll('[data-testid="stException"]'))
    .map((e) => e.innerText.slice(0, 2000)),
}))()`;

function report(ok, detail) {
  writeFileSync(RESULT_PATH, JSON.stringify({ ok, detail }, null, 2));
  app.quit();
}

async function run(win) {
  const deadline = Date.now() + UI_TIMEOUT_MS;
  while (Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, POLL_MS));
    if (!win || win.isDestroyed()) return report(false, "window closed before UI rendered");
    let state;
    try {
      state = await win.webContents.executeJavaScript(PROBE);
    } catch {
      continue; // page still navigating
    }
    if (state.exceptions.length > 0) {
      return report(false, `Streamlit exception:\n${state.exceptions.join("\n---\n")}`);
    }
    if (state.rendered) {
      // Give the script a moment to finish its first run, then re-check
      // for exceptions raised further down the page.
      await new Promise((r) => setTimeout(r, 5_000));
      const final = await win.webContents.executeJavaScript(PROBE);
      if (final.exceptions.length > 0) {
        return report(false, `Streamlit exception:\n${final.exceptions.join("\n---\n")}`);
      }
      return report(true, `UI rendered at ${win.webContents.getURL()}`);
    }
  }
  report(false, `UI did not render within ${UI_TIMEOUT_MS / 1000}s`);
}

module.exports = { enabled: Boolean(RESULT_PATH), run, report };
