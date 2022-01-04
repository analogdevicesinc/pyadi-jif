import adijif
import pprint

vcxo = 80e6

clk = adijif.ad9528()

output_clocks = [998400000 / 16, 998400000 / 16, 998400000 / 512]
print(output_clocks)
output_clocks = list(map(int, output_clocks))  # force to be ints
clock_names = ["ADC", "FPGA", "SYSREF"]

clk.set_requested_clocks(vcxo, output_clocks, clock_names)

clk.solve()

o = clk.get_config()

pprint.pprint(o)
