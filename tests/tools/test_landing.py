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
    assert at.title[0].value == "PyADI-JIF Tools"

    # Check that help button exists
    assert len(at.button) > 0
    help_button_found = False
    for button in at.button:
        if button.label == "Help":
            help_button_found = True
            break
    assert help_button_found, "Help button not found"


def test_landing_page_lists_frequency_planner() -> None:
    """The landing page has a card for the Frequency Planner."""
    at = AppTest.from_file(app_file_path).run()
    assert not at.exception
    subheaders = [s.value for s in at.subheader]
    assert any(s.endswith(" Frequency Planner") for s in subheaders)


def test_landing_cards_have_icons() -> None:
    """Every landing card title starts with its Material icon."""
    from adijif.tools.explorer.src.pages.landing import CARD_ICONS

    at = AppTest.from_file(app_file_path).run()
    assert not at.exception
    subheaders = [s.value for s in at.subheader]
    assert subheaders == [
        f":material/{icon}: {title}" for title, icon in CARD_ICONS.items()
    ]


def test_landing_cards_open_their_tool() -> None:
    """Clicking a tool card's button switches to that tool's page."""
    from adijif.tools.explorer.src.pages import PAGE_MAP
    from adijif.tools.explorer.src.pages.landing import CARD_PAGES, _slug

    for title, page in CARD_PAGES.items():
        at = AppTest.from_file(app_file_path).run()
        at.button(key=f"open_{_slug(title)}").click().run()
        # Only the switch is checked here; each tool's own tests cover it
        # rendering (some draw diagrams that need optional extras).
        assert at.sidebar.radio[0].value == page
        assert at.title[0].value == PAGE_MAP[page].name


def test_general_information_card_is_not_a_button() -> None:
    """Only tool cards are buttons."""
    at = AppTest.from_file(app_file_path).run()
    keys = {b.key for b in at.button}
    assert "open_general_information" not in keys
    assert len([k for k in keys if k and k.startswith("open_")]) == 6


def test_sidebar_links_to_docs() -> None:
    """The sidebar has a link button to the PyADI-JIF docs."""
    at = AppTest.from_file(app_file_path).run()
    links = [
        e
        for e in at.sidebar.get("link_button")
        if getattr(e, "proto", None) is not None
    ]
    assert any(
        e.proto.url == "https://analogdevicesinc.github.io/pyadi-jif/"
        for e in links
    )
