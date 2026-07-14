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


def test_layout_draw_emits_ntype_classes_and_uses_jif_library():
    """Verify Node.ntype is serialized as a JIF class for pyd2lang-native."""
    lo = Layout("Test")
    parent = Node("Parent", ntype="shell")
    child = Node("ADC", ntype="adc")
    child.shape = "parallelogram"
    divider = Node("Divider", ntype="divider")
    valued = Node("Valued", ntype="input")
    valued.value = 1
    parent.add_child(child)
    parent.add_child(divider)
    parent.add_child(valued)
    lo.add_node(parent)

    with mock.patch("d2.compile", return_value="<svg/>") as compile_mock:
        assert lo.draw() == "<svg/>"

    compile_mock.assert_called_once()
    diag = compile_mock.call_args.args[0]
    assert compile_mock.call_args.kwargs == {"library": "jif", "theme": "dark"}
    assert "Parent.class: shell\n" in diag
    assert "    ADC.class: adc\n" in diag
    assert "    ADC.shape: parallelogram\n" in diag
    assert "    Divider.class: divider\n" in diag
    assert "    Divider.shape: rectangle\n" not in diag
    assert (
        "    Valued: {tooltip: Valued = 1 }\n    Valued.class: input\n" in diag
    )


def test_layout_selects_light_theme_and_rejects_unknown_theme():
    """Drawing theme is explicit, validated, and forwarded to pyd2."""
    lo = Layout("Light", theme="light")
    lo.add_node(Node("ADC", ntype="adc"))

    with mock.patch("d2.compile", return_value="<svg/>") as compile_mock:
        assert lo.draw() == "<svg/>"

    assert compile_mock.call_args.kwargs == {"library": "jif", "theme": "light"}
    with pytest.raises(ValueError, match="theme must be 'light' or 'dark'"):
        Layout("Invalid", theme="sepia")


def test_layout_draw_emits_semantic_signal_classes():
    """Connections use the released JIF system-theme signal vocabulary."""
    lo = Layout("Signals")
    reference = Node("REF_IN", ntype="input")
    clock = Node("Clock")
    sysref = Node("SYSREF_IN", ntype="input")
    converter = Node("Converter")
    fpga = Node("FPGA")
    for node in (reference, clock, sysref, converter, fpga):
        lo.add_node(node)

    lo.add_connection({"from": reference, "to": clock, "rate": 125e6})
    lo.add_connection({"from": clock, "to": converter, "rate": 20e9})
    lo.add_connection({"from": sysref, "to": fpga, "rate": 25e6})
    lo.add_connection(
        {"from": converter, "to": fpga, "rate": 20.625e9, "type": "data"}
    )

    with mock.patch("d2.compile", return_value="<svg/>") as compile_mock:
        lo.draw()

    diag = compile_mock.call_args.args[0]
    assert "(REF_IN -> Clock)[0].class: jif-signal-reference\n" in diag
    assert "(Clock -> Converter)[0].class: jif-signal-clock\n" in diag
    assert "(SYSREF_IN -> FPGA)[0].class: jif-signal-sysref\n" in diag
    assert "(Converter -> FPGA)[0].class: jif-signal-data\n" in diag


def test_layout_recognizes_rewired_sysref_and_jesd_lane_connections():
    """System rewiring keeps SYSREF and JESD links visually distinct."""
    lo = Layout("Rewired signals")
    divider = Node("D1", ntype="divider")
    converter_framer = Node("JESD204 Framer", ntype="jesd204framer")
    fpga_deframer = Node("JESD204 Deframer", ntype="deframer")
    for node in (divider, converter_framer, fpga_deframer):
        lo.add_node(node)
    lo.add_connection({"from": divider, "to": converter_framer})
    lo.add_connection({"from": converter_framer, "to": fpga_deframer})

    with mock.patch("d2.compile", return_value="<svg/>") as compile_mock:
        lo.draw()

    diag = compile_mock.call_args.args[0]
    assert "(D1 -> JESD204 Framer)[0].class: jif-signal-sysref\n" in diag
    assert (
        "(JESD204 Framer -> JESD204 Deframer)[0].class: jif-signal-data\n"
        in diag
    )


def test_xilinx_draw_gtxe2_standalone():
    """Verify standalone drawing for GTXE2 (Gen 2)."""
    fpga = adijif.xilinx()
    fpga.setup_by_dev_kit_name("zc706")

    # Mock solution and solver state needed for draw
    fpga._last_config = True
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

    fpga._last_config = True
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

    conv._last_config = True

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
        res = sys.draw(config, theme="light")
        assert res is not None


def test_system_draw_is_repeatable_across_light_and_dark_themes():
    """Rendering one palette must not leave component state that breaks the next."""
    sys = adijif.system("ad9680", "hmc7044", "xilinx", 125e6)
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.converter.sample_clock = 1e9
    config = sys.solve()

    light = sys.draw(config, theme="light")
    dark = sys.draw(config, theme="dark")

    assert "#E9F8F1" in light
    assert "#102B29" in dark
