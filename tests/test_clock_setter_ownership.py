"""Regression tests for clock-divider setter ownership."""

import pytest

from adijif.registry import get_component_class

SETTER_CASES = [
    ("ad9523_1", "m1", [3, 4]),
    ("ad9523_1", "d", [1, 2]),
    ("ad9523_1", "n2", [12, 16]),
    ("ad9523_1", "r2", [1, 2]),
    ("ad9528", "m1", [3, 4]),
    ("ad9528", "d", [1, 2]),
    ("ad9528", "k", [1, 2]),
    ("ad9528", "n2", [12, 16]),
    ("ad9528", "r1", [1, 2]),
    ("ad9528", "a", [0, 1]),
    ("ad9528", "b", [3, 4]),
    ("hmc7044", "d", [1, 2]),
    ("hmc7044", "n2", [8, 9]),
    ("hmc7044", "r2", [1, 2]),
    ("hmc7044", "vcxo_doubler", [1, 2]),
    ("ltc6952", "d", [1, 2]),
    ("ltc6952", "n2", [1, 2]),
    ("ltc6952", "r2", [1, 2]),
    ("ltc6953", "m", [1, 2]),
]


@pytest.mark.parametrize("name,attribute,selection", SETTER_CASES)
def test_clock_setter_copies_mutable_selection(name, attribute, selection):
    """Changing a setter input later must not alter the clock selection."""
    clock_class = get_component_class("clock", name)
    clock = clock_class(solver="gekko")
    expected = list(selection)

    setattr(clock, attribute, selection)
    selection.clear()

    assert getattr(clock, attribute) == expected
    if name == "ltc6953":
        assert clock._d == expected
        assert clock._m == expected
        assert clock._d is not clock._m
