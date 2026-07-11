"""Tests for explicit AD9084/AD9088 RX variant metadata."""

import pytest

import adijif
from adijif.converters.ad9084_dp import ad9084_dp_rx
from adijif.converters.ad9088_dp import ad9088_dp_rx


@pytest.mark.parametrize(
    ("device_type", "datapath_type", "sample_clock", "cddcs", "fddcs", "mode"),
    [
        (adijif.ad9084_rx, ad9084_dp_rx, int(2.5e9), 4, 8, "47"),
        (adijif.ad9088_rx, ad9088_dp_rx, int(1e9), 8, 16, "45"),
    ],
)
def test_rx_variant_metadata_preserves_defaults(
    device_type, datapath_type, sample_clock, cddcs, fddcs, mode
):
    """Explicit metadata preserves each silicon variant's existing defaults."""
    device = device_type(solver="gekko")

    assert isinstance(device.datapath, datapath_type)
    assert device.sample_clock == sample_clock
    assert len(device.datapath.cddc_decimations) == cddcs
    assert len(device.datapath.fddc_decimations) == fddcs
    assert device._check_valid_jesd_mode() == mode


def test_rx_defaults_do_not_depend_on_display_name():
    """Aliases and renamed subclasses retain the declared silicon behavior."""

    class renamed_ad9088(adijif.ad9088_rx):
        name = "MXFE_RX_ALIAS"

    device = renamed_ad9088(solver="gekko")

    assert isinstance(device.datapath, ad9088_dp_rx)
    assert device.sample_clock == int(1e9)
    assert len(device.datapath.cddc_decimations) == 8
    assert len(device.datapath.fddc_decimations) == 16
    assert device._check_valid_jesd_mode() == "45"
