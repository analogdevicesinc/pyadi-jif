"""Helper functions for Selenium tests."""

import time
from typing import Any

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def wait_for_element(
    driver: webdriver.Chrome, by: str, value: str, timeout: int = 10
) -> Any:
    """Wait for an element to be present and return it."""
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )


def wait_for_element_clickable(
    driver: webdriver.Chrome, by: str, value: str, timeout: int = 10
) -> Any:
    """Wait for an element to be clickable and return it."""
    return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, value)))


def wait_for_page_load(driver: webdriver.Chrome, timeout: int = 10) -> None:
    """Wait for page to load completely."""
    time.sleep(0.5)  # Give React time to start rendering
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


def wait_for_text_in_element(
    driver: webdriver.Chrome, by: str, value: str, text: str, timeout: int = 10
) -> bool:
    """Wait for specific text to appear in an element."""
    try:
        WebDriverWait(driver, timeout).until(
            EC.text_to_be_present_in_element((by, value), text)
        )
        return True
    except TimeoutException:
        return False


def click_mui_select(driver: webdriver.Chrome, label: str, timeout: int = 10) -> None:
    """Click a Material-UI Select component by its label."""
    # Find the FormControl containing the label
    label_element = wait_for_element_clickable(
        driver, By.XPATH, f"//label[text()='{label}']", timeout
    )
    # Click the parent div to open the select
    parent = label_element.find_element(By.XPATH, "..")
    parent.click()
    time.sleep(0.5)


def select_mui_option(driver: webdriver.Chrome, option_text: str, timeout: int = 10) -> None:
    """Select an option from an open Material-UI Select dropdown."""
    # Wait for the dropdown menu to appear
    wait_for_element(driver, By.CSS_SELECTOR, "[role='listbox']", timeout)
    # Find and click the option
    option = wait_for_element_clickable(
        driver, By.XPATH, f"//li[@role='option' and contains(., '{option_text}')]", timeout
    )
    option.click()
    time.sleep(0.5)


def get_console_errors(driver: webdriver.Chrome) -> list:
    """Get severe console errors from the browser."""
    logs = driver.get_log("browser")
    return [log for log in logs if log["level"] == "SEVERE"]
