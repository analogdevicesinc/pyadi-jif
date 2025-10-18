"""Tests for System Configurator page."""

import time

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class TestSystemConfigurator:
    """Test suite for System Configurator page."""

    def test_page_loads(self, driver: webdriver.Chrome, base_url: str) -> None:
        """Test that the System Configurator page loads correctly."""
        driver.get(f"{base_url}/system-configurator")
        time.sleep(1)

        # Check page title
        assert "System Configurator" in driver.page_source

        # Check for system settings section
        assert "System Settings" in driver.page_source

    def test_converter_part_selection(self, driver: webdriver.Chrome, base_url: str) -> None:
        """Test selecting a converter part."""
        driver.get(f"{base_url}/system-configurator")
        time.sleep(2)

        # Find and click the converter part selector
        part_selector = driver.find_element(By.XPATH, "//label[text()='Converter Part']/..")
        part_selector.click()
        time.sleep(1)

        # Select first part from dropdown
        parts = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        if parts:
            parts[0].click()
            time.sleep(2)

            # Verify converter configuration appears
            assert "Converter Configuration" in driver.page_source

    def test_clock_part_selection(self, driver: webdriver.Chrome, base_url: str) -> None:
        """Test selecting a clock part."""
        driver.get(f"{base_url}/system-configurator")
        time.sleep(2)

        # Find and click the clock part selector
        part_selector = driver.find_element(By.XPATH, "//label[text()='Clock Part']/..")
        part_selector.click()
        time.sleep(1)

        # Select first part from dropdown
        parts = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        if parts:
            parts[0].click()
            time.sleep(1)

    def test_fpga_dev_kit_selection(self, driver: webdriver.Chrome, base_url: str) -> None:
        """Test selecting an FPGA development kit."""
        driver.get(f"{base_url}/system-configurator")
        time.sleep(2)

        # Find and click the FPGA dev kit selector
        kit_selector = driver.find_element(
            By.XPATH, "//label[text()='FPGA Development Kit']/.."
        )
        kit_selector.click()
        time.sleep(1)

        # Select first kit from dropdown
        kits = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        if kits:
            kits[0].click()
            time.sleep(1)

    def test_reference_rate_input(self, driver: webdriver.Chrome, base_url: str) -> None:
        """Test changing reference rate."""
        driver.get(f"{base_url}/system-configurator")
        time.sleep(2)

        # Find reference rate input
        ref_rate_input = driver.find_element(
            By.XPATH, "//label[contains(text(), 'Reference Rate')]/..//input"
        )
        ref_rate_input.clear()
        ref_rate_input.send_keys("150000000")
        time.sleep(1)

        # Verify value changed
        assert ref_rate_input.get_attribute("value") == "150000000"

    def test_fpga_configuration_options(self, driver: webdriver.Chrome, base_url: str) -> None:
        """Test FPGA configuration options."""
        driver.get(f"{base_url}/system-configurator")
        time.sleep(2)

        # Verify FPGA Configuration section exists
        assert "FPGA Configuration" in driver.page_source

        # Verify various FPGA options are present
        assert "Reference Clock Constraint" in driver.page_source
        assert "System Clock Source" in driver.page_source
        assert "Transceiver PLL" in driver.page_source

    def test_solve_button_disabled_when_incomplete(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that solve button is disabled when configuration is incomplete."""
        driver.get(f"{base_url}/system-configurator")
        time.sleep(2)

        # Find solve button
        solve_button = driver.find_element(
            By.XPATH, "//button[contains(., 'Solve System Configuration')]"
        )

        # Verify button is disabled initially
        assert solve_button.get_attribute("disabled") is not None

    def test_navigation_in_sidebar(self, driver: webdriver.Chrome, base_url: str) -> None:
        """Test sidebar navigation."""
        driver.get(f"{base_url}/system-configurator")
        time.sleep(1)

        # Click on JESD Mode Selector in sidebar
        jesd_link = driver.find_element(By.XPATH, "//a[contains(., 'JESD204 Mode Selector')]")
        jesd_link.click()
        time.sleep(1)

        # Verify navigation
        assert "/jesd-mode-selector" in driver.current_url
        assert "JESD204 Mode Selector" in driver.page_source
