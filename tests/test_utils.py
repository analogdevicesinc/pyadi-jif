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
    conv.decimation = 1

    # Determine max data rate from FPGA
    fpga = jif.xilinx()
    fpga.setup_by_dev_kit_name("zc706")
    fpga.sys_clk_select = "GTH34_SYSCLK_QPLL0"  # Use faster QPLL

    limits = {"jesd_class": "jesd204b", "bit_clock": {"<": 1e9}}

    results = jif.utils.get_max_sample_rates(conv, fpga)

    ref = [
        {
            "sample_clock": 4000000000.0,
            "bit_clock": 10000000000.0,
            "L": 8,
            "M": 1,
            "quick_configuration_mode": "19.01",
        },
        {
            "sample_clock": 3333333333.3333335,
            "bit_clock": 12500000000.0,
            "L": 8,
            "M": 2,
            "quick_configuration_mode": "28.0",
        },
        {
            "sample_clock": 625000000.0,
            "bit_clock": 12500000000.0,
            "L": 3,
            "M": 3,
            "quick_configuration_mode": "9.01",
        },
        {
            "sample_clock": 1666666666.6666667,
            "bit_clock": 12500000000.0,
            "L": 8,
            "M": 4,
            "quick_configuration_mode": "27.0",
        },
        {
            "sample_clock": 625000000.0,
            "bit_clock": 12500000000.0,
            "L": 6,
            "M": 6,
            "quick_configuration_mode": "15.01",
        },
        {
            "sample_clock": 833333333.3333334,
            "bit_clock": 12500000000.0,
            "L": 8,
            "M": 8,
            "quick_configuration_mode": "26.0",
        },
        {
            "sample_clock": 312500000.0,
            "bit_clock": 12500000000.0,
            "L": 6,
            "M": 12,
            "quick_configuration_mode": "15.1",
        },
        {
            "sample_clock": 312500000.0,
            "bit_clock": 12500000000.0,
            "L": 8,
            "M": 16,
            "quick_configuration_mode": "17.0",
        },
    ]
    assert len(results) == len(ref)
    for result in results:
        # print(result)
        assert result in ref


def test_generate_max_rates_utility():
    conv = jif.ad9081_rx()
    conv.decimation = 1

    results = jif.utils.get_max_sample_rates(conv)

    ref = [
        {
            "L": 8,
            "M": 1,
            "bit_clock": 10000000000.0,
            "quick_configuration_mode": "19.01",
            "sample_clock": 4000000000.0,
        },
        {
            "L": 8,
            "M": 2,
            "bit_clock": 15000000000.0,
            "quick_configuration_mode": "28.0",
            "sample_clock": 4000000000.0,
        },
        {
            "L": 3,
            "M": 3,
            "bit_clock": 15500000000.0,
            "quick_configuration_mode": "9.01",
            "sample_clock": 775000000.0,
        },
        {
            "L": 8,
            "M": 4,
            "bit_clock": 24750000000.0,
            "quick_configuration_mode": "27.0",
            "sample_clock": 3300000000.0,
        },
        {
            "L": 6,
            "M": 6,
            "bit_clock": 15500000000.0,
            "quick_configuration_mode": "15.01",
            "sample_clock": 775000000.0,
        },
        {
            "L": 8,
            "M": 8,
            "bit_clock": 24750000000.0,
            "quick_configuration_mode": "26.0",
            "sample_clock": 1650000000.0,
        },
        {
            "L": 6,
            "M": 12,
            "bit_clock": 15500000000.0,
            "quick_configuration_mode": "15.1",
            "sample_clock": 387500000.0,
        },
        {
            "L": 8,
            "M": 16,
            "bit_clock": 15500000000.0,
            "quick_configuration_mode": "17.0",
            "sample_clock": 387500000.0,
        },
    ]

    pprint.pprint(results)

    assert len(results) == len(ref)
    for result in results:
        print(result)
        assert result in ref
