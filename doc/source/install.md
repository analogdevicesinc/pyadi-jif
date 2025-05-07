# Installing PyADI-JIF

Before installing the module make sure **python 3.9+** is installed. **pyadi-jif** has been validated to function on Windows, Linux, and MacOS. However, not all internal solvers function across all architectures. Specifically the CPLEX solver will not function under ARM. This does not limit functionality, only solving speed.

## Installing from pip (Recommended)

**pyadi-jif** can be installed from pip with all its dependencies: 

```bash
pip install --index-url https://test.pypi.org/simple/ 'pyadi-jif[cplex]'
```

## Installing from source

Alternatively, **pyadi-jif** can be installed directly from source. This will require git to be installed

```bash
git clone https://github.com/analogdevicesinc/pyadi-jif.git
cd pyadi-jif
pip install ".[cplex]"
```


:::{note}

pyadi-jif requires a solver to be installed. We recommend using CPLEX but most features will work with GEKKO.

CPLEX:
```bash
pip install --index-url https://test.pypi.org/simple/ 'pyadi-jif[cplex]'
```

GEKKO:
```bash
pip install --index-url https://test.pypi.org/simple/ 'pyadi-jif[gekko]'
```
:::

## Developers

For developers check out the [Developers](developers.md) section.
