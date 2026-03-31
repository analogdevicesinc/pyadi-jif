"""Integration tests for AD9084 RX/TX/combined EBZ board configuration workflows.

Mirrors the two example scripts:
  - examples/ad9084_rx_ebz_profile.py     (profile-based flow)
  - examples/ad9084_rx_hmc7044_ext_pll_adf4382.py  (manual-datapath flow)

Also covers the same flows for the TX-only (ad9084_tx) and combined (ad9084)
converter models.
"""

import os

import pytest

import adijif
import adijif.utils

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILE_JSON = os.path.join(
    HERE, "apollo_profiles", "ad9084_profiles", "id00_stock_mode.json"
)

VCXO = int(125e6)

# Stock mode reference values (id00_stock_mode profile, AD9084 4T4R)
STOCK_SAMPLE_CLOCK = 2.5e9  # 20 GSPS ADC / (cddc=4 * fddc=2)
STOCK_L = 8
STOCK_M = 4
STOCK_F = 1
STOCK_NP = 16
STOCK_S = 1
# bit_clock = (M/L) * Np * (66/64) * sample_clock
STOCK_BIT_CLOCK = (
    (STOCK_M / STOCK_L) * STOCK_NP * (66 / 64) * STOCK_SAMPLE_CLOCK
)


# ── Helper ────────────────────────────────────────────────────────────────────


def _build_profile_system() -> adijif.system:
    """Build the EBZ profile system (mirrors ad9084_rx_ebz_profile.py)."""
    sys = adijif.system("ad9084_rx", "hmc7044", "xilinx", VCXO, solver="CPLEX")
    sys.converter.apply_profile_settings(PROFILE_JSON)
    sys.fpga.setup_by_dev_kit_name("vcu118")
    sys.converter.clocking_option = "direct"
    sys.add_pll_inline("adf4382", VCXO, sys.converter)
    sys.add_pll_sysref("adf4030", VCXO, sys.converter, sys.fpga)
    sys.clock.minimize_feedback_dividers = False
    return sys


def _build_manual_system() -> adijif.system:
    """Build the manual-datapath system (mirrors ad9084_rx_hmc7044_ext_pll_adf4382.py)."""
    cddc_dec = 4
    fddc_dec = 2
    converter_rate = int(20e9)

    sys = adijif.system("ad9084_rx", "hmc7044", "xilinx", VCXO, solver="CPLEX")
    sys.fpga.setup_by_dev_kit_name("vcu118")
    sys.converter.sample_clock = converter_rate / (cddc_dec * fddc_dec)
    sys.converter.datapath.cddc_decimations = [cddc_dec] * 4
    sys.converter.datapath.fddc_decimations = [fddc_dec] * 8
    sys.converter.datapath.fddc_enabled = [True] * 8
    sys.converter.clocking_option = "direct"
    sys.add_pll_inline("adf4382", VCXO, sys.converter)
    sys.add_pll_sysref("adf4030", VCXO, sys.converter, sys.fpga)
    sys.clock.minimize_feedback_dividers = False
    return sys


# ── Profile-based flow ────────────────────────────────────────────────────────


def test_ebz_profile_sets_sample_clock():
    """Verify apply_profile_settings configures the expected sample clock."""
    sys = adijif.system("ad9084_rx", "hmc7044", "xilinx", VCXO, solver="CPLEX")
    sys.converter.apply_profile_settings(PROFILE_JSON)
    assert sys.converter.sample_clock == pytest.approx(STOCK_SAMPLE_CLOCK)


def test_ebz_profile_sets_jesd_params():
    """Verify apply_profile_settings configures L, M, F, Np, S from the profile."""
    sys = adijif.system("ad9084_rx", "hmc7044", "xilinx", VCXO, solver="CPLEX")
    sys.converter.apply_profile_settings(PROFILE_JSON)
    assert sys.converter.L == STOCK_L
    assert sys.converter.M == STOCK_M
    assert sys.converter.F == STOCK_F
    assert sys.converter.Np == STOCK_NP
    assert sys.converter.S == STOCK_S


def test_ebz_profile_bit_clock():
    """Verify bit clock matches the stock JESD204C lane rate after profile load."""
    sys = adijif.system("ad9084_rx", "hmc7044", "xilinx", VCXO, solver="CPLEX")
    sys.converter.apply_profile_settings(PROFILE_JSON)
    assert sys.converter.bit_clock == pytest.approx(STOCK_BIT_CLOCK)


def test_ebz_profile_bit_clock_gbps():
    """Verify lane rate is approximately 20.625 Gbps (stock AD9084 mode)."""
    sys = adijif.system("ad9084_rx", "hmc7044", "xilinx", VCXO, solver="CPLEX")
    sys.converter.apply_profile_settings(PROFILE_JSON)
    assert sys.converter.bit_clock / 1e9 == pytest.approx(20.625)


def test_ebz_profile_core_clock():
    """Verify derived core clock (bit_clock/66) is ~312.5 MHz for 204C."""
    sys = adijif.system("ad9084_rx", "hmc7044", "xilinx", VCXO, solver="CPLEX")
    sys.converter.apply_profile_settings(PROFILE_JSON)
    core_clock_mhz = sys.converter.bit_clock / 66 / 1e6
    assert core_clock_mhz == pytest.approx(312.5)


def test_ebz_profile_clock_relations():
    """Verify JESD clock relations are internally consistent after profile load."""
    sys = adijif.system("ad9084_rx", "hmc7044", "xilinx", VCXO, solver="CPLEX")
    sys.converter.apply_profile_settings(PROFILE_JSON)
    sys.converter._check_clock_relations()  # must not raise


def test_ebz_profile_clocking_option_direct():
    """Verify clocking option can be set to direct after profile load."""
    sys = adijif.system("ad9084_rx", "hmc7044", "xilinx", VCXO, solver="CPLEX")
    sys.converter.apply_profile_settings(PROFILE_JSON)
    sys.converter.clocking_option = "direct"
    assert sys.converter.clocking_option == "direct"


def test_ebz_profile_solve_returns_config():
    """Verify full EBZ profile workflow produces a valid solver configuration."""
    sys = _build_profile_system()
    cfg = sys.solve()
    assert cfg is not None


def test_ebz_profile_solve_clock_config_present():
    """Verify solver result contains a clock sub-config."""
    sys = _build_profile_system()
    cfg = sys.solve()
    assert "clock" in cfg


def test_ebz_profile_solve_converter_config_present():
    """Verify solver result contains a converter sub-config."""
    sys = _build_profile_system()
    cfg = sys.solve()
    assert "converter" in cfg or "converters" in cfg


# ── Manual-datapath flow ──────────────────────────────────────────────────────


def test_manual_sample_clock():
    """Verify sample_clock is set correctly from converter_rate and decimations."""
    sys = _build_manual_system()
    assert sys.converter.sample_clock == pytest.approx(STOCK_SAMPLE_CLOCK)


def test_manual_datapath_cddc():
    """Verify CDDC decimations are applied to all four channels."""
    sys = _build_manual_system()
    assert sys.converter.datapath.cddc_decimations == [4, 4, 4, 4]


def test_manual_datapath_fddc():
    """Verify FDDC decimations are applied to all eight channels."""
    sys = _build_manual_system()
    assert sys.converter.datapath.fddc_decimations == [2, 2, 2, 2, 2, 2, 2, 2]


def test_manual_datapath_fddc_enabled():
    """Verify all eight FDDC channels are enabled."""
    sys = _build_manual_system()
    assert sys.converter.datapath.fddc_enabled == [True] * 8


def test_manual_get_jesd_mode_from_params_finds_mode():
    """Verify get_jesd_mode_from_params returns at least one match for M=4 L=8."""
    sys = _build_manual_system()
    modes = adijif.utils.get_jesd_mode_from_params(
        sys.converter, M=4, L=8, S=1, Np=16, jesd_class="jesd204c"
    )
    assert modes, "Expected at least one matching JESD mode"


def test_manual_get_jesd_mode_from_params_mode_number():
    """Verify the matched mode is the stock AD9084 RX mode (47)."""
    sys = _build_manual_system()
    modes = adijif.utils.get_jesd_mode_from_params(
        sys.converter, M=4, L=8, S=1, Np=16, jesd_class="jesd204c"
    )
    assert any(m["mode"] == "47" for m in modes)


def test_manual_set_mode_configures_jesd_params():
    """Verify set_quick_configuration_mode applies expected JESD parameters."""
    sys = _build_manual_system()
    modes = adijif.utils.get_jesd_mode_from_params(
        sys.converter, M=4, L=8, S=1, Np=16, jesd_class="jesd204c"
    )
    mode_key = modes[0]["mode"]
    sys.converter.set_quick_configuration_mode(mode_key, "jesd204c")
    assert sys.converter.L == STOCK_L
    assert sys.converter.M == STOCK_M
    assert sys.converter.Np == STOCK_NP
    assert sys.converter.S == STOCK_S
    assert sys.converter.jesd_class == "jesd204c"


def test_manual_bit_clock_after_mode_set():
    """Verify lane rate after manual mode selection matches the stock value."""
    sys = _build_manual_system()
    modes = adijif.utils.get_jesd_mode_from_params(
        sys.converter, M=4, L=8, S=1, Np=16, jesd_class="jesd204c"
    )
    sys.converter.set_quick_configuration_mode(modes[0]["mode"], "jesd204c")
    assert sys.converter.bit_clock == pytest.approx(STOCK_BIT_CLOCK)


def test_manual_clock_relations():
    """Verify JESD clock relations are consistent after manual configuration."""
    sys = _build_manual_system()
    modes = adijif.utils.get_jesd_mode_from_params(
        sys.converter, M=4, L=8, S=1, Np=16, jesd_class="jesd204c"
    )
    sys.converter.set_quick_configuration_mode(modes[0]["mode"], "jesd204c")
    sys.converter._check_clock_relations()  # must not raise


def test_manual_solve_returns_config():
    """Verify full manual-datapath workflow produces a valid solver configuration."""
    sys = _build_manual_system()
    modes = adijif.utils.get_jesd_mode_from_params(
        sys.converter, M=4, L=8, S=1, Np=16, jesd_class="jesd204c"
    )
    sys.converter.set_quick_configuration_mode(modes[0]["mode"], "jesd204c")
    cfg = sys.solve()
    assert cfg is not None


# ── Make-command generation ───────────────────────────────────────────────────


def _make_command(conv: adijif.ad9084_rx) -> str:
    """Generate the HDL make command from a solved converter (mirrors example script)."""
    mode = "64B66B" if conv.jesd_class == "jesd204c" else "8B10B"
    rate = conv.bit_clock / 1e9
    return (
        f"JESD_MODE={mode} "
        f"RX_RATE={rate:.4f} TX_RATE={rate:.4f} "
        f"RX_JESD_M={conv.M} TX_JESD_M={conv.M} "
        f"RX_JESD_L={conv.L} TX_JESD_L={conv.L} "
        f"RX_JESD_S={conv.S} TX_JESD_S={conv.S} "
        f"RX_JESD_NP={conv.Np} TX_JESD_NP={conv.Np} "
        f"RX_B_RATE={rate:.4f} TX_B_RATE={rate:.4f} "
        f"RX_B_JESD_M={conv.M} TX_B_JESD_M={conv.M} "
        f"RX_B_JESD_L={conv.L} TX_B_JESD_L={conv.L} "
        f"RX_B_JESD_S={conv.S} TX_B_JESD_S={conv.S} "
        f"RX_B_JESD_NP={conv.Np} TX_B_JESD_NP={conv.Np}"
    )


def test_make_command_jesd_mode_204c():
    """Verify make command uses 64B66B encoding label for jesd204c."""
    sys = adijif.system("ad9084_rx", "hmc7044", "xilinx", VCXO, solver="CPLEX")
    sys.converter.apply_profile_settings(PROFILE_JSON)
    cmd = _make_command(sys.converter)
    assert "JESD_MODE=64B66B" in cmd


def test_make_command_rate():
    """Verify make command lane rate matches the stock bit clock."""
    sys = adijif.system("ad9084_rx", "hmc7044", "xilinx", VCXO, solver="CPLEX")
    sys.converter.apply_profile_settings(PROFILE_JSON)
    cmd = _make_command(sys.converter)
    assert "RX_RATE=20.6250" in cmd


def test_make_command_jesd_params():
    """Verify make command contains correct M, L, S, Np values."""
    sys = adijif.system("ad9084_rx", "hmc7044", "xilinx", VCXO, solver="CPLEX")
    sys.converter.apply_profile_settings(PROFILE_JSON)
    cmd = _make_command(sys.converter)
    assert f"RX_JESD_M={STOCK_M}" in cmd
    assert f"RX_JESD_L={STOCK_L}" in cmd
    assert f"RX_JESD_S={STOCK_S}" in cmd
    assert f"RX_JESD_NP={STOCK_NP}" in cmd


def test_make_command_b_rate_matches_rate():
    """Verify RX_B_RATE equals RX_RATE in the make command."""
    sys = adijif.system("ad9084_rx", "hmc7044", "xilinx", VCXO, solver="CPLEX")
    sys.converter.apply_profile_settings(PROFILE_JSON)
    cmd = _make_command(sys.converter)
    # Both RX_RATE and RX_B_RATE should appear with the same value
    assert "RX_B_RATE=20.6250" in cmd


# ── AD9084 TX — profile-based flow ───────────────────────────────────────────


def test_tx_profile_sets_sample_clock():
    """Verify apply_profile_settings sets the correct TX sample clock."""
    sys = adijif.system("ad9084_tx", "hmc7044", "xilinx", VCXO, solver="CPLEX")
    sys.converter.apply_profile_settings(PROFILE_JSON)
    assert sys.converter.sample_clock == pytest.approx(STOCK_SAMPLE_CLOCK)


def test_tx_profile_sets_jesd_params():
    """Verify apply_profile_settings configures TX JESD params from the profile."""
    sys = adijif.system("ad9084_tx", "hmc7044", "xilinx", VCXO, solver="CPLEX")
    sys.converter.apply_profile_settings(PROFILE_JSON)
    assert sys.converter.L == STOCK_L
    assert sys.converter.M == STOCK_M
    assert sys.converter.F == STOCK_F
    assert sys.converter.Np == STOCK_NP
    assert sys.converter.S == STOCK_S


def test_tx_profile_bit_clock():
    """Verify TX bit clock matches the stock lane rate after profile load."""
    sys = adijif.system("ad9084_tx", "hmc7044", "xilinx", VCXO, solver="CPLEX")
    sys.converter.apply_profile_settings(PROFILE_JSON)
    assert sys.converter.bit_clock == pytest.approx(STOCK_BIT_CLOCK)


def test_tx_profile_interpolation():
    """Verify TX interpolation equals cduc * fduc from the stock profile."""
    sys = adijif.system("ad9084_tx", "hmc7044", "xilinx", VCXO, solver="CPLEX")
    sys.converter.apply_profile_settings(PROFILE_JSON)
    # id00_stock_mode: cduc_interpolation=4, fduc_interpolation=2 → overall=8
    assert sys.converter.interpolation == 4 * 2


def test_tx_profile_clock_relations():
    """Verify JESD clock relations are consistent after TX profile load."""
    sys = adijif.system("ad9084_tx", "hmc7044", "xilinx", VCXO, solver="CPLEX")
    sys.converter.apply_profile_settings(PROFILE_JSON)
    sys.converter._check_clock_relations()  # must not raise


# ── AD9084 TX — manual-datapath flow ─────────────────────────────────────────


def _build_manual_tx_system() -> adijif.system:
    """Build the manual TX system (analog to the manual RX system)."""
    cduc_interp = 4
    fduc_interp = 2
    converter_rate = int(20e9)

    sys = adijif.system("ad9084_tx", "hmc7044", "xilinx", VCXO, solver="CPLEX")
    sys.fpga.setup_by_dev_kit_name("vcu118")
    sys.converter.sample_clock = converter_rate / (cduc_interp * fduc_interp)
    sys.converter.datapath.cduc_interpolation = cduc_interp
    sys.converter.datapath.fduc_interpolation = fduc_interp
    sys.converter.datapath.fduc_enabled = [True] * 8
    sys.converter.clocking_option = "direct"
    sys.add_pll_inline("adf4382", VCXO, sys.converter)
    sys.add_pll_sysref("adf4030", VCXO, sys.converter, sys.fpga)
    sys.clock.minimize_feedback_dividers = False
    return sys


def test_manual_tx_sample_clock():
    """Verify TX sample_clock is set correctly from converter_rate and interpolation."""
    sys = _build_manual_tx_system()
    assert sys.converter.sample_clock == pytest.approx(STOCK_SAMPLE_CLOCK)


def test_manual_tx_interpolation():
    """Verify TX interpolation reflects cduc * fduc settings."""
    sys = _build_manual_tx_system()
    assert sys.converter.interpolation == 4 * 2


def test_manual_tx_datapath_cduc():
    """Verify CDUC interpolation is applied."""
    sys = _build_manual_tx_system()
    assert sys.converter.datapath.cduc_interpolation == 4


def test_manual_tx_datapath_fduc():
    """Verify FDUC interpolation is applied."""
    sys = _build_manual_tx_system()
    assert sys.converter.datapath.fduc_interpolation == 2


def test_manual_tx_get_jesd_mode_finds_mode_47():
    """Verify get_jesd_mode_from_params finds mode 47 for the stock TX config."""
    sys = _build_manual_tx_system()
    modes = adijif.utils.get_jesd_mode_from_params(
        sys.converter, M=4, L=8, S=1, Np=16, jesd_class="jesd204c"
    )
    assert any(m["mode"] == "47" for m in modes)


def test_manual_tx_set_mode_configures_jesd_params():
    """Verify set_quick_configuration_mode applies expected TX JESD parameters."""
    sys = _build_manual_tx_system()
    modes = adijif.utils.get_jesd_mode_from_params(
        sys.converter, M=4, L=8, S=1, Np=16, jesd_class="jesd204c"
    )
    sys.converter.set_quick_configuration_mode(modes[0]["mode"], "jesd204c")
    assert sys.converter.L == STOCK_L
    assert sys.converter.M == STOCK_M
    assert sys.converter.Np == STOCK_NP
    assert sys.converter.jesd_class == "jesd204c"


def test_manual_tx_bit_clock():
    """Verify TX lane rate after manual mode selection matches the stock value."""
    sys = _build_manual_tx_system()
    modes = adijif.utils.get_jesd_mode_from_params(
        sys.converter, M=4, L=8, S=1, Np=16, jesd_class="jesd204c"
    )
    sys.converter.set_quick_configuration_mode(modes[0]["mode"], "jesd204c")
    assert sys.converter.bit_clock == pytest.approx(STOCK_BIT_CLOCK)


def test_manual_tx_clock_relations():
    """Verify JESD clock relations are consistent after manual TX configuration."""
    sys = _build_manual_tx_system()
    modes = adijif.utils.get_jesd_mode_from_params(
        sys.converter, M=4, L=8, S=1, Np=16, jesd_class="jesd204c"
    )
    sys.converter.set_quick_configuration_mode(modes[0]["mode"], "jesd204c")
    sys.converter._check_clock_relations()  # must not raise


def test_manual_tx_solve_returns_config():
    """Verify full manual TX workflow produces a valid solver configuration."""
    sys = _build_manual_tx_system()
    modes = adijif.utils.get_jesd_mode_from_params(
        sys.converter, M=4, L=8, S=1, Np=16, jesd_class="jesd204c"
    )
    sys.converter.set_quick_configuration_mode(modes[0]["mode"], "jesd204c")
    cfg = sys.solve()
    assert cfg is not None


# ── AD9084 combined — profile-based flow ─────────────────────────────────────


def _build_profile_combined_system() -> adijif.system:
    """Build the combined EBZ profile system."""
    sys = adijif.system("ad9084", "hmc7044", "xilinx", VCXO, solver="CPLEX")
    sys.converter.apply_profile_settings(PROFILE_JSON)
    sys.fpga.setup_by_dev_kit_name("vcu118")
    sys.converter.clocking_option = "direct"
    sys.add_pll_inline("adf4382", VCXO, sys.converter)
    sys.add_pll_sysref("adf4030", VCXO, sys.converter, sys.fpga)
    sys.clock.minimize_feedback_dividers = False
    return sys


def test_combined_profile_sets_adc_sample_clock():
    """Verify apply_profile_settings sets the correct RX sample clock on adc."""
    sys = adijif.system("ad9084", "hmc7044", "xilinx", VCXO, solver="CPLEX")
    sys.converter.apply_profile_settings(PROFILE_JSON)
    assert sys.converter.adc.sample_clock == pytest.approx(STOCK_SAMPLE_CLOCK)


def test_combined_profile_sets_dac_sample_clock():
    """Verify apply_profile_settings sets the correct TX sample clock on dac."""
    sys = adijif.system("ad9084", "hmc7044", "xilinx", VCXO, solver="CPLEX")
    sys.converter.apply_profile_settings(PROFILE_JSON)
    assert sys.converter.dac.sample_clock == pytest.approx(STOCK_SAMPLE_CLOCK)


def test_combined_profile_adc_jesd_params():
    """Verify apply_profile_settings configures adc JESD params from the profile."""
    sys = adijif.system("ad9084", "hmc7044", "xilinx", VCXO, solver="CPLEX")
    sys.converter.apply_profile_settings(PROFILE_JSON)
    assert sys.converter.adc.L == STOCK_L
    assert sys.converter.adc.M == STOCK_M
    assert sys.converter.adc.Np == STOCK_NP


def test_combined_profile_dac_jesd_params():
    """Verify apply_profile_settings configures dac JESD params from the profile."""
    sys = adijif.system("ad9084", "hmc7044", "xilinx", VCXO, solver="CPLEX")
    sys.converter.apply_profile_settings(PROFILE_JSON)
    assert sys.converter.dac.L == STOCK_L
    assert sys.converter.dac.M == STOCK_M
    assert sys.converter.dac.Np == STOCK_NP


def test_combined_profile_adc_bit_clock():
    """Verify ADC bit clock matches the stock lane rate after combined profile load."""
    sys = adijif.system("ad9084", "hmc7044", "xilinx", VCXO, solver="CPLEX")
    sys.converter.apply_profile_settings(PROFILE_JSON)
    assert sys.converter.adc.bit_clock == pytest.approx(STOCK_BIT_CLOCK)


def test_combined_profile_dac_bit_clock():
    """Verify DAC bit clock matches the stock lane rate after combined profile load."""
    sys = adijif.system("ad9084", "hmc7044", "xilinx", VCXO, solver="CPLEX")
    sys.converter.apply_profile_settings(PROFILE_JSON)
    assert sys.converter.dac.bit_clock == pytest.approx(STOCK_BIT_CLOCK)


def test_combined_profile_clock_names():
    """Verify combined clock names reference the DAC clock and separate sysfefs."""
    sys = adijif.system("ad9084", "hmc7044", "xilinx", VCXO, solver="CPLEX")
    sys.converter.clocking_option = "direct"
    names = sys.converter.get_required_clock_names()
    assert names[0] == "ad9084_dac_clock"
    assert "ad9084_adc_sysref" in names
    assert "ad9084_dac_sysref" in names


def test_combined_profile_solve_returns_config():
    """Verify full combined profile workflow produces a valid solver configuration."""
    sys = _build_profile_combined_system()
    cfg = sys.solve()
    assert cfg is not None


# ── AD9084 combined — manual flow ────────────────────────────────────────────


def _build_manual_combined_system() -> adijif.system:
    """Build the manual combined system configuring both adc and dac."""
    cddc_dec = 4
    fddc_dec = 2
    cduc_interp = 4
    fduc_interp = 2
    converter_rate = int(20e9)

    sys = adijif.system("ad9084", "hmc7044", "xilinx", VCXO, solver="CPLEX")
    sys.fpga.setup_by_dev_kit_name("vcu118")

    # ADC sub-converter
    sys.converter.adc.sample_clock = converter_rate / (cddc_dec * fddc_dec)
    sys.converter.adc.datapath.cddc_decimations = [cddc_dec] * 4
    sys.converter.adc.datapath.fddc_decimations = [fddc_dec] * 8
    sys.converter.adc.datapath.fddc_enabled = [True] * 8

    # DAC sub-converter
    sys.converter.dac.sample_clock = converter_rate / (
        cduc_interp * fduc_interp
    )
    sys.converter.dac.datapath.cduc_interpolation = cduc_interp
    sys.converter.dac.datapath.fduc_interpolation = fduc_interp
    sys.converter.dac.datapath.fduc_enabled = [True] * 8

    sys.converter.clocking_option = "direct"
    sys.add_pll_inline("adf4382", VCXO, sys.converter)
    sys.add_pll_sysref("adf4030", VCXO, sys.converter, sys.fpga)
    sys.clock.minimize_feedback_dividers = False
    return sys


def test_manual_combined_adc_sample_clock():
    """Verify combined model's adc sample clock is set correctly."""
    sys = _build_manual_combined_system()
    assert sys.converter.adc.sample_clock == pytest.approx(STOCK_SAMPLE_CLOCK)


def test_manual_combined_dac_sample_clock():
    """Verify combined model's dac sample clock is set correctly."""
    sys = _build_manual_combined_system()
    assert sys.converter.dac.sample_clock == pytest.approx(STOCK_SAMPLE_CLOCK)


def test_manual_combined_dac_interpolation():
    """Verify combined model's dac interpolation reflects cduc * fduc."""
    sys = _build_manual_combined_system()
    assert sys.converter.dac.interpolation == 4 * 2


def test_manual_combined_set_modes():
    """Verify JESD modes can be set on both sub-converters."""
    sys = _build_manual_combined_system()
    rx_modes = adijif.utils.get_jesd_mode_from_params(
        sys.converter.adc, M=4, L=8, S=1, Np=16, jesd_class="jesd204c"
    )
    tx_modes = adijif.utils.get_jesd_mode_from_params(
        sys.converter.dac, M=4, L=8, S=1, Np=16, jesd_class="jesd204c"
    )
    sys.converter.adc.set_quick_configuration_mode(
        rx_modes[0]["mode"], "jesd204c"
    )
    sys.converter.dac.set_quick_configuration_mode(
        tx_modes[0]["mode"], "jesd204c"
    )
    assert sys.converter.adc.L == STOCK_L
    assert sys.converter.dac.L == STOCK_L


def test_manual_combined_solve_returns_config():
    """Verify full manual combined workflow produces a valid solver configuration."""
    sys = _build_manual_combined_system()
    rx_modes = adijif.utils.get_jesd_mode_from_params(
        sys.converter.adc, M=4, L=8, S=1, Np=16, jesd_class="jesd204c"
    )
    tx_modes = adijif.utils.get_jesd_mode_from_params(
        sys.converter.dac, M=4, L=8, S=1, Np=16, jesd_class="jesd204c"
    )
    sys.converter.adc.set_quick_configuration_mode(
        rx_modes[0]["mode"], "jesd204c"
    )
    sys.converter.dac.set_quick_configuration_mode(
        tx_modes[0]["mode"], "jesd204c"
    )
    cfg = sys.solve()
    assert cfg is not None
