"""Streamlit testing for landing page"""

import pathlib
import sys
import time

from streamlit.testing.v1 import AppTest

app_path = (
    pathlib.Path(__file__).parent.parent.parent
    / "adijif"
    / "tools"
    / "explorer"
)
app_file_path = app_path / "main.py"

sys.path.append(str(app_path))


def test_landing_page_basic() -> None:
    """Test basic jesd mode selector page loading."""
    at = AppTest.from_file(app_file_path).run()

    # Navigate to the JESD Mode Selector page
    # sb = at.sidebar
    # set_item(sb, "radio", "Select a Tool", "JESD204 Mode Selector")
    time.sleep(1)

    # Verify page title
    assert len(at.title) > 0
    assert at.title[0].value == "Table of Contents"

    # Check that help button exists
    assert len(at.button) > 0
    help_button_found = False
    for button in at.button:
        if button.label == "Help":
            help_button_found = True
            break
    assert help_button_found, "Help button not found"
