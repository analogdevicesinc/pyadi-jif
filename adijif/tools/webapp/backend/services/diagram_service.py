"""Service for generating diagrams."""

import logging
from typing import Optional

import adijif as jif

logger = logging.getLogger(__name__)


def draw_adc_diagram(adc: Optional[object] = None) -> str:
    """Draw ADC clock tree diagram.

    Args:
        adc: ADC converter object. If None, uses ad9680 as default.

    Returns:
        SVG data as string.
    """
    if adc is None:
        adc = jif.ad9680()

    # Check static
    adc.validate_config()

    required_clocks = adc.get_required_clocks()
    required_clock_names = adc.get_required_clock_names()

    # Add generic clock sources for solver
    clks = []
    for clock, name in zip(required_clocks, required_clock_names, strict=False):
        clk = jif.types.arb_source(name)
        adc._add_equation(clk(adc.model) == clock)
        clks.append(clk)

    # Solve
    solution = adc.model.solve(LogVerbosity="Quiet")
    settings = adc.get_config(solution)

    # Get clock values
    clock_values = {}
    for clk in clks:
        clock_values.update(clk.get_config(solution))
    settings["clocks"] = clock_values

    adc.show_rates = False
    return adc.draw(settings["clocks"])


def draw_dac_diagram(dac: Optional[object] = None) -> str:
    """Draw DAC clock tree diagram.

    Args:
        dac: DAC converter object. If None, uses ad9144 as default.

    Returns:
        SVG data as string.
    """
    if dac is None:
        dac = jif.ad9144()

    # Check static
    dac.validate_config()

    required_clocks = dac.get_required_clocks()
    required_clock_names = dac.get_required_clock_names()

    # Add generic clock sources for solver
    clks = []
    for clock, name in zip(required_clocks, required_clock_names, strict=False):
        clk = jif.types.arb_source(name)
        dac._add_equation(clk(dac.model) == clock)
        clks.append(clk)

    # Solve
    solution = dac.model.solve(LogVerbosity="Quiet")
    settings = dac.get_config(solution)

    # Get clock values
    clock_values = {}
    for clk in clks:
        clock_values.update(clk.get_config(solution))
    settings["clocks"] = clock_values

    dac.show_rates = False
    return dac.draw(settings["clocks"])
