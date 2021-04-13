"""AD9144 high speed DAC clocking model."""
from typing import Dict, List, Union

from docplex.cp.model import integer_var  # type: ignore

from adijif.converters.ad9144_bf import ad9144_bf


def _convert_to_config(
    L: Union[int, float],
    M: Union[int, float],
    F: Union[int, float],
    S: Union[int, float],
    # HD: Union[int, float],
    N: Union[int, float],
    Np: Union[int, float],
    # CS: Union[int, float],
    DualLink: bool,
) -> Dict:
    # return {"L": L, "M": M, "F": F, "S": S, "HD": HD, "N": N, "Np": Np, "CS": CS}
    return {
        "L": L,
        "M": M,
        "F": F,
        "S": S,
        "HD": 1 if F == 1 else 0,
        "Np": Np,
        "CS": 0,
        "DualLink": DualLink,
    }


# IF F==1, HD=1, otherwise 0
quick_configuration_modes = {
    str(0): _convert_to_config(DualLink=False, M=4, L=8, S=1, F=1, N=16, Np=16),
    str(1): _convert_to_config(DualLink=False, M=4, L=8, S=2, F=2, N=16, Np=16),
    str(2): _convert_to_config(DualLink=False, M=4, L=4, S=1, F=2, N=16, Np=16),
    str(3): _convert_to_config(DualLink=False, M=4, L=2, S=1, F=4, N=16, Np=16),
    str(4): _convert_to_config(DualLink=False, M=2, L=4, S=1, F=1, N=16, Np=16),
    str(5): _convert_to_config(DualLink=False, M=2, L=4, S=2, F=2, N=16, Np=16),
    str(6): _convert_to_config(DualLink=False, M=2, L=2, S=1, F=2, N=16, Np=16),
    str(7): _convert_to_config(DualLink=False, M=2, L=1, S=1, F=4, N=16, Np=16),
    # 8 is missing in datasheet
    str(9): _convert_to_config(DualLink=False, M=1, L=2, S=1, F=1, N=16, Np=16),
    str(10): _convert_to_config(DualLink=False, M=1, L=1, S=1, F=2, N=16, Np=16),
}

quick_configuration_modes = {
    **quick_configuration_modes,
    **{
        str(4)
        + "-DL": _convert_to_config(DualLink=False, M=2, L=4, S=1, F=1, N=16, Np=16),
        str(5)
        + "-DL": _convert_to_config(DualLink=False, M=2, L=4, S=2, F=2, N=16, Np=16),
        str(6)
        + "-DL": _convert_to_config(DualLink=False, M=2, L=2, S=1, F=2, N=16, Np=16),
        str(7)
        + "-DL": _convert_to_config(DualLink=False, M=2, L=1, S=1, F=4, N=16, Np=16),
        # 8 is missing in datasheet
        str(9)
        + "-DL": _convert_to_config(DualLink=False, M=1, L=2, S=1, F=1, N=16, Np=16),
        str(10)
        + "-DL": _convert_to_config(DualLink=False, M=1, L=1, S=1, F=2, N=16, Np=16),
    },
}


class ad9144(ad9144_bf):
    """AD9144 high speed DAC model.

    This model supports both direct clock configurations and on-board
    generation

    Clocking: AD9144 has directly clocked DAC that have optional input dividers.
    The sample rate can be determined as follows:

        baseband_sample_rate = (input_clock / input_clock_divider) / datapath_decimation
    """

    name = "AD9144"

    direct_clocking = True
    use_direct_clocking = True
    DualLink = False

    available_jesd_modes = ["jesd204b"]
    K_possible = [4, 8, 12, 16, 20, 24, 28, 32]
    L_possible = [1, 2, 4, 8]
    M_possible = [1, 2, 4, 4]
    N_possible = [*range(7, 16 + 1)]
    Np_possible = [8, 16]
    F_possible = [1, 2, 4, 8, 16]
    CS_possible = [0, 1, 2, 3]
    CF_possible = [0]
    S_possible = [1]  # Not found in DS
    link_min = 3.125e9
    link_max = 12.5e9

    quick_configuration_modes = quick_configuration_modes

    # Input clock requirements
    available_input_clock_dividers = [1, 2, 4, 8]
    input_clock_divider = 1
    available_datapath_interpolation = [1, 2, 4, 8]
    datapath_interpolation = 1

    # Internal limits
    pfd_min = 35e6
    pfd_max = 80e6

    config = {}  # type: ignore

    max_input_clock = 4e9

    def set_quick_configuration_mode(self, mode: str) -> None:
        """Set JESD configuration based on preset mode table. This does not set K or N.

        Args:
            mode (str): Integer of desired mode. See table 26 of datasheet

        Raises:
            Exception: Invalid mode selected
        """
        smode = str(mode)
        if smode not in self.quick_configuration_modes.keys():
            raise Exception("Mode {smode} not among configurations".format(smode))
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
            L=self.L,
            M=self.M,
            F=self.F,
            S=self.S,
            N=self.N,
            Np=self.Np,
            DualLink=self.DualLink,
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
        clk = "ad9144_dac_clock" if self.use_direct_clocking else "ad9144_pll_ref"
        return [clk, "ad9144_sysref"]

    def _pll_config(self) -> Dict:

        dac_clk = self.datapath_interpolation * self.sample_clock
        self.config["dac_clk"] = self._convert_input(dac_clk, "dac_clk")

        if self.solver == "gekko":

            # self.config["ref_div_factor"] = self.model.sos1([1, 2, 4, 8, 16])
            self.config["ref_div_factor_i"] = self.model.Var(
                integer=True, lb=0, ub=4, value=4
            )
            self.config["ref_div_factor"] = self.model.Intermediate(
                2 ** (self.config["ref_div_factor_i"])
            )

            self.config["BCount"] = self.model.Var(integer=True, lb=6, ub=127, value=6)
            self.config["ref_clk"] = self.model.Var(
                integer=True, lb=35e6, ub=1e9, value=35e6
            )
        elif self.solver == "CPLEX":
            self.config["ref_div_factor"] = self._convert_input(
                [1, 2, 4, 8, 16], "ref_div_factor"
            )
            self.config["BCount"] = self._convert_input([*range(6, 128)], "BCount")
            self.config["ref_clk"] = integer_var(int(35e6), int(1e9), name="ref_clock")

        if dac_clk > 2800e6:
            raise Exception("DAC Clock too fast")
        elif dac_clk >= 1500e6:
            self.config["lo_div_mode_p2"] = self._convert_input(2 ** (1 + 1))
        elif dac_clk >= 720e6:
            self.config["lo_div_mode_p2"] = self._convert_input(2 ** (2 + 1))
        elif dac_clk >= 420e6:
            self.config["lo_div_mode_p2"] = self._convert_input(2 ** (3 + 1))
        else:
            raise Exception("DAC Clock too slow")

        if self.solver == "gekko":
            self.config["vco"] = self.model.Intermediate(
                self.config["dac_clk"] * self.config["lo_div_mode_p2"]
            )
        elif self.solver == "CPLEX":
            self.config["vco"] = self.config["dac_clk"] * self.config["lo_div_mode_p2"]
        else:
            raise Exception(f"Unknown solver: {self.solver}")

        self._add_equation(
            [
                self.config["ref_div_factor"] * self.pfd_min < self.config["ref_clk"],
                self.config["ref_div_factor"] * self.pfd_max > self.config["ref_clk"],
                self.config["ref_clk"] * 2 * self.config["BCount"]
                == self.config["dac_clk"] * self.config["ref_div_factor"],
            ]
        )

        return self.config["ref_clk"]

    def get_required_clocks(self) -> List:
        """Generate list required clocks.

        For AD9144 this will contain [converter clock, sysref requirement SOS]

        Returns:
            List: List of dictionaries of solver components
        """
        # possible_sysrefs = []
        # for n in range(1, 20):
        #     r = self.multiframe_clock / (n * n)
        #     if r == int(r) and r > 1e6:
        #         possible_sysrefs.append(r)
        # self.config["sysref"] = self.model.sos1(possible_sysrefs)
        self._check_valid_jesd_mode()
        self.config = {}
        if self.solver == "gekko":
            self.config["lmfc_divisor_sysref"] = self.model.Var(
                integer=True, lb=1, ub=20, value=19
            )
            self.config["sysref"] = self.model.Intermediate(
                self.multiframe_clock
                / (
                    self.config["lmfc_divisor_sysref"]
                    * self.config["lmfc_divisor_sysref"]
                )
            )
        elif self.solver == "CPLEX":
            self.config["lmfc_divisor_sysref"] = self._convert_input([*range(1, 20)])
            self.config["sysref"] = self.multiframe_clock / (
                self.config["lmfc_divisor_sysref"] * self.config["lmfc_divisor_sysref"]
            )

        if self.use_direct_clocking:
            clk = self.sample_clock * self.datapath_interpolation
            # LaneRate = (20 × DataRate × M)/L
            assert self.bit_clock == (20 * self.sample_clock * self.M) / self.L
        else:
            # vco = dac_clk * 2^(LO_DIV_MODE + 1)
            # 6 GHz <= vco <= 12 GHz
            # BCount = floor( dac_clk/(2 * ref_clk/ref_div ) )
            # 5 <= BCount <= 127
            # ref_div = 2^ref_div_mode = 1,2,4,8,16
            clk = self._pll_config()  # type: ignore

        # Objectives
        # self.model.Obj(self.config["sysref"])  # This breaks many searches
        # self.model.Obj(-1*self.config["lmfc_divisor_sysref"])

        return [clk, self.config["sysref"]]
