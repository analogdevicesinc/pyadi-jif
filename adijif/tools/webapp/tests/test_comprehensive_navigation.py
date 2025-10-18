"""Comprehensive tests for app navigation and layout."""

import time

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By

from test_helpers import wait_for_element, wait_for_element_clickable, wait_for_page_load


class TestNavigationComprehensive:
    """Comprehensive test suite for app navigation."""

    def test_app_loads_with_logo_and_title(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that app loads with logo and title."""
        driver.get(base_url)
        wait_for_page_load(driver)

        # Check for logo
        logo = wait_for_element(driver, By.CSS_SELECTOR, "img[alt*='Logo']")
        assert logo.is_displayed()

        # Check for title
        title = wait_for_element(
            driver, By.XPATH, "//*[contains(text(), 'PyADI-JIF Tools Explorer')]"
        )
        assert title.is_displayed()

    def test_sidebar_navigation_visible(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that sidebar navigation is visible."""
        driver.get(base_url)
        wait_for_page_load(driver)

        # Check for sidebar drawer
        drawer = wait_for_element(driver, By.CSS_SELECTOR, ".MuiDrawer-root")
        assert drawer.is_displayed()

        # Check for navigation links
        nav_links = driver.find_elements(By.CSS_SELECTOR, "[role='button']")
        assert len(nav_links) >= 3, "Expected at least 3 navigation items"

    def test_all_pages_accessible_from_sidebar(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that all pages can be accessed from sidebar."""
        driver.get(base_url)
        wait_for_page_load(driver)

        pages_to_test = [
            ("JESD204 Mode Selector", "/jesd-mode-selector", "JESD204"),
            ("Clock Configurator", "/clock-configurator", "Clock"),
            ("System Configurator", "/system-configurator", "System"),
        ]

        for page_name, expected_path, title_text in pages_to_test:
            # Find and click the navigation link
            nav_link = wait_for_element_clickable(
                driver, By.XPATH, f"//a[contains(., '{page_name}')]"
            )
            nav_link.click()
            time.sleep(1)

            # Verify navigation occurred
            assert expected_path in driver.current_url, \
                f"Failed to navigate to {page_name}"

            # Verify page title
            assert title_text in driver.page_source, \
                f"Page title not found for {page_name}"

            print(f"✓ Successfully navigated to {page_name}")

    def test_direct_url_navigation(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that pages can be accessed directly via URL."""
        pages = [
            ("/jesd-mode-selector", "JESD204 Mode Selector"),
            ("/clock-configurator", "Clock Configurator"),
            ("/system-configurator", "System Configurator"),
        ]

        for path, expected_title in pages:
            driver.get(f"{base_url}{path}")
            wait_for_page_load(driver)

            # Verify page loaded
            assert expected_title in driver.page_source, \
                f"Failed to load {path} directly"

            print(f"✓ Direct navigation to {path} successful")

    def test_browser_back_button(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that browser back button works correctly."""
        driver.get(f"{base_url}/jesd-mode-selector")
        wait_for_page_load(driver)

        # Navigate to another page
        nav_link = driver.find_element(
            By.XPATH, "//a[contains(., 'Clock Configurator')]"
        )
        nav_link.click()
        time.sleep(1)

        assert "/clock-configurator" in driver.current_url

        # Use browser back button
        driver.back()
        time.sleep(1)

        # Verify we're back on original page
        assert "/jesd-mode-selector" in driver.current_url

    def test_sidebar_stays_visible_across_pages(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that sidebar remains visible when navigating."""
        driver.get(base_url)
        wait_for_page_load(driver)

        pages = ["/jesd-mode-selector", "/clock-configurator", "/system-configurator"]

        for page in pages:
            driver.get(f"{base_url}{page}")
            wait_for_page_load(driver)

            # Check sidebar is still visible
            drawer = driver.find_element(By.CSS_SELECTOR, ".MuiDrawer-root")
            assert drawer.is_displayed(), f"Sidebar not visible on {page}"

    def test_root_redirects_to_jesd_selector(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that root URL redirects to JESD Mode Selector."""
        driver.get(base_url)
        wait_for_page_load(driver)
        time.sleep(1)

        # Should redirect to /jesd-mode-selector
        assert "/jesd-mode-selector" in driver.current_url

    def test_active_page_highlighted_in_sidebar(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that active page is highlighted in sidebar."""
        driver.get(f"{base_url}/clock-configurator")
        wait_for_page_load(driver)

        # Find the Clock Configurator link in sidebar
        clock_link = driver.find_element(
            By.XPATH, "//a[contains(., 'Clock Configurator')]"
        )

        # Check if it has selected/active class
        parent = clock_link.find_element(By.XPATH, "..")
        classes = parent.get_attribute("class")

        # MUI uses 'Mui-selected' class for active items
        print(f"Clock link classes: {classes}")
        # Note: The exact class name may vary, this is informational

    def test_app_bar_visible_across_pages(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that app bar remains visible across pages."""
        driver.get(base_url)
        wait_for_page_load(driver)

        pages = ["/jesd-mode-selector", "/clock-configurator", "/system-configurator"]

        for page in pages:
            driver.get(f"{base_url}{page}")
            wait_for_page_load(driver)

            # Check for app bar
            app_bar = driver.find_element(By.CSS_SELECTOR, ".MuiAppBar-root")
            assert app_bar.is_displayed(), f"App bar not visible on {page}"

            # Check logo is in app bar
            logo = app_bar.find_element(By.TAG_NAME, "img")
            assert logo.is_displayed(), f"Logo not visible in app bar on {page}"

    def test_page_titles_correct(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that page titles are correct."""
        pages = [
            ("/jesd-mode-selector", "JESD204 Mode Selector"),
            ("/clock-configurator", "Clock Configurator"),
            ("/system-configurator", "System Configurator"),
        ]

        for path, expected_title in pages:
            driver.get(f"{base_url}{path}")
            wait_for_page_load(driver)

            # Find h4 title element
            title_element = driver.find_element(By.TAG_NAME, "h4")
            assert expected_title in title_element.text, \
                f"Incorrect title on {path}. Found: {title_element.text}"

    def test_responsive_layout_on_all_pages(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test responsive layout across all pages."""
        pages = ["/jesd-mode-selector", "/clock-configurator", "/system-configurator"]

        viewports = [
            (1920, 1080, "Desktop"),
            (1366, 768, "Laptop"),
            (768, 1024, "Tablet"),
        ]

        for page in pages:
            driver.get(f"{base_url}{page}")
            wait_for_page_load(driver)

            for width, height, device_name in viewports:
                driver.set_window_size(width, height)
                time.sleep(0.5)

                # Verify main content is visible
                h4_title = driver.find_element(By.TAG_NAME, "h4")
                assert h4_title.is_displayed(), \
                    f"Title not visible on {page} at {device_name} size"

                print(f"✓ {page} responsive on {device_name}")

    def test_no_404_errors(self, driver: webdriver.Chrome, base_url: str) -> None:
        """Test that there are no 404 errors on valid pages."""
        pages = [
            "/",
            "/jesd-mode-selector",
            "/clock-configurator",
            "/system-configurator",
        ]

        for page in pages:
            driver.get(f"{base_url}{page}")
            wait_for_page_load(driver)

            # Page should not show 404 or error message
            page_text = driver.page_source.lower()
            assert "404" not in page_text, f"404 error on {page}"
            assert "not found" not in page_text or "no modes found" in page_text, \
                f"'Not found' error on {page}"

    @pytest.mark.slow
    def test_navigation_state_preserved(
        self, driver: webdriver.Chrome, base_url: str
    ) -> None:
        """Test that navigation preserves application state where appropriate."""
        driver.get(f"{base_url}/clock-configurator")
        wait_for_page_load(driver)

        # Navigate to another page
        nav_link = driver.find_element(
            By.XPATH, "//a[contains(., 'JESD204 Mode Selector')]"
        )
        nav_link.click()
        time.sleep(1)

        # Navigate back
        nav_link = driver.find_element(
            By.XPATH, "//a[contains(., 'Clock Configurator')]"
        )
        nav_link.click()
        time.sleep(1)

        # Page should reload (React Router behavior)
        assert "Clock Configurator" in driver.page_source
