"use strict";

const path = require("node:path");
const { app, BrowserWindow, ipcMain, Menu } = require("electron");
const pythonRuntime = require("./pythonRuntime");
const { errorPageDataUrl } = require("./errorPage");
const { openCplexInstallerWindow } = require("./cplexInstaller");

if (!app.requestSingleInstanceLock()) {
  app.quit();
}

let win = null;

function createWindow() {
  win = new BrowserWindow({
    width: 1280,
    height: 860,
    title: "PyADI-JIF",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, "..", "preload", "errorPreload.js"),
    },
  });
  win.on("closed", () => {
    win = null;
  });
  return win;
}

async function attemptLaunch() {
  if (!win) return;
  try {
    const port = await pythonRuntime.start();
    // The window keeps errorPreload.js loaded even once we're on the real
    // app - it only exposes a harmless retry() call, and the loaded content
    // is our own bundled Streamlit app, not remote/untrusted content.
    win.loadURL(`http://127.0.0.1:${port}`);
  } catch (err) {
    console.error(err);
    win.loadURL(errorPageDataUrl(err.message || String(err)));
  }
}

ipcMain.on("retry-launch", () => {
  attemptLaunch();
});

function buildMenu() {
  const template = [
    // macOS needs its standard app menu (About/Hide/Quit/Cmd shortcuts) kept
    // - replacing the whole application menu without it removes those.
    ...(process.platform === "darwin" ? [{ role: "appMenu" }] : []),
    {
      label: "Solvers",
      submenu: [
        {
          label: "Install CPLEX Support (Online)…",
          click: () => openCplexInstallerWindow(win, pythonRuntime, () => win),
        },
      ],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

app.on("second-instance", () => {
  if (win) {
    if (win.isMinimized()) win.restore();
    win.focus();
  }
});

app.whenReady().then(() => {
  buildMenu();
  createWindow();
  attemptLaunch();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
    attemptLaunch();
  }
});

let quitting = false;
app.on("before-quit", (e) => {
  if (quitting) return;
  quitting = true;
  e.preventDefault();
  pythonRuntime.stop();
  app.exit(0);
});
