"""End-to-end tests for JESD204 Mode Selector tool."""

import pytest


@pytest.mark.e2e
@pytest.mark.jesd
@pytest.mark.smoke
def test_jesd_page_loads_successfully(jesd_page):
    """Test JESD Mode Selector page loads without errors."""
    assert jesd_page.page.title() is not None
    assert jesd_page.is_help_button_visible()
    assert jesd_page.is_visible("JESD204 Mode Selector")


@pytest.mark.e2e
@pytest.mark.jesd
def test_jesd_part_selection_updates_ui(jesd_page):
    """Test selecting different parts updates UI correctly."""
    # Select a part and verify the page responds
    jesd_page.select_part("ad9680")
    # Verify that datapath configuration is visible (content loaded)
    assert jesd_page.is_visible("Datapath Configuration")


@pytest.mark.e2e
@pytest.mark.jesd
def test_jesd_converter_rate_units_change(jesd_page):
    """Test changing converter rate units."""
    jesd_page.select_part("ad9680")
    for unit in ["Hz", "kHz", "MHz", "GHz"]:
        jesd_page.select_units(unit)
        # Wait for the converter rate label to appear with the new unit
        # (the label is dynamically generated and may take a moment to update)
        label_text = f"Converter Rate ({unit})"
        jesd_page.page.wait_for_selector(
            f"label:has-text({label_text!r})",
            state="visible",
            timeout=5000,
        )


@pytest.mark.e2e
@pytest.mark.jesd
def test_jesd_valid_modes_toggle(jesd_page):
    """Test toggling valid modes filter."""
    jesd_page.select_part("ad9680")
    # Toggle off
    jesd_page.toggle_valid_modes_only(False)
    # Verify the checkbox still exists
    assert jesd_page.is_visible("Show only valid modes")
    # Toggle on
    jesd_page.toggle_valid_modes_only(True)
    assert jesd_page.is_visible("Show only valid modes")


@pytest.mark.e2e
@pytest.mark.jesd
def test_jesd_multiple_parts_selection(jesd_page):
    """Test selecting multiple different parts."""
    parts = ["ad9680", "ad9144"]
    for part in parts:
        jesd_page.select_part(part)
        # Verify the page responded to the selection
        assert jesd_page.is_visible("Datapath Configuration")


@pytest.mark.e2e
@pytest.mark.jesd
def test_jesd_diagram_generation(jesd_page):
    """Test diagram is generated and displayed."""
    jesd_page.select_part("ad9680")
    jesd_page.expand_expander("Diagram")
    assert jesd_page.is_diagram_visible()


@pytest.mark.e2e
@pytest.mark.jesd
def test_jesd_converter_rate_input(jesd_page):
    """Test converter rate input with different units."""
    jesd_page.select_part("ad9680")
    jesd_page.select_units("GHz")
    jesd_page.set_converter_rate(1.0, "GHz")
    # Compare as float to handle formatting variations (1.0 vs 1.00)
    value = jesd_page.get_text_value("Converter Rate (GHz)")
    assert float(value) == 1.0
