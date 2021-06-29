import adijif

vcxo = 125000000
# vcxo = adijif.types.range(100000000, 126000000, 1000000, "vcxo")
# vcxo = adijif.types.range(125000000, 125000010, 10, "vcxo")
n2 = 24

clk = adijif.ad9523_1()

# Check config valid
clk.n2 = n2
# clk.r2 = 1
# clk.m1 = 3
clk.use_vcxo_double = False

output_clocks = [1e9, 500e6, 7.8125e6]
output_clocks = list(map(int, output_clocks))
clock_names = ["ADC", "FPGA", "SYSREF"]

clk.set_requested_clocks(vcxo, output_clocks, clock_names)

clk.solve()

o = clk.get_config()

print(o)

assert sorted(o["out_dividers"]) == [1, 2, 128]
assert o["m1"] == 3
assert o["m1"] in clk.m1_available
assert o["n2"] == n2
assert o["n2"] in clk.n2_available
assert o["r2"] == 1
assert o["r2"] in clk.r2_available
assert o["output_clocks"]["ADC"]["rate"] == 1e9
