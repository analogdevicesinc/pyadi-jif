"""AD9152 high speed DAC clocking model."""

from typing import Any, Dict, List, Union

from adijif.converters.ad9144 import ad9144
from adijif.converters.ad9152_dp import ad9152_dp

from ..solvers import CpoSolveResult  # noqa: I202


class ad9152(ad9144):
    """AD9152 high speed DAC model.

    This model inherits from AD9144 but with AD9152 specific constraints.
    """

    name = "AD9152"
    
    converter_clock_max = 2.25e9
    sample_clock_max = 2.25e9

    datapath = ad9152_dp()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize AD9152 class.

        Args:
            *args (Any): Pass through arguments
            **kwargs (Any): Pass through keyword arguments
        """
        super().__init__(*args, **kwargs)
        self.datapath = ad9152_dp()

    @property
    def interpolation(self) -> int:
        """Interpolation factor.

        Returns:
            int: interpolation factor
        """
        return self.datapath.interpolation

    @interpolation.setter
    def interpolation(self, value: int) -> None:
        """Set interpolation factor.

        Args:
            value (int): interpolation factor
        """
        self.datapath.interpolation = value

    def get_required_clock_names(self) -> List[str]:
        """Get list of strings of names of requested clocks.

        Returns:
            List[str]: List of strings of clock names in order
        """
        clk = f"{self.name.lower()}_ref_clk"
        return [clk, f"{self.name.lower()}_sysref"]

    def _pll_config(self) -> Dict:
        # Override to ensure correct VCO range for AD9152 if different from AD9144
        # For now, assuming AD9152 internal PLL is similar enough to AD9144
        return super()._pll_config()
