"""Hardware validation for the 'mini2' DUT: AD9081 on zcu102.

Reads the live JESD link status from the booted board, asserts the
pyadi-jif AD9081 models reproduce the measured lane rates, and — the
xcvr-wizard-specific part — asserts the ``adi.xgt-wizard`` export of a
solve matching the measured configuration would drive the Xilinx GT
wizard to exactly what the working hardware runs (lane rates, JESD
encoding, lane counts).

Run: pytest --run-hardware tests/hardware/test_hw_mini2_ad9081.py -v
"""

from __future__ import annotations

import pytest

import adijif

from .validation import available_lane_rates, match_link

pytestmark = pytest.mark.hardware

PLACE = "mini2"
VCXO = 122.88e6  # mini2 rig hdl-config m8_l4_vcxo122p88 (HMC7044)


def _links(status, direction):
    """Return the up links for one direction ('rx' or 'tx')."""
    if direction == "tx":
        return [
            st for name, st in status.items() if st.up and "tx" in name.lower()
        ]
    return [
        st
        for name, st in status.items()
        if st.up and "tx" not in name.lower()
    ]


@pytest.mark.parametrize("dut", [PLACE], indirect=True)
def test_ad9081_jesd_links_up(dut):
    """At least one AD9081 JESD link is enabled and (if reported) in DATA."""
    status = dut.jesd_status()
    assert status, f"no axi-jesd204 status nodes found on '{PLACE}'"
    up = {name: st for name, st in status.items() if st.up}
    assert up, f"no JESD link is up on '{PLACE}': {status}"


@pytest.mark.parametrize("dut", [PLACE], indirect=True)
@pytest.mark.parametrize("direction", ["rx", "tx"])
def test_ad9081_model_matches_hw(dut, direction):
    """pyadi-jif AD9081 reproduces the measured lane rate per direction."""
    status = dut.jesd_status()
    sample_rates = list(dut.sampling_frequencies().values())
    assert sample_rates, "no IIO sampling_frequency reported by DUT"

    links = _links(status, direction)
    if not links:
        pytest.skip(f"no {direction} JESD link up on '{PLACE}'")
    lane_rate = links[0].lane_rate_hz
    assert lane_rate, f"{direction} link reports no lane rate"

    factory = adijif.ad9081_rx if direction == "rx" else adijif.ad9081_tx
    result = match_link(factory, lane_rate, sample_rates)
    assert result is not None, (
        f"no AD9081 {direction} mode reproduces HW lane rate "
        f"{lane_rate / 1e9:.4f} GHz at sample rates {sample_rates}; "
        f"model offers {available_lane_rates(factory(), sample_rates[0])}"
    )
    assert result[1].bit_clock == pytest.approx(lane_rate, rel=1e-6)


@pytest.mark.parametrize("dut", [PLACE], indirect=True)
def test_ad9081_xgt_wizard_export_matches_hw(dut):
    """The adi.xgt-wizard export agrees with the running hardware.

    Matches each measured link to an AD9081 quick-config mode, solves the
    full zcu102 system at those modes, exports the xgt_wizard parameters,
    and asserts the exported lane rates, JESD mode, and lane counts equal
    what the board reports.
    """
    status = dut.jesd_status()
    sample_rates = list(dut.sampling_frequencies().values())
    assert sample_rates, "no IIO sampling_frequency reported by DUT"

    rx_links = _links(status, "rx")
    tx_links = _links(status, "tx")
    if not rx_links or not tx_links:
        pytest.skip(f"need both rx and tx links up on '{PLACE}': {status}")
    rx_rate = rx_links[0].lane_rate_hz
    tx_rate = tx_links[0].lane_rate_hz
    assert rx_rate and tx_rate, "links report no lane rate"

    rx_match = match_link(adijif.ad9081_rx, rx_rate, sample_rates)
    tx_match = match_link(adijif.ad9081_tx, tx_rate, sample_rates)
    assert rx_match and tx_match, (
        f"no AD9081 mode reproduces measured rates rx={rx_rate} tx={tx_rate}"
    )
    (rx_sample, rx_mode), (tx_sample, tx_mode) = rx_match, tx_match

    sys = adijif.system(
        "ad9081", "hmc7044", "xilinx", VCXO, solver="CPLEX"
    )
    sys.fpga.setup_by_dev_kit_name("zcu102")
    sys.fpga.ref_clock_constraint = "Unconstrained"
    sys.converter.clocking_option = "integrated_pll"
    sys.converter.adc.sample_clock = rx_sample
    sys.converter.dac.sample_clock = tx_sample
    sys.converter.adc.set_quick_configuration_mode(
        rx_mode.mode, rx_mode.jesd_class
    )
    sys.converter.dac.set_quick_configuration_mode(
        tx_mode.mode, tx_mode.jesd_class
    )

    wiz = sys.export_config(format="adi.xgt-wizard")

    assert wiz.tx.lane_rate_gbps == pytest.approx(tx_rate / 1e9, rel=1e-6)
    assert wiz.rx.lane_rate_gbps == pytest.approx(rx_rate / 1e9, rel=1e-6)
    assert wiz.rx.num_lanes == rx_mode.L
    assert wiz.tx.num_lanes == tx_mode.L
    hw_encoding = rx_links[0].encoding or tx_links[0].encoding
    if hw_encoding is not None:
        assert wiz.jesd_mode == hw_encoding
