# Determine ADSY1100 Configuration For RX

import adijif
import pprint

vcxo = int(125e6)
cddc_dec  = 4
fddc_dec  = 2
converter_rate = int(14e9)

sys = adijif.system("ad9084_rx", "hmc7044", "xilinx", vcxo, solver="CPLEX")

sys.fpga.setup_by_dev_kit_name("adsy1100")
sys.converter.sample_clock = converter_rate / (cddc_dec * fddc_dec)
sys.converter.datapath.cddc_decimations = [cddc_dec] * 4
sys.converter.datapath.fddc_decimations = [fddc_dec] * 8
sys.converter.datapath.fddc_enabled = [True] * 8

sys.converter.clocking_option = "direct"
sys.add_pll_inline("adf4382", vcxo, sys.converter)
sys.add_pll_sysref("adf4030", vcxo, sys.converter, sys.fpga, bsync_reference=sys.clock)

sys.clock.minimize_feedback_dividers = False
sys.clock.vco_min = 2e9

mode_rx = adijif.utils.get_jesd_mode_from_params(
    sys.converter, M=4, L=8, S=1, Np=16, jesd_class="jesd204c"
)
print(f"RX JESD Mode: {mode_rx}")
assert mode_rx
mode_rx = mode_rx[0]['mode']

sys.converter.set_quick_configuration_mode(mode_rx, "jesd204c")


print(f"Lane rate: {sys.converter.bit_clock/1e9} Gbps")
print(f"Needed Core clock: {sys.converter.bit_clock/66} MHz")

sys.converter._check_clock_relations()

cfg = sys.solve()

pprint.pprint(cfg)

# Draw
data = sys.draw(cfg)
with open("ad9084_rx_hmc7044_ext_pll_adf4382.svg", "w") as f:
    f.write(data)

## Generate make commands for HDL
mode = "64B66B" if sys.converter.jesd_class == "jesd204c" else "8B10B"
make_cmd = f"JESD_MODE={mode} " \
    +f"RX_RATE={sys.converter.bit_clock/1e9:.4f} TX_RATE={sys.converter.bit_clock/1e9:.4f} " \
    +f"RX_JESD_M={sys.converter.M} TX_JESD_M={sys.converter.M} " \
    +f"RX_JESD_L={sys.converter.L} TX_JESD_L={sys.converter.L} " \
    +f"RX_JESD_S={sys.converter.S} TX_JESD_S={sys.converter.S} " \
    +f"RX_JESD_NP={sys.converter.Np} TX_JESD_NP={sys.converter.Np} " \
    +f"RX_B_RATE={sys.converter.bit_clock/1e9:.4f} TX_B_RATE={sys.converter.bit_clock/1e9:.4f} " \
    +f"RX_B_JESD_M={sys.converter.M} TX_B_JESD_M={sys.converter.M} " \
    +f"RX_B_JESD_L={sys.converter.L} TX_B_JESD_L={sys.converter.L} " \
    +f"RX_B_JESD_S={sys.converter.S} TX_B_JESD_S={sys.converter.S} " \
    +f"RX_B_JESD_NP={sys.converter.Np} TX_B_JESD_NP={sys.converter.Np}"

print("Make command:")
print(make_cmd)

# ltc_vco = cfg['clock']['VCO']
# adf_vco = cfg['clock_ext_pll_sysref_adf4030']['vco']

# ltc_output_divs = sys.clock._d
# adf_output_divs = sys._plls_sysref[0]._o

# found = False
# for i, div in enumerate(ltc_output_divs):
#     for j, adf_div in enumerate(adf_output_divs):
#         ltc_out = ltc_vco / div
#         adf_out = adf_vco / adf_div
#         if adf_out > 10e6:
#             continue
#         # Check adf_out is a whole number
#         if abs(adf_out - round(adf_out)) > 0.00000000001:
#             continue
#         if abs(ltc_out - adf_out) < 0.0001:
#             print(f"Match found: LTC6952 output {i} with divider {div} = {ltc_out/1e6:.3f} MHz, "
#                   f"ADF4030 output {j} with divider {adf_div} = {adf_out} Hz")
#             found = True
#             break
#     if found:
#         break
