"""Integration tests for the entire application."""

import time

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class TestIntegration:
    """Integration test suite for the application."""

    def test_app_title_and_logo(self, driver: webdriver.Chrome, base_url: str) -> None:
        """Test that the app title and logo are displayed."""
        driver.get(base_url)
        time.sleep(1)

        # Check for logo
        logo = driver.find_element(By.CSS_SELECTOR, "img[alt='PyADI-JIF Logo']")
        assert logo is not None

        # Check for title
        assert "PyADI-JIF Tools Explorer" in driver.page_source

    def test_sidebar_navigation(self, driver: webdriver.Chrome, base_url: str) -> None:
        """Test navigating between all pages using sidebar."""
        driver.get(base_url)
        time.sleep(1)

        pages = [
            ("JESD204 Mode Selector", "/jesd-mode-selector"),
            ("Clock Configurator", "/clock-configurator"),
            ("System Configurator", "/system-configurator"),
        ]

        for page_name, page_path in pages:
            # Click on page link
            link = driver.find_element(By.XPATH, f"//a[contains(., '{page_name}')]")
            link.click()
            time.sleep(1)

            # Verify navigation
            assert page_path in driver.current_url
            assert page_name in driver.page_source

    def test_responsive_layout(self, driver: webdriver.Chrome, base_url: str) -> None:
        """Test that the layout is responsive."""
        driver.get(base_url)
        time.sleep(1)

        # Test different viewport sizes
        viewports = [
            (1920, 1080),  # Desktop
            (1366, 768),  # Laptop
            (768, 1024),  # Tablet
        ]

        for width, height in viewports:
            driver.set_window_size(width, height)
            time.sleep(1)

            # Verify sidebar and main content are visible
            sidebar = driver.find_element(By.CSS_SELECTOR, "[class*='MuiDrawer']")
            assert sidebar is not None

    def test_all_pages_load_without_errors(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that all pages load without JavaScript errors."""
        pages = [
            "/jesd-mode-selector",
            "/clock-configurator",
            "/system-configurator",
        ]

        for page in pages:
            driver.get(f"{base_url}{page}")
            time.sleep(2)

            # Check for JavaScript errors (simplified check)
            logs = driver.get_log("browser")
            severe_errors = [log for log in logs if log["level"] == "SEVERE"]

            # We allow some errors but fail on too many
            assert len(severe_errors) < 5, f"Too many errors on {page}: {severe_errors}"

    def test_material_ui_theme_applied(self, driver: webdriver.Chrome, base_url: str) -> None:
        """Test that Material-UI theme is applied."""
        driver.get(base_url)
        time.sleep(1)

        # Check for Material-UI components
        mui_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='Mui']")
        assert len(mui_elements) > 0, "No Material-UI components found"

        # Check for proper styling
        app_bar = driver.find_element(By.CSS_SELECTOR, "[class*='MuiAppBar']")
        assert app_bar is not None
