"""Regression tests for AD9084 profile cache invalidation."""

from pathlib import Path
from typing import Any

import pytest

import adijif

PROFILE = (
    Path(__file__).parent
    / "apollo_profiles"
    / "ad9084_profiles"
    / "id00_stock_mode.json"
)


@pytest.mark.parametrize("device_type", [adijif.ad9084_rx, adijif.ad9084_tx])
def test_profile_application_invalidates_converter_cache(device_type):
    """Applying a profile must make prior solved converter state stale."""
    device: Any = device_type(solver="CPLEX")
    device._last_config = object()

    device.apply_profile_settings(str(PROFILE))

    assert device._last_config is None


def test_rejected_profile_application_invalidates_converter_cache():
    """A rejected profile must not leave an old solution looking current."""
    device: Any = adijif.ad9084_rx(solver="CPLEX")
    device._last_config = object()

    with pytest.raises(FileNotFoundError, match="does not exist"):
        device.apply_profile_settings("missing-profile.json")

    assert device._last_config is None
