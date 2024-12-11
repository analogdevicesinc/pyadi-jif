"""Converter base meta class for all converter clocking models."""

from abc import ABCMeta, abstractmethod
from typing import List, Union

from adijif.converters.converter import converter


class adc(converter, metaclass=ABCMeta):
    """ADC base meta class used to enforce all ADC classes.

    This class should be inherited from for all ADCs and transceivers.

    """

    def _check_valid_internal_configuration(self) -> None:
        """Verify current internal clocking configuration for part is valid.

        Raises:
            Exception: Invalid clocking configuration
        """
        if self.decimation * self.sample_clock > self.converter_clock_max:
            raise Exception(
                "ADC rate too fast for configuration {}".format(
                    self.decimation * self.sample_clock
                )
            )
        if self.decimation * self.sample_clock < self.converter_clock_min:
            raise Exception(
                "ADC rate too slow for configuration {}".format(
                    self.decimation * self.sample_clock
                )
            )

    @property
    @abstractmethod
    def decimation_available(self) -> List[int]:
        """Decimation settings available.

        Must be a list or None

        Raises:
            NotImplementedError: If child classes do not implement method/property
        """
        raise NotImplementedError  # pragma: no cover

    _decimation = 1

    @property
    def decimation(self) -> Union[int, float]:
        """Decimation between DAC and JESD framer. If none device is not an ADC.

        Generally a multiple of 2

        Returns:
            int: decimation value
        """
        return self._decimation

    @decimation.setter
    def decimation(self, value: int) -> None:
        """Decimation between DAC and JESD framer. If none device is not an ADC.

        Args:
            value (int): decimation

        Raises:
            Exception: decimation not an integer or not in range
        """
        if int(value) != value:
            raise Exception("decimation_available must be an integer")
        if value not in self.decimation_available:
            raise Exception("decimation_available not in range for device")
        self._decimation = value

    @property
    def converter_clock(self) -> Union[int, float]:
        """Get rate of converter in samples per second.

        Returns:
            float: converter clock rate in samples per second
        """
        return self.sample_clock * self.decimation
