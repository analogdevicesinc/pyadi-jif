#!/usr/bin/env node
// Points config/pyadi-jif.json at a locally built pyadi-jif wheel, so every
// consumer of that file (render-installer-scripts.mjs, fetch-wheels.mjs, and
// the packaged app's self-heal in src/main/pythonRuntime.js) pins the exact
// same version. Used by CI to bundle the wheel built from the commit under
// test - pair with PYADI_JIF_LOCAL_WHEELS (see fetch-wheels.mjs).
//
// Also sets package.json's version to the wheel's base release (e.g. 0.1.8
// for 0.1.8.dev20261017120000) so installer filenames track pyadi-jif.
// The .devN suffix is deliberately not carried over: it isn't valid semver,
// and rpm/NSIS version fields are stricter still.
//
// Usage: node scripts/set-version.mjs <path/to/pyadi_jif-<ver>-py3-none-any.whl>

import { readFileSync, writeFileSync, existsSync } from "node:fs";
import path from "node:path";

const wheel = process.argv[2];
if (!wheel || !existsSync(wheel)) {
  throw new Error("usage: set-version.mjs <path/to/pyadi_jif-<ver>-*.whl>");
}
const match = path.basename(wheel).match(/^pyadi_jif-([^-]+)-/);
if (!match) throw new Error(`not a pyadi-jif wheel: ${wheel}`);
const version = match[1];
const baseVersion = version.match(/^\d+\.\d+\.\d+/)?.[0];
if (!baseVersion) throw new Error(`can't parse base version from ${version}`);

const configPath = "config/pyadi-jif.json";
const config = JSON.parse(readFileSync(configPath, "utf8"));
config.version = version;
writeFileSync(configPath, JSON.stringify(config, null, 2) + "\n");

const pkg = JSON.parse(readFileSync("package.json", "utf8"));
pkg.version = baseVersion;
writeFileSync("package.json", JSON.stringify(pkg, null, 2) + "\n");

console.log(`pyadi-jif ${version} (app version ${baseVersion})`);
