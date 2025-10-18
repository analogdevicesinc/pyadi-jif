"""Tests for JESD Mode Selector page."""

import time

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class TestJESDModeSelector:
    """Test suite for JESD Mode Selector page."""

    def test_page_loads(self, driver: webdriver.Chrome, base_url: str) -> None:
        """Test that the JESD Mode Selector page loads correctly."""
        driver.get(f"{base_url}/jesd-mode-selector")
        time.sleep(1)

        # Check page title
        assert "JESD204 Mode Selector" in driver.page_source

        # Check for help button
        help_button = driver.find_element(By.XPATH, "//button[contains(., 'Help')]")
        assert help_button is not None

    def test_part_selection(self, driver: webdriver.Chrome, base_url: str) -> None:
        """Test selecting a converter part."""
        driver.get(f"{base_url}/jesd-mode-selector")
        time.sleep(2)

        # Find and click the part selector
        part_selector = driver.find_element(By.XPATH, "//label[text()='Select a Part']/..")
        part_selector.click()
        time.sleep(1)

        # Select first part from dropdown
        parts = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        if parts:
            parts[0].click()
            time.sleep(2)

            # Verify datapath configuration appears
            assert "Datapath Configuration" in driver.page_source

    def test_help_dialog(self, driver: webdriver.Chrome, base_url: str) -> None:
        """Test opening and closing the help dialog."""
        driver.get(f"{base_url}/jesd-mode-selector")
        time.sleep(1)

        # Click help button
        help_button = driver.find_element(By.XPATH, "//button[contains(., 'Help')]")
        help_button.click()
        time.sleep(1)

        # Check dialog appears
        assert "About JESD204 Mode Selector" in driver.page_source

        # Close dialog (click outside or press escape)
        driver.find_element(By.TAG_NAME, "body").click()
        time.sleep(1)

    def test_converter_rate_input(self, driver: webdriver.Chrome, base_url: str) -> None:
        """Test changing converter rate."""
        driver.get(f"{base_url}/jesd-mode-selector")
        time.sleep(2)

        # Select a part first
        part_selector = driver.find_element(By.XPATH, "//label[text()='Select a Part']/..")
        part_selector.click()
        time.sleep(1)

        parts = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        if parts:
            parts[0].click()
            time.sleep(2)

            # Find converter rate input
            rate_inputs = driver.find_elements(
                By.XPATH, "//label[contains(text(), 'Converter Rate')]/..//input"
            )
            if rate_inputs:
                rate_input = rate_inputs[0]
                rate_input.clear()
                rate_input.send_keys("2")
                time.sleep(1)

                # Verify sample rate is updated
                assert "Sample Rate" in driver.page_source

    def test_navigation_to_other_pages(self, driver: webdriver.Chrome, base_url: str) -> None:
        """Test navigation from JESD Mode Selector to other pages."""
        driver.get(f"{base_url}/jesd-mode-selector")
        time.sleep(1)

        # Click on Clock Configurator in sidebar
        clock_link = driver.find_element(By.XPATH, "//a[contains(., 'Clock Configurator')]")
        clock_link.click()
        time.sleep(1)

        # Verify navigation
        assert "/clock-configurator" in driver.current_url
        assert "Clock Configurator" in driver.page_source
