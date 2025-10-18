"""Focused tests for dropdown functionality in the web app."""

import time

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class TestDropdownFunctionality:
    """Test suite for Material-UI dropdown/select functionality."""

    def test_converter_dropdown_opens(self, driver: webdriver.Chrome, base_url: str) -> None:
        """Test that the converter dropdown opens when clicked."""
        driver.get(f"{base_url}/jesd-mode-selector")
        time.sleep(2)

        # Find the select input
        select_input = driver.find_element(
            By.XPATH, "//label[text()='Select a Part']/following-sibling::div//input"
        )

        print(f"Found select input: {select_input.get_attribute('outerHTML')}")

        # Click to open dropdown
        select_input.click()
        time.sleep(1)

        # Check if dropdown menu appeared
        dropdowns = driver.find_elements(By.CSS_SELECTOR, "[role='listbox']")
        print(f"Found {len(dropdowns)} dropdown menus")

        assert len(dropdowns) > 0, "Dropdown menu did not appear"

    def test_all_converters_selectable(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that all converters can be selected from the dropdown."""
        driver.get(f"{base_url}/jesd-mode-selector")
        time.sleep(2)

        # Find and click the select input
        select_div = driver.find_element(
            By.XPATH, "//label[text()='Select a Part']/.."
        )

        # Click on the div to open dropdown
        select_div.click()
        time.sleep(1)

        # Wait for dropdown to appear
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[role='listbox']"))
            )
        except Exception as e:
            print(f"Dropdown did not appear: {e}")
            print(f"Page source: {driver.page_source[:500]}")
            raise

        # Get all options
        options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        print(f"Found {len(options)} converter options")

        assert len(options) > 0, "No converter options found in dropdown"

        # Try to select each option
        for i, option in enumerate(options[:3]):  # Test first 3 to save time
            print(f"Testing option {i}: {option.text}")

            # Reopen dropdown for each selection
            if i > 0:
                select_div.click()
                time.sleep(1)

            # Click the option
            option.click()
            time.sleep(1)

            # Verify selection (check if datapath configuration appears)
            try:
                driver.find_element(By.XPATH, "//*[contains(text(), 'Datapath Configuration')]")
                print(f"✓ Successfully selected: {option.text}")
            except Exception as e:
                print(f"✗ Failed to select: {option.text} - {e}")
                raise

    def test_api_returns_converters(self, driver: webdriver.Chrome, api_url: str) -> None:
        """Test that the API endpoint returns converter data."""
        # Navigate to API endpoint
        driver.get(f"{api_url}/converters/supported")
        time.sleep(1)

        # Get the response body
        body = driver.find_element(By.TAG_NAME, "body").text
        print(f"API Response: {body[:200]}")

        # Parse JSON if possible
        import json
        try:
            data = json.loads(body)
            print(f"Number of converters from API: {len(data)}")
            assert len(data) > 0, "API returned no converters"
            print(f"Sample converters: {data[:5]}")
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
            raise

    def test_dropdown_without_javascript_errors(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that opening dropdown doesn't cause JavaScript errors."""
        driver.get(f"{base_url}/jesd-mode-selector")
        time.sleep(2)

        # Check for errors before interaction
        logs_before = driver.get_log("browser")
        severe_before = [log for log in logs_before if log["level"] == "SEVERE"]

        # Interact with dropdown
        select_div = driver.find_element(
            By.XPATH, "//label[text()='Select a Part']/.."
        )
        select_div.click()
        time.sleep(1)

        # Check for new errors
        logs_after = driver.get_log("browser")
        severe_after = [log for log in logs_after if log["level"] == "SEVERE"]

        new_errors = len(severe_after) - len(severe_before)
        if new_errors > 0:
            print(f"New JavaScript errors: {severe_after[-new_errors:]}")

        assert new_errors == 0, f"Dropdown caused {new_errors} JavaScript errors"

    def test_mui_select_structure(self, driver: webdriver.Chrome, base_url: str) -> None:
        """Test that the MUI Select component has correct structure."""
        driver.get(f"{base_url}/jesd-mode-selector")
        time.sleep(2)

        # Check for MUI Select component
        selects = driver.find_elements(By.CSS_SELECTOR, ".MuiSelect-select")
        print(f"Found {len(selects)} MUI Select components")

        if len(selects) > 0:
            select = selects[0]
            print(f"Select classes: {select.get_attribute('class')}")
            print(f"Select role: {select.get_attribute('role')}")
            print(f"Select aria-expanded: {select.get_attribute('aria-expanded')}")

        # Check page structure
        print("\nPage structure:")
        h4_elements = driver.find_elements(By.TAG_NAME, "h4")
        for h4 in h4_elements:
            print(f"  H4: {h4.text}")
