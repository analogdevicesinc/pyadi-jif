"use strict";

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("pyadiJif", {
  retry: () => ipcRenderer.send("retry-launch"),
});
