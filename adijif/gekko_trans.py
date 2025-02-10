"""Translation methods for solvers and module."""

from typing import List, Optional, Union

import numpy as np

from adijif.solvers import GK_Intermediate
from adijif.solvers import (
    binary_var,
    CpoExpr,
    CpoFunctionCall,
    CpoSolveResult,
    GEKKO,
    GK_Operators,
    GKVariable,
    integer_var,
)


class gekko_translation:
    """Collection of utility functions to translate to and from solver types."""

    # @property
    # @abstractmethod
    # def model(self):
    #     raise NotImplementedError
    model: Union[GEKKO, CpoExpr] = None

    solution: CpoSolveResult = None

    solver = "gekko"  # "CPLEX"

    def _add_intermediate(
        self, eqs: Union[GK_Operators, CpoFunctionCall]
    ) -> Union[GK_Intermediate, CpoFunctionCall]:
        """Add intermediate/simplified equation.

        Args:
            eqs (GK_Operators, CpoFunctionCall): Equation

        Returns:
            GK_Intermediate/CpoFunctionCall: Converted equation for solver

        Raises:
            Exception: Unknown solver selected
        """
        if self.solver == "gekko":
            return self.model.Intermediate(eqs)
        elif self.solver == "CPLEX":
            return eqs
        else:
            raise Exception(f"Unknown solver: {self.solver}")

    def _add_equation(
        self,
        eqs: List[Union[GKVariable, GK_Intermediate, GK_Operators, CpoExpr]],
    ) -> None:
        """Add equation or relation to solver.

        Args:
            eqs (List[Union[GKVariable, GK_Intermediate, GK_Operators, CpoExpr]]):
                List of equations or CPLEX constraints to add to solver.

        Raises:
            Exception: Unknown solver selected
        """
        if not isinstance(eqs, list):
            eqs = [eqs]

        if self.solver == "gekko":
            self.model.Equations(eqs)
        elif self.solver == "CPLEX":
            for eq in eqs:
                self.model.add_constraint(eq)
        else:
            raise Exception(f"Unknown solver {self.solver}")

    def _get_val(
        self,
        value: Union[int, float, GKVariable, GK_Intermediate, GK_Operators],
    ) -> Union[int, float, str]:
        """Extract value from solver types.

        Args:
            value (GKVariable, GK_Intermediate, GK_Operators): Solver variable

        Returns:
            int/float: Extracted value

        Raises:
            Exception: Unknown solver selected
        """
        if isinstance(value, (float, int)):
            return value
        if self.solver == "gekko":
            if type(value) in [
                GKVariable,
                GK_Intermediate,
            ]:
                return value.value[0]
            elif type(value) is GK_Operators:
                return value.value
            else:
                return value
        elif self.solver == "CPLEX":
            if isinstance(value, (int, float)):
                return value
            return self.solution.get_value(value.get_name())
        else:
            raise Exception(f"Unknown solver {self.solver}")

    def _check_in_range(
        self,
        value: Union[int, str, List[int], List[str]],
        possible: Union[List[int], List[str]],
        varname: str,
    ) -> None:
        """Check if desired value in list.

        Args:
            value (int, str, List[int], List[str]): Desired input value
            possible (List[int], List[str]): Possible valid options
            varname (str): Name of variable

        Raises:
            Exception: Value not indexable from list or possible

        """
        if not isinstance(value, list):
            value = [value]  # type: ignore
        for v in value:  # type: ignore
            if v not in possible:
                raise Exception(f"{v} invalid for {varname}. Only {possible} possible")

    def _convert_input(
        self,
        val: Union[int, List[int], float, List[float]],
        name: Optional[str] = None,
        default: Union[int, float] = None,
    ) -> Union[CpoExpr, GKVariable, GK_Operators]:
        """Convert input to solver variables.

        Args:
            val (int, List[int], float, List[float]): Values or list of
                values to convert to solver variables.
            name (Optional[str]): Name of variable
            default (Optional[int, float]): Default/initial value

        Returns:
            CpoExpr, GKVariable, GK_Operators: Solver variables

        Raises:
            Exception: Unknown solver selected
        """
        if self.solver == "gekko":
            name = None
            return self._convert_input_gekko(val, name, default)
        elif self.solver == "CPLEX":
            return self._convert_input_cplex(val, name)
        else:
            raise Exception(f"Unknown solver {self.solver}")

    def _convert_input_gekko(
        self,
        val: Union[int, List[int], float, List[float]],
        name: Optional[str] = None,
        default: Optional[Union[int, float]] = None,
    ) -> Union[GKVariable, GK_Operators]:
        """Convert input to GEKKO solver variables.

        Args:
            val (int, List[int], float, List[float]): Values or list of
                values to convert to solver variables.
            name (str): Name of variable
            default (Optional[int, float]): Default/initial value

        Returns:
            GKVariable, GK_Operators: Solver variables
        """
        if isinstance(val, list) and len(val) > 1:
            return self._convert_list(val, name, default)
        if name:
            name + "_Const"
        return self.model.Const(value=val, name=name)

    def _convert_input_cplex(
        self,
        val: Union[int, List[int], float, List[float]],
        name: Optional[str] = None,
    ) -> CpoExpr:
        """Convert input to CPLEX solver variables.

        Args:
            val (int, List[int], float, List[float]): Values or list of
                values to convert to solver variables.
            name (str): Name of variable

        Returns:
            CpoExpr: Solver variables

        Raises:
            Exception: Variable already exists in solver model
        """
        if name:
            names = [var.get_name() for var in self.model.get_all_variables()]
            if name in names:
                raise Exception(f"Variable {name} already exists in model")
        if isinstance(val, list) and val.sort() == [0, 1]:
            return binary_var(name=name)
        # if isinstance(val, (float, int)):
        #     return constant(val)
        # return integer_var(domain=(val, val), name=name)
        if isinstance(val, int):
            return val
        if isinstance(val, float):
            if float(int(val)) == val:
                val = int(val)
            return val
            # return integer_var(domain=(val, val), name=name)
            # return self.model.continuous_var(domain=(val, val), name=name)
        return integer_var(domain=val, name=name)

    def _convert_list(
        self,
        val: Union[List[int], List[float]],
        name: Optional[str] = None,
        default: Optional[Union[int, float]] = None,
    ) -> GK_Operators:
        """Convert input list to GEKKO solver variables.

        Args:
            val (List[int], List[float]): List of values to convert
                to solver variables.
            name (str): Name of variable
            default (Optional[int, float]): Default/initial value

        Returns:
            GK_Operators: Solver variables

        Raises:
            Exception: Unsupported case
        """
        # Check if contiguous by simply stride
        delta = val[0] - val[1]
        for i in range(len(val) - 1):
            if val[i] - val[i + 1] is not delta:
                # Must use SOS2
                # print(val[i] - val[i + 1], delta)
                # return self._convert_list2sos(val, name)
                return self.model.sos1(val)

        if np.abs(delta) == 1:  # Easy mode
            # print(np.min(val), np.max(val))
            if not default:
                default = np.min(val)
            if name:
                name + "_Var"
            return self.model.Var(
                integer=True,
                lb=np.min(val),
                ub=np.max(val),
                value=default,
                name=name,
            )

        else:
            # SOS practical in small cases
            if len(val) < 6:
                print("SOS pract")
                # Need to still handle name
                return self.model.sos1(val)
            # Since stride is not zero the best is to use a scale
            # factor and intermediate for best solving performance

            # Need to fit-> (Array+B)*C+D == org_arrar
            # 1,3,5 -> ([1,2,3]-1) * 2 + 1
            # 3,6,9 -> [1,2,3]*3
            # 2,4,6 -> [1,2,3]*2

            raise Exception("NOT COMPLETE")

            # val = np.array(val)
            # vlen = len(val)
            # Array = np.array(range(1, vlen + 1))
            # for B in range(0, vlen):
            #     for C in range(1, vlen):
            #         for D in range(0, vlen):
            #             if val == (Array + B) * C + D:
            #                 break
            # array = self.model.Var(
            #     integer=True, lb=1, ub=4, value=1, name=name + "_Var"
            # )

    # def _convert_back(self, value):
    #     return value
