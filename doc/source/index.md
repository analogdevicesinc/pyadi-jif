# pyadi-jif: Python interface for the ADI JESD Interface Framework

**pyadi-jif** is a Python modeling and configuration tool that simplifies JESD204 interface setup for Analog Devices converters, clock chips, and FPGAs. It can automatically solve for valid clock divider settings and JESD204 link parameters at both the individual component level and across a complete system.

```{image} _static/logos/PyADI-JIF_logo_w_cropped.png?://
:class: only-dark
:width: 400px
:alt: PyADI-IIO Logo
```

```{image} _static/logos/PyADI-JIF_logo_cropped.png?://
:class: only-light
:width: 400px
:alt: PyADI-IIO Logo
```

````{flex}
:class: badges
```{image} https://img.shields.io/pypi/pyversions/pyadi-jif.svg
:alt: Python versions
:target: https://pypi.python.org/pypi/pyadi-jif/
```
```{image} https://github.com/analogdevicesinc/pyadi-jif/actions/workflows/tests.yml/badge.svg
:alt: Build Status
:target: https://github.com/analogdevicesinc/pyadi-jif/actions/workflows/tests.yml
```
```{image} https://codecov.io/gh/analogdevicesinc/pyadi-jif/branch/main/graph/badge.svg
:alt: codecov
:target: https://codecov.io/gh/analogdevicesinc/pyadi-jif
```
````
````{flex}
:class: badges
```{image} https://img.shields.io/badge/doc-latest-blue.svg
:alt: Documentation
:target: https://analogdevicesinc.github.io/pyadi-jif/
```
```{image} https://img.shields.io/pypi/v/pyadi-jif.svg
:alt: pypi
:target: https://pypi.python.org/pypi/pyadi-jif/
```
````

```{image} _static/imgs/jesd_light.png
:class: only-light
:alt: JESD204 system overview
:width: 75%
```

```{image} _static/imgs/jesd_dark.png
:class: only-dark
:alt: JESD204 system overview
:width: 75%
```

## What is pyadi-jif?

JESD204 is a high-speed serial interface standard used to connect data converters (ADCs and DACs) to FPGAs. Configuring a JESD204 system requires coordinating clock frequencies, lane rates, and link parameters across multiple chips simultaneously — a process that is error-prone when done manually.

**pyadi-jif** models the constraints of each component (converter, clock chip, FPGA transceiver) and uses a constraint solver to automatically find valid configurations. It supports both:

- **Component-level** use: configure a single clock chip or verify an existing setup in isolation.
- **System-level** use: solve for a complete, consistent configuration across converter + clock + FPGA together.

## Key Features

- Automatic constraint solving for JESD204B/C clock and link parameters
- Models for ADI converters (ADCs, DACs, MxFEs), clock chips (HMC7044, AD9523-1, AD9545), and FPGA transceivers (Xilinx, Intel)
- Interactive web-based **JIF Tools Explorer** (`jiftools`) for graphical configuration and exploration
- MCP server for AI assistant integration
- Clock tree and system block diagram generation

## Quick Start

Install with pip and launch the interactive tools:

```bash
pip install 'pyadi-jif[cplex,tools,draw]'
jiftools
```

Or use the Python API directly:

```python
import adijif

# System-level: solve converter + clock + FPGA together
sys = adijif.system("ad9680", "ad9523_1", "xilinx", vcxo=125e6)
sys.converter.sample_clock = 1e9
sys.converter.decimation = 1
sys.converter.L = 4
sys.converter.M = 2
sys.converter.N = 14
sys.converter.Np = 16
sys.converter.K = 32
sys.converter.F = 1
sys.fpga.setup_by_dev_kit_name("zc706")
config = sys.solve()
```

See [Installation](install.md) for full setup instructions, and [Usage Flows](flow.md) for detailed examples.

## Interactive Tools

The **JIF Tools Explorer** (`jiftools`) is a Streamlit web application with three tools:

- **JESD204 Mode Selector** — browse and filter valid JESD204 modes for a given converter and sample rate
- **Clock Configurator** — configure ADI clock chips to generate required output clocks
- **System Configurator** — end-to-end configuration of converter + clock chip + FPGA

See the [Quick Start Guide](tools_quickstart.md) and [full tools documentation](tools.md).

```{toctree}
:maxdepth: 1
:caption: Contents:
install.md
tools_quickstart.md
tools.md
mcp_server.md
flow.md
converters.md
clocks.md
fpgas/index
parts.md
defs.md
devs/index
draw.md
developers.md
```
