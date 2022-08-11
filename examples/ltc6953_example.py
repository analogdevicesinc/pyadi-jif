import adijif
import pprint

ref_in = adijif.types.range(1000000000, 4500000000, 1000000, "ref_in")


clk = adijif.ltc6953(solver="CPLEX")

output_clocks = [1e9, 500e6, 7.8125e6]
print(output_clocks)
output_clocks = list(map(int, output_clocks))  # force to be ints
clock_names = ["ADC", "FPGA", "SYSREF"]

clk.set_requested_clocks(ref_in, output_clocks, clock_names)

clk.solve()

o = clk.get_config()

pprint.pprint(o)
