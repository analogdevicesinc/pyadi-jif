# Developer documentation

**pyadi-jif** uses a modern python flow based around [Nox](https://nox.thea.codes/en/stable/) and [uv](https://docs.astral.sh/uv/). This is done to keep development isolated from the rest of developer's system and have consistent testing.

## Set up python

Python 3.9 is required for development as it is considered the _target_ release. **Nox** tests other variants when available as well. If you do not have 3.9 installed, [install uv](#install-uv) and then use it to install the Python 3.9:

```bash
uv venv venv --python 3.9
source venv/bin/activate
```

If Python 3.9 is your current installed python version, you can use virtaulenvs directly:

```bash
# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

```ps1
# Windows
python3 -m venv venv
venv\Scripts\activate.bat
```

(install-uv)=
### Install uv

**uv** is a python virtual environment manager that is a bit more modern than virtualenv. It is a good option for managing virtual environments and python versions. To install **uv** follow the instructions on the [uv website](https://docs.astral.sh/uv/getting-started/installation/#standalone-installer).

## Set up Nox

Nox is a python automation tool that allows you to define reusable tasks in a `noxfile.py`. It is used to run tests, linters, and other tasks. To install nox:

```bash
(uv) pip install nox
```

### Running nox

To run nox, simply run the following command:

```bash
nox -s <session>
```

Where `<session>` is the name of the session defined in the `noxfile.py`. For example, to run the tests:
```bash
nox -s tests
```

## Using make

Make is muscle memory for most developers so it is a driver of **pyadi-jif** development if you want to use it. Running `make help` provides the possible operations. Note that the Makefile wraps most commands in poetry calls so you do not necessarily need to enable the poetry shell.

```bash

make help

make[1]: Entering directory '/tmp/pyadi-jif'
clean                remove all build, test, coverage and Python artifacts
clean-build          remove build artifacts
clean-pyc            remove Python file artifacts
clean-test           remove test and coverage artifacts
test                 run tests
testp                run tests parallel
coverage             run test with coverage enabled
lint                 format and lint code
docs                 build documentation
install              install module

```

## When committing code

Before committing code and creating pull-requests make sure all tests are passing. CI verifies commits but any assigned reviewers ignore any PRs that have not passed CI checks.

Please run the linters:

```bash
make lint
```

and the tests:

```bash
make test
```
