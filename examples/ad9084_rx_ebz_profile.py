# Determine ADSY1100 Configuration For RX

import adijif
import pprint
import os

vcxo = int(125e6)

here = os.path.dirname(os.path.abspath(__file__))
profile_json = os.path.join(
    here, "..", "tests", "apollo_profiles", "ad9084_profiles", "id00_stock_mode.json"
)

sys = adijif.system("ad9084_rx", "hmc7044", "xilinx", vcxo, solver="CPLEX")

sys.converter.apply_profile_settings(profile_json)

sys.fpga.setup_by_dev_kit_name("vcu118")

sys.converter.clocking_option = "direct"
sys.add_pll_inline("adf4382", vcxo, sys.converter)
sys.add_pll_sysref("adf4030", vcxo, sys.converter, sys.fpga)


sys.clock.minimize_feedback_dividers = False

print(f"Lane rate: {sys.converter.bit_clock/1e9} Gbps")
print(f"Needed Core clock: {sys.converter.bit_clock/66} MHz")

sys.converter._check_clock_relations()

cfg = sys.solve()

pprint.pprint(cfg)
