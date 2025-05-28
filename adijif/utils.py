"""Collection of utility scripts for specialized checks."""

import copy
from typing import List, Optional

import numpy as np

import adijif.fpgas.xilinx.sevenseries as xp
import adijif.fpgas.xilinx.ultrascaleplus as us
from adijif.converters.converter import converter
from adijif.fpgas.fpga import fpga


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
    if any([i == "jesd_class" for i in kwargs.items()]):
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
            trx = xp.SevenSeries(parent=fpga, transceiver_type=fpga.transceiver_type)
            max_lane_rate = trx.plls["QPLL"].vco_max
        elif int(fpga.transceiver_type[4]) in [3, 4]:
            trx = us.UltraScalePlus(parent=fpga, transceiver_type=fpga.transceiver_type)
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
                                if lc in [">", "<", "<=", ">=", "=="]:
                                    attr = getattr(conv, limit)
                                    e = eval(  # noqa: S307
                                        f"{attr} {lc} {limits[limit][lc]}"
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
