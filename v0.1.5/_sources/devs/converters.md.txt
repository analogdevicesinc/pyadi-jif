# Converter Reference

(adijif-converters-ad9081)=
## AD9081

### AD9081 RX diagram

```{exec_code}
:hide_output: True
import adijif as jif

conv = jif.ad9081_rx()
conv.validate_config()
required_clocks = conv.get_required_clocks()
required_clock_names = conv.get_required_clock_names()
clks = []
for clock, name in zip(required_clocks, required_clock_names):
    clk = jif.types.arb_source(name)
    conv._add_equation(clk(conv.model) == clock)
    clks.append(clk)
solution = conv.model.solve(LogVerbosity="Quiet")
settings = conv.get_config(solution)
clock_values = {}
for clk in clks:
    clock_values.update(clk.get_config(solution))
settings["clocks"] = clock_values
image_data = conv.draw(settings["clocks"])
with open("ad9081_rx_diagram.svg", "w") as f:
    f.write(image_data)
#HIDE:START
import os, shutil
if os.path.exists("ad9081_rx_diagram.svg"):
    shutil.move("ad9081_rx_diagram.svg", "source/devs/ad9081_rx_diagram.svg")
#HIDE:STOP
```

```{figure} ad9081_rx_diagram.svg
---
name: ad9081_rx_diagram
width: 80%
---
AD9081 RX clock tree
```

### AD9081 TX diagram

```{exec_code}
:hide_output: True
import adijif as jif

conv = jif.ad9081_tx()
conv.validate_config()
required_clocks = conv.get_required_clocks()
required_clock_names = conv.get_required_clock_names()
clks = []
for clock, name in zip(required_clocks, required_clock_names):
    clk = jif.types.arb_source(name)
    conv._add_equation(clk(conv.model) == clock)
    clks.append(clk)
solution = conv.model.solve(LogVerbosity="Quiet")
settings = conv.get_config(solution)
clock_values = {}
for clk in clks:
    clock_values.update(clk.get_config(solution))
settings["clocks"] = clock_values
image_data = conv.draw(settings["clocks"])
with open("ad9081_tx_diagram.svg", "w") as f:
    f.write(image_data)
#HIDE:START
import os, shutil
if os.path.exists("ad9081_tx_diagram.svg"):
    shutil.move("ad9081_tx_diagram.svg", "source/devs/ad9081_tx_diagram.svg")
#HIDE:STOP
```

```{figure} ad9081_tx_diagram.svg
---
name: ad9081_tx_diagram
width: 80%
---
AD9081 TX clock tree
```

```{eval-rst}
.. automodule:: adijif.converters.ad9081.ad9081
   :members:
   :show-inheritance:
```

(adijif-converters-ad9082)=
## AD9082

### AD9082 RX diagram

```{exec_code}
:hide_output: True
import adijif as jif

conv = jif.ad9082_rx()
conv.validate_config()
required_clocks = conv.get_required_clocks()
required_clock_names = conv.get_required_clock_names()
clks = []
for clock, name in zip(required_clocks, required_clock_names):
    clk = jif.types.arb_source(name)
    conv._add_equation(clk(conv.model) == clock)
    clks.append(clk)
solution = conv.model.solve(LogVerbosity="Quiet")
settings = conv.get_config(solution)
clock_values = {}
for clk in clks:
    clock_values.update(clk.get_config(solution))
settings["clocks"] = clock_values
image_data = conv.draw(settings["clocks"])
with open("ad9082_rx_diagram.svg", "w") as f:
    f.write(image_data)
#HIDE:START
import os, shutil
if os.path.exists("ad9082_rx_diagram.svg"):
    shutil.move("ad9082_rx_diagram.svg", "source/devs/ad9082_rx_diagram.svg")
#HIDE:STOP
```

```{figure} ad9082_rx_diagram.svg
---
name: ad9082_rx_diagram
width: 80%
---
AD9082 RX clock tree
```

```{eval-rst}
.. automodule:: adijif.converters.ad9081.ad9082
   :members:
   :show-inheritance:
```

(adijif-converters-ad9084)=
## AD9084

### AD9084 RX diagram

```{exec_code}
:hide_output: True
import adijif as jif

conv = jif.ad9084_rx()
conv.validate_config()
required_clocks = conv.get_required_clocks()
required_clock_names = conv.get_required_clock_names()
clks = []
for clock, name in zip(required_clocks, required_clock_names):
    clk = jif.types.arb_source(name)
    conv._add_equation(clk(conv.model) == clock)
    clks.append(clk)
solution = conv.model.solve(LogVerbosity="Quiet")
settings = conv.get_config(solution)
clock_values = {}
for clk in clks:
    clock_values.update(clk.get_config(solution))
settings["clocks"] = clock_values
image_data = conv.draw(settings["clocks"])
with open("ad9084_rx_diagram.svg", "w") as f:
    f.write(image_data)
#HIDE:START
import os, shutil
if os.path.exists("ad9084_rx_diagram.svg"):
    shutil.move("ad9084_rx_diagram.svg", "source/devs/ad9084_rx_diagram.svg")
#HIDE:STOP
```

```{figure} ad9084_rx_diagram.svg
---
name: ad9084_rx_diagram
width: 80%
---
AD9084 RX clock tree
```

```{eval-rst}
.. automodule:: adijif.converters.ad9084.ad9084_rx
   :members:
   :show-inheritance:
```

(adijif-converters-ad9088)=
## AD9088

### AD9088 RX diagram

```{exec_code}
:hide_output: True
import adijif as jif

conv = jif.ad9088_rx()
conv.validate_config()
required_clocks = conv.get_required_clocks()
required_clock_names = conv.get_required_clock_names()
clks = []
for clock, name in zip(required_clocks, required_clock_names):
    clk = jif.types.arb_source(name)
    conv._add_equation(clk(conv.model) == clock)
    clks.append(clk)
solution = conv.model.solve(LogVerbosity="Quiet")
settings = conv.get_config(solution)
clock_values = {}
for clk in clks:
    clock_values.update(clk.get_config(solution))
settings["clocks"] = clock_values
image_data = conv.draw(settings["clocks"])
with open("ad9088_rx_diagram.svg", "w") as f:
    f.write(image_data)
#HIDE:START
import os, shutil
if os.path.exists("ad9088_rx_diagram.svg"):
    shutil.move("ad9088_rx_diagram.svg", "source/devs/ad9088_rx_diagram.svg")
#HIDE:STOP
```

```{figure} ad9088_rx_diagram.svg
---
name: ad9088_rx_diagram
width: 80%
---
AD9088 RX clock tree
```

```{eval-rst}
.. automodule:: adijif.converters.ad9084.ad9088_rx
   :members:
   :show-inheritance:
```

(adijif-converters-ad9680)=
## AD9680

### AD9680 diagram

```{exec_code}
:hide_output: True
import adijif as jif

conv = jif.ad9680()
conv.validate_config()
required_clocks = conv.get_required_clocks()
required_clock_names = conv.get_required_clock_names()
clks = []
for clock, name in zip(required_clocks, required_clock_names):
    clk = jif.types.arb_source(name)
    conv._add_equation(clk(conv.model) == clock)
    clks.append(clk)
solution = conv.model.solve(LogVerbosity="Quiet")
settings = conv.get_config(solution)
clock_values = {}
for clk in clks:
    clock_values.update(clk.get_config(solution))
settings["clocks"] = clock_values
image_data = conv.draw(settings["clocks"])
with open("ad9680_diagram.svg", "w") as f:
    f.write(image_data)
#HIDE:START
import os, shutil
if os.path.exists("ad9680_diagram.svg"):
    shutil.move("ad9680_diagram.svg", "source/devs/ad9680_diagram.svg")
#HIDE:STOP
```

```{figure} ad9680_diagram.svg
---
name: ad9680_diagram
width: 80%
---
AD9680 clock tree
```

```{eval-rst}
.. automodule:: adijif.converters.ad9680
   :members:
   :show-inheritance:
```

(adijif-converters-ad9144)=
## AD9144

### AD9144 diagram

```{exec_code}
:hide_output: True
import adijif as jif

conv = jif.ad9144()
conv.validate_config()
required_clocks = conv.get_required_clocks()
required_clock_names = conv.get_required_clock_names()
clks = []
for clock, name in zip(required_clocks, required_clock_names):
    clk = jif.types.arb_source(name)
    conv._add_equation(clk(conv.model) == clock)
    clks.append(clk)
solution = conv.model.solve(LogVerbosity="Quiet")
settings = conv.get_config(solution)
clock_values = {}
for clk in clks:
    clock_values.update(clk.get_config(solution))
settings["clocks"] = clock_values
image_data = conv.draw(settings["clocks"])
with open("ad9144_diagram.svg", "w") as f:
    f.write(image_data)
#HIDE:START
import os, shutil
if os.path.exists("ad9144_diagram.svg"):
    shutil.move("ad9144_diagram.svg", "source/devs/ad9144_diagram.svg")
#HIDE:STOP
```

```{figure} ad9144_diagram.svg
---
name: ad9144_diagram
width: 80%
---
AD9144 clock tree
```

```{eval-rst}
.. automodule:: adijif.converters.ad9144
   :members:
   :show-inheritance:
```

(adijif-converters-ad9152)=
## AD9152

### AD9152 diagram

```{exec_code}
:hide_output: True
import adijif as jif

conv = jif.ad9152()
conv.validate_config()
required_clocks = conv.get_required_clocks()
required_clock_names = conv.get_required_clock_names()
clks = []
for clock, name in zip(required_clocks, required_clock_names):
    clk = jif.types.arb_source(name)
    conv._add_equation(clk(conv.model) == clock)
    clks.append(clk)
solution = conv.model.solve(LogVerbosity="Quiet")
settings = conv.get_config(solution)
clock_values = {}
for clk in clks:
    clock_values.update(clk.get_config(solution))
settings["clocks"] = clock_values
image_data = conv.draw(settings["clocks"])
with open("ad9152_diagram.svg", "w") as f:
    f.write(image_data)
#HIDE:START
import os, shutil
if os.path.exists("ad9152_diagram.svg"):
    shutil.move("ad9152_diagram.svg", "source/devs/ad9152_diagram.svg")
#HIDE:STOP
```

```{figure} ad9152_diagram.svg
---
name: ad9152_diagram
width: 80%
---
AD9152 clock tree
```

```{eval-rst}
.. automodule:: adijif.converters.ad9152
   :members:
   :show-inheritance:
```

(adijif-converters-adrv9009)=
## ADRV9009

### ADRV9009 RX diagram

```{exec_code}
:hide_output: True
import adijif as jif

conv = jif.adrv9009_rx()
conv.sample_clock = 122.88e6
conv.decimation = 4
conv.set_quick_configuration_mode("17", "jesd204b")
conv.validate_config()
required_clocks = conv.get_required_clocks()
required_clock_names = conv.get_required_clock_names()
clks = []
for clock, name in zip(required_clocks, required_clock_names):
    clk = jif.types.arb_source(name)
    conv._add_equation(clk(conv.model) == clock)
    clks.append(clk)
solution = conv.model.solve(LogVerbosity="Quiet")
settings = conv.get_config(solution)
clock_values = {}
for clk in clks:
    clock_values.update(clk.get_config(solution))
settings["clocks"] = clock_values
image_data = conv.draw(settings["clocks"])
with open("adrv9009_rx_diagram.svg", "w") as f:
    f.write(image_data)
#HIDE:START
import os, shutil
if os.path.exists("adrv9009_rx_diagram.svg"):
    shutil.move("adrv9009_rx_diagram.svg", "source/devs/adrv9009_rx_diagram.svg")
#HIDE:STOP
```

```{figure} adrv9009_rx_diagram.svg
---
name: adrv9009_rx_diagram
width: 80%
---
ADRV9009 RX clock tree
```

### ADRV9009 TX diagram

```{exec_code}
:hide_output: True
import adijif as jif

conv = jif.adrv9009_tx()
conv.sample_clock = 122.88e6
conv.interpolation = 4
conv.set_quick_configuration_mode("6", "jesd204b")
conv.validate_config()
required_clocks = conv.get_required_clocks()
required_clock_names = conv.get_required_clock_names()
clks = []
for clock, name in zip(required_clocks, required_clock_names):
    clk = jif.types.arb_source(name)
    conv._add_equation(clk(conv.model) == clock)
    clks.append(clk)
solution = conv.model.solve(LogVerbosity="Quiet")
settings = conv.get_config(solution)
clock_values = {}
for clk in clks:
    clock_values.update(clk.get_config(solution))
settings["clocks"] = clock_values
image_data = conv.draw(settings["clocks"])
with open("adrv9009_tx_diagram.svg", "w") as f:
    f.write(image_data)
#HIDE:START
import os, shutil
if os.path.exists("adrv9009_tx_diagram.svg"):
    shutil.move("adrv9009_tx_diagram.svg", "source/devs/adrv9009_tx_diagram.svg")
#HIDE:STOP
```

```{figure} adrv9009_tx_diagram.svg
---
name: adrv9009_tx_diagram
width: 80%
---
ADRV9009 TX clock tree
```

```{eval-rst}
.. automodule:: adijif.converters.adrv9009
   :members:
   :show-inheritance:

```
