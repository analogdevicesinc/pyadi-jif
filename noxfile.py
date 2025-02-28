# flake8: noqa
import tempfile
from datetime import datetime

import nox
from nox.sessions import Session

# Default tasks (nox no args)
# nox.options.sessions = "lint", "mypy", "pytype", "safety", "tests"
# nox.options.sessions = "lint", "mypy", "tests"
nox.options.sessions = "lint", "tests", "testsnb"
nox.options.error_on_missing_interpreters = False
nox.options.default_venv_backend = "uv"

locations = "adijif", "tests", "noxfile.py"
main_python = "3.8"
multi_python_versions_support = ["3.7", "3.8", "3.9"]
package = "adijif"


def install_with_constraints(session, *args, **kwargs):
    session.install(*args, **kwargs)


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
        # "flake8-black",
        "flake8-docstrings",
        # "flake8-isort",
        "flake8-bugbear",
        "flake8-import-order",
    )
    session.run("flake8", "--config", ".flake8", *args)


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
    install_with_constraints(session, "pytest", "pytest-mock", "typeguard")
    session.run("pytest", f"--typeguard-packages={package}", *args)


@nox.session(python=multi_python_versions_support)
def xdoctest(session: Session) -> None:
    """Run examples with xdoctest."""
    args = session.posargs or ["all"]
    install_with_constraints(session, "xdoctest")
    session.run("python", "-m", "xdoctest", package, *args)


# @nox.session(python=main_python)
# def safety(session):
#     with tempfile.NamedTemporaryFile() as requirements:
#         session.run(
#             "poetry",
#             "export",
#             "--with",
#             "dev",
#             "--format=requirements.txt",
#             "--without-hashes",
#             f"--output={requirements.name}",
#             external=True,
#         )
#         install_with_constraints(session, "safety")
#         session.run("safety", "check", f"--file={requirements.name}", "--full-report")


@nox.session(python=multi_python_versions_support)
def tests(session):
    args = session.posargs or ["--cov=adijif"]
    install_with_constraints(
        session,
        ".[cplex,gekko]",
        "pytest",
        "pytest-cov",
        "pytest-xdist",
        "pytest-mock",
        "numpy",
        "coverage[toml]",
        "rich",
    )
    session.run("pytest", *args)


@nox.session(python=multi_python_versions_support)
def testsp(session):
    import os

    args = [f"-n={os.cpu_count()}"] or ["--cov=adijif"]
    install_with_constraints(
        session,
        ".[cplex,gekko]",
        "pytest",
        "pytest-cov",
        "pytest-xdist",
        "pytest-mock",
        "numpy",
        "coverage[toml]",
        "rich",
    )
    session.run("pytest", *args)


@nox.session(python=multi_python_versions_support)
def testsnb(session):
    import os

    args = ["--nbmake", "examples"]
    install_with_constraints(
        session,
        ".[cplex,gekko]",
        "pytest",
        "pytest-cov",
        "pytest-xdist",
        "pytest-mock",
        "numpy",
        "coverage[toml]",
        "nbmake",
        "pandas",
        "itables",
        "git+https://github.com/analogdevicesinc/pyadi-dt.git",
        "jinja2",
        "pillow",
    )
    session.run("pytest", *args)


@nox.session(python=main_python)
def coverage(session: Session) -> None:
    """Upload coverage data."""
    install_with_constraints(session, "coverage[toml]")
    session.run("coverage", "xml", "--fail-under=0")
    # session.run("codecov", *session.posargs)


@nox.session(python=main_python)
def docs(session: Session) -> None:
    """Build the documentation."""
    install_with_constraints(
        session, "mkdocs", "mkdocs-material", "mkdocstrings", "numpy", "click", "gekko"
    )
    session.run("mkdocs", "build", "--verbose", "--strict")


@nox.session(python=main_python)
def dev_release(session: Session) -> None:
    """Generate development release."""
    install_with_constraints(session, "numpy")
    out_lines = []
    org_lines = []
    with open("pyproject.toml", "r") as f:
        lines = f.readlines()
        org_lines = lines
        for line in lines:
            if "version" in line:
                current_version = line.split("=")[1].strip().replace('"', "")
                print(f"Current version: {current_version}")
                now = datetime.now().strftime("%Y%m%d%H%M%S")
                line = f'version = "{current_version}.dev.{now}"\n'
            out_lines.append(line)

    with open("pyproject.toml", "w") as f:
        f.writelines(out_lines)

    try:
        session.run("uv", "build")

    finally:
        with open("pyproject.toml", "w") as f:
            f.writelines(org_lines)
