# FPGA Reference

## AMD (Xilinx)

### Xilinx FPGA diagram

```{exec_code}
:hide_output: True
import adijif as jif

fpga = jif.xilinx()
fpga.setup_by_dev_kit_name("vcu118")

dc = jif.ad9680()

fpga_ref = jif.types.arb_source("FPGA_REF")
link_out_ref = jif.types.arb_source("LINK_OUT_REF")

clocks = fpga.get_required_clocks(dc, fpga_ref(fpga.model), link_out_ref(fpga.model))

solution = fpga.model.solve(LogVerbosity="Quiet")

settings = {}
clock_values = {}
for clk in [fpga_ref, link_out_ref]:
    clock_values.update(clk.get_config(solution))
settings["clocks"] = clock_values
settings["fpga"] = fpga.get_config(dc, settings["clocks"]["FPGA_REF"], solution)

image_data = fpga.draw(settings)
with open("xilinx_diagram.svg", "w") as f:
    f.write(image_data)
#HIDE:START
import os, shutil
if os.path.exists("xilinx_diagram.svg"):
    shutil.move("xilinx_diagram.svg", "source/devs/xilinx_diagram.svg")
#HIDE:STOP
```

```{figure} xilinx_diagram.svg
---
name: xilinx_diagram
width: 80%
---
Xilinx FPGA clock tree (VCU118 with AD9680)
```

```{eval-rst}

.. automodule:: adijif.fpgas.xilinx
   :members:
   :show-inheritance:

```

### AMD (Xilinx) Transceivers


#### AMD (Xilinx) 7 Series Transceivers
```{eval-rst}

.. automodule:: adijif.fpgas.xilinx.sevenseries
   :members:
   :show-inheritance:

```

#### AMD (Xilinx) UltraScale+ Transceivers
```{eval-rst}

.. automodule:: adijif.fpgas.xilinx.ultrascaleplus
   :members:
   :show-inheritance:

```

```{eval-rst}