"""Tests for the Frequency Planner page and its frame helpers."""

import pathlib
import sys

import pandas as pd
import pytest
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
    apply_editor_delta,
    merge_input_signals,
    parse_dac_routing,
    rx_frames_from_plan,
    rx_plan_from_frames,
    set_block_field,
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


def _is_verdict_line(text: str) -> bool:
    """True for a verdict line, optionally prefixed by a bold path label."""
    if text.startswith(GLYPHS):
        return True
    head, sep, tail = text.partition(" — ")
    return bool(sep) and head.startswith("**") and tail.startswith(GLYPHS)


def _tab(at: AppTest, label: str):
    """The Rx or Tx tab block."""
    return next(t for t in at.tabs if t.label == label)


def _verdicts(node) -> list[str]:
    """Verdict lines rendered under ``node``."""
    return [m.value for m in node.markdown if _is_verdict_line(m.value)]


def _charts(node) -> list:
    """Vega-Lite charts rendered under ``node`` (diagram plus spectra)."""
    return list(node.get("vega_lite_chart"))


def _panel(widgets, prefix: str):
    """The panel widget whose key starts with ``prefix``."""
    found = [w for w in widgets if w.key and w.key.startswith(prefix)]
    assert len(found) == 1, (prefix, [w.key for w in widgets])
    return found[0]


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
    # One selected path per tab (Rx FDDC0, Tx S1 on DAC0), both ok.
    assert sum(t.startswith("✓") for t in texts) == 2


def test_frequencyplanner_glyphs_only_in_verdicts() -> None:
    """Glyphs appear only on verdict markdown lines."""
    at = _loaded()
    at.session_state["fp_tx_path"] = "all"
    at.run(timeout=30)
    for group in (at.caption, at.warning, at.error, at.info, at.subheader):
        for el in group:
            assert not any(g in str(el.value) for g in GLYPHS)
    for m in at.markdown:
        if any(g in m.value for g in GLYPHS):
            assert _is_verdict_line(m.value), m.value
    for sc in at.segmented_control:
        assert not any(g in str(o) for o in sc.options for g in GLYPHS)


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
    assert not at.error
    caps = [c.value for c in at.caption]
    assert any(c.startswith("fddc0") for c in caps)
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
    assert sum(m.value.startswith("✓") for m in at.markdown) == 2


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
        assert sum(m.value.startswith("\u2713") for m in at.markdown) == 2


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
        ("view_path", {"tx": {"path": 5}}, "view.tx.path"),
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
        assert sum(m.value.startswith("✓") for m in at.markdown) == 2, name
        assert not any(m.value.startswith("⚠") for m in at.markdown), name


def _switch_page(at: AppTest, page: str) -> None:
    for item in at.sidebar.radio:
        if item.label == "Select a Tool":
            item.set_value(page).run(timeout=30)


def _edit(at: AppTest, edits: dict) -> None:
    """Apply data-editor cell edits the way the frontend reports them.

    AppTest does not resend data-editor state on later runs, so all edits
    for one step are applied in a single run.

    Args:
        at: The app under test.
        edits: Editor key prefix to ``(row, column, value)``.
    """
    gen = at.session_state["fp_editor_gen"]
    for editor, (row, col, value) in edits.items():
        at.session_state[f"{editor}_{gen}"] = {
            "edited_rows": {row: {col: value}},
            "added_rows": [],
            "deleted_rows": [],
        }
    at.run(timeout=30)


def test_table_edits_survive_page_switch() -> None:
    """Rx and Tx table edits persist when navigating away and back."""
    at = _loaded()
    _edit(
        at,
        {
            "fp_rx_cddc": (0, "rf_mhz", 1300.0),
            "fp_tx_cduc": (0, "dac_nco_mhz", 3500.0),
        },
    )
    caps = [c.value for c in at.caption]
    assert any(c.startswith("cddc0 · NCO 1300 MHz") for c in caps)
    assert any(c.startswith("cduc0 · NCO 3500 MHz") for c in caps)
    _switch_page(at, "Basic JESD204 Calculator")
    navigate_to_planner(at)
    assert not at.exception
    caps = [c.value for c in at.caption]
    assert any(c.startswith("cddc0 · NCO 1300 MHz") for c in caps), caps
    assert any(c.startswith("cduc0 · NCO 3500 MHz") for c in caps), caps
    # A later edit on top of the restored tables still applies.
    at.session_state["fp_rx_path"] = "fddc2"
    _edit(at, {"fp_rx_cddc": (1, "rf_mhz", 2100.0)})
    caps = [c.value for c in at.caption]
    assert any(c.startswith("cddc1 · NCO 2100 MHz") for c in caps), caps
    live = at.session_state["fp_rx_live"]["cddc"]
    assert live.loc["cddc0", "rf_mhz"] == 1300.0


def test_editor_generation_stable_on_rerun() -> None:
    """Plain reruns keep the editor generation (no editor reset)."""
    at = _loaded()
    gen = at.session_state["fp_editor_gen"]
    _edit(at, {"fp_rx_cddc": (0, "rf_mhz", 1300.0)})
    at.run(timeout=30)
    assert at.session_state["fp_editor_gen"] == gen


def test_reset_and_upload_not_overridden_by_live_tables() -> None:
    """Reset after an edit restores defaults rather than the edited table."""
    at = _loaded()
    _edit(at, {"fp_rx_cddc": (0, "rf_mhz", 1300.0)})
    at.button(key="fp_reset").click().run(timeout=30)
    caps = [c.value for c in at.caption]
    assert any(c.startswith("cddc0 · NCO 1200 MHz") for c in caps), caps


def test_set_block_field() -> None:
    """Writes land in the right frame, keep dtypes and reach the plan."""
    fr = rx_frames_from_plan(default_rx_plan())
    set_block_field(fr, "cddc0", "rf_mhz", 1600.0)
    set_block_field(fr, "fddc1", "decimation", 8)
    set_block_field(fr, "cddc1", "enabled", False)
    plan = rx_plan_from_frames(
        "AD9084", 20000.0, 0.8, fr["signals"], fr["cddc"], fr["fddc"], fr
    )
    assert plan.cddc_rf_hz[0] == 1.6e9
    assert plan.datapath.fddc_decimations[1] == 8
    assert fr["cddc"]["enabled"].dtype == bool
    assert pd.api.types.is_integer_dtype(fr["fddc"]["decimation"])
    tx = tx_frames_from_plan(default_tx_plan())
    set_block_field(tx, "dac0", "cducs", "1")
    assert tx["dac"].loc["dac0", "cducs"] == "1"
    with pytest.raises(ValueError):
        set_block_field(fr, "cddc0", "bogus", 1)
    with pytest.raises(ValueError):
        set_block_field(fr, "cddc99", "rf_mhz", 1.0)
    with pytest.raises(ValueError):
        set_block_field(fr, "dac0", "cducs", "1")


def test_apply_editor_delta() -> None:
    """Edits, additions and deletions apply to a copy of the frame."""
    df = pd.DataFrame(
        {
            "name": ["A", "B"],
            "center_mhz": [1.0, 2.0],
            "bw_mhz": [10.0, 20.0],
            "adc": [0, 1],
        }
    )
    delta = {
        "edited_rows": {1: {"bw_mhz": 25.0}},
        "added_rows": [{"name": "C", "center_mhz": 3.0, "adc": 2}],
        "deleted_rows": [0],
    }
    out = apply_editor_delta(df, delta)
    assert list(out["name"]) == ["B", "C"]
    assert out["bw_mhz"].iloc[0] == 25.0
    assert pd.isna(out["bw_mhz"].iloc[1])
    assert list(out.index) == [0, 1]
    assert df["bw_mhz"].tolist() == [10.0, 20.0]
    str_keys = {"edited_rows": {"1": {"bw_mhz": 25.0}}, "deleted_rows": ["0"]}
    out2 = apply_editor_delta(df, str_keys)
    assert list(out2["name"]) == ["B"]
    assert out2["bw_mhz"].iloc[0] == 25.0
    assert apply_editor_delta(df, {}).equals(df)


def test_merge_input_signals() -> None:
    """Replacing one input's rows keeps the others in order."""
    sig = rx_frames_from_plan(default_rx_plan())["signals"]
    edited = pd.DataFrame(
        {
            "name": ["S2", "S5"],
            "center_mhz": [2000.0, 3000.0],
            "bw_mhz": [100.0, 50.0],
            "adc": [9, 9],
        }
    )
    out = merge_input_signals(sig, "adc", 1, edited)
    assert list(out["name"]) == ["S1", "S2", "S5", "S3", "S4"]
    assert out.loc[out["name"].isin(["S2", "S5"]), "adc"].tolist() == [1, 1]
    assert list(out.index) == list(range(5))
    none = merge_input_signals(sig, "adc", 7, edited)
    assert list(none["name"]) == ["S1", "S2", "S3", "S4", "S2", "S5"]


def test_default_shows_one_path() -> None:
    """Each tab draws the diagram plus one path's three spectra."""
    at = _loaded()
    assert not at.exception
    assert len(_charts(at)) == 8
    for label in ("Rx", "Tx"):
        tab = _tab(at, label)
        assert len(_charts(tab)) == 4, label
        lines = _verdicts(tab)
        assert len(lines) == 1, (label, lines)
        assert lines[0].startswith("✓")
    assert at.session_state["fp_rx_path"] == "fddc0"
    assert at.session_state["fp_tx_path"] == "S1@dac0"


def test_select_path_shows_its_stages() -> None:
    """Selecting a path shows only that path's stages."""
    at = _loaded()
    at.session_state["fp_rx_path"] = "fddc2"
    at.run(timeout=30)
    assert not at.exception
    caps = [c.value for c in _tab(at, "Rx").caption]
    for name in ("adc1", "cddc1", "fddc2"):
        assert any(c.startswith(name) for c in caps), (name, caps)
    assert not any(c.startswith("fddc0") for c in caps), caps


def test_all_outputs_lists_every_verdict() -> None:
    """The All outputs view lists every Rx output and draws no spectra."""
    at = _loaded()
    at.session_state["fp_rx_path"] = "all"
    at.run(timeout=30)
    assert not at.exception
    tab = _tab(at, "Rx")
    lines = _verdicts(tab)
    assert len(lines) == 4, lines
    assert all(line.startswith("**") for line in lines)
    assert len(_charts(tab)) == 1


def test_tx_path_signal_listed_first() -> None:
    """A Tx path's verdict line leads with that path's own signal."""
    at = _loaded()
    at.session_state["fp_tx_block"] = "dac2"
    at.run(timeout=30)
    _panel(at.text_input, "fp_tx_pn_dac2_cducs").input("1, 3").run(timeout=30)
    assert not at.exception
    assert (
        at.session_state["fp_tx_frames"]["dac"].loc["dac2", "cducs"] == "1, 3"
    )
    for sig in ("S1", "S2"):
        at.session_state["fp_tx_path"] = f"{sig}@dac2"
        at.run(timeout=30)
        assert not at.exception
        lines = _verdicts(_tab(at, "Tx"))
        assert len(lines) == 1
        assert lines[0][2:].startswith(sig), lines
        assert "S1" in lines[0] and "S2" in lines[0], lines


def test_cddc_direct_path_two_charts() -> None:
    """Disabling FDDC0 in the panel makes CDDC0 a two-stage path."""
    at = _loaded()
    at.session_state["fp_rx_block"] = "fddc0"
    at.run(timeout=30)
    assert _tab(at, "Rx").subheader[0].value.startswith("FDDC0")
    _panel(at.checkbox, "fp_rx_pn_fddc0_enabled").uncheck().run(timeout=30)
    assert not at.exception
    assert not at.session_state["fp_rx_frames"]["fddc"].loc["fddc0", "enabled"]
    at.session_state["fp_rx_path"] = "cddc0"
    at.run(timeout=30)
    assert not at.exception
    tab = _tab(at, "Rx")
    caps = [c.value for c in tab.caption]
    assert "CDDC output, no FDDC" in caps, caps
    assert any(c.startswith("cddc0") for c in caps)
    assert len(_charts(tab)) == 3


def test_disabled_cddc_path_shows_error() -> None:
    """A path through a disabled CDDC shows its error, not a crash."""
    at = _loaded()
    at.session_state["fp_rx_block"] = "cddc1"
    at.run(timeout=30)
    _panel(at.checkbox, "fp_rx_pn_cddc1_enabled").uncheck().run(timeout=30)
    at.session_state["fp_rx_path"] = "fddc2"
    at.run(timeout=30)
    assert not at.exception
    tab = _tab(at, "Rx")
    caps = [c.value for c in tab.caption]
    assert any(c.startswith("cddc1") and "disabled" in c for c in caps), caps
    lines = _verdicts(tab)
    assert len(lines) == 1 and lines[0].startswith("✗"), lines


def test_panel_edit_updates_plan() -> None:
    """Editing the CDDC0 RF NCO in the panel reaches the plan."""
    at = _loaded()
    at.session_state["fp_rx_block"] = "cddc0"
    at.run(timeout=30)
    _panel(at.number_input, "fp_rx_pn_cddc0_rf_mhz").set_value(1600.0).run(
        timeout=30
    )
    assert not at.exception
    caps = [c.value for c in at.caption]
    assert any(c.startswith("cddc0 · NCO 1600 MHz") for c in caps), caps


def test_panel_then_table_edit() -> None:
    """Panel and table edits feed the same source frames, neither lost."""
    at = _loaded()
    at.session_state["fp_rx_block"] = "cddc0"
    at.run(timeout=30)
    _panel(at.number_input, "fp_rx_pn_cddc0_rf_mhz").set_value(1600.0).run(
        timeout=30
    )
    cddc = at.session_state["fp_rx_frames"]["cddc"]
    assert cddc.loc["cddc0", "rf_mhz"] == 1600.0
    # A table-originated change (last run's editor output) ...
    live = dict(at.session_state["fp_rx_live"])
    live["cddc"] = live["cddc"].copy()
    live["cddc"].loc["cddc1", "rf_mhz"] = 2100.0
    at.session_state["fp_rx_live"] = live
    # ... survives the next panel edit to another field.
    _panel(at.selectbox, "fp_rx_pn_cddc0_decimation").set_value(6).run(
        timeout=30
    )
    assert not at.exception
    cddc = at.session_state["fp_rx_frames"]["cddc"]
    assert cddc.loc["cddc0", "rf_mhz"] == 1600.0
    assert cddc.loc["cddc0", "decimation"] == 6
    assert cddc.loc["cddc1", "rf_mhz"] == 2100.0


def _signals_edit_script(app_dir: str) -> None:
    """Render the planner, applying a panel signals-editor delta first."""
    import sys

    sys.path.insert(0, app_dir)
    import streamlit as st
    from src.pages import frequencyplanner as fp

    delta = st.session_state.get("test_delta")
    if delta is not None:
        key = fp._panel_key("rx", "adc0", "signals")
        st.session_state[key] = delta
        fp._on_signals_edit("rx", 0, key)
        st.session_state["test_delta"] = None
    fp.FrequencyPlanner(None).write()


def test_panel_signals_edit() -> None:
    """The ADC panel's signals editor edits and adds that input's signals."""
    at = AppTest.from_function(_signals_edit_script, args=(str(app_path),))
    at.run(timeout=30)
    assert not at.exception
    at.session_state["test_delta"] = {
        "edited_rows": {0: {"bw_mhz": 300.0}},
        "added_rows": [{"name": "S9", "center_mhz": 1500.0, "bw_mhz": 20.0}],
        "deleted_rows": [],
    }
    at.run(timeout=30)
    assert not at.exception
    sig = at.session_state["fp_rx_frames"]["signals"]
    assert list(sig["name"]) == ["S1", "S9", "S2", "S3", "S4"]
    assert sig.loc[0, "bw_mhz"] == 300.0
    assert sig.loc[1, "adc"] == 0


def test_load_legacy_view_keys() -> None:
    """Old view keys (hidden_kinds/channels) load without an error."""
    view = {"rx": {"hidden_kinds": ["adc"], "hidden_channels": ["fddc0"]}}
    at = _upload_app().run(timeout=30)
    at.session_state["test_upload"] = (
        "legacy",
        dumps(default_rx_plan(), default_tx_plan(), view),
    )
    at.run(timeout=30)
    assert not at.exception
    assert not at.error
    assert len(_verdicts(_tab(at, "Rx"))) == 1


def test_load_view_with_stale_path() -> None:
    """A saved path that no longer exists falls back to the first path."""
    view = {"rx": {"path": "fddc5"}, "tx": {"path": "S2@dac2"}}
    at = _upload_app().run(timeout=30)
    at.session_state["test_upload"] = (
        "stale",
        dumps(default_rx_plan(), default_tx_plan(), view),
    )
    at.run(timeout=30)
    assert not at.exception
    assert not at.error
    assert at.session_state["fp_rx_path"] == "fddc0"
    assert at.session_state["fp_tx_path"] == "S2@dac2"


def test_export_view_has_path() -> None:
    """The exported view records the selected path per tab."""
    from adijif.tools.explorer.src.pages import frequencyplanner as fp

    with pytest.raises(ValueError):
        fp._view_updates({"rx": {"path": 3}})
    updates, _ = fp._view_updates(
        {"rx": {"path": "fddc2", "hidden_kinds": ["adc"]}}
    )
    assert updates["fp_rx_path"] == "fddc2"
    assert updates["fp_tx_path"] is None
    assert not any("hidden" in k for k in updates)
