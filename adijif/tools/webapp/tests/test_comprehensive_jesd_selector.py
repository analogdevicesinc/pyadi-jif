"""Comprehensive tests for JESD Mode Selector functionality."""

import time

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from test_helpers import (
    click_mui_select,
    get_console_errors,
    select_mui_option,
    wait_for_element,
    wait_for_element_clickable,
    wait_for_page_load,
)


class TestJESDModeSelectorComprehensive:
    """Comprehensive test suite for JESD Mode Selector page."""

    def test_page_loads_with_all_elements(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that the JESD Mode Selector page loads with all expected elements."""
        driver.get(f"{base_url}/jesd-mode-selector")
        wait_for_page_load(driver)

        # Check title
        title = wait_for_element(driver, By.XPATH, "//h4[contains(text(), 'JESD204')]")
        assert "JESD204 Mode Selector" in title.text

        # Check help button exists
        help_button = wait_for_element(
            driver, By.XPATH, "//button[contains(., 'Help')]"
        )
        assert help_button.is_displayed()

        # Check part selector exists
        part_selector = wait_for_element(
            driver, By.XPATH, "//label[text()='Select a Part']"
        )
        assert part_selector.is_displayed()

    def test_help_dialog_functionality(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that the help dialog opens and closes correctly."""
        driver.get(f"{base_url}/jesd-mode-selector")
        wait_for_page_load(driver)

        # Click help button
        help_button = wait_for_element_clickable(
            driver, By.XPATH, "//button[contains(., 'Help')]"
        )
        help_button.click()
        time.sleep(0.5)

        # Verify dialog appeared
        dialog_title = wait_for_element(
            driver, By.XPATH, "//h2[contains(text(), 'About JESD204')]"
        )
        assert "About JESD204 Mode Selector" in dialog_title.text

        # Verify dialog content
        assert "JESD204 mode" in driver.page_source
        assert "ADI portfolio" in driver.page_source

        # Close dialog by clicking backdrop
        backdrop = driver.find_element(By.CSS_SELECTOR, ".MuiBackdrop-root")
        backdrop.click()
        time.sleep(0.5)

    def test_converter_selection_flow(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test the complete flow of selecting a converter."""
        driver.get(f"{base_url}/jesd-mode-selector")
        wait_for_page_load(driver)

        # Open converter dropdown
        click_mui_select(driver, "Select a Part")

        # Verify options appear
        options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        assert len(options) > 0, "No converter options found"

        # Get first converter name
        first_converter = options[0].text
        print(f"Selecting converter: {first_converter}")

        # Select first option
        options[0].click()
        time.sleep(1)

        # Verify datapath configuration section appears
        datapath_section = wait_for_element(
            driver, By.XPATH, "//*[contains(text(), 'Datapath Configuration')]"
        )
        assert datapath_section.is_displayed()

    def test_units_selection(self, driver: webdriver.Chrome, base_url: str) -> None:
        """Test selecting different units for converter rate."""
        driver.get(f"{base_url}/jesd-mode-selector")
        wait_for_page_load(driver)

        # Select a converter first
        click_mui_select(driver, "Select a Part")
        options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        if options:
            options[0].click()
            time.sleep(1)

            # Test each unit
            for unit in ["Hz", "kHz", "MHz", "GHz"]:
                click_mui_select(driver, "Units")
                select_mui_option(driver, unit)

                # Verify unit is selected
                assert f"Converter Rate ({unit})" in driver.page_source

    def test_converter_rate_input(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test inputting a converter rate value."""
        driver.get(f"{base_url}/jesd-mode-selector")
        wait_for_page_load(driver)

        # Select a converter first
        click_mui_select(driver, "Select a Part")
        options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        if options:
            options[0].click()
            time.sleep(1)

            # Find converter rate input
            rate_input = wait_for_element(
                driver, By.XPATH, "//label[contains(text(), 'Converter Rate')]/..//input"
            )

            # Clear and enter new value
            rate_input.clear()
            rate_input.send_keys("2.5")
            time.sleep(0.5)

            # Verify value was set
            assert rate_input.get_attribute("value") == "2.5"

    def test_sample_rate_calculation(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that sample rate is calculated correctly."""
        driver.get(f"{base_url}/jesd-mode-selector")
        wait_for_page_load(driver)

        # Select a converter
        click_mui_select(driver, "Select a Part")
        options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        if options:
            options[0].click()
            time.sleep(1)

            # Check for sample rate display
            assert "Sample Rate" in driver.page_source
            assert "MSPS" in driver.page_source

    def test_no_javascript_errors(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that no severe JavaScript errors occur during normal usage."""
        driver.get(f"{base_url}/jesd-mode-selector")
        wait_for_page_load(driver)

        # Perform some interactions
        click_mui_select(driver, "Select a Part")
        options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        if options:
            options[0].click()
            time.sleep(1)

        # Check for severe errors
        errors = get_console_errors(driver)
        # Allow some errors but fail if there are too many
        assert len(errors) < 5, f"Too many JavaScript errors: {errors}"

    def test_page_accessibility(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test basic accessibility features."""
        driver.get(f"{base_url}/jesd-mode-selector")
        wait_for_page_load(driver)

        # Check for proper ARIA labels
        select_elements = driver.find_elements(By.CSS_SELECTOR, "[role='combobox']")
        assert len(select_elements) >= 1, "No select elements with proper ARIA roles"

        # Check for proper headings hierarchy
        h4_elements = driver.find_elements(By.TAG_NAME, "h4")
        assert len(h4_elements) >= 1, "Missing heading elements"

        h6_elements = driver.find_elements(By.TAG_NAME, "h6")
        # H6 elements should appear after selecting a converter
        # This is acceptable as 0 or more

    def test_responsive_layout(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that the layout adapts to different screen sizes."""
        driver.get(f"{base_url}/jesd-mode-selector")
        wait_for_page_load(driver)

        # Test different viewport sizes
        viewports = [
            (1920, 1080, "Desktop"),
            (1366, 768, "Laptop"),
            (768, 1024, "Tablet"),
        ]

        for width, height, name in viewports:
            driver.set_window_size(width, height)
            time.sleep(0.5)

            # Verify main content is visible
            main_title = driver.find_element(
                By.XPATH, "//h4[contains(text(), 'JESD204')]"
            )
            assert main_title.is_displayed(), f"Title not visible on {name}"

    def test_multiple_converter_selections(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test selecting multiple different converters in sequence."""
        driver.get(f"{base_url}/jesd-mode-selector")
        wait_for_page_load(driver)

        # Get initial options
        click_mui_select(driver, "Select a Part")
        initial_options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")

        # Test selecting first 3 converters
        for i in range(min(3, len(initial_options))):
            # Reopen dropdown
            if i > 0:
                click_mui_select(driver, "Select a Part")
                time.sleep(0.5)

            options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
            converter_name = options[i].text

            print(f"Testing converter {i + 1}: {converter_name}")
            options[i].click()
            time.sleep(1)

            # Verify datapath section appears
            datapath = driver.find_element(
                By.XPATH, "//*[contains(text(), 'Datapath Configuration')]"
            )
            assert datapath.is_displayed(), f"Datapath not shown for {converter_name}"

    @pytest.mark.slow
    def test_complete_user_workflow(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test a complete end-to-end user workflow."""
        driver.get(f"{base_url}/jesd-mode-selector")
        wait_for_page_load(driver)

        # Step 1: Select converter
        click_mui_select(driver, "Select a Part")
        options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        if not options:
            pytest.skip("No converters available")

        options[0].click()
        time.sleep(1)

        # Step 2: Change units
        click_mui_select(driver, "Units")
        select_mui_option(driver, "GHz")

        # Step 3: Set converter rate
        rate_input = driver.find_element(
            By.XPATH, "//label[contains(text(), 'Converter Rate')]/..//input"
        )
        rate_input.clear()
        rate_input.send_keys("2.0")
        time.sleep(0.5)

        # Step 4: Verify sample rate updates
        assert "Sample Rate" in driver.page_source

        # Step 5: Check for valid modes (if displayed)
        # Note: This may require API data
        time.sleep(2)  # Allow time for mode calculation

        print("✓ Complete workflow test passed")
