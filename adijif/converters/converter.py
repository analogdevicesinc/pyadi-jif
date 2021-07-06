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
    _jesd_params_to_skip = ["S"]  # Params in table not to set
    _jesd_params_to_skip_check = ["DualLink"]

    def validate_config(self) -> None:
        """Validate device configuration including JESD and clocks.

        This check only is for static configuration that does not include
        variables which are solved.
        """
        self._check_valid_jesd_mode()
        self._check_valid_internal_configuration()  # type: ignore
        self.validate_clocks()

    def set_quick_configuration_mode(self, mode: Union[str, int]) -> None:
        """Set JESD configuration based on preset mode table.

        Args:
            mode (str): Integer of desired mode.

        Raises:
            Exception: Invalid mode selected
        """
        smode = str(mode)
        if smode not in self.quick_configuration_modes.keys():
            raise Exception("Mode {} not among configurations".format(smode))
        for jparam in self.quick_configuration_modes[smode]:
            if jparam in self._jesd_params_to_skip:
                continue
            setattr(self, jparam, self.quick_configuration_modes[smode][jparam])

    def _check_valid_jesd_mode(self) -> None:
        """Verify current JESD configuration for part is valid.

        Raises:
            Exception: Invalid JESD configuration
        """
        # Check to make sure JESD clocks in range
        self._check_jesd_config()
        # Pull current mode
        k = next(iter(self.quick_configuration_modes))
        attrs = self.quick_configuration_modes[k].keys()
        current_config = {attr: getattr(self, attr) for attr in attrs}
        print("current_config", current_config)
        # Check mode in supported modes
        for mode in self.quick_configuration_modes.keys():
            cmode = self.quick_configuration_modes[mode]
            for k in self._jesd_params_to_skip_check:
                if hasattr(cmode, k):
                    del cmode[k]
                if hasattr(current_config, k):
                    del current_config[k]
            if current_config == cmode:
                return
        print("current_config", current_config)
        raise Exception("Invalid JESD configuration for {}".format(self.name))

    @property
    @abstractmethod
    def clocking_option_available(self) -> List[str]:
        """Supported clocking modes.

        Returns:
            List: List of string of clocking modes
        """
        raise NotImplementedError  # pragma: no cover

    _clocking_option = "direct"

    @property
    def clocking_option(self) -> str:
        """Get clocking mode for device.

        Returns:
            str: Clocking mode for device (integrated_pll, direct)
        """
        return self._clocking_option

    @clocking_option.setter
    def clocking_option(self, value: str) -> None:
        """Set clocking mode for device.

        Args:
            value (str): Clocking mode for device (integrated_pll, direct)

        Raises:
            Exception: clocking_option not supported by device
        """
        if value not in self.clocking_option_available:
            raise Exception("clocking_option not available for device")
        self._clocking_option = value

    @property
    @abstractmethod
    def quick_configuration_modes(self) -> Dict:
        """Supported JESD mode table.

        Returns:
            Dict: Dictionary of supported modes
        """
        raise NotImplementedError  # pragma: no cover

    @property
    @abstractmethod
    def _check_valid_internal_configuration(self) -> None:
        """Check current device mode is valid."""
        raise NotImplementedError  # pragma: no cover

    @property
    @abstractmethod
    def converter_clock_min(self) -> Union[int, float]:
        """Minimum rate of data converter.

        Returns:
            Union[int, float]: converter min rate
        """
        raise NotImplementedError  # pragma: no cover

    @property
    @abstractmethod
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

    @property
    @abstractmethod
    def get_config(self) -> Dict:
        """Extract configuration from solver solution.

        Return dictionary of clocking config for converter

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
