"""Bundle of inter-component clock expressions returned by ``system.initialize()``."""

from typing import Any, Iterable, List, Optional, Tuple, Union


class ClocksBundle(dict):
    """Inter-component clock expressions returned by ``system.initialize()``.

    Maps a clock name to the solver expression representing the rate of a clock
    that flows between two high-level components in the system (clock chip to
    converter, clock chip to FPGA, clock chip to inline / sysref PLL, etc.).

    ``ClocksBundle`` is a regular ``dict``: ``clocks[name]`` returns the raw
    solver expression, ``for k in clocks`` iterates clock names, and
    ``dict()``-consuming code keeps working. ``constrain()`` is provided as a
    convenience that hides the solver-backend differences.

    Canonical clock names (created by ``system.initialize()``):

    - ``{converter}_ref_clk`` -- clock chip to converter device clock.
    - ``{converter}_ref_clk_from_ext_pll`` -- inline PLL output to converter
      (when ``add_pll_inline`` is used).
    - ``{converter}_sysref`` -- sysref to converter.
    - ``{converter}_fpga_ref_clk`` -- clock chip to FPGA reference clock.
    - ``{converter}_fpga_device_clk`` -- clock chip to FPGA link clock.
    - ``{pll}_ref_clk`` -- clock chip to inline / sysref PLL reference.
    - ``{pll}_bsync_reference`` -- clock chip to sysref PLL BSYNC reference.

    For nested converters (MxFE / transceivers) the converter name is replaced
    by the nested channel name (e.g. ``adc_sysref``, ``dac_fpga_ref_clk``).

    Example:
        clocks = sys.initialize()
        clocks.constrain("AD9680_fpga_ref_clk", range=(250e6, 350e6))
        clocks.constrain("AD9680_sysref", equal_to=7.8125e6)
        cfg = sys.do_solve()
    """

    def __init__(self, items: dict, owner: Any) -> None:
        """Wrap a dict of clock expressions with constraint helpers.

        Args:
            items: Mapping of clock name to solver expression.
            owner: System instance that owns the solver model. Used to
                forward constraints to the active solver via
                ``owner.clock._add_equation``.
        """
        super().__init__(items)
        self._owner = owner

    def _resolve(self, value: Any) -> Any:
        """Resolve ``value`` to a solver expression or scalar.

        Strings are looked up as another clock name in this bundle so users
        can express equality between two clocks without grabbing the
        expression themselves.

        Args:
            value: Scalar, solver expression, or name of another clock.

        Returns:
            The solver expression / scalar to use in a constraint.

        Raises:
            KeyError: If ``value`` is a string that is not a clock name.
        """
        if isinstance(value, str):
            if value not in self:
                raise KeyError(self._unknown_message(value))
            return self[value]
        return value

    def _unknown_message(self, name: str) -> str:
        return (
            f"Unknown clock name '{name}'. "
            f"Available clocks: {sorted(self.keys())}"
        )

    def constrain(
        self,
        name: str,
        *,
        equal_to: Any = None,
        min: Optional[Union[int, float]] = None,
        max: Optional[Union[int, float]] = None,
        range: Optional[Tuple[Union[int, float], Union[int, float]]] = None,
        choices: Optional[Iterable[Union[int, float]]] = None,
    ) -> None:
        """Add a constraint on an inter-component clock.

        Pass ``range=(lo, hi)`` as sugar for ``min=lo, max=hi``. Bounds and
        ``equal_to`` may be combined (e.g. ``min=`` plus ``max=``); ``choices``
        and ``equal_to`` are mutually exclusive with bounds.

        Args:
            name: Clock name. Must be a key in this bundle.
            equal_to: Force the clock equal to a scalar, another solver
                expression, or another clock by name.
            min: Lower bound on the clock rate.
            max: Upper bound on the clock rate.
            range: ``(lo, hi)`` tuple; equivalent to ``min=lo, max=hi``.
            choices: Iterable of allowed exact rates. Currently CPLEX only.

        Raises:
            KeyError: ``name`` is not in this bundle.
            ValueError: No constraint kwarg was given, or ``range`` was passed
                together with ``min`` / ``max``.
            NotImplementedError: ``choices`` was passed with a non-CPLEX
                solver backend.
        """
        if name not in self:
            raise KeyError(self._unknown_message(name))
        expr = self[name]
        clk = self._owner.clock

        if range is not None:
            if min is not None or max is not None:
                raise ValueError(
                    "Pass either range=(lo, hi) or min=/max=, not both"
                )
            min, max = range[0], range[1]

        added = False
        if equal_to is not None:
            other = self._resolve(equal_to)
            clk._add_equation(expr == other)
            added = True
        if min is not None:
            clk._add_equation(expr >= min)
            added = True
        if max is not None:
            clk._add_equation(expr <= max)
            added = True
        if choices is not None:
            choices_list: List[Union[int, float]] = list(choices)
            if not choices_list:
                raise ValueError("choices must be a non-empty iterable")
            if self._owner.solver != "CPLEX":
                raise NotImplementedError(
                    "constrain(..., choices=...) currently requires the "
                    "CPLEX solver. Use range=/equal_to= with GEKKO."
                )
            from docplex.cp.modeler import logical_or  # noqa: PLC0415

            self._owner.model.add(
                logical_or(*[expr == c for c in choices_list])
            )
            added = True

        if not added:
            raise ValueError(
                "constrain() requires at least one of "
                "equal_to=, min=, max=, range=, or choices="
            )
