# This example determines the maximum sample rate based on
# FPGA platform and JESD204 class
import adijif as jif
import numpy as np

conv = jif.ad9081_rx()

# Determine max data rate from FPGA
fpga = jif.xilinx()
fpga.setup_by_dev_kit_name("zc706")
fpga.sys_clk_select = "GTH34_SYSCLK_QPLL0"  # Use faster QPLL
max_lanes = fpga.max_serdes_lanes
max_lane_rate = max([fpga.vco1_max, fpga.vco0_max])

print(
    "Max aggregate bandwidth into FPGA SERDES:", max_lanes * max_lane_rate / 1e9, "Gbps"
)
print("Max individual lane for FPGA SERDES:", max_lane_rate / 1e9, "Gbps")

conv.jesd_class = "jesd204c"

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
        if conv.jesd_class not in ["jesd204c"]:
            continue
        if conv.L > max_lanes:
            continue

        # Set bit_clock
        max_bit_clock = conv.bit_clock_max
        max_bit_clock = min(max_lane_rate,max_bit_clock)

        conv.sample_clock = conv.sample_clock_max
        max_bit_clock_at_max_adc_rate = conv.bit_clock

        ## Update model with valid max so we can get true sample clock
        conv.bit_clock = min(
            max_bit_clock,
            max_bit_clock_at_max_adc_rate,
        )

        # Collect sample rate
        sr = min(conv.sample_clock, conv.converter_clock_max)
        sample_rates.append(sr)
        mode_vals.append(mode)

    i = np.argmax(sample_rates)
    mode = mode_vals[i]
    conv.set_quick_configuration_mode(mode)
    conv.sample_clock = sample_rates[i]
    print(
        "M={}: Max Sample rate per channel: {} (MSPS) Lane rate: {} (L={})".format(
            conv.M,
            np.floor(conv.sample_clock / 1e6),
            conv.bit_clock / 1e9,
            conv.L,
        )
    )