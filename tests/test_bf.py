#!/usr/bin/env python

"""Tests for `adijif` package."""

import numpy as np
import pytest

import adijif

# from adijif import adijif
# from adijif import cli

# from click.testing import CliRunner


def test_ad9680_config_ex1a():
    # Full bandwidth example 1a
    j = adijif.ad9680()
    j.sample_clock = 1e9
    j.L = 4
    j.M = 2
    j.N = 14
    j.Np = 16
    j.K = 32
    j.F = 1

    assert j.S == 1
    assert j.bit_clock == 10e9
    assert j.multiframe_clock == 7812500 * 4


def test_ad9680_config_ex1b():
    # Full bandwidth example 1b
    j = adijif.ad9680()
    j.sample_clock = 1e9
    j.set_quick_configuration_mode(str(0x88))
    j.K = 32  # must set manually
    assert j.L == 4
    assert j.M == 2
    assert j.Np == 16
    assert j.K == 32
    assert j.F == 1
    assert j.S == 1

    assert j.bit_clock == 10e9
    assert j.multiframe_clock == 10e9 / 10 / j.F / j.K


def test_ad9680_config_ex2():
    # Full bandwidth example 1b
    j = adijif.ad9680()
    j.sample_clock = 1e9 / 16
    j.L = 1
    j.M = 8
    j.N = 14
    j.Np = 16
    j.K = 32
    j.F = 16

    assert j.S == 1  # assumed
    assert j.bit_clock == 10e9
    assert j.multiframe_clock == 7812500 / 4


def test_ad9523_1_daq2_config():
    # Full bandwidth example 1b
    clk = adijif.ad9523_1()
    rates = 1e9
    vcxo = 125000000
    cfs = clk.find_dividers(vcxo, rates)

    ref = [
        {
            "m1": 3,
            "n2": 24,
            "vco": 3000000000.0,
            "r2": 1,
            "required_output_divs": 1.0,
        },
        {
            "m1": 3,
            "n2": 48,
            "vco": 3000000000.0,
            "r2": 2,
            "required_output_divs": 1.0,
        },
        {
            "m1": 3,
            "n2": 72,
            "vco": 3000000000.0,
            "r2": 3,
            "required_output_divs": 1.0,
        },
        {
            "m1": 3,
            "n2": 96,
            "vco": 3000000000.0,
            "r2": 4,
            "required_output_divs": 1.0,
        },
        {
            "m1": 3,
            "n2": 120,
            "vco": 3000000000.0,
            "r2": 5,
            "required_output_divs": 1.0,
        },
        {
            "m1": 3,
            "n2": 144,
            "vco": 3000000000.0,
            "r2": 6,
            "required_output_divs": 1.0,
        },
        {
            "m1": 3,
            "n2": 168,
            "vco": 3000000000.0,
            "r2": 7,
            "required_output_divs": 1.0,
        },
        {
            "m1": 3,
            "n2": 192,
            "vco": 3000000000.0,
            "r2": 8,
            "required_output_divs": 1.0,
        },
        {
            "m1": 3,
            "n2": 216,
            "vco": 3000000000.0,
            "r2": 9,
            "required_output_divs": 1.0,
        },
        {
            "m1": 3,
            "n2": 240,
            "vco": 3000000000.0,
            "r2": 10,
            "required_output_divs": 1.0,
        },
    ]
    assert len(cfs) == 10
    assert cfs == ref


def test_ad9523_1_daq2_config_force_m2():
    # Full bandwidth example 1b
    clk = adijif.ad9523_1()
    rates = np.array([1e9, 3e9 / 1000 / 4])
    vcxo = 125000000
    cfs = clk.find_dividers(vcxo, rates)
    assert len(cfs) == 40
    ref = [
        {
            "m1": 3,
            "m2": 4,
            "n2": 24,
            "vco": 3000000000.0,
            "r2": 1,
            "required_output_divs": [1.0],
            "required_output_divs2": [1000.0],
        },
        {
            "m1": 3,
            "m2": 5,
            "n2": 24,
            "vco": 3000000000.0,
            "r2": 1,
            "required_output_divs": [1.0],
            "required_output_divs2": [800.0],
        },
        {
            "m1": 4,
            "m2": 3,
            "n2": 24,
            "vco": 3000000000.0,
            "r2": 1,
            "required_output_divs": [1000.0],
            "required_output_divs2": [1.0],
        },
        {
            "m1": 5,
            "m2": 3,
            "n2": 24,
            "vco": 3000000000.0,
            "r2": 1,
            "required_output_divs": [800.0],
            "required_output_divs2": [1.0],
        },
        {
            "m1": 3,
            "m2": 4,
            "n2": 48,
            "vco": 3000000000.0,
            "r2": 2,
            "required_output_divs": [1.0],
            "required_output_divs2": [1000.0],
        },
        {
            "m1": 3,
            "m2": 5,
            "n2": 48,
            "vco": 3000000000.0,
            "r2": 2,
            "required_output_divs": [1.0],
            "required_output_divs2": [800.0],
        },
        {
            "m1": 4,
            "m2": 3,
            "n2": 48,
            "vco": 3000000000.0,
            "r2": 2,
            "required_output_divs": [1000.0],
            "required_output_divs2": [1.0],
        },
        {
            "m1": 5,
            "m2": 3,
            "n2": 48,
            "vco": 3000000000.0,
            "r2": 2,
            "required_output_divs": [800.0],
            "required_output_divs2": [1.0],
        },
        {
            "m1": 3,
            "m2": 4,
            "n2": 72,
            "vco": 3000000000.0,
            "r2": 3,
            "required_output_divs": [1.0],
            "required_output_divs2": [1000.0],
        },
        {
            "m1": 3,
            "m2": 5,
            "n2": 72,
            "vco": 3000000000.0,
            "r2": 3,
            "required_output_divs": [1.0],
            "required_output_divs2": [800.0],
        },
        {
            "m1": 4,
            "m2": 3,
            "n2": 72,
            "vco": 3000000000.0,
            "r2": 3,
            "required_output_divs": [1000.0],
            "required_output_divs2": [1.0],
        },
        {
            "m1": 5,
            "m2": 3,
            "n2": 72,
            "vco": 3000000000.0,
            "r2": 3,
            "required_output_divs": [800.0],
            "required_output_divs2": [1.0],
        },
        {
            "m1": 3,
            "m2": 4,
            "n2": 96,
            "vco": 3000000000.0,
            "r2": 4,
            "required_output_divs": [1.0],
            "required_output_divs2": [1000.0],
        },
        {
            "m1": 3,
            "m2": 5,
            "n2": 96,
            "vco": 3000000000.0,
            "r2": 4,
            "required_output_divs": [1.0],
            "required_output_divs2": [800.0],
        },
        {
            "m1": 4,
            "m2": 3,
            "n2": 96,
            "vco": 3000000000.0,
            "r2": 4,
            "required_output_divs": [1000.0],
            "required_output_divs2": [1.0],
        },
        {
            "m1": 5,
            "m2": 3,
            "n2": 96,
            "vco": 3000000000.0,
            "r2": 4,
            "required_output_divs": [800.0],
            "required_output_divs2": [1.0],
        },
        {
            "m1": 3,
            "m2": 4,
            "n2": 120,
            "vco": 3000000000.0,
            "r2": 5,
            "required_output_divs": [1.0],
            "required_output_divs2": [1000.0],
        },
        {
            "m1": 3,
            "m2": 5,
            "n2": 120,
            "vco": 3000000000.0,
            "r2": 5,
            "required_output_divs": [1.0],
            "required_output_divs2": [800.0],
        },
        {
            "m1": 4,
            "m2": 3,
            "n2": 120,
            "vco": 3000000000.0,
            "r2": 5,
            "required_output_divs": [1000.0],
            "required_output_divs2": [1.0],
        },
        {
            "m1": 5,
            "m2": 3,
            "n2": 120,
            "vco": 3000000000.0,
            "r2": 5,
            "required_output_divs": [800.0],
            "required_output_divs2": [1.0],
        },
        {
            "m1": 3,
            "m2": 4,
            "n2": 144,
            "vco": 3000000000.0,
            "r2": 6,
            "required_output_divs": [1.0],
            "required_output_divs2": [1000.0],
        },
        {
            "m1": 3,
            "m2": 5,
            "n2": 144,
            "vco": 3000000000.0,
            "r2": 6,
            "required_output_divs": [1.0],
            "required_output_divs2": [800.0],
        },
        {
            "m1": 4,
            "m2": 3,
            "n2": 144,
            "vco": 3000000000.0,
            "r2": 6,
            "required_output_divs": [1000.0],
            "required_output_divs2": [1.0],
        },
        {
            "m1": 5,
            "m2": 3,
            "n2": 144,
            "vco": 3000000000.0,
            "r2": 6,
            "required_output_divs": [800.0],
            "required_output_divs2": [1.0],
        },
        {
            "m1": 3,
            "m2": 4,
            "n2": 168,
            "vco": 3000000000.0,
            "r2": 7,
            "required_output_divs": [1.0],
            "required_output_divs2": [1000.0],
        },
        {
            "m1": 3,
            "m2": 5,
            "n2": 168,
            "vco": 3000000000.0,
            "r2": 7,
            "required_output_divs": [1.0],
            "required_output_divs2": [800.0],
        },
        {
            "m1": 4,
            "m2": 3,
            "n2": 168,
            "vco": 3000000000.0,
            "r2": 7,
            "required_output_divs": [1000.0],
            "required_output_divs2": [1.0],
        },
        {
            "m1": 5,
            "m2": 3,
            "n2": 168,
            "vco": 3000000000.0,
            "r2": 7,
            "required_output_divs": [800.0],
            "required_output_divs2": [1.0],
        },
        {
            "m1": 3,
            "m2": 4,
            "n2": 192,
            "vco": 3000000000.0,
            "r2": 8,
            "required_output_divs": [1.0],
            "required_output_divs2": [1000.0],
        },
        {
            "m1": 3,
            "m2": 5,
            "n2": 192,
            "vco": 3000000000.0,
            "r2": 8,
            "required_output_divs": [1.0],
            "required_output_divs2": [800.0],
        },
        {
            "m1": 4,
            "m2": 3,
            "n2": 192,
            "vco": 3000000000.0,
            "r2": 8,
            "required_output_divs": [1000.0],
            "required_output_divs2": [1.0],
        },
        {
            "m1": 5,
            "m2": 3,
            "n2": 192,
            "vco": 3000000000.0,
            "r2": 8,
            "required_output_divs": [800.0],
            "required_output_divs2": [1.0],
        },
        {
            "m1": 3,
            "m2": 4,
            "n2": 216,
            "vco": 3000000000.0,
            "r2": 9,
            "required_output_divs": [1.0],
            "required_output_divs2": [1000.0],
        },
        {
            "m1": 3,
            "m2": 5,
            "n2": 216,
            "vco": 3000000000.0,
            "r2": 9,
            "required_output_divs": [1.0],
            "required_output_divs2": [800.0],
        },
        {
            "m1": 4,
            "m2": 3,
            "n2": 216,
            "vco": 3000000000.0,
            "r2": 9,
            "required_output_divs": [1000.0],
            "required_output_divs2": [1.0],
        },
        {
            "m1": 5,
            "m2": 3,
            "n2": 216,
            "vco": 3000000000.0,
            "r2": 9,
            "required_output_divs": [800.0],
            "required_output_divs2": [1.0],
        },
        {
            "m1": 3,
            "m2": 4,
            "n2": 240,
            "vco": 3000000000.0,
            "r2": 10,
            "required_output_divs": [1.0],
            "required_output_divs2": [1000.0],
        },
        {
            "m1": 3,
            "m2": 5,
            "n2": 240,
            "vco": 3000000000.0,
            "r2": 10,
            "required_output_divs": [1.0],
            "required_output_divs2": [800.0],
        },
        {
            "m1": 4,
            "m2": 3,
            "n2": 240,
            "vco": 3000000000.0,
            "r2": 10,
            "required_output_divs": [1000.0],
            "required_output_divs2": [1.0],
        },
        {
            "m1": 5,
            "m2": 3,
            "n2": 240,
            "vco": 3000000000.0,
            "r2": 10,
            "required_output_divs": [800.0],
            "required_output_divs2": [1.0],
        },
    ]
    assert cfs == ref


@pytest.mark.skip(reason="Deprecated due to new transceiver models")
def test_daq2_fpga_qpll_rxtx_zc706_config():
    # Full bandwidth example 1b
    clk = adijif.ad9523_1()
    rates = 1e9
    vcxo = 125000000
    cfs = clk.find_dividers(vcxo, rates)
    assert len(cfs) == 10

    adc = adijif.ad9680()
    adc.sample_clock = 1e9
    adc.datapath_decimation = 1
    adc.L = 4
    adc.M = 2
    adc.N = 14
    adc.Np = 16
    adc.K = 32
    adc.F = 1
    assert adc.S == 1
    assert adc.bit_clock == 10e9

    fpga = adijif.xilinx()
    fpga.transciever_type = "GTX2"
    fpga.fpga_family = "Zynq"
    fpga.fpga_package = "FF"
    fpga.speed_grade = -2
    fpga.ref_clock_min = 60000000
    fpga.ref_clock_max = 670000000

    refs = clk.list_available_references(cfs[0])
    for ref in refs:
        try:
            info = fpga.determine_qpll(adc.bit_clock, ref)
            print("PASS", ref, info)
            break
        except:
            print("FAIL")
            continue
    ref = {
        "vco": 10000000000.0,
        "band": 1,
        "d": 1,
        "m": 1,
        "n": 20,
        "qty4_full_rate": 0,
        "type": "QPLL",
    }
    assert info == ref


@pytest.mark.skip(reason="Deprecated due to new transceiver models")
def test_system_daq2_rx_ad9528():
    vcxo = 125000000

    sys = adijif.system("ad9680", "ad9528", "xilinx", vcxo)
    sys.converter.sample_clock = 1e9
    sys.converter.datapath_decimation = 1
    sys.converter.L = 4
    sys.converter.M = 2
    sys.converter.N = 14
    sys.converter.Np = 16
    sys.converter.K = 32
    sys.converter.F = 1

    sys.fpga.setup_by_dev_kit_name("zc706")

    clks = sys.determine_clocks()

    ref = [
        {
            "Converter": np.array(1000000000),
            "ClockChip": [
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 8,
                    "r1": 1,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 16,
                    "r1": 2,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 24,
                    "r1": 3,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 32,
                    "r1": 4,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 40,
                    "r1": 5,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 48,
                    "r1": 6,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 56,
                    "r1": 7,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 64,
                    "r1": 8,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 72,
                    "r1": 9,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 80,
                    "r1": 10,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 88,
                    "r1": 11,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 96,
                    "r1": 12,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 104,
                    "r1": 13,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 112,
                    "r1": 14,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 120,
                    "r1": 15,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 128,
                    "r1": 16,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 136,
                    "r1": 17,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 144,
                    "r1": 18,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 152,
                    "r1": 19,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 160,
                    "r1": 20,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 168,
                    "r1": 21,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 176,
                    "r1": 22,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 184,
                    "r1": 23,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 192,
                    "r1": 24,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 200,
                    "r1": 25,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 208,
                    "r1": 26,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 216,
                    "r1": 27,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 224,
                    "r1": 28,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 240,
                    "r1": 30,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 4,
                    "vco": 4000000000.0,
                    "n2": 248,
                    "r1": 31,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
            ],
        }
    ]

    assert clks == ref


@pytest.mark.skip(reason="Takes too long")
def test_system_daq2_rx_hmc7044():
    vcxo = 125000000

    sys = adijif.system("ad9680", "hmc7044", "xilinx", vcxo)
    sys.converter.sample_clock = 1e9
    sys.converter.datapath_decimation = 1
    sys.converter.L = 4
    sys.converter.M = 2
    sys.converter.N = 14
    sys.converter.Np = 16
    sys.converter.K = 32
    sys.converter.F = 1

    sys.fpga.setup_by_dev_kit_name("zc706")

    clks = sys.determine_clocks()

    print(clks)

    ref = [
        {
            "Converter": np.array(1000000000),
            "ClockChip": [
                {
                    "n2": 12,
                    "r2": 1,
                    "vco": 3000000000.0,
                    "required_output_divs": 3.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                }
            ],
        }
    ]

    assert clks == ref


@pytest.mark.skip(reason="Deprecated due to new transceiver models")
def test_system_daq2_rx():
    vcxo = 125000000

    sys = adijif.system("ad9680", "ad9523_1", "xilinx", vcxo)
    sys.converter.sample_clock = 1e9
    sys.converter.datapath_decimation = 1
    sys.converter.L = 4
    sys.converter.M = 2
    sys.converter.N = 14
    sys.converter.Np = 16
    sys.converter.K = 32
    sys.converter.F = 1

    sys.fpga.setup_by_dev_kit_name("zc706")

    clks = sys.determine_clocks()

    ref = [
        {
            "Converter": np.array(1000000000),
            "ClockChip": [
                {
                    "m1": 3,
                    "n2": 24,
                    "vco": 3000000000.0,
                    "r2": 1,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 3,
                    "n2": 48,
                    "vco": 3000000000.0,
                    "r2": 2,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 3,
                    "n2": 72,
                    "vco": 3000000000.0,
                    "r2": 3,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 3,
                    "n2": 96,
                    "vco": 3000000000.0,
                    "r2": 4,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 3,
                    "n2": 120,
                    "vco": 3000000000.0,
                    "r2": 5,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 3,
                    "n2": 144,
                    "vco": 3000000000.0,
                    "r2": 6,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 3,
                    "n2": 168,
                    "vco": 3000000000.0,
                    "r2": 7,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 3,
                    "n2": 192,
                    "vco": 3000000000.0,
                    "r2": 8,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 3,
                    "n2": 216,
                    "vco": 3000000000.0,
                    "r2": 9,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
                {
                    "m1": 3,
                    "n2": 240,
                    "vco": 3000000000.0,
                    "r2": 10,
                    "required_output_divs": 1.0,
                    "fpga_pll_config": {
                        "vco": 10000000000.0,
                        "band": 1,
                        "d": 1,
                        "m": 1,
                        "n": 20,
                        "qty4_full_rate": 0,
                        "type": "QPLL",
                    },
                    "sysref_rate": 7812500.0,
                },
            ],
        }
    ]
    assert clks == ref
