"""Tests for the JESD204 link solver of the frequency planner."""

import pytest

from adijif.freqplan.jesd import (
    DEV_KITS,
    TRANSCEIVERS,
    FpgaLimits,
    fpga_custom,
    fpga_from_devkit,
    jesd_from_dict,
    jesd_to_dict,
    link_summary,
    rx_link,
    solve_link,
    tx_link,
)
from adijif.freqplan.rx import compute_rx, default_rx_plan
from adijif.freqplan.tx import compute_tx, default_tx_plan


def _rx(mutate=None):
    plan = default_rx_plan()
    if mutate:
        mutate(plan.datapath)
    return plan, compute_rx(plan)


def _tx(mutate=None):
    plan = default_tx_plan()
    if mutate:
        mutate(plan.datapath)
    return plan, compute_tx(plan)


# --- link requirement -------------------------------------------------


def test_rx_link_m_and_rate_from_fastest_output():
    plan, res = _rx()
    req = rx_link(plan, res)
    assert req.direction == "rx"
    assert req.M == 8  # four complex FDDCs
    assert req.channels == ("fddc0", "fddc2", "fddc4", "fddc6")
    assert req.sample_rate_hz == pytest.approx(2.5e9)  # FDDC4: 4 x 2
    assert req.rate_set_by == ("fddc4",)
    assert req.converter_rate_hz == pytest.approx(20e9)


def test_rx_link_counts_cddc_only_outputs():
    def only_cddcs(dp):
        dp.fddc_enabled = [False] * 8

    plan, res = _rx(only_cddcs)
    req = rx_link(plan, res)
    assert req.M == 8
    assert req.channels == ("cddc0", "cddc1", "cddc2", "cddc3")
    assert req.sample_rate_hz == pytest.approx(5e9)
    assert req.rate_set_by == ("cddc0", "cddc1", "cddc2", "cddc3")


def test_rx_link_excludes_errored_outputs():
    def kill_cddc0(dp):
        dp.cddc_enabled = [False, True, True, True]

    plan, res = _rx(kill_cddc0)
    req = rx_link(plan, res)
    assert "fddc0" not in req.channels
    assert req.M == 6
    assert any(e.startswith("FDDC0") for e in req.excluded)


def test_rx_link_no_outputs():
    def all_off(dp):
        dp.fddc_enabled = [False] * 8
        dp.cddc_enabled = [False] * 4

    plan, res = _rx(all_off)
    req = rx_link(plan, res)
    assert req.M == 0
    sol = solve_link(plan, req)
    assert sol.modes == []
    assert "no active outputs" in sol.message.lower()


def test_tx_link_rate_is_fduc_input_rate():
    plan, res = _tx()
    req = tx_link(plan, res)
    assert req.direction == "tx"
    assert req.M == 4  # FDUC0 and FDUC4, complex
    assert req.channels == ("fduc0", "fduc4")
    # 20 GSPS / (CDUC 4 x FDUC 2)
    assert req.sample_rate_hz == pytest.approx(2.5e9)
    assert req.converter_rate_hz == pytest.approx(20e9)


def test_tx_link_cduc_only():
    def no_fducs(dp):
        dp.fduc_enabled = [False] * 8

    plan, res = _tx(no_fducs)
    req = tx_link(plan, res)
    enabled = sum(plan.datapath.cduc_enabled)
    assert req.M == 2 * enabled
    assert req.sample_rate_hz == pytest.approx(20e9 / 4)


# --- solving ------------------------------------------------------------


def test_solve_rx_default_single_fit():
    plan, res = _rx()
    sol = solve_link(plan, rx_link(plan, res))
    fits = [m for m in sol.modes if m.ok]
    assert len(fits) == 1
    m = fits[0]
    assert (m.jesd_class, m.M, m.L, m.Np) == ("jesd204c", 8, 12, 12)
    assert m.lane_rate_hz == pytest.approx(20.625e9)
    # Every row is for the requested M
    assert {r.M for r in sol.modes} == {8}
    # Rejected rows say why
    bad = [r for r in sol.modes if not r.ok]
    assert bad and all(r.converter_reason for r in bad)


def test_solve_uses_plan_interpolation_not_converter_default():
    # A default converter has interpolation 1 and would reject every mode
    # on its DAC clock; the plan's CDUC x FDUC = 8 must be used instead.
    plan, res = _tx()
    sol = solve_link(plan, tx_link(plan, res))
    fits = [m for m in sol.modes if m.ok]
    assert len(fits) >= 5
    assert all("DAC" not in (m.converter_reason or "") for m in sol.modes)


def test_solve_m_outside_mode_table():
    def all_fddcs(dp):
        dp.fddc_enabled = [True] * 8
        dp.fddc_source = [1, 1, 2, 2, 3, 3, 4, 4]

    plan, res = _rx(all_fddcs)
    req = rx_link(plan, res)
    assert req.M == 16
    sol = solve_link(plan, req)
    assert sol.modes == []
    assert "M=16" in sol.message
    assert "single" in sol.message.lower()


def test_fpga_limits_filter_modes():
    plan, res = _tx()
    req = tx_link(plan, res)
    zcu = fpga_from_devkit("zcu102")  # GTHE4 16.375 Gbps, 8 lanes
    assert zcu == FpgaLimits("zcu102", "GTHE4", 16.375e9, 8)
    sol = solve_link(plan, req, zcu)
    for m in sol.modes:
        if m.converter_ok:
            assert m.fpga_ok == (m.lane_rate_hz <= 16.375e9 and m.L <= 8)
        if m.fpga_ok is False:
            assert m.fpga_reason
            if m.lane_rate_hz > 16.375e9:
                assert "over GTHE4 max 16.375 Gbps" in m.fpga_reason
            if m.L > 8:
                assert f"L={m.L} > 8 FPGA lanes" in m.fpga_reason
    assert any(m.ok for m in sol.modes)
    assert any(m.converter_ok and m.fpga_ok is False for m in sol.modes)


def test_no_fpga_leaves_fpga_verdict_empty():
    plan, res = _rx()
    sol = solve_link(plan, rx_link(plan, res))
    assert all(m.fpga_ok is None and m.fpga_reason is None for m in sol.modes)


def test_fpga_custom_and_tables():
    f = fpga_custom("GTYE4", 4)
    assert f.max_lane_rate_hz == pytest.approx(32.75e9)
    assert f.max_lanes == 4
    assert "vcu118" in DEV_KITS
    assert "GTYE4" in TRANSCEIVERS
    with pytest.raises(ValueError):
        fpga_custom("NOPE", 4)
    with pytest.raises(ValueError):
        fpga_custom("GTYE4", 0)
    with pytest.raises(ValueError):
        fpga_from_devkit("nope")


def test_link_summary_text():
    plan, res = _rx()
    sol = solve_link(plan, rx_link(plan, res))
    s = link_summary(sol)
    assert "M=8" in s
    assert "2500 MSPS" in s
    assert "FDDC4" in s
    assert "1 of" in s


# --- config -------------------------------------------------------------


def test_jesd_config_round_trip():
    plan, res = _rx()
    fit = next(m for m in solve_link(plan, rx_link(plan, res)).modes if m.ok)
    d = jesd_to_dict({"devkit": "vcu118"}, {"rx": fit, "tx": None})
    assert d["rx"]["mode"] == fit.mode
    assert d["rx"]["jesd_class"] == "jesd204c"
    assert (d["rx"]["M"], d["rx"]["L"], d["rx"]["Np"]) == (8, 12, 12)
    assert d["rx"]["sample_rate_hz"] == pytest.approx(2.5e9)
    assert d["rx"]["lane_rate_hz"] == pytest.approx(20.625e9)
    assert d["tx"] is None
    fpga, modes = jesd_from_dict(d)
    assert fpga == {"devkit": "vcu118"}
    assert modes == {"rx": ("jesd204c", fit.mode), "tx": None}


def test_jesd_config_custom_fpga_round_trip():
    d = jesd_to_dict({"transceiver": "GTHE4", "lanes": 4}, {})
    fpga, modes = jesd_from_dict(d)
    assert fpga == {"transceiver": "GTHE4", "lanes": 4}
    assert modes == {"rx": None, "tx": None}


def test_jesd_config_missing_is_empty():
    assert jesd_from_dict(None) == (None, {"rx": None, "tx": None})


@pytest.mark.parametrize(
    "bad",
    [
        "nope",
        {"fpga": "vcu118"},
        {"fpga": {"devkit": "nope"}},
        {"fpga": {"transceiver": "GTYE4", "lanes": "x"}},
        {"rx": "23"},
        {"rx": {"mode": 23}},
        {"tx": {"mode": "4", "jesd_class": "jesd204z"}},
    ],
)
def test_jesd_config_malformed(bad):
    with pytest.raises(ValueError):
        jesd_from_dict(bad)


def test_rejection_reason_names_the_mode_class():
    plan, res = _rx()
    sol = solve_link(plan, rx_link(plan, res))
    b = next(m for m in sol.modes if m.jesd_class == "jesd204b" and not m.ok)
    assert "204B max 20 Gbps" in b.converter_reason
    assert "204C" not in b.converter_reason
    c = next(m for m in sol.modes if m.jesd_class == "jesd204c" and not m.ok)
    assert "204C max 28.21 Gbps" in c.converter_reason


def test_lane_rate_below_minimum_is_reported():
    def slow(dp):
        dp.cddc_decimations = [12, 12, 12, 12]
        dp.fddc_decimations = [8, 1, 8, 1, 8, 1, 8, 1]

    plan, res = _rx(slow)  # 20 GSPS / 96 = 208.3 MSPS
    sol = solve_link(plan, rx_link(plan, res))
    assert any("204B min 5 Gbps" in (m.converter_reason or "") for m in sol.modes)
