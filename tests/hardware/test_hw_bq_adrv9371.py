"""Hardware validation for the 'bq' DUT: ADRV9371 (AD9371) on zc706.

Reads the live JESD link status + sample rates from the booted board and
asserts that the newly added pyadi-jif ADRV9371 model reproduces the measured
lane rate(s), and that the full zc706 system solve closes.

Run: pytest --run-hardware tests/hardware/test_hw_bq_adrv9371.py -v
"""

from __future__ import annotations

import pytest

import adijif

from .validation import available_lane_rates, match_link

pytestmark = pytest.mark.hardware

PLACE = "bq"


@pytest.mark.parametrize("dut", [PLACE], indirect=True)
def test_adrv9371_jesd_links_up(dut):
    """At least one ADRV9371 JESD link is enabled and (if reported) in DATA."""
    status = dut.jesd_status()
    assert status, f"no axi-jesd204 status nodes found on '{PLACE}'"
    up = {name: st for name, st in status.items() if st.up}
    assert up, f"no JESD link is up on '{PLACE}': {status}"


@pytest.mark.parametrize("dut", [PLACE], indirect=True)
def test_adrv9371_rx_model_matches_hw(dut):
    """pyadi-jif ADRV9371 Rx reproduces the measured Rx lane rate."""
    status = dut.jesd_status()
    sample_rates = list(dut.sampling_frequencies().values())
    assert sample_rates, "no IIO sampling_frequency reported by DUT"

    rx = [
        st for name, st in status.items() if st.up and "tx" not in name.lower()
    ]
    if not rx:
        pytest.skip(f"no Rx JESD link up on '{PLACE}': {list(status)}")
    lane_rate = rx[0].lane_rate_hz
    assert lane_rate, "Rx link reports no lane rate"

    result = match_link(adijif.adrv9371_rx, lane_rate, sample_rates)
    assert result is not None, (
        f"no ADRV9371 Rx mode reproduces HW lane rate {lane_rate / 1e9:.4f} GHz "
        f"at sample rates {sample_rates}; model offers "
        f"{available_lane_rates(adijif.adrv9371_rx(), sample_rates[0])}"
    )
    assert result[1].bit_clock == pytest.approx(lane_rate, rel=1e-6)


@pytest.mark.parametrize("dut", [PLACE], indirect=True)
def test_adrv9371_tx_model_matches_hw(dut):
    """pyadi-jif ADRV9371 Tx reproduces the measured Tx lane rate."""
    status = dut.jesd_status()
    sample_rates = list(dut.sampling_frequencies().values())
    assert sample_rates, "no IIO sampling_frequency reported by DUT"

    tx = [st for name, st in status.items() if st.up and "tx" in name.lower()]
    if not tx:
        pytest.skip(f"no Tx JESD link up on '{PLACE}': {list(status)}")
    lane_rate = tx[0].lane_rate_hz
    assert lane_rate, "Tx link reports no lane rate"

    result = match_link(adijif.adrv9371_tx, lane_rate, sample_rates)
    assert result is not None, (
        f"no ADRV9371 Tx mode reproduces HW lane rate {lane_rate / 1e9:.4f} GHz "
        f"at sample rates {sample_rates}"
    )
    assert result[1].bit_clock == pytest.approx(lane_rate, rel=1e-6)


@pytest.mark.parametrize("dut", [PLACE], indirect=True)
def test_adrv9371_system_solve_matches_hw(dut):
    """Full zc706 ADRV9371 system solve closes at the measured config."""
    status = dut.jesd_status()
    sample_rates = list(dut.sampling_frequencies().values())
    rx = [
        st for name, st in status.items() if st.up and "tx" not in name.lower()
    ]
    tx = [st for name, st in status.items() if st.up and "tx" in name.lower()]
    if not (rx and tx):
        pytest.skip(f"need both Rx and Tx links up on '{PLACE}'")

    rx_match = match_link(adijif.adrv9371_rx, rx[0].lane_rate_hz, sample_rates)
    tx_match = match_link(adijif.adrv9371_tx, tx[0].lane_rate_hz, sample_rates)
    assert rx_match and tx_match, "could not match both Rx and Tx to HW"

    vcxo = 122.88e6
    sys = adijif.system("adrv9371", "ad9528", "xilinx", vcxo, solver="CPLEX")
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

    assert sys.converter.adc.bit_clock == pytest.approx(
        rx[0].lane_rate_hz, rel=1e-6
    )
    assert sys.converter.dac.bit_clock == pytest.approx(
        tx[0].lane_rate_hz, rel=1e-6
    )

    cfg = sys.solve()
    assert "clock" in cfg and "converter" in cfg


@pytest.mark.parametrize("dut", [PLACE], indirect=True)
def test_adrv9371_tx_framing_is_m4(dut):
    """Booted Tx framing is M=4 (two complex I/Q channels) and the model has it.

    A lane rate fixes only F (and the M/L ratio), not M and L independently, so
    the lane-rate match tests above cannot tell M=4/L=4 from M=2/L=2. This reads
    the authoritative ``converters-per-device`` from the device tree the board
    booted with and asserts the pyadi-jif ADRV9371 Tx model offers that framing.
    """
    framing = dut.jesd_framing()
    assert framing, f"no axi-jesd204 framing found in '{PLACE}' device tree"
    tx = next(
        (f for f in framing.values() if f.get("role") == "tx" and "M" in f),
        None,
    )
    if tx is None:
        pytest.skip(
            f"no Tx framing with converters-per-device in DT: {framing}"
        )

    assert tx["M"] == 4, f"expected Tx M=4 (two complex channels), got {tx}"
    modes = adijif.utils.get_jesd_mode_from_params(
        adijif.adrv9371_tx(), M=tx["M"], F=tx["F"], Np=tx.get("Np", 16)
    )
    assert modes, (
        f"jif adrv9371_tx offers no mode for HW framing "
        f"M={tx['M']} F={tx['F']} Np={tx.get('Np', 16)}"
    )
