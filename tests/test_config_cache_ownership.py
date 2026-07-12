"""Regression tests for solved-configuration cache ownership."""

import pytest

import adijif


@pytest.mark.parametrize(
    "component,configure",
    [
        (
            adijif.ltc6953,
            lambda device: device.set_requested_clocks(
                1_000_000_000, [500_000_000], ["output"]
            ),
        ),
        (
            adijif.adf4030,
            lambda device: device.set_requested_clocks(
                125_000_000, [100_000_000], ["output"]
            ),
        ),
    ],
)
def test_returned_config_does_not_alias_cached_solution(component, configure):
    """Callers must not be able to corrupt the cache used by drawing."""
    device = component(solver="CPLEX")
    configure(device)
    device.solve()

    config = device.get_config()
    cached = device._last_config
    assert cached == config
    assert cached is not config

    config["output_clocks"]["output"]["rate"] = -1

    assert device._last_config["output_clocks"]["output"]["rate"] != -1
