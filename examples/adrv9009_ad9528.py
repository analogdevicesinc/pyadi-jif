# Determine clocking for ADRV9009+ZC706

import adijif

vcxo = 122.88e6

sys = adijif.system("adrv9009", "ad9528", "xilinx", vcxo)

# Get Converter clocking requirements
sys.converter.sample_clock = 122.88e6 * 1
sys.converter.L = 2
sys.converter.M = 4
sys.converter.N = 14
sys.converter.Np = 16

sys.converter.K = 32
sys.converter.F = 4
assert sys.converter.S == 1
sys.Debug_Solver = True

assert 9830.4e6 / 2 == sys.converter.bit_clock
assert sys.converter.multiframe_clock == 7.68e6 / 2  # LMFC
assert sys.converter.device_clock == 9830.4e6 / 40 / 2

# Get FPGA clocking requirements
sys.fpga.setup_by_dev_kit_name("zc706")

sys.solve()

print("----- Clock config:")
for c in sys.clock.config:
    vs = sys.clock.config[c]
    for v in vs:
        if len(vs) > 1:
            print(c, v[0])
        else:
            print(c, v)

print("----- FPGA config:")
for c in sys.fpga.config:
    vs = sys.fpga.config[c]
    if not isinstance(vs, list) and not isinstance(vs, dict):
        print(c, vs.value)
        continue
    for v in vs:
        if len(vs) > 1:
            print(c, v[0])
        else:
            print(c, v)

print("----- Converter config:")
for c in sys.converter.config:
    vs = sys.converter.config[c]
    for v in vs:
        if len(vs) > 1:
            print(c, v[0])
        else:
            print(c, v)

print(
    "Lane rate FPGA",
    sys.fpga.config["vco_select"].value[0] / sys.fpga.config["d_select"].value[0],
)
print(
    "Lane rate Converter",
    sys.converter.bit_clock / sys.fpga.config["rate_divisor_select"].value[0],
)
