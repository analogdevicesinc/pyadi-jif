# Generate HDL repo xgt_wizard (adi_xcvr_project) parameters for
# AD9081+ZCU102 from a solved configuration

import adijif

vcxo = 100e6
cddc = 6
fddc = 4

sys = adijif.system("ad9081", "hmc7044", "xilinx", vcxo, solver="CPLEX")
sys.fpga.setup_by_dev_kit_name("zcu102")
sys.fpga.ref_clock_constraint = "Unconstrained"
sys.fpga.sys_clk_select = "XCVR_QPLL0"  # Use faster QPLL
sys.converter.clocking_option = "integrated_pll"
sys.fpga.out_clk_select = "XCVR_PROGDIV_CLK"
sys.converter.adc.sample_clock = 2900000000 / (cddc * fddc)
sys.converter.dac.sample_clock = 5800000000 / (cddc * fddc)

sys.converter.adc.datapath.cddc_decimations = [cddc] * 4
sys.converter.adc.datapath.fddc_decimations = [fddc] * 8
sys.converter.adc.datapath.fddc_enabled = [True] * 8
sys.converter.dac.datapath.cduc_interpolation = cddc
sys.converter.dac.datapath.fduc_interpolation = fddc
sys.converter.dac.datapath.fduc_enabled = [True] * 8

# TX mode 4 (L=2 M=8 Np=12) and RX mode 1.0 both solve to 11.9625 Gbps,
# inside the GTHE4 line-rate range on the ZCU102.
sys.converter.dac.set_quick_configuration_mode("4", "jesd204c")
sys.converter.adc.set_quick_configuration_mode("1.0", "jesd204c")

cfg = sys.solve()

wiz = sys.export_config(format="adi.xgt-wizard", solution=cfg)

print("# Build command for the ADI HDL repo:")
print(wiz.to_make_command("ad9081_fmca_ebz/zcu102"))
print()
print("# Sourceable tcl for system_project.tcl / block design:")
print(wiz.to_tcl())
