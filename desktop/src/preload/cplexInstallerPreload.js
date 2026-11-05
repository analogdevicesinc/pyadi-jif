"use strict";

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("cplexInstaller", {
  getLicense: () => ipcRenderer.invoke("cplex:get-license"),
  install: () => ipcRenderer.invoke("cplex:install"),
  restartApp: () => ipcRenderer.invoke("cplex:restart-app"),
  cancel: () => ipcRenderer.invoke("cplex:cancel"),
  onProgress: (callback) => {
    ipcRenderer.on("cplex:progress", (_event, chunk) => callback(chunk));
  },
});
