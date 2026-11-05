"use strict";

const path = require("node:path");
const { spawn } = require("node:child_process");
const { BrowserWindow, ipcMain } = require("electron");
const { pythonBin } = require("./paths");

// Same isolation flags as pythonRuntime.js and the installer scripts: -s
// disables user-site, -E ignores inherited PYTHON* env vars, so this stays
// self-contained in the bundled interpreter.
const ISOLATION_FLAGS = ["-E", "-s"];

// cplex is IBM's proprietary Community Edition package - it carries a full
// click-through EULA on its own PyPI page. We deliberately never vendor or
// auto-install it (see config/pyadi-jif.json / docs): this is the one path
// where it's installed, and only after the user is shown the live license
// text (fetched at click-time, not a bundled copy that can go stale as IBM
// revises terms) and explicitly agrees. It hits PyPI directly over the
// network - not our offline wheelhouse - so the user's agreement is the
// same act as if they'd typed `pip install cplex` themselves.
const CPLEX_PYPI_JSON_URL = "https://pypi.org/pypi/cplex/json";

let installerWindow = null;
let handlersRegistered = false;

function registerHandlers(getMainWindow, pythonRuntime) {
  if (handlersRegistered) return;
  handlersRegistered = true;

  ipcMain.handle("cplex:get-license", async () => {
    const res = await fetch(CPLEX_PYPI_JSON_URL);
    if (!res.ok) {
      throw new Error(`PyPI lookup failed: ${res.status} ${res.statusText}`);
    }
    const data = await res.json();
    return {
      version: data.info.version,
      text: data.info.description || "(PyPI returned no license text for this release)",
    };
  });

  ipcMain.handle("cplex:install", (event) => {
    return new Promise((resolve) => {
      const child = spawn(pythonBin(), [
        ...ISOLATION_FLAGS,
        "-m",
        "pip",
        "install",
        "--no-cache-dir",
        "--disable-pip-version-check",
        "cplex",
      ]);
      child.stdout.on("data", (d) => event.sender.send("cplex:progress", d.toString()));
      child.stderr.on("data", (d) => event.sender.send("cplex:progress", d.toString()));
      child.on("error", (err) => resolve({ success: false, message: err.message }));
      child.on("close", (code) => {
        resolve({
          success: code === 0,
          message: code === 0 ? "cplex installed successfully." : `pip exited with code ${code}.`,
        });
      });
    });
  });

  // Restarts the bundled Streamlit process so adijif's solver detection
  // (which runs at import time) picks up the newly-installed cplex engine,
  // then reloads the main window against the fresh server.
  ipcMain.handle("cplex:restart-app", async () => {
    pythonRuntime.stop();
    const mainWindow = getMainWindow();
    const port = await pythonRuntime.start();
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.loadURL(`http://127.0.0.1:${port}`);
    }
    closeInstallerWindow();
    return { ok: true };
  });

  ipcMain.handle("cplex:cancel", () => {
    closeInstallerWindow();
    return { ok: true };
  });
}

function closeInstallerWindow() {
  if (installerWindow && !installerWindow.isDestroyed()) {
    installerWindow.close();
  }
  installerWindow = null;
}

function openCplexInstallerWindow(parentWindow, pythonRuntime, getMainWindow) {
  registerHandlers(getMainWindow, pythonRuntime);

  if (installerWindow && !installerWindow.isDestroyed()) {
    installerWindow.focus();
    return;
  }

  installerWindow = new BrowserWindow({
    width: 680,
    height: 760,
    parent: parentWindow || undefined,
    modal: !!parentWindow,
    title: "Install CPLEX Support",
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, "..", "preload", "cplexInstallerPreload.js"),
    },
  });
  installerWindow.on("closed", () => {
    installerWindow = null;
  });
  installerWindow.loadFile(path.join(__dirname, "..", "renderer", "cplexInstaller.html"));
}

module.exports = { openCplexInstallerWindow };
