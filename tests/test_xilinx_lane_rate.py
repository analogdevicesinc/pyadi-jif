"""Per-transceiver-type maximum lane (line) rate enforcement."""

import pytest

import adijif

from .common import skip_solver


def _ad9081_zcu102(mode_tx: str, mode_rx: str):
    cddc, fddc = 6, 4
    sys = adijif.system("ad9081", "hmc7044", "xilinx", 100e6, solver="CPLEX")
    sys.fpga.setup_by_dev_kit_name("zcu102")
    sys.fpga.ref_clock_constraint = "Unconstrained"
    sys.fpga.sys_clk_select = "XCVR_QPLL0"
    sys.fpga.out_clk_select = "XCVR_PROGDIV_CLK"
    sys.converter.clocking_option = "integrated_pll"
    sys.converter.adc.sample_clock = 2900000000 / (cddc * fddc)
    sys.converter.dac.sample_clock = 5800000000 / (cddc * fddc)
    sys.converter.adc.datapath.cddc_decimations = [cddc] * 4
    sys.converter.adc.datapath.fddc_decimations = [fddc] * 8
    sys.converter.adc.datapath.fddc_enabled = [True] * 8
    sys.converter.dac.datapath.cduc_interpolation = cddc
    sys.converter.dac.datapath.fduc_interpolation = fddc
    sys.converter.dac.datapath.fduc_enabled = [True] * 8
    sys.converter.dac.set_quick_configuration_mode(mode_tx, "jesd204c")
    sys.converter.adc.set_quick_configuration_mode(mode_rx, "jesd204c")
    return sys


def test_max_lane_rate_per_transceiver_type():
    fpga = adijif.xilinx()
    for trx, expected in (
        ("GTXE2", 12.5e9),
        ("GTHE3", 16.375e9),
        ("GTHE4", 16.375e9),
        ("GTYE3", 30.5e9),
        ("GTYE4", 32.75e9),
        ("GTYE5", 32.75e9),
        ("GTYP", 32.75e9),
    ):
        fpga.transceiver_type = trx
        assert fpga.max_lane_rate == expected


def test_unknown_transceiver_type_max_lane_rate_raises():
    fpga = adijif.xilinx()
    fpga.transceiver_type = "GTFAKE9"
    with pytest.raises(Exception, match="[Uu]nknown"):
        _ = fpga.max_lane_rate


def test_out_of_range_lane_rate_rejected_on_gthe4():
    """AD9081 TX mode 0 solves to 23.925 Gbps: beyond GTHE4's 16.375."""
    skip_solver("CPLEX")
    sys = _ad9081_zcu102(mode_tx="0", mode_rx="1.0")
    with pytest.raises(Exception, match="exceeds.*GTHE4.*16\\.375"):
        sys.solve()


def test_in_range_lane_rate_still_solves_on_gthe4():
    """TX mode 4 / RX mode 1.0 (11.9625 Gbps) stays solvable."""
    skip_solver("CPLEX")
    sys = _ad9081_zcu102(mode_tx="4", mode_rx="1.0")
    cfg = sys.solve()
    assert cfg["jesd_dac"]["bit_clock"] == pytest.approx(11.9625e9)
    assert cfg["jesd_adc"]["bit_clock"] == pytest.approx(11.9625e9)
