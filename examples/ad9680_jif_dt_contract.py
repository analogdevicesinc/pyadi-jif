"""Solve AD9680 clocks and export the versioned pyadi-jif -> pyadi-dt contract."""

import adijif

system = adijif.system("ad9680", "hmc7044", "xilinx", 125_000_000)
system.converter.sample_clock = 1_000_000_000
system.converter.decimation = 1
system.converter.set_quick_configuration_mode(str(0x88))
system.converter.K = 32
system.fpga.setup_by_dev_kit_name("zc706")
system.fpga.force_qpll = 1

solution = system.solve()
contract = system.export_config(format="adi.jif-dt", solution=solution)

# The JSON contains semantic requirements only. A pyadi-dt board profile maps
# them onto physical output channels and device-tree labels.
print(contract.to_json(), end="")
