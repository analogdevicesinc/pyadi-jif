"""Regression tests for AD908x datapath configuration snapshots."""

import pytest

import adijif

DATAPATH_CASES = [
    (adijif.ad9081_rx, "cddc", "decimations", "cddc_decimations"),
    (adijif.ad9081_tx, "fduc", "enabled", "fduc_enabled"),
    (adijif.ad9084_rx, "cddc", "decimations", "cddc_decimations"),
    (adijif.ad9084_tx, "fduc", "enabled", "fduc_enabled"),
    (adijif.ad9088_rx, "fddc", "source", "fddc_source"),
    (adijif.ad9088_tx, "fduc", "enabled", "fduc_enabled"),
]


@pytest.mark.parametrize("device_type,stage,field,attribute", DATAPATH_CASES)
def test_datapath_get_config_returns_independent_snapshot(
    device_type, stage, field, attribute
):
    """Mutating a returned configuration must not alter the converter datapath."""
    device = device_type(solver="gekko")
    expected = list(getattr(device.datapath, attribute))

    config = device.datapath.get_config()
    config[stage][field][0] = "changed"

    assert getattr(device.datapath, attribute) == expected


def test_datapath_snapshots_do_not_alias_each_other():
    """Separate snapshots must not share nested lists."""
    device = adijif.ad9084_rx(solver="gekko")

    first = device.datapath.get_config()
    second = device.datapath.get_config()
    first["cddc"]["decimations"][0] = 99

    assert second["cddc"]["decimations"][0] != 99
