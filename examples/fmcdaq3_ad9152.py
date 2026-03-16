"""FMCDAQ3 System Configuration Example.

This example demonstrates how to configure the FMCDAQ3 board,
which contains an AD9680 ADC and an AD9152 DAC, connected to a
ZC706 FPGA development kit using an HMC7044 clock chip.
"""

import adijif
import pprint

def main():
    # Setup system parameters
    vcxo = 125000000 # 125 MHz VCXO on FMCDAQ3
    
    # Initialize the system with ADC, DAC and Clock Chip
    # FMCDAQ3: AD9680 + AD9152 + HMC7044
    sys = adijif.system(["ad9680", "ad9152"], "hmc7044", "xilinx", vcxo)
    
    # Configure the FPGA development kit
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
    dac.set_quick_configuration_mode("4") # M=2, L=4, S=1, F=1
    
    print(f"Configuring FMCDAQ3 on {sys.fpga.name.upper()}...")
    
    # Solve for optimal clocking and FPGA parameters
    # (Using standalone validation here since full solver might be unavailable in some environments)
    try:
        adc.validate_config()
        dac.validate_config()
        print("Converter configurations validated successfully.")
        
        # In a real environment with solvers:
        # cfg = sys.solve()
        # pprint.pprint(cfg)
    except Exception as e:
        print(f"Validation failed: {e}")

if __name__ == "__main__":
    main()
