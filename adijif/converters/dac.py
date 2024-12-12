"""Converter base meta class for all converter clocking models."""

from abc import ABCMeta, abstractmethod
from typing import List, Union

from adijif.converters.converter import converter


class dac(converter, metaclass=ABCMeta):
    """DAC base meta class used to enforce all DAC classes.

    This class should be inherited from for all DACs and transceivers.

    """

    def _check_valid_internal_configuration(self) -> None:
        """Verify current internal clocking configuration for part is valid.

        Raises:
            Exception: Invalid clocking configuration
        """
        if self.interpolation * self.sample_clock > self.converter_clock_max:
            raise Exception(
                "DAC rate too fast for configuration {} (max: {})".format(
                    self.interpolation * self.sample_clock,
                    self.converter_clock_max,
                )
            )
        if self.interpolation * self.sample_clock < self.converter_clock_min:
            raise Exception(
                "DAC rate too slow for configuration {} (min: {})".format(
                    self.interpolation * self.sample_clock,
                    self.converter_clock_min,
                )
            )

    @property
    @abstractmethod
    def interpolation_available(self) -> List:
        """Interpolation settings available.

        Must be a list or None

        Raises:
            NotImplementedError: If child classes do not implement method/property
        """
        raise NotImplementedError  # pragma: no cover

    _interpolation = 1

    @property
    def interpolation(self) -> Union[int, float]:
        """Interpolation between DAC and JESD framer. If none device is not an DAC.

        Generally a multiple of 2

        Returns:
            int: interpolation value
        """
        return self._interpolation

    @interpolation.setter
    def interpolation(self, value: int) -> None:
        """Interpolation between DAC and JESD framer. If none device is not an DAC.

        Args:
            value (int): interpolation

        Raises:
            Exception: interpolation not an integer or not in range
        """
        if int(value) != value:
            raise Exception("interpolation_available must be an integer")
        if value not in self.interpolation_available:
            raise Exception("interpolation_available not in range for device")
        self._interpolation = value

    @property
    def converter_clock(self) -> Union[int, float]:
        """Get rate of converter in samples per second.

        Returns:
            float: converter clock rate in samples per second
        """
        return self.sample_clock * self.interpolation
