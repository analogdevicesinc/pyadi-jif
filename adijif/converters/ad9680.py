"""AD9680 high speed ADC clocking model."""

from typing import Any, Dict, List, Union

from adijif.converters.ad9680_bf import ad9680_bf

from ..solvers import CpoSolveResult  # noqa: I202
from .ad9680_draw import ad9680_draw  # noqa: I202


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
    return {
        "L": L,
        "M": M,
        "F": F,
        "S": S,
        "HD": HD,
        "Np": Np,
        "jesd_class": "jesd204b",
    }


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
    str(0x1C): _convert_to_config(1, 8, 16, 1, 0, -1, 16, -1),
    str(0x5B): _convert_to_config(2, 8, 8, 1, 0, -1, 16, -1),
    str(0x9A): _convert_to_config(4, 8, 4, 1, 0, -1, 16, -1),
}


class ad9680(ad9680_draw, ad9680_bf):
    """AD9680 high speed ADC model.

    This model supports direct clock configurations

    Clocking: AD9680 has directly clocked ADC that have optional input dividers.
    The sample rate can be determined as follows:

        baseband_sample_rate = (input_clock / input_clock_divider) / datapath_decimation
    """

    name = "AD9680"
    converter_type = "ADC"

    # JESD parameters
    _jesd_params_to_skip_check = ["DualLink", "CS", "N", "HD"]
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

    # Clock constraints
    clocking_option_available = ["direct"]
    _clocking_option = "direct"
    converter_clock_min = 300e6
    converter_clock_max = 1.25e9
    bit_clock_min_available = {"jesd204b": 3.125e9}
    bit_clock_max_available = {"jesd204b": 12.5e9}
    sample_clock_min = 300e6
    sample_clock_max = 1250e6
    decimation_available = [1, 2, 4, 8, 16]
    _decimation = 1
    _lmfc_sys_divisor = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    quick_configuration_modes = {"jesd204b": quick_configuration_modes}

    # Input clock requirements
    input_clock_divider_available = [1, 2, 4, 8]  # FIXME
    input_clock_divider = 1  # FIXME
    input_clock_max = 4e9  # FIXME

    """ Clocking
        AD9680 has directly clocked ADCs that have optional input dividers.
        The sample rate can be determined as follows:

        baseband_sample_rate = (input_clock / input_clock_divider) / datapath_decimation
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize AD9680 class.

        Objects will default to mode 0x88 with 1e9 sample_clock.

        Args:
            *args (Any): Pass through arguments
            **kwargs (Any): Pass through keyword arguments
        """
        # Set default mode
        self.set_quick_configuration_mode(str(0x88))
        self.K = 32
        self.sample_clock = 1e9
        super().__init__(*args, **kwargs)
        self._init_diagram()

    def _check_valid_jesd_mode(self) -> str:
        """Verify current JESD configuration for part is valid.

        Returns:
            str: Current JESD mode
        """
        if self.F == 1:
            assert self.K in [20, 24, 28, 32], "Invalid K value for F=1"
        if self.F == 2:
            assert self.K in [12, 16, 20, 24, 28, 32], "Invalid K value for F=1"
        if self.F == 4:
            assert self.K in [8, 12, 16, 20, 24, 28, 32], "Invalid K value for F=1"
        if self.F in [8, 16]:
            assert self.K in [4, 8, 12, 16, 20, 24, 28, 32], "Invalid K value for F=1"

        return super()._check_valid_jesd_mode()

    def get_config(self, solution: CpoSolveResult = None) -> Dict:
        """Extract configurations from solver results.

        Collect internal converter configuration and output clock definitions
        leading to connected devices (clock chips, FPGAs)

        Args:
            solution (CpoSolveResult): CPlex solution. Only needed for CPlex solver

        Returns:
            Dict: Dictionary of clocking rates and dividers for configuration
        """
        if solution:
            self._saved_solution = solution
        return {"clocking_option": self.clocking_option, "decimation": self.decimation}

    def get_required_clock_names(self) -> List[str]:
        """Get list of strings of names of requested clocks.

        This list of names is for the clocks defined by get_required_clocks

        Returns:
            List[str]: List of strings of clock names in order
        """
        return ["AD9680_ref_clk", "AD9680_sysref"]

    def get_required_clocks(self) -> List:
        """Generate list required clocks.

        For AD9680 this will contain [converter clock, sysref requirement SOS]

        Returns:
            List: List of solver variables, equations, and constants
        """
        # possible_sysrefs = []
        # for n in range(1, 10):
        #     r = self.multiframe_clock / (n * n)
        #     if r == int(r) and r > 1e6:
        #         possible_sysrefs.append(r)
        # self.config = {"sysref": self.model.sos1(possible_sysrefs)}

        self.config = {}
        self.config["lmfc_divisor_sysref"] = self._convert_input(
            self._lmfc_sys_divisor,
            default=self._lmfc_sys_divisor[-1],
            name="AD9680_lmfc_divisor_sysref",
        )

        self.config["lmfc_divisor_sysref_squared"] = self._add_intermediate(
            self.config["lmfc_divisor_sysref"] * self.config["lmfc_divisor_sysref"]
        )
        self.config["sysref"] = self._add_intermediate(
            self.multiframe_clock / self.config["lmfc_divisor_sysref_squared"]
        )

        # Objectives
        # self.model.Obj(self.config["sysref"])  # This breaks many searches

        return [self.converter_clock, self.config["sysref"]]
