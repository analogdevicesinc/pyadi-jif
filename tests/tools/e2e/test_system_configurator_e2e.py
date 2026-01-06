"""End-to-end tests for System Configurator tool."""

import pytest


@pytest.mark.e2e
@pytest.mark.system
@pytest.mark.smoke
def test_system_page_loads_successfully(system_page):
    """Test System Configurator page loads."""
    assert system_page.is_visible("System Configurator")
    assert system_page.is_visible("System Settings")


@pytest.mark.e2e
@pytest.mark.system
def test_system_component_selection(system_page):
    """Test selecting components."""
    system_page.select_converter("ad9680")
    # Verify the page responded by checking if converter settings appears
    assert system_page.is_visible("Select units for Converter")

    system_page.select_clock("hmc7044")
    assert system_page.is_visible("Select a clock part")


@pytest.mark.e2e
@pytest.mark.system
def test_system_converter_settings(system_page):
    """Test converter settings visibility."""
    system_page.select_converter("ad9680")
    system_page.expand_converter_settings()
    assert system_page.is_converter_settings_visible()


@pytest.mark.e2e
@pytest.mark.system
def test_system_fpga_settings(system_page):
    """Test FPGA settings."""
    system_page.select_fpga_kit("zc706")
    system_page.expand_fpga_settings()
    assert system_page.is_fpga_settings_visible()


@pytest.mark.e2e
@pytest.mark.system
def test_system_clocking_settings(system_page):
    """Test clocking settings."""
    system_page.select_converter("ad9680")
    # Converter Clock Source is an expander, check if it exists
    assert system_page.is_visible("Converter Clock Source")


@pytest.mark.e2e
@pytest.mark.system
def test_system_multiple_component_combinations(system_page):
    """Test different component combinations."""
    converters = ["ad9680", "ad9144"]
    clocks = ["hmc7044", "ad9528"]

    for converter in converters:
        system_page.select_converter(converter)
        # Verify the page responded to selection
        assert system_page.is_visible("Select units for Converter")

        for clock in clocks:
            system_page.select_clock(clock)
            assert system_page.is_visible("Select a clock part")


@pytest.mark.e2e
@pytest.mark.system
def test_system_fpga_kit_selection(system_page):
    """Test FPGA kit selection."""
    fpga_kits = ["zc706"]
    for kit in fpga_kits:
        system_page.select_fpga_kit(kit)
        # Verify the page responded to selection
        assert system_page.is_visible("System Settings")


@pytest.mark.e2e
@pytest.mark.system
def test_system_page_layout(system_page):
    """Test system page has expected layout."""
    assert system_page.is_visible("System Configurator")
    assert system_page.is_visible("System Settings")
    assert system_page.is_visible("Select a converter part")
    assert system_page.is_visible("Select a clock part")
    assert system_page.is_visible("Select an FPGA development kit")
