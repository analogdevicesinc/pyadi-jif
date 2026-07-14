"""Theme selection coverage for Explorer diagram tools."""

import pytest

import adijif
from adijif.tools.explorer.src.utils import get_diagram_theme


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_explorer_diagram_theme_preserves_known_variants(theme: str) -> None:
    assert get_diagram_theme(theme) == theme


def test_explorer_diagram_theme_defaults_to_light_for_unknown_variant() -> None:
    assert get_diagram_theme("custom") == "light"


def test_component_diagram_theme_is_validated() -> None:
    converter = adijif.ad9680()
    assert converter.diagram_theme == "dark"

    converter.diagram_theme = "light"
    assert converter.diagram_theme == "light"

    with pytest.raises(
        ValueError, match="diagram_theme must be 'light' or 'dark'"
    ):
        converter.diagram_theme = "sepia"
