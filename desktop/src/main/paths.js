"use strict";

const path = require("node:path");
const { app } = require("electron");

// macOS ships the bundled Python outside the signed .app bundle (see
// build/installer/mac/postinstall) so that pip-installed native extensions
// never touch the hardened-runtime-signed, notarized code the OS validates.
// Windows/Linux keep it inside the packaged resources dir, which their
// installer hooks (NSIS customInstall / deb-rpm postinst) populate in place.
const MAC_SUPPORT_DIR = "/Library/Application Support/PyADI-JIF";

// In dev (unpackaged) mode, resources/ holds one subdir per platform-arch,
// as written by scripts/fetch-python.mjs / fetch-wheels.mjs:
//   resources/python/<platform>-<arch>/...
//   resources/wheels/<platform>-<arch>/...
// Once packaged, electron-builder's per-platform extraResources config
// flattens this to just the current platform's own files, directly under
// resourcesPath (see electron-builder.yml's win/linux extraResources
// `to: python` / `to: wheels`, and build/installer/mac's pkgbuild root for
// darwin's out-of-bundle support directory).
function devResourceDir(kind) {
  return path.join(
    __dirname,
    "..",
    "..",
    "resources",
    kind,
    `${process.platform}-${process.arch}`
  );
}

function pythonDir() {
  if (!app.isPackaged) return devResourceDir("python");
  if (process.platform === "darwin") return path.join(MAC_SUPPORT_DIR, "python");
  return path.join(process.resourcesPath, "python");
}

function wheelsDir() {
  if (!app.isPackaged) return devResourceDir("wheels");
  if (process.platform === "darwin") return path.join(MAC_SUPPORT_DIR, "wheels");
  return path.join(process.resourcesPath, "wheels");
}

function pythonBin() {
  const dir = pythonDir();
  return process.platform === "win32"
    ? path.join(dir, "python.exe")
    : path.join(dir, "bin", "python3");
}

module.exports = { pythonDir, pythonBin, wheelsDir };
