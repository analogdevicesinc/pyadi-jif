"""Additional tests for system and FPGA coverage."""

import pytest

import adijif


def test_system_gekko_solve_smoke():
    """Verify system solving with gekko solver path."""
    # We know this raises an Exception for Xilinx but we want to cover the system.py code
    sys = adijif.system("ad9680", "ad9523_1", "xilinx", 125e6, solver="gekko")
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.converter.sample_clock = 1e9

    with pytest.raises(Exception, match="Gekko solver not supported"):
        sys.initialize()


def test_xilinx_setup_by_dev_kit_various():
    """Verify Xilinx setup for various boards to cover subclasses."""
    fpga = adijif.xilinx()

    fpga.setup_by_dev_kit_name("zcu102")
    assert fpga.transceiver_type == "GTHE4"

    fpga.setup_by_dev_kit_name("vck190")
    assert fpga.transceiver_type == "GTYE5"

    fpga.setup_by_dev_kit_name("zc706")
    assert fpga.transceiver_type == "GTXE2"


def test_xilinx_sevenseries_initialization():
    """Verify SevenSeries initialization."""
    from adijif.fpgas.xilinx.sevenseries import SevenSeries

    fpga = SevenSeries(transceiver_type="GTXE2")
    assert fpga.transceiver_type == "GTXE2"


def test_system_mcp_solve_with_inline_pll():
    """Verify system solve with an inline PLL."""
    sys = adijif.system("ad9680", "hmc7044", "xilinx", 125e6, solver="CPLEX")
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.converter.sample_clock = 1e9

    # Add an inline PLL
    sys.add_pll_inline("adf4371", sys.clock, sys.converter)

    config = sys.solve()
    assert "clock_ext_pll_adf4371" in config


def test_system_solve_no_fpga_clocks():
    """Verify system solve with FPGA clocks disabled."""
    sys = adijif.system("ad9680", "ad9523_1", "xilinx", 125e6, solver="CPLEX")
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.converter.sample_clock = 1e9
    sys.enable_fpga_clocks = False

    config = sys.solve()
    assert config is not None
    # Verify no fpga_ref_clk in clock output_clocks
    assert "zc706_fpga_ref_clk" not in config["clock"]["output_clocks"]
