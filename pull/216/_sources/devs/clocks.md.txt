# Clock Chip Reference

(adijif-clocks-ad9523)=
## AD9523

### AD9523-1 diagram

```{exec_code}
:hide_output: True
import adijif as jif

clk = jif.ad9523_1()
output_clocks = [1000000000, 500000000, 7812500]
clock_names = ["ADC", "FPGA", "SYSREF"]
clk.set_requested_clocks(125000000, output_clocks, clock_names)
clk.solve()
clk.get_config()
image_data = clk.draw()
with open("ad9523_diagram.svg", "w") as f:
    f.write(image_data)
#HIDE:START
import os, shutil
if os.path.exists("ad9523_diagram.svg"):
    shutil.move("ad9523_diagram.svg", "source/devs/ad9523_diagram.svg")
#HIDE:STOP
```

```{figure} ad9523_diagram.svg
---
name: ad9523_diagram
width: 80%
---
AD9523-1 clock tree
```

```{eval-rst}
.. automodule:: adijif.clocks.ad9523
   :members:
   :show-inheritance:
```

(adijif-clocks-ad9528)=
## AD9528

### AD9528 diagram

```{exec_code}
:hide_output: True
import adijif as jif

clk = jif.ad9528()
output_clocks = [1000000000, 500000000, 7812500]
clock_names = ["ADC", "FPGA", "SYSREF"]
clk.set_requested_clocks(125000000, output_clocks, clock_names)
clk.solve()
clk.get_config()
image_data = clk.draw()
with open("ad9528_diagram.svg", "w") as f:
    f.write(image_data)
#HIDE:START
import os, shutil
if os.path.exists("ad9528_diagram.svg"):
    shutil.move("ad9528_diagram.svg", "source/devs/ad9528_diagram.svg")
#HIDE:STOP
```

```{figure} ad9528_diagram.svg
---
name: ad9528_diagram
width: 80%
---
AD9528 clock tree
```

```{eval-rst}
.. automodule:: adijif.clocks.ad9528
   :members:
   :show-inheritance:

```

(adijif-clocks-ad9545)=
## AD9545
```{eval-rst}
.. automodule:: adijif.clocks.ad9545
   :members:
   :show-inheritance:

```

(adijif-clocks-hmc7044)=
## HMC7044

### HMC7044 diagram

```{exec_code}
:hide_output: True
import adijif as jif

clk = jif.hmc7044()
output_clocks = [1000000000, 500000000, 7812500]
clock_names = ["ADC", "FPGA", "SYSREF"]
clk.set_requested_clocks(125000000, output_clocks, clock_names)
clk.solve()
clk.get_config()
image_data = clk.draw()
with open("hmc7044_diagram.svg", "w") as f:
    f.write(image_data)
#HIDE:START
import os, shutil
if os.path.exists("hmc7044_diagram.svg"):
    shutil.move("hmc7044_diagram.svg", "source/devs/hmc7044_diagram.svg")
#HIDE:STOP
```

```{figure} hmc7044_diagram.svg
---
name: hmc7044_diagram
width: 80%
---
HMC7044 clock tree
```

```{eval-rst}
.. automodule:: adijif.clocks.hmc7044
   :members:
   :show-inheritance:

```

(adijif-clocks-ltc6952)=
## LTC6952

### LTC6952 diagram

```{exec_code}
:hide_output: True
import adijif as jif

clk = jif.ltc6952()
output_clocks = [1000000000, 500000000, 7812500]
clock_names = ["ADC", "FPGA", "SYSREF"]
clk.set_requested_clocks(125000000, output_clocks, clock_names)
clk.solve()
clk.get_config()
image_data = clk.draw()
with open("ltc6952_diagram.svg", "w") as f:
    f.write(image_data)
#HIDE:START
import os, shutil
if os.path.exists("ltc6952_diagram.svg"):
    shutil.move("ltc6952_diagram.svg", "source/devs/ltc6952_diagram.svg")
#HIDE:STOP
```

```{figure} ltc6952_diagram.svg
---
name: ltc6952_diagram
width: 80%
---
LTC6952 clock tree
```

```{eval-rst}
.. automodule:: adijif.clocks.ltc6952
   :members:
   :show-inheritance:

```

(adijif-clocks-ltc6953)=
## LTC6953
```{eval-rst}
.. automodule:: adijif.clocks.ltc6953
   :members:
   :show-inheritance:

```