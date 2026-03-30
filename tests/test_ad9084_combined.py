"""Tests for AD9084 combined RX+TX model."""

import pytest

import adijif
from adijif.converters.ad9084 import ad9084, ad9084_rx, ad9084_tx

# ── Instantiation ────────────────────────────────────────────────────────────


def test_ad9084_instantiation():
    """Verify AD9084 combined model instantiates without error."""
    dev = ad9084(solver="CPLEX")
    assert dev is not None


def test_ad9084_name():
    """Verify AD9084 combined model has the expected name."""
    dev = ad9084(solver="CPLEX")
    assert dev.name == "AD9084"


def test_ad9084_converter_type():
    """Verify AD9084 combined model reports adc_dac converter type."""
    dev = ad9084(solver="CPLEX")
    assert dev.converter_type == "adc_dac"


def test_ad9084_nested_attribute():
    """Verify _nested lists both adc and dac."""
    dev = ad9084(solver="CPLEX")
    assert dev._nested == ["adc", "dac"]


def test_ad9084_has_adc_sub_converter():
    """Verify AD9084 combined model exposes an adc sub-converter."""
    dev = ad9084(solver="CPLEX")
    assert hasattr(dev, "adc")
    assert isinstance(dev.adc, ad9084_rx)


def test_ad9084_has_dac_sub_converter():
    """Verify AD9084 combined model exposes a dac sub-converter."""
    dev = ad9084(solver="CPLEX")
    assert hasattr(dev, "dac")
    assert isinstance(dev.dac, ad9084_tx)


def test_ad9084_via_system():
    """Verify AD9084 combined model can be created through the system factory."""
    sys = adijif.system(
        "ad9084", "hmc7044", "xilinx", 125000000, solver="CPLEX"
    )
    assert sys.converter.name == "AD9084"


def test_ad9084_accessible_from_adijif():
    """Verify ad9084 is exported at the adijif package level."""
    assert hasattr(adijif, "ad9084")
    assert adijif.ad9084 is ad9084


# ── Sub-converter defaults ────────────────────────────────────────────────────


def test_ad9084_adc_is_ad9084_rx():
    """Verify the adc sub-converter is an AD9084_RX instance."""
    dev = ad9084(solver="CPLEX")
    assert dev.adc.name == "AD9084_RX"
    assert dev.adc.converter_type == "adc"


def test_ad9084_dac_is_ad9084_tx():
    """Verify the dac sub-converter is an AD9084_TX instance."""
    dev = ad9084(solver="CPLEX")
    assert dev.dac.name == "AD9084_TX"
    assert dev.dac.converter_type == "dac"


def test_ad9084_clock_limits_match_rx():
    """Verify combined model clock limits reflect the RX limits."""
    dev = ad9084(solver="CPLEX")
    assert dev.converter_clock_min == ad9084_rx.converter_clock_min
    assert dev.converter_clock_max == ad9084_rx.converter_clock_max


# ── _get_converters ──────────────────────────────────────────────────────────


def test_ad9084_get_converters_returns_two():
    """Verify _get_converters returns both sub-converters."""
    dev = ad9084(solver="CPLEX")
    convs = dev._get_converters()
    assert len(convs) == 2


def test_ad9084_get_converters_contains_adc_and_dac():
    """Verify _get_converters list contains the adc and dac sub-converters."""
    dev = ad9084(solver="CPLEX")
    convs = dev._get_converters()
    assert dev.adc in convs
    assert dev.dac in convs


# ── Clock names ──────────────────────────────────────────────────────────────


def test_ad9084_clock_names_count():
    """Verify get_required_clock_names returns three names."""
    dev = ad9084(solver="CPLEX")
    names = dev.get_required_clock_names()
    assert len(names) == 3


def test_ad9084_clock_names_direct():
    """Verify clock names under direct clocking use the dac_clock prefix."""
    dev = ad9084(solver="CPLEX")
    dev.adc.clocking_option = "direct"
    names = dev.get_required_clock_names()
    assert names[0] == "ad9084_dac_clock"
    assert names[1] == "ad9084_adc_sysref"
    assert names[2] == "ad9084_dac_sysref"


def test_ad9084_clock_names_pll():
    """Verify clock names under PLL clocking use the pll_ref prefix."""
    dev = ad9084(solver="CPLEX")
    dev.adc._clocking_option = "integrated_pll"
    names = dev.get_required_clock_names()
    assert names[0] == "ad9084_pll_ref"


# ── validate_config ───────────────────────────────────────────────────────────


def test_ad9084_validate_config_delegates_to_sub_converters():
    """Verify validate_config calls through to both sub-converters.

    Confirm that an error from either sub-converter propagates out of the
    combined validate_config, proving delegation rather than a no-op.
    """
    dev = ad9084(solver="CPLEX")
    # Default TX state (mode "2", sample_clock 8 GHz) has a bit clock that
    # exceeds the JESD204C lane-rate limit, so validate_config must raise.
    with pytest.raises(Exception, match="bit clock"):
        dev.validate_config()


# ── empty quick_configuration_modes ──────────────────────────────────────────


def test_ad9084_quick_configuration_modes_empty():
    """Verify combined model has empty quick_configuration_modes."""
    dev = ad9084(solver="CPLEX")
    assert dev.quick_configuration_modes == {}


# ── Sub-converter independence ────────────────────────────────────────────────


def test_ad9084_adc_sample_clock_settable():
    """Verify the adc sub-converter sample clock can be modified."""
    dev = ad9084(solver="CPLEX")
    dev.adc.sample_clock = 1e9
    assert dev.adc.sample_clock == 1e9


def test_ad9084_dac_sample_clock_settable():
    """Verify the dac sub-converter sample clock can be modified."""
    dev = ad9084(solver="CPLEX")
    dev.dac.sample_clock = 2e9
    assert dev.dac.sample_clock == 2e9


def test_ad9084_adc_mode_change_does_not_affect_dac():
    """Verify changing the ADC JESD mode does not change the DAC mode."""
    dev = ad9084(solver="CPLEX")
    original_dac_L = dev.dac.L
    dev.adc.set_quick_configuration_mode("47", "jesd204c")
    assert dev.dac.L == original_dac_L


def test_ad9084_dac_mode_change_does_not_affect_adc():
    """Verify changing the DAC JESD mode does not change the ADC mode."""
    dev = ad9084(solver="CPLEX")
    original_adc_L = dev.adc.L
    dev.dac.set_quick_configuration_mode("2", "jesd204c")
    assert dev.adc.L == original_adc_L


# ── System factory integration ────────────────────────────────────────────────


def test_ad9084_system_has_nested_converters():
    """Verify system created with ad9084 exposes _nested on the converter."""
    sys = adijif.system(
        "ad9084", "hmc7044", "xilinx", 125000000, solver="CPLEX"
    )
    assert sys.converter._nested == ["adc", "dac"]


def test_ad9084_system_sub_converters_accessible():
    """Verify adc and dac are accessible from the converter in a system context."""
    sys = adijif.system(
        "ad9084", "hmc7044", "xilinx", 125000000, solver="CPLEX"
    )
    assert isinstance(sys.converter.adc, ad9084_rx)
    assert isinstance(sys.converter.dac, ad9084_tx)


def test_ad9084_system_full_solve():
    """Verify a system with the ad9084 converter can solve without error."""
    sys = adijif.system(
        "ad9084", "hmc7044", "xilinx", 125000000, solver="CPLEX"
    )
    sys.fpga.setup_by_dev_kit_name("vcu118")

    converter_rate = int(20e9)
    cddc_dec = 4
    fddc_dec = 2
    sys.converter.adc.sample_clock = converter_rate / (cddc_dec * fddc_dec)
    sys.converter.adc.datapath.cddc_decimations = [cddc_dec] * 4
    sys.converter.adc.datapath.fddc_decimations = [fddc_dec] * 8
    sys.converter.adc.datapath.fddc_enabled = [True] * 8
    sys.converter.adc.clocking_option = "direct"
    sys.add_pll_inline("adf4382", 125e6, sys.converter)
    # sys.add_pll_sysref("adf4030", 125e6, sys.converter, sys.fpga)

    sys.converter.dac.sample_clock = converter_rate / (cddc_dec * fddc_dec)
    sys.converter.dac.datapath.cduc_interpolation = 4
    sys.converter.dac.clocking_option = "direct"
    # sys.add_pll_inline("adf4382", 125e6, sys.converter)
    # sys.add_pll_sysref("adf4030", 125e6, sys.converter, sys.fpga)

    # JESD
    mode_rx = adijif.utils.get_jesd_mode_from_params(
        sys.converter.adc, M=4, L=8, S=1, Np=16, jesd_class="jesd204c"
    )
    assert mode_rx
    mode_rx = mode_rx[0]["mode"]
    sys.converter.adc.set_quick_configuration_mode(mode_rx, "jesd204c")
    mode_tx = adijif.utils.get_jesd_mode_from_params(
        sys.converter.dac, M=4, L=8, S=1, Np=16, jesd_class="jesd204c"
    )
    assert mode_tx
    mode_tx = mode_tx[0]["mode"]
    sys.converter.dac.set_quick_configuration_mode(mode_tx, "jesd204c")

    cfg = sys.solve()

    assert cfg is not None
