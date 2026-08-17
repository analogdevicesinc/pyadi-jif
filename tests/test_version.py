"""Regression tests for synchronized package-version surfaces."""

import configparser
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]


def extract(pattern: str, path: Path) -> str:
    """Extract one version and fail clearly when its surface disappears."""
    match = re.search(pattern, path.read_text(), re.MULTILINE)
    assert match, f"Could not find a managed version in {path}"
    return match.group(1)


def test_package_version_surfaces_are_synchronized():
    """Code, packaging, release tooling, and docs expose one version."""
    project_version = extract(r'^version = "([^"]+)"$', ROOT / "pyproject.toml")
    code_version = extract(
        r'^__version__ = "([^"]+)"$', ROOT / "adijif/__init__.py"
    )

    config = configparser.ConfigParser()
    config.read(ROOT / "setup.cfg")
    tool_version = config["bumpversion"]["current_version"]

    sphinx_release = extract(
        r"^release = 'v([^']+)'$",
        ROOT / "doc/source/conf.py",
    )
    documented_version = extract(
        r'"producer": \{\s*"name": "pyadi-jif",\s*"version": "([^"]+)"',
        ROOT / "doc/source/jif_dt.md",
    )

    assert {
        project_version,
        code_version,
        tool_version,
        sphinx_release,
        documented_version,
    } == {project_version}
