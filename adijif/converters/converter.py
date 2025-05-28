"""Converter base meta class for all converter clocking models."""

from abc import ABCMeta, abstractmethod
from typing import Dict, List, Union

from ..common import core
from ..draw import Layout, Node
from ..gekko_trans import gekko_translation
from ..jesd import jesd


class converter(core, jesd, gekko_translation, metaclass=ABCMeta):
    """Converter base meta class used to enforce all converter classes.

    This class should be inherited from for all converters: ADCs, DACs,
    and transceivers.

    """

    """Nested device with multiple dependent converters. Includes MxFE and
    transceivers"""
    _nested = False

    """DSP data path of device"""
    datapath = None

    config: Dict = {}
    _jesd_params_to_skip = [
        "E",
        "global_index",
    ]  # Params in table not to set
    _jesd_params_to_skip_check = [
        "DualLink",
        "E",
        "decimations",
        "global_index",
    ]

    def draw(
        self, clocks: Dict, lo: Layout = None, clock_chip_node: Node = None
    ) -> str:
        """Generic Draw converter model.

        Args:
            clocks (Dict): Clocking configuration
            lo (Layout): Layout object to draw on
            clock_chip_node (Node): Clock chip node to add to. Defaults to None.

        Returns:
            str: Path to image file

        Raises:
            Exception: If no solution is saved
        """
        system_draw = lo is not None
        name = self.name.lower()

        if not system_draw:
            lo = Layout(f"{name} Example")
        else:
            assert isinstance(lo, Layout), "lo must be a Layout object"

        ic_node = Node(self.name)
        lo.add_node(ic_node)

        # rate = clocks[f"{name}_ref_clk"]
        # Find key with ending
        ref_clk_name = None
        for key in clocks.keys():
            if key.lower().endswith(f"{name.lower()}_ref_clk"):
                ref_clk_name = key
                break
        if ref_clk_name is None:
            raise Exception(
                f"No clock found for {name}_ref_clk\n.Options: {clocks.keys()}"
            )

        sysref_clk_name = None
        for key in clocks.keys():
            if key.lower().endswith(f"{name.lower()}_sysref"):
                sysref_clk_name = key
                break
        if sysref_clk_name is None:
            raise Exception(
                f"No clock found for {name}_sysref\n.Options: {clocks.keys()}"
            )

        if not system_draw:
            ref_in = Node("REF_IN", ntype="input")
            lo.add_node(ref_in)
        else:
            to_node = lo.get_node(ref_clk_name)
            from_node = lo.get_connection(to=to_node.name)
            assert from_node, "No connection found"
            assert isinstance(from_node, list), "Connection must be a list"
            assert len(from_node) == 1, "Only one connection allowed"
            ref_in = from_node[0]["from"]
            # Remove to_node since it is not needed
            lo.remove_node(to_node.name)

        rate = clocks[ref_clk_name]

        lo.add_connection({"from": ref_in, "to": ic_node, "rate": rate})

        # Add framer
        jesd204_framer = Node("JESD204 Framer", ntype="jesd204framer")
        ic_node.add_child(jesd204_framer)

        # SYSREF
        if not system_draw:
            sysref_in = Node("SYSREF_IN", ntype="input")
            lo.add_connection(
                {
                    "from": sysref_in,
                    "to": jesd204_framer,
                    # "rate": clocks[f"{name}_sysref"],
                    "rate": clocks[sysref_clk_name],
                }
            )
        else:
            # to_node = lo.get_node(f"{name}_sysref")
            to_node = lo.get_node(sysref_clk_name)
            from_node = lo.get_connection(to=to_node.name)
            assert from_node, "No connection found"
            assert isinstance(from_node, list), "Connection must be a list"
            assert len(from_node) == 1, "Only one connection allowed"
            sysref_in = from_node[0]["from"]
            lo.remove_node(to_node.name)

            lo.add_connection(
                {
                    "from": sysref_in,
                    "to": jesd204_framer,
                    # "rate": clocks[f"{name}_sysref"],
                    "rate": clocks[sysref_clk_name],
                }
            )

        # WIP Add remote deframer
        jesd204_deframer = Node("JESD204 Deframer", ntype="deframer")

        # Add connect for each lane
        for _ in range(self.L):
            lane_rate = self.bit_clock
            lo.add_connection(
                {"from": jesd204_framer, "to": jesd204_deframer, "rate": lane_rate}
            )

        if not system_draw:
            return lo.draw()

    def validate_config(self) -> None:
        """Validate device configuration including JESD and clocks.

        This check only is for static configuration that does not include
        variables which are solved.
        """
        self._check_valid_jesd_mode()
        self._check_valid_internal_configuration()  # type: ignore
        self.validate_clocks()

    def set_quick_configuration_mode(
        self, mode: Union[str, int], jesd_class: str = "jesd204b"
    ) -> None:
        """Set JESD configuration based on preset mode table.

        Args:
            mode (str): Integer of desired mode.
            jesd_class (str): JESD class to use. Default is jesd204b.

        Raises:
            Exception: Invalid mode selected
        """
        smode = str(mode)
        if smode not in self.quick_configuration_modes[jesd_class].keys():
            raise Exception(f"Mode {smode} not among configurations for {jesd_class}")

        if jesd_class not in self.available_jesd_modes:
            raise Exception(f"{jesd_class} not available for {self.name}")
        self.jesd_class = jesd_class

        cfg = self.quick_configuration_modes[jesd_class][smode]
        for jparam in cfg:
            if jparam in self._jesd_params_to_skip:
                continue
            setattr(self, jparam, cfg[jparam])

    def _check_valid_jesd_mode(self) -> str:
        """Verify current JESD configuration for part is valid.

        Raises:
            Exception: Invalid JESD configuration

        Returns:
            str: Current JESD mode
        """
        # Check to make sure JESD clocks in range
        self._check_jesd_config()
        # Pull current mode
        k = next(iter(self.quick_configuration_modes[self.jesd_class]))
        attrs = self.quick_configuration_modes[self.jesd_class][k].keys()

        current_config = {}
        for attr in attrs:
            if attr in self._jesd_params_to_skip_check:
                continue
            current_config[attr] = getattr(self, attr)

        # Check mode in supported modes
        for mode in self.quick_configuration_modes[self.jesd_class].keys():
            cmode = self.quick_configuration_modes[self.jesd_class][mode].copy()
            for k in self._jesd_params_to_skip_check:
                if hasattr(cmode, k) or k in cmode:
                    del cmode[k]
                if hasattr(current_config, k) or k in current_config:
                    del current_config[k]
            if current_config == cmode:
                return mode
        raise Exception(f"Invalid JESD configuration for {self.name}\n{current_config}")

    def get_current_jesd_mode_settings(self) -> Dict:
        """Get current JESD mode settings.

        Returns:
            Dict: Current JESD mode settings
            str: Current JESD mode
        """
        k = next(iter(self.quick_configuration_modes[self.jesd_class]))
        attrs = self.quick_configuration_modes[self.jesd_class][k].keys()
        current_config = {}
        for attr in attrs:
            if attr in self._jesd_params_to_skip_check:
                continue
            current_config[attr] = getattr(self, attr)
        return current_config

    @property
    @abstractmethod
    def converter_type(self) -> str:
        """Type of converter. ADC or DAC.

        Returns:
            str: Type of converter
        """
        raise NotImplementedError

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
