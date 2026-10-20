#!/usr/bin/env node
// Single source of truth for the pyadi-jif version/extras pinned in
// config/pyadi-jif.json, fanned out into every installer hook script.
// The rendered files under build/installer/{win,mac,linux}/ are generated
// artifacts - edit the .tmpl files under build/installer/templates/ instead.

import { readFileSync, writeFileSync, chmodSync, existsSync, mkdirSync } from "node:fs";
import path from "node:path";

const { version, extras, extraPackages = [] } = JSON.parse(
  readFileSync("config/pyadi-jif.json", "utf8")
);
// pip requires each requirement as its own argv entry - a single quoted
// blob like "pyadi-jif[tools]==1 docplex" would be parsed as one (invalid)
// requirement string, not two. Each entry is individually double-quoted
// here so the substituted result drops in as pre-quoted argv tokens in
// both POSIX shell and Windows CreateProcess command-line parsing (both
// use double-quotes to group an argument containing special characters
// like the [ ] in "pyadi-jif[tools,gekko]").
const requirements = [`pyadi-jif[${extras}]==${version}`, ...extraPackages];
const PKG_SPEC = requirements.map((r) => `"${r}"`).join(" ");

const JOBS = [
  [
    "build/installer/templates/win-customInstall.nsh.tmpl",
    "build/installer/win/customInstall.nsh",
    null,
  ],
  [
    "build/installer/templates/mac-preinstall.sh.tmpl",
    "build/installer/mac/preinstall",
    0o755,
  ],
  [
    "build/installer/templates/mac-postinstall.sh.tmpl",
    "build/installer/mac/postinstall",
    0o755,
  ],
  [
    "build/installer/templates/linux-postinst.sh.tmpl",
    "build/installer/linux/postinst",
    0o755,
  ],
  [
    "build/installer/templates/linux-postremove.sh.tmpl",
    "build/installer/linux/postremove",
    0o755,
  ],
];

for (const [src, dst, mode] of JOBS) {
  if (!existsSync(src)) {
    throw new Error(`template missing: ${src}`);
  }
  const rendered = readFileSync(src, "utf8").replaceAll("__PKG_SPEC__", PKG_SPEC);
  // build/installer/{win,mac,linux}/ hold only generated, gitignored output
  // - on a fresh checkout (e.g. CI) they don't exist at all, since git
  // doesn't track empty directories.
  mkdirSync(path.dirname(dst), { recursive: true });
  writeFileSync(dst, rendered);
  if (mode !== null) chmodSync(dst, mode);
  console.log(`rendered ${dst}`);
}
