# Determine AD9081+ZCU102 supported mode and clocking

import adijif
import pprint
import adidt as dt

vcxo = 125e6

sys = adijif.system("ad9680", "ad9523_1", "xilinx", vcxo)
sys.Debug_Solver = False

sys.fpga.setup_by_dev_kit_name("zcu102")
sys.fpga.force_cpll = True
sys.fpga.request_fpga_core_clock_ref = True  # force reference to be core clock rate

sys.converter.use_direct_clocking = True
sys.converter.set_quick_configuration_mode(0x88)
assert sys.converter.S == 1

# Limit upper dividers to powers of 2
sys.clock.d = [int(2 ** i) for i in range(8)]

# Current configuration
sys.converter.sample_clock = 1e9 / 2
# sys.converter.sample_clock = 750e6

print("Lane rate:", sys.converter.bit_clock)
print("Lane rate/40: ", sys.converter.bit_clock / 40)

cfg = sys.solve()

# Map to existing names in DT
ref = cfg["clock"]["output_clocks"]["AD9680_fpga_ref_clk"]
cfg["clock"]["output_clocks"]["ADC_CLK_FMC"] = ref
del cfg["clock"]["output_clocks"]["AD9680_fpga_ref_clk"]

ref = cfg["clock"]["output_clocks"]["AD9680_ref_clk"]
cfg["clock"]["output_clocks"]["ADC_CLK"] = ref
del cfg["clock"]["output_clocks"]["AD9680_ref_clk"]

ref = cfg["clock"]["output_clocks"]["AD9680_sysref"]
cfg["clock"]["output_clocks"]["CLKD_ADC_SYSREF"] = ref
cfg["clock"]["output_clocks"]["ADC_SYSREF"] = ref
del cfg["clock"]["output_clocks"]["AD9680_sysref"]

pprint.pprint(cfg)

## Update on board


d = dt.clock(dt_source="remote_sd", ip="ip.analog-2")
d.set(cfg["clock"]["part"], cfg["clock"], append=True)
d.update_current_dt(reboot=True)
