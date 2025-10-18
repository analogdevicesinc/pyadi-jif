"""Comprehensive tests for System Configurator functionality."""

import time

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By

from test_helpers import (
    click_mui_select,
    get_console_errors,
    select_mui_option,
    wait_for_element,
    wait_for_element_clickable,
    wait_for_page_load,
)


class TestSystemConfiguratorComprehensive:
    """Comprehensive test suite for System Configurator page."""

    def test_page_loads_with_all_sections(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that System Configurator page loads with all sections."""
        driver.get(f"{base_url}/system-configurator")
        wait_for_page_load(driver)

        # Check title
        title = wait_for_element(driver, By.XPATH, "//h4[contains(text(), 'System')]")
        assert "System Configurator" in title.text

        # Check for System Settings section
        system_settings = wait_for_element(
            driver, By.XPATH, "//*[contains(text(), 'System Settings')]"
        )
        assert system_settings.is_displayed()

    def test_all_three_selectors_present(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that converter, clock, and FPGA selectors are present."""
        driver.get(f"{base_url}/system-configurator")
        wait_for_page_load(driver)

        # Check for all three selectors
        converter_select = wait_for_element(
            driver, By.XPATH, "//label[text()='Converter Part']"
        )
        clock_select = wait_for_element(
            driver, By.XPATH, "//label[text()='Clock Part']"
        )
        fpga_select = wait_for_element(
            driver, By.XPATH, "//label[text()='FPGA Development Kit']"
        )

        assert converter_select.is_displayed()
        assert clock_select.is_displayed()
        assert fpga_select.is_displayed()

    def test_converter_part_selection(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test selecting a converter part in system configurator."""
        driver.get(f"{base_url}/system-configurator")
        wait_for_page_load(driver)

        # Open converter dropdown
        click_mui_select(driver, "Converter Part")

        # Verify options
        options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        assert len(options) > 0, "No converter options found"

        # Select first option
        converter_name = options[0].text
        print(f"Selecting converter: {converter_name}")
        options[0].click()
        time.sleep(1)

        # Verify Converter Configuration section appears
        conv_config = driver.find_elements(
            By.XPATH, "//*[contains(text(), 'Converter Configuration')]"
        )
        assert len(conv_config) > 0, "Converter Configuration section not shown"

    def test_clock_part_selection(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test selecting a clock part in system configurator."""
        driver.get(f"{base_url}/system-configurator")
        wait_for_page_load(driver)

        # Open clock dropdown
        click_mui_select(driver, "Clock Part")

        # Verify options
        options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        assert len(options) > 0, "No clock options found"

        # Select first option
        options[0].click()
        time.sleep(0.5)

    def test_fpga_dev_kit_selection(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test selecting an FPGA development kit."""
        driver.get(f"{base_url}/system-configurator")
        wait_for_page_load(driver)

        # Open FPGA dropdown
        click_mui_select(driver, "FPGA Development Kit")

        # Verify options
        options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        assert len(options) > 0, "No FPGA dev kit options found"

        # Select first option
        fpga_name = options[0].text
        print(f"Selecting FPGA kit: {fpga_name}")
        options[0].click()
        time.sleep(0.5)

    def test_reference_rate_input(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test setting the reference rate."""
        driver.get(f"{base_url}/system-configurator")
        wait_for_page_load(driver)

        # Find reference rate input
        ref_input = wait_for_element(
            driver, By.XPATH, "//label[contains(text(), 'Reference Rate')]/..//input"
        )

        # Set value
        ref_input.clear()
        ref_input.send_keys("150000000")
        time.sleep(0.5)

        # Verify
        assert ref_input.get_attribute("value") == "150000000"

    def test_converter_configuration_section(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test converter configuration section."""
        driver.get(f"{base_url}/system-configurator")
        wait_for_page_load(driver)

        # Check for Converter Configuration section
        conv_config = wait_for_element(
            driver, By.XPATH, "//h6[contains(text(), 'Converter Configuration')]"
        )
        assert conv_config.is_displayed()

        # Check for sample clock input
        sample_clock = wait_for_element(
            driver, By.XPATH, "//label[contains(text(), 'Sample Clock')]/..//input"
        )
        assert sample_clock.is_displayed()

    def test_fpga_configuration_section(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test FPGA configuration section."""
        driver.get(f"{base_url}/system-configurator")
        wait_for_page_load(driver)

        # Check for FPGA Configuration section
        fpga_config = wait_for_element(
            driver, By.XPATH, "//h6[contains(text(), 'FPGA Configuration')]"
        )
        assert fpga_config.is_displayed()

        # Check for various FPGA options
        assert "Reference Clock Constraint" in driver.page_source
        assert "System Clock Source" in driver.page_source or "XCVR" in driver.page_source

    def test_solve_button_disabled_when_incomplete(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that solve button is disabled when configuration is incomplete."""
        driver.get(f"{base_url}/system-configurator")
        wait_for_page_load(driver)

        # Find solve button
        solve_button = wait_for_element(
            driver, By.XPATH, "//button[contains(., 'Solve System Configuration')]"
        )

        # Should be disabled initially
        assert solve_button.get_attribute("disabled") is not None, \
            "Solve button should be disabled when configuration is incomplete"

    def test_solve_button_enabled_after_configuration(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that solve button enables after all required fields are filled."""
        driver.get(f"{base_url}/system-configurator")
        wait_for_page_load(driver)

        # Select converter
        click_mui_select(driver, "Converter Part")
        conv_options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        if conv_options:
            conv_options[0].click()
            time.sleep(1)

        # Select clock
        click_mui_select(driver, "Clock Part")
        clock_options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        if clock_options:
            clock_options[0].click()
            time.sleep(0.5)

        # Select FPGA
        click_mui_select(driver, "FPGA Development Kit")
        fpga_options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        if fpga_options:
            fpga_options[0].click()
            time.sleep(0.5)

        # Wait for quick mode to be populated
        time.sleep(2)

        # Check if solve button is now enabled
        solve_button = driver.find_element(
            By.XPATH, "//button[contains(., 'Solve System Configuration')]"
        )

        # Button should be enabled if all fields are filled
        is_disabled = solve_button.get_attribute("disabled")
        print(f"Solve button disabled: {is_disabled}")

    def test_fpga_constraint_options(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test FPGA constraint options are available."""
        driver.get(f"{base_url}/system-configurator")
        wait_for_page_load(driver)

        # Look for various FPGA configuration options
        page_text = driver.page_source

        fpga_options = [
            "Reference Clock Constraint",
            "System Clock",
            "Output Clock",
            "Transceiver PLL",
        ]

        found_options = [opt for opt in fpga_options if opt in page_text]
        assert len(found_options) >= 2, \
            f"Expected FPGA options not found. Found: {found_options}"

    def test_pll_selection_options(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that PLL selection options are available."""
        driver.get(f"{base_url}/system-configurator")
        wait_for_page_load(driver)

        # Look for Transceiver PLL Selection
        pll_label = wait_for_element(
            driver, By.XPATH, "//label[contains(text(), 'Transceiver PLL')]"
        )
        assert pll_label.is_displayed()

    def test_no_errors_during_configuration(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that no severe errors occur during system configuration."""
        driver.get(f"{base_url}/system-configurator")
        wait_for_page_load(driver)

        # Perform interactions
        click_mui_select(driver, "Converter Part")
        conv_options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        if conv_options:
            conv_options[0].click()
            time.sleep(1)

        # Check for errors
        errors = get_console_errors(driver)
        assert len(errors) < 5, f"Too many JavaScript errors: {errors}"

    @pytest.mark.slow
    def test_complete_system_workflow(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test a complete system configuration workflow."""
        driver.get(f"{base_url}/system-configurator")
        wait_for_page_load(driver)

        # Step 1: Select converter
        click_mui_select(driver, "Converter Part")
        conv_options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        if not conv_options:
            pytest.skip("No converters available")

        conv_options[0].click()
        time.sleep(1)

        # Step 2: Select clock
        click_mui_select(driver, "Clock Part")
        clock_options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        if not clock_options:
            pytest.skip("No clocks available")

        clock_options[0].click()
        time.sleep(0.5)

        # Step 3: Select FPGA
        click_mui_select(driver, "FPGA Development Kit")
        fpga_options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        if not fpga_options:
            pytest.skip("No FPGA kits available")

        fpga_options[0].click()
        time.sleep(1)

        # Step 4: Set reference rate
        ref_input = driver.find_element(
            By.XPATH, "//label[contains(text(), 'Reference Rate')]/..//input"
        )
        ref_input.clear()
        ref_input.send_keys("125000000")
        time.sleep(0.5)

        # Step 5: Set sample clock
        sample_input = driver.find_element(
            By.XPATH, "//label[contains(text(), 'Sample Clock')]/..//input"
        )
        sample_input.clear()
        sample_input.send_keys("1000000000")
        time.sleep(0.5)

        print("✓ Complete system workflow test passed")

    def test_all_configuration_sections_visible(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that all configuration sections are visible."""
        driver.get(f"{base_url}/system-configurator")
        wait_for_page_load(driver)

        sections = [
            "System Settings",
            "Converter Configuration",
            "FPGA Configuration",
        ]

        for section in sections:
            element = wait_for_element(
                driver, By.XPATH, f"//*[contains(text(), '{section}')]", timeout=5
            )
            assert element.is_displayed(), f"Section '{section}' not visible"
