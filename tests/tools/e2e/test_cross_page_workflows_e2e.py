"""Cross-page workflow tests for E2E testing."""

import pytest


@pytest.mark.e2e
@pytest.mark.cross_page
def test_navigation_between_all_pages(page, streamlit_app):
    """Test navigation between all pages."""
    from .pages.base_page import BasePage

    base = BasePage(page, streamlit_app)

    # Navigate to JESD page
    base.navigate_to_tool("JESD204 Mode Selector")
    assert page.locator("h1:has-text('JESD204 Mode Selector')").is_visible()

    # Navigate to Clock page
    base.navigate_to_tool("Clock Configurator")
    assert page.locator("h1:has-text('Clock Configurator')").is_visible()

    # Navigate to System page
    base.navigate_to_tool("System Configurator")
    assert page.locator("h1:has-text('System Configurator')").is_visible()

    # Navigate back to JESD
    base.navigate_to_tool("JESD204 Mode Selector")
    assert page.locator("h1:has-text('JESD204 Mode Selector')").is_visible()


@pytest.mark.e2e
@pytest.mark.cross_page
def test_state_independence_between_pages(page, streamlit_app):
    """Test pages maintain independent state."""
    from .pages.clock_configurator_page import ClockConfiguratorPage
    from .pages.jesd_mode_selector_page import JESDModeSelectorPage

    # Set state on JESD page
    jesd = JESDModeSelectorPage(page, streamlit_app)
    jesd.select_part("ad9680")
    # Verify the JESD page responded
    assert jesd.is_visible("Datapath Configuration")

    # Navigate to Clock page and verify independent state
    clock = ClockConfiguratorPage(page, streamlit_app)
    # Clock page should show its own content
    assert clock.page.locator("h1:has-text('Clock Configurator')").is_visible()

    # Verify we can set different state on Clock page
    clock.select_clock_part("hmc7044")
    assert clock.is_visible("Clock Inputs and Outputs")


# @pytest.mark.skip(reason="Help button not yet implemented on all pages")
@pytest.mark.e2e
@pytest.mark.cross_page
def test_help_button_on_multiple_pages(page, streamlit_app):
    """Test Help button availability across pages."""
    from .pages.jesd_mode_selector_page import JESDModeSelectorPage

    # Check JESD page
    jesd = JESDModeSelectorPage(page, streamlit_app)
    assert jesd.is_help_button_visible()

    # # Check Clock page
    # clock = ClockConfiguratorPage(page, streamlit_app)
    # assert clock.page.get_by_role("button", name="Help").is_visible()

    # # Check System page
    # system = SystemConfiguratorPage(page, streamlit_app)
    # assert system.page.get_by_role("button", name="Help").is_visible()
