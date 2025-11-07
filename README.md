# pyadi-jif: Python Configurator for ADI JESD204 Interface Framework (JIF)

A framework to simplify the use of JESD204 with Analog Devices, Inc. data converters and clock chips.

**New:** Try the interactive web-based [JIF Tools Explorer](#jif-tools-explorer) for a graphical interface!

<p align="center">
<img src="doc/source/imgs/PyADI-JIF_logo.png" width="500" alt="PyADI-JIF Logo"> </br>
</p>

<p align="center">

<a href="https://opensource.org/licenses/">
<img src="https://img.shields.io/badge/License-EPL%20v2-blue.svg" alt="EPL v2.0>
</a>

<a href="https://github.com/analogdevicesinc/pyadi-jif/actions/workflows/tests.yml">
<img src="https://github.com/analogdevicesinc/pyadi-jif/actions/workflows/tests.yml/badge.svg" alt="Test Status">
</a>

<a href="https://codecov.io/gh/analogdevicesinc/pyadi-jif">
<img src="https://codecov.io/gh/analogdevicesinc/pyadi-jif/branch/main/graph/badge.svg?token=WVSRCSXFWL" alt="Coverage Status">
</a>
</p>

## Installation

Install JIF with pip

```bash
pip install 'pyadi-jif[cplex]'
```

## JIF Tools Explorer

Launch the interactive web-based tools for JESD204 configuration:

```bash
jiftools
```

The JIF Tools Explorer provides:
- **JESD204 Mode Selector** - Find and filter valid JESD204 modes for ADI converters
- **Clock Configurator** - Configure ADI clock chips (HMC7044, AD9545, etc.)
- **System Configurator** - Complete end-to-end system design (FPGA + Converter + Clock)

See the [Tools Documentation](https://analogdevicesinc.github.io/pyadi-jif/tools.html) for detailed usage guide.

## Documentation

[Documentation](https://analogdevicesinc.github.io/pyadi-jif)


## License

[EPL-2.0](https://www.eclipse.org/legal/epl-2.0/)
