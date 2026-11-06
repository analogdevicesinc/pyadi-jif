"""Tests for frequency planner output-path enumeration and selection."""

from adijif.freqplan import (
    compute_rx,
    compute_tx,
    default_rx_plan,
    default_tx_plan,
)
from adijif.tools.explorer.src.pages.helpers.freqplan_paths import (
    path_status,
    resolve_path_id,
    rx_paths,
    select_path_for_block,
    tx_paths,
)


def _rx(plan=None):
    plan = plan or default_rx_plan()
    return plan, rx_paths(plan, compute_rx(plan))


def test_rx_paths_default():
    _, paths = _rx()
    assert [p.id for p in paths] == ["fddc0", "fddc2", "fddc4", "fddc6"]
    assert paths[0].stages == ("adc0", "cddc0", "fddc0")
    assert paths[0].label == "S1 · FDDC0"


def test_rx_paths_cddc_direct():
    plan = default_rx_plan()
    plan.datapath.fddc_enabled[0] = False
    _, paths = _rx(plan)
    by_id = {p.id: p for p in paths}
    assert by_id["cddc0"].stages == ("adc0", "cddc0")
    assert by_id["cddc0"].label == "S1 · CDDC0"


def test_rx_paths_error_stage():
    plan = default_rx_plan()
    plan.datapath.cddc_enabled[0] = False
    result = compute_rx(plan)
    paths = rx_paths(plan, result)
    by_id = {p.id: p for p in paths}
    assert by_id["fddc0"].stages == ("adc0", "cddc0", "fddc0")
    assert path_status(by_id["fddc0"], plan, result) == "error"


def test_rx_paths_empty_label():
    plan = default_rx_plan()
    dp = plan.datapath
    dp.fddc_enabled[1] = True
    dp.fddc_source[1] = 1
    dp.fddc_nco_frequencies[1] = 2000e6
    dp.fddc_decimations[1] = 8
    result = compute_rx(plan)
    paths = rx_paths(plan, result)
    by_id = {p.id: p for p in paths}
    assert by_id["fddc1"].label == "(empty) · FDDC1"
    assert path_status(by_id["fddc0"], plan, result) in ("ok", "warn", "error")


def test_tx_paths_default():
    plan = default_tx_plan()
    paths = tx_paths(plan, compute_tx(plan))
    assert [p.id for p in paths] == [
        "S1@dac0",
        "S1@dac1",
        "S2@dac2",
        "S2@dac3",
    ]
    assert paths[0].stages == ("fduc0", "cduc0", "dac0")
    assert paths[0].label == "S1 · FDUC0 → DAC0"
    assert paths[0].signals == ("S1",)


def test_tx_paths_disabled_fduc_has_no_path():
    plan = default_tx_plan()
    plan.signals.append(type(plan.signals[0])("S3", 0, 100e6, 1))
    paths = tx_paths(plan, compute_tx(plan))
    assert not any(p.id.startswith("S3@") for p in paths)
    assert path_status(paths[0], plan, compute_tx(plan)) in (
        "ok",
        "warn",
        "error",
    )


def test_select_path_for_block():
    _, paths = _rx()
    assert select_path_for_block(paths, "fddc2", "cddc1") == "fddc2"
    assert select_path_for_block(paths, "fddc2", "cddc0") == "fddc0"
    assert select_path_for_block(paths, "fddc2", "fddc1") == "fddc2"
    assert select_path_for_block(paths, "fddc2", "adc3") == "fddc6"


def test_select_path_for_input_block():
    """Clicking a signal input selects a path through its ADC."""
    _, paths = _rx()
    assert select_path_for_block(paths, "fddc0", "input3") == "fddc6"
    assert select_path_for_block(paths, "fddc6", "input3") == "fddc6"
    assert select_path_for_block(paths, "fddc0", "input9") == "fddc0"


def test_resolve_stale_path():
    _, paths = _rx()
    assert resolve_path_id(paths, "fddc5") == "fddc0"
    assert resolve_path_id(paths, "all") == "all"
    assert resolve_path_id([], "x") == "all"
