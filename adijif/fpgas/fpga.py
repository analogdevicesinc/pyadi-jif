"""FPGA parent metaclass to maintain consistency for all FPGA classes."""

from abc import ABCMeta, abstractmethod
from typing import Dict, List, Optional, Union

from adijif.common import core
from adijif.converters.converter import converter as conv
from adijif.gekko_trans import gekko_translation
from adijif.solvers import CpoSolveResult


class fpga(core, gekko_translation, metaclass=ABCMeta):
    """Parent metaclass for all FPGA classes."""

    """Generate another clock for link layer output.
    This is used when the GEARBOX is enabled in HDL within link layer core.
    """
    requires_separate_link_layer_out_clock: bool = False

    @property
    @abstractmethod
    def determine_cpll(self) -> None:
        """Try to use CPLL for clocking.

        This method is only used in brute-force classes

        Raises:
            NotImplementedError: Method not implemented
        """
        raise NotImplementedError  # pragma: no cover

    @property
    @abstractmethod
    def determine_qpll(self) -> None:
        """Try to use QPLL for clocking.

        This method is only used in brute-force classes

        Raises:
            NotImplementedError: Method not implemented
        """
        raise NotImplementedError  # pragma: no cover

    @property
    @abstractmethod
    def get_config(  # type: ignore
        self,
        converter: conv,
        fpga_ref: Union[float, int],
        solution: Optional[CpoSolveResult] = None,
    ) -> Union[List[Dict], Dict]:
        """Extract clocking configuration from solutions.

        Args:
            converter (conv): Converter object connected to FPGA who config is
                collected
            fpga_ref (int or float): Reference clock generated for FPGA for specific
                converter
            solution (CpoSolveResult): CPlex solution. Only needed for CPlex solver

        Raises:
            NotImplementedError: Method not implemented
        """
        raise NotImplementedError  # pragma: no cover
