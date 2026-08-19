"""Hardware validation for the 'nemo' DUT: ADRV9009 on zc706.

Reads the live JESD link status + sample rates from the booted board and
asserts that pyadi-jif's ADRV9009 model reproduces the measured lane rate(s),
and that the full zc706 system solve closes.

Run: pytest --run-hardware tests/hardware/test_hw_nemo_adrv9009.py -v
"""

from __future__ import annotations

import pytest

import adijif

from .validation import available_lane_rates, match_link

pytestmark = pytest.mark.hardware

PLACE = "nemo"


@pytest.mark.parametrize("dut", [PLACE], indirect=True)
def test_adrv9009_jesd_links_up(dut):
    """At least one ADRV9009 JESD link is enabled and (if reported) in DATA."""
    status = dut.jesd_status()
    assert status, f"no axi-jesd204 status nodes found on '{PLACE}'"
    up = {name: st for name, st in status.items() if st.up}
    assert up, f"no JESD link is up on '{PLACE}': {status}"


@pytest.mark.parametrize("dut", [PLACE], indirect=True)
def test_adrv9009_rx_model_matches_hw(dut):
    """pyadi-jif ADRV9009 Rx reproduces the measured Rx lane rate."""
    status = dut.jesd_status()
    sample_rates = list(dut.sampling_frequencies().values())
    assert sample_rates, "no IIO sampling_frequency reported by DUT"

    rx = [st for name, st in status.items() if st.up and "tx" not in name.lower()]
    if not rx:
        pytest.skip(f"no Rx JESD link up on '{PLACE}': {list(status)}")
    lane_rate = rx[0].lane_rate_hz
    assert lane_rate, "Rx link reports no lane rate"

    result = match_link(adijif.adrv9009_rx, lane_rate, sample_rates)
    assert result is not None, (
        f"no ADRV9009 Rx mode reproduces HW lane rate {lane_rate/1e9:.4f} GHz "
        f"at sample rates {sample_rates}; model offers "
        f"{available_lane_rates(adijif.adrv9009_rx(), sample_rates[0])}"
    )
    assert result[1].bit_clock == pytest.approx(lane_rate, rel=1e-6)


@pytest.mark.parametrize("dut", [PLACE], indirect=True)
def test_adrv9009_tx_model_matches_hw(dut):
    """pyadi-jif ADRV9009 Tx reproduces the measured Tx lane rate."""
    status = dut.jesd_status()
    sample_rates = list(dut.sampling_frequencies().values())
    assert sample_rates, "no IIO sampling_frequency reported by DUT"

    tx = [st for name, st in status.items() if st.up and "tx" in name.lower()]
    if not tx:
        pytest.skip(f"no Tx JESD link up on '{PLACE}': {list(status)}")
    lane_rate = tx[0].lane_rate_hz
    assert lane_rate, "Tx link reports no lane rate"

    result = match_link(adijif.adrv9009_tx, lane_rate, sample_rates)
    assert result is not None, (
        f"no ADRV9009 Tx mode reproduces HW lane rate {lane_rate/1e9:.4f} GHz "
        f"at sample rates {sample_rates}"
    )
    assert result[1].bit_clock == pytest.approx(lane_rate, rel=1e-6)


@pytest.mark.parametrize("dut", [PLACE], indirect=True)
def test_adrv9009_system_solve_matches_hw(dut):
    """Full zc706 ADRV9009 system solve closes at the measured config."""
    status = dut.jesd_status()
    sample_rates = list(dut.sampling_frequencies().values())
    rx = [st for name, st in status.items() if st.up and "tx" not in name.lower()]
    tx = [st for name, st in status.items() if st.up and "tx" in name.lower()]
    if not (rx and tx):
        pytest.skip(f"need both Rx and Tx links up on '{PLACE}'")

    rx_match = match_link(adijif.adrv9009_rx, rx[0].lane_rate_hz, sample_rates)
    tx_match = match_link(adijif.adrv9009_tx, tx[0].lane_rate_hz, sample_rates)
    assert rx_match and tx_match, "could not match both Rx and Tx to HW"

    vcxo = 122.88e6
    sys = adijif.system("adrv9009", "ad9528", "xilinx", vcxo, solver="CPLEX")
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.clock.d = [*range(1, 257)]

    sys.converter.adc.sample_clock = rx_match[0]
    sys.converter.adc.decimation = 4
    sys.converter.adc.set_quick_configuration_mode(
        rx_match[1].mode, rx_match[1].jesd_class
    )
    sys.converter.dac.sample_clock = tx_match[0]
    sys.converter.dac.interpolation = 4
    sys.converter.dac.set_quick_configuration_mode(
        tx_match[1].mode, tx_match[1].jesd_class
    )

    assert sys.converter.adc.bit_clock == pytest.approx(rx[0].lane_rate_hz, rel=1e-6)
    assert sys.converter.dac.bit_clock == pytest.approx(tx[0].lane_rate_hz, rel=1e-6)

    cfg = sys.solve()
    assert "clock" in cfg and "converter" in cfg
