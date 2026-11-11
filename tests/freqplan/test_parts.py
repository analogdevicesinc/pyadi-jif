"""Device capability, simple topology, and cross-device persistence checks."""

import json

import pytest

from adijif.freqplan import (
    ADAPTERS,
    compute_rx,
    compute_tx,
    default_rx_plan,
    default_tx_plan,
    dumps,
    loads,
    rx_link,
    solve_link,
    tx_link,
)

PARTS = [
    "AD9084",
    "AD9081",
    "AD9082",
    "AD9088",
    "AD9680",
    "AD9144",
    "AD9152",
    "AD9371",
    "AD9371_OBS",
    "ADRV9371",
    "ADRV9009",
]


def test_registered_parts():
    assert set(ADAPTERS) == set(PARTS)


@pytest.mark.parametrize("part", PARTS)
def test_defaults_compute_and_roundtrip(part):
    adapter = ADAPTERS[part]
    rx = default_rx_plan(part) if adapter.rx_datapath else None
    tx = default_tx_plan(part) if adapter.tx_datapath else None
    for plan, compute in ((rx, compute_rx), (tx, compute_tx)):
        if plan:
            assert compute(plan).stages
    restored = loads(dumps(rx, tx))
    assert json.loads(dumps(*restored[:2])) == json.loads(dumps(rx, tx))


def test_ad9082_physical_adc_mapping():
    plan = default_rx_plan("AD9082")
    assert ADAPTERS["AD9082"].num_adcs == 2
    assert len(plan.datapath.cddc_enabled) == 4
    assert max(plan.adc_to_cddc) == 1


def test_ad9088_has_eight_dacs():
    plan = default_tx_plan("AD9088")
    assert len(plan.datapath.cduc_enabled) == 8
    assert len(plan.datapath.fduc_enabled) == 16
    assert sum(s.kind == "dac" for s in compute_tx(plan).stages.values()) == 8


def test_transceiver_lo_translation():
    rx = default_rx_plan("ADRV9009")
    rx.signals[0].center_hz = 2.41e9
    rx.datapath.lo_hz = 2.4e9
    out = compute_rx(rx).stages["ddc0"]
    desired = [s for s in out.spans if not s.image and s.signal == "S1"]
    assert (desired[0].lo + desired[0].hi) / 2 == pytest.approx(10e6)
    tx = default_tx_plan("ADRV9009")
    tx.signals[0].center_hz = 10e6
    tx.datapath.lo_hz = 2.4e9
    spans = compute_tx(tx).stages["dac0"].spans
    desired = [s for s in spans if not s.image and s.signal == "S1"]
    assert (desired[0].lo + desired[0].hi) / 2 == pytest.approx(2.41e9)


def test_real_and_complex_transport_counts():
    rx = default_rx_plan("AD9680")
    rx.datapath.factor = 1
    assert rx_link(rx, compute_rx(rx)).M == 2
    rx.datapath.factor = 4
    assert rx_link(rx, compute_rx(rx)).M == 4
    tx = default_tx_plan("AD9152")
    assert tx_link(tx, compute_tx(tx)).M == 2


def test_simple_wrong_direction_and_invalid_nco():
    with pytest.raises(ValueError, match="Tx"):
        default_tx_plan("AD9680")
    rx = default_rx_plan("ADRV9009")
    rx.datapath.nco_hz = [10e6, 0]
    with pytest.raises(ValueError, match="NCO"):
        compute_rx(rx)


def test_ad9680_decimated_link_uses_converter_rate():
    rx = default_rx_plan("AD9680")
    rx.adc_rate_hz = 1e9
    rx.datapath.factor = 4
    req = rx_link(rx, compute_rx(rx))
    assert req.sample_rate_hz == 250e6
    assert solve_link(rx, req).fits


def test_ad9680_tuning_resolution():
    assert ADAPTERS["AD9680"].rx_nco_bits == 12


def test_v1_ad9084_still_loads():
    doc = json.loads(dumps(default_rx_plan(), default_tx_plan()))
    doc["version"] = 1
    rx, tx, _ = loads(json.dumps(doc))
    assert rx.part == tx.part == "AD9084"


def test_ad9144_dual_link_modes_are_not_single_link_fits():
    tx = default_tx_plan("AD9144")
    sol = solve_link(tx, tx_link(tx, compute_tx(tx)))
    table = ADAPTERS[tx.part].tx_converter.quick_configuration_modes
    assert all(
        not table[m.jesd_class][m.mode].get("DualLink", False)
        for m in sol.modes
    )


@pytest.mark.parametrize("part", ["AD9371", "AD9371_OBS"])
def test_known_profile_pairs_enforced(part):
    rx = default_rx_plan(part)
    rx.adc_rate_hz *= 0.99
    with pytest.raises(ValueError, match="profile rate/factor"):
        compute_rx(rx)


def test_imported_profile_constraints_enforced():
    rx = default_rx_plan("ADRV9009")
    rx.datapath.profile_constraints = {"factor": rx.datapath.factor}
    assert (
        loads(dumps(rx, None))[0].datapath.profile_constraints
        == rx.datapath.profile_constraints
    )
    rx.datapath.factor *= 2
    with pytest.raises(ValueError, match="profile constraint"):
        compute_rx(rx)
    rx.datapath.profile_constraints = {"unknown": 1}
    with pytest.raises(ValueError, match="Unknown profile"):
        compute_rx(rx)


def test_simple_state_is_not_shared():
    first, second = default_rx_plan("AD9680"), default_rx_plan("AD9680")
    first.datapath.nco_hz[0] = 100e6
    assert second.datapath.nco_hz == [0, 0]


def test_mxfe_tuning_word_widths():
    assert ADAPTERS["AD9084"].rx_coarse_nco_bits == 32
    assert ADAPTERS["AD9088"].tx_coarse_nco_bits == 32
    assert ADAPTERS["AD9081"].rx_coarse_nco_bits == 48


def test_fine_nco_rate_limit_checked_independently():
    tx = default_tx_plan("AD9088")
    tx.datapath.cduc_interpolation = 4
    sol = solve_link(tx, tx_link(tx, compute_tx(tx)))
    assert not sol.fits
    assert all("NCO clock limit" in m.converter_reason for m in sol.modes)


@pytest.mark.parametrize(
    "part,direction",
    [
        (name, direction)
        for name, adapter in ADAPTERS.items()
        for direction in adapter.directions
    ],
)
@pytest.mark.parametrize("outside", ["below", "above", "nan", "infinity"])
def test_physical_converter_rate_limits_checked_independently(
    part, direction, outside
):
    """Model overrides must not bypass physical converter rate constraints."""
    from dataclasses import replace

    plan = default_rx_plan(part) if direction == "rx" else default_tx_plan(part)
    if direction == "rx":
        req = rx_link(plan, compute_rx(plan))
        attr = "adc_rate_hz"
    else:
        req = tx_link(plan, compute_tx(plan))
        attr = "dac_rate_hz"
    low, high = getattr(ADAPTERS[part], f"{direction}_rate_bounds_hz")
    invalid = {
        "below": low * 0.99,
        "above": high * 1.01,
        "nan": float("nan"),
        "infinity": float("inf"),
    }[outside]
    old = getattr(plan, attr)
    setattr(plan, attr, invalid)
    req = replace(
        req,
        converter_rate_hz=invalid,
        sample_rate_hz=req.sample_rate_hz * invalid / old,
    )
    sol = solve_link(plan, req)
    assert not sol.fits
    reason = sol.message or " ".join(
        m.converter_reason or "" for m in sol.modes
    )
    assert "converter rate" in reason.lower()
