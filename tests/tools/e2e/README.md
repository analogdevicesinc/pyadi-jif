# PyADI-JIF End-to-End (E2E) Tests

This directory contains comprehensive end-to-end tests for the PyADI-JIF Streamlit web UI tools using Playwright and pytest.

## Test Coverage

The E2E test suite includes **28 tests** across 5 test modules:

- **JESD204 Mode Selector**: 7 tests
- **Clock Configurator**: 7 tests
- **System Configurator**: 8 tests
- **Cross-Page Workflows**: 3 tests
- **Visual Regression**: 3 tests

## Architecture

```
tests/tools/e2e/
├── conftest.py                          # Core pytest configuration and fixtures
├── fixtures/
│   ├── __init__.py
│   └── streamlit_app.py                # Streamlit app lifecycle management
├── pages/
│   ├── __init__.py
│   ├── base_page.py                    # Common Streamlit interactions
│   ├── jesd_mode_selector_page.py      # JESD Mode Selector page object
│   ├── clock_configurator_page.py      # Clock Configurator page object
│   └── system_configurator_page.py     # System Configurator page object
├── helpers/
│   ├── __init__.py
│   └── visual_regression.py            # Visual regression testing utilities
├── baselines/                           # Visual regression baseline screenshots
│   ├── jesd_mode_selector/
│   ├── clock_configurator/
│   └── system_configurator/
├── test_jesd_mode_selector_e2e.py      # JESD tests
├── test_clock_configurator_e2e.py      # Clock tests
├── test_system_configurator_e2e.py     # System tests
├── test_cross_page_workflows_e2e.py    # Cross-page tests
└── test_visual_regression_e2e.py       # Visual regression tests
```

## Running Tests

### Run All E2E Tests

```bash
nox -rs teste2e
```

### Run Specific Test Module

```bash
# JESD Mode Selector tests
nox -rs teste2e -- tests/tools/e2e/test_jesd_mode_selector_e2e.py

# Clock Configurator tests
nox -rs teste2e -- tests/tools/e2e/test_clock_configurator_e2e.py

# System Configurator tests
nox -rs teste2e -- tests/tools/e2e/test_system_configurator_e2e.py
```

### Run Specific Test Markers

```bash
# Smoke tests only (fastest)
nox -rs teste2e -- -m smoke

# JESD tests only
nox -rs teste2e -- -m jesd

# Clock tests only
nox -rs teste2e -- -m clock

# System tests only
nox -rs teste2e -- -m system

# Cross-page tests
nox -rs teste2e -- -m cross_page

# Visual regression tests
nox -rs teste2e -- -m visual

# Exclude slow tests
nox -rs teste2e -- -m "not slow"
```

### Run with Headed Mode (See Browser)

```bash
nox -rs teste2e -- --headed
```

### Parallel Execution

```bash
# Run with 4 parallel workers
nox -rs teste2e -- -n 4
```

## Page Object Model

The test suite uses the Page Object Model pattern for maintainability and reusability:

- **BasePage**: Common Streamlit interactions (selectbox, number input, button, expander)
- **JESDModeSelectorPage**: JESD-specific methods (select_part, set_converter_rate, etc.)
- **ClockConfiguratorPage**: Clock-specific methods (select_clock_part, set_reference_clock, etc.)
- **SystemConfiguratorPage**: System-specific methods (select_converter, select_clock, select_fpga_kit, etc.)

Example usage:

```python
def test_example(jesd_page):
    """Example test using JESD page object."""
    jesd_page.select_part("ad9680")
    jesd_page.set_converter_rate(1.0, "GHz")
    assert jesd_page.is_diagram_visible()
```

## Fixtures

### Core Fixtures (conftest.py)

- **streamlit_app**: Session-scoped fixture that starts/stops the Streamlit app
- **page**: Function-scoped Playwright Page object
- **jesd_page, clock_page, system_page**: Page object fixtures for each tool
- **visual_regression**: Visual regression testing helper

### Custom Markers

```python
@pytest.mark.e2e          # All E2E tests
@pytest.mark.jesd         # JESD Mode Selector tests
@pytest.mark.clock        # Clock Configurator tests
@pytest.mark.system       # System Configurator tests
@pytest.mark.cross_page   # Cross-page workflow tests
@pytest.mark.visual       # Visual regression tests
@pytest.mark.smoke        # Quick smoke tests
@pytest.mark.slow         # Slow-running tests
```

## Visual Regression Testing

Visual regression tests capture screenshots and compare them to baseline images.

### Update Baselines

When UI changes are intentional, update baselines:

```bash
nox -rs teste2e_update_baselines
```

This will regenerate baseline screenshots in `tests/tools/e2e/baselines/`.

### Visual Regression Configuration

- **Threshold**: 0.05 (5% pixel difference allowed)
- **Baseline Format**: PNG images
- **Comparison Method**: Pixel-by-pixel comparison

## Test Performance

Expected execution times:

- **Smoke tests** (3 tests): ~30 seconds
- **Full suite** (28 tests): 4-6 minutes
- **Parallel execution** (-n 4): 2-4 minutes

## Streamlit App Lifecycle

The test suite automatically manages the Streamlit app lifecycle:

1. **Start**: Launches `jiftools` command with headless mode
2. **Health Check**: Waits for app to be ready (up to 30 seconds)
3. **Stabilization**: Waits additional 2 seconds for full initialization
4. **Stop**: Gracefully terminates the app after tests complete

## Troubleshooting

### Port Already in Use

If Streamlit fails to start due to port 8501 being in use:

```bash
# Kill any process on port 8501
lsof -ti:8501 | xargs kill -9

# Or specify a different port in conftest.py
```

### Playwright Browser Not Installed

The test suite automatically installs Chromium on first run:

```bash
nox -rs teste2e  # Installs Chromium automatically
```

To manually install:

```bash
playwright install chromium
```

### Visual Regression Baseline Issues

If visual regression tests fail due to environment differences:

1. Update baselines on your environment:
   ```bash
   nox -rs teste2e_update_baselines
   ```

2. Commit updated baselines to version control

3. Other developers will use the updated baselines

## Dependencies

E2E tests require the `e2e` optional dependency group:

```bash
pip install 'pyadi-jif[e2e]'
```

Or with all dependencies:

```bash
pip install 'pyadi-jif[cplex,gekko,draw,tools,e2e]'
```

Key dependencies:

- **playwright**: Browser automation
- **pytest-playwright**: Pytest integration with Playwright
- **pillow**: Screenshot comparison
- **pixelmatch**: Pixel-level image comparison (optional)

## Non-Breaking Integration

- E2E tests coexist with existing AppTest tests
- No changes to existing test infrastructure
- E2E dependencies are optional
- Existing CI/CD pipelines unaffected

## Next Steps

1. Generate visual regression baselines:
   ```bash
   nox -rs teste2e_update_baselines
   ```

2. Run full test suite:
   ```bash
   nox -rs teste2e
   ```

3. Add E2E tests to CI/CD pipeline (optional):
   ```bash
   # Add to GitHub Actions or other CI
   nox -rs teste2e
   ```

