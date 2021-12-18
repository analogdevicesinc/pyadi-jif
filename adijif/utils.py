"""Collection of utility scripts for specialized checks."""
import ast
from typing import List, Optional

import numpy as np

from adijif.converters.converter import converter
from adijif.fpgas.fpga import fpga
from adijif.fpgas.xilinx import xilinx


def get_jesd_mode_from_params(conv: converter, **kwargs) -> List[dict]:  # noqa: ANN003
    """Find the JESD mode that matches the supplied parameters.

    Args:
        conv (converter): Converter object of desired device
        kwargs: Parameters and values to match against

    Raises:
        Exception: If no mode is found that matches the supplied parameters

    Returns:
        List of dictionaries containing the matching JESD modes
    """
    results = []
    needed = len(kwargs.items())
    for mode in conv.quick_configuration_modes:
        found = 0
        settings = conv.quick_configuration_modes[mode]
        for key, value in kwargs.items():
            if key not in settings:
                raise Exception(f"{key} not in JESD Configs")
            if settings[key] == value:
                found += 1
        if found == needed:
            results.append(mode)

    return results


def get_max_sample_rates(conv: converter, fpga: Optional[fpga] = None) -> List[float]:
    """Get max rates from M and FPGA.

    Determine the maximum sample rate across all values of M (number of
    virtual converters) and supplied limits.

    Args:
        conv (converter): Converter object of desired device
        fpga (fpga,optional): FPGA object of desired fpga device

    Raises:
        AttributeError: converter does not have property
        Exception: Numeric limits must be described in a nested dict

    Returns:
        List of maximum sample rates per M value
    """
    if fpga and isinstance(fpga, xilinx):
        max_lanes = fpga.max_serdes_lanes
        max_lane_rate = max([fpga.vco1_max, fpga.vco0_max])
    else:
        max_lanes = 0
        max_lane_rate = 0

    limits = None

    if limits:
        assert isinstance(limits, dict), "limits must be a dictionary"

    results = []
    # Loop across enabled channel counts
    for channels in conv.M_available:
        sample_rates = []
        mode_vals = []
        modes = conv.quick_configuration_modes
        # Cycle through all modes to determine
        for mode in modes:
            if modes[mode]["M"] not in [channels]:
                continue
            # Set mode
            conv.set_quick_configuration_mode(mode)
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
                        for cp in ld:
                            if cp in [">", "<", "<=", ">=", "=="]:
                                e = ast.literal_eval(
                                    f"{getattr(conv,limit)} {cp} {limits[limit][cp]}"
                                )
                                if not e:
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

        if not sample_rates:
            continue

        i = int(np.argmax(sample_rates))
        mode = mode_vals[i]
        conv.set_quick_configuration_mode(mode)
        conv.sample_clock = sample_rates[i]
        results.append(
            {
                "sample_clock": conv.sample_clock,
                "bit_clock": conv.bit_clock,
                "L": conv.L,
                "M": conv.M,
                "quick_configuration_mode": mode,
            }
        )
    return results
