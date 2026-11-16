#!/usr/bin/env node
// Vendors the full wheel closure for pyadi-jif[tools]==<pinned version> for a
// target platform/arch, so the installer's pip step can run fully offline
// (`pip install --no-index --find-links <this dir>`). Uses the *build host's*
// python/pip as the resolver (via pip's --platform/--python-version/--abi/
// --implementation cross-platform download support) - it does not need to
// execute the bundled target-platform Python, which may not even be runnable
// on this host (e.g. building the Windows wheel closure from a Linux/macOS
// build machine).
//
// Requires python3 (with a reasonably recent pip, >=21) on PATH.
//
// Usage: node scripts/fetch-wheels.mjs --platform win32 --arch x64 [--local-wheels <dir>]
//
// --local-wheels (or the PYADI_JIF_LOCAL_WHEELS env var, which is how CI
// passes it through `npm run dist:*`) adds a directory of locally built
// wheels as an extra pip --find-links source. CI uses this to bundle the
// pyadi-jif wheel built from the commit under test (a .devN version, see
// scripts/set-version.mjs) instead of a release from PyPI. Dependencies are
// still resolved from PyPI for the target platform.

import { execFileSync } from "node:child_process";
import { readFileSync, mkdirSync, existsSync } from "node:fs";
import path from "node:path";

const PYTHON_VERSION = "312"; // matches PYTHON_VERSION_PREFIX in fetch-python.mjs (cpython-3.12)

const PIP_PLATFORM_TAGS = {
  "win32-x64": ["win_amd64"],
  "win32-arm64": ["win_arm64"],
  // darwin-x64 (Intel Mac) intentionally unsupported - see fetch-python.mjs.
  "darwin-arm64": ["macosx_11_0_arm64", "macosx_12_0_arm64"],
  "linux-x64": ["manylinux2014_x86_64", "manylinux_2_17_x86_64"],
  "linux-arm64": ["manylinux2014_aarch64", "manylinux_2_17_aarch64"],
};

function parseArgs() {
  const args = process.argv.slice(2);
  const out = {};
  for (let i = 0; i < args.length; i += 2) {
    out[args[i].replace(/^--/, "")] = args[i + 1];
  }
  if (!out.platform || !out.arch) {
    throw new Error("usage: fetch-wheels.mjs --platform <win32|darwin|linux> --arch <x64|arm64>");
  }
  return out;
}

function findPython() {
  for (const candidate of ["python3", "python"]) {
    try {
      execFileSync(candidate, ["--version"], { stdio: "ignore" });
      return candidate;
    } catch {
      // try next candidate
    }
  }
  throw new Error("no python3/python found on PATH - required to resolve/download wheels");
}

function main() {
  const { platform, arch, "local-wheels": localWheelsArg } = parseArgs();
  const localWheels = localWheelsArg || process.env.PYADI_JIF_LOCAL_WHEELS;
  const key = `${platform}-${arch}`;
  const tags = PIP_PLATFORM_TAGS[key];
  if (!tags) throw new Error(`no pip platform tag mapped for ${key}`);

  const { version, extras, extraPackages = [] } = JSON.parse(
    readFileSync("config/pyadi-jif.json", "utf8")
  );
  const requirements = [`pyadi-jif[${extras}]==${version}`, ...extraPackages];

  const destDir = path.join("resources", "wheels", key);
  mkdirSync(destDir, { recursive: true });

  const python = findPython();
  const [mainSpec, ...extraReqs] = requirements;

  // extraPackages (currently just docplex) publish no prebuilt wheels on
  // PyPI, only an sdist. `pip download` saves the sdist .tar.gz as-is,
  // which the installer's `pip install --only-binary=:all:` step would
  // then reject (verified empirically). `pip wheel` instead builds an
  // actual wheel from the sdist here on the build host - safe because
  // these are pure Python packages (no native extensions to cross-compile),
  // so the resulting py3-none-any wheel works unmodified on any target
  // platform. --no-deps because dependencies are already covered by the
  // main requirement's cross-platform download pass below. Built *first*
  // so that pass can find them too (destDir is passed as --find-links):
  // pyadi-jif itself depends on docplex, so without a prebuilt wheel there
  // the --only-binary resolve fails outright.
  if (extraReqs.length > 0) {
    console.log(`Building wheels for extra packages: ${extraReqs.join(", ")}`);
    execFileSync(python, ["-m", "pip", "wheel", "--no-deps", "-w", destDir, ...extraReqs], {
      stdio: "inherit",
    });
  }

  const crossPlatformArgs = [
    "-m",
    "pip",
    "download",
    "--only-binary=:all:",
    "--python-version",
    PYTHON_VERSION,
    "--implementation",
    "cp",
    "--abi",
    `cp${PYTHON_VERSION}`,
    "-d",
    destDir,
  ];
  for (const tag of tags) {
    crossPlatformArgs.push("--platform", tag);
  }
  crossPlatformArgs.push("--find-links", path.resolve(destDir));
  if (localWheels) {
    if (!existsSync(localWheels)) throw new Error(`local wheel dir not found: ${localWheels}`);
    console.log(`Using local wheels from ${localWheels}`);
    crossPlatformArgs.push("--find-links", path.resolve(localWheels));
  }
  crossPlatformArgs.push(mainSpec);

  console.log(`Downloading wheel closure for ${mainSpec} (${key})...`);
  execFileSync(python, crossPlatformArgs, { stdio: "inherit" });

  console.log(`Wheels ready at ${destDir}`);
}

if (!existsSync("config/pyadi-jif.json")) {
  throw new Error("run this from the project root (config/pyadi-jif.json not found)");
}
main();
