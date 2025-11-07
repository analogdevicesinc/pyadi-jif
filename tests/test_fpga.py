# flake8: noqa
import pprint

import pytest

import adijif


def test_jesd_unknown_dev():
    name = "zcu103"
    with pytest.raises(Exception, match=f"No boardname found in library for {name}"):
        f = adijif.xilinx()
        f.setup_by_dev_kit_name(name)


def test_jesd_wrong_order():
    msg = (
        "get_required_clocks must be run to generated"
        + " dependent clocks before names are available"
    )
    with pytest.raises(Exception, match=msg):
        f = adijif.xilinx()
        f.ref_clock_min = 60000000
        f.ref_clock_max = 670000000
        cn = f.get_required_clock_names()


def test_ref_clock_not_set():
    msg = "ref_clock_min or ref_clock_max not set"
    with pytest.raises(Exception, match=msg):
        f = adijif.xilinx()
        cn = f.get_required_clocks([], [])


def test_xilinx_transceiver_generation():
    """Test xilinx transceiver generation method."""
    f = adijif.xilinx()
    f.transceiver_type = "GTXE2"

    gen = f.trx_gen()
    assert gen == 2

    f.transceiver_type = "GTHE3"
    gen = f.trx_gen()
    assert gen == 3


def test_xilinx_speed_grades():
    """Test xilinx speed grade configuration."""
    f = adijif.xilinx()

    # Test valid speed grade
    f.speed_grade = -3
    assert f.speed_grade in f.available_speed_grades

    # Test another valid speed grade
    f.speed_grade = -1
    assert f.speed_grade in f.available_speed_grades


def test_xilinx_force_cpll():
    """Test xilinx CPLL forcing attribute."""
    sys = adijif.system("ad9680", "hmc7044", "xilinx", 125e6)
    sys.fpga.setup_by_dev_kit_name("zc706")

    # Test that attribute can be set
    sys.fpga.force_cpll = True
    assert sys.fpga.force_cpll is True


def test_xilinx_force_separate_device_clock():
    """Test xilinx with forced separate device clock attribute."""
    sys = adijif.system("ad9680", "hmc7044", "xilinx", 125e6)
    sys.fpga.setup_by_dev_kit_name("zc706")

    # Test that attribute can be set
    sys.fpga.force_separate_device_clock = True
    assert sys.fpga.force_separate_device_clock is True


def test_xilinx_ref_clock_constraint():
    """Test xilinx reference clock constraint options."""
    sys = adijif.system("ad9680", "hmc7044", "xilinx", 125e6)
    sys.fpga.setup_by_dev_kit_name("zc706")

    # Test that constraint can be set
    sys.fpga._ref_clock_constraint = "CORE_CLOCK_DIV2"
    assert sys.fpga._ref_clock_constraint == "CORE_CLOCK_DIV2"


def test_xilinx_favor_cpll_over_qpll():
    """Test xilinx with favor CPLL over QPLL attribute."""
    sys = adijif.system("ad9680", "hmc7044", "xilinx", 125e6)
    sys.fpga.setup_by_dev_kit_name("zc706")

    # Test that attribute can be set
    sys.fpga.favor_cpll_over_qpll = True
    assert sys.fpga.favor_cpll_over_qpll is True


def test_xilinx_minimize_fpga_ref_clock():
    """Test xilinx with minimize FPGA ref clock attribute."""
    sys = adijif.system("ad9680", "hmc7044", "xilinx", 125e6)
    sys.fpga.setup_by_dev_kit_name("zc706")

    # Test that attribute can be set
    sys.fpga.minimize_fpga_ref_clock = True
    assert sys.fpga.minimize_fpga_ref_clock is True


def test_xilinx_package_and_family():
    """Test xilinx package and family settings."""
    f = adijif.xilinx()

    # Test valid package
    f.fpga_package = "FF"
    assert f.fpga_package in f.available_fpga_packages

    # Test valid family
    f.fpga_family = "Kintex"
    assert f.fpga_family in f.available_fpga_families
