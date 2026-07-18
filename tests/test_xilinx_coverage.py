"""Additional tests for adijif.fpgas.xilinx to improve coverage."""

import pytest

import adijif
from adijif.fpgas.xilinx.bf import CPLLConfigurationError


def test_xilinx_setup_by_dev_kit_vck190():
    """Verify setup_by_dev_kit_name for vck190."""
    fpga = adijif.xilinx()
    fpga.setup_by_dev_kit_name("vck190")
    assert fpga.transceiver_type == "GTYE5"
    assert fpga.fpga_family == "Versal"


def test_xilinx_setup_by_dev_kit_invalid_should_raise():
    """Verify setup_by_dev_kit_name raises on unknown kit."""
    fpga = adijif.xilinx()
    with pytest.raises(Exception, match="No boardname found"):
        fpga.setup_by_dev_kit_name("invalid_board")


def test_xilinx_dev_kit_setup_is_repeatable():
    """Repeated board setup must not destructively mutate clock capabilities."""
    fpga = adijif.xilinx(solver="gekko")

    fpga.setup_by_dev_kit_name("zc706")
    fpga.setup_by_dev_kit_name("zc706")

    assert fpga._out_clk_selections == ["XCVR_REFCLK", "XCVR_REFCLK_DIV2"]


def test_xilinx_dev_kit_switch_restores_clock_capabilities():
    """Switching away from ZC706 must restore PROGDIV support."""
    fpga = adijif.xilinx(solver="gekko")
    fpga.setup_by_dev_kit_name("zc706")

    fpga.setup_by_dev_kit_name("zcu102")
    fpga.out_clk_select = "XCVR_PROGDIV_CLK"

    assert fpga.out_clk_select == "XCVR_PROGDIV_CLK"
    assert fpga._out_clk_selections == list(type(fpga)._out_clk_selections)


def test_xilinx_trx_gen_gtyp():
    """Verify trx_gen for GTYP."""
    fpga = adijif.xilinx()
    fpga.transceiver_type = "GTYP"
    assert fpga.trx_gen() == 5


def test_xilinx_fpga_generation_unknown_should_raise():
    """Verify fpga_generation raises on unknown generation."""
    fpga = adijif.xilinx()
    fpga.transceiver_type = "UNKNOWN9"
    with pytest.raises(Exception, match="Unknown transceiver generation"):
        fpga.fpga_generation()


def test_xilinx_ref_clock_max_gtxe2_speedgrade_3e():
    """Verify _ref_clock_max for GTXE2 with -3E speed grade."""
    fpga = adijif.xilinx()
    fpga.transceiver_type = "GTXE2"
    fpga.speed_grade = "-3E"
    assert fpga._ref_clock_max == 700000000


def test_xilinx_ref_clock_max_unknown_type_should_raise():
    """Verify _ref_clock_max raises on unknown transceiver type."""
    fpga = adijif.xilinx()
    fpga.transceiver_type = "UNKNOWN"
    with pytest.raises(Exception, match="Unknown ref_clock_max"):
        _ = fpga._ref_clock_max


def test_xilinx_ref_clock_min_unknown_type_should_raise():
    """Verify _ref_clock_min raises on unknown transceiver type."""
    fpga = adijif.xilinx()
    fpga.transceiver_type = "UNKNOWN"
    with pytest.raises(Exception, match="Unknown ref_clock_min"):
        _ = fpga._ref_clock_min


def test_xilinx_str_representation():
    """Verify __str__ representation."""
    fpga = adijif.xilinx()
    assert "adijif.fpgas.xilinx.xilinx" in str(fpga)


def test_determine_pll_falls_back_only_for_infeasible_cpll(monkeypatch):
    """Programming errors in CPLL discovery must not be hidden by QPLL fallback."""
    fpga = adijif.xilinx()
    qpll_config = {"type": "QPLL"}

    monkeypatch.setattr(
        fpga,
        "determine_cpll",
        lambda *_: (_ for _ in ()).throw(CPLLConfigurationError()),
    )
    monkeypatch.setattr(fpga, "determine_qpll", lambda *_: qpll_config)
    assert fpga.determine_pll(1, 1) == qpll_config

    monkeypatch.setattr(
        fpga,
        "determine_cpll",
        lambda *_: (_ for _ in ()).throw(RuntimeError("implementation defect")),
    )
    with pytest.raises(RuntimeError, match="implementation defect"):
        fpga.determine_pll(1, 1)


def test_gty4_qpll_full_rate_path():
    """GTY4 brute-force discovery must use the full-rate QPLL path."""
    fpga = adijif.xilinx()
    fpga.transceiver_type = "GTY4"
    fpga.ref_clock_min = 60_000_000
    fpga.ref_clock_max = 820_000_000
    fpga.vco0_min = 8_000_000_000
    fpga.vco0_max = 9_800_000_000
    fpga.vco1_min = 9_800_000_000
    fpga.vco1_max = 13_000_000_000
    fpga.N = [16, 20, 32, 40, 64, 66, 80, 100]

    config = fpga.determine_qpll(16_000_000_000, 80_000_000)

    assert config["qty4_full_rate"] == 1
