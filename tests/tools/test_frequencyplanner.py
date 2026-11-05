"""Tests for the Frequency Planner page and its frame helpers."""

import pathlib
import sys

from streamlit.testing.v1 import AppTest

from adijif.freqplan import (
    compute_rx,
    compute_tx,
    default_rx_plan,
    default_tx_plan,
    dumps,
    evaluate_output,
    loads,
    plan_to_dict,
)
from adijif.tools.explorer.src.pages.helpers.freqplan_frames import (
    parse_dac_routing,
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
        dac=fr["dac"],
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
        dac=tfr["dac"],
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


def test_load_out_of_range_config_keeps_plan() -> None:
    """Values outside the widget bounds are rejected, not crashed on."""
    rx = default_rx_plan()
    tx = default_tx_plan()
    rx.alpha = tx.alpha = 0.4
    at = _upload_app().run(timeout=30)
    at.session_state["test_upload"] = ("lo_alpha", dumps(rx, tx))
    at.run(timeout=30)
    assert not at.exception
    assert any("alpha 0.4" in e.value for e in at.error)
    assert at.slider(key="fp_alpha").value == 0.8

    tx = default_tx_plan()
    tx.datapath.cduc_interpolation = 5
    at.session_state["test_upload"] = ("bad_interp", dumps(None, tx))
    at.run(timeout=30)
    assert not at.exception
    assert any("CDUC interpolation 5" in e.value for e in at.error)
    assert at.selectbox(key="fp_tx_cduc_interp").value == 4


def _bad_configs() -> list[tuple[str, str, str]]:
    """Configs with out-of-range indices, with the expected error text."""
    out = []

    def add(name: str, expect: str, mut_rx=None, mut_tx=None) -> None:
        rx, tx = default_rx_plan(), default_tx_plan()
        if mut_rx:
            mut_rx(rx)
        if mut_tx:
            mut_tx(tx)
        out.append((name, dumps(rx, tx), expect))

    add("a2c", "cddc0 ADC 4", mut_rx=lambda r: r.adc_to_cddc.__setitem__(0, 4))
    add(
        "fddc_src",
        "fddc0 source CDDC 5",
        mut_rx=lambda r: r.datapath.fddc_source.__setitem__(0, 5),
    )
    add(
        "cddc_dec",
        "cddc0 decimation 5",
        mut_rx=lambda r: r.datapath.cddc_decimations.__setitem__(0, 5),
    )
    add(
        "fddc_dec",
        "fddc0 decimation 5",
        mut_rx=lambda r: r.datapath.fddc_decimations.__setitem__(0, 5),
    )
    add(
        "rx_sig",
        "signal S1 ADC 7",
        mut_rx=lambda r: setattr(r.signals[0], "source", 7),
    )
    add(
        "fduc_src",
        "fduc0 source CDUC 5",
        mut_tx=lambda t: t.datapath.fduc_source.__setitem__(0, 5),
    )
    add(
        "cduc_src",
        "dac0 CDUC 9",
        mut_tx=lambda t: setattr(
            t.datapath, "cduc_sources", [[9], [1], [3], [3]]
        ),
    )
    add(
        "tx_sig",
        "signal S1 FDUC 8",
        mut_tx=lambda t: setattr(t.signals[0], "source", 8),
    )
    return out


def test_load_out_of_range_indices_keeps_plan() -> None:
    """Out-of-range routing, sources and ratios are rejected on load."""
    at = _upload_app().run(timeout=30)
    for name, text, expect in _bad_configs():
        at.session_state["test_upload"] = (name, text)
        at.run(timeout=30)
        assert not at.exception, name
        errs = [e.value for e in at.error]
        assert any(expect in e for e in errs), (name, errs)
        assert sum(m.value.startswith("\u2713") for m in at.markdown) == 8


def test_parse_dac_routing() -> None:
    """DAC routing text parses to 1-indexed CDUC lists, skipping junk."""
    fr = tx_frames_from_plan(default_tx_plan())
    dac = fr["dac"]
    assert list(dac["cducs"]) == ["1", "1", "3", "3"]
    dac.loc["dac0", "cducs"] = "1, 3"
    dac.loc["dac1", "cducs"] = "x, 9, 2"
    dac.loc["dac2", "cducs"] = ""
    routing, notes = parse_dac_routing(dac, 4)
    assert routing == [[1, 3], [2], [], [3]]
    assert len(notes) == 2
    assert any("'x'" in n for n in notes)
    assert any("9" in n for n in notes)


def test_dac_routing_in_plan() -> None:
    """Edited DAC routing reaches the Tx plan and its DAC outputs."""
    tx = default_tx_plan()
    fr = tx_frames_from_plan(tx)
    fr["dac"].loc["dac1", "cducs"] = "3"
    notes: list[str] = []
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
        dac=fr["dac"],
        notes=notes,
    )
    assert plan.datapath.cduc_sources == [[1], [3], [3], [3]]
    assert notes == []
    res = compute_tx(plan)
    assert {s.signal for s in res.stages["dac1"].spans} == {"S2"}


def test_dac_caption_notes_two_nyquist_zones() -> None:
    """DAC captions say the row spans the first two Nyquist zones."""
    res = compute_tx(default_tx_plan())
    cap = stage_caption(res.stages["dac0"], None, None)
    assert "Nyquist zones 1-2" in cap
    rx = compute_rx(default_rx_plan())
    assert "Nyquist" not in stage_caption(rx.stages["adc0"], None, None)


def test_dac_nco_above_half_fs_verdict_ok() -> None:
    """A DAC NCO of 12 GHz at 20 GSPS gives a full-capture ok verdict."""
    from adijif.freqplan import evaluate_dac

    tx = default_tx_plan()
    tx.cduc_dac_hz[0] = 12e9
    res = compute_tx(tx)
    sigs = {s.name: s for s in tx.signals}
    line = verdict_line(evaluate_dac(res.stages["dac0"], sigs))
    assert line.startswith("✓")
    assert "S1: 400 of 400 MHz captured" in line


def _malformed_configs() -> list[tuple[str, str, str]]:
    """Configs whose rx section is valid (and non-default) but which fail
    later, so a partial load would visibly change the Rx verdicts."""
    import json

    rx, tx = default_rx_plan(), default_tx_plan()
    rx.datapath.fddc_decimations[0] = 16
    out = []
    for name, view, expect in (
        ("view_str", {"rx": "junk"}, "view.rx must be an object"),
        ("view_list", {"tx": {"hidden_kinds": 5}}, "hidden_kinds"),
        ("view_top", ["rx"], "view must be an object"),
    ):
        d = plan_to_dict(rx, tx)
        d["view"] = view
        out.append((name, json.dumps(d), expect))
    d = plan_to_dict(rx, tx)
    d["part"] = ["AD9084"]
    out.append(("part_list", json.dumps(d), "'part' must be a string"))
    d = plan_to_dict(rx, tx)
    d["tx"]["datapath"]["fduc"]["nco_frequencies"][0] = "abc"
    out.append(("tx_nco_str", json.dumps(d), "Malformed config"))
    return out


def test_load_malformed_config_keeps_plan() -> None:
    """Malformed view/part/tx show an error and leave both tabs unchanged."""
    at = _upload_app().run(timeout=30)
    for name, text, expect in _malformed_configs():
        at.session_state["test_upload"] = (name, text)
        at.run(timeout=30)
        assert not at.exception, (name, at.exception)
        errs = [e.value for e in at.error]
        assert any(expect in e for e in errs), (name, errs)
        assert sum(m.value.startswith("✓") for m in at.markdown) == 8, name
        assert not any(m.value.startswith("⚠") for m in at.markdown), name
