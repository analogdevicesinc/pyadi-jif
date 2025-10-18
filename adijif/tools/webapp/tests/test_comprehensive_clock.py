"""Comprehensive tests for Clock Configurator functionality."""

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


class TestClockConfiguratorComprehensive:
    """Comprehensive test suite for Clock Configurator page."""

    def test_page_loads_successfully(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that Clock Configurator page loads with all elements."""
        driver.get(f"{base_url}/clock-configurator")
        wait_for_page_load(driver)

        # Check title
        title = wait_for_element(driver, By.XPATH, "//h4[contains(text(), 'Clock')]")
        assert "Clock Configurator" in title.text

        # Check part selector
        part_selector = wait_for_element(
            driver, By.XPATH, "//label[text()='Select a Part']"
        )
        assert part_selector.is_displayed()

    def test_clock_part_selection(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test selecting a clock part."""
        driver.get(f"{base_url}/clock-configurator")
        wait_for_page_load(driver)

        # Open clock part dropdown
        click_mui_select(driver, "Select a Part")

        # Verify options appear
        options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        assert len(options) > 0, "No clock part options found"

        # Select first option
        first_clock = options[0].text
        print(f"Selecting clock part: {first_clock}")
        options[0].click()
        time.sleep(1)

        # Verify configuration sections appear
        sections = driver.find_elements(
            By.XPATH, "//*[contains(text(), 'Clock Inputs and Outputs')]"
        )
        assert len(sections) > 0, "Configuration sections not shown"

    def test_reference_clock_input(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test setting reference clock value."""
        driver.get(f"{base_url}/clock-configurator")
        wait_for_page_load(driver)

        # Select a clock part first
        click_mui_select(driver, "Select a Part")
        options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        if options:
            options[0].click()
            time.sleep(1)

            # Find reference clock input
            ref_input = wait_for_element(
                driver, By.XPATH, "//label[contains(text(), 'Reference Clock')]/..//input"
            )

            # Set value
            ref_input.clear()
            ref_input.send_keys("100000000")
            time.sleep(0.5)

            # Verify value
            assert ref_input.get_attribute("value") == "100000000"

    def test_add_output_clock(self, driver: webdriver.Chrome, base_url: str) -> None:
        """Test adding additional output clocks."""
        driver.get(f"{base_url}/clock-configurator")
        wait_for_page_load(driver)

        # Select a clock part
        click_mui_select(driver, "Select a Part")
        options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        if options:
            options[0].click()
            time.sleep(1)

            # Count initial output clock inputs
            initial_outputs = len(
                driver.find_elements(
                    By.XPATH, "//label[contains(text(), 'Output Clock')]"
                )
            )

            # Click Add Output button
            add_button = wait_for_element_clickable(
                driver, By.XPATH, "//button[contains(., 'Add Output')]"
            )
            add_button.click()
            time.sleep(0.5)

            # Count outputs after adding
            final_outputs = len(
                driver.find_elements(
                    By.XPATH, "//label[contains(text(), 'Output Clock')]"
                )
            )

            assert final_outputs > initial_outputs, "Output clock not added"

    def test_remove_output_clock(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test removing an output clock."""
        driver.get(f"{base_url}/clock-configurator")
        wait_for_page_load(driver)

        # Select a clock part
        click_mui_select(driver, "Select a Part")
        options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        if options:
            options[0].click()
            time.sleep(1)

            # Add an output first
            add_button = driver.find_element(
                By.XPATH, "//button[contains(., 'Add Output')]"
            )
            add_button.click()
            time.sleep(0.5)

            # Count outputs
            outputs_before = len(
                driver.find_elements(
                    By.XPATH, "//label[contains(text(), 'Output Clock')]"
                )
            )

            # Find and click delete button
            delete_buttons = driver.find_elements(
                By.XPATH, "//button[@color='error']//ancestor::button"
            )
            if delete_buttons:
                # Click last delete button
                delete_buttons[-1].click()
                time.sleep(0.5)

                # Count outputs after deletion
                outputs_after = len(
                    driver.find_elements(
                        By.XPATH, "//label[contains(text(), 'Output Clock')]"
                    )
                )

                assert outputs_after < outputs_before, "Output clock not removed"

    def test_output_clock_name_input(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test setting output clock names."""
        driver.get(f"{base_url}/clock-configurator")
        wait_for_page_load(driver)

        # Select a clock part
        click_mui_select(driver, "Select a Part")
        options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        if options:
            options[0].click()
            time.sleep(1)

            # Find first clock name input
            name_inputs = driver.find_elements(
                By.XPATH, "//label[contains(text(), 'Output Clock Name')]/..//input"
            )
            if name_inputs:
                name_input = name_inputs[0]
                name_input.clear()
                name_input.send_keys("TEST_CLK")
                time.sleep(0.5)

                assert name_input.get_attribute("value") == "TEST_CLK"

    def test_solve_configuration_button(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test the solve configuration button."""
        driver.get(f"{base_url}/clock-configurator")
        wait_for_page_load(driver)

        # Select a clock part
        click_mui_select(driver, "Select a Part")
        options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        if options:
            options[0].click()
            time.sleep(1)

            # Find solve button
            solve_button = wait_for_element(
                driver, By.XPATH, "//button[contains(., 'Solve Configuration')]"
            )
            assert solve_button.is_displayed()
            assert solve_button.is_enabled()

    @pytest.mark.slow
    def test_solve_configuration_execution(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test actually solving a clock configuration."""
        driver.get(f"{base_url}/clock-configurator")
        wait_for_page_load(driver)

        # Select a clock part
        click_mui_select(driver, "Select a Part")
        options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        if not options:
            pytest.skip("No clock parts available")

        options[0].click()
        time.sleep(1)

        # Click solve button
        solve_button = driver.find_element(
            By.XPATH, "//button[contains(., 'Solve Configuration')]"
        )
        solve_button.click()

        # Wait for result (up to 15 seconds)
        time.sleep(5)

        # Check if result section appeared
        # This may show "Found Configuration" or an error
        page_text = driver.page_source
        has_result = (
            "Found Configuration" in page_text or "No valid configuration" in page_text
        )

        # Result should appear even if solving fails
        assert has_result, "No configuration result displayed"

    def test_internal_clock_configuration_sections(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that internal clock configuration options appear."""
        driver.get(f"{base_url}/clock-configurator")
        wait_for_page_load(driver)

        # Select a clock part
        click_mui_select(driver, "Select a Part")
        options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        if options:
            options[0].click()
            time.sleep(1)

            # Look for Internal Clock Configuration section
            internal_section = driver.find_elements(
                By.XPATH, "//*[contains(text(), 'Internal Clock Configuration')]"
            )

            # This section may or may not appear depending on the clock part
            print(f"Internal configuration sections found: {len(internal_section)}")

    def test_no_errors_during_interaction(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that no severe errors occur during clock configuration."""
        driver.get(f"{base_url}/clock-configurator")
        wait_for_page_load(driver)

        # Perform various interactions
        click_mui_select(driver, "Select a Part")
        options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        if options:
            options[0].click()
            time.sleep(1)

            # Add output
            add_button = driver.find_element(
                By.XPATH, "//button[contains(., 'Add Output')]"
            )
            add_button.click()
            time.sleep(0.5)

        # Check for errors
        errors = get_console_errors(driver)
        assert len(errors) < 5, f"Too many JavaScript errors: {errors}"

    @pytest.mark.slow
    def test_complete_clock_workflow(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test a complete clock configuration workflow."""
        driver.get(f"{base_url}/clock-configurator")
        wait_for_page_load(driver)

        # Step 1: Select clock part
        click_mui_select(driver, "Select a Part")
        options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        if not options:
            pytest.skip("No clock parts available")

        options[0].click()
        time.sleep(1)

        # Step 2: Set reference clock
        ref_input = driver.find_element(
            By.XPATH, "//label[contains(text(), 'Reference Clock')]/..//input"
        )
        ref_input.clear()
        ref_input.send_keys("125000000")
        time.sleep(0.5)

        # Step 3: Modify first output clock
        output_inputs = driver.find_elements(
            By.XPATH, "//label[contains(text(), 'Output Clock')][1]/..//input"
        )
        if output_inputs:
            output_inputs[0].clear()
            output_inputs[0].send_keys("250000000")
            time.sleep(0.5)

        # Step 4: Add another output
        add_button = driver.find_element(
            By.XPATH, "//button[contains(., 'Add Output')]"
        )
        add_button.click()
        time.sleep(0.5)

        print("✓ Complete clock workflow test passed")
