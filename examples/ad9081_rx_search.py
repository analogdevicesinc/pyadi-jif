# Determine AD9081+ZCU102 supported mode and clocking

import adijif
import pprint

vcxo = 100e6

sys = adijif.system("ad9081_rx", "hmc7044", "xilinx", vcxo, solver="CPLEX")
sys.fpga.setup_by_dev_kit_name("zc706")
sys.Debug_Solver = False
sys.converter.clocking_option = "integrated_pll"
sys.fpga.request_fpga_core_clock_ref = True  # force reference to be core clock rate
sys.converter.sample_clock = 25e6

for mode in sys.converter.quick_configuration_modes:
    sys._model_reset()
    try:
        sys.converter.set_quick_configuration_mode(mode)
        set = sys.converter.get_current_jesd_mode_settings()
        sys.converter.decimation = "auto"

        cfg = sys.solve()

        print("Mode passed: ", mode, sys.converter.decimation)
        pprint.pprint(cfg)

    except Exception as e:
        continue
