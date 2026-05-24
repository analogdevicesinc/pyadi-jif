"""Streamlit testing for the ADF4030 System Designer page."""

import pathlib
import sys
import time

import pytest
from streamlit.testing.v1 import AppTest

app_path = (
    pathlib.Path(__file__).parent.parent.parent
    / "adijif"
    / "tools"
    / "explorer"
)
app_file_path = app_path / "main.py"
sys.path.append(str(app_path))

_APP_TIMEOUT = 30


def _new_app():
    return AppTest.from_file(app_file_path, default_timeout=_APP_TIMEOUT).run()


def _navigate(at: AppTest) -> AppTest:
    for item in at.sidebar.radio:
        if item.label == "Select a Tool":
            item.set_value("ADF4030 System Designer").run()
            break
    time.sleep(0.5)
    return at


@pytest.mark.parametrize("arch", ["cascade", "tree", "hybrid", "hybrid2"])
def test_adf4030_system_designer_renders(arch: str) -> None:
    at = _navigate(_new_app())
    # Find and set the architecture selectbox.
    for sb in at.selectbox:
        if sb.key == "adf4030_architecture":
            sb.set_value(arch).run()
            break
    else:
        raise AssertionError("architecture selectbox not found")
    assert not at.exception
