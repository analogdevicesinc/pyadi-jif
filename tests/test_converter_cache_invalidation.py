"""Regression tests for converter quick-mode cache invalidation."""

from typing import Any

import pytest

import adijif


@pytest.mark.parametrize(
    "device_type,mode,jesd_class",
    [
        (adijif.ad9680, "1", "jesd204b"),
        (adijif.ad9144, "4", "jesd204b"),
        (adijif.ad9084_rx, "47", "jesd204c"),
        (adijif.ad9084_tx, "3", "jesd204c"),
    ],
)
def test_quick_mode_change_invalidates_converter_drawing_cache(
    device_type, mode, jesd_class
):
    """Changing JESD mode must make a prior solved converter state stale."""
    device: Any = device_type(solver="CPLEX")
    device._last_config = object()

    device.set_quick_configuration_mode(mode, jesd_class)

    assert device._last_config is None


def test_invalid_quick_mode_attempt_invalidates_converter_drawing_cache():
    """A failed mode change must not leave an old solution looking current."""
    device: Any = adijif.ad9680(solver="CPLEX")
    device._last_config = object()

    with pytest.raises(Exception, match="not among configurations"):
        device.set_quick_configuration_mode("not-a-mode")

    assert device._last_config is None
