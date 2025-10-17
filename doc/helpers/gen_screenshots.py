# flake8: noqa
"""Generate screenshots for the documentation."""
import os


def generate_jesdmodeselector_screenshots():
    """Start streamlit, open the browser to the jesdmodeselector app, and take screenshots."""
    import time
    import subprocess
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    # from webdriver_manager.chrome import GeckoDriverManager
    from webdriver_manager.chrome import ChromeDriverManager

    # Start the streamlit app
    print("Starting Streamlit app...")
    streamlit_process = subprocess.Popen(
        ["jiftools", "--server.headless", "true"],
    )
    print("Streamlit app started")
    # Wait for the app to start
    time.sleep(5)

    driver = None
    try:

        # Set up Selenium WebDriver
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        # driver = webdriver.Firefox(executable_path=GeckoDriverManager().install())
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options,
        )

        # Get the Chrome process PID
        chrome_pid = driver.service.process.pid
        print(f"Chrome driver started with PID: {chrome_pid}")

        # Open the app in the browser
        driver.get("http://localhost:8501")

        # Wait for the page to load and Streamlit to be ready
        wait = WebDriverWait(driver, 20)

        apps = [
            "JESD Mode Selector",
            "Clock Configurator",
            "System Configurator",
        ]

        # Select JESD Mode Selector Radio Button
        # Click the label element instead of the input, as Streamlit wraps radio buttons
        # Try multiple strategies to find the clickable element
        for app in apps:
            try:
                # Strategy 1: Find by label text containing "JESD Mode Selector"
                button = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, f"//label[contains(., '{app}')]")
                    )
                )
                print("Found button using label text")
            except Exception as e:
                print(f"Strategy 1 failed: {e}")
                try:
                    # Strategy 2: Find the label parent of the input element
                    xpath = "/html/body/div[1]/div[1]/div[1]/div/div/section/div[1]/div[2]/div/div/div[3]/div/div/label[1]"
                    button = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                    print("Found button using label XPath")
                except Exception as e2:
                    print(f"Strategy 2 failed: {e2}")
                    # Strategy 3: Use JavaScript to click the element
                    xpath = "/html/body/div[1]/div[1]/div[1]/div/div/section/div[1]/div[2]/div/div/div[3]/div/div/label[1]/input"
                    button = wait.until(
                        EC.presence_of_element_located((By.XPATH, xpath))
                    )
                    driver.execute_script("arguments[0].click();", button)
                    print("Clicked button using JavaScript")
                    time.sleep(10)  # Wait for the app to update

                    # Take screenshot after JavaScript click
                    here = os.path.dirname(os.path.abspath(__file__))
                    filename = app.lower().replace(" ", "") + ".png"
                    screenshot_file = os.path.join(here, filename)
                    driver.save_screenshot(screenshot_file)
                    print(f"Saved screenshot: {screenshot_file}")
                    continue  # Move to next app

            assert button is not None, f"Could not find {app} Radio Button"
            button.click()
            print("Clicked button successfully")
            time.sleep(10)  # Wait for the app to update

            here = os.path.dirname(os.path.abspath(__file__))
            here = os.path.join(here, "..", "source", "_static", "imgs")
            filename = app.lower().replace(" ", "") + ".png"
            screenshot_file = os.path.join(here, filename)
            # Take screenshot
            driver.save_screenshot(screenshot_file)
            print(f"Saved screenshot: {screenshot_file}")

    except Exception as e:
        print(f"Error during screenshot generation: {e}")
        # Take a debug screenshot to see what the page looks like
        if driver is not None:
            debug_file = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "debug_screenshot.png"
            )
            try:
                driver.save_screenshot(debug_file)
                print(f"Saved debug screenshot: {debug_file}")
            except:
                pass
        raise
    finally:
        # Clean up
        print("Cleaning up...")
        if driver is not None:
            try:
                print("Quitting Chrome driver")
                driver.quit()
                print("Chrome driver closed")
            except Exception as e:
                print(f"Error quitting driver: {e}")

        print("Terminating Streamlit process")
        streamlit_process.terminate()
        streamlit_process.wait()
        print("Streamlit process terminated")

        # Kill the Chrome process if still running
        if "chrome_pid" in locals():
            try:
                print(f"Killing Chrome process with PID: {chrome_pid}")
                os.kill(chrome_pid, 9)
                print("Chrome process killed")
            except Exception as e:
                print(f"Error killing Chrome process: {e}")


if __name__ == "__main__":
    generate_jesdmodeselector_screenshots()
