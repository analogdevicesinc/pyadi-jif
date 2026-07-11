"""System level interface for manage clocks across all devices."""

import os
import shutil  # noqa: F401
from typing import Callable, Dict, List, Optional, Tuple, Union

import numpy as np

import adijif.solvers as solvers
from adijif.clocks.clock import clock as clockc
from adijif.converters.converter import converter as convc
from adijif.optimization import Objective, apply_objectives, collect_objectives
from adijif.plls.pll import pll as pllc
from adijif.registry import get_component_class
from adijif.sys.clocks_bundle import ClocksBundle
from adijif.sys.s_plls import SystemPLL
from adijif.system_draw import system_draw as system_draw
from adijif.types import arb_source as arb_sourcec
from adijif.types import range as rangec


class system(SystemPLL, system_draw):
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
    _solution = None

    _plls = []
    _initialized = False
    _last_clocks: Optional[ClocksBundle] = None

    @property
    def plls(self) -> List[pllc]:
        """External PLLs used to drive converters.

        Returns:
            List: List of PLL objects
        """
        return self._plls

    def add_objective(
        self,
        expr,
        *,
        sense: str = "min",
        tier: int = 0,
        weight: float = 1.0,
        name: str = None,
    ) -> None:
        """Register a system-level optimization objective.

        Layered on top of the built-in objectives that components register
        during ``initialize``. Persists across re-solves.

        Args:
            expr: Solver expression to optimize.
            sense: ``"min"`` or ``"max"``.
            tier: Lexicographic priority. Lower tier = higher priority.
            weight: Within-tier multiplier when summing.
            name: Optional debug identifier.
        """
        self._user_objectives.append(
            Objective(
                expr=expr, sense=sense, tier=tier, weight=weight, name=name
            )
        )

    def list_objectives(self) -> List[Objective]:
        """Return all currently-registered objectives across components.

        Useful for debugging which optimizations are active before solving.
        Must be called after ``initialize`` (so components have populated
        their ``_objectives`` lists).

        Returns:
            List of Objective instances with ``component`` set to the
            originating class name (or ``"user"`` for system-level).
        """
        return collect_objectives(self)

    def add_pll_inline(self, pll_name: str, clk: clockc, cnv: convc) -> None:
        """Add External PLL to system between clock chip and converter.

        Args:
            pll_name (str): Name of PLL class
            clk (clockc): Clock chip reference
            cnv (convc): Converter reference
        """
        pll = get_component_class("pll", pll_name)(
            self.model, solver=self.solver
        )
        self._plls.append(pll)
        pll._connected_to_output = cnv.name
        pll._ref = clk

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
        self.clock._reset_config()
        self.fpga.model = model
        self.fpga._reset_config()
        if isinstance(self.converter, list):
            for conv in self.converter:
                conv.model = model
                conv._reset_config()
        else:
            self.converter._reset_config()
            self.converter.model = model

        self._plls = []
        self._initialized = False
        self._last_clocks = None

    def __init__(
        self,
        conv: Union[str, List[str]],
        clk: str,
        fpga: str,
        vcxo: Union[int, float, rangec, arb_sourcec],
        solver: str = None,
    ) -> None:
        """Initialize system interface and manage all clocking aspects.

        Args:
            conv (str): Name of converter class
            clk (str): Name of Clock chip class
            fpga (str): Name of FPGA class
            vcxo (int,float,rangec,arb_sourcec): Fixed VCXO value, range, or arb_source
            solver (str): Solver name (gekko, cplex)

        Raises:
            Exception: Unknown solver
            Exception: GEKKO Solver not installed
            Exception: arb_source requires CPLEX solver
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
        self._plls = []
        self._plls_sysref = []
        self._initialized = False
        self._last_clocks = None
        self._user_objectives: List[Objective] = []

        # Validate arb_source compatibility with solver
        if isinstance(vcxo, arb_sourcec) and self.solver == "gekko":
            raise Exception(
                "arb_source type requires CPLEX solver. "
                "Either use solver='CPLEX' or use adijif.types.range "
                "for discrete values."
            )

        # FIXME: Do checks

        self.converter: Union[convc, List[convc]] = []
        if isinstance(conv, list):
            for c in conv:
                converter_class = get_component_class("converter", c)
                self.converter.append(
                    converter_class(self.model, solver=self.solver)
                )
        else:
            converter_class = get_component_class("converter", conv)
            self.converter: convc = converter_class(
                self.model, solver=self.solver
            )
        self.clock = get_component_class("clock", clk)(
            self.model, solver=self.solver
        )
        self.fpga = get_component_class("fpga", fpga)(
            self.model, solver=self.solver
        )
        self.vcxo = vcxo

        # TODO: Add these constraints to solver options
        self.configs_to_find = 1
        self.sysref_sample_clock_ratio = 16
        self.sysref_min_div = 4
        self.sysref_max_div = 2**14

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
        converter = getattr(self, "converter", None)
        if isinstance(converter, list):
            converter.clear()
        self.converter = []
        self.clock = []

    def _get_configs(self) -> Dict:
        """Collect extracted configurations from all components in system from solver.

        Returns:
            Dict: Dictionary containing all clocking configurations of all components
        """
        cfg = {"clock": self.clock.get_config(self._solution), "converter": []}

        c = (
            self.converter
            if isinstance(self.converter, list)
            else [self.converter]
        )
        for conv in c:
            if conv._nested:
                names = conv._nested
                for name in names:
                    clk_ref = cfg["clock"]["output_clocks"][
                        f"{self.fpga.name}_{name}_ref_clk"
                    ]["rate"]
                    cfg["fpga_" + name] = self.fpga.get_config(
                        solution=self._solution,
                        converter=getattr(conv, name),
                        fpga_ref=clk_ref,
                    )
                    cfg["converter"] = conv.get_config(self._solution)  # type: ignore
                    cfg["jesd_" + name] = getattr(conv, name).get_jesd_config(
                        self._solution
                    )
                    if getattr(conv, name).datapath:
                        cfg["datapath_" + name] = getattr(
                            conv, name
                        ).datapath.get_config()
            else:
                clk_ref = cfg["clock"]["output_clocks"][
                    f"{self.fpga.name}_{conv.name}_ref_clk"
                ]["rate"]
                cfg["fpga_" + conv.name] = self.fpga.get_config(
                    solution=self._solution, converter=conv, fpga_ref=clk_ref
                )
                cfg["converter_" + conv.name] = conv.get_config(self._solution)
                cfg["jesd_" + conv.name] = conv.get_jesd_config(self._solution)

        # Collect PLLs driving converter sampling clock configs
        for pll in self._plls:
            cfg["clock_ext_pll_" + pll.name] = pll.get_config(self._solution)

        # Collect PLLs driving sysref clocks configurations.
        for pll in self._plls_sysref:
            cfg["clock_ext_pll_sysref_" + pll.name] = pll.get_config(
                self._solution
            )
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
            self.model.cleanup()
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
        wl = 0  # WarningLevel 0-off 3-all warnings
        # self.model.export_model()
        self._solution = self.model.solve(LogVerbosity=ll, WarningLevel=wl)
        # self._solution.print_solution()
        if not self._solution.is_solution():
            raise Exception("No solution found")

    def solve(
        self,
        out_clock_constraints: dict = None,
        constrain: Optional[Callable[[ClocksBundle], None]] = None,
    ) -> Dict:
        """Define clocking requirements and run the active solver.

        For richer constraints than equality (range bounds, rate equality
        between two clocks, allowed-value lists), pass a ``constrain`` callback
        that receives the :class:`ClocksBundle` returned by
        :meth:`initialize`. Or call :meth:`initialize` yourself, add
        constraints, then call :meth:`do_solve`.

        Args:
            out_clock_constraints: Optional dict of exact target rates keyed by
                clock name (the keys exposed by :meth:`initialize`). Values may
                be a number or ``{"rate": number}``.
            constrain: Optional callback invoked with the
                :class:`ClocksBundle` after constraints have been wired but
                before the solver runs. Use it to add custom range / equality
                / OR constraints via ``clocks.constrain(...)`` or by passing
                solver expressions directly to ``self.model``.

        Returns:
            Dict: Dictionary containing all clocking configuration for all components
        """
        if not self._initialized:
            clocks = self.initialize(out_clock_constraints)
        else:
            clocks = self._last_clocks
            if out_clock_constraints:
                self._apply_out_clock_constraints(clocks, out_clock_constraints)
        if constrain is not None:
            constrain(clocks)
        return self.do_solve()

    def _apply_out_clock_constraints(
        self, clocks: ClocksBundle, out_clock_constraints: dict
    ) -> None:
        """Apply equality constraints from ``out_clock_constraints`` to clocks.

        Accepted value forms per key:
        - number (float/int): treated as a target rate.
        - dict with ``"rate"`` key: target rate.

        Unknown clock names are skipped with a printed warning. Unknown value
        types are skipped with a printed warning. This preserves the
        pre-existing behavior of the ``out_clock_constraints`` kwarg.
        """
        for occ in out_clock_constraints:
            if occ in clocks.keys():
                if isinstance(out_clock_constraints[occ], dict):
                    d = out_clock_constraints[occ]
                    if "rate" in d:
                        self.clock._add_equation([clocks[occ] == d["rate"]])
                    else:
                        print(f"Input constraint {occ} ignored. Bad type")
                elif type(out_clock_constraints[occ]) in [float, int]:
                    self.clock._add_equation(
                        [clocks[occ] == out_clock_constraints[occ]]
                    )
                else:
                    print(f"Input constraint {occ} ignored. Bad type")
            else:
                print(f"Input constraint {occ} not used")

    def initialize(self, out_clock_constraints: dict = None) -> ClocksBundle:
        """Wire all inter-component clock constraints into the solver model.

        Returns a :class:`ClocksBundle` (a dict subclass) mapping each
        inter-component clock name to the solver expression that represents
        its rate. Use the bundle to add custom constraints before calling
        :meth:`do_solve`. See :class:`ClocksBundle` for the canonical clock
        names and :meth:`ClocksBundle.constrain` for the helper API.

        Calling this method a second time without first calling
        :meth:`_model_reset` will not re-wire constraints; the cached bundle
        from the first call is returned. Use :meth:`solve` instead if you
        want a single end-to-end call.

        Args:
            out_clock_constraints: Dict of exact target rates of generated
                clocks. Must be dict of values or dict of dicts that contain
                a ``rate`` field.

        Returns:
            ClocksBundle: Mapping of clock name to solver expression for all
            clocks that flow between high-level components.

        Raises:
            Exception: FPGA and Converter disabled
        """
        if self._initialized and self._last_clocks is not None:
            if out_clock_constraints:
                self._apply_out_clock_constraints(
                    self._last_clocks, out_clock_constraints
                )
            return self._last_clocks

        if not self.enable_converter_clocks and not self.enable_fpga_clocks:
            raise Exception("Converter and/or FPGA clocks must be enabled")

        # Reset per-component objective accumulators so re-solving a system
        # is idempotent. User objectives registered via system.add_objective
        # persist across solves.
        self.fpga._objectives = []
        self.clock._objectives = []
        for pll in self._plls + self._plls_sysref:
            pll._objectives = []
        convs_iter = (
            self.converter
            if isinstance(self.converter, list)
            else [self.converter]
        )
        for conv in convs_iter:
            conv._objectives = []
        self._objectives = []

        clock_names: List[str] = []
        config = {}
        if self.enable_converter_clocks:
            convs: List[convc] = (
                self.converter
                if isinstance(self.converter, list)
                else [self.converter]
            )

            # Setup clock chip
            self.clock.setup_constraints(self.vcxo)

            # Initialize loop variables for clock constraints
            self.fpga.configs = []  # reset
            serdes_used_tx: int = 0
            serdes_used_rx: int = 0
            sys_refs = []  # DEBUG ONLY
            sys_ref_names = []  # DEBUG ONLY

            # Setup external sysref PLLs
            for pll in self._plls_sysref:
                if isinstance(pll._ref, clockc):
                    # Get reference clock for PLL from clock chip
                    config, clock_names = self._get_ref_clock(
                        pll, config, clock_names
                    )
                    pll.setup_constraints(config[pll.name + "_ref_clk"])
                else:  # Assume its a int or float constant or arb_source
                    pll.setup_constraints(pll._ref)
                # Connect BSYNC reference if applicable
                if hasattr(pll, "_bsync_reference") and pll._bsync_reference:
                    if isinstance(pll._bsync_reference, clockc):
                        # Request a clock for BSYNC reference from clock chip
                        # THIS IS NOT THE REFERENCE FOR THE SYSREF PLL ITSELF
                        config, clock_names = self._get_ref_clock_bsync(
                            pll, config, clock_names
                        )
                        pll._setup_bsync_reference(
                            config[pll.name + "_bsync_reference"]
                        )
                    else:  # Assume its a int or float constant or arb_source
                        pll._setup_bsync_reference(pll._bsync_reference)

            for conv in convs:
                if conv._nested:  # MxFE, Transceivers
                    for name in conv._nested:
                        ctype = getattr(conv, name).converter_type.lower()
                        if ctype == "adc":
                            serdes_used_rx += getattr(conv, name).L
                        elif ctype == "dac":
                            serdes_used_tx += getattr(conv, name).L
                        else:
                            raise Exception(f"Unknown converter type {ctype}")
                else:
                    ctype = conv.converter_type.lower()
                    if ctype == "adc":
                        serdes_used_rx += conv.L
                    elif ctype == "dac":
                        serdes_used_tx += conv.L
                    else:
                        raise Exception(f"Unknown converter type: {ctype}")

                if (
                    serdes_used_rx > self.fpga.max_serdes_lanes
                    or serdes_used_tx > self.fpga.max_serdes_lanes
                ):
                    raise Exception(
                        "Max SERDES lanes exceeded. {} only available".format(
                            self.fpga.max_serdes_lanes
                        )
                    )

                # Check to make sure static configurations are in range
                conv.validate_config()

                # Check if we are using the same converter name
                if conv.name + "_ref_clk" in config:
                    raise Exception("Duplicate converter names found")

                # Setup converter
                clks = conv.get_required_clocks()  # type: ignore
                if not conv._nested:
                    assert len(clks) == 2, "Converter must have 2 clocks"

                # Check if converter uses external PLL
                uses_external_pll_clock_source = False
                for pll in self._plls:
                    if pll._connected_to_output == conv.name:
                        uses_external_pll_clock_source = True
                        # Give clock chip output as PLL's reference
                        # TODO: Check if this is handled somewhere else

                        if isinstance(pll._ref, clockc):
                            # Ask clock chip for PLL reference clock
                            config, clock_names = self._get_ref_clock(
                                pll, config, clock_names
                            )
                            pll.setup_constraints(config[pll.name + "_ref_clk"])

                        else:
                            assert isinstance(
                                pll._ref, (int, float, rangec, arb_sourcec)
                            ), (
                                "PLL reference must be clock object, constant, range, or arb_source"
                            )
                            pll.setup_constraints(pll._ref)

                        # Give PLL's output as converter's reference
                        config[conv.name + "_ref_clk_from_ext_pll"] = (
                            pll.request_clock_constraint(
                                conv.name + "_ref_clk_from_ext_pll"
                            )
                        )
                        self.clock._add_equation(
                            config[conv.name + "_ref_clk_from_ext_pll"]
                            == clks[0]
                        )

                if not uses_external_pll_clock_source:
                    # Connect clock chip to converter as clock source
                    # for direct clocking or converter PLL source
                    config, clock_names = self._get_ref_clock(
                        conv, config, clock_names
                    )
                    self.clock._add_equation(
                        config[conv.name + "_ref_clk"] == clks[0]
                    )

                # Setup sysref clocks (clock-chip or external sysref PLL).
                # Must run regardless of whether converter ref clk uses an external PLL.
                config, sys_ref_names = self._get_sysref_clock(
                    conv, config, sys_ref_names
                )

                # Converter sysref (handles both clock-chip and external PLL paths)
                sys_refs = self._apply_sysref_constraint(
                    conv, clks, config, sys_refs
                )

                # Determine if separate device clock / link clock output is needed
                need_separate_link_clock = True  # Let solver decide

                # Ask clock chip for fpga ref
                config, clock_names = self._get_ref_clock_fpga(
                    conv, config, clock_names, need_separate_link_clock
                )

                # Setup fpga
                if conv._nested:
                    names = conv._nested
                    for name in names:
                        if need_separate_link_clock:
                            self.fpga.get_required_clocks(
                                getattr(conv, name),
                                config[name + "_fpga_ref_clk"],
                                config[name + "_fpga_device_clk"],
                            )
                        else:
                            self.fpga.get_required_clocks(
                                getattr(conv, name),
                                config[name + "_fpga_ref_clk"],
                            )
                else:
                    if need_separate_link_clock:
                        self.fpga.get_required_clocks(
                            conv,
                            config[conv.name + "_fpga_ref_clk"],
                            config[conv.name + "_fpga_device_clk"],
                        )
                    else:
                        self.fpga.get_required_clocks(
                            conv, config[conv.name + "_fpga_ref_clk"]
                        )

            # self.clock._clk_names = clock_names
            # FIXME: THIS IS TEMP HACK TO TEST
            # if self.plls_sysref:
            #     self._plls_sysref[0]._clk_names = sys_ref_names

            apply_objectives(self.model, self.solver, collect_objectives(self))

        clocks = ClocksBundle(config, owner=self)

        # Add user explicit constraints
        if out_clock_constraints:
            self._apply_out_clock_constraints(clocks, out_clock_constraints)

        self._last_clocks = clocks
        self._initialized = True
        return clocks

    def do_solve(self) -> Dict:
        """Solve actual solver on model which has been fully configured.

        Returns:
            Dict: Dictionary containing all clocking configuration for all components

        Raises:
            Exception: Solver invalid
        """
        # Call solvers
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
                refs = self.clock.list_available_references(clk_config)
                for ref in refs:
                    try:
                        info = self.fpga.determine_pll(
                            self.converter.bit_clock,
                            ref,  # type: ignore
                        )
                        break
                    except:  # noqa: B036, B001
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
                except:  # noqa: B036, B001, S112
                    continue

            if not complete_clock_configs:
                continue
                # raise Exception("No valid configurations possible for sysref")
            out.append({"Converter": rate, "ClockChip": complete_clock_configs})

        if not out:
            raise Exception(
                "No valid configurations possible converter sample rate"
            )

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
