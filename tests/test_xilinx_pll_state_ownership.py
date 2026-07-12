"""Regression tests for Xilinx transceiver PLL state ownership."""

import pytest

from adijif.fpgas.xilinx.sevenseries import SevenSeries
from adijif.fpgas.xilinx.ultrascaleplus import UltraScalePlus
from adijif.fpgas.xilinx.versal import Versal

PARENTS = {
    "seven": (SevenSeries, "GTXE2"),
    "usp": (UltraScalePlus, "GTHE4"),
    "versal": (Versal, "GTYE5"),
}

SETTER_CASES = [
    ("seven", "CPLL", "M", [1, 2]),
    ("seven", "CPLL", "N2", [1, 2]),
    ("seven", "CPLL", "N1", [4, 5]),
    ("seven", "CPLL", "D", [1, 2]),
    ("seven", "QPLL", "M", [1, 2]),
    ("seven", "QPLL", "N", [16, 20]),
    ("seven", "QPLL", "D", [1, 2]),
    ("usp", "QPLL", "QPLL_CLKOUTRATE", [1, 2]),
    ("usp", "QPLL", "SDMWIDTH", [16, 20]),
    ("versal", "RPLL", "M", [1, 2]),
    ("versal", "RPLL", "N", [5, 6]),
    ("versal", "RPLL", "D", [1, 2]),
    ("versal", "RPLL", "SDMWIDTH", [16, 20]),
    ("versal", "LCPLL", "M", [1, 2]),
    ("versal", "LCPLL", "N", [13, 14]),
    ("versal", "LCPLL", "D", [1, 2]),
    ("versal", "LCPLL", "LCPLL_CLKOUTRATE", [1, 2]),
    ("versal", "LCPLL", "SDMWIDTH", [16, 20]),
]


def _parent(kind):
    parent_type, transceiver_type = PARENTS[kind]
    return parent_type(transceiver_type=transceiver_type, solver="CPLEX")


@pytest.mark.parametrize("kind,pll_name,attribute,selection", SETTER_CASES)
def test_transceiver_pll_setters_copy_mutable_selections(
    kind, pll_name, attribute, selection
):
    """Caller mutations must not alter retained transceiver PLL selections."""
    pll = _parent(kind).plls[pll_name]
    expected = list(selection)

    setattr(pll, attribute, selection)
    selection.clear()

    assert getattr(pll, attribute) == expected


@pytest.mark.parametrize("kind", PARENTS)
def test_transceiver_pll_instances_isolate_private_mutable_defaults(kind):
    """PLL children in separate FPGA models must not share runtime defaults."""
    first = _parent(kind)
    second = _parent(kind)

    for pll_name, first_pll in first.plls.items():
        second_pll = second.plls[pll_name]
        mutable_fields = {
            field
            for cls in type(first_pll).__mro__
            for field, value in vars(cls).items()
            if field.startswith("_")
            and not field.startswith("__")
            and isinstance(value, (list, dict, set))
        }
        for field in mutable_fields:
            assert getattr(first_pll, field) is not getattr(second_pll, field), (
                pll_name,
                field,
            )
