# Developer documentation

**pyadi-jif** uses a modern python flow based around [Poetry](https://python-poetry.org) and [Nox](https://nox.thea.codes/en/stable/). This is done to keep development isolated from the rest of developer's system

## Set up python

Python 3.8 is required for development as it is considered the _target_ release. **Nox** tests other variants when available as well but 3.8 is required. If you do not have 3.8 installed the recommended option is to use [pyenv](https://github.com/pyenv/pyenv)

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

## Set up poetry

**Poetry** manages the virtual environment for the project which includes the dependencies. **Poetry** can be installed manually or the _Makefile_ can be leveraged as at this point a valid version of Python is installed. To install poetry and set up the environment run:

```bash

make dev

```

If you already have poetry installed it is not reinstalled.

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
dev                  setup development environment

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
