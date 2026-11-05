"""Tests for frequency plan JSON config export/import."""

import json

import pytest

from adijif.freqplan import (
    compute_rx,
    compute_tx,
    default_rx_plan,
    default_tx_plan,
    spans_mhz,
)
from adijif.freqplan.config import dumps, loads, plan_from_dict, plan_to_dict


def _spans(res):
    return {k: spans_mhz(v.spans) for k, v in res.stages.items()}


def test_round_trip():
    rx, tx = default_rx_plan(), default_tx_plan()
    rx2, tx2, view = loads(dumps(rx, tx, {"hide": ["adc"]}))
    assert _spans(compute_rx(rx2)) == _spans(compute_rx(rx))
    assert _spans(compute_tx(tx2)) == _spans(compute_tx(tx))
    assert view == {"hide": ["adc"]}
    assert rx2.targets == rx.targets
    assert rx2.datapath is not rx.datapath


def test_export_hardware_nco():
    rx = default_rx_plan()
    rx.cddc_rf_hz[0] = 12e9
    d = plan_to_dict(rx, None)
    cddc = d["rx"]["datapath"]["cddc"]
    assert cddc["nco_frequencies"][0] == 8e9
    assert cddc["nyquist_zones"][0] == 2
    assert "tx" not in d or d["tx"] is None
    json.dumps(d)


def test_alpha_global_and_one_sided():
    rx = default_rx_plan()
    rx.alpha = 0.7
    rx2, tx2, view = loads(dumps(rx, None))
    assert tx2 is None and view == {}
    assert rx2.alpha == 0.7
    tx = default_tx_plan()
    tx.alpha = 0.6
    rx3, tx3, _ = loads(dumps(None, tx))
    assert rx3 is None and tx3.alpha == 0.6


def test_bad_config_rejected():
    with pytest.raises(ValueError, match="version"):
        plan_from_dict({})
    d = plan_to_dict(default_rx_plan(), default_tx_plan())
    d["part"] = "AD9999"
    with pytest.raises(ValueError, match="Unsupported part"):
        plan_from_dict(d)


def test_length_mismatch_and_malformed():
    d = plan_to_dict(default_rx_plan(), default_tx_plan())
    d["rx"]["datapath"]["fddc"]["enabled"].pop()
    with pytest.raises(ValueError, match="expected 8"):
        plan_from_dict(d)
    d = plan_to_dict(default_rx_plan(), default_tx_plan())
    d["tx"]["cduc_dac_hz"].append(0.0)
    with pytest.raises(ValueError, match="cduc_dac_hz"):
        plan_from_dict(d)
    d = plan_to_dict(default_rx_plan(), default_tx_plan())
    del d["rx"]["adc_rate_hz"]
    with pytest.raises(ValueError):
        plan_from_dict(d)
    with pytest.raises(ValueError):
        loads("not json")


def test_export_wraps_fine_ncos():
    """FDDC/FDUC NCOs are exported wrapped into their stage's Nyquist band."""
    rx, tx = default_rx_plan(), default_tx_plan()
    # cddc0 output is 20 GSPS / 4 = 5 GSPS, so +3 GHz wraps to -2 GHz.
    rx.datapath.fddc_nco_frequencies[0] = 3e9
    rx.datapath.fddc_nco_frequencies[2] = 1e9
    # FDUC output (CDUC input) is 20 GSPS / 4 = 5 GSPS: +4 GHz -> -1 GHz.
    tx.datapath.fduc_nco_frequencies[0] = 4e9
    tx.datapath.fduc_nco_frequencies[4] = -2.5e9
    d = plan_to_dict(rx, tx)
    fddc = d["rx"]["datapath"]["fddc"]["nco_frequencies"]
    fduc = d["tx"]["datapath"]["fduc"]["nco_frequencies"]
    assert fddc[0] == -2e9 and fddc[2] == 1e9
    assert fduc[0] == -1e9 and fduc[4] == -2.5e9
    rx2, tx2, _ = loads(dumps(rx, tx))
    assert _spans(compute_rx(rx2)) == _spans(compute_rx(rx))
    assert _spans(compute_tx(tx2)) == _spans(compute_tx(tx))
