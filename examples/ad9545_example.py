import adijif
import pprint

clk = adijif.ad9545(solver="gekko")

clk.avoid_min_max_PLL_rates = True
clk.minimize_input_dividers = True

input_refs = [(0, 1), (1, 10e6)]
output_clocks = [(0, 30720000)]

input_refs = list(map(lambda x: (int(x[0]), int(x[1])), input_refs))  # force to be ints
output_clocks = list(map(lambda x: (int(x[0]), int(x[1])), output_clocks))  # force to be ints

clk.set_requested_clocks(input_refs, output_clocks)

clk.solve()

o = clk.get_config()

pprint.pprint(o)
