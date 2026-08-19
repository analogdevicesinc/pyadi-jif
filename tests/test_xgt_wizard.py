"""Tests for the Xilinx xgt_wizard (adi_xcvr_project) export."""

from __future__ import annotations

import json
from copy import deepcopy
from types import SimpleNamespace

import pytest

from adijif.fpgas.xilinx.xgt_wizard import XgtWizardConfig, XgtWizardLink
from adijif.system import system as System


def _fake_ad9081_zcu102():
    """AD9081+ZCU102-shaped fake system and solution (real solve numbers)."""
    converter = SimpleNamespace(
        name="ad9081",
        _nested=["adc", "dac"],
        adc=SimpleNamespace(converter_type="adc"),
        dac=SimpleNamespace(converter_type="dac"),
    )
    system = SimpleNamespace(
        converter=converter,
        fpga=SimpleNamespace(name="zcu102", transceiver_type="GTHE4"),
    )
    solution = {
        "fpga_adc": {"type": "qpll1", "sys_clk_select": "XCVR_QPLL1"},
        "jesd_adc": {
            "bit_clock": 11_962_500_000.0,
            "jesd_class": "jesd204c",
            "L": 1,
        },
        "fpga_dac": {"type": "qpll", "sys_clk_select": "XCVR_QPLL0"},
        "jesd_dac": {
            "bit_clock": 23_925_000_000.0,
            "jesd_class": "jesd204c",
            "L": 4,
        },
        "clock": {
            "output_clocks": {
                "ad9081_ref_clk": {"rate": 580_000_000.0, "divider": 5},
                "zcu102_adc_ref_clk": {"rate": 362_500_000.0, "divider": 8},
                "zcu102_adc_device_clk": {
                    "rate": 120_833_333.33,
                    "divider": 24,
                },
                "zcu102_dac_ref_clk": {"rate": 362_500_000.0, "divider": 8},
                "zcu102_dac_device_clk": {
                    "rate": 241_666_666.67,
                    "divider": 12,
                },
            }
        },
    }
    return system, solution


def _fake_ad9680_zc706():
    """Flat single-direction (ADC only) fake system and solution."""
    converter = SimpleNamespace(
        name="AD9680", converter_type="adc", _nested=None
    )
    system = SimpleNamespace(
        converter=converter,
        fpga=SimpleNamespace(name="zc706", transceiver_type="GTXE2"),
    )
    solution = {
        "fpga_AD9680": {"type": "qpll", "sys_clk_select": "XCVR_QPLL0"},
        "jesd_AD9680": {
            "bit_clock": 10_000_000_000.0,
            "jesd_class": "jesd204b",
            "L": 4,
        },
        "clock": {
            "output_clocks": {
                "AD9680_ref_clk": {"rate": 1_000_000_000.0, "divider": 3},
                "zc706_AD9680_ref_clk": {
                    "rate": 250_000_000.0,
                    "divider": 12,
                },
                "zc706_AD9680_device_clk": {
                    "rate": 250_000_000.0,
                    "divider": 12,
                },
            }
        },
    }
    return system, solution


def test_nested_rxtx_mapping_extracts_both_directions():
    system, solution = _fake_ad9081_zcu102()
    cfg = XgtWizardConfig.from_system_solution(system, solution)

    assert cfg.jesd_mode == "64B66B"
    assert cfg.transceiver_type == "GTHE4"
    assert cfg.rx == XgtWizardLink(
        lane_rate_gbps=11.9625,
        ref_clk_mhz=362.5,
        pll_type="QPLL1",
        num_lanes=1,
    )
    assert cfg.tx == XgtWizardLink(
        lane_rate_gbps=23.925,
        ref_clk_mhz=362.5,
        pll_type="QPLL0",
        num_lanes=4,
    )


def test_flat_single_direction_mapping_has_no_tx():
    system, solution = _fake_ad9680_zc706()
    cfg = XgtWizardConfig.from_system_solution(system, solution)

    assert cfg.jesd_mode == "8B10B"
    assert cfg.tx is None
    assert cfg.rx == XgtWizardLink(
        lane_rate_gbps=10.0,
        ref_clk_mhz=250.0,
        pll_type="QPLL0",
        num_lanes=4,
    )


def test_cpll_maps_and_versal_plls_are_rejected():
    system, solution = _fake_ad9680_zc706()
    solution["fpga_AD9680"]["type"] = "cpll"
    cfg = XgtWizardConfig.from_system_solution(system, solution)
    assert cfg.rx.pll_type == "CPLL"

    for pll in ("rpll", "lcpll"):
        bad = deepcopy(solution)
        bad["fpga_AD9680"]["type"] = pll
        with pytest.raises(ValueError, match="not support"):
            XgtWizardConfig.from_system_solution(system, bad)


def test_jesd_class_mismatch_and_unknown_class_raise():
    system, solution = _fake_ad9081_zcu102()
    solution["jesd_adc"]["jesd_class"] = "jesd204b"
    with pytest.raises(ValueError, match="jesd_class"):
        XgtWizardConfig.from_system_solution(system, solution)

    system2, solution2 = _fake_ad9680_zc706()
    solution2["jesd_AD9680"]["jesd_class"] = "jesd204z"
    with pytest.raises(ValueError, match="jesd_class"):
        XgtWizardConfig.from_system_solution(system2, solution2)


def test_multi_converter_systems_are_rejected():
    system, solution = _fake_ad9680_zc706()
    system.converter = [system.converter]
    with pytest.raises(ValueError, match="single converter"):
        XgtWizardConfig.from_system_solution(system, solution)


def test_missing_ref_clk_raises_and_suffix_fallback_works():
    system, solution = _fake_ad9680_zc706()
    clocks = solution["clock"]["output_clocks"]
    clocks["ZC706_AD9680_ref_clk"] = clocks.pop("zc706_AD9680_ref_clk")
    cfg = XgtWizardConfig.from_system_solution(system, solution)
    assert cfg.rx.ref_clk_mhz == 250.0

    del solution["clock"]["output_clocks"]["ZC706_AD9680_ref_clk"]
    with pytest.raises(ValueError, match="AD9680_ref_clk"):
        XgtWizardConfig.from_system_solution(system, solution)


def test_link_and_config_validation():
    with pytest.raises(ValueError, match="pll_type"):
        XgtWizardLink(
            lane_rate_gbps=10.0, ref_clk_mhz=250.0, pll_type="QPLL9",
            num_lanes=4,
        )
    with pytest.raises(ValueError, match="num_lanes"):
        XgtWizardLink(
            lane_rate_gbps=10.0, ref_clk_mhz=250.0, pll_type="CPLL",
            num_lanes=0,
        )
    with pytest.raises(ValueError, match="positive"):
        XgtWizardLink(
            lane_rate_gbps=-1.0, ref_clk_mhz=250.0, pll_type="CPLL",
            num_lanes=4,
        )
    with pytest.raises(ValueError, match="jesd_mode"):
        XgtWizardConfig(jesd_mode="8b10b", tx=None, rx=None)
    with pytest.raises(ValueError, match="tx or rx"):
        XgtWizardConfig(jesd_mode="8B10B", tx=None, rx=None)


def test_number_formatting_strips_trailing_zeros_and_noise():
    from adijif.fpgas.xilinx.xgt_wizard import _fmt

    assert _fmt(10.0) == "10"
    assert _fmt(245.76) == "245.76"
    assert _fmt(11.9625) == "11.9625"
    assert _fmt(362.5) == "362.5"
    assert _fmt(11.962500000001) == "11.9625"


def test_make_renderers_emit_tx_primary_with_rx_overrides():
    system, solution = _fake_ad9081_zcu102()
    cfg = XgtWizardConfig.from_system_solution(system, solution)

    assert cfg.to_make_args() == (
        "LANE_RATE=23.925 REF_CLK=362.5 PLL_TYPE=QPLL0 JESD_MODE=64B66B "
        "XCVR_RX_LANE_RATE=11.9625 XCVR_RX_PLL_TYPE=QPLL1"
    )
    assert cfg.to_make_command("ad9081_fmca_ebz/zcu102") == (
        "make -C projects/ad9081_fmca_ebz/zcu102 "
        "LANE_RATE=23.925 REF_CLK=362.5 PLL_TYPE=QPLL0 JESD_MODE=64B66B "
        "XCVR_RX_LANE_RATE=11.9625 XCVR_RX_PLL_TYPE=QPLL1"
    )


def test_make_args_single_direction_has_no_overrides():
    system, solution = _fake_ad9680_zc706()
    cfg = XgtWizardConfig.from_system_solution(system, solution)
    assert cfg.to_make_args() == (
        "LANE_RATE=10 REF_CLK=250 PLL_TYPE=QPLL0 JESD_MODE=8B10B"
    )


def test_make_args_omits_overrides_matching_tx():
    rx = XgtWizardLink(
        lane_rate_gbps=10.0, ref_clk_mhz=250.0, pll_type="QPLL0", num_lanes=2
    )
    tx = XgtWizardLink(
        lane_rate_gbps=10.0, ref_clk_mhz=250.0, pll_type="QPLL0", num_lanes=4
    )
    cfg = XgtWizardConfig(jesd_mode="8B10B", tx=tx, rx=rx)
    assert cfg.to_make_args() == (
        "LANE_RATE=10 REF_CLK=250 PLL_TYPE=QPLL0 JESD_MODE=8B10B"
    )


def test_tcl_renderer_defines_sourceable_variables():
    system, solution = _fake_ad9081_zcu102()
    cfg = XgtWizardConfig.from_system_solution(system, solution)
    tcl = cfg.to_tcl()

    assert tcl.startswith("# Generated by pyadi-jif")
    assert (
        "set adi_xcvr_project_args [list \\\n"
        "  LANE_RATE 23.925 \\\n"
        "  REF_CLK 362.5 \\\n"
        "  PLL_TYPE QPLL0 \\\n"
        "  JESD_MODE 64B66B \\\n"
        "  XCVR_RX_LANE_RATE 11.9625 \\\n"
        "  XCVR_RX_PLL_TYPE QPLL1 \\\n"
        "]\n"
    ) in tcl
    assert (
        "set adi_xcvr_parameters_args [list \\\n"
        "  RX_NUM_OF_LANES 1 \\\n"
        "  TX_NUM_OF_LANES 4 \\\n"
        "]\n"
    ) in tcl


def test_tcl_renderer_single_direction_lane_counts():
    system, solution = _fake_ad9680_zc706()
    cfg = XgtWizardConfig.from_system_solution(system, solution)
    tcl = cfg.to_tcl()
    assert "RX_NUM_OF_LANES 4" in tcl
    assert "TX_NUM_OF_LANES" not in tcl
    assert "XCVR_RX_" not in tcl


def test_to_json_round_trips():
    system, solution = _fake_ad9081_zcu102()
    cfg = XgtWizardConfig.from_system_solution(system, solution)
    payload = json.loads(cfg.to_json())
    assert payload == cfg.to_dict()
    assert payload["rx"]["pll_type"] == "QPLL1"


def test_export_config_dispatches_xgt_wizard_format():
    fake_system, solution = _fake_ad9081_zcu102()
    sys_obj = object.__new__(System)
    sys_obj.converter = fake_system.converter
    sys_obj.fpga = fake_system.fpga

    cfg = sys_obj.export_config(format="adi.xgt-wizard", solution=solution)
    assert isinstance(cfg, XgtWizardConfig)
    assert cfg.tx.pll_type == "QPLL0"

    with pytest.raises(ValueError, match="unsupported export format"):
        sys_obj.export_config(format="raw-dict", solution=solution)


def test_agent_export_xgt_wizard_operation(monkeypatch):
    import adijif.agent_api as agent_api

    fake_system, solution = _fake_ad9680_zc706()

    class FakeSystem:
        converter = fake_system.converter
        fpga = fake_system.fpga
        clock = SimpleNamespace(name="HMC7044")

        def solve(self, out_clock_constraints):
            return solution

    monkeypatch.setattr(agent_api, "_system", lambda **kwargs: FakeSystem())
    config = {"conv": "AD9680", "clk": "HMC7044", "fpga": "XILINX"}

    result = agent_api.export_xgt_wizard(json.dumps(config))
    assert result["status"] == "ok"
    assert result["config"]["rx"]["pll_type"] == "QPLL0"
    assert result["make_args"] == (
        "LANE_RATE=10 REF_CLK=250 PLL_TYPE=QPLL0 JESD_MODE=8B10B"
    )
    assert "make_command" not in result
    assert "set adi_xcvr_project_args" in result["tcl"]

    with_project = agent_api.export_xgt_wizard(
        json.dumps(config), hdl_project="daq2/zc706"
    )
    assert with_project["make_command"].startswith(
        "make -C projects/daq2/zc706 "
    )

    assert "export_xgt_wizard" in agent_api.AGENT_OPERATIONS


def test_agent_export_xgt_wizard_error_paths():
    import adijif.agent_api as agent_api

    assert "error" in agent_api.export_xgt_wizard("not json")
    assert "must specify" in agent_api.export_xgt_wizard("{}")["error"]
    assert "error" in agent_api.export_xgt_wizard(123)
