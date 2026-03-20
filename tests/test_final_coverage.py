"""Final batch of tests to reach 90% coverage."""

import pytest

import adijif


def test_xilinx_ref_clock_ranges_coverage():
    """Verify reference clock ranges for various transceivers."""
    fpga = adijif.xilinx()

    # GTXE2
    fpga.transceiver_type = "GTXE2"
    assert fpga._ref_clock_min == 60000000

    # GTHE3
    fpga.transceiver_type = "GTHE3"
    with pytest.raises(Exception, match="Unknown ref_clock_min"):
        _ = fpga._ref_clock_min

    # GTYE4
    fpga.transceiver_type = "GTYE4"
    with pytest.raises(Exception, match="Unknown ref_clock_max"):
        _ = fpga._ref_clock_max


def test_system_initialize_edge_cases():
    """Verify edge cases in system initialization."""
    sys = adijif.system("ad9680", "ad9523_1", "xilinx", 125e6, solver="CPLEX")
    sys.fpga.setup_by_dev_kit_name("zc706")

    # ad9523_1 model is missing some initialization in standalone mode
    if not hasattr(sys.clock, "config"):
        sys.clock.config = {"out_dividers": [], "r2": 1, "n2": 10, "m1": 1}

    # Exercise _get_ref_clock and related paths
    from adijif.converters.ad9680 import ad9680

    conv = ad9680(sys.model)
    config = {}
    clock_names = []

    # Call internal helper
    res_config, res_names = sys._get_ref_clock(conv, config, clock_names)
    assert "AD9680_ref_clk" in res_config


def test_ad9084_util_apply_settings_no_mode():
    """Verify apply_settings raises on missing mode."""
    from adijif.converters.ad9084_util import apply_settings

    # Mock a converter
    class MockConv:
        name = "AD9084"
        quick_configuration_modes = {"jesd204c": {}}

        def __init__(self):
            class DP:
                cddc_decimations = []
                fddc_decimations = []
                fddc_enabled = []

            self.datapath = DP()

    profile_settings = {
        "device_clock_Hz": 10e9,
        "datapath": {"cddc_decimation": 1, "fddc_decimation": 1},
        "jesd_settings": {
            "jtx": {
                "M": 99,
                "L": 1,
                "S": 1,
                "Np": 16,
                "K": 32,
                "F": 2,
                "N": 16,
            },
            "jrx": {
                "M": 99,
                "L": 1,
                "S": 1,
                "Np": 16,
                "K": 32,
                "F": 2,
                "N": 16,
            },
        },
    }
    with pytest.raises(Exception, match="No JESD mode found"):
        apply_settings(MockConv(), profile_settings)


def test_ad9084_util_load_rx_modes():
    """Verify _load_rx_config_modes internal helper."""
    from adijif.converters.ad9084_util import _load_rx_config_modes

    modes = _load_rx_config_modes(part="AD9084")
    assert len(modes) > 0
    # It's a dict where keys are mode IDs
    key = list(modes.keys())[0]
    assert modes[key] is not None


def test_system_complex_filter_sysref():
    """Verify complex branch in _filter_sysref."""
    sys = adijif.system("ad9680", "ad9523_1", "xilinx", 125e6, solver="CPLEX")
    sys.use_common_sysref = True

    # Mock multiple converters to hit the loop logic
    conv1 = adijif.ad9680(sys.model)
    conv2 = adijif.ad9680(sys.model)
    conv1.name = "C1"
    conv2.name = "C2"

    clocks = [1e9, 7.8125e6, 1e9, 7.8125e6]
    names = ["C1_clk", "C1_sr", "C2_clk", "C2_sr"]

    res_clks, res_names = sys._filter_sysref(clocks, names, [conv1, conv2])
    assert len(res_clks) == 3
    assert "C2_sr" not in res_names
