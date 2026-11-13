"""Explorer controls for explicit ADRV9042 profile settings."""

from streamlit.testing.v1 import AppTest


def test_standalone_reference_and_instance_controls():
    app = AppTest.from_string("""
import adijif
from adijif.tools.explorer.src.pages.helpers.adrv9042 import select_link, configure_link
link = select_link(adijif.adrv9042_tx(), "test")
configure_link(link, "test")
import streamlit as st
st.json({"link_index": link.link_index, "reference_clock": link.reference_clock, "E": link.E})
""").run(timeout=30)
    assert not app.exception
    app.selectbox(key="test_link_index").set_value(1).run()
    app.number_input(key="test_reference_clock").set_value(122_880_000).run()
    assert not app.exception
    assert "122880000" in app.json[0].value


def test_combined_controls_show_five_links():
    app = AppTest.from_string("""
import adijif
from adijif.tools.explorer.src.pages.helpers.adrv9042 import configure_device
configure_device(adijif.adrv9042())
""").run(timeout=30)
    assert not app.exception
    assert len(app.checkbox) == 5
    assert app.checkbox(key="adrv9042_framer0_enabled").value
    assert not app.checkbox(key="adrv9042_framer2_enabled").value
    app.checkbox(key="adrv9042_framer2_enabled").set_value(True).run()
    assert not app.exception
    assert app.multiselect(key="adrv9042_framer2_lanes")


def test_system_page_exposes_standalone_framing():
    from pathlib import Path

    main = Path(__file__).resolve().parents[2] / "adijif/tools/explorer/main.py"
    app = AppTest.from_file(str(main), default_timeout=30).run()
    app.sidebar.radio[0].set_value("System Configurator").run()
    app.selectbox(key="converter_part_select").set_value("adrv9042_rx").run()
    assert not app.exception
    assert any(widget.label == "K" for widget in app.number_input)
    modes = app.selectbox(key="system_jesd_mode_select")
    modes.set_value(
        next(mode for mode in modes.options if mode.startswith("JESD204C"))
    ).run()
    assert not app.exception
    assert any(widget.label == "E" for widget in app.selectbox)
