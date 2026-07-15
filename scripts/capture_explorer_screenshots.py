"""Capture Streamlit Explorer screenshots for the documentation.

The script captures an overview for every Explorer page and a focused result
view for the longer solver-backed pages. Keeping the screenshots reproducible
makes it straightforward to refresh the docs after UI changes.

Prerequisites (included in the ``e2e`` extra):

    .venv/bin/python -m pip install -e '.[cplex,draw,tools,e2e]'
    .venv/bin/playwright install chromium

Run from the repository root:

    .venv/bin/python scripts/capture_explorer_screenshots.py

Writes PNGs into ``doc/source/_static/imgs/``.
"""

from __future__ import annotations

import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, ViewportSize, sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_FILE = REPO_ROOT / "adijif" / "tools" / "explorer" / "main.py"
OUT_DIR = REPO_ROOT / "doc" / "source" / "_static" / "imgs"
PORT = 8765
URL = f"http://localhost:{PORT}"
VIEWPORT: ViewportSize = {"width": 1440, "height": 960}


def _wait_for_server(url: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2):  # noqa: S310
                return
        except (urllib.error.URLError, ConnectionResetError):
            time.sleep(0.5)
    raise TimeoutError(f"Streamlit at {url} not ready after {timeout}s")


def _wait_for_render(page: Page, timeout: int = 45_000) -> None:
    """Wait for the Streamlit shell and any active spinner to settle."""
    page.wait_for_selector(
        '[data-testid="stApp"]', state="visible", timeout=timeout
    )
    page.wait_for_selector(
        '[data-testid="stSidebarUserContent"]', state="visible", timeout=timeout
    )
    try:
        page.wait_for_function(
            "() => document.querySelectorAll('[data-testid=\"stSpinner\"]').length === 0",
            timeout=timeout,
        )
    except Exception:  # noqa: S110
        # Some solver-backed pages replace their spinner during rerenders. The
        # heading waits below still ensure the target content exists.
        pass
    page.wait_for_timeout(2_000)


def _write_screenshot(page: Page, filename: str) -> None:
    out = OUT_DIR / filename
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(out))
    print(f"wrote {out.relative_to(REPO_ROOT)}")


def _select_page(page: Page, label: str) -> None:
    sidebar = page.locator('[data-testid="stSidebarUserContent"]')
    radio = sidebar.locator(f'label:has-text("{label}")')
    radio.wait_for(state="visible", timeout=15_000)
    radio.click()
    _wait_for_render(page)


def _set_selectbox(page: Page, label: str, value: str) -> None:
    """Choose a Streamlit selectbox option by its visible label and value."""
    field_label = page.locator(f'label:has-text("{label}")').first
    field_label.wait_for(state="visible", timeout=15_000)
    combobox = field_label.locator("..").locator('[role="combobox"]')
    combobox.wait_for(state="visible", timeout=10_000)
    combobox.focus()
    combobox.click()
    try:
        page.wait_for_function(
            "() => document.querySelectorAll('[role=\"option\"]').length > 0",
            timeout=5_000,
        )
    except Exception:
        combobox.press("ArrowDown")
        page.wait_for_function(
            "() => document.querySelectorAll('[role=\"option\"]').length > 0",
            timeout=5_000,
        )

    options = page.locator('[role="option"]')
    for index in range(options.count()):
        option = options.nth(index)
        if value.casefold() in (option.text_content() or "").casefold():
            option.click()
            break
    else:
        available = options.all_text_contents()
        raise ValueError(f"Option {value!r} not found; available: {available}")
    _wait_for_render(page, timeout=60_000)


def _capture_page(
    page: Page,
    *,
    label: str,
    overview_filename: str,
    result_heading: str,
    result_filename: str,
) -> None:
    """Capture the page header and a viewport centered on its key result."""
    _select_page(page, label)

    if label == "System Configurator":
        # Use the same known-good combination as the documentation workflow so
        # the result view demonstrates a solved system rather than an arbitrary
        # first registry entry that may be incompatible with the default clock.
        _set_selectbox(page, "Select a converter part", "AD9680")
        _set_selectbox(page, "Select JESD Configuration Mode", "Mode: 136 ")

    title = page.get_by_role("heading", name=label, exact=True)
    title.wait_for(state="visible", timeout=60_000)
    title.scroll_into_view_if_needed()
    page.wait_for_timeout(500)
    _write_screenshot(page, overview_filename)

    heading = page.get_by_role("heading", name=result_heading, exact=True).last
    heading.wait_for(state="visible", timeout=60_000)
    heading.evaluate("el => el.scrollIntoView({block: 'start'})")
    page.wait_for_timeout(1_500)
    _write_screenshot(page, result_filename)


def _capture_overview(page: Page, *, label: str, filename: str) -> None:
    """Capture a short page whose inputs and result share one viewport."""
    _select_page(page, label)
    title = page.get_by_role("heading", name=label, exact=True)
    title.wait_for(state="visible", timeout=60_000)
    title.scroll_into_view_if_needed()
    page.wait_for_timeout(500)
    _write_screenshot(page, filename)


def main() -> None:
    """Launch Streamlit, capture the documentation screenshots, and stop it."""
    proc = subprocess.Popen(  # noqa: S603
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
            page = browser.new_page(viewport=VIEWPORT)
            page.goto(URL, wait_until="networkidle", timeout=60_000)
            _wait_for_render(page)

            captures = [
                {
                    "label": "JESD204 Mode Selector",
                    "overview_filename": "jesdmodeselector.png",
                    "result_heading": "JESD204 Modes",
                    "result_filename": "jesdmodeselector_modes.png",
                },
                {
                    "label": "Clock Configurator",
                    "overview_filename": "clockconfigurator.png",
                    "result_heading": "Diagram",
                    "result_filename": "clockconfigurator_diagram.png",
                },
                {
                    "label": "System Configurator",
                    "overview_filename": "systemconfigurator.png",
                    "result_heading": "Diagram",
                    "result_filename": "systemconfigurator_diagram.png",
                },
                {
                    "label": "ADF4030 System Designer",
                    "overview_filename": "adf4030systemdesigner.png",
                    "result_heading": "Diagram",
                    "result_filename": "adf4030systemdesigner_topology.png",
                },
            ]
            for capture in captures:
                _capture_page(page, **capture)

            _capture_overview(
                page,
                label="Basic JESD204 Calculator",
                filename="jesdbasiccalculator.png",
            )

            browser.close()
    finally:
        proc.terminate()
        proc.wait(timeout=10)


if __name__ == "__main__":
    main()
