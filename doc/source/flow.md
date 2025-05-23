# Usage Flows

**pyadi-jif** at its core is a modeling tool for configuration and can be used to determine configurations at the component and system levels.

-   _Component level_: Certain components can be isolated or used standalone like clock chip models. This is useful when compartmentalizing a problem or checking an existing configuration.
-   _System level_: When all or most of the top-level constraints need to be modeled together leveraging the system classes provides the most consistent connection between the constraints across the components that must work together.

## Component Level

When working at the component level each component's settings can be constrained or left unconstrained. Since each class's implementation will model possible settings as well as their limitations, any user-applied constraints are checked for validity. By default, all settings are left unconstrained. Constraints for divider settings and clocks can be scalars, lists, or even ranges. This applies to dividers and clock rates.

Below is an example of a configuration of a clock chip where the three desired output clocks and VCXO are supplied but the internal dividers need to be determined. The input divider **n2** is also constrained to 24 as well. Without applying this constraint, the solver could set **n2** to values between 12 and 255.

### AD9523-1 Component Example

```{exec_code}
:caption_output: Clock output
import adijif
import pprint
# Create instance of AD9523-1 clocking model
clk = adijif.ad9523_1()
# Constrain feedback divider n2 to only 24
clk.n2 = 24
# Define clock sources and output clocks
vcxo = 125000000
output_clocks = [1e9, 500e6, 7.8125e6]
clock_names = ["ADC", "FPGA", "SYSREF"]
clk.set_requested_clocks(vcxo, output_clocks, clock_names)
# Call solver and collect configuration
clk.solve()
o = clk.get_config()
pprint.pprint(o)

```

After the solver runs successfully, all the internal dividers and clocks are provided in a single dictionary.

Alternatively a range for the VCXO could be provided using the types classes as:

```python
vcxo = adijif.types.range(100000000, 251000000, 1000000, "vcxo")
```

In this case, any VCXO could be used in the range 100 MHz to 250 MHz in 1 MHz steps.

## System Level

When component constraints need to be mixed together the **system** class is used and is designed to support an FPGA, clock chip, and multiple data converters. Below is an example of the system class usage for a board similar to [AD-FMCDAQ2-EBZ](https://www.analog.com/en/design-center/evaluation-hardware-and-software/evaluation-boards-kits/eval-ad-fmcdaq2-ebz.html), but just looking at the ADC side alone.

### AD-FMCDAQ2-EBZ ADC Side System Example

```{exec_code}
:caption_output: System output
import adijif
import pprint
vcxo = 125000000
# Create instance of system class with desired parts
sys = adijif.system("ad9680", "ad9523_1", "xilinx", vcxo)
# Set Converter clocking requirements
sys.converter.sample_clock = 1e9
sys.converter.decimation = 1
sys.converter.L = 4
sys.converter.M = 2
sys.converter.N = 14
sys.converter.Np = 16
sys.converter.K = 32
sys.converter.F = 1
# Set FPGA clocking requirements
sys.fpga.setup_by_dev_kit_name("zc706")
# Call solver and collect configuration
config = sys.solve()
pprint.pprint(config)
```
The output in this case contains information for all three components. Listing divider settings, certain enabled modes, and clock rates. The ADC is directly clocked so it requires no configuration.

Alternatively, the output dividers **d** could be limited to power of two:

```{exec_code}
:caption_output: Clock output
# --- hide: start ---
import adijif
import pprint
vcxo = 125000000
# Create instance of system class with desired parts
sys = adijif.system("ad9680", "ad9523_1", "xilinx", vcxo)
# Set Converter clocking requirements
sys.converter.sample_clock = 1e9
sys.converter.decimation = 1
sys.converter.L = 4
sys.converter.M = 2
sys.converter.N = 14
sys.converter.Np = 16
sys.converter.K = 32
sys.converter.F = 1
# Set FPGA clocking requirements
sys.fpga.setup_by_dev_kit_name("zc706")
# --- hide: stop ---
sys.clock.d = [2**n for n in range(0,7)]
config = sys.solve()
pprint.pprint(config['clock'])
```
