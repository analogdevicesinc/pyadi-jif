# Determine AD9081+ZCU102 supported mode and clocking

import adijif
import pprint

vcxo = 100e6

sys = adijif.system("ad9081_rx", "hmc7044", "xilinx", vcxo, solver="CPLEX")
sys.fpga.setup_by_dev_kit_name("zcu102")
sys.Debug_Solver = False
sys.converter.use_direct_clocking = False
sys.fpga.request_fpga_core_clock_ref = True # force reference to be core clock rate
sys.converter.sample_clock = 250e6
sys.converter.datapath_decimation = 16

for mode in sys.converter.quick_configuration_modes_rx:
    sys._model_reset()
    try:
        sys.converter.set_quick_configuration_mode_rx(mode)
        cfg = sys.solve()
        
        print("Mode passed: ",mode)
        pprint.pprint(cfg)
        break

    except Exception as e:
        print("Mode failed: ",mode,e)
        continue
