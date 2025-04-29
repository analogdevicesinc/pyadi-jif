import pprint
import adijif

# Reference example from AD9084 system

######################

pll = adijif.adf4382()


ref_in = int(125e6/2)
output_clocks = int(8e9)
pll.n = 128 # Y
pll.d = 1 # Y
pll.o = 2 # Y



# adf4382 spi3.0: VCO=16000000000 PFD=62500000 RFout_div=2 N=128 FRAC1=0 FRAC2=0 MOD2=0
o = 2 #  
n = 128 #
d = 1 # 1
r = 1
vco = ref_in * d * n * o / r
out = vco / o
print(f"VCO: {vco}")
print(f"Output: {out}") 


pll.set_requested_clocks(ref_in, output_clocks)

pll.solve()

cfg = pll.get_config()

pprint.pprint(cfg)

pfd = ref_in * cfg["d"] / cfg["r"]
vco = pfd * cfg["n"] * cfg["o"]
rf_out = vco / cfg["o"]

print(f"PFD: {pfd}")
print(f"VCO: {vco}")
print(f"RF Out: {rf_out}")

assert rf_out == output_clocks, "Output frequency does not match requested"
