# PyADI-JIF Webapp Test Suite

Comprehensive Selenium headless tests for the PyADI-JIF Tools Explorer web application.

## Overview

This test suite provides complete coverage of the webapp functionality including:
- **UI Component Testing** - All dropdowns, inputs, buttons
- **Navigation Testing** - Page routing, sidebar, browser navigation
- **API Testing** - Backend endpoints and data validation
- **Integration Testing** - Complete user workflows
- **Accessibility Testing** - Basic ARIA and semantic HTML checks
- **Responsive Testing** - Multiple viewport sizes

## Test Organization

### Test Files

| File | Purpose | Tests |
|------|---------|-------|
| `test_comprehensive_jesd_selector.py` | JESD Mode Selector page | 14+ tests |
| `test_comprehensive_clock.py` | Clock Configurator page | 12+ tests |
| `test_comprehensive_system.py` | System Configurator page | 12+ tests |
| `test_comprehensive_navigation.py` | App navigation & layout | 14+ tests |
| `test_api_endpoints.py` | Backend API endpoints | 10+ tests |
| `test_dropdown_functionality.py` | Dropdown specific tests | 6+ tests |

### Test Categories (Markers)

Tests are organized with pytest markers:

- `@pytest.mark.slow` - Long-running tests (solving, complete workflows)
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.ui` - UI component tests
- `@pytest.mark.integration` - End-to-end workflow tests

## Prerequisites

### Required Services

Both the frontend and backend must be running before tests:

```bash
# Terminal 1 - Start backend
cd adijif/tools/webapp
python -m uvicorn adijif.tools.webapp.backend.main:app --reload --port 8000

# Terminal 2 - Start frontend
cd adijif/tools/webapp/frontend
npm run dev

# Terminal 3 - Run tests
cd adijif/tools/webapp/tests
pytest
```

**OR** use the development script:

```bash
# Terminal 1 - Start both services
cd adijif/tools/webapp
python run_dev.py

# Terminal 2 - Run tests
cd tests
pytest
```

### Dependencies

Install test dependencies:

```bash
cd adijif/tools/webapp/tests
pip install -r requirements.txt
```

This installs:
- `pytest` - Test framework
- `selenium` - Browser automation
- `webdriver-manager` - Automatic ChromeDriver management
- `requests` - HTTP client for API tests
- `pytest-html` - HTML test reports
- `pytest-xdist` - Parallel test execution
- `pytest-timeout` - Test timeouts

## Running Tests

### Quick Start

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest test_comprehensive_jesd_selector.py

# Run specific test
pytest test_comprehensive_jesd_selector.py::TestJESDModeSelectorComprehensive::test_page_loads_with_all_elements
```

### Using the Test Runner

The test runner script provides convenient options:

```bash
# Run all tests
python run_tests.py

# Run only quick tests (skip slow tests)
python run_tests.py --quick

# Run only slow tests
python run_tests.py --slow

# Run tests in parallel (4 workers)
python run_tests.py --parallel 4

# Generate HTML report
python run_tests.py --html

# Run specific test file
python run_tests.py --test test_api_endpoints.py

# Run tests matching keyword
python run_tests.py -k "dropdown"

# Run tests with specific marker
python run_tests.py -m "api"

# Fail fast (stop on first failure)
python run_tests.py --failfast

# Verbose output
python run_tests.py --verbose
```

### Advanced Usage

```bash
# Run API tests only
pytest -m "api" -v

# Run UI tests in parallel
pytest -m "ui" -n 4

# Run tests except slow ones
pytest -m "not slow"

# Run with HTML report
pytest --html=report.html --self-contained-html

# Run with specific keyword
pytest -k "dropdown or select"

# Run with coverage
pytest --cov=../backend --cov-report=html

# Run with detailed output
pytest -vv -s

# Run and stop on first failure
pytest -x
```

## Test Configuration

### pytest.ini

Configure pytest behavior in `pytest.ini`:

- Test discovery patterns
- Marker definitions
- Default options
- Logging configuration
- Warning filters

### conftest.py

Shared pytest fixtures:

- `driver` - Chrome WebDriver instance (headless)
- `base_url` - Frontend URL (http://localhost:3000)
- `api_url` - Backend URL (http://localhost:8000)
- `check_services` - Verify services are running

### test_helpers.py

Reusable helper functions for tests:

- `wait_for_element()` - Wait for element to appear
- `wait_for_element_clickable()` - Wait for element to be clickable
- `wait_for_page_load()` - Wait for page to load completely
- `click_mui_select()` - Click Material-UI Select component
- `select_mui_option()` - Select option from dropdown
- `get_console_errors()` - Get browser console errors

## Test Coverage

### JESD Mode Selector (`test_comprehensive_jesd_selector.py`)

- ✅ Page loads with all elements
- ✅ Help dialog functionality
- ✅ Converter selection flow
- ✅ Units selection (Hz, kHz, MHz, GHz)
- ✅ Converter rate input
- ✅ Sample rate calculation
- ✅ No JavaScript errors
- ✅ Page accessibility
- ✅ Responsive layout
- ✅ Multiple converter selections
- ✅ Complete user workflow

### Clock Configurator (`test_comprehensive_clock.py`)

- ✅ Page loads successfully
- ✅ Clock part selection
- ✅ Reference clock input
- ✅ Add output clock
- ✅ Remove output clock
- ✅ Output clock name input
- ✅ Solve configuration button
- ✅ Solve configuration execution
- ✅ Internal clock configuration sections
- ✅ No errors during interaction
- ✅ Complete clock workflow

### System Configurator (`test_comprehensive_system.py`)

- ✅ Page loads with all sections
- ✅ All three selectors present
- ✅ Converter part selection
- ✅ Clock part selection
- ✅ FPGA dev kit selection
- ✅ Reference rate input
- ✅ Converter configuration section
- ✅ FPGA configuration section
- ✅ Solve button disabled when incomplete
- ✅ Solve button enabled after configuration
- ✅ FPGA constraint options
- ✅ PLL selection options
- ✅ No errors during configuration
- ✅ Complete system workflow

### Navigation (`test_comprehensive_navigation.py`)

- ✅ App loads with logo and title
- ✅ Sidebar navigation visible
- ✅ All pages accessible from sidebar
- ✅ Direct URL navigation
- ✅ Browser back button
- ✅ Sidebar stays visible across pages
- ✅ Root redirects to JESD selector
- ✅ Active page highlighted in sidebar
- ✅ App bar visible across pages
- ✅ Page titles correct
- ✅ Responsive layout on all pages
- ✅ No 404 errors

### API Endpoints (`test_api_endpoints.py`)

- ✅ Health endpoint
- ✅ Root endpoint
- ✅ Supported converters endpoint
- ✅ Supported clocks endpoint
- ✅ FPGA dev kits endpoint
- ✅ FPGA constraints endpoint
- ✅ Converter info endpoint
- ✅ API documentation available
- ✅ Invalid endpoint returns 404
- ✅ API response times
- ✅ Converter JESD controls
- ✅ API error handling

## Headless Mode

All tests run in headless Chrome by default (configured in `conftest.py`):

```python
options.add_argument("--headless=new")  # Use new headless mode
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
```

### Running in Headed Mode (for debugging)

To see the browser during tests, modify `conftest.py`:

```python
# Comment out headless argument
# options.add_argument("--headless=new")
```

Or create a custom fixture:

```python
@pytest.fixture
def headed_driver(chrome_options):
    chrome_options._arguments.remove("--headless=new")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    yield driver
    driver.quit()
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Webapp Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install Python dependencies
        run: |
          pip install -e ".[webapp,cplex,draw]"
          pip install -r adijif/tools/webapp/tests/requirements.txt

      - name: Install frontend dependencies
        run: |
          cd adijif/tools/webapp/frontend
          npm install

      - name: Start backend
        run: |
          python -m uvicorn adijif.tools.webapp.backend.main:app --port 8000 &
          sleep 5

      - name: Start frontend
        run: |
          cd adijif/tools/webapp/frontend
          npm run dev &
          sleep 10

      - name: Run tests
        run: |
          cd adijif/tools/webapp/tests
          pytest -v --html=report.html --self-contained-html

      - name: Upload test report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-report
          path: adijif/tools/webapp/tests/report.html
```

## Troubleshooting

### Tests Fail with "Services not available"

**Problem**: Backend or frontend not running

**Solution**:
```bash
# Check backend
curl http://localhost:8000/health

# Check frontend
curl http://localhost:3000

# Start both services
python run_dev.py
```

### ChromeDriver Issues

**Problem**: ChromeDriver version mismatch

**Solution**: `webdriver-manager` automatically downloads the correct version. If issues persist:
```bash
pip install --upgrade webdriver-manager
```

### Timeout Errors

**Problem**: Tests timeout waiting for elements

**Solution**:
- Increase timeout in `conftest.py`
- Check that services are running and responsive
- Use `--timeout=300` flag with pytest

### Parallel Execution Failures

**Problem**: Tests fail when run in parallel

**Solution**:
- Some tests may have race conditions
- Run without `-n` flag
- Ensure tests are independent

## Writing New Tests

### Test Structure

```python
import time
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from test_helpers import wait_for_element, wait_for_page_load

class TestMyFeature:
    """Test suite for my feature."""

    def test_my_feature(self, driver: webdriver.Chrome, base_url: str) -> None:
        """Test my specific feature."""
        # Navigate to page
        driver.get(f"{base_url}/my-page")
        wait_for_page_load(driver)

        # Find element
        element = wait_for_element(driver, By.ID, "my-element")

        # Perform action
        element.click()
        time.sleep(0.5)

        # Assert result
        assert "expected text" in driver.page_source
```

### Best Practices

1. **Use helper functions** from `conftest.py`
2. **Add appropriate sleep** after interactions (0.5-1s)
3. **Use explicit waits** instead of implicit waits
4. **Check for errors** using `get_console_errors()`
5. **Add descriptive docstrings**
6. **Use appropriate markers** (`@pytest.mark.slow`, etc.)
7. **Clean up** resources in fixtures
8. **Make tests independent** - don't rely on test order

### Example: Testing a Dropdown

```python
from test_helpers import click_mui_select, select_mui_option

def test_dropdown_selection(driver, base_url):
    driver.get(f"{base_url}/jesd-mode-selector")

    # Open dropdown
    click_mui_select(driver, "Select a Part")

    # Select option
    select_mui_option(driver, "AD9680")

    # Verify selection
    assert "AD9680" in driver.page_source
```

## Test Metrics

Run tests and view coverage:

```bash
pytest --cov=../backend --cov-report=html --cov-report=term
open htmlcov/index.html  # View coverage report
```

Generate HTML test report:

```bash
pytest --html=report.html --self-contained-html
open report.html  # View test report
```

## Support

For issues or questions:

1. Check [DROPDOWN_TROUBLESHOOTING.md](../DROPDOWN_TROUBLESHOOTING.md)
2. Review test output and console logs
3. Run tests with `-vv -s` for detailed output
4. Check that services are running correctly
5. Open an issue on GitHub with test output

## Summary

- **60+ comprehensive tests** covering all functionality
- **Headless execution** by default
- **Parallel execution** support
- **HTML reports** generation
- **Service validation** before running tests
- **Helper functions** for common operations
- **Well-organized** test structure
- **Extensive documentation**

Run `python run_tests.py --help` for all available options!
