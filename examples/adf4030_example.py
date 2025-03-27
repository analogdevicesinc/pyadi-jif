# Generate sysref with ADF4030

import adijif as jif
import pprint

ref_in = int(100e6)

sync = jif.adf4030()

output_clocks = [2.5e6,]
output_clocks = list(map(int, output_clocks))  # force to be ints
clock_names = ["SYSREF",]

sync.set_requested_clocks(ref_in, output_clocks, clock_names)

sync.solve()

o = sync.get_config()

pprint.pprint(o)



