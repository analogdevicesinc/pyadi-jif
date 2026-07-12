"""Tests for ownership of clock request inputs."""

import pytest

from adijif.registry import get_component_class


@pytest.mark.parametrize(
    "name,vcxo",
    [
        ("ad9523_1", 125_000_000),
        ("ad9528", 125_000_000),
        ("hmc7044", 125_000_000),
        ("ltc6952", 125_000_000),
        ("ltc6953", 3_000_000_000),
    ],
)
def test_clock_does_not_retain_caller_clock_names(name, vcxo):
    """Configured output names must not alias the caller's mutable list."""
    clock_class = get_component_class("clock", name)
    clock = clock_class(solver="gekko")
    names = ["output"]

    clock.set_requested_clocks(vcxo, [10_000_000], names)
    names[0] = "renamed-by-caller"
    names.append("extra")

    assert clock._clk_names == ["output"]
