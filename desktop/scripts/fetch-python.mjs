#!/usr/bin/env node
// Downloads a python-build-standalone "install_only" release for the given
// platform/arch into resources/python/<platform>-<arch>/. That directory is
// what electron-builder's per-platform extraResources config picks up, and
// what the installer hook scripts / src/main/paths.js expect to find.
//
// Usage: node scripts/fetch-python.mjs --platform win32 --arch x64

import { pipeline } from "node:stream/promises";
import { createWriteStream, mkdirSync, rmSync, existsSync } from "node:fs";
import { execFileSync } from "node:child_process";
import path from "node:path";

// Pin a specific python-build-standalone release for reproducibility. Bump
// deliberately, not implicitly.
const RELEASE_TAG = "20250808";
const PYTHON_VERSION_PREFIX = "cpython-3.12";

const TRIPLES = {
  // Windows: plain (non "-shared") triple - that variant has no
  // install_only build in this release. We spawn python.exe as a
  // subprocess rather than embedding via the C API, so we don't need the
  // shared pythonXY.dll variant anyway.
  "win32-x64": "x86_64-pc-windows-msvc",
  "win32-arm64": "aarch64-pc-windows-msvc",
  // darwin-x64 (Intel Mac) is intentionally unsupported - pyd2lang-native
  // (the "draw" extra) ships no Intel-Mac wheel and no sdist, and Apple
  // Silicon has been the standard for years. macOS builds are arm64 only.
  "darwin-arm64": "aarch64-apple-darwin",
  "linux-x64": "x86_64-unknown-linux-gnu",
  "linux-arm64": "aarch64-unknown-linux-gnu",
};

function parseArgs() {
  const args = process.argv.slice(2);
  const out = {};
  for (let i = 0; i < args.length; i += 2) {
    out[args[i].replace(/^--/, "")] = args[i + 1];
  }
  if (!out.platform || !out.arch) {
    throw new Error("usage: fetch-python.mjs --platform <win32|darwin|linux> --arch <x64|arm64>");
  }
  return out;
}

async function resolveAssetUrl(platform, arch) {
  const key = `${platform}-${arch}`;
  const triple = TRIPLES[key];
  if (!triple) throw new Error(`no python-build-standalone triple mapped for ${key}`);

  const res = await fetch(
    `https://api.github.com/repos/astral-sh/python-build-standalone/releases/tags/${RELEASE_TAG}`,
    { headers: { "User-Agent": "pyadi-jif-explorer-build" } }
  );
  if (!res.ok) {
    throw new Error(`GitHub releases lookup failed: ${res.status} ${res.statusText}`);
  }
  const release = await res.json();
  const asset = release.assets.find(
    (a) =>
      a.name.startsWith(PYTHON_VERSION_PREFIX) &&
      a.name.includes(triple) &&
      a.name.endsWith("-install_only.tar.gz")
  );
  if (!asset) {
    throw new Error(
      `no install_only asset found for ${triple} in release ${RELEASE_TAG} ` +
        `(${release.assets.length} assets checked)`
    );
  }
  return asset.browser_download_url;
}

async function main() {
  const { platform, arch } = parseArgs();
  const destDir = path.join("resources", "python", `${platform}-${arch}`);
  const tarPath = `${destDir}.tar.gz`;

  if (existsSync(destDir)) {
    console.log(`${destDir} already exists, skipping fetch (delete it to re-fetch)`);
    return;
  }

  console.log(`Resolving python-build-standalone asset for ${platform}-${arch}...`);
  const url = await resolveAssetUrl(platform, arch);

  console.log(`Downloading ${url}`);
  mkdirSync(path.dirname(destDir), { recursive: true });
  const res = await fetch(url);
  if (!res.ok) throw new Error(`download failed: ${res.status} ${res.statusText}`);
  await pipeline(res.body, createWriteStream(tarPath));

  mkdirSync(destDir, { recursive: true });
  execFileSync("tar", ["-xzf", tarPath, "-C", destDir, "--strip-components=1"]);
  rmSync(tarPath);

  console.log(`Python runtime ready at ${destDir}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
