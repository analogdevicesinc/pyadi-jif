"""System level interface for manage clocks across all devices."""
import os
import shutil  # noqa: F401
from typing import Dict, List, Tuple, Union

import numpy as np

import adijif  # noqa: F401
import adijif.solvers as solvers
from adijif.converters.converter import converter as convc
from adijif.types import range as rangec


class system:
    """System Manager Class.

    Manage requirements from all system components and feed into clock rate
    generation algorithms

    All converters shared a common sysref. This requires that all
        converters have the same multiframe clock (LMFC)
    """

    use_common_sysref = False

    enable_converter_clocks = True
    enable_fpga_clocks = True

    Debug_Solver = False
    solver = "CPLEX"
    solution = None

    def _model_reset(self) -> None:
        if self.solver == "gekko":
            if not solvers.gekko_solver:
                raise Exception("GEKKO Solver not installed")
            model = solvers.GEKKO(remote=False)
        elif self.solver == "CPLEX":
            if not solvers.cplex_solver:
                raise Exception("CPLEX Solver not installed")
            model = solvers.CpoModel()
        else:
            raise Exception(f"Unknown solver {self.solver}")

        self.model = model
        self.clock.model = model
        self.clock.config = {}
        self.fpga.model = model
        self.fpga.config = {}
        if isinstance(self.converter, list):
            for conv in self.converter:
                conv.model = model
                conv.config = {}
        else:
            self.converter.config = {}
            self.converter.model = model

    def __init__(
        self,
        conv: str,
        clk: str,
        fpga: str,
        vcxo: Union[int, rangec],
        solver: str = None,
    ) -> None:
        """Initialize system interface and manage all clocking aspects.

        Args:
            conv (str): Name of converter class
            clk (str): Name of Clock chip class
            fpga (str): Name of FPGA class
            vcxo (int,rangec): Value of fixed VCXO or range allowed
            solver (str): Solver name (gekko, cplex)

        Raises:
            Exception: Unknown solver
            Exception: GEKKO Solver not installed
        """
        if solver:
            self.solver = solver
        if self.solver == "gekko":
            if not solvers.gekko_solver:
                raise Exception("GEKKO Solver not installed")
            model = solvers.GEKKO(remote=False)
        elif self.solver == "CPLEX":
            if not solvers.cplex_solver:
                raise Exception("CPLEX Solver not installed")
            model = solvers.CpoModel()
        else:
            raise Exception(f"Unknown solver {self.solver}")

        self.model = model
        self.vcxo = vcxo
        # FIXME: Do checks

        self.converter: Union[convc, List[convc]] = []
        if isinstance(conv, list):
            for c in conv:
                self.converter.append(
                    eval(f"adijif.{c}(self.model,solver=self.solver)")
                )
        else:
            self.converter: convc = eval(  # type: ignore
                f"adijif.{conv}(self.model,solver=self.solver)"
            )
        self.clock = eval(f"adijif.{clk}(self.model,solver=self.solver)")
        self.fpga = eval(f"adijif.{fpga}(self.model,solver=self.solver)")
        self.vcxo = vcxo

        # TODO: Add these constraints to solver options
        self.configs_to_find = 1
        self.sysref_sample_clock_ratio = 16
        self.sysref_min_div = 4
        self.sysref_max_div = 2 ** 14

        # self.solver_options = [
        #     "minlp_maximum_iterations 1000",  # minlp iterations with integer solution
        #     "minlp_max_iter_with_int_sol 100",  # treat minlp as nlp
        #     "minlp_as_nlp 0",  # nlp sub-problem max iterations
        #     "nlp_maximum_iterations 5000",  # 1 = depth first, 2 = breadth first
        #     "minlp_branch_method 1",  # maximum deviation from whole number
        #     "minlp_integer_tol 0.05",  # covergence tolerance
        #     "minlp_gap_tol 0.01",
        # ]
        self.solver_options = [
            "minlp_maximum_iterations 10000",  # minlp iterations with integer solution
            "minlp_max_iter_with_int_sol 100",  # treat minlp as nlp
            "minlp_as_nlp 0",  # nlp sub-problem max iterations
            "nlp_maximum_iterations 500",  # 1 = depth first, 2 = breadth first
            "minlp_branch_method 1",  # maximum deviation from whole number
            "minlp_integer_tol 0",  # covergence tolerance 0.000001
            "minlp_gap_tol 0.1",
        ]
        # self.solver_options = [
        #     "minlp_maximum_iterations 1000",  # minlp iterations with integer solution
        # ]

    def __del__(self) -> None:
        """Deconstructor: Cleanup system by clearing all leaf objects."""
        self.fpga = []
        if isinstance(self.converter, list):
            for c, _ in enumerate(self.converter):
                del self.converter[c]
        self.converter = []
        self.clock = []

    def _get_configs(self) -> Dict:
        """Collect extracted configurations from all components in system from solver.

        Returns:
            Dict: Dictionary containing all clocking configurations of all components
        """
        cfg = {"clock": self.clock.get_config(self.solution), "converter": []}
        c = self.converter if isinstance(self.converter, list) else [self.converter]
        for conv in c:
            clk_ref = cfg["clock"]["output_clocks"][conv.name + "_fpga_ref_clk"]["rate"]
            cfg["fpga_" + conv.name] = self.fpga.get_config(
                solution=self.solution, converter=conv, fpga_ref=clk_ref
            )
            cfg["converter"].append(conv.name)
        return cfg

    def _filter_sysref(
        self,
        cnv_clocks: List,
        clock_names: List[str],
        convs: List[convc],
    ) -> Tuple[List, List[str]]:
        """Filter sysref clocks to remove duplicate constraints.

        Args:
            cnv_clocks (List): List of clock constraints
            clock_names (List[str]): List of clock names
            convs (List[convc]): List of converter objects

        Returns:
            List,List[str]: Touple with list of filter clocks and names

        Raises:
            Exception: Invalid shared sysref configuration
        """
        cnv_clocks_filters = []
        clock_names_filters = []
        if len(cnv_clocks) > 2 and self.use_common_sysref:
            ref = convs[0].multiframe_clock
            for conv in convs:
                if ref != conv.multiframe_clock:
                    raise Exception(
                        "SYSREF cannot be shared. "
                        + "Converters at different LMFCs."
                        + "\nSet use_common_sysref to False "
                        + "for current rates"
                    )

            for i, clk in enumerate(cnv_clocks):
                # 1,3,5,... are sysrefs. Keep first 1
                if i / 2 == int(i / 2) or i == 1:
                    cnv_clocks_filters.append(clk)
                    clock_names_filters.append(clock_names[i])
        else:
            cnv_clocks_filters = cnv_clocks
            clock_names_filters = clock_names
        return cnv_clocks_filters, clock_names_filters

    def _solve_gekko(self) -> None:
        """Call gekko solver API."""
        # Set up solver
        self.model.solver_options = self.solver_options
        self.model.options.SOLVER = 1  # APOPT solver
        folder = self.model._path
        # self.model.options.SOLVER = 3  # 1 APOPT, 2 BPOPT, 3 IPOPT
        # self.model.options.IMODE = 5   # simultaneous estimation
        try:
            self.model.solve(disp=self.Debug_Solver, debug=True)
        finally:
            if os.path.isdir(folder) and os.path.isfile(
                os.path.join(folder, "apopt.opt")
            ):
                print("DELETE: " + folder)
                # shutil.rmtree(folder)

    def _solve_cplex(self) -> None:
        """Call CPLEX solver API."""
        # Set up solver
        ll = "Normal" if self.Debug_Solver else "Quiet"
        self.solution = self.model.solve(LogVerbosity=ll)
        if not self.solution.is_a_solution:
            raise Exception("No solution found")

    def solve(self) -> Dict:
        """Defined clocking requirements in Solver model and start solvers routine.

        Returns:
            Dict: Dictionary containing all clocking configuration for all components

        Raises:
            Exception: FPGA and Converter disabled
            Exception: Solver invalid
        """
        if not self.enable_converter_clocks and not self.enable_fpga_clocks:
            raise Exception("Converter and/or FPGA clocks must be enabled")

        clock_names: List[str] = []
        config = {}
        if self.enable_converter_clocks:

            convs: List[convc] = (
                self.converter if isinstance(self.converter, list) else [self.converter]
            )

            # Setup clock chip
            self.clock._setup(self.vcxo)
            self.fpga.configs = []  # reset
            serdes_used: float = 0

            for conv in convs:

                serdes_used += conv.L
                if serdes_used > self.fpga.max_serdes_lanes:
                    raise Exception(
                        "Max SERDES lanes exceeded. {} only available".format(
                            self.fpga.max_serdes_lanes
                        )
                    )

                # Check to make sure static configurations are in range
                conv.validate_config()

                # Ask clock chip for converter ref
                config[conv.name + "_ref_clk"] = self.clock._get_clock_constraint(
                    conv.name + "_ref_clk"
                )
                config[conv.name + "_sysref"] = self.clock._get_clock_constraint(
                    conv.name + "_sysref"
                )
                clock_names.append(conv.name + "_ref_clk")
                clock_names.append(conv.name + "_sysref")

                # Setup converter
                clks = conv.get_required_clocks()  # type: ignore
                self.clock._add_equation(config[conv.name + "_ref_clk"] == clks[0])
                self.clock._add_equation(config[conv.name + "_sysref"] == clks[1])

                # Ask clock chip for fpga ref
                config[conv.name + "_fpga_ref_clk"] = self.clock._get_clock_constraint(
                    "xilinx"
                )
                clock_names.append(conv.name + "_fpga_ref_clk")

                # Setup fpga
                self.fpga.get_required_clocks(conv, config[conv.name + "_fpga_ref_clk"])

            self.clock._clk_names = clock_names

        # Set up solver
        if self.solver == "gekko":
            self._solve_gekko()
        elif self.solver == "CPLEX":
            self._solve_cplex()
        else:
            raise Exception("Unknown solver {}".format(self.solver))

        # Organize data
        return self._get_configs()

    def determine_clocks(self) -> List:
        """Defined clocking requirements and search over all possible dividers.

        Raises:
            Exception: No valid configurations found

        Returns:
            List: List of valid configurations for all clocking components
        """
        # Extract dependent rates from converter
        rates = self.converter.device_clock_available()  # type: ignore

        out = []
        for rate in rates:
            rate = np.array(rate, dtype=int)

            # Search across clock chip settings for supported modes
            clk_configs = self.clock.find_dividers(
                self.vcxo, rate, find=self.configs_to_find
            )

            # Find FPGA PLL settings that meet Lane rate
            # requirements based on available reference clocks
            valid_clock_configs = []
            for clk_config in clk_configs:
                print("clk_config", clk_config)
                refs = self.clock.list_available_references(clk_config)
                for ref in refs:
                    try:
                        info = self.fpga.determine_pll(
                            self.converter.bit_clock, ref  # type: ignore
                        )
                        break
                    except BaseException:
                        ref = False
                        continue

                if ref:
                    clk_config["fpga_pll_config"] = info
                    valid_clock_configs.append(clk_config)

            if not valid_clock_configs:
                continue
                # raise Exception("No valid configurations possible for FPGA")

            # Check available output dividers for sysref required
            complete_clock_configs = []
            for clk_config in valid_clock_configs:
                refs = self.clock.list_available_references(clk_config)
                try:
                    sysref_rate = self._determine_sysref(refs)
                    clk_config["sysref_rate"] = sysref_rate
                    complete_clock_configs.append(clk_config)
                except BaseException:
                    continue

            if not complete_clock_configs:
                continue
                # raise Exception("No valid configurations possible for sysref")
            out.append({"Converter": rate, "ClockChip": complete_clock_configs})

        if not out:
            raise Exception("No valid configurations possible converter sample rate")

        return out

    def _determine_sysref(
        self, refs: Union[List[int], List[float]]
    ) -> Union[int, float]:
        """Find possible sysrefs based on required clocks and JESD configs.

        Args:
            refs (List[int],List[float]): List of system device clocks

        Raises:
            Exception: No valid configurations found

        Returns:
            int/float: Sysref rate in samples per second
        """
        lmfc = self.converter.multiframe_clock  # type: ignore
        div = self.sysref_min_div

        while div < self.sysref_max_div:
            sysref_rate = lmfc / div
            if sysref_rate in refs:
                # vco_div = cfs[0]['vco']/sysref/cfs[0]['m1']
                # print("FOUND")
                break
            else:
                sysref_rate = False
            div *= 2

        if not sysref_rate:
            raise Exception("No possible sysref found")

        return sysref_rate
