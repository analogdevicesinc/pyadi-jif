# flake8: noqa
import tempfile

import nox
from nox.sessions import Session

# Default tasks (nox no args)
# nox.options.sessions = "lint", "mypy", "pytype", "safety", "tests"
nox.options.sessions = "lint", "mypy", "tests"

locations = "adijif", "tests", "noxfile.py"
main_python = "3.7"
multi_python_versions_support = ["3.8", "3.7"]
package = "adijif"


def install_with_constraints(session, *args, **kwargs):
    with tempfile.NamedTemporaryFile() as requirements:
        session.run(
            "poetry",
            "export",
            "--dev",
            "--without-hashes",
            "--format=requirements.txt",
            f"--output={requirements.name}",
            external=True,
        )
        session.install(f"--constraint={requirements.name}", *args, **kwargs)


@nox.session(python=main_python)
def format(session):
    args = session.posargs or locations
    install_with_constraints(session, "black", "isort")
    session.run("black", *args)
    session.run("isort", *args)


@nox.session(python=main_python)
def lint(session):
    args = session.posargs or locations
    install_with_constraints(
        session,
        "darglint",
        "flake8",
        "flake8-annotations",
        "flake8-bandit",
        "flake8-black",
        "flake8-docstrings",
        # "flake8-isort",
        "flake8-bugbear",
        "flake8-import-order",
    )
    session.run("flake8", *args)


@nox.session(python=multi_python_versions_support)
def mypy(session):
    args = session.posargs or locations
    install_with_constraints(session, "mypy", "numpy", "docplex", "gekko")
    session.run("mypy", *args)


@nox.session(python=main_python)
def pytype(session):
    """Run the static type checker."""
    args = session.posargs or ["--disable=import-error", *locations]
    install_with_constraints(session, "pytype")
    session.run("pytype", *args)


@nox.session(python=multi_python_versions_support)
def typeguard(session):
    args = session.posargs
    session.run("poetry", "install", "--no-dev", external=True)
    install_with_constraints(session, "pytest", "pytest-mock", "typeguard")
    session.run("pytest", f"--typeguard-packages={package}", *args)


@nox.session(python=multi_python_versions_support)
def xdoctest(session: Session) -> None:
    """Run examples with xdoctest."""
    args = session.posargs or ["all"]
    session.run("poetry", "install", "--no-dev", external=True)
    install_with_constraints(session, "xdoctest")
    session.run("python", "-m", "xdoctest", package, *args)


@nox.session(python=main_python)
def safety(session):
    with tempfile.NamedTemporaryFile() as requirements:
        session.run(
            "poetry",
            "export",
            "--dev",
            "--format=requirements.txt",
            "--without-hashes",
            f"--output={requirements.name}",
            external=True,
        )
        install_with_constraints(session, "safety")
        session.run("safety", "check", f"--file={requirements.name}", "--full-report")


@nox.session(python=multi_python_versions_support)
def tests(session):
    args = session.posargs or ["--cov=adijif"]
    session.run("poetry", "install", "--no-dev", external=True)
    install_with_constraints(
        session,
        "pytest",
        "pytest-cov",
        "pytest-xdist",
        "pytest-mock",
        "gekko",
        "numpy",
        "docplex",
        "coverage[toml]",
    )
    session.run("pytest", *args)


@nox.session(python=main_python)
def coverage(session: Session) -> None:
    """Upload coverage data."""
    install_with_constraints(session, "coverage[toml]", "codecov")
    session.run("coverage", "xml", "--fail-under=0")
    session.run("codecov", *session.posargs)


@nox.session(python=main_python)
def docs(session: Session) -> None:
    """Build the documentation."""
    install_with_constraints(
        session, "mkdocs", "mkdocs-material", "mkdocstrings", "numpy", "click", "gekko"
    )
    session.run("mkdocs", "build", "--verbose", "--strict")
