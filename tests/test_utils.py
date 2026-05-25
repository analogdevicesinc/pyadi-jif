# flake8: noqa
import pprint

import pytest

import adijif as jif


def test_get_jesd_mode_from_params_with_jesd_class():
    """Test get_jesd_mode_from_params with jesd_class specified."""
    conv = jif.ad9081_rx()

    # Test with jesd_class filter
    results = jif.utils.get_jesd_mode_from_params(
        conv, jesd_class="jesd204b", M=4
    )
    assert len(results) > 0
    for result in results:
        assert result["jesd_class"] == "jesd204b"
        assert result["settings"]["M"] == 4


def test_get_jesd_mode_from_params_with_list_values():
    """Test get_jesd_mode_from_params with list of values."""
    conv = jif.ad9081_rx()

    # Test with list of values
    results = jif.utils.get_jesd_mode_from_params(conv, M=[2, 4])
    assert len(results) > 0
    for result in results:
        assert result["settings"]["M"] in [2, 4]


def test_get_jesd_mode_from_params_invalid_key():
    """Test get_jesd_mode_from_params with invalid key."""
    conv = jif.ad9081_rx()

    # Test with invalid key should raise exception
    with pytest.raises(Exception, match="not in JESD Configs"):
        jif.utils.get_jesd_mode_from_params(conv, invalid_key=123)


def test_get_jesd_mode_from_params_no_match():
    """Test get_jesd_mode_from_params when no mode matches."""
    conv = jif.ad9081_rx()

    # Test with impossible parameters should raise exception
    with pytest.raises(Exception, match="No JESD mode found"):
        jif.utils.get_jesd_mode_from_params(conv, M=999)


def test_generate_max_rates_fpga_limits_utility():
    """Test get_max_sample_rates with FPGA and various limits."""
    conv = jif.ad9081_rx()

    # Determine max data rate from FPGA
    fpga = jif.xilinx()
    fpga.setup_by_dev_kit_name("zc706")
    fpga.sys_clk_select = "XCVR_QPLL0"  # Use faster QPLL

    limits = {"jesd_class": "jesd204b", "bit_clock": {"<=": 10e9}}

    results = jif.utils.get_max_sample_rates(conv, fpga, limits)

    assert len(results) > 0
    for result in results:
        assert result["bit_clock"] <= 10e9
        assert result["jesd_class"] == "jesd204b"


def test_generate_max_rates_with_numeric_limits():
    """Test get_max_sample_rates with numeric comparison limits."""
    conv = jif.ad9081_rx()

    # Test with greater than limit
    limits = {"L": {">": 3}}
    results = jif.utils.get_max_sample_rates(conv, limits=limits)

    assert len(results) > 0
    for result in results:
        assert result["L"] > 3


def test_generate_max_rates_with_invalid_limit_format():
    """Test get_max_sample_rates with invalid limit format."""
    conv = jif.ad9081_rx()

    # Test with invalid limit format (not dict or string)
    limits = {"L": [1, 2, 3]}  # list is invalid

    with pytest.raises(
        Exception, match="Numeric limits must be described in a nested dict"
    ):
        jif.utils.get_max_sample_rates(conv, limits=limits)


def test_generate_max_rates_with_invalid_property():
    """Test get_max_sample_rates with invalid converter property."""
    conv = jif.ad9081_rx()

    # Test with property that doesn't exist
    limits = {"nonexistent_property": {"==": 10}}

    with pytest.raises(AttributeError, match="does not have property"):
        jif.utils.get_max_sample_rates(conv, limits=limits)


def test_generate_max_rates_with_string_limits():
    """Test get_max_sample_rates with string value limits."""
    conv = jif.ad9680()

    # Test with string comparison
    limits = {"jesd_class": "jesd204b"}
    results = jif.utils.get_max_sample_rates(conv, limits=limits)

    assert len(results) > 0
    for result in results:
        assert result["jesd_class"] == "jesd204b"


def test_generate_max_rates_unsupported_fpga():
    """Test get_max_sample_rates with unsupported FPGA transceiver type."""
    conv = jif.ad9680()

    fpga = jif.xilinx()
    fpga.setup_by_dev_kit_name("zc706")
    # Mock an unsupported transceiver type
    fpga.transceiver_type = "GTH19"  # Invalid - position 4 should be 2, 3, or 4

    with pytest.raises(Exception, match="Unsupported FPGA transceiver type"):
        jif.utils.get_max_sample_rates(conv, fpga=fpga)


def test_generate_max_rates_with_ultrascaleplus():
    """Test get_max_sample_rates with UltraScale+ FPGA."""
    conv = jif.ad9680()

    fpga = jif.xilinx()
    fpga.setup_by_dev_kit_name("vcu118")  # UltraScale+ board

    results = jif.utils.get_max_sample_rates(
        conv, fpga=fpga, limits={"jesd_class": "jesd204b"}
    )

    assert len(results) > 0


# def test_generate_max_rates_fpga_limits_utility():
#     conv = jif.ad9081_rx()

#     # Determine max data rate from FPGA
#     fpga = jif.xilinx()
#     fpga.setup_by_dev_kit_name("zc706")
#     fpga.sys_clk_select = "GTH34_SYSCLK_QPLL0"  # Use faster QPLL

#     limits = {"jesd_class": "jesd204b", "bit_clock": {"<=": 10e9}}

#     results = jif.utils.get_max_sample_rates(conv, fpga, limits)

#     ref = []
#     assert results == ref


def test_generate_max_rates_fpga_utility():
    conv = jif.ad9081_rx()
    # conv.decimation = 1

    # Determine max data rate from FPGA
    fpga = jif.xilinx()
    fpga.setup_by_dev_kit_name("zc706")
    fpga.sys_clk_select = "XCVR_QPLL0"  # Use faster QPLL

    limits = {"jesd_class": "jesd204b"}

    results = jif.utils.get_max_sample_rates(conv, fpga, limits)

    ref = [
        {
            "sample_clock": 4000000000.0,
            "bit_clock": 10000000000.0,
            "L": 8,
            "M": 1,
            "quick_configuration_mode": "19.01",
            "jesd_class": "jesd204b",
        },
        {
            "sample_clock": 2062500000.0,
            "bit_clock": 10312500000.0,
            "L": 8,
            "M": 2,
            "quick_configuration_mode": "19.0",
            "jesd_class": "jesd204b",
        },
        {
            "sample_clock": 515625000.0,
            "bit_clock": 10312500000.0,
            "L": 3,
            "M": 3,
            "quick_configuration_mode": "9.01",
            "jesd_class": "jesd204b",
        },
        {
            "sample_clock": 1031250000.0,
            "bit_clock": 10312500000.0,
            "L": 8,
            "M": 4,
            "quick_configuration_mode": "18.0",
            "jesd_class": "jesd204b",
        },
        {
            "sample_clock": 515625000.0,
            "bit_clock": 10312500000.0,
            "L": 6,
            "M": 6,
            "quick_configuration_mode": "15.01",
            "jesd_class": "jesd204b",
        },
        {
            "sample_clock": 515625000.0,
            "bit_clock": 10312500000.0,
            "L": 8,
            "M": 8,
            "quick_configuration_mode": "16.0",
            "jesd_class": "jesd204b",
        },
        {
            "sample_clock": 257812500.0,
            "bit_clock": 10312500000.0,
            "L": 6,
            "M": 12,
            "quick_configuration_mode": "15.1",
            "jesd_class": "jesd204b",
        },
        {
            "sample_clock": 257812500.0,
            "bit_clock": 10312500000.0,
            "L": 8,
            "M": 16,
            "quick_configuration_mode": "17.0",
            "jesd_class": "jesd204b",
        },
    ]
    assert len(results) == len(ref)
    for result in results:
        # print(result)
        if result not in ref:
            pprint.pprint(result)
        assert result in ref


def test_find_extreme_rate_single_mode_max_lane_no_fpga():
    """Single mode, max lane rate, no FPGA: should equal JESD-class max."""
    conv = jif.ad9081_rx()
    result = jif.utils.find_extreme_rate(
        conv, target="lane", sense="max", mode="19.0", jesd_class="jesd204b"
    )
    assert result["bit_clock"] == 15.5e9
    assert result["jesd_class"] == "jesd204b"
    assert result["mode"] == "19.0"
    # Input converter must not be mutated
    assert conv._sample_clock == 122.88e6


def test_find_extreme_rate_single_mode_min_sample_no_fpga():
    """Single mode, min sample rate: bounded by JESD-class bit_clock_min."""
    conv = jif.ad9081_rx()
    result = jif.utils.find_extreme_rate(
        conv, target="sample", sense="min", mode="19.0", jesd_class="jesd204b"
    )
    # bit_clock_min[jesd204b] = 1.5e9; factor = L*en/(ed*M*Np) = 8*8/(10*2*16) = 0.2
    # sc_min = 1.5e9 * 0.2 = 3e8
    assert result["sample_clock"] == 3e8
    assert result["bit_clock"] == 1.5e9


def test_find_extreme_rate_with_fpga_matches_get_max_sample_rates():
    """With FPGA, single mode matches the reference brute-force result."""
    conv = jif.ad9081_rx()
    fpga = jif.xilinx()
    fpga.setup_by_dev_kit_name("zc706")
    fpga.sys_clk_select = "XCVR_QPLL0"

    # Mode 19.01 (M=1, L=8) bounded by converter sample_clock_max = 4e9
    result_19_01 = jif.utils.find_extreme_rate(
        conv,
        target="lane",
        sense="max",
        mode="19.01",
        jesd_class="jesd204b",
        fpga=fpga,
    )
    assert result_19_01["bit_clock"] == 10e9
    assert result_19_01["sample_clock"] == 4e9
    assert result_19_01["M"] == 1
    assert result_19_01["L"] == 8

    # Mode 19.0 (M=2, L=8) bounded by FPGA QPLL VCO cap
    result_19_0 = jif.utils.find_extreme_rate(
        conv,
        target="lane",
        sense="max",
        mode="19.0",
        jesd_class="jesd204b",
        fpga=fpga,
    )
    assert result_19_0["bit_clock"] == 10.3125e9
    assert result_19_0["sample_clock"] == 2.0625e9
    assert result_19_0["M"] == 2


def test_find_extreme_rate_enumerate_modes_no_fpga():
    """Mode=None enumerates all modes and picks the best."""
    conv = jif.ad9081_rx()
    result = jif.utils.find_extreme_rate(conv, target="lane", sense="max")
    # Max possible: jesd204c bit_clock_max = 24.75e9
    assert result["bit_clock"] == 24.75e9
    assert result["jesd_class"] == "jesd204c"


def test_find_extreme_rate_enumerate_modes_with_fpga():
    """Enumeration with FPGA cap; max sample rate respects converter cap."""
    conv = jif.ad9081_rx()
    fpga = jif.xilinx()
    fpga.setup_by_dev_kit_name("zc706")
    fpga.sys_clk_select = "XCVR_QPLL0"

    result = jif.utils.find_extreme_rate(
        conv, target="sample", sense="max", fpga=fpga
    )
    # AD9081_RX sample_clock_max = 4e9; achievable in mode 19.01
    assert result["sample_clock"] == 4e9


def test_find_extreme_rate_does_not_mutate_input():
    """Repeated calls leave the input converter's state untouched."""
    conv = jif.ad9081_rx()
    conv.sample_clock = 1.5e9
    original_sc = conv._sample_clock
    original_jesd = conv.jesd_class
    jif.utils.find_extreme_rate(conv, target="lane", sense="max")
    assert conv._sample_clock == original_sc
    assert conv.jesd_class == original_jesd


def test_find_extreme_rate_jesd_class_auto_search():
    """Mode key that lives in only one JESD class is auto-detected."""
    conv = jif.ad9680()
    # AD9680 only supports jesd204b
    result = jif.utils.find_extreme_rate(
        conv, mode="64", target="lane", sense="max"
    )
    assert result["jesd_class"] == "jesd204b"


def test_find_extreme_rate_ambiguous_mode_requires_jesd_class():
    """Mode present in multiple classes errors when jesd_class is omitted."""
    conv = jif.ad9081_rx()
    with pytest.raises(ValueError, match="ambiguous"):
        jif.utils.find_extreme_rate(conv, mode="19.0")


def test_find_extreme_rate_invalid_target():
    with pytest.raises(ValueError, match="target"):
        jif.utils.find_extreme_rate(jif.ad9081_rx(), target="invalid")


def test_find_extreme_rate_invalid_sense():
    with pytest.raises(ValueError, match="sense"):
        jif.utils.find_extreme_rate(jif.ad9081_rx(), sense="invalid")


def test_find_extreme_rate_unknown_mode():
    with pytest.raises(ValueError, match="not found"):
        jif.utils.find_extreme_rate(
            jif.ad9081_rx(), mode="999", jesd_class="jesd204b"
        )


def test_find_extreme_rate_nested_converter_rejected():
    """Nested MxFE devices must be split into rx/tx before calling."""
    with pytest.raises(Exception, match="nested"):
        jif.utils.find_extreme_rate(jif.ad9081())


def test_find_extreme_rate_clock_requires_fpga():
    """Clock supplied without an FPGA is a hard error."""
    with pytest.raises(ValueError, match="requires fpga"):
        jif.utils.find_extreme_rate(
            jif.ad9680(), clock=jif.hmc7044(), vcxo=125e6
        )


def test_find_extreme_rate_clock_requires_vcxo():
    """Clock supplied without a VCXO is a hard error."""
    fpga = jif.xilinx()
    fpga.setup_by_dev_kit_name("zc706")
    with pytest.raises(ValueError, match="vcxo is required"):
        jif.utils.find_extreme_rate(
            jif.ad9680(), clock=jif.hmc7044(), fpga=fpga
        )


def test_find_extreme_rate_vcxo_without_clock_rejected():
    """vcxo passed without clock is rejected."""
    fpga = jif.xilinx()
    fpga.setup_by_dev_kit_name("zc706")
    with pytest.raises(ValueError, match="vcxo is only meaningful"):
        jif.utils.find_extreme_rate(jif.ad9680(), vcxo=125e6, fpga=fpga)


def test_find_extreme_rate_with_clock_and_fpga_single_mode():
    """Full clock chain: AD9680 + HMC7044 + ZC706 caps at the FPGA QPLL VCO."""
    conv = jif.ad9680()
    clock = jif.hmc7044()
    fpga = jif.xilinx()
    fpga.setup_by_dev_kit_name("zc706")

    result = jif.utils.find_extreme_rate(
        conv,
        target="lane",
        sense="max",
        mode="64",
        jesd_class="jesd204b",
        clock=clock,
        fpga=fpga,
        vcxo=125e6,
    )
    # ZC706 GTX QPLL VCO max = 10.3125 GHz, applied as the bit-rate cap
    assert result["bit_clock"] == 10.3125e9
    assert result["sample_clock"] == 1.03125e9
    assert result["mode"] == "64"
    assert result["clock_config"] is not None
    assert result["fpga_config"] is not None
    assert "output_clocks" in result["clock_config"]
    # Inputs unchanged
    assert conv._sample_clock == 1e9  # AD9680 default
    assert clock._objectives == [] or all(
        not isinstance(o.expr, type(None)) for o in clock._objectives
    )


def test_find_extreme_rate_with_clock_min_sense():
    """Min sense bounded by JESD-class bit_clock_min."""
    conv = jif.ad9680()
    clock = jif.hmc7044()
    fpga = jif.xilinx()
    fpga.setup_by_dev_kit_name("zc706")

    result = jif.utils.find_extreme_rate(
        conv,
        target="lane",
        sense="min",
        mode="64",
        jesd_class="jesd204b",
        clock=clock,
        fpga=fpga,
        vcxo=125e6,
    )
    # AD9680 bit_clock_min[jesd204b] = 3.125e9
    assert result["bit_clock"] == 3.125e9


def test_find_extreme_rate_with_clock_enumerate_modes():
    """Mode=None with clock+fpga enumerates and picks the winner."""
    clock = jif.hmc7044()
    fpga = jif.xilinx()
    fpga.setup_by_dev_kit_name("zc706")
    result = jif.utils.find_extreme_rate(
        jif.ad9680(),
        target="sample",
        sense="max",
        clock=clock,
        fpga=fpga,
        vcxo=125e6,
    )
    # AD9680 sample_clock_max = 1.25 GSPS, reachable via at least one mode
    assert result["sample_clock"] == 1.25e9
    assert result["clock_config"] is not None


def test_find_extreme_rate_ad9680_ultrascaleplus():
    """AD9680 with UltraScale+ FPGA enumeration returns a feasible result."""
    conv = jif.ad9680()
    fpga = jif.xilinx()
    fpga.setup_by_dev_kit_name("vcu118")
    result = jif.utils.find_extreme_rate(
        conv, target="sample", sense="max", fpga=fpga
    )
    # AD9680 sample_clock_max = 1.25 GSPS
    assert result["sample_clock"] == 1.25e9


def test_generate_max_rates_utility():
    conv = jif.ad9081_rx()
    # conv.decimation = 1

    results = jif.utils.get_max_sample_rates(conv)

    ref = [
        {
            "L": 8,
            "M": 1,
            "bit_clock": 10000000000.0,
            "quick_configuration_mode": "19.01",
            "sample_clock": 4000000000.0,
            "jesd_class": "jesd204b",
        },
        {
            "L": 4,
            "M": 2,
            "bit_clock": 24750000000.0,
            "quick_configuration_mode": "14.0",
            "sample_clock": 4000000000.0,
            "jesd_class": "jesd204c",
        },
        {
            "L": 3,
            "M": 3,
            "bit_clock": 24750000000.0,
            "quick_configuration_mode": "9.01",
            "sample_clock": 1500000000.0,
            "jesd_class": "jesd204c",
        },
        {
            "L": 8,
            "M": 4,
            "bit_clock": 24750000000.0,
            "quick_configuration_mode": "27.0",
            "sample_clock": 4000000000.0,
            "jesd_class": "jesd204c",
        },
        {
            "L": 6,
            "M": 6,
            "bit_clock": 24750000000.0,
            "quick_configuration_mode": "15.01",
            "sample_clock": 1500000000.0,
            "jesd_class": "jesd204c",
        },
        {
            "L": 8,
            "M": 8,
            "bit_clock": 24750000000.0,
            "quick_configuration_mode": "26.0",
            "sample_clock": 2000000000.0,
            "jesd_class": "jesd204c",
        },
        {
            "L": 6,
            "M": 12,
            "bit_clock": 24750000000.0,
            "quick_configuration_mode": "15.0",
            "sample_clock": 750000000.0,
            "jesd_class": "jesd204c",
        },
        {
            "L": 8,
            "M": 16,
            "bit_clock": 24750000000.0,
            "quick_configuration_mode": "17.0",
            "sample_clock": 750000000.0,
            "jesd_class": "jesd204c",
        },
    ]

    # pprint.pprint(results)

    assert len(results) == len(ref)
    for result in results:
        if result not in ref:
            pprint.pprint(result)
        assert result in ref
