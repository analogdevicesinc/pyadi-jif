# Triton (Quad-Apollo) clock configuration
# This example models the clock configuration for the Triton (Quad-Apollo) platform.
# Not all 4 AD9084s are modeled since they share the same clock and JESD configuration.
# The main limitation compared to the AD9084 FMC single chip board is the reduction of lanes,
# since all 4 AD9084s must shared the same 24-lanes available on the VCU118 FMC+ connector.
# We will also assume RX and TX have the same configuration. If the ADC/DAC configurations
# are different but the resulting samples rates and late rates are the same this assumption
# will hold.

import adijif
import pprint
import os

#L = 2  # max_available_lanes_per_ad9084_side
#M = 4  # Converters used to AD9084 side
#Np = 16  # Bits per sample

vcxo = int(400e6)
#cddc_dec = 4
#fddc_dec = 8
#converter_rate = int(12.8e9)

here = os.path.dirname(os.path.abspath(__file__))
profile_json = os.path.join(here, "id00_triton_M4_L2_RX13p2.json")
profile_bin = profile_json.replace('.json','.bin')

sys = adijif.system("ad9084_rx", "ltc6952", "xilinx", vcxo, solver="CPLEX")

sys.fpga.setup_by_dev_kit_name("vcu118")

# Apply datapath config
sys.converter.apply_profile_settings(profile_json)
# sys.converter.sample_clock = converter_rate / (cddc_dec * fddc_dec)
# sys.converter.datapath.cddc_decimations = [cddc_dec] * 4
# sys.converter.datapath.fddc_decimations = [fddc_dec] * 8
# sys.converter.datapath.fddc_enabled = [True] * 8

# Setup clocks
sys.converter.clocking_option = "direct"
sys.add_pll_inline("adf4382", vcxo, sys.converter)
sys.add_pll_sysref("adf4030", sys.clock, sys.converter, sys.fpga)

# Optimizations
sys.clock.minimize_feedback_dividers = False

# mode_rx = adijif.utils.get_jesd_mode_from_params(
#     sys.converter, M=M, L=L, Np=Np, jesd_class="jesd204c"
# )
# print(f"RX JESD Mode: {mode_rx}")
# assert mode_rx
# mode_rx = mode_rx[0]["mode"]
# sys.converter.set_quick_configuration_mode(mode_rx, "jesd204c")

print(f"Lane rate: {sys.converter.bit_clock/1e9} Gbps")
print(f"Needed Core clock: {sys.converter.bit_clock/66} MHz")

assert sys.converter.bit_clock == int(13.2e9)
assert sys.converter.M == 4
assert sys.converter.L == 2

cfg = sys.solve()

pprint.pprint(cfg)

## Generate make commands for HDL
mode = "64B66B" if sys.converter.jesd_class == "jesd204c" else "8B10B"
make_cmd = (
    f"JESD_MODE={mode} "
    + f"RX_RATE={sys.converter.bit_clock/1e9:.4f} TX_RATE={sys.converter.bit_clock/1e9:.4f} "
    + f"RX_JESD_M={sys.converter.M} TX_JESD_M={sys.converter.M} "
    + f"RX_JESD_L={sys.converter.L} TX_JESD_L={sys.converter.L} "
    + f"RX_JESD_S={sys.converter.S} TX_JESD_S={sys.converter.S} "
    + f"RX_JESD_NP={sys.converter.Np} TX_JESD_NP={sys.converter.Np} "
)
print("Make command:")
print(make_cmd)

from importlib.util import find_spec

if find_spec("jinja2"):
    import jinja2
    # Read template
    with open("triton_dt.tmpl", "r") as f:
        template = jinja2.Template(f.read())
        rendered = template.render(cfg=cfg, profile_filename=profile_bin)

    with open("triton_dt.dts", "w") as f:
        f.write(rendered)
else:
    print("jinja2 not installed, install with pip install jinja2")

with open("triton_dt.dts", "w") as f:
    f.write(rendered)