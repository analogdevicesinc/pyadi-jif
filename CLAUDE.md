# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

**pyadi-jif** (Python Analog Devices, Inc. JESD204 Interface Framework) is a framework that simplifies JESD204 configuration for ADI data converters and clock chips. The codebase uses constraint solvers (CPLEX, GEKKO, or OR-Tools) to automatically calculate optimal clock rates, dividers, and JESD parameters for complex multi-chip systems.

## Project Structure

The codebase is organized into several key domains:

### `adijif/converters/`
Contains ADC/DAC/transceiver models (AD9081, AD9084, AD9144, AD9680, ADRV9009, etc.). Each converter:
- Inherits from the `converter` base class in `converter.py`
- Implements JESD parameter constraints and data path models
- Can have `_draw.py` variants for visualization support
- May have `_dp.py` variants for dual-platform support
- Can have `_bf.py` variants for legacy/bitfield representations

Resource files in `converters/resources/` contain CSV tables with valid JESD modes for each device.

### `adijif/clocks/`
Contains clock chip models (HMC7044, AD9523, AD9528, AD9545, LTC6952, LTC6953). Each clock:
- Inherits from the `clock` base class in `clock.py`
- Implements output divider constraints and clock distribution logic
- May have `_bf.py` variants for alternative representations

### `adijif/fpgas/xilinx/`
Contains FPGA timing models for Xilinx devices:
- `sevenseries.py` and `ultrascaleplus.py` - architecture-specific timing constraints
- `pll.py` - FPGA PLL models
- `xilinx_draw.py` - Xilinx-specific drawing support

### `adijif/plls/`
Contains external PLL models (ADF4030, ADF4371, ADF4382) that can be inserted between clock chips and converters in multi-chip systems.

### `adijif/system.py`
The main system-level interface. The `system` class:
- Manages CPLEX/GEKKO constraint solver instances
- Coordinates converters, clock chips, FPGAs, and PLLs into complete systems
- Provides `solve()` method to find valid configurations
- Uses SystemPLL mixin for PLL management
- Supports drawing system diagrams

### `adijif/tools/explorer/`
Streamlit-based web UI with three main pages:
- **JESD Mode Selector** - Filters valid JESD modes for a converter
- **Clock Configurator** - Configures individual clock chips
- **System Configurator** - End-to-end system design tool
- State is managed in `state.py` to persist selections across page navigation

### `adijif/pysym/`
A solver-agnostic constraint programming framework supporting CPLEX, GEKKO, and OR-Tools:
- **Model API** - Core optimization model supporting multiple solvers
- **Variables and Constraints** - Integer, binary, and continuous variable types
- **Translators** - Convert abstract constraints to solver-specific APIs
- **Solution extraction** - Uniform interface across all solvers
- Enables educational examples, rapid prototyping, and solver comparison
- See `examples/README_ORTOOLS.md` for OR-Tools example usage

## Key Architecture Patterns

### Constraint Solver Pattern
All components inherit from `core` (in `common.py`) and use a shared solver model. The solver enables:
- Integer linear programming with CPLEX's CpoModel (preferred for deterministic solutions)
- Optimization with GEKKO as fallback
- Components define constraints via solver variable expressions
- `solve()` method applies all constraints and finds valid values

### JESD Class Hierarchy
The `jesd` base class in `jesd.py` defines:
- Standard JESD204B/C parameters (M, L, Np, K, F, S, etc.)
- Bit clock rate calculations from sample clock
- Methods that devices override to add device-specific constraints

### Device Parameterization
Devices read constraints from CSV resource files (e.g., `ad9081_JTx_204C.csv`) containing valid JESD mode tables. This allows rapid expansion to new device models without code changes.

### GEKKO Translation Layer
`gekko_trans.py` provides a translation layer between constraint models defined for CPLEX and GEKKO, allowing solver agnostic constraint definitions in base classes.

## Common Development Commands

All commands use `nox` for environment management:

```bash
# Run tests
make test                           # Single run with coverage
make testp                          # Parallel runs (faster)
make testnb                         # Run Jupyter notebook examples as tests

# Linting and formatting
make lint                           # Check code style
make format                         # Auto-format code (black, isort)

# Documentation
make docs                           # Build Sphinx documentation

# E2E testing (Streamlit tools)
nox -rs teste2e                    # Run Playwright E2E tests
nox -rs teste2e_update_baselines   # Update visual regression baselines
```

### Running Single Tests

```bash
# Run specific test file
nox -rs tests -- tests/test_ad9081.py

# Run specific test function
nox -rs tests -- tests/test_ad9081.py::test_ad9081_rx

# Run tests for specific device/module
nox -rs tests -- -k "ad9081"
```

## Testing Strategy

- **Unit tests** in `tests/` directory test individual components (converters, clocks, PLLs)
- **Notebook tests** run example scripts in `examples/` as Jupyter tests to verify end-to-end workflows
- **E2E tests** in `tests/tools/e2e/` use Playwright to test the Streamlit UI
- Coverage requirement: 90% minimum (enforced via `pyproject.toml`)

## Key Files for Common Tasks

- **Add new converter**: Create `adijif/converters/new_device.py` inheriting from `converter` base class
- **Add new clock chip**: Create `adijif/clocks/new_chip.py` inheriting from `clock` base class
- **Update JESD mode tables**: Modify CSV files in `adijif/converters/resources/`
- **Modify system-level logic**: Edit `adijif/system.py` and mixins in `adijif/sys/`
- **Update Streamlit UI**: Edit files in `adijif/tools/explorer/src/pages/`

## Solver Configuration

The system supports three constraint solvers:

- **CPLEX** (default): Install with `pip install pyadi-jif[cplex]`. Provides deterministic optimal integer solutions. Recommended for production.
- **GEKKO**: Install with `pip install pyadi-jif[gekko]`. Alternative optimization-based solver for nonlinear problems.
- **OR-Tools**: Install with `pip install pyadi-jif[ortools]`. Google's free, open-source constraint programming solver. Good for learning and combinatorial optimization.

**Legacy API:** Device constraints work with `solvers.py` wrapper, automatically using the installed solver.

**pysym Framework:** New development uses the `adijif/pysym/` framework with explicit solver selection:
```python
from adijif.pysym.model import Model
model = Model(solver="ortools")  # or "CPLEX" or "gekko"
```

The pysym framework enables solver-agnostic constraint definition and easy comparison across solvers. See `examples/README_ORTOOLS.md` for examples.

## Dependencies & Optional Features

- **Core**: numpy, openpyxl, pandas
- **CPLEX solver**: `[cplex]` extra - contains docplex and cplex (commercial)
- **GEKKO solver**: `[gekko]` extra - alternative constraint solver
- **OR-Tools solver**: `[ortools]` extra - free, open-source constraint programming (includes ortools>=9.7.0)
- **Drawing**: `[draw]` extra - pyd2lang for system diagram generation
- **Tools (Streamlit UI)**: `[tools]` extra
- **E2E testing**: `[e2e]` extra - playwright and pytest-playwright
