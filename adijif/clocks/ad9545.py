"""AD9545 clock chip model."""

from typing import Dict, List

import docplex.cp.catalog as ctg
import docplex.cp.expression as exp
import docplex.cp.modeler as mod

from adijif.clocks.clock import clock
from adijif.solvers import CpoSolveResult


class ad9545(clock):
    """AD9545 clock chip model.

    Currently this model supports only the internal zero delay mode

    PLL_in_rate_0 = input_ref_0 / r0
    PLL_in_rate_1 = input_ref_1 / r1
    PLL_in_rate_2 = input_ref_2 / r2
    PLL_in_rate_3 = input_ref_3 / r3

    PLL_in_rate_0 < PLL_in_max
    PLL_in_rate_1 < PLL_in_max
    PLL_in_rate_2 < PLL_in_max
    PLL_in_rate_3 < PLL_in_max

    PLL0_rate = n0_profile_0 * PLL_in_rate_0
    PLL0_rate = n0_profile_1 * PLL_in_rate_1
    PLL0_rate = n0_profile_2 * PLL_in_rate_2
    PLL0_rate = n0_profile_3 * PLL_in_rate_3

    out_rate_0 = PLL0_rate / q0
    out_rate_1 = PLL0_rate / q1
    ...
    out_rate_5 = PLL0_rate / q5
    """

    # Limits
    """ Internal limits """
    PLL_out_min = [1200e6, 1600e6]
    PLL_out_max = [1600e6, 2000e6]

    PLL_in_min = 1
    PLL_in_max = 200000

    """ Output dividers limits

        Value is programmed on 32 bits but
        2 GHz is the maximum PLL output that feeds
        directly to the output dividers.
    """
    Q_max = 2000000000
    Q_min = 1

    """ Input dividers limits

        Value is programmed on 32 bits but
        750 MHz is the maximum input frequency anyway.
    """
    R_max = 750000000
    R_min = 1

    """ PLL N dividers limits

        Value is programmed on 32 bits.

        There are constraints on the input and output frequency.
        This places lower and upper bounds on N too.

        Maximum input frequency is 200 kHz.
    """
    N_max = 2000000000
    N_min = 6000

    PLL_used = [False, False]

    avoid_min_max_PLL_rates = True
    minimize_input_dividers = True

    config = {
        "r0": 0,
        "r1": 0,
        "r2": 0,
        "r3": 0,
        "PLL0": {},
        "PLL1": {},
        "q0": 0,
        "q1": 0,
        "q2": 0,
        "q3": 0,
        "q4": 0,
        "q5": 0,
        "q6": 0,
        "q7": 0,
        "q8": 0,
        "q9": 0,
    }

    def list_available_references(self) -> List[int]:
        """List available references for a given divider set."""
        return [self.ref0, self.ref1, self.ref2, self.ref3]

    def find_dividers(self) -> None:
        """Find dividers for a given input reference.

        Not implemented for this model.

        Raises:
            NotImplementedError: Always
        """
        raise NotImplementedError

    def get_config(self, solution: CpoSolveResult = None) -> Dict:
        """Extract configurations from solver results.

        Collect internal clock chip configuration and output clock definitions
        leading to connected devices (converters, FPGAs)

        Args:
            solution (CpoSolveResult): CPlex solution. Only needed for CPlex solver

        Returns:
            Dict: Dictionary of clocking rates and dividers for configuration
        """
        if solution:
            self.solution = solution

        config: Dict = {
            "PLL0": {},
            "PLL1": {},
        }

        for i in range(0, 4):
            config["r" + str(i)] = self._get_val(self.config["r" + str(i)])

        for i in range(0, 2):
            for j in range(0, 4):
                if self.input_refs[j] != 0 and self.PLL_used[i]:
                    n_name = "n" + str(i) + "_profile_" + str(j)
                    config["PLL" + str(i)][n_name] = self._get_val(self.config[n_name])
                    config["PLL" + str(i)]["rate_hz"] = self._get_val(
                        self.config["PLL" + str(i) + "_rate"]
                    )

        for i in range(0, 10):
            config["q" + str(i)] = self._get_val(self.config["q" + str(i)])

        return config

    def _setup_solver_constraints(
        self, input_refs: List[int], out_freqs: List[int]
    ) -> None:
        """Apply constraints to solver model.

        Args:
            input_refs (List[int]): 4 references (frequency in hertz)
            out_freqs (List[int]): 10 outputs (frequency in hertz)

        Raises:
            Exception: Invalid solver
        """
        self.input_refs = input_refs

        self.PLL_used = [False, False]
        for i in range(0, 10):
            if out_freqs[i] != 0:
                if i > 5:
                    self.PLL_used[1] = True
                else:
                    self.PLL_used[0] = True

        equations = []

        if self.solver == "gekko":
            """Add divider as variables to the model"""
            for i in range(0, 4):
                if input_refs[i] != 0:
                    self.config["r" + str(i)] = self.model.Var(
                        integer=True, lb=self.R_min, ub=self.R_max
                    )
                    self.config["input_ref_" + str(i)] = self.model.Const(
                        int(input_refs[i])
                    )

            """ Add PLL N as variables to the model for each PLL profile """
            for i in range(0, 2):
                if self.PLL_used[i]:
                    """Force PLL input rates and output rates to be integer values"""
                    self.config["PLL" + str(i) + "_rate"] = self.model.Var(
                        integer=True, lb=self.PLL_out_min[i], ub=self.PLL_out_max[i]
                    )

                    for j in range(0, 4):
                        if input_refs[j] != 0:
                            n_name = "n" + str(i) + "_profile_" + str(j)
                            self.config[n_name] = self.model.Var(
                                integer=True, lb=self.N_min, ub=self.N_max
                            )

                            """ Internally the PLL block is composed of a
                            Digital PLL and an Analog PLL with different
                            constraints on dividers.
                            """
                            DPLL_N = self.model.Var(integer=True, lb=1, ub=300000000)
                            APLL_M = self.model.Var(integer=True, lb=1, ub=255)

                            equations = equations + [
                                self.config[n_name] == DPLL_N * APLL_M
                            ]

        elif self.solver == "CPLEX":
            """Add divider as variables to the model"""
            for i in range(0, 4):
                if input_refs[i] != 0:
                    self.config["r" + str(i)] = exp.integer_var(
                        int(self.R_min), int(self.R_max), "r" + str(i)
                    )
                    self.config["input_ref_" + str(i)] = exp.CpoValue(
                        int(input_refs[i]), type=ctg.Type_Int
                    )

            """ Add PLL N as variables to the model for each PLL profile """
            for i in range(0, 2):
                if self.PLL_used[i]:
                    self.config["PLL" + str(i) + "_rate"] = exp.integer_var(
                        int(self.PLL_out_min[i]),
                        int(self.PLL_out_max[i]),
                        "PLL" + str(i) + "_rate",
                    )

                for j in range(0, 4):
                    if input_refs[j] != 0:
                        n_name = "n" + str(i) + "_profile_" + str(j)
                        self.config[n_name] = exp.integer_var(
                            int(self.N_min), int(self.N_max), n_name
                        )

                        """ Internally the PLL block is composed of a Digital
                        PLL and an Analog PLL with different constraints on
                        dividers.
                        """
                        DPLL_N = exp.integer_var(int(1), int(300e6))
                        APLL_M = exp.integer_var(int(1), int(255))

                        equations = equations + [self.config[n_name] == DPLL_N * APLL_M]
        else:
            raise Exception("Unknown solver {}".format(self.solver))

        for i in range(0, 4):
            if self.input_refs[i] != 0:
                if self.solver == "gekko":
                    self.config["PLL_in_rate_" + str(i)] = self.model.Var(
                        integer=True, lb=self.PLL_in_min, ub=self.PLL_in_max
                    )
                elif self.solver == "CPLEX":
                    self.config["PLL_in_rate_" + str(i)] = exp.integer_var(
                        int(self.PLL_in_min),
                        int(self.PLL_in_max),
                        "PLL_in_rate_" + str(i),
                    )
                else:
                    raise Exception("Unknown solver {}".format(self.solver))

                equations = equations + [
                    self.config["PLL_in_rate_" + str(i)] * self.config["r" + str(i)]
                    == self.config["input_ref_" + str(i)]
                ]

                """ Need to make sure here the PLLs do not receive more than 200
                kHz input """
                equations = equations + [
                    self.config["PLL_in_rate_" + str(i)] < self.PLL_in_max
                ]

        for i in range(0, 2):
            for j in range(0, 4):
                if self.input_refs[j] != 0 and self.PLL_used[i]:
                    n_name = "n" + str(i) + "_profile_" + str(j)
                    equations = equations + [
                        self.config[n_name] * self.config["PLL_in_rate_" + str(j)]
                        == self.config["PLL" + str(i) + "_rate"]
                    ]

        self._add_equation(equations)

        cplex_objectives = []

        """ Instruct solver to try to avoid Minimum and Maximum PLL rates """
        if self.avoid_min_max_PLL_rates:
            for i in range(0, 2):
                if self.PLL_used[i]:
                    average_PLL_rate = self.PLL_out_min[i] / 2 + self.PLL_out_max[i] / 2

                    if self.solver == "CPLEX":
                        cplex_objectives = cplex_objectives + [
                            mod.abs(
                                self.config["PLL" + str(i) + "_rate"] - average_PLL_rate
                            )
                        ]
                    elif self.solver == "gekko":
                        self.model.Minimize(
                            self.model.abs3(
                                self.config["PLL" + str(i) + "_rate"] - average_PLL_rate
                            )
                        )
                    else:
                        raise Exception("Unknown solver {}".format(self.solver))

        """ Instruct solver to maximize PLL input rates """
        if self.minimize_input_dividers:
            for i in range(0, 4):
                if self.input_refs[i] != 0:
                    if self.solver == "CPLEX":
                        cplex_objectives = cplex_objectives + [
                            self.config["r" + str(i)]
                        ]
                    elif self.solver == "gekko":
                        self.model.Maximize(self.config["PLL_in_rate_" + str(i)])
                    else:
                        raise Exception("Unknown solver {}".format(self.solver))

        if self.solver == "CPLEX" and len(cplex_objectives) != 0:
            self.model.add(mod.minimize_static_lex(cplex_objectives))

    def _setup(self, input_refs: List[int], out_freqs: List[int]) -> None:
        # Setup clock chip internal constraints

        self._setup_solver_constraints(input_refs, out_freqs)

    def set_requested_clocks(self, ins: List[int], outs: List[int]) -> None:
        """Define necessary clocks to be generated in model.

        Args:
            ins (List[int]): list of input references rates
            outs (List[int]): list of output rates required

        Raises:
            Exception: if the number of input references is not equal to the
                number of output rates
        """
        input_refs = [0] * 4
        out_freqs = [0] * 10

        for in_ref in ins:
            input_refs[in_ref[0]] = in_ref[1]

        for out_ref in outs:
            out_freqs[out_ref[0]] = out_ref[1]

        self._setup(input_refs, out_freqs)

        """ Add output dividers as variables to the model """
        for i in range(0, 10):
            if out_freqs[i] != 0:
                if self.solver == "gekko":
                    self.config["q" + str(i)] = self.model.Var(
                        integer=True, lb=self.Q_min, ub=self.Q_max
                    )
                    self.config["out_rate_" + str(i)] = self.model.Const(
                        int(out_freqs[i])
                    )
                elif self.solver == "CPLEX":
                    self.config["q" + str(i)] = exp.integer_var(
                        int(self.Q_min), int(self.Q_max), "q" + str(i)
                    )
                    self.config["out_rate_" + str(i)] = exp.CpoValue(
                        value=int(out_freqs[i]), type=ctg.Type_Int
                    )
                else:
                    raise Exception("Unknown solver {}".format(self.solver))

        for i in range(0, 10):
            if out_freqs[i] != 0:
                if i > 5:
                    pll_number = 1
                else:
                    pll_number = 0

                self._add_equation(
                    [
                        self.config["PLL" + str(pll_number) + "_rate"]
                        == self.config["out_rate_" + str(i)] * self.config["q" + str(i)]
                    ]
                )

    def _solve_gekko(self) -> bool:
        """Local solve method for clock model.

        Call model solver with correct arguments.

        Returns:
            bool: Always False
        """
        self.model.options.SOLVER = 1  # APOPT solver
        self.model.solver_options = [
            "minlp_maximum_iterations 300000000",
            "minlp_max_iter_with_int_sol 6000",
            "minlp_as_nlp 0",
            "minlp_branch_method 1",
            "minlp_integer_tol 0.0001",
        ]

        self.model.solve(disp=False)
        return False
