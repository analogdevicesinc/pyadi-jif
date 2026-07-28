"""Hardware validation for the 'nuc' DUT: FMCDAQ3 (AD9680 + AD9152) on vcu118.

Reads the live JESD link status + sample rates from the booted board and
asserts that pyadi-jif's AD9680/AD9152 models reproduce the measured lane
rate, and that the full vcu118 system solve closes.

Run: pytest --run-hardware tests/hardware/test_hw_nuc_fmcdaq3.py -v
"""

from __future__ import annotations

import pytest

import adijif

from .validation import available_lane_rates, match_link

pytestmark = pytest.mark.hardware

PLACE = "nuc"


@pytest.mark.parametrize("dut", [PLACE], indirect=True)
def test_fmcdaq3_jesd_links_up(dut):
    """At least one JESD link on the FMCDAQ3 is enabled and (if reported) DATA."""
    status = dut.jesd_status()
    assert status, f"no axi-jesd204 status nodes found on '{PLACE}'"
    up = {name: st for name, st in status.items() if st.up}
    assert up, f"no JESD link is up on '{PLACE}': {status}"


@pytest.mark.parametrize("dut", [PLACE], indirect=True)
def test_ad9680_model_matches_hw(dut):
    """pyadi-jif AD9680 (ADC) reproduces the measured Rx lane rate."""
    status = dut.jesd_status()
    sample_rates = list(dut.sampling_frequencies().values())
    assert sample_rates, "no IIO sampling_frequency reported by DUT"

    rx_links = [
        st for name, st in status.items() if st.up and "tx" not in name.lower()
    ]
    if not rx_links:
        pytest.skip(f"no Rx JESD link up on '{PLACE}': {list(status)}")
    lane_rate = rx_links[0].lane_rate_hz
    assert lane_rate, "Rx link reports no lane rate"

    result = match_link(adijif.ad9680, lane_rate, sample_rates)
    assert result is not None, (
        f"no AD9680 mode reproduces HW lane rate {lane_rate/1e9:.4f} GHz at "
        f"sample rates {sample_rates}; "
        f"model offers {available_lane_rates(adijif.ad9680(), sample_rates[0])}"
    )
    sr, mode = result
    assert mode.bit_clock == pytest.approx(lane_rate, rel=1e-6)


@pytest.mark.parametrize("dut", [PLACE], indirect=True)
def test_ad9152_model_matches_hw(dut):
    """pyadi-jif AD9152 (DAC) reproduces the measured Tx lane rate."""
    status = dut.jesd_status()
    sample_rates = list(dut.sampling_frequencies().values())
    assert sample_rates, "no IIO sampling_frequency reported by DUT"

    tx_links = [st for name, st in status.items() if st.up and "tx" in name.lower()]
    if not tx_links:
        pytest.skip(f"no Tx JESD link up on '{PLACE}': {list(status)}")
    lane_rate = tx_links[0].lane_rate_hz
    assert lane_rate, "Tx link reports no lane rate"

    result = match_link(adijif.ad9152, lane_rate, sample_rates)
    assert result is not None, (
        f"no AD9152 mode reproduces HW lane rate {lane_rate/1e9:.4f} GHz at "
        f"sample rates {sample_rates}"
    )
    sr, mode = result
    assert mode.bit_clock == pytest.approx(lane_rate, rel=1e-6)


@pytest.mark.parametrize("dut", [PLACE], indirect=True)
def test_fmcdaq3_system_solve_matches_hw(dut):
    """Full vcu118 FMCDAQ3 system solve closes at the measured config."""
    status = dut.jesd_status()
    sample_rates = list(dut.sampling_frequencies().values())
    rx = [st for name, st in status.items() if st.up and "tx" not in name.lower()]
    tx = [st for name, st in status.items() if st.up and "tx" in name.lower()]
    if not (rx and tx):
        pytest.skip(f"need both Rx and Tx links up on '{PLACE}'")

    adc_match = match_link(adijif.ad9680, rx[0].lane_rate_hz, sample_rates)
    dac_match = match_link(adijif.ad9152, tx[0].lane_rate_hz, sample_rates)
    assert adc_match and dac_match, "could not match both converters to HW"

    vcxo = 125000000
    sys = adijif.system(["ad9680", "ad9152"], "ad9528", "xilinx", vcxo, solver="CPLEX")
    sys.fpga.setup_by_dev_kit_name("vcu118")

    adc = sys.converter[0]
    adc.sample_clock = adc_match[0]
    adc.decimation = 1
    adc.set_quick_configuration_mode(adc_match[1].mode, adc_match[1].jesd_class)

    dac = sys.converter[1]
    dac.sample_clock = dac_match[0]
    dac.interpolation = 1
    dac.set_quick_configuration_mode(dac_match[1].mode, dac_match[1].jesd_class)

    assert adc.bit_clock == pytest.approx(rx[0].lane_rate_hz, rel=1e-6)
    assert dac.bit_clock == pytest.approx(tx[0].lane_rate_hz, rel=1e-6)

    cfg = sys.solve()
    assert "clock" in cfg and "converter" in cfg
