"""Pytest configuration for Selenium tests."""

import sys
import time
from pathlib import Path
from typing import Generator

import pytest
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Add tests directory to Python path so test_helpers can be imported
tests_dir = Path(__file__).parent
if str(tests_dir) not in sys.path:
    sys.path.insert(0, str(tests_dir))


@pytest.fixture(scope="session")
def chrome_options() -> Options:
    """Create Chrome options for headless testing."""
    options = Options()
    # Google Chrome is installed, let it auto-detect
    options.add_argument("--headless=new")  # Use new headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    return options


@pytest.fixture(scope="function")
def driver(chrome_options: Options) -> Generator[webdriver.Chrome, None, None]:
    """Create a Chrome WebDriver instance."""
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(10)
    yield driver
    driver.quit()


@pytest.fixture(scope="session")
def base_url() -> str:
    """Base URL for the application."""
    return "http://localhost:3000"


@pytest.fixture(scope="session")
def api_url() -> str:
    """API URL for the backend."""
    return "http://localhost:8000"


@pytest.fixture(scope="session", autouse=True)
def check_services(base_url: str, api_url: str) -> None:
    """Check that frontend and backend services are running before tests."""
    max_retries = 3
    retry_delay = 2

    # Check backend
    for i in range(max_retries):
        try:
            response = requests.get(f"{api_url}/health", timeout=5)
            if response.status_code == 200:
                print(f"\n✓ Backend is running at {api_url}")
                break
        except requests.exceptions.RequestException:
            if i < max_retries - 1:
                print(f"\n⏳ Waiting for backend... (attempt {i + 1}/{max_retries})")
                time.sleep(retry_delay)
            else:
                pytest.exit(
                    f"❌ Backend not available at {api_url}/health. "
                    "Please start the backend with: python run_dev.py"
                )

    # Check frontend
    for i in range(max_retries):
        try:
            response = requests.get(base_url, timeout=5)
            if response.status_code == 200:
                print(f"✓ Frontend is running at {base_url}")
                break
        except requests.exceptions.RequestException:
            if i < max_retries - 1:
                print(f"⏳ Waiting for frontend... (attempt {i + 1}/{max_retries})")
                time.sleep(retry_delay)
            else:
                pytest.exit(
                    f"❌ Frontend not available at {base_url}. "
                    "Please start the frontend with: npm run dev"
                )


# Note: Helper functions have been moved to test_helpers.py
# Import them with: from test_helpers import wait_for_element, click_mui_select, etc.
