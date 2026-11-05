"""Tests for the Frequency Planner page and its frame helpers."""

import pathlib
import sys

from streamlit.testing.v1 import AppTest

from adijif.freqplan import (
    compute_rx,
    default_rx_plan,
    default_tx_plan,
    dumps,
    evaluate_output,
    loads,
    plan_to_dict,
)
from adijif.tools.explorer.src.pages.helpers.freqplan_frames import (
    rx_frames_from_plan,
    rx_plan_from_frames,
    stage_caption,
    tx_frames_from_plan,
    tx_plan_from_frames,
    verdict_line,
)

app_path = (
    pathlib.Path(__file__).parent.parent.parent
    / "adijif"
    / "tools"
    / "explorer"
)
app_file_path = app_path / "main.py"

sys.path.append(str(app_path))

GLYPHS = ("✓", "⚠", "✗")


def navigate_to_planner(at: AppTest) -> AppTest:
    """Navigate the sidebar to the Frequency Planner page."""
    for item in at.sidebar.radio:
        if item.label == "Select a Tool":
            item.set_value("Frequency Planner").run(timeout=30)
            break
    return at


def _loaded() -> AppTest:
    at = AppTest.from_file(app_file_path).run(timeout=30)
    return navigate_to_planner(at)


def test_frequencyplanner_loads() -> None:
    """The page renders without exceptions."""
    at = _loaded()
    assert not at.exception
    assert at.title[0].value == "Frequency Planner"


def test_frequencyplanner_default_verdicts() -> None:
    """Default plan shows ok verdicts and no errors."""
    at = _loaded()
    assert not at.exception
    texts = [m.value for m in at.markdown]
    assert any("✓" in t for t in texts)
    assert not any("✗" in t for t in texts)
    # Four Rx outputs plus four DACs, all ok.
    assert sum(t.startswith("✓") for t in texts) == 8


def test_frequencyplanner_glyphs_only_in_verdicts() -> None:
    """Glyphs appear only on verdict markdown lines."""
    at = _loaded()
    for group in (at.caption, at.warning, at.error, at.info, at.subheader):
        for el in group:
            assert not any(g in str(el.value) for g in GLYPHS)


def test_frequencyplanner_hide_kind() -> None:
    """Hiding the fddc kind on Rx hides its charts and verdicts."""
    at = _loaded()
    pills = {p.key: p for p in at.pills}
    pills["fp_rx_kinds"].unselect("fddc").run(timeout=30)
    assert not at.exception
    caps = [c.value for c in at.caption]
    assert not any(c.startswith("fddc") for c in caps)
    assert any(c.startswith("cddc0") for c in caps)


def test_frequencyplanner_disable_cddc_hides_it() -> None:
    """Disabled CDDC rows produce no stage (helper level)."""
    rx = default_rx_plan()
    fr = rx_frames_from_plan(rx)
    fr["cddc"].loc["cddc1", "enabled"] = False
    plan = rx_plan_from_frames(
        "AD9084", 20000.0, 0.8, fr["signals"], fr["cddc"], fr["fddc"], fr
    )
    res = compute_rx(plan)
    assert "cddc1" not in res.stages
    assert res.stages["fddc2"].error


def test_fddc0_decimation_16_warns() -> None:
    """FDDC0 at decimation 16 only partially captures S1."""
    rx = default_rx_plan()
    fr = rx_frames_from_plan(rx)
    fr["fddc"].loc["fddc0", "decimation"] = 16
    plan = rx_plan_from_frames(
        "AD9084", 20000.0, 0.8, fr["signals"], fr["cddc"], fr["fddc"], fr
    )
    res = compute_rx(plan)
    sigs = {s.name: s for s in plan.signals}
    v = evaluate_output(res.stages["fddc0"], sigs, plan.targets["fddc0"])
    assert v.status == "warn"
    assert verdict_line(v).startswith("⚠")
    assert "250 of 400 MHz" in verdict_line(v)


def test_rx_frames_roundtrip_default() -> None:
    """Frames built from the default plan rebuild the same plan."""
    rx = default_rx_plan()
    fr = rx_frames_from_plan(rx)
    plan = rx_plan_from_frames(
        "AD9084", 20000.0, 0.8, fr["signals"], fr["cddc"], fr["fddc"], fr
    )
    assert plan_to_dict(plan, None) == plan_to_dict(rx, None)


def test_tx_frames_roundtrip_default() -> None:
    """Tx frames built from the default plan rebuild the same plan."""
    tx = default_tx_plan()
    fr = tx_frames_from_plan(tx)
    plan = tx_plan_from_frames(
        "AD9084",
        20000.0,
        0.8,
        fr["cduc_interp"],
        fr["fduc_interp"],
        fr["signals"],
        fr["cduc"],
        fr["fduc"],
        fr,
    )
    assert plan_to_dict(None, plan) == plan_to_dict(None, tx)


def test_export_load_roundtrip() -> None:
    """Export then load through the page's frame path restores the plan."""
    rx = default_rx_plan()
    tx = default_tx_plan()
    rx.datapath.fddc_decimations[0] = 16
    rx.datapath.cddc_nco_phases = [1, 2, 3, 4]
    rx.signals[0].center_hz = 1.25e9
    rx.alpha = tx.alpha = 0.7
    tx.datapath.cduc_sources = [[1], [2], [3], [4]]
    tx.datapath.fduc_nco_frequencies[0] = 50e6
    view = {"rx": {"hidden_kinds": ["adc"], "show_alias": False}}
    text = dumps(rx, tx, view)

    rx2, tx2, view2 = loads(text)
    assert rx2 is not None and tx2 is not None
    rfr = rx_frames_from_plan(rx2)
    tfr = tx_frames_from_plan(tx2)
    rxp = rx_plan_from_frames(
        rx2.part,
        rx2.adc_rate_hz / 1e6,
        rx2.alpha,
        rfr["signals"],
        rfr["cddc"],
        rfr["fddc"],
        rfr,
    )
    txp = tx_plan_from_frames(
        tx2.part,
        tx2.dac_rate_hz / 1e6,
        tx2.alpha,
        tfr["cduc_interp"],
        tfr["fduc_interp"],
        tfr["signals"],
        tfr["cduc"],
        tfr["fduc"],
        tfr,
    )
    assert view2 == view
    assert plan_to_dict(rxp, txp, view2) == plan_to_dict(rx, tx, view)


def test_signal_rows_with_blanks_skipped() -> None:
    """Rows with an empty name or NaN values are ignored."""
    rx = default_rx_plan()
    fr = rx_frames_from_plan(rx)
    sig = fr["signals"]
    sig.loc[len(sig)] = ["", 100.0, 10.0, 0]
    sig.loc[len(sig)] = ["X", float("nan"), 10.0, 0]
    sig.loc[len(sig)] = [None, None, None, None]
    plan = rx_plan_from_frames(
        "AD9084", 20000.0, 0.8, sig, fr["cddc"], fr["fddc"], fr
    )
    assert [s.name for s in plan.signals] == ["S1", "S2", "S3", "S4"]


def test_stage_caption() -> None:
    """Captions show channel, NCO, ratio and rate, or the error."""
    res = compute_rx(default_rx_plan())
    cap = stage_caption(res.stages["cddc0"], 1200.0, "÷4")
    assert cap.startswith("cddc0")
    assert "1200 MHz" in cap and "÷4" in cap and "5000 MSPS" in cap
    st_err = res.stages["cddc0"]
    st_err.error = "source CDDC1 is disabled"
    st_err.rate_hz = 0.0
    cap = stage_caption(st_err, None, None)
    assert "source CDDC1 is disabled" in cap
    assert "MSPS" not in cap


def _upload_script(app_dir: str) -> None:
    """Render the planner after applying a fake upload from state."""
    import sys

    sys.path.insert(0, app_dir)
    import streamlit as st
    from src.pages.frequencyplanner import FrequencyPlanner, apply_upload

    class _File:
        def __init__(self, file_id: str, text: str) -> None:
            self.file_id = file_id
            self._text = text

        def getvalue(self) -> bytes:
            return self._text.encode()

    up = st.session_state.get("test_upload")
    if up is not None:
        apply_upload(_File(*up))
    FrequencyPlanner(None).write()


def _upload_app() -> AppTest:
    return AppTest.from_function(_upload_script, args=(str(app_path),))


def test_load_config_restores_plan_and_view() -> None:
    """Loading a config replaces the plan, alpha and view, once per file."""
    rx = default_rx_plan()
    tx = default_tx_plan()
    rx.datapath.fddc_decimations[0] = 16
    rx.alpha = tx.alpha = 0.7
    view = {"rx": {"hidden_kinds": ["adc"], "show_alias": False}}
    at = _upload_app().run(timeout=30)
    assert not at.exception
    at.session_state["test_upload"] = ("f1", dumps(rx, tx, view))
    at.run(timeout=30)
    assert not at.exception
    assert at.slider(key="fp_alpha").value == 0.7
    assert at.toggle(key="fp_rx_alias").value is False
    caps = [c.value for c in at.caption]
    assert not any(c.startswith("adc") for c in caps)
    assert any(c.startswith("dac0") for c in caps)
    assert any(m.value.startswith("⚠") for m in at.markdown)
    # Same file on later reruns is not re-applied.
    at.slider(key="fp_alpha").set_value(0.75).run(timeout=30)
    assert at.slider(key="fp_alpha").value == 0.75


def test_load_bad_config_keeps_plan() -> None:
    """A bad config shows an error and keeps the current plan."""
    at = _upload_app().run(timeout=30)
    at.session_state["test_upload"] = ("bad", "{not json")
    at.run(timeout=30)
    assert not at.exception
    assert any("Invalid JSON" in e.value for e in at.error)
    assert at.slider(key="fp_alpha").value == 0.8
    assert sum(m.value.startswith("✓") for m in at.markdown) == 8


def test_alpha_survives_page_switch() -> None:
    """Widget values persist when navigating away and back."""
    at = _loaded()
    at.slider(key="fp_alpha").set_value(0.7).run(timeout=30)
    for item in at.sidebar.radio:
        if item.label == "Select a Tool":
            item.set_value("Basic JESD204 Calculator").run(timeout=30)
    navigate_to_planner(at)
    assert not at.exception
    assert at.slider(key="fp_alpha").value == 0.7
