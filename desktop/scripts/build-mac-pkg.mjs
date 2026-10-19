#!/usr/bin/env node
// Assembles the final macOS .pkg from the electron-builder-produced .app
// (signed, notarized separately as an app bundle) plus a second component
// package carrying the bundled Python runtime + vendored wheels, installed
// outside the .app at /Library/Application Support/PyADI-JIF. See
// electron-builder.yml's `mac` section comment for why this isn't done via
// electron-builder's built-in `pkg` target.
//
// Run after `electron-builder --mac` (see package.json's dist:mac script).
//
// Env vars:
//   APPLE_INSTALLER_SIGNING_IDENTITY  "Developer ID Installer: Org (TEAMID)"
//                                     - required for a distributable, signed
//                                       .pkg; if unset, builds an UNSIGNED
//                                       .pkg (useful for local testing only).
//   APPLE_NOTARY_PROFILE              notarytool keychain profile name -
//                                     if set, submits + staples the final
//                                       .pkg after assembly.

import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, rmSync, cpSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import os from "node:os";

const PRODUCT_NAME = "PyADI-JIF";
const SUPPORT_INSTALL_LOCATION = "/Library/Application Support/PyADI-JIF";
const OUT_DIR = "dist";
const APP_PKG_ID = "com.analog.pyadi-jif-explorer.app";
const SUPPORT_PKG_ID = "com.analog.pyadi-jif-explorer.support";
const PACKAGE_VERSION = JSON.parse(readFileSync("package.json", "utf8")).version;
const LICENSE_PATH = "build/license.txt";

function findBuiltApp() {
  // electron-builder's `dir` target writes to dist/mac/<ProductName>.app or
  // dist/mac-arm64/<ProductName>.app depending on arch.
  for (const dir of ["mac", "mac-arm64", "mac-x64"]) {
    const candidate = path.join(OUT_DIR, dir, `${PRODUCT_NAME}.app`);
    if (existsSync(candidate)) return candidate;
  }
  throw new Error(
    `couldn't find ${PRODUCT_NAME}.app under ${OUT_DIR}/mac* - run electron-builder --mac first`
  );
}

function detectArch() {
  // arm64 only - pyd2lang-native (the "draw" extra) ships no Intel-Mac
  // wheel and no sdist; see fetch-python.mjs.
  const arg = process.argv.find((a) => a.startsWith("--arch="));
  return arg ? arg.split("=")[1] : "arm64";
}

// productbuild only shows a license-agreement page when driven by an
// explicit Distribution.xml with a <license> element - the simpler
// "productbuild --package a --package b out.pkg" form (used previously)
// has no way to attach one. Written by hand rather than via
// `productbuild --synthesize` since we already know exactly the two
// pkg-refs involved.
function writeDistributionXml(distPath, licenseFilename) {
  const xml = `<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="1">
  <title>${PRODUCT_NAME}</title>
  <license file="${licenseFilename}" mime-type="text/plain"/>
  <options customize="never" require-scripts="false"/>
  <choices-outline>
    <line choice="default">
      <line choice="${APP_PKG_ID}"/>
      <line choice="${SUPPORT_PKG_ID}"/>
    </line>
  </choices-outline>
  <choice id="default"/>
  <choice id="${APP_PKG_ID}" visible="false">
    <pkg-ref id="${APP_PKG_ID}"/>
  </choice>
  <choice id="${SUPPORT_PKG_ID}" visible="false">
    <pkg-ref id="${SUPPORT_PKG_ID}"/>
  </choice>
  <pkg-ref id="${APP_PKG_ID}" version="${PACKAGE_VERSION}" onConclusion="none">app-component.pkg</pkg-ref>
  <pkg-ref id="${SUPPORT_PKG_ID}" version="${PACKAGE_VERSION}" onConclusion="none">support-component.pkg</pkg-ref>
</installer-gui-script>
`;
  writeFileSync(distPath, xml);
}

function main() {
  const identity = process.env.APPLE_INSTALLER_SIGNING_IDENTITY;
  if (!identity) {
    console.warn(
      "WARNING: APPLE_INSTALLER_SIGNING_IDENTITY not set - building an UNSIGNED " +
        ".pkg. This will fail Gatekeeper on other machines; only use for local testing."
    );
  }

  const appPath = findBuiltApp();
  const arch = detectArch();
  const pythonSrc = path.join("resources", "python", `darwin-${arch}`);
  const wheelsSrc = path.join("resources", "wheels", `darwin-${arch}`);
  if (!existsSync(pythonSrc) || !existsSync(wheelsSrc)) {
    throw new Error(
      `missing ${pythonSrc} or ${wheelsSrc} - run npm run prebuild:mac first`
    );
  }
  if (!existsSync(LICENSE_PATH)) {
    throw new Error(
      `missing ${LICENSE_PATH} - run npm run collect:licenses (part of prebuild:mac) first`
    );
  }

  const workDir = path.join(os.tmpdir(), `pyadi-jif-pkg-${Date.now()}`);
  const stageRoot = path.join(workDir, "support-root");
  mkdirSync(path.join(stageRoot, "python"), { recursive: true });
  // verbatimSymlinks: true is required so relative symlinks in the Python
  // runtime (e.g. bin/python3 -> python3.12) are preserved verbatim instead of
  // being resolved to absolute paths on the build machine.
  cpSync(pythonSrc, path.join(stageRoot, "python"), {
    recursive: true,
    verbatimSymlinks: true,
  });
  cpSync(wheelsSrc, path.join(stageRoot, "wheels"), {
    recursive: true,
    verbatimSymlinks: true,
  });

  const appComponentPkg = path.join(workDir, "app-component.pkg");
  const supportComponentPkg = path.join(workDir, "support-component.pkg");
  mkdirSync(OUT_DIR, { recursive: true });
  const finalPkg = path.join(OUT_DIR, `${PRODUCT_NAME}-Installer.pkg`);

  const signArgs = identity ? ["--sign", identity] : [];

  console.log("Building app component package...");
  execFileSync("pkgbuild", [
    "--component", appPath,
    "--identifier", APP_PKG_ID,
    "--version", PACKAGE_VERSION,
    "--install-location", "/Applications",
    ...signArgs,
    appComponentPkg,
  ], { stdio: "inherit" });

  console.log("Building support (python + wheels) component package...");
  execFileSync("pkgbuild", [
    "--root", stageRoot,
    "--identifier", SUPPORT_PKG_ID,
    "--version", PACKAGE_VERSION,
    "--install-location", SUPPORT_INSTALL_LOCATION,
    "--scripts", "build/installer/mac",
    ...signArgs,
    supportComponentPkg,
  ], { stdio: "inherit" });

  // productbuild's simpler "--package a --package b" form has no way to
  // attach a license page - that requires an explicit Distribution.xml
  // (see writeDistributionXml) plus a --resources dir the <license file="">
  // reference resolves against.
  console.log("Assembling Distribution.xml with license agreement...");
  const resourcesDir = path.join(workDir, "resources");
  mkdirSync(resourcesDir, { recursive: true });
  const licenseFilename = path.basename(LICENSE_PATH);
  cpSync(LICENSE_PATH, path.join(resourcesDir, licenseFilename));
  const distPath = path.join(workDir, "distribution.xml");
  writeDistributionXml(distPath, licenseFilename);

  console.log("Joining components into final installer package...");
  execFileSync("productbuild", [
    "--distribution", distPath,
    "--package-path", workDir,
    "--resources", resourcesDir,
    ...signArgs,
    finalPkg,
  ], { stdio: "inherit" });

  rmSync(workDir, { recursive: true, force: true });
  console.log(`Built ${finalPkg}`);

  const notaryProfile = process.env.APPLE_NOTARY_PROFILE;
  if (notaryProfile) {
    console.log("Submitting for notarization...");
    execFileSync(
      "xcrun",
      ["notarytool", "submit", finalPkg, "--keychain-profile", notaryProfile, "--wait"],
      { stdio: "inherit" }
    );
    console.log("Stapling notarization ticket...");
    execFileSync("xcrun", ["stapler", "staple", finalPkg], { stdio: "inherit" });
  } else {
    console.warn(
      "APPLE_NOTARY_PROFILE not set - skipping notarization. The .pkg will " +
        "be rejected by Gatekeeper on other machines until notarized."
    );
  }
}

main();
