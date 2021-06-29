import adijif
import pprint

vcxo = 125000000

clk = adijif.hmc7044()

clk.n2 = 24

output_clocks = [1e9, 500e6, 7.8125e6]
output_clocks = list(map(int, output_clocks))  # force to be ints
clock_names = ["ADC", "FPGA", "SYSREF"]

clk.set_requested_clocks(vcxo, output_clocks, clock_names)

clk.solve()

o = clk.get_config()

pprint.pprint(o)
