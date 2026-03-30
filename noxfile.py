# flake8: noqa
import tempfile
from datetime import datetime

import nox
from nox.sessions import Session

# Default tasks (nox no args)
# nox.options.sessions = "lint", "mypy", "pytype", "safety", "tests"
# nox.options.sessions = "lint", "mypy", "tests"
nox.options.sessions = "ty", "lint", "tests", "testsnb"
nox.options.error_on_missing_interpreters = False
nox.options.default_venv_backend = "uv"

locations = "adijif", "tests", "noxfile.py"
main_python = "3.10"
multi_python_versions_support = ["3.10", "3.11"]
package = "adijif"


def install_with_constraints(session, *args, **kwargs):
    session.install(*args, **kwargs)


@nox.session(python=main_python)
def format(session):
    args = session.posargs or locations
    install_with_constraints(session, "ruff")
    session.run("ruff", "format", *args)
    session.run("ruff", "check", "--fix", "--unsafe-fixes", *args)


@nox.session(python=main_python)
def lint(session):
    args = session.posargs or locations
    install_with_constraints(session, "ruff")
    session.run("ruff", "check", *args)


@nox.session(python=main_python)
def ty(session):
    args = session.posargs or locations
    install_with_constraints(
        session,
        "ty",
        ".[cplex,gekko,draw,mcp]",
        "pytest",
        "pytest-asyncio",
        "playwright",
        "numpy",
        "docplex",
        "gekko",
        "streamlit",
        "pandas",
        "mpmath",
        "rich",
    )
    session.run(
        "ty",
        "check",
        "--ignore",
        "invalid-parameter-default",
        "--ignore",
        "invalid-argument-type",
        "--ignore",
        "not-iterable",
        "--ignore",
        "unsupported-operator",
        "--ignore",
        "unresolved-attribute",
        "--ignore",
        "not-subscriptable",
        "--ignore",
        "invalid-assignment",
        "--ignore",
        "unresolved-import",
        "--ignore",
        "possibly-missing-submodule",
        "--ignore",
        "invalid-method-override",
        "--ignore",
        "call-non-callable",
        "--ignore",
        "invalid-return-type",
        "--ignore",
        "unknown-argument",
        "--ignore",
        "invalid-type-form",
        "--ignore",
        "unresolved-reference",
        "--ignore",
        "unused-type-ignore-comment",
        *args,
    )


@nox.session(python=multi_python_versions_support)
def mypy(session):
    args = session.posargs or locations
    install_with_constraints(
        session, "mypy", "numpy", "docplex", "gekko", "streamlit"
    )
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
        ".[cplex,gekko,draw,mcp]",
        "pytest",
        "pytest-cov",
        "pytest-asyncio",
        "pytest-xdist",
        "pytest-mock",
        "numpy",
        "coverage[toml]",
        "rich",
        "mpmath",
        "streamlit",
    )
    session.run("pytest", "--ignore=tests/tools/e2e", *args)


@nox.session(python=main_python)
def generate_screenshots(session):
    args = session.posargs or ["--cov=adijif"]
    install_with_constraints(
        session,
        ".[cplex,gekko,draw,mcp]",
        "pytest",
        "pytest-cov",
        "pytest-xdist",
        "pytest-mock",
        "numpy",
        "coverage[toml]",
        "rich",
        "mpmath",
        "streamlit",
        "webdriver-manager",
        "selenium",
    )
    session.run("python", "doc/helpers/gen_screenshots.py", *args)


@nox.session(python=multi_python_versions_support)
def testsp(session):
    import os

    args = [f"-n={os.cpu_count()}"] or ["--cov=adijif"]
    install_with_constraints(
        session,
        ".[cplex,gekko,draw,mcp]",
        "pytest",
        "pytest-cov",
        "pytest-asyncio",
        "pytest-xdist",
        "pytest-mock",
        "numpy",
        "coverage[toml]",
        "rich",
        "mpmath",
        "streamlit",
    )
    session.run("pytest", "--ignore=tests/tools/e2e", *args)


@nox.session(python=multi_python_versions_support)
def testsnb(session):
    import os

    args = ["--nbmake", "examples"]
    install_with_constraints(
        session,
        ".[cplex,gekko,draw]",
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
        "mpmath",
        "streamlit",
    )
    session.run("pytest", "--ignore=tests/tools/e2e", *args)


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
        session,
        ".[cplex,gekko,draw,tools]",
        "sphinx>=5.0",
        "myst-parser",
        "https://github.com/analogdevicesinc/doctools/releases/download/latest/adi-doctools.tar.gz",
        "sphinxcontrib-mermaid",
        "sphinx-simplepdf",
        "pillow",
        "sphinx-exec-code",
    )
    (session.chdir("doc"),)
    session.run("sphinx-build", "source", "build", "-W", "-jauto")


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


@nox.session(python=main_python)
def release(session: Session) -> None:
    """Generate release."""
    install_with_constraints(session, "numpy")

    session.run("uv", "build")


@nox.session(python=main_python)
def teste2e(session: Session) -> None:
    """Run E2E tests with Playwright."""
    args = session.posargs or []
    install_with_constraints(
        session,
        ".[cplex,gekko,draw,tools,e2e]",
        "pytest",
        "pytest-timeout",
        "pytest-xdist",
        "playwright",
        "pytest-playwright",
        "pytest-base-url",
        "pillow",
        "pixelmatch",
    )
    session.run("playwright", "install", "chromium")
    session.run("pytest", "tests/tools/e2e", "-v", "--timeout=30", *args)


@nox.session(python=main_python)
def teste2e_update_baselines(session: Session) -> None:
    """Update visual regression baselines."""
    install_with_constraints(
        session,
        ".[cplex,gekko,draw,tools,e2e]",
        "pytest",
        "pytest-timeout",
        "playwright",
        "pytest-playwright",
        "pillow",
    )
    session.run("playwright", "install", "chromium")
    session.run(
        "pytest",
        "tests/tools/e2e/test_visual_regression_e2e.py",
        "--update-baselines",
        "-v",
        "--timeout=60",
    )
