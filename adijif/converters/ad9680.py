"""AD9680 high speed ADC clocking model."""
from typing import Any, Dict, List, Union

from adijif.converters.ad9680_bf import ad9680_bf


def _convert_to_config(
    L: Union[int, float],
    M: Union[int, float],
    F: Union[int, float],
    S: Union[int, float],
    HD: Union[int, float],
    N: Union[int, float],
    Np: Union[int, float],
    CS: Union[int, float],
) -> Dict:
    # return {"L": L, "M": M, "F": F, "S": S, "HD": HD, "N": N, "Np": Np, "CS": CS}
    return {"L": L, "M": M, "F": F, "S": S, "HD": HD, "Np": Np}


quick_configuration_modes = {
    # M = 1
    str(0x01): _convert_to_config(1, 1, 2, 1, 0, -1, 16, -1),
    str(0x40): _convert_to_config(2, 1, 1, 1, 1, -1, 16, -1),
    str(0x41): _convert_to_config(2, 1, 2, 2, 0, -1, 16, -1),
    str(0x80): _convert_to_config(4, 1, 1, 2, 1, -1, 16, -1),
    str(0x81): _convert_to_config(4, 1, 2, 4, 0, -1, 16, -1),
    # M = 2
    str(0x0A): _convert_to_config(1, 2, 4, 1, 0, -1, 16, -1),
    str(0x49): _convert_to_config(2, 2, 2, 1, 0, -1, 16, -1),
    str(0x88): _convert_to_config(4, 2, 1, 1, 1, -1, 16, -1),
    str(0x89): _convert_to_config(4, 2, 2, 2, 0, -1, 16, -1),
    # M = 4
    str(0x13): _convert_to_config(1, 4, 8, 1, 0, -1, 16, -1),
    str(0x52): _convert_to_config(2, 4, 4, 1, 0, -1, 16, -1),
    str(0x91): _convert_to_config(4, 4, 2, 1, 0, -1, 16, -1),
    # M = 8
    str(0x13): _convert_to_config(1, 8, 16, 1, 0, -1, 16, -1),
    str(0x52): _convert_to_config(2, 8, 8, 1, 0, -1, 16, -1),
    str(0x91): _convert_to_config(4, 8, 4, 1, 0, -1, 16, -1),
}


class ad9680(ad9680_bf):
    """AD9680 high speed ADC model.

    This model supports direct clock configurations

    Clocking: AD9680 has directly clocked ADC that have optional input dividers.
    The sample rate can be determined as follows:

        baseband_sample_rate = (input_clock / input_clock_divider) / datapath_decimation
    """

    name = "AD9680"

    _jesd_params_to_skip_check = ["DualLink", "CS", "N", "HD"]

    direct_clocking = True
    available_jesd_modes = ["jesd204b"]
    K_available = [4, 8, 12, 16, 20, 24, 28, 32]
    L_available = [1, 2, 4]
    M_available = [1, 2, 4, 8]
    N_available = [*range(7, 16)]
    Np_available = [8, 16]
    F_available = [1, 2, 4, 8, 16]
    CS_available = [0, 1, 2, 3]
    CF_available = [0]
    S_available = [1, 2, 4]
    converter_clock_min = 300e6
    converter_clock_max = 1.25e9
    bit_clock_min_available = {"jesd204b": 3.125e9}
    bit_clock_max_available = {"jesd204b": 12.5e9}
    sample_clock_min = 300e6
    sample_clock_max = 1250e6
    decimation_available = [1, 2, 4, 8, 16]
    decimation = 1

    quick_configuration_modes = quick_configuration_modes

    # Input clock requirements
    available_input_clock_dividers = [1, 2, 4, 8]
    input_clock_divider = 1

    """ Clocking
        AD9680 has directly clocked ADCs that have optional input dividers.
        The sample rate can be determined as follows:

        baseband_sample_rate = (input_clock / input_clock_divider) / datapath_decimation
    """
    max_input_clock = 4e9

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize AD9680 class.

        Objects will default to mode 0x88 with 1e9 sample_clock.

        Args:
            *args (Any): Pass through arguments
            **kwargs (Any): Pass through keyword arguments
        """
        # Set default mode
        self.set_quick_configuration_mode(str(0x88))
        self.sample_clock = 1e9
        super().__init__(*args, **kwargs)

    def set_quick_configuration_mode(self, mode: Union[int, str]) -> None:
        """Set JESD configuration based on preset mode table. This does not set K or N.

        Args:
            mode (int,str): Integer of desired mode. See table 26 of datasheet

        Raises:
            Exception: Invalid mode selected
        """
        smode = str(mode)
        if smode not in self.quick_configuration_modes.keys():
            raise Exception("Mode {} not among configurations".format(smode))
        for jparam in self.quick_configuration_modes[smode]:
            if jparam == "S":
                continue
            setattr(self, jparam, self.quick_configuration_modes[smode][jparam])

    def _check_valid_jesd_mode(self) -> None:
        """Verify current JESD configuration for part is valid.

        Raises:
            Exception: Invalid JESD configuration
        """
        self._check_jesd_config()
        current_config = _convert_to_config(
            self.L, self.M, self.F, self.S, self.HD, self.N, self.Np, self.CS
        )
        for mode in self.quick_configuration_modes.keys():
            if current_config == quick_configuration_modes[mode]:
                return
        raise Exception("Invalid JESD configuration")

    def get_required_clock_names(self) -> List[str]:
        """Get list of strings of names of requested clocks.

        This list of names is for the clocks defined by get_required_clocks

        Returns:
            List[str]: List of strings of clock names in order
        """
        return ["ad9680_adc_clock", "ad9680_sysref"]

    def get_required_clocks(self) -> List:
        """Generate list required clocks.

        For AD9680 this will contain [converter clock, sysref requirement SOS]

        Returns:
            List: List of solver variables, equations, and constants
        """
        self._check_valid_jesd_mode()
        self._check_valid_internal_configuration()
        # possible_sysrefs = []
        # for n in range(1, 10):
        #     r = self.multiframe_clock / (n * n)
        #     if r == int(r) and r > 1e6:
        #         possible_sysrefs.append(r)
        # self.config = {"sysref": self.model.sos1(possible_sysrefs)}

        self.config = {}
        self.config["lmfc_divisor_sysref"] = self._convert_input(
            [*range(1, 18)], default=18, name="AD9680_lmfc_divisor_sysref"
        )

        self.config["lmfc_divisor_sysref_squared"] = self._add_intermediate(
            self.config["lmfc_divisor_sysref"] * self.config["lmfc_divisor_sysref"]
        )
        self.config["sysref"] = self._add_intermediate(
            self.multiframe_clock / self.config["lmfc_divisor_sysref_squared"]
        )

        # Objectives
        # self.model.Obj(self.config["sysref"])  # This breaks many searches

        return [self.sample_clock, self.config["sysref"]]
