"use strict";

function errorPageDataUrl(message) {
  const html = `<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>PyADI-JIF</title>
<style>
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: #0A2540;
    color: #FFFFFF;
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100vh;
    margin: 0;
  }
  .card {
    max-width: 32rem;
    padding: 2rem;
    text-align: center;
  }
  h1 { font-size: 1.25rem; margin-bottom: 0.5rem; }
  pre {
    text-align: left;
    background: #102B4F;
    padding: 0.75rem;
    border-radius: 6px;
    overflow-x: auto;
    font-size: 0.8rem;
    white-space: pre-wrap;
    word-break: break-word;
  }
  button {
    margin-top: 1.5rem;
    background: #0067B9;
    color: white;
    border: none;
    padding: 0.6rem 1.5rem;
    border-radius: 6px;
    font-size: 1rem;
    cursor: pointer;
  }
  button:hover { background: #0055a0; }
</style>
</head>
<body>
  <div class="card">
    <h1>PyADI-JIF Tools Explorer couldn't start</h1>
    <p>The bundled Python environment failed to start correctly. This can
       happen if the install-time setup step didn't complete.</p>
    <pre>${escapeHtml(message)}</pre>
    <button onclick="window.pyadiJif.retry()">Retry</button>
  </div>
</body>
</html>`;
  return `data:text/html;charset=utf-8,${encodeURIComponent(html)}`;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

module.exports = { errorPageDataUrl };
