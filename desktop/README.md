# PyADI-JIF Desktop Explorer

Electron desktop wrapper around [PyADI-JIF Tools Explorer](https://pypi.org/project/pyadi-jif/), a
Streamlit app for configuring ADI JESD204 interface clocking. Instead of freezing the whole Python
interpreter into the app (PyInstaller-style), this bundles a portable Python runtime and has the OS
installer itself run `pip install` into it at install time, offline, from a vendored wheel closure.

See `config/pyadi-jif.json` for the pinned `pyadi-jif` version/extras — every build script and
installer hook reads from this one file.

## How it fits together

- `src/main/` — the Electron main process. `pythonRuntime.js` spawns the bundled Python running
  the Streamlit app on a free local port, health-checks it, and self-heals (re-runs the offline pip
  install) if the environment turns out to be broken — which is also what the app's error-screen
  Retry button triggers.
- `scripts/fetch-python.mjs` — downloads a [python-build-standalone](https://github.com/astral-sh/python-build-standalone)
  release for a given platform/arch into `resources/python/<platform>-<arch>/`.
- `scripts/fetch-wheels.mjs` — vendors the full offline wheel closure for the pinned `pyadi-jif`
  spec into `resources/wheels/<platform>-<arch>/`, so installs never need network access.
- `scripts/render-installer-scripts.mjs` — fans the version pin out into the three per-platform
  installer hook scripts under `build/installer/{win,mac,linux}/` (generated — edit the `.tmpl`
  files under `build/installer/templates/` instead).
- `scripts/collect-licenses.mjs` (+ `extract_wheel_licenses.py`) — reads every vendored wheel's own
  license metadata/file and assembles `build/generated/THIRD-PARTY-LICENSES.txt`, shown as the
  actual license-agreement page during install (see "Third-party licenses" below).
- `scripts/build-mac-pkg.mjs` — assembles the final macOS `.pkg` via `pkgbuild`/`productbuild`
  (electron-builder only produces the signed `.app`; see the comment in `electron-builder.yml`).
- `resources/` and `build/generated/` — gitignored. Populated by the fetch/collect scripts, not
  checked in. `scripts/license-texts/` (fallback SPDX license texts) *is* checked in — it's a small,
  static asset we maintain, not build output.

## Prerequisites

- Node.js 22+ and npm
- `python3` on `PATH` (used only at build time, by `fetch-wheels.mjs`, to resolve/download wheels
  for the *target* platform via pip's cross-platform `--platform`/`--abi` flags — it does not need
  to match the bundled runtime's version)
- `build/icons/icon.png`, `icon.ico` and `icon.icns` exist (rendered/converted from `pyadi-jif`'s
  own `favicon.svg`) but are placeholders, not a production-ready icon set. Commission a real icon
  set before a public release.
- Building the macOS `.pkg` requires running on actual macOS (`pkgbuild`/`productbuild` are Apple
  tools); building `deb`/`rpm` needs the corresponding Linux packaging tools available to
  electron-builder.
- **macOS is arm64 (Apple Silicon) only** — `pyd2lang-native` (the `draw` extra, diagramming
  support) ships no Intel-Mac wheel and no sdist, and Intel Mac support was dropped rather than
  making `draw` conditional per-platform. `resources/python/darwin-x64` /
  `resources/wheels/darwin-x64` are not a thing; don't try to fetch them.
- **Building the Windows target from a non-Windows host requires Wine** (`sudo apt-get install wine
  wine64` on Debian/Ubuntu) — electron-builder needs it to run `rcedit`/signing-adjacent tooling on
  the packaged `.exe` files, independent of whether you're actually code-signing. Building on
  `windows-latest` (see CI below) avoids this entirely.

```bash
npm install
```

## Local development

Fetch a portable Python and the offline wheel closure for your own machine's platform/arch, then
just run the app — first launch self-installs `pyadi-jif` into the bundled interpreter:

```bash
npm run fetch:python -- --platform <win32|darwin|linux> --arch <x64|arm64>
npm run fetch:wheels -- --platform <win32|darwin|linux> --arch <x64|arm64>
npm start
```

(e.g. on Linux x64: `npm run fetch:python -- --platform linux --arch x64`)

To pick up a version bump, edit `config/pyadi-jif.json`, delete the corresponding
`resources/python/<platform>-<arch>/` and `resources/wheels/<platform>-<arch>/` directories, and
re-run the two fetch commands above.

## Building installers

Each platform's build fetches its own Python + wheels, renders the installer scripts, then invokes
electron-builder (plus the extra macOS packaging step):

```bash
npm run dist:win     # NSIS installer, runs pip during install
npm run dist:mac     # signed .app + separate pkgbuild/productbuild .pkg assembly
npm run dist:linux   # deb + rpm, run pip via a postinst/afterInstall script
```

Notes:

- macOS and Linux targets were chosen specifically because they support an install-time hook that
  can run `pip` (`pkg` postinstall scripts, `deb`/`rpm` `afterInstall`) — plain drag-install DMG and
  single-file AppImage don't have an install step to hook into, so they aren't used here.
- A distributable macOS `.pkg` needs a **Developer ID Application** cert (to sign the `.app`) and a
  separate **Developer ID Installer** cert (to sign the `.pkg` itself), plus notarization via
  `xcrun notarytool` — set `CSC_NAME`/`CSC_LINK` for the former, and
  `APPLE_INSTALLER_SIGNING_IDENTITY` / `APPLE_NOTARY_PROFILE` (read by
  `scripts/build-mac-pkg.mjs`) for the latter. Without these, `dist:mac` still produces a `.pkg`,
  but it's unsigned and will be rejected by Gatekeeper on any other machine.
- Windows code signing isn't wired up yet; add electron-builder's standard `win.certificateFile`/
  `certificatePassword` (or `CSC_LINK`/`CSC_KEY_PASSWORD` env vars) before a public release, or
  installs will trip SmartScreen warnings.

## Bundling a locally built pyadi-jif

By default the installers bundle the PyPI release pinned in `config/pyadi-jif.json`. To bundle a
wheel built from this repo's checkout instead (what CI does):

```bash
(cd .. && nox -s dev_release)            # -> ../dist/pyadi_jif-<ver>.devN-py3-none-any.whl
mkdir -p local-wheels && cp ../dist/*.whl local-wheels/
node scripts/set-version.mjs local-wheels/pyadi_jif-*.whl
PYADI_JIF_LOCAL_WHEELS=local-wheels npm run dist:linux
```

`set-version.mjs` rewrites `config/pyadi-jif.json` (and `package.json`'s version) to match the
wheel; `fetch-wheels.mjs` adds `PYADI_JIF_LOCAL_WHEELS` as an extra `--find-links` source. Don't
commit the rewritten files.

## CI

`../.github/workflows/desktop.yml` builds all three installers (NSIS on `windows-latest`, deb/rpm
on `ubuntu-latest`, pkg on `macos-14`) around a single `nox -s dev_release` wheel of the commit
under test. It runs:

- after every successful **Tests** run on `main` — and then republishes the installers plus the
  wheel as the rolling pre-release **"Development Release"** (tag `dev`, recreated each time);
- on pull requests touching `desktop/` — build only, no publish;
- on manual `workflow_dispatch` — build only.

Every installer is then installed on a fresh runner of its own OS and checked by
`scripts/smoke-test.mjs`: the bundled Python must have the expected `pyadi-jif` version and solve
an HMC7044 clock tree with gekko, and the installed app must launch and render the Tools Explorer
UI without a Streamlit exception. The app side of that check is `src/main/smokeTest.js`, active
only when `PYADI_JIF_SMOKE_RESULT` is set. Publishing waits for every build and smoke test to pass.

All CI installers are unsigned.

## Why `pyadi-jif[tools,gekko,draw]` plus a standalone `docplex`

`pyadi-jif[tools]` alone crashes on import: its solver module needs `gekko` or `cplex`/`docplex`,
and separately its FPGA module unconditionally imports `docplex` regardless of which solver extra
was requested (not actually optional despite being nominally gated behind pyproject.toml's `cplex`
extra). The `cplex` PyPI package is proprietary-licensed (IBM's Community Edition EULA), which isn't
appropriate to vendor into a public installer's offline wheelhouse — `docplex` itself is Apache 2.0
and satisfies the import on its own without the proprietary solver engine, so it's pinned as a
standalone `extraPackages` entry in `config/pyadi-jif.json` rather than pulling in the `cplex`
extra. `docplex` also ships only as an sdist on PyPI (no prebuilt wheel), so `fetch-wheels.mjs`
builds it into a wheel at fetch time via `pip wheel` rather than vendoring the raw sdist, which the
installer's `--only-binary=:all:` step would otherwise reject.

pyadi-jif 0.1.8 and later list `docplex` as a core dependency, so the wheel is needed even
without the `extraPackages` entry. `fetch-wheels.mjs` builds the `extraPackages` wheels *before*
resolving `pyadi-jif`, so that resolve can use the locally built `docplex` wheel.

`draw` pulls in `pyd2lang-native` (native Python bindings to [d2lang](https://d2lang.com), MPL-2.0)
for the app's diagramming feature. It's included in the default offline install on Windows/Linux/
Apple Silicon Mac — see the Intel Mac note above for why it's not everywhere.

Note that `adijif/solvers.py` only checks `find_spec("docplex")` to decide whether the "cplex"
solver path is available — it doesn't actually check for the `cplex` package itself, which is what
provides the real solving engine. So with only `docplex` bundled, that path imports fine but can't
actually solve anything; the in-app CPLEX installer (below) is what makes it functional.

## Third-party licenses

`scripts/collect-licenses.mjs` builds `build/generated/THIRD-PARTY-LICENSES.txt` from every wheel
actually vendored for the platform being built (via `scripts/extract_wheel_licenses.py`, which
reads each wheel's own `dist-info` metadata/license file directly — automated rather than a
hand-picked list, so it can't silently miss a transitive dependency and stays correct as versions
change). This is real license text pulled from the packages themselves — including `pyadi-jif`'s
own EPL-2.0 and `pyd2lang-native`'s MPL-2.0 — not just a declared-license label. A handful of
packages declare a license but don't embed its text in the wheel; for those, `scripts/license-texts/`
carries canonical SPDX text (MIT, Apache-2.0, BSD-2/3-Clause, MPL-2.0) as a fallback, clearly
labeled as such in the combined doc. Anything matching neither gets an explicit
"license text not available, see PyPI" note rather than being silently omitted — check the
`collect-licenses.mjs` output for that case and extend `SPDX_ALIASES`/`license-texts/` if it comes up.

This combined document is what the user actually agrees to during setup, not a separate afterthought:

- **Windows**: `nsis.license` — the standard NSIS installer license page.
- **macOS**: `scripts/build-mac-pkg.mjs` writes a `Distribution.xml` with a `<license>` element,
  since the simpler `productbuild --package a --package b` form (no distribution file) has no way
  to show one — this is the only reason that script builds its own Distribution.xml instead of the
  simpler form.
- **Linux**: no interactive agreement mechanism exists in `dpkg`/`rpm`, so the document is instead
  shipped inside the installed app at `/opt/PyADI-JIF/resources/THIRD-PARTY-LICENSES.txt` for the
  user to review.

`cplex` is deliberately **not** part of this combined document — see below for why it gets its own,
separate, live-fetched agreement instead of being bundled up front.

## Optional: installing CPLEX support from within the app

The app never bundles or auto-installs the actual `cplex` engine — it's IBM's proprietary
Community Edition package and carries its own click-through EULA on PyPI. Instead, the running app
has a **Solvers → Install CPLEX Support (Online)…** menu item that:

1. Fetches the *current* license text live from PyPI at click time (not a bundled copy that can go
   stale as IBM revises terms) and displays it — nothing installs until the user clicks "I Agree &
   Install".
2. On agreement, runs `pip install cplex` against PyPI directly (this one path needs network access
   — everything else in this app is offline by design) into the bundled interpreter, streaming
   progress into the window.
3. Offers to restart the app afterward, since `adijif`'s solver detection runs at import time and
   won't pick up the new engine in an already-running process.

See `src/main/cplexInstaller.js`, `src/preload/cplexInstallerPreload.js`, and
`src/renderer/cplexInstaller.*`.
