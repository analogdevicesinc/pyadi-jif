"""Visual regression tests for E2E testing."""

import pytest


@pytest.mark.e2e
@pytest.mark.visual
def test_jesd_page_visual(jesd_page, visual_regression, request):
    """Test JESD Mode Selector page visual appearance."""
    jesd_page.select_part("ad9680")
    # Just take a screenshot of the loaded page
    screenshot = jesd_page.take_screenshot("jesd_full")
    update = request.config.getoption("--update-baselines", False)

    matches, diff = visual_regression.compare_screenshot(
        screenshot,
        "jesd_mode_selector/default.png",
        threshold=0.05,
        update_baseline=update,
    )

    if not update:
        assert matches, f"Visual diff: {diff*100:.2f}%"


@pytest.mark.e2e
@pytest.mark.visual
def test_clock_page_visual(clock_page, visual_regression, request):
    """Test Clock Configurator page visual appearance."""
    clock_page.select_clock_part("hmc7044")
    # Just take a screenshot of the loaded page
    screenshot = clock_page.take_screenshot("clock_full")
    update = request.config.getoption("--update-baselines", False)

    matches, diff = visual_regression.compare_screenshot(
        screenshot,
        "clock_configurator/default.png",
        threshold=0.05,
        update_baseline=update,
    )

    if not update:
        assert matches, f"Visual diff: {diff*100:.2f}%"


@pytest.mark.e2e
@pytest.mark.visual
def test_system_page_visual(system_page, visual_regression, request):
    """Test System Configurator page visual appearance."""
    system_page.select_converter("ad9680")
    system_page.select_clock("hmc7044")
    system_page.select_fpga_kit("zc706")

    # Just take a screenshot of the loaded page
    screenshot = system_page.take_screenshot("system_full")
    update = request.config.getoption("--update-baselines", False)

    matches, diff = visual_regression.compare_screenshot(
        screenshot,
        "system_configurator/default.png",
        threshold=0.05,
        update_baseline=update,
    )

    if not update:
        assert matches, f"Visual diff: {diff*100:.2f}%"
