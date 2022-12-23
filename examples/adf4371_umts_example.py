import pprint
import adijif

# Reference example from ADF4371 datasheet

######################

INT = 68
FRAC1 = 26039637
MOD2 = 1536
FRAC2 = 512
RF_DIV = 2

MOD1 = 2**25

D = 0
R = 1
T = 1

F_PFD = 122.88e6* (1+D)/(R*(1+T))

vco = (INT + (FRAC1 + FRAC2/MOD2)/MOD1) * F_PFD


print(f"F_PFD: {F_PFD/1e6} MHz")
print(f"VCO: {vco/1e6} MHz")
print(f"RF: {vco/RF_DIV/1e6} MHz")

######################

pll = adijif.adf4371()


ref_in = int(122.88e6)
output_clocks = int(2112.8e6)

pll.set_requested_clocks(ref_in, output_clocks)

pll.solve()

o = pll.get_config()

pprint.pprint(o)
