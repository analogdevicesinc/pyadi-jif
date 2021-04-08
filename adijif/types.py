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
        assert isinstance(
            model, (GEKKO, CpoModel)
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
            # 1,3,5,7->(1,2,3,4)*2-1
            # 100,200,300,400->(1,2,3,4)*100
            # 0,300,600,900,1200->(1,2,3,4)*300-300
            #
            # o_array->(ints)*step-(step-start)

            o_array = np.arange(self.start, self.stop, self.step)
            s_arrange = np.arange(1, len(o_array) + 1, 1)
            assert np.array_equal(
                o_array, s_arrange * (self.step) - (self.step - self.start)
            ), "Unexpected case"

            config["set"] = model.Var(
                integer=True,
                lb=s_arrange[0],
                ub=s_arrange[-1],
                value=s_arrange[0],
                name=self.name + "_Var",
            )
            config["scale"] = model.Const(self.step)
            config["bias"] = model.Const(self.step - self.start)
            config["range"] = model.Intermediate(
                config["set"] * config["scale"] - config["bias"]
            )
        return config
