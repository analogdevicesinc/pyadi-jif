# Installing PyADI-JIF

Before installing the module make sure **python 3.9+** is installed. **pyadi-jif** has been validated to function on Windows, Linux, and MacOS. However, not all internal solvers function across all architectures. Specifically the CPLEX solver will not function under ARM. This does not limit functionality, only solving speed.

## Installing from pip (Recommended)

**pyadi-jif** can be installed from pip with all its dependencies:

```bash
pip install 'pyadi-jif[cplex,draw]'
```

## Installing from source

Alternatively, **pyadi-jif** can be installed directly from source. This will require git to be installed

```bash
git clone https://github.com/analogdevicesinc/pyadi-jif.git
cd pyadi-jif
pip install ".[cplex,draw]"
```


:::{note}

pyadi-jif requires a solver to be installed. See below for options.

:::

## Solver Installation

pyadi-jif supports multiple constraint solvers. Choose one based on your needs:

### CPLEX (Recommended for Production)

**Best for:** Guaranteed optimal solutions, large-scale problems, enterprise use

```bash
pip install 'pyadi-jif[cplex]'
```

**Note:** CPLEX requires a commercial license. IBM offers a free Community Edition for academic and research use.

### OR-Tools (Free, Open-Source)

**Best for:** Learning, prototyping, free optimization, clock configuration

```bash
pip install 'pyadi-jif[ortools]'
```

Includes Google's CP-SAT solver. No licensing required. See [OR-Tools Examples](../../examples/README_ORTOOLS.md) for getting started.

### GEKKO (Alternative Nonlinear Solver)

**Best for:** Nonlinear optimization, educational purposes

```bash
pip install 'pyadi-jif[gekko]'
```

Good for problems with smooth nonlinear constraints. Slower than CPLEX for integer problems.

If you want to install the drawing features, you will need to install the `draw` extra:

```bash
pip install 'pyadi-jif[draw]'
```

## Developers

For developers check out the [Developers](developers.md) section.
