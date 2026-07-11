"""Collection of utility scripts for specialized checks."""

import copy
import operator
from functools import wraps
from typing import Any, Callable, List, Optional

import numpy as np

import adijif.fpgas.xilinx.sevenseries as xp
import adijif.fpgas.xilinx.ultrascaleplus as us
from adijif.converters.converter import converter
from adijif.fpgas.fpga import fpga
from adijif.solvers import CpoModel, cplex_solver, integer_var  # type: ignore


def _preserve_converter_jesd_state(func: Callable) -> Callable:
    """Restore caller-owned JESD state after a converter utility returns."""

    @wraps(func)
    def wrapper(conv: converter, *args: Any, **kwargs: Any) -> Any:
        original_config = conv.get_current_jesd_mode_settings()
        original_jesd_class = conv.jesd_class
        original_sample_clock = conv.sample_clock
        try:
            return func(conv, *args, **kwargs)
        finally:
            conv.jesd_class = original_jesd_class
            for attr, value in original_config.items():
                setattr(conv, attr, value)
            conv.sample_clock = original_sample_clock

    return wrapper


def get_jesd_mode_from_params(conv: converter, **kwargs: int) -> List[dict]:
    """Find the JESD mode that matches the supplied parameters.

    Args:
        conv (converter): Converter object of desired device
        kwargs: Parameters and values to match against

    Raises:
        Exception: Converter does not have specified JESD property

    Returns:
        List[dict]: JESD mode that matches the supplied parameters
    """
    results = []
    needed = len(kwargs.items())

    # Remove JESD modes if not needed
    if any(i == "jesd_class" for i in kwargs.items()):
        modes = conv.quick_configuration_modes[kwargs["jesd_class"]]
        modes = {kwargs["jesd_class"]: modes}
    else:
        modes = conv.quick_configuration_modes

    modes = copy.deepcopy(modes)

    for standard in modes:
        for mode in modes[standard]:
            found = 0
            settings = modes[standard][mode]
            for key, value in kwargs.items():
                if key not in settings:
                    raise Exception(f"{key} not in JESD Configs")
                if isinstance(value, list):
                    for v in value:
                        if settings[key] == v:
                            found += 1
                else:
                    if settings[key] == value:
                        found += 1
            if found == needed:
                results.append(
                    {"mode": mode, "jesd_class": standard, "settings": settings}
                )

    if not results:
        raise Exception(f"No JESD mode found for {kwargs}")

    return results


@_preserve_converter_jesd_state
def get_max_sample_rates(
    conv: converter, fpga: Optional[fpga] = None, limits: Optional[dict] = None
) -> dict:
    """Determine the maximum sample rates for the device.

    Determine the maximum sample rate across all values of M (number of
    virtual converters and supplied limits

    Args:
        conv (converter): Converter object of desired device
        fpga (Optional[fpga]): FPGA object of desired fpga device
        limits (Optional[dict]): Limits to apply to the device and JESD mode

    Raises:
        Exception: Converter does not have specified property
        Exception: Numeric limits must be described in a nested dict
        AttributeError: FPGA object does not have specified property

    Returns:
        dict: Dictionary of maximum sample rates per M
    """
    if fpga:
        max_lanes = fpga.max_serdes_lanes
        if int(fpga.transceiver_type[4]) == 2:
            trx = xp.SevenSeries(
                parent=fpga, transceiver_type=fpga.transceiver_type
            )
            max_lane_rate = trx.plls["QPLL"].vco_max
        elif int(fpga.transceiver_type[4]) in [3, 4]:
            trx = us.UltraScalePlus(
                parent=fpga, transceiver_type=fpga.transceiver_type
            )
            max_lane_rate = trx.plls["QPLL"].vco_max * 2
        else:
            raise Exception("Unsupported FPGA transceiver type")
    else:
        max_lanes = None
        max_lane_rate = None

    if limits:
        assert isinstance(limits, dict), "limits must be a dictionary"

    results = []
    # Loop across enabled channel counts
    for channels in conv.M_available:
        sample_rates = []
        mode_vals = []
        standards = []
        modes = conv.quick_configuration_modes
        # Cycle through all modes to determine
        for standard in modes:
            for mode in modes[standard]:
                if modes[standard][mode]["M"] not in [channels]:
                    continue
                # Set mode
                conv.set_quick_configuration_mode(mode, standard)
                if max_lanes:
                    if conv.L > max_lanes:
                        continue

                # Set bit_clock
                max_bit_clock = conv.bit_clock_max
                if max_lane_rate:
                    max_bit_clock = min(max_lane_rate, max_bit_clock)

                conv.sample_clock = conv.sample_clock_max
                max_bit_clock_at_max_adc_rate = conv.bit_clock

                # Update model with valid max so we can get true sample clock
                conv.bit_clock = min(
                    max_bit_clock,
                    max_bit_clock_at_max_adc_rate,
                )

                # Apply extra checks
                b = False
                if limits:
                    for limit in limits:
                        if not hasattr(conv, limit):
                            raise AttributeError(
                                f"converter does not have property {limit}"
                            )
                        if isinstance(limits[limit], str):
                            if getattr(conv, limit) != limits[limit]:
                                b = True
                                break
                        elif isinstance(limits[limit], dict):
                            ld = limits[limit]
                            for lc in ld:
                                comparisons = {
                                    ">": operator.gt,
                                    "<": operator.lt,
                                    "<=": operator.le,
                                    ">=": operator.ge,
                                    "==": operator.eq,
                                }
                                if lc in comparisons:
                                    attr = getattr(conv, limit)
                                    if not comparisons[lc](attr, limits[limit][lc]):
                                        b = True
                                        break
                            if b:
                                break

                        else:
                            raise Exception(
                                "Numeric limits must be described in a nested dict"
                            )
                if b:
                    continue

                # Collect sample rate
                sr = min(conv.sample_clock, conv.converter_clock_max)
                sample_rates.append(sr)
                mode_vals.append(mode)
                standards.append(standard)

        if not sample_rates:
            continue

        i = np.argmax(sample_rates)
        mode = mode_vals[i]
        standard = standards[i]
        conv.set_quick_configuration_mode(mode, standard)
        conv.sample_clock = sample_rates[i]
        results.append(
            {
                "sample_clock": conv.sample_clock,
                "bit_clock": conv.bit_clock,
                "L": conv.L,
                "M": conv.M,
                "quick_configuration_mode": mode,
                "jesd_class": standard,
            }
        )
    return results


class _InfeasibleMode(Exception):
    """Internal sentinel: this mode cannot be made feasible. Skip it."""


def _fpga_max_lane_rate(fpga_obj: fpga) -> float:
    """Return the max lane rate the FPGA's QPLL can produce.

    Mirrors the per-family logic in ``get_max_sample_rates``:
    7-Series uses QPLL VCO max directly; UltraScale+ doubles it.
    """
    trx_type = fpga_obj.transceiver_type
    family_digit = int(trx_type[4])
    if family_digit == 2:
        trx = xp.SevenSeries(parent=fpga_obj, transceiver_type=trx_type)
        return trx.plls["QPLL"].vco_max
    if family_digit in (3, 4):
        trx = us.UltraScalePlus(parent=fpga_obj, transceiver_type=trx_type)
        return trx.plls["QPLL"].vco_max * 2
    raise Exception(f"Unsupported FPGA transceiver type: {trx_type}")


def _enumerate_modes(
    conv: converter, mode: Optional[str], jesd_class: Optional[str]
) -> List[tuple]:
    """Build the list of (jesd_class, mode) pairs to try."""
    if mode is not None:
        smode = str(mode)
        if jesd_class is not None:
            if smode not in conv.quick_configuration_modes[jesd_class]:
                raise ValueError(
                    f"Mode {smode!r} not found in {jesd_class} for {conv.name}"
                )
            return [(jesd_class, smode)]
        # Search for which JESD class contains this mode
        matches = [
            jc
            for jc in conv.quick_configuration_modes
            if smode in conv.quick_configuration_modes[jc]
        ]
        if not matches:
            raise ValueError(
                f"Mode {smode!r} not found in any JESD class for {conv.name}"
            )
        if len(matches) > 1:
            raise ValueError(
                f"Mode {smode!r} is ambiguous across {matches}; "
                "pass jesd_class explicitly."
            )
        return [(matches[0], smode)]
    return [
        (jc, m)
        for jc in conv.quick_configuration_modes
        for m in conv.quick_configuration_modes[jc]
    ]


def _solve_one_mode(
    conv_template: converter,
    jesd_class: str,
    mode: str,
    target: str,
    sense: str,
    fpga_max_lane_rate: Optional[float],
    fpga_max_lanes: Optional[int],
) -> dict:
    """Solve for the extreme rate within a single JESD mode.

    Returns the result dict. Raises ``_InfeasibleMode`` if the mode cannot
    satisfy the requested constraints (lane count, empty bound range, or no
    solver solution).
    """
    conv = copy.deepcopy(conv_template)
    try:
        conv.set_quick_configuration_mode(mode, jesd_class)
    except Exception as e:
        raise _InfeasibleMode() from e

    if fpga_max_lanes is not None and conv.L > fpga_max_lanes:
        raise _InfeasibleMode()

    bc_min = conv.bit_clock_min_available[jesd_class]
    bc_max = conv.bit_clock_max_available[jesd_class]
    if fpga_max_lane_rate is not None:
        bc_max = min(bc_max, fpga_max_lane_rate)

    # sample_clock = bit_clock * L * encoding_n / (encoding_d * M * Np)
    factor = (conv.L * conv.encoding_n) / (conv.encoding_d * conv.M * conv.Np)
    sc_min = bc_min * factor
    sc_max = bc_max * factor

    dev_sc_min = getattr(conv, "sample_clock_min", None)
    if dev_sc_min is not None:
        sc_min = max(sc_min, dev_sc_min)
    dev_sc_max = getattr(conv, "sample_clock_max", None)
    if dev_sc_max is not None:
        sc_max = min(sc_max, dev_sc_max)

    if sc_min > sc_max:
        raise _InfeasibleMode()

    model = CpoModel()
    sc_var = integer_var(int(sc_min), int(sc_max), name="sample_clock")
    conv._sample_clock = sc_var

    expr = conv.bit_clock if target == "lane" else conv.sample_clock
    if sense == "max":
        model.maximize(expr)
    else:
        model.minimize(expr)

    solution = model.solve(LogVerbosity="Quiet", WarningLevel=0)
    if not solution.is_solution():
        raise _InfeasibleMode()

    sc_value = solution.get_value(sc_var)
    bc_value = (
        (conv.M / conv.L)
        * conv.Np
        * (conv.encoding_d / conv.encoding_n)
        * sc_value
    )
    obj_value = bc_value if target == "lane" else float(sc_value)

    return {
        "sample_clock": float(sc_value),
        "bit_clock": float(bc_value),
        "mode": mode,
        "jesd_class": jesd_class,
        "M": conv.M,
        "L": conv.L,
        "Np": conv.Np,
        "F": conv.F,
        "S": conv.S,
        "K": conv.K,
        "clock_config": None,
        "fpga_config": None,
        "objective_value": float(obj_value),
    }


def _solve_one_mode_with_clock(
    conv_template: converter,
    clock_template: object,
    fpga_template: fpga,
    vcxo: float,
    jesd_class: str,
    mode: str,
    target: str,
    sense: str,
) -> dict:
    """Solve for the extreme rate within a single mode using a full clock chain.

    Uses ``adijif.system`` to wire the clock chip, converter, and FPGA. The
    converter's ``_sample_clock`` is replaced with an integer variable so the
    solver chooses it under the user objective; range-validation hooks that
    can't tolerate a solver expression are bypassed (variable bounds enforce
    the same limits).
    """
    import adijif  # local: utils sits below system in the dependency graph

    if conv_template.L > fpga_template.max_serdes_lanes:
        raise _InfeasibleMode()

    conv_local = copy.deepcopy(conv_template)
    clock_local = copy.deepcopy(clock_template)
    fpga_local = copy.deepcopy(fpga_template)

    try:
        conv_local.set_quick_configuration_mode(mode, jesd_class)
    except Exception as e:
        raise _InfeasibleMode() from e

    if conv_local.L > fpga_local.max_serdes_lanes:
        raise _InfeasibleMode()

    sys_obj = adijif.system(
        type(conv_local).__name__,
        type(clock_local).__name__,
        type(fpga_local).__name__,
        vcxo,
        solver="CPLEX",
    )
    # Override the system's freshly-constructed components with the user's
    # deep-copies, rebinding each to the system's shared solver model.
    sys_obj.converter = conv_local
    sys_obj.converter.model = sys_obj.model
    sys_obj.clock = clock_local
    sys_obj.clock.model = sys_obj.model
    sys_obj.fpga = fpga_local
    sys_obj.fpga.model = sys_obj.model

    bc_min = conv_local.bit_clock_min_available[jesd_class]
    bc_max = conv_local.bit_clock_max_available[jesd_class]
    fpga_cap = _fpga_max_lane_rate(fpga_local)
    bc_max = min(bc_max, fpga_cap)

    factor = (conv_local.L * conv_local.encoding_n) / (
        conv_local.encoding_d * conv_local.M * conv_local.Np
    )
    sc_min = bc_min * factor
    sc_max = bc_max * factor
    dev_sc_min = getattr(conv_local, "sample_clock_min", None)
    if dev_sc_min is not None:
        sc_min = max(sc_min, dev_sc_min)
    dev_sc_max = getattr(conv_local, "sample_clock_max", None)
    if dev_sc_max is not None:
        sc_max = min(sc_max, dev_sc_max)
    if sc_min > sc_max:
        raise _InfeasibleMode()

    sc_var = integer_var(int(sc_min), int(sc_max), name="sample_clock")
    sys_obj.converter._sample_clock = sc_var

    # Skip scalar-range validation hooks that can't handle a CpoExpr. The
    # integer_var bounds enforce the same limits at solve time.
    sys_obj.converter._skip_clock_validation = True
    sys_obj.converter._check_jesd_config = lambda: None
    sys_obj.converter._check_valid_internal_configuration = lambda: None

    expr_target = (
        sys_obj.converter.bit_clock
        if target == "lane"
        else sys_obj.converter.sample_clock
    )
    sys_obj.add_objective(
        expr_target,
        sense=sense,
        tier=0,
        name=f"find_extreme_rate.{target}_{sense}",
    )

    try:
        sys_obj.initialize()
        sys_obj._solve_cplex()
    except Exception as e:
        raise _InfeasibleMode() from e

    sc_value = sys_obj._solution.get_value(sc_var)
    # Rebind to a scalar so component get_config() calls (which compare
    # bit_clock to PLL outputs as plain numbers) work normally.
    sys_obj.converter._sample_clock = float(sc_value)
    full_config = sys_obj._get_configs()

    bc_value = (
        (conv_local.M / conv_local.L)
        * conv_local.Np
        * (conv_local.encoding_d / conv_local.encoding_n)
        * sc_value
    )
    obj_value = bc_value if target == "lane" else float(sc_value)

    return {
        "sample_clock": float(sc_value),
        "bit_clock": float(bc_value),
        "mode": mode,
        "jesd_class": jesd_class,
        "M": conv_local.M,
        "L": conv_local.L,
        "Np": conv_local.Np,
        "F": conv_local.F,
        "S": conv_local.S,
        "K": conv_local.K,
        "clock_config": full_config.get("clock"),
        "fpga_config": {
            k: v for k, v in full_config.items() if k.startswith("fpga_")
        },
        "objective_value": float(obj_value),
    }


def find_extreme_rate(
    conv: converter,
    *,
    target: str = "lane",
    sense: str = "max",
    fpga: Optional[fpga] = None,
    clock: Optional[object] = None,
    vcxo: Optional[float] = None,
    mode: Optional[str] = None,
    jesd_class: Optional[str] = None,
    solver: str = "CPLEX",
) -> dict:
    """Find the max or min lane rate or sample rate for a converter.

    Two modes:

    - **Constraint-only** (default): builds a small CPLEX model per JESD
      mode, bounds ``sample_clock`` by the JESD class and (if ``fpga`` is
      given) the FPGA's QPLL VCO cap, and optimizes the chosen target.
    - **Full clock chain** (when ``clock`` is supplied): also wires the
      clock chip through ``adijif.system`` so the solution must be
      reachable by the clock chip's dividers. Requires ``fpga`` and
      ``vcxo``.

    When ``mode`` is omitted, every mode in
    ``conv.quick_configuration_modes`` is tried and the best result is
    returned. The input ``conv`` (and ``clock``, ``fpga``) is not
    mutated; each attempt runs on a deep copy.

    Args:
        conv: Converter object to evaluate. Nested converters (MxFE /
            transceivers) are not supported -- pass the rx or tx side
            directly.
        target: ``"lane"`` to optimize ``bit_clock``, ``"sample"`` for
            ``sample_clock``.
        sense: ``"max"`` (default) or ``"min"``.
        fpga: Optional FPGA object. When supplied, its lane-count and
            QPLL-derived max lane rate bound the search. Required when
            ``clock`` is supplied.
        clock: Optional clock chip. When supplied, the solver also
            satisfies the clock-chain dividers, and ``fpga`` and ``vcxo``
            are required.
        vcxo: VCXO frequency in Hz. Required when ``clock`` is supplied.
        mode: Optional JESD quick-configuration mode key. If omitted, all
            modes are enumerated.
        jesd_class: ``"jesd204b"`` or ``"jesd204c"``. Required only when
            ``mode`` is set and ambiguous across classes.
        solver: Currently only ``"CPLEX"`` is supported.

    Returns:
        dict: Resulting configuration. Keys: ``sample_clock``, ``bit_clock``,
        ``mode``, ``jesd_class``, ``M``, ``L``, ``Np``, ``F``, ``S``, ``K``,
        ``clock_config``, ``fpga_config``, ``objective_value``.
        ``clock_config`` and ``fpga_config`` are populated only when the
        respective component is supplied.

    Raises:
        ValueError: Invalid ``target``, ``sense``, or mode arguments, or
            ``clock`` supplied without ``fpga``/``vcxo``.
        NotImplementedError: ``solver != "CPLEX"`` or CPLEX is not installed.
        Exception: No feasible mode found, or the converter is nested.
    """
    if target not in ("lane", "sample"):
        raise ValueError(f"target must be 'lane' or 'sample', got {target!r}")
    if sense not in ("max", "min"):
        raise ValueError(f"sense must be 'max' or 'min', got {sense!r}")
    if solver != "CPLEX":
        raise NotImplementedError(
            "find_extreme_rate currently only supports solver='CPLEX'"
        )
    if not cplex_solver:
        raise NotImplementedError(
            "find_extreme_rate requires CPLEX/docplex. "
            "Install with: pip install 'pyadi-jif[cplex]'"
        )
    if clock is not None:
        if fpga is None:
            raise ValueError(
                "find_extreme_rate requires fpga when clock is supplied "
                "(no-FPGA clock-chain solving is not supported)."
            )
        if vcxo is None:
            raise ValueError("vcxo is required when clock is supplied")
    elif vcxo is not None:
        raise ValueError("vcxo is only meaningful when clock is supplied")
    if getattr(conv, "_nested", False):
        raise Exception(
            f"{conv.name} is a nested device; pass the rx or tx side "
            "(e.g. ad9081_rx) directly."
        )

    modes_to_try = _enumerate_modes(conv, mode, jesd_class)

    fpga_max_lane_rate = (
        _fpga_max_lane_rate(fpga)
        if (fpga is not None and clock is None)
        else None
    )
    fpga_max_lanes = (
        fpga.max_serdes_lanes if (fpga is not None and clock is None) else None
    )

    best: Optional[dict] = None
    for jc, m in modes_to_try:
        try:
            if clock is not None:
                result = _solve_one_mode_with_clock(
                    conv, clock, fpga, vcxo, jc, m, target, sense
                )
            else:
                result = _solve_one_mode(
                    conv,
                    jc,
                    m,
                    target,
                    sense,
                    fpga_max_lane_rate,
                    fpga_max_lanes,
                )
        except _InfeasibleMode:
            continue
        if best is None:
            best = result
            continue
        if sense == "max":
            if result["objective_value"] > best["objective_value"]:
                best = result
        else:
            if result["objective_value"] < best["objective_value"]:
                best = result

    if best is None:
        raise Exception(f"No feasible JESD configuration found for {conv.name}")
    return best
