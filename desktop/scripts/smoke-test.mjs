#!/usr/bin/env node
// Smoke-tests an *installed* PyADI-JIF desktop app (CI runs this right after
// installing the freshly built installer on each OS):
//   1. the installer's pip step populated the bundled Python with the pinned
//      pyadi-jif version (config/pyadi-jif.json) and a clock solve works;
//   2. the packaged Electron app launches, starts Streamlit and renders the
//      Tools Explorer UI without exceptions (see src/main/smokeTest.js).
//
// Usage: node scripts/smoke-test.mjs --platform <win32|darwin|linux> [--install-dir <dir>]
// --install-dir is only needed on Windows, where the NSIS location is chosen
// at install time (CI passes /D=<dir>).

import { spawn, execFileSync } from "node:child_process";
import { existsSync, readFileSync, rmSync, mkdtempSync } from "node:fs";
import os from "node:os";
import path from "node:path";

const APP_TIMEOUT_MS = 300_000;

function parseArgs() {
  const args = process.argv.slice(2);
  const out = {};
  for (let i = 0; i < args.length; i += 2) {
    out[args[i].replace(/^--/, "")] = args[i + 1];
  }
  if (!out.platform) {
    throw new Error("usage: smoke-test.mjs --platform <win32|darwin|linux> [--install-dir <dir>]");
  }
  return out;
}

// Mirrors the install layouts in electron-builder.yml, scripts/build-mac-pkg.mjs
// and src/main/paths.js.
function installedPaths(platform, installDir) {
  switch (platform) {
    case "win32":
      if (!installDir) throw new Error("--install-dir is required on win32");
      return {
        python: path.join(installDir, "resources", "python", "python.exe"),
        app: path.join(installDir, "PyADI-JIF.exe"),
      };
    case "darwin":
      return {
        python: "/Library/Application Support/PyADI-JIF/python/bin/python3",
        app: "/Applications/PyADI-JIF.app/Contents/MacOS/PyADI-JIF",
      };
    case "linux":
      return {
        python: "/opt/PyADI-JIF/resources/python/bin/python3",
        app: "/opt/PyADI-JIF/pyadi-jif",
      };
    default:
      throw new Error(`unsupported platform: ${platform}`);
  }
}

// Same -E -s isolation as the installer hooks and pythonRuntime.js.
const PYTHON_CHECK = `
import importlib.metadata as md, sys
expected = sys.argv[1]
version = md.version("pyadi-jif")
print("pyadi-jif", version)
assert version == expected, f"expected pyadi-jif {expected}, got {version}"
import adijif, streamlit, gekko, docplex  # noqa: F401
clk = adijif.hmc7044(solver="gekko")
clk.n2 = 24
clk.set_requested_clocks(125000000, [1000000000, 500000000, 7812500], ["ADC", "FPGA", "SYSREF"])
clk.solve()
print("hmc7044 solve:", clk.get_config()["out_dividers"])
`;

function checkPython(python, expectedVersion) {
  console.log(`== bundled Python: ${python}`);
  execFileSync(python, ["-E", "-s", "-c", PYTHON_CHECK, expectedVersion], { stdio: "inherit" });
}

async function checkApp(appBin) {
  console.log(`== app launch: ${appBin}`);
  const tmp = mkdtempSync(path.join(os.tmpdir(), "pyadi-jif-smoke-"));
  const resultPath = path.join(tmp, "result.json");
  const child = spawn(appBin, [], {
    env: { ...process.env, PYADI_JIF_SMOKE_RESULT: resultPath },
    stdio: "inherit",
  });
  const exited = new Promise((resolve) => child.once("exit", resolve));
  const timedOut = new Promise((resolve) => setTimeout(() => resolve("timeout"), APP_TIMEOUT_MS));
  const outcome = await Promise.race([exited, timedOut]);
  if (outcome === "timeout") {
    child.kill();
    throw new Error(`app did not finish its smoke test within ${APP_TIMEOUT_MS / 1000}s`);
  }
  if (!existsSync(resultPath)) {
    throw new Error(`app exited (code ${outcome}) without writing a smoke-test result`);
  }
  const result = JSON.parse(readFileSync(resultPath, "utf8"));
  rmSync(tmp, { recursive: true, force: true });
  console.log(result.detail);
  if (!result.ok) throw new Error("app smoke test failed");
}

async function main() {
  const { platform, "install-dir": installDir } = parseArgs();
  const { version } = JSON.parse(readFileSync("config/pyadi-jif.json", "utf8"));
  const { python, app } = installedPaths(platform, installDir);
  for (const p of [python, app]) {
    if (!existsSync(p)) throw new Error(`not installed: ${p}`);
  }
  checkPython(python, version);
  await checkApp(app);
  console.log("smoke test passed");
}

await main();
