import adijif as jif
import pprint

ref_in = 125000000
pll = "adf4382"
pll = "adf4371"

clk = eval(f"jif.{pll}()")
# clk = jif.hmc7044()

output_clocks = int(6e9)

clk.set_requested_clocks(ref_in, output_clocks)

clk.solve()

o = clk.get_config()

pprint.pprint(o)

img = clk.draw()

with open("pll.svg", "w") as file:
    file.write(img)



