from pprint import pprint
import adijif

vcxo = 125000000

sys = adijif.system("ad9680", "hmc7044", "xilinx", vcxo)

# Get Converter clocking requirements
sys.converter.sample_clock = 1e9
sys.converter.decimation = 1
sys.converter.set_quick_configuration_mode(str(0x88))
sys.converter.K = 32
sys.Debug_Solver = False

# Get FPGA clocking requirements
sys.fpga.setup_by_dev_kit_name("zc706")
sys.fpga.force_qpll = 1

cfg = sys.solve()

pprint(cfg)

# print("Clock config:")
# pprint.pprint(cfg["clock"])

# print("Converter config:")
# pprint.pprint(cfg["converter"])

print("FPGA config:")
pprint(cfg["fpga_AD9680"])

# print("JESD config:")
# pprint.pprint(cfg["jesd_AD9680"])

data = sys.draw(cfg)

with open("daq2_example.svg", "w") as f:
    f.write(data)
