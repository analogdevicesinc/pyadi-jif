# Installing PyADI-JIF

Before installing the module make sure <img src="https://img.shields.io/badge/python-3.7+-blue.svg" alt="Python Version"> is installed. **pyadi-jif** has been validated to function on Windows, Linux, and MacOS. However, not all internal solvers function across all architectures. Specifically the CPLEX solver will not function under ARM. This does not limit functionality, only solving speed.

## Installing from pip (Recommended)

**pyadi-jif** can be installed from pip with all its dependencies: 

<div class="termy">

```console
$ pip install pyadi-jif

---> 100%
```

</div>

## Installing from source

Alternatively, **pyadi-jif** can be installed directly from source. This will require git to be installed

<div class="termy">

```console
$ git clone https://github.com/analogdevicesinc/pyadi-jif.git

Cloning into 'pyadi-jif'...
remote: Enumerating objects: 61, done.
remote: Counting objects: 100% (61/61), done.
remote: Compressing objects: 100% (53/53), done.
remote: Total 1063 (delta 16), reused 30 (delta 8), pack-reused 1002
Receiving objects: 100% (1063/1063), 553.66 KiB | 3.24 MiB/s, done.
Resolving deltas: 100% (681/681), done.

$ cd pyadi-jif
$ python setup.py install

---> 100%
```

</div>

For developers check out the [Developers](developers.md) section.