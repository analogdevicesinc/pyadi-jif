"""Tests for Explorer JESD mode helper ownership."""

import copy

import adijif
from adijif.tools.explorer.src.pages.helpers.jesd import (
    get_jesd_controls,
    get_valid_jesd_modes,
)


def test_get_valid_jesd_modes_does_not_mutate_mode_table():
    """Formatting mode results must not modify its caller-owned mode table."""
    converter = adijif.ad9680(solver="gekko")
    _, modes = get_jesd_controls(converter)
    before = copy.deepcopy(modes)

    results, found = get_valid_jesd_modes(converter, modes, {})

    assert found
    assert results
    assert modes == before
    assert all(
        "mode" not in config for table in modes.values() for config in table.values()
    )


def test_get_valid_jesd_modes_returns_independent_rows():
    """Derived columns belong only to result rows, not capability records."""
    converter = adijif.ad9680(solver="gekko")
    _, modes = get_jesd_controls(converter)

    results, _ = get_valid_jesd_modes(converter, modes, {})
    results[0]["result_only"] = True

    assert all(
        "result_only" not in config
        for table in modes.values()
        for config in table.values()
    )


def test_get_valid_jesd_modes_restores_converter_state():
    """Enumerating modes must not leave the caller on the last tested mode."""
    converter = adijif.ad9680(solver="gekko")
    converter.set_quick_configuration_mode("1", "jesd204b")
    converter.sample_clock = 500_000_000
    attrs = ("jesd_class", "L", "M", "F", "S", "N", "Np", "K", "sample_clock")
    before = tuple(getattr(converter, attr) for attr in attrs)
    _, modes = get_jesd_controls(converter)

    get_valid_jesd_modes(converter, modes, {})

    after = tuple(getattr(converter, attr) for attr in attrs)
    assert after == before
