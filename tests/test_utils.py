# flake8: noqa
import pprint

import pytest

import adijif as jif

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
