"""Regression tests for AD9144 JESD quick-configuration metadata."""

import pytest

import adijif

DUAL_LINK_MODES = ("4-DL", "5-DL", "6-DL", "7-DL", "9-DL", "10-DL")
SINGLE_LINK_MODES = ("0", "1", "2", "3", "4", "5", "6", "7", "9", "10")


@pytest.mark.parametrize("mode", DUAL_LINK_MODES)
def test_ad9144_dual_link_modes_enable_dual_link(mode):
    converter = adijif.ad9144()

    converter.set_quick_configuration_mode(mode)

    assert converter.DualLink is True
    assert converter.quick_configuration_modes["jesd204b"][mode]["DualLink"] is True


@pytest.mark.parametrize("mode", SINGLE_LINK_MODES)
def test_ad9144_single_link_modes_disable_dual_link(mode):
    converter = adijif.ad9144()

    converter.set_quick_configuration_mode(mode)

    assert converter.DualLink is False
    assert converter.quick_configuration_modes["jesd204b"][mode]["DualLink"] is False
