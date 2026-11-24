"use strict";

const statusEl = document.getElementById("status");
const licenseEl = document.getElementById("license");
const progressEl = document.getElementById("progress");
const resultEl = document.getElementById("result");
const actionsEl = document.getElementById("actions");

function setActions(buttons) {
  actionsEl.innerHTML = "";
  for (const { label, kind, onClick } of buttons) {
    const btn = document.createElement("button");
    btn.textContent = label;
    btn.className = kind;
    btn.addEventListener("click", onClick);
    actionsEl.appendChild(btn);
  }
}

async function loadLicense() {
  try {
    const { version, text } = await window.cplexInstaller.getLicense();
    statusEl.textContent = `cplex ${version} - license terms from PyPI:`;
    licenseEl.textContent = text;
    licenseEl.style.display = "block";
    setActions([
      { label: "Cancel", kind: "secondary", onClick: () => window.cplexInstaller.cancel() },
      { label: "I Agree & Install", kind: "primary", onClick: runInstall },
    ]);
  } catch (err) {
    statusEl.textContent = `Couldn't fetch the license from PyPI: ${err.message || err}`;
    setActions([
      { label: "Cancel", kind: "secondary", onClick: () => window.cplexInstaller.cancel() },
      { label: "Retry", kind: "primary", onClick: loadLicense },
    ]);
  }
}

async function runInstall() {
  licenseEl.style.display = "none";
  progressEl.style.display = "block";
  statusEl.textContent = "Installing cplex…";
  setActions([]);

  window.cplexInstaller.onProgress((chunk) => {
    progressEl.textContent += chunk;
    progressEl.scrollTop = progressEl.scrollHeight;
  });

  const { success, message } = await window.cplexInstaller.install();

  resultEl.textContent = message;
  resultEl.className = success ? "success" : "failure";

  if (success) {
    statusEl.textContent = "Done. Restart the app to pick up the new solver.";
    setActions([
      { label: "Later", kind: "secondary", onClick: () => window.cplexInstaller.cancel() },
      { label: "Restart Now", kind: "primary", onClick: () => window.cplexInstaller.restartApp() },
    ]);
  } else {
    statusEl.textContent = "Installation failed.";
    setActions([{ label: "Close", kind: "secondary", onClick: () => window.cplexInstaller.cancel() }]);
  }
}

loadLicense();
