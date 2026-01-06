"""End-to-end tests for Clock Configurator tool."""

import pytest


@pytest.mark.e2e
@pytest.mark.clock
@pytest.mark.smoke
def test_clock_page_loads_successfully(clock_page):
    """Test Clock Configurator page loads without errors."""
    assert clock_page.is_visible("Clock Configurator")
    assert clock_page.is_visible("Select a part")


@pytest.mark.e2e
@pytest.mark.clock
def test_clock_part_selection_updates_ui(clock_page):
    """Test selecting different clock chips updates UI."""
    clock_page.select_clock_part("hmc7044")
    # Verify the page responded by checking if content became visible
    assert clock_page.is_visible("Clock Inputs and Outputs")


@pytest.mark.e2e
@pytest.mark.clock
def test_clock_reference_configuration(clock_page):
    """Test configuring reference clock."""
    clock_page.select_clock_part("hmc7044")
    clock_page.set_reference_clock(125000000)
    # Verify the reference clock section is visible
    assert clock_page.is_visible("Reference Clock")


@pytest.mark.e2e
@pytest.mark.clock
def test_clock_internal_params(clock_page):
    """Test internal parameter configuration."""
    clock_page.select_clock_part("hmc7044")
    clock_page.expand_internal_config()
    assert clock_page.is_internal_config_visible()


@pytest.mark.e2e
@pytest.mark.clock
def test_clock_multiple_parts_selection(clock_page):
    """Test selecting multiple different clock chips."""
    parts = ["hmc7044", "ad9528"]
    for part in parts:
        clock_page.select_clock_part(part)
        # Verify the page responded to selection
        assert clock_page.is_visible("Clock Inputs and Outputs")


@pytest.mark.e2e
@pytest.mark.clock
def test_clock_reference_range(clock_page):
    """Test setting different reference clock values."""
    clock_page.select_clock_part("hmc7044")
    frequencies = [100000000, 125000000, 156250000]
    for freq in frequencies:
        clock_page.set_reference_clock(freq)
        # Verify the widget is still visible
        assert clock_page.is_visible("Reference Clock")


@pytest.mark.e2e
@pytest.mark.clock
def test_clock_page_layout(clock_page):
    """Test clock page has expected sections."""
    clock_page.select_clock_part("hmc7044")
    assert clock_page.is_visible("Select a part")
    assert clock_page.is_visible("Reference Clock")
    assert clock_page.is_visible("Clock Inputs and Outputs")
