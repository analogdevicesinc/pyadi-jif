import pytest
import adijif

@pytest.mark.parametrize("solver", ["CPLEX"])
def test_fmcdaq3_system_smoke(solver):
    vcxo = 125000000
    # FMCDAQ3 has AD9680 (ADC) and AD9152 (DAC)
    sys = adijif.system(["ad9680", "ad9152"], "hmc7044", "xilinx", vcxo, solver=solver)
    sys.fpga.setup_by_dev_kit_name("zc706")

    # Configure AD9680 (ADC)
    adc = sys.converter[0]
    adc.sample_clock = 500e6
    adc.decimation = 1
    adc.set_quick_configuration_mode("1") # M=2, L=4, S=1, F=1

    # Configure AD9152 (DAC)
    dac = sys.converter[1]
    dac.sample_clock = 500e6
    dac.interpolation = 1
    dac.set_quick_configuration_mode("4") # M=2, L=4, S=1, F=1 (based on AD9144/AD9152 modes)

    # Solve system
    cfg = sys.solve()

    assert "clock" in cfg
    assert "converter" in cfg
    assert cfg["fpga_AD9680"]["type"] in ["cpll", "qpll"]
    assert cfg["fpga_AD9152"]["type"] in ["cpll", "qpll"]
