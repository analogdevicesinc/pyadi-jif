"""Collection of utility scripts for specialized checks"""
import numpy as np

import adijif as jif
from adijif.converters.converter import converter as convc
from adijif.fpgas.fpga import fpga


def get_max_sample_rates(conv: convc, fpga: fpga = None):
    """Determine the maximum sample rate across all values of M (number of
    virtual converters and supplied limits

    Args:
        conv (converter): Converter object of desired device
        fpga (fpga,optional): FPGA object of desired fpga device
    """

    if fpga:
        max_lanes = fpga.max_serdes_lanes
        max_lane_rate = max([fpga.vco1_max, fpga.vco0_max])
    else:
        max_lanes = None
        max_lane_rate = None

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

            ## Update model with valid max so we can get true sample clock
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
                        for l in ld:
                            if l in [">", "<", "<=", ">=", "=="]:
                                s = f"{getattr(conv,limit)} {l} {limits[limit][l]}"
                                e = eval(
                                    f"{getattr(conv,limit)} {l} {limits[limit][l]}"
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

        i = np.argmax(sample_rates)
        mode = mode_vals[i]
        conv.set_quick_configuration_mode(mode)
        # conv.bit_clock = min(
        #     conv.bit_clock_max_available[conv.jesd_class],
        #     conv.bit_clock_min_available[conv.jesd_class],
        # )
        # conv.sample_clock = min(conv.sample_clock, conv.converter_clock_max)
        conv.sample_clock = sample_rates[i]
        # print(
        #     "M={}: Max Sample rate per channel: {} (MSPS) Lane rate: {} (L={})".format(
        #         conv.M,
        #         np.floor(conv.sample_clock / 1e6),
        #         conv.bit_clock / 1e9,
        #         conv.L,
        #     )
        # )
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
