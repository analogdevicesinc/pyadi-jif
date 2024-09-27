# Developer documentation

**pyadi-jif** uses a modern python flow based around [Nox](https://nox.thea.codes/en/stable/). This is done to keep development isolated from the rest of developer's system and have consistent testing.

## Set up python

Python 3.8 is required for development as it is considered the _target_ release. **Nox** tests other variants when available as well but 3.8 is required. If you do not have 3.8 installed the recommended option is to use [pyenv](https://github.com/pyenv/pyenv)

Alternatively, using plane older virtualenvs is good option as well. Run the following commands to set up a virtualenv:


```bash
python3 -m venv venv
# Linux/macOS
source venv/bin/activate
# Windows
venv\Scripts\activate.bat
```

### Install pyenv

**pyenv** is a handy tool for installing different and isolated versions of python on your system. Since distributions can ship with rather random versions of python, pyenv can help install exactly the versions required. The quick way to install pyenv is with their bash script:

```bash

 curl https://pyenv.run | bash

```

Add to your path and shell startup script (like .bashrc or .zshrc)

```bash

 export PATH="/home/<username>/.pyenv/bin:$PATH
 eval "$(pyenv init -)"
 eval "$(pyenv virtualenv-init -)"

```

Install the desired python version

```bash

  pyenv install 3.8.7

```

## Set up Nox

Nox is a python automation tool that allows you to define reusable tasks in a `noxfile.py`. It is used to run tests, linters, and other tasks. To install nox:

```bash
pip install nox
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
