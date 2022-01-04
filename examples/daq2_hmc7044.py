# Determine clocking for DAQ2

import pprint
import adijif

vcxo = 125000000

sys = adijif.system("ad9680", "hmc7044", "xilinx", vcxo)

# Get Converter clocking requirements
sys.converter.sample_clock = 1e9
sys.converter.decimation = 1
sys.converter.L = 4
sys.converter.M = 2
sys.converter.N = 14
sys.converter.Np = 16
sys.converter.K = 32
sys.converter.F = 1
sys.Debug_Solver = False

# Get FPGA clocking requirements
sys.fpga.setup_by_dev_kit_name("zc706")
sys.fpga.force_qpll = 1

cfg = sys.solve()

print("Clock config:")
pprint.pprint(cfg["clock"])

print("FPGA config:")
pprint.pprint(cfg["converter"])

print("Converter config:")
pprint.pprint(cfg["fpga_AD9680"])
