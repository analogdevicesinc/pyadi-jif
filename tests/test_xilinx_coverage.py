"""Additional tests for adijif.fpgas.xilinx to improve coverage."""

import pytest
import adijif

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
