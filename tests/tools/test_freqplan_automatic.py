"""Automatic planner UI state and part switching regressions."""

from concurrent.futures import Future
from types import SimpleNamespace

from adijif.freqplan import default_rx_plan, default_tx_plan


def test_snapshot_fingerprint_includes_settings_and_targets():
    from adijif.tools.explorer.src.pages.helpers.freqplan_solver import (
        fingerprint,
    )

    rx = default_rx_plan()
    before = fingerprint(rx, None, {"automatic": []})
    assert fingerprint(rx, None, {"automatic": ["rx.rate"]}) != before
    rx.adc_rate_hz += 1
    assert fingerprint(rx, None, {"automatic": []}) != before


def test_job_rejects_stale_results():
    from adijif.tools.explorer.src.pages.helpers.freqplan_solver import SolveJob

    future = Future()
    future.set_result(
        SimpleNamespace(status="optimal", rx=default_rx_plan(), tx=None)
    )
    job = SolveJob("before", future)
    assert job.applicable("before")
    assert not job.applicable("after")


def test_targets_keep_tx_baseband_separate():
    from adijif.tools.explorer.src.pages.helpers.freqplan_solver import (
        target_rows,
    )

    tx = default_tx_plan()
    original = [s.center_hz for s in tx.signals]
    rows = target_rows(None, tx)
    assert not rows.empty
    assert set(rows.direction) == {"tx"}
    assert rows.target_mhz.max() > 0
    assert [s.center_hz for s in tx.signals] == original


def _app():
    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    path = Path(__file__).parents[2] / "adijif/tools/explorer/main.py"
    app = AppTest.from_file(str(path)).run(timeout=30)
    next(w for w in app.sidebar.radio if w.label == "Select a Tool").set_value(
        "Frequency Planner"
    ).run(timeout=30)
    return app


def test_adc_part_switch_hides_tx_and_resets_rates():
    app = _app()
    app.selectbox(key="fp_part").set_value("AD9680").run(timeout=30)
    assert not app.exception
    assert [tab.label for tab in app.tabs] == ["Rx"]
    assert any(w.label == "Decimation" for w in app.selectbox)
    assert not any(w.label == "CDUC interpolation" for w in app.selectbox)
    app.selectbox(key="fp_part").set_value("AD9081").run(timeout=30)
    assert not app.exception
    assert [tab.label for tab in app.tabs] == ["Rx", "Tx"]
    assert app.number_input(key="fp_rx_rate").value <= 4000


def test_transceiver_shows_analog_lo_and_no_fictitious_nco():
    app = _app()
    app.selectbox(key="fp_part").set_value("ADRV9009").run(timeout=30)
    assert not app.exception
    assert (
        len([w for w in app.number_input if w.label == "Analog LO (MHz)"]) == 2
    )
    auto = next(w for w in app.multiselect if w.label == "Automatically choose")
    assert any("LO" in option for option in auto.options)
    assert not any("NCO" in option for option in auto.options)


def test_solver_result_cannot_apply_after_input_change():
    from adijif.tools.explorer.src.pages.helpers.freqplan_solver import (
        SolveJob,
        fingerprint,
    )

    app = _app()
    future = Future()
    rx, tx = default_rx_plan(), default_tx_plan()
    options = app.session_state["fp_solver_options"]
    future.set_result(
        SimpleNamespace(
            status="optimal",
            rx=rx,
            tx=None,
            message="Validated",
            objective_bps=1e9,
            achieved=[],
            settings={},
            elapsed_s=0.1,
        )
    )
    app.session_state["fp_solve_job"] = SolveJob(
        fingerprint(rx, tx, options), future
    )
    app.run(timeout=30)
    assert not app.button(key="fp_solve_apply").disabled
    app.number_input(key="fp_rx_rate").set_value(18000).run(timeout=30)
    assert app.button(key="fp_solve_apply").disabled
    assert any("Inputs changed" in w.value for w in app.warning)


def test_solver_rejects_malformed_persisted_inputs():
    import pytest

    from adijif.tools.explorer.src.pages.helpers.freqplan_solver import (
        validated_options,
    )

    with pytest.raises(ValueError, match="object"):
        validated_options([])
    with pytest.raises(ValueError, match="finite"):
        validated_options(
            {
                "targets": [
                    {
                        "direction": "tx",
                        "signal": "S1",
                        "path": "dac0",
                        "target_mhz": float("nan"),
                    }
                ]
            }
        )
    with pytest.raises(ValueError, match="minimum"):
        validated_options(
            {
                "rate_domains": {
                    "rx": {
                        "mode": "Range",
                        "minimum": 200,
                        "maximum": 100,
                        "step": 1,
                    }
                }
            }
        )


def test_rate_domain_error_is_inline():
    app = _app()
    next(
        w for w in app.multiselect if w.label == "Automatically choose"
    ).set_value(["rx.rate"]).run(timeout=30)
    next(w for w in app.number_input if w.label == "Minimum (MHz)").set_value(
        30000
    ).run(timeout=30)
    assert not app.exception
    assert app.button(key="fp_solve_start").disabled
    assert any("minimum rate" in e.value for e in app.error)


def test_pending_job_disables_duplicate_submissions():
    from adijif.tools.explorer.src.pages.helpers.freqplan_solver import SolveJob

    app = _app()
    future = Future()
    app.session_state["fp_solve_job"] = SolveJob("pending", future)
    app.run(timeout=30)
    assert not app.exception
    assert app.button(key="fp_solve_start").disabled
    assert any("background" in value.value for value in app.info)
    future.set_result(
        SimpleNamespace(
            status="infeasible", rx=None, tx=None, message="No configuration"
        )
    )
    app.run(timeout=30)
    assert not app.button(key="fp_solve_start").disabled


def test_solution_applies_in_callback_without_changing_other_direction():
    from adijif.tools.explorer.src.pages.helpers.freqplan_solver import (
        SolveJob,
        fingerprint,
    )

    app = _app()
    future = Future()
    rx, tx = default_rx_plan(), default_tx_plan()
    signature = fingerprint(rx, tx, app.session_state["fp_solver_options"])
    rx.datapath.fddc_decimations[0] = 8
    future.set_result(
        SimpleNamespace(
            status="optimal",
            rx=rx,
            tx=None,
            message="Validated",
            objective_bps=1e9,
            achieved=[],
            settings={},
            elapsed_s=0.1,
        )
    )
    app.session_state["fp_solve_job"] = SolveJob(signature, future)
    app.run(timeout=30)
    app.button(key="fp_solve_apply").click().run(timeout=30)
    assert not app.exception
    assert app.session_state["fp_rx_frames"]["fddc"].iloc[0].decimation == 8
    assert app.number_input(key="fp_tx_rate").value == 20000


def test_every_part_renders_supported_directions():
    from adijif.freqplan import ADAPTERS

    app = _app()
    for part, adapter in ADAPTERS.items():
        app.selectbox(key="fp_part").set_value(part).run(timeout=30)
        assert not app.exception, part
        expected = []
        if adapter.rx_datapath is not None:
            expected.append("Observation Rx" if part == "AD9371_OBS" else "Rx")
        if adapter.tx_datapath is not None:
            expected.append("Tx")
        assert [tab.label for tab in app.tabs] == expected, part
        assert not app.error, part


def _upload_script():
    from types import SimpleNamespace

    import streamlit as st

    from adijif.tools.explorer.src.pages.frequencyplanner import (
        FrequencyPlanner,
        _init_state,
        apply_upload,
    )

    _init_state()
    upload = st.session_state.pop("test_upload", None)
    if upload:
        identity, payload = upload
        apply_upload(
            SimpleNamespace(file_id=identity, getvalue=lambda: payload.encode())
        )
    FrequencyPlanner(None).write()


def test_simple_upload_and_invalid_solver_options_are_transactional():
    import json

    from streamlit.testing.v1 import AppTest

    from adijif.freqplan import dumps

    app = AppTest.from_function(_upload_script).run(timeout=30)
    tx = default_tx_plan("AD9152")
    app.session_state["test_upload"] = ("dac", dumps(None, tx))
    app.run(timeout=30)
    assert not app.exception
    assert app.selectbox(key="fp_part").value == "AD9152"
    assert [tab.label for tab in app.tabs] == ["Tx"]
    bad = json.loads(dumps(default_rx_plan(), default_tx_plan()))
    bad["view"]["solver"] = {"options": {"timeout_s": -1}}
    app.session_state["test_upload"] = ("malformed", json.dumps(bad))
    app.run(timeout=30)
    assert not app.exception
    assert app.selectbox(key="fp_part").value == "AD9152"
    assert any("timeout_s" in e.value for e in app.error)


def test_simple_edits_survive_page_switch():
    app = _app()
    app.selectbox(key="fp_part").set_value("ADRV9009").run(timeout=30)
    next(w for w in app.number_input if w.label == "Analog LO (MHz)").set_value(
        2500.0
    ).run(timeout=30)
    next(w for w in app.sidebar.radio if w.label == "Select a Tool").set_value(
        "Basic JESD204 Calculator"
    ).run(timeout=30)
    next(w for w in app.sidebar.radio if w.label == "Select a Tool").set_value(
        "Frequency Planner"
    ).run(timeout=30)
    assert not app.exception
    assert (
        next(w for w in app.number_input if w.label == "Analog LO (MHz)").value
        == 2500.0
    )


def test_automatic_rates_preserve_jesd_constraints_in_submitted_requests(
    monkeypatch,
):
    import importlib

    from adijif.freqplan import (
        compute_rx,
        compute_tx,
        rx_link,
        solve_link,
        tx_link,
    )

    app = _app()
    ui = importlib.import_module("src.pages.helpers.freqplan_solver")
    captured = []

    def capture_request(request, signature):
        captured.append(request)
        future = Future()
        future.set_result(
            SimpleNamespace(
                status="infeasible", rx=None, tx=None, message="Test submission"
            )
        )
        return ui.SolveJob(signature, future)

    monkeypatch.setattr(ui, "_start", capture_request)
    pinned = {}
    for direction, plan, compute, link in (
        ("rx", default_rx_plan(), compute_rx, rx_link),
        ("tx", default_tx_plan(), compute_tx, tx_link),
    ):
        fit = solve_link(plan, link(plan, compute(plan))).fits[0]
        pinned[direction] = fit.key
        app.selectbox(key=f"fp_{direction}_jesd_mode").set_value(
            f"{fit.jesd_class}:{fit.mode}"
        ).run(timeout=30)
    cases = (
        ("Rx", ["rx.rate"], False),
        ("Tx", ["tx.rate"], False),
        ("Rx and Tx", ["rx.rate", "tx.rate"], True),
    )
    for scope, automatic, pin in cases:
        next(w for w in app.radio if w.label == "Solve directions").set_value(
            scope
        ).run(timeout=30)
        next(
            w for w in app.multiselect if w.label == "Automatically choose"
        ).set_value(automatic).run(timeout=30)
        next(
            w
            for w in app.checkbox
            if w.label == "Constrain to selected JESD modes"
        ).set_value(pin).run(timeout=30)
        app.button(key="fp_solve_start").click().run(timeout=30)
        assert not app.exception
        request = captured[-1]
        assert request.automatic == set(automatic)
        assert set(request.rate_domains) == {
            key.split(".")[0] for key in automatic
        }
        assert request.jesd_modes == (pinned if pin else {})
        assert app.session_state["fp_solver_options"]["jesd_modes"] == (
            pinned if pin else {}
        )


def test_pinned_jesd_mode_survives_incompatible_fpga_until_explicit_update(
    monkeypatch,
):
    import importlib

    from adijif.freqplan import compute_rx, rx_link, solve_link

    app = _app()
    ui = importlib.import_module("src.pages.helpers.freqplan_solver")
    captured = []

    def capture_request(request, signature):
        captured.append(request)
        future = Future()
        future.set_result(
            SimpleNamespace(
                status="infeasible", rx=None, tx=None, message="Test submission"
            )
        )
        return ui.SolveJob(signature, future)

    monkeypatch.setattr(ui, "_start", capture_request)
    rx = default_rx_plan()
    fit = solve_link(rx, rx_link(rx, compute_rx(rx))).fits[0]
    pinned = {"rx": fit.key}
    app.selectbox(key="fp_rx_jesd_mode").set_value(
        f"{fit.jesd_class}:{fit.mode}"
    ).run(timeout=30)
    next(
        w for w in app.checkbox if w.label == "Constrain to selected JESD modes"
    ).set_value(True).run(timeout=30)
    app.selectbox(key="fp_fpga").set_value("zcu102").run(timeout=30)
    assert app.session_state["fp_rx_jesd_mode"] is None
    next(
        w for w in app.multiselect if w.label == "Automatically choose"
    ).set_value(["rx.rate"]).run(timeout=30)
    app.button(key="fp_solve_start").click().run(timeout=30)
    assert not app.exception
    assert captured[-1].jesd_modes == pinned
    assert app.session_state["fp_solver_options"]["pinned_modes"] == pinned
    assert any(fit.mode in c.value and "Pinned" in c.value for c in app.caption)
    app.button(key="fp_solve_update_pins").click().run(timeout=30)
    app.button(key="fp_solve_start").click().run(timeout=30)
    assert captured[-1].jesd_modes == {}


def test_pins_roundtrip_without_current_fits_and_survive_scope_and_apply():
    from streamlit.testing.v1 import AppTest

    from adijif.freqplan import (
        compute_rx,
        compute_tx,
        dumps,
        rx_link,
        solve_link,
        tx_link,
    )
    from adijif.tools.explorer.src.pages.helpers.freqplan_solver import (
        SolveJob,
        fingerprint,
    )

    rx, tx = default_rx_plan(), default_tx_plan()
    rx_mode = solve_link(rx, rx_link(rx, compute_rx(rx))).fits[0].key
    tx_mode = solve_link(tx, tx_link(tx, compute_tx(tx))).fits[0].key
    pins = {"rx": rx_mode}
    rx.adc_rate_hz = 40e9
    config = dumps(
        rx,
        tx,
        {
            "solver": {
                "options": {
                    "scope": "Rx",
                    "pin_modes": True,
                    "pinned_modes": pins,
                }
            }
        },
    )
    app = AppTest.from_function(_upload_script).run(timeout=30)
    app.session_state["test_upload"] = ("pinned", config)
    app.run(timeout=30)
    assert not app.exception
    assert app.session_state["fp_rx_jesd_mode"] is None
    assert app.session_state["fp_solver_options"]["jesd_modes"] == pins
    next(w for w in app.radio if w.label == "Solve directions").set_value(
        "Tx"
    ).run(timeout=30)
    assert app.session_state["fp_solver_options"]["pinned_modes"] == pins
    assert app.session_state["fp_solver_options"]["jesd_modes"] == {}
    future = Future()
    future.set_result(
        SimpleNamespace(
            status="optimal",
            rx=None,
            tx=tx,
            message="Validated",
            objective_bps=1e9,
            achieved=[],
            settings={},
            elapsed_s=0.1,
            modes={"tx": tx_mode},
        )
    )
    app.session_state["fp_solve_job"] = SolveJob(
        fingerprint(rx, tx, app.session_state["fp_solver_options"]), future
    )
    app.run(timeout=30)
    app.button(key="fp_solve_apply").click().run(timeout=30)
    assert not app.exception
    assert app.session_state["fp_solver_options"]["pinned_modes"] == pins
    next(w for w in app.radio if w.label == "Solve directions").set_value(
        "Rx"
    ).run(timeout=30)
    assert app.session_state["fp_solver_options"]["jesd_modes"] == pins


def test_imported_pin_must_exist_for_part_but_need_not_currently_fit():
    import pytest

    from adijif.tools.explorer.src.pages.helpers.freqplan_solver import (
        validated_options,
    )

    with pytest.raises(ValueError, match="Unknown pinned"):
        validated_options(
            {"pinned_modes": {"rx": ["jesd204c", "not-a-mode"]}}, "AD9084"
        )
    with pytest.raises(ValueError, match="Unknown pinned"):
        validated_options({"pinned_modes": {"tx": ["jesd204b", "0"]}}, "AD9680")
    with pytest.raises(ValueError, match="pair"):
        validated_options({"pinned_modes": {"rx": "jesd204c:59"}}, "AD9084")
