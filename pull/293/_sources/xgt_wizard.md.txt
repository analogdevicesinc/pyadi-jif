# Export to the HDL repo xgt_wizard flow

The [ADI HDL repository's xgt_wizard
flow](https://analogdevicesinc.github.io/hdl/library/jesd204/xgt_wizard/index.html)
automates Xilinx gigabit transceiver configuration. A project's
`system_project.tcl` calls `adi_xcvr_project` with a flat parameter list
(`LANE_RATE`, `REF_CLK`, `PLL_TYPE`, `JESD_MODE`, and optional `XCVR_RX_*`
overrides), and the block design script passes lane counts through
`adi_xcvr_parameters`. These parameters are also overridable at the make
level, e.g. `make LANE_RATE=10 REF_CLK=250 PLL_TYPE=QPLL0`.

pyadi-jif can map a solved system directly onto that contract with the
`adi.xgt-wizard` export format, so no hand-edited tcl is needed:

```python
solution = system.solve()
wizard = system.export_config(format="adi.xgt-wizard", solution=solution)
print(wizard.to_make_command("ad9081_fmca_ebz/zcu102"))
print(wizard.to_tcl())
```

Passing the existing `solution` avoids solving twice. If it is omitted,
`export_config()` solves the current system first.

## Solve and export an AD9081 + ZCU102 system

The complete runnable example is checked by the normal example test suite:

```{literalinclude} ../../examples/ad9081_zcu102_xgt_wizard.py
:language: python
:caption: examples/ad9081_zcu102_xgt_wizard.py
```

## What the exporter emits

Three renderings of the same frozen `XgtWizardConfig` snapshot:

- `to_make_command(project)` / `to_make_args()` — the exact make
  invocation for an HDL project, e.g.
  `make -C projects/ad9081_fmca_ebz/zcu102 LANE_RATE=23.925 REF_CLK=362.5
  PLL_TYPE=QPLL1 JESD_MODE=64B66B XCVR_RX_LANE_RATE=11.9625`
- `to_tcl()` — a sourceable snippet defining `adi_xcvr_project_args`
  (for `adi_xcvr_project` in `system_project.tcl`) and
  `adi_xcvr_parameters_args` (RX/TX lane counts for
  `adi_xcvr_parameters` in the block design script)
- `to_dict()` / `to_json()` — a structured snapshot for other tooling

### Primary direction and RX overrides

When both directions exist, TX is the primary direction: its lane rate,
reference clock, and PLL fill `LANE_RATE`, `REF_CLK`, and `PLL_TYPE`.
Each `XCVR_RX_*` override is emitted individually and only where the RX
value differs from TX. Single-direction systems emit no overrides.

## Supported scope

- 7-series and UltraScale+ transceivers using `CPLL`, `QPLL0` (solver
  type `qpll`), or `QPLL1`. Versal (`RPLL`/`LCPLL`) is rejected because
  the xgt_wizard flow does not cover it.
- The FPGA must be configured with `setup_by_dev_kit_name()` so the
  solved clock names (`<carrier>_<link>_ref_clk`) can be located.
- Note: the `ad9081_fmca_ebz/zcu102` HDL project has not yet adopted the
  xgt_wizard flow (`daq2`, `daq3`, and `adrv9371x` carriers have). The
  generated tcl variables are exactly what such a conversion sources.

## Agent and MCP access

The same export is available as the `export_xgt_wizard` operation for the
`jifagent` CLI (`jifagent call export_xgt_wizard ...`) and the `jifmcp`
MCP server. It accepts the same JSON system configuration as
`solve_system` plus an optional `hdl_project` string, and returns the
structured config, `make_args`, `tcl`, and (when `hdl_project` is given)
`make_command`.
