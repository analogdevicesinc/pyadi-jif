"""Tests for Clock Configurator page."""

import time

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class TestClockConfigurator:
    """Test suite for Clock Configurator page."""

    def test_page_loads(self, driver: webdriver.Chrome, base_url: str) -> None:
        """Test that the Clock Configurator page loads correctly."""
        driver.get(f"{base_url}/clock-configurator")
        time.sleep(1)

        # Check page title
        assert "Clock Configurator" in driver.page_source

        # Check for part selector
        assert "Select a Part" in driver.page_source

    def test_part_selection(self, driver: webdriver.Chrome, base_url: str) -> None:
        """Test selecting a clock part."""
        driver.get(f"{base_url}/clock-configurator")
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

            # Verify configuration sections appear
            assert "Clock Inputs and Outputs" in driver.page_source

    def test_reference_clock_input(self, driver: webdriver.Chrome, base_url: str) -> None:
        """Test changing reference clock value."""
        driver.get(f"{base_url}/clock-configurator")
        time.sleep(2)

        # Select a part
        part_selector = driver.find_element(By.XPATH, "//label[text()='Select a Part']/..")
        part_selector.click()
        time.sleep(1)

        parts = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        if parts:
            parts[0].click()
            time.sleep(2)

            # Find reference clock input
            ref_clock_input = driver.find_element(
                By.XPATH, "//label[contains(text(), 'Reference Clock')]/..//input"
            )
            ref_clock_input.clear()
            ref_clock_input.send_keys("100000000")
            time.sleep(1)

            # Verify value changed
            assert ref_clock_input.get_attribute("value") == "100000000"

    def test_add_output_clock(self, driver: webdriver.Chrome, base_url: str) -> None:
        """Test adding an output clock."""
        driver.get(f"{base_url}/clock-configurator")
        time.sleep(2)

        # Select a part
        part_selector = driver.find_element(By.XPATH, "//label[text()='Select a Part']/..")
        part_selector.click()
        time.sleep(1)

        parts = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        if parts:
            parts[0].click()
            time.sleep(2)

            # Count initial outputs
            initial_outputs = len(
                driver.find_elements(By.XPATH, "//label[contains(text(), 'Output Clock')]")
            )

            # Click add output button
            add_button = driver.find_element(By.XPATH, "//button[contains(., 'Add Output')]")
            add_button.click()
            time.sleep(1)

            # Verify output was added
            final_outputs = len(
                driver.find_elements(By.XPATH, "//label[contains(text(), 'Output Clock')]")
            )
            assert final_outputs > initial_outputs

    def test_solve_configuration(self, driver: webdriver.Chrome, base_url: str) -> None:
        """Test solving clock configuration."""
        driver.get(f"{base_url}/clock-configurator")
        time.sleep(2)

        # Select a part
        part_selector = driver.find_element(By.XPATH, "//label[text()='Select a Part']/..")
        part_selector.click()
        time.sleep(1)

        parts = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        if parts:
            parts[0].click()
            time.sleep(2)

            # Click solve button
            solve_button = driver.find_element(
                By.XPATH, "//button[contains(., 'Solve Configuration')]"
            )
            solve_button.click()
            time.sleep(3)

            # Wait for result
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//*[contains(text(), 'Found Configuration')]")
                )
            )

            # Verify result appears
            assert "Found Configuration" in driver.page_source
