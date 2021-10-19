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
            "quick_configuration_mode": "963",
        },
        {
            "sample_clock": 3333333333.3333335,
            "bit_clock": 12500000000.0,
            "L": 8,
            "M": 2,
            "quick_configuration_mode": "1263",
        },
        {
            "sample_clock": 625000000.0,
            "bit_clock": 12500000000.0,
            "L": 3,
            "M": 3,
            "quick_configuration_mode": "859",
        },
        {
            "sample_clock": 1666666666.6666667,
            "bit_clock": 12500000000.0,
            "L": 8,
            "M": 4,
            "quick_configuration_mode": "1261",
        },
        {
            "sample_clock": 625000000.0,
            "bit_clock": 12500000000.0,
            "L": 6,
            "M": 6,
            "quick_configuration_mode": "919",
        },
        {
            "sample_clock": 833333333.3333334,
            "bit_clock": 12500000000.0,
            "L": 8,
            "M": 8,
            "quick_configuration_mode": "1259",
        },
        {
            "sample_clock": 312500000.0,
            "bit_clock": 12500000000.0,
            "L": 6,
            "M": 12,
            "quick_configuration_mode": "206",
        },
        {
            "sample_clock": 312500000.0,
            "bit_clock": 12500000000.0,
            "L": 8,
            "M": 16,
            "quick_configuration_mode": "234",
        },
    ]
    print(results)
    assert results == ref


def test_generate_max_rates_utility():
    conv = jif.ad9081_rx()

    results = jif.utils.get_max_sample_rates(conv)

    ref = [
        {
            "sample_clock": 4000000000.0,
            "bit_clock": 20000000000.0,
            "L": 4,
            "M": 1,
            "quick_configuration_mode": "913",
        },
        {
            "sample_clock": 4000000000.0,
            "bit_clock": 20000000000.0,
            "L": 8,
            "M": 2,
            "quick_configuration_mode": "262",
        },
        {
            "sample_clock": 1237500000.0,
            "bit_clock": 24750000000.0,
            "L": 3,
            "M": 3,
            "quick_configuration_mode": "859",
        },
        {
            "sample_clock": 3300000000.0,
            "bit_clock": 24750000000.0,
            "L": 8,
            "M": 4,
            "quick_configuration_mode": "1261",
        },
        {
            "sample_clock": 1237500000.0,
            "bit_clock": 24750000000.0,
            "L": 6,
            "M": 6,
            "quick_configuration_mode": "919",
        },
        {
            "sample_clock": 1650000000.0,
            "bit_clock": 24750000000.0,
            "L": 8,
            "M": 8,
            "quick_configuration_mode": "1259",
        },
        {
            "sample_clock": 618750000.0,
            "bit_clock": 24750000000.0,
            "L": 6,
            "M": 12,
            "quick_configuration_mode": "206",
        },
        {
            "sample_clock": 618750000.0,
            "bit_clock": 24750000000.0,
            "L": 8,
            "M": 16,
            "quick_configuration_mode": "234",
        },
    ]

    print(results)
    # assert results == ref
