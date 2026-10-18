# Architecture Tools Reference

(adijif-plls-utils-adf4030-arch)=
## adijif.plls.utils.adf4030_arch

The architecture tooling for the ADF4030 (Aion) clock-distribution
PLL. `Adf4030Architecture` wraps the legacy free functions
(`Apollo_per_Aion_*`, `Aion_per_FPGA_*`) with a single object that
also exposes a textual summary and an SVG drawing method. The
`_connect_aions_*` helpers are private but documented here because
they are the load-bearing pieces of `draw()`.

```{eval-rst}
.. automodule:: adijif.plls.utils.adf4030_arch
   :members:
   :private-members:
   :show-inheritance:
```
