# flake8: noqa
import pprint

import pytest

import adijif as jif


def test_get_jesd_mode_from_params_with_jesd_class():
    """Test get_jesd_mode_from_params with jesd_class specified."""
    conv = jif.ad9081_rx()

    # Test with jesd_class filter
    results = jif.utils.get_jesd_mode_from_params(conv, jesd_class="jesd204b", M=4)
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
