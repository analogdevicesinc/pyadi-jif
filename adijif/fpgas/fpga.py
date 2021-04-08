"""FPGA parent metaclass to maintain consistency for all FPGA classes."""
from abc import ABCMeta, abstractmethod
from typing import Dict, List, Union

from adijif.common import core
from adijif.gekko_trans import gekko_translation


class fpga(core, gekko_translation, metaclass=ABCMeta):
    """Parent metaclass for all FPGA classes."""

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
    def get_config(self) -> Union[List[Dict], Dict]:
        """Extract clocking configuration from solutions.

        Raises:
            NotImplementedError: Method not implemented
        """
        raise NotImplementedError  # pragma: no cover
