"use strict";

const net = require("node:net");
const path = require("node:path");
const { readFileSync } = require("node:fs");
const { spawn, spawnSync } = require("node:child_process");
const { app } = require("electron");
const { pythonBin, wheelsDir } = require("./paths");

const HEALTH_ENDPOINTS = ["/_stcore/health", "/healthz"];
const HEALTH_TIMEOUT_MS = 60_000;
const HEALTH_POLL_INTERVAL_MS = 500;

// -s (disable user site) and -E (ignore inherited PYTHON* env vars) keep
// the bundled interpreter isolated from whatever Python setup happens to
// exist on the host - verified empirically that without this, pip/import
// can silently pick up same-version packages from the invoking account's
// user site-packages instead of using the bundled, self-contained copy.
const ISOLATION_FLAGS = ["-E", "-s"];

let child = null;
let currentPort = null;

function getFreePort() {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.on("error", reject);
    srv.listen(0, "127.0.0.1", () => {
      const { port } = srv.address();
      srv.close(() => resolve(port));
    });
  });
}

async function waitForHealth(port, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    for (const endpoint of HEALTH_ENDPOINTS) {
      try {
        const res = await fetch(`http://127.0.0.1:${port}${endpoint}`);
        if (res.ok) return;
      } catch {
        // Server not accepting connections yet - keep polling.
      }
    }
    await new Promise((r) => setTimeout(r, HEALTH_POLL_INTERVAL_MS));
  }
  throw new Error(
    "Streamlit did not become healthy in time. The bundled Python " +
      "environment may be missing pyadi-jif (installer's pip step may " +
      "have failed) - see stderr output above."
  );
}

function readPinnedRequirements() {
  const configPath = path.join(app.getAppPath(), "config", "pyadi-jif.json");
  const { version, extras, extraPackages = [] } = JSON.parse(readFileSync(configPath, "utf8"));
  return [`pyadi-jif[${extras}]==${version}`, ...extraPackages];
}

// Installer scripts (NSIS customInstall / macOS postinstall / deb-rpm
// postinst) deliberately exit 0 even if their pip step failed, so a broken
// install looks identical to a healthy one until the app actually tries to
// run - see build/installer/templates/*.tmpl. This is the other half of
// that contract: every start() call self-heals by checking whether adijif
// actually imports, and if not, re-running the same offline pip install
// the installer was supposed to have done. This is also what the error
// screen's Retry button ultimately triggers (via start()), so retry can
// only succeed if this repair step exists.
function ensureAdijifInstalled() {
  const bin = pythonBin();
  const check = spawnSync(bin, [...ISOLATION_FLAGS, "-c", "import adijif"]);
  if (check.status === 0) return;

  const requirements = readPinnedRequirements();
  const result = spawnSync(
    bin,
    [
      ...ISOLATION_FLAGS,
      "-m",
      "pip",
      "install",
      "--no-index",
      "--find-links",
      wheelsDir(),
      "--no-cache-dir",
      "--disable-pip-version-check",
      "--only-binary=:all:",
      ...requirements,
    ],
    { encoding: "utf8" }
  );
  if (result.status !== 0) {
    const detail = (result.stderr || result.stdout || "").trim();
    throw new Error(
      `Couldn't set up the bundled Python environment (pip exited ${result.status}).\n${detail}`
    );
  }
}

async function start() {
  // Idempotent: a second call while already running (e.g. macOS re-opening
  // via the dock after all windows closed) reuses the live server instead
  // of throwing or spawning a second one on a second port.
  if (child && currentPort) {
    return currentPort;
  }

  ensureAdijifInstalled();

  const port = await getFreePort();
  const bin = pythonBin();

  child = spawn(
    bin,
    [
      ...ISOLATION_FLAGS,
      "-m",
      "adijif.tools.explorer.cli",
      "--server.headless=true",
      `--server.port=${port}`,
      "--server.address=127.0.0.1",
    ],
    {
      detached: process.platform !== "win32",
      stdio: ["ignore", "pipe", "pipe"],
    }
  );

  child.stdout.on("data", (d) => process.stdout.write(`[streamlit] ${d}`));
  child.stderr.on("data", (d) => process.stderr.write(`[streamlit] ${d}`));

  const exitPromise = new Promise((_, reject) => {
    child.once("error", (err) => reject(err));
    child.once("exit", (code, signal) => {
      if (child) {
        // Died before we ever got healthy.
        reject(new Error(`Python process exited early (code=${code} signal=${signal})`));
      }
    });
  });

  try {
    await Promise.race([waitForHealth(port, HEALTH_TIMEOUT_MS), exitPromise]);
  } catch (err) {
    stop();
    throw err;
  }

  currentPort = port;
  return port;
}

function stop() {
  currentPort = null;
  if (!child) return;
  const pid = child.pid;
  if (process.platform === "win32") {
    spawn("taskkill", ["/pid", String(pid), "/T", "/F"]);
  } else {
    try {
      process.kill(-pid, "SIGTERM");
    } catch {
      // Process group already gone.
    }
  }
  child = null;
}

module.exports = { start, stop };
