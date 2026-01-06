"""Pytest configuration and fixtures for E2E tests."""

import os
from pathlib import Path

import pytest
from playwright.sync_api import BrowserContext, Page


@pytest.fixture(scope="session")
def streamlit_app():
    """Start Streamlit app and return base URL."""
    from .fixtures.streamlit_app import start_streamlit_app, stop_streamlit_app

    process = start_streamlit_app()
    base_url = "http://localhost:8501"

    yield base_url

    stop_streamlit_app(process)


@pytest.fixture(scope="function")
def page(context: BrowserContext):
    """Create new page for each test."""
    page = context.new_page()
    page.set_default_timeout(10000)
    yield page
    page.close()


@pytest.fixture
def jesd_page(page: Page, streamlit_app: str):
    """JESD Mode Selector page object."""
    from .pages.jesd_mode_selector_page import JESDModeSelectorPage

    return JESDModeSelectorPage(page, streamlit_app)


@pytest.fixture
def clock_page(page: Page, streamlit_app: str):
    """Clock Configurator page object."""
    from .pages.clock_configurator_page import ClockConfiguratorPage

    return ClockConfiguratorPage(page, streamlit_app)


@pytest.fixture
def system_page(page: Page, streamlit_app: str):
    """System Configurator page object."""
    from .pages.system_configurator_page import SystemConfiguratorPage

    return SystemConfiguratorPage(page, streamlit_app)


@pytest.fixture
def visual_regression():
    """Visual regression testing helper."""
    from .helpers.visual_regression import VisualRegression

    baseline_dir = Path(__file__).parent / "baselines"
    return VisualRegression(baseline_dir)


def pytest_addoption(parser):
    """Add custom CLI options."""
    parser.addoption(
        "--update-baselines",
        action="store_true",
        default=False,
        help="Update visual regression baselines",
    )


def pytest_configure(config):
    """Register custom markers and configure timeouts."""
    # Set timeout for e2e tests (30 seconds per test, 120 seconds for slow tests)
    # Can be overridden via --timeout command line option
    timeout_value = os.getenv("PYTEST_TIMEOUT", "30")
    config.option.timeout = int(timeout_value)

    config.addinivalue_line("markers", "e2e: mark test as an end-to-end test")
    config.addinivalue_line(
        "markers", "jesd: mark test as related to JESD Mode Selector"
    )
    config.addinivalue_line(
        "markers", "clock: mark test as related to Clock Configurator"
    )
    config.addinivalue_line(
        "markers", "system: mark test as related to System Configurator"
    )
    config.addinivalue_line("markers", "cross_page: mark test as cross-page workflow")
    config.addinivalue_line("markers", "visual: mark test as visual regression test")
    config.addinivalue_line("markers", "smoke: mark test as smoke test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line(
        "markers", "timeout=N: set test timeout in seconds (overrides global timeout)"
    )
