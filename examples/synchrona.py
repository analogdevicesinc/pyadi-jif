import adijif
import pprint

vcxo = adijif.range(100000000,150000000,25000000,"vcxo")

clk = adijif.hmc7044(solver="gekko")

clk.vxco_doubler = 2

output_clocks = [1e9, 500e6, 7.8125e6]
output_clocks = list(map(int, output_clocks))  # force to be ints
clock_names = ["ADC", "FPGA", "SYSREF"]

clk.set_requested_clocks(vcxo, output_clocks, clock_names)

clk.solve()

o = clk.get_config()

pprint.pprint(o)
