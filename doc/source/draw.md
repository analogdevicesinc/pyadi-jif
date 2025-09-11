# Drawings

**pyadi-jif** has been extended to generate diagrams of the clock trees for components and systems. This is done using the [d2lang](https://d2lang.com/) language.

## Pre-requisites

To generate the diagrams, you will need to leverage the d2 interface support provided by **pyadi-jif**. This is done by either installing [pyd2lang-native](https://pypi.org/project/pyd2lang-native/) or by building the d2lang interface from source.

To build the d2lang interface from source will require the [go](https://golang.org/dl/) on your system. Once available run the build script to generate the interface library:

```bash
cd adijif/d2
chmod +x build.sh
./build.sh
```
This will create a shared object library in the `adijif/d2` directory. This is the only requirement to generate diagrams.

## Generating diagrams

Generating diagrams is done by calling the `draw` method on the system or component object. This will generate a diagram of the clock tree. Drawing is only valid once the component or system has been solved. Here is an example of generating a diagram for the AD9680 and dummy sources:

```{exec_code}
:hide_output: True
import adijif as jif

adc = jif.ad9680()

# Check static
adc.validate_config()

required_clocks = adc.get_required_clocks()
required_clock_names = adc.get_required_clock_names()

# Add generic clock sources for solver
clks = []
for clock, name in zip(required_clocks, required_clock_names):
    clk = jif.types.arb_source(name)
    adc._add_equation(clk(adc.model) == clock)
    clks.append(clk)

# Solve
solution = adc.model.solve(LogVerbosity="Quiet")
settings = adc.get_config(solution)

# Get clock values
clock_values = {}
for clk in clks:
    clock_values.update(clk.get_config(solution))
settings["clocks"] = clock_values

image_data = adc.draw(settings["clocks"])

with open("ad9680_example.svg", "w") as f:
    f.write(image_data)
#HIDE:START
import os
import shutil
# Move to source
if os.path.exists("ad9680_example.svg"):
    shutil.move("ad9680_example.svg", "source/ad9680_example.svg")
else:
    print("File not found")
#HIDE:STOP
```

This will generate a file called `ad9680_example.svg` in the current working directory. This file can be opened in any SVG viewer. The diagram will look similar to the one below:

```{figure} ad9680_example.svg
---
name: ad9680_example
width: 80%
---
```

### Generating System Diagrams

The same process can be used to generate diagrams for systems. The only difference is that the system object must be used instead of the component object. Here is an example of generating a diagram for the AD9680 and AD9144:

```{exec_code}
:hide_output: True
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

data = sys.draw(cfg)

with open("daq2_example.svg", "w") as f:
    f.write(data)

#HIDE:START
import os
import shutil
# Move to source
if os.path.exists("daq2_example.svg"):
    shutil.move("daq2_example.svg", "source/daq2_example.svg")
else:
    print("File not found")
#HIDE:STOP
```

This will generate a file called `daq2_example.svg` in the current working directory. This file can be opened in any SVG viewer. The diagram will look similar to the one below:

```{figure} daq2_example.svg
---
name: daq2_example
width: 80%
---
```
