"""Converter base meta class for all converter clocking models."""
from abc import ABCMeta, abstractmethod
from typing import Dict, List, Union

from adijif.common import core
from adijif.gekko_trans import gekko_translation
from adijif.jesd import jesd


class converter(core, jesd, gekko_translation, metaclass=ABCMeta):
    """Converter base meta class used to enforce all converter classes.

    This class should be inherited from for all converters: ADCs, DACs,
    and transceivers.

    """

    config: Dict = {}

    def validate_config(self):
        """Validate device configuration including JESD and clocks"""
        self._check_valid_jesd_mode()
        self._check_valid_internal_configuration()
        self.validate_clocks()

    @property
    def _check_valid_jesd_mode(self) -> None:
        """Check current JESD mode is valid."""
        raise NotImplementedError  # pragma: no cover

    @property
    def _check_valid_internal_configuration(self) -> None:
        """Check current device mode is valid."""
        raise NotImplementedError  # pragma: no cover

    @property
    def converter_clock_min(self) -> Union[int, float]:
        """Minimum rate of data converter.

        Returns:
            Union[int, float]: converter min rate
        """
        raise NotImplementedError  # pragma: no cover

    @property
    def converter_clock_max(self) -> Union[int, float]:
        """Maximum rate of data converter.

        Returns:
            Union[int, float]: converter max rate
        """
        raise NotImplementedError  # pragma: no cover

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of supported by device.

        Must be a string

        Raises:
            NotImplementedError: If child classes do not implement method/property
        """
        raise NotImplementedError  # pragma: no cover

    @property
    @abstractmethod
    def direct_clocking(self) -> bool:
        """Utilize direct clocking or internal PLLs.

        Must be a boolean and handle either mode

        Raises:
            NotImplementedError: If child classes do not implement method/property
        """
        raise NotImplementedError  # pragma: no cover

    @property
    @abstractmethod
    def device_clock_available(self) -> None:
        """Allowable K settings for device.

        Must be a list ints

        Raises:
            NotImplementedError: If child classes do not implement method/property
        """
        raise NotImplementedError  # pragma: no cover

    @property
    @abstractmethod
    def device_clock_ranges(self) -> None:
        """Allowable ranges for device clocks based on config.

        This is only used for brute-force implementations and not solver based

        Raises:
            NotImplementedError: If child classes do not implement method/property
        """
        raise NotImplementedError  # pragma: no cover

    @property
    @abstractmethod
    def get_required_clocks(self) -> List:
        """Get list of strings of names of requested clocks.

        This list of names is for the clocks defined by get_required_clocks

        Raises:
            NotImplementedError: If child classes do not implement method/property
        """
        raise NotImplementedError  # pragma: no cover

    @property
    @abstractmethod
    def get_required_clock_names(self) -> List[str]:
        """Generate list of required clock names.

        This is a list of strings

        Raises:
            NotImplementedError: If child classes do not implement method/property
        """
        raise NotImplementedError  # pragma: no cover

    def _get_converters(self) -> Union["converter", List["converter"]]:
        return self

    def __str__(self) -> str:
        """Get string description of converter object.

        Returns:
            str: Description string
        """
        return f"{self.name} data converter model"
