# Determine clocking for ADRV9009+ZC706

import adijif
import pprint

vcxo = 122.88e6
sys = adijif.system("adrv9009", "ad9528", "xilinx", vcxo, solver="CPLEX")

# vcxo = 200e6
# sys = adijif.system("adrv9009", "hmc7044", "xilinx", vcxo, solver="CPLEX")
# sys.Debug_Solver = True


# Get Converter clocking requirements
sys.converter.sample_clock = vcxo
sys.converter.L = 2
sys.converter.M = 4
sys.converter.N = 14
sys.converter.Np = 16

sys.converter.K = 32
sys.converter.F = 4
assert sys.converter.S == 1

assert sys.converter.bit_clock == vcxo*40

# Get FPGA clocking requirements
sys.fpga.setup_by_dev_kit_name("zc706")
# sys.fpga.request_fpga_core_clock_ref = True # force reference to be core clock rate

cfg = sys.solve()
pprint.pprint(cfg)
