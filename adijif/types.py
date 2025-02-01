"""ADI JIF utility types and functions."""

from typing import Dict, Union

import numpy as np

from adijif.solvers import GEKKO, CpoModel, integer_var  # type: ignore


class range:
    """Model range of possible values.

    This class is similar to range but interfaces with
    the modeling layers to create correct mappings for internal
    solvers
    """

    def __init__(self, start: int, stop: int, step: int, name: str) -> None:
        """Model range of possible values.

        This class is similar to range but interfaces with
        the modeling layers to create correct mappings for internal
        solvers

        Args:
            start (int): Start value of range
            stop (int): Last value of range-step
            step (int): Difference between successive values in range
            name (str): Name of variable
        """
        assert isinstance(start, int), "start must be an int"
        assert isinstance(stop, int), "stop must be an int"
        assert isinstance(step, int), "step must be an int"
        assert isinstance(name, str), "name must be a string"

        self.start = start
        self.stop = stop
        self.step = step
        self.name = name

    def __call__(self, model: Union[GEKKO, CpoModel]) -> Dict:
        """Generate range for parameter solver.

        Args:
            model (GEKKO, CpoModel): Model of JESD system or part to solve

        Returns:
            Dict: Dictionary of solver variable(s) for model
        """
        if GEKKO and CpoModel:
            assert isinstance(
                model, (GEKKO, CpoModel)
            ), "range must be called with input type model"
        elif GEKKO:
            assert isinstance(
                model, GEKKO
            ), "range must be called with input type model"
        elif CpoModel:
            assert isinstance(
                model, CpoModel
            ), "range must be called with input type model"

        config = {}
        if isinstance(model, CpoModel):
            o_array = np.arange(self.start, self.stop, self.step)
            config["range"] = integer_var(domain=o_array, name=self.name + "_Var")
            return config

        if self.step == 1:
            config["range"] = model.Var(
                integer=True,
                lb=self.start,
                ub=self.stop,
                value=self.start,
                name=self.name + "_Var",
            )
        else:
            # Create piecewise problem with binary values (DO NOT USE SOS1!)
            o_array = np.arange(self.start, self.stop, self.step)
            o_array = list(map(int, o_array))

            options = model.Array(model.Var, len(o_array), lb=0, ub=1, integer=True)
            model.Equation(model.sum(options) == 1)  # only select one
            config["range"] = model.Intermediate(model.sum(o_array * options))

        return config


class arb_source:
    """Arbitrary source for solver.

    This internally uses a division of two integers to create an arbitrary clock
    source.
    """

    _max_scalar = int(1e11)

    def __init__(self, name: str) -> None:
        """Arbitrary source for solver.

        Args:
            name (str): Name of source
        """
        self.name = name

        self._a = integer_var(0, self._max_scalar, name=name + "_a")
        self._b = integer_var(0, self._max_scalar, name=name + "_b")

    def __call__(self, model: Union[GEKKO, CpoModel]) -> Dict:
        """Generate arbitrary source for solver.

        Args:
            model (GEKKO, CpoModel): Model of JESD system or part to solve

        Returns:
            Dict: Dictionary of solver variable(s) for model

        Raises:
            NotImplementedError: Only CpoModel is supported
        """
        if GEKKO and CpoModel:
            assert isinstance(
                model, (GEKKO, CpoModel)
            ), "arb_source must be called with input type model"
        elif GEKKO:
            assert isinstance(
                model, GEKKO
            ), "arb_source must be called with input type model"
        elif CpoModel:
            assert isinstance(
                model, CpoModel
            ), "arb_source must be called with input type model"

        # config = {}
        if isinstance(model, CpoModel):
            # config[self.name] = self._a / self._b
            # return config
            return self._a / self._b

        raise NotImplementedError("Only CpoModel is supported")

    def get_config(self, solution: Dict) -> Dict:
        """Get configuration from solver results.

        Args:
            solution (Dict): Solver results

        Returns:
            Dict: Dictionary of solver variable(s) for model
        """
        return {self.name: solution[self._a] / solution[self._b]}
