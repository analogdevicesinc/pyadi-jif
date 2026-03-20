"""Additional tests for drawing functions to improve coverage."""

import unittest.mock as mock

import pytest

import adijif
from adijif.draw import Layout, Node


def test_draw_layout_basic_coverage():
    """Verify basic Layout methods."""
    lo = Layout("Test")
    n1 = Node("N1")
    n2 = Node("N2")
    lo.add_node(n1)
    lo.add_node(n2)
    lo.add_connection({"from": n1, "to": n2})

    assert lo.get_node("N1") == n1
    assert len(lo.get_connection(to="N2")) == 1

    lo.remove_node("N1")
    with pytest.raises(ValueError, match="Node with name N1 not found"):
        lo.get_node("N1")


def test_xilinx_draw_gtxe2_standalone():
    """Verify standalone drawing for GTXE2 (Gen 2)."""
    fpga = adijif.xilinx()
    fpga.setup_by_dev_kit_name("zc706")

    # Mock solution and solver state needed for draw
    fpga._saved_solution = True
    # _draw_phy expects FPGA_REF and LINK_OUT_REF in config["clocks"] if converter is None
    fpga.config = {
        "clocks": {
            "FPGA_REF": 125e6,
            "LINK_OUT_REF": 125e6,
            "zc706_adc_device_clk": 1e9,
            "zc706_adc_sysref": 7.8125e6,
        },
        "fpga": {
            "device_clock_source": "external",
            "type": "cpll",
            "m": 1,
            "n1": 4,
            "n2": 5,
            "d": 2,
            "vco": 2.5e9,
            "n": 20,  # n1 * n2
            "out_clk_select": "XCVR_PROGDIV_CLK",
            "progdiv": 40.0,
            "separate_device_clock_required": 0,
            "transport_samples_per_clock": 8,
        },
    }

    # standalone draw (no lo provided)
    res = fpga.draw(fpga.config)
    assert res is not None


def test_xilinx_draw_gtye5_standalone():
    """Verify standalone drawing for GTYE5 (Versal)."""
    fpga = adijif.xilinx()
    fpga.setup_by_dev_kit_name("vck190")

    fpga._saved_solution = True
    fpga.config = {
        "clocks": {
            "FPGA_REF": 125e6,
            "LINK_OUT_REF": 125e6,
            "vck190_adc_device_clk": 1e9,
            "vck190_adc_sysref": 7.8125e6,
        },
        "fpga": {
            "device_clock_source": "external",
            "type": "LCPLL",
            "m": 1,
            "n": 80,
            "d": 1,
            "vco": 10e9,
            "out_clk_select": "XCVR_PROGDIV_CLK",
            "progdiv": 40.0,
            "separate_device_clock_required": 0,
            "transport_samples_per_clock": 8,
        },
    }

    res = fpga.draw(fpga.config)
    assert res is not None


def test_ad9084_draw_standalone():
    """Verify AD9084 standalone drawing logic."""
    conv = adijif.ad9084_rx()

    conv._saved_solution = True

    # ad9084_draw.py L142 uses clocks[f"{name}_ref_clk"] where name is self.name
    # and it seems it expects "AD9084" for the standalone path if it's not 9088
    clocks = {
        "AD9084_ref_clk": 1e9,
        "AD9084_sysref": 7.8125e6,
    }

    res = conv.draw(clocks)
    assert res is not None


def test_system_draw_smoke():
    """Verify system-level drawing."""
    sys = adijif.system("ad9680", "ad9523_1", "xilinx", 125e6)
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.converter.sample_clock = 1e9

    config = sys.solve()

    # Let's bypass the internal drawing call for this smoke test to cover
    # the rest of system_draw.py
    sys.clock.ic_diagram_node = Node("ClockChip")
    with (
        mock.patch.object(sys.clock, "draw"),
        mock.patch.object(sys.converter, "draw"),
        mock.patch.object(sys.fpga, "draw"),
    ):
        res = sys.draw(config)
        assert res is not None
