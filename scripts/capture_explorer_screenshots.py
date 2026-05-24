"""Capture Streamlit Explorer page screenshots for the docs.

Currently produces the ADF4030 System Designer screenshot. Extend
with additional capture functions to refresh other page screenshots
when the UI changes.

Prerequisites (already installed in the project venv):

    .venv/bin/python -m pip install playwright pytest-playwright
    .venv/bin/playwright install chromium

Run from the repo root:

    .venv/bin/python scripts/capture_explorer_screenshots.py

Writes PNG(s) into doc/source/_static/imgs/.
"""

from __future__ import annotations

import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_FILE = REPO_ROOT / "adijif" / "tools" / "explorer" / "main.py"
OUT_DIR = REPO_ROOT / "doc" / "source" / "_static" / "imgs"
PORT = 8765
URL = f"http://localhost:{PORT}"


def _wait_for_server(url: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return
        except (urllib.error.URLError, ConnectionResetError):
            time.sleep(0.5)
    raise TimeoutError(f"Streamlit at {url} not ready after {timeout}s")


def _capture_adf4030_system_designer(page) -> None:
    page.set_viewport_size({"width": 1440, "height": 960})
    page.goto(URL, wait_until="networkidle")

    # Wait for the Streamlit app and sidebar to fully render
    page.wait_for_selector('[data-testid="stApp"]', state="visible", timeout=15000)
    page.wait_for_selector(
        '[data-testid="stSidebarUserContent"]', state="visible", timeout=15000
    )

    # Pick the page from the sidebar using the same pattern as the e2e page objects
    sidebar_content = page.locator('[data-testid="stSidebarUserContent"]')
    radio_button = sidebar_content.locator('label:has-text("ADF4030 System Designer")')
    radio_button.wait_for(state="visible", timeout=10000)
    radio_button.click()

    # Wait for Streamlit to finish re-rendering
    page.wait_for_selector('[data-testid="stApp"]', state="visible", timeout=15000)
    try:
        page.wait_for_function(
            "() => document.querySelectorAll('[data-testid=\"stSpinner\"]').length === 0",
            timeout=5000,
        )
    except Exception:
        pass

    # Give the iframe-rendered SVG time to render.
    page.wait_for_timeout(5000)

    out = OUT_DIR / "adf4030systemdesigner.png"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(out), full_page=True)
    print(f"wrote {out.relative_to(REPO_ROOT)}")


def main() -> None:
    """Launch Streamlit, capture screenshots, then tear down."""
    proc = subprocess.Popen(
        [
            str(REPO_ROOT / ".venv" / "bin" / "streamlit"),
            "run",
            str(APP_FILE),
            "--server.headless=true",
            f"--server.port={PORT}",
            "--browser.gatherUsageStats=false",
        ],
        cwd=str(REPO_ROOT),
    )
    try:
        _wait_for_server(URL)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context()
            page = ctx.new_page()
            _capture_adf4030_system_designer(page)
            browser.close()
    finally:
        proc.terminate()
        proc.wait(timeout=10)


if __name__ == "__main__":
    main()
