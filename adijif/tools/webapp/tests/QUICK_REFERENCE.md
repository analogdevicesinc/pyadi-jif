# Test Suite Quick Reference

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Ensure services are running
python ../run_dev.py  # In another terminal
```

## Common Commands

```bash
# Run all tests
pytest

# Quick tests only
pytest -m "not slow"

# Specific test file
pytest test_comprehensive_jesd_selector.py

# Specific test
pytest test_api_endpoints.py::TestAPIEndpoints::test_health_endpoint

# With HTML report
pytest --html=report.html --self-contained-html

# In parallel
pytest -n 4

# With coverage
pytest --cov=../backend --cov-report=html

# Verbose output
pytest -vv

# Stop on first failure
pytest -x

# Match keyword
pytest -k "dropdown"

# Match marker
pytest -m "api"
```

## Using Test Runner

```bash
# Quick tests with HTML report
python run_tests.py --quick --html

# Parallel execution
python run_tests.py --parallel 4

# Verbose with failfast
python run_tests.py -v -x

# All options
python run_tests.py --help
```

## Test Markers

- `slow` - Long-running tests
- `api` - API endpoint tests
- `ui` - UI component tests
- `integration` - End-to-end workflows

```bash
# Run only API tests
pytest -m "api"

# Run UI tests but not slow ones
pytest -m "ui and not slow"
```

## Debugging Tests

```bash
# Show print statements
pytest -s

# Very verbose
pytest -vv -s

# Show local variables on failure
pytest -l

# Drop into debugger on failure
pytest --pdb
```

## Test Files

| File | Tests | Focus |
|------|-------|-------|
| `test_comprehensive_jesd_selector.py` | 14+ | JESD page |
| `test_comprehensive_clock.py` | 12+ | Clock page |
| `test_comprehensive_system.py` | 12+ | System page |
| `test_comprehensive_navigation.py` | 14+ | Navigation |
| `test_api_endpoints.py` | 10+ | API |
| `test_dropdown_functionality.py` | 6+ | Dropdowns |

## Helper Functions

```python
from test_helpers import (
    wait_for_element,
    wait_for_element_clickable,
    wait_for_page_load,
    click_mui_select,
    select_mui_option,
    get_console_errors,
)

# Wait for element
element = wait_for_element(driver, By.ID, "my-id")

# Click Material-UI select
click_mui_select(driver, "Select a Part")

# Select option
select_mui_option(driver, "AD9680")

# Check errors
errors = get_console_errors(driver)
```

## Fixtures

```python
def test_example(driver, base_url, api_url):
    # driver - Chrome WebDriver (headless)
    # base_url - http://localhost:3000
    # api_url - http://localhost:8000
    pass
```

## Troubleshooting

```bash
# Services not running
curl http://localhost:8000/health  # Backend
curl http://localhost:3000          # Frontend

# Update ChromeDriver
pip install --upgrade webdriver-manager

# Clear pytest cache
pytest --cache-clear

# Show available fixtures
pytest --fixtures

# Show available markers
pytest --markers
```

## CI/CD

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    cd adijif/tools/webapp/tests
    pytest -v --html=report.html
```

## Coverage

```bash
# Generate coverage report
pytest --cov=../backend --cov-report=html

# View report
open htmlcov/index.html
```

## Common Patterns

### Test a dropdown
```python
def test_dropdown(driver, base_url):
    driver.get(f"{base_url}/page")
    wait_for_page_load(driver)

    click_mui_select(driver, "Label")
    select_mui_option(driver, "Option")

    assert "Option" in driver.page_source
```

### Test an input
```python
def test_input(driver, base_url):
    driver.get(f"{base_url}/page")

    input_field = wait_for_element(
        driver, By.XPATH, "//label[text()='Label']/..//input"
    )
    input_field.clear()
    input_field.send_keys("value")

    assert input_field.get_attribute("value") == "value"
```

### Test a button
```python
def test_button(driver, base_url):
    driver.get(f"{base_url}/page")

    button = wait_for_element_clickable(
        driver, By.XPATH, "//button[contains(., 'Text')]"
    )
    button.click()
    time.sleep(1)

    assert "result" in driver.page_source
```

## Performance

```bash
# Run tests in parallel (faster)
pytest -n auto  # Use all CPUs

# Or specify number of workers
pytest -n 4

# Profile test execution time
pytest --durations=10  # Show 10 slowest tests
```

## Reports

```bash
# HTML report
pytest --html=report.html --self-contained-html

# JUnit XML (for CI)
pytest --junit-xml=results.xml

# JSON report
pytest --json-report --json-report-file=report.json
```

## Tips

1. **Always wait** after interactions: `time.sleep(0.5)`
2. **Use explicit waits** over implicit waits
3. **Check console errors** to catch JS issues
4. **Make tests independent** - don't rely on order
5. **Use descriptive names** for tests and classes
6. **Add docstrings** explaining what test does
7. **Use markers** to organize tests
8. **Run quick tests often**, slow tests before commit

## Example Test

```python
import time
import pytest
from selenium.webdriver.common.by import By
from test_helpers import wait_for_element, click_mui_select

class TestMyFeature:
    """Test my feature."""

    def test_feature_works(self, driver, base_url):
        """Test that my feature works correctly."""
        # Navigate
        driver.get(f"{base_url}/my-page")
        time.sleep(1)

        # Interact
        click_mui_select(driver, "My Select")
        option = driver.find_element(
            By.XPATH, "//li[@role='option'][1]"
        )
        option.click()
        time.sleep(0.5)

        # Assert
        assert "expected" in driver.page_source

    @pytest.mark.slow
    def test_slow_feature(self, driver, base_url):
        """Test that requires more time."""
        # Test long-running feature
        pass
```

See [README.md](README.md) for complete documentation!
