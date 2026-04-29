"""Apply custom constraints to the inter-component clocks of an adijif.system.

`system.initialize()` returns a `ClocksBundle` (a dict) keyed by clock name
that maps to the solver expression for every clock that flows between high
level components (clock chip <-> converter, clock chip <-> FPGA, etc.). Use
the bundle to add range / equality / OR constraints that go beyond the
equality-only `out_clock_constraints` shortcut, then call `do_solve()`.

Two equivalent flows are shown below: a manual two-step path, and a single
`solve(constrain=...)` callback.
"""

import pprint

import adijif
from adijif.sys import ClocksBundle


def _build_daq2_system() -> adijif.system:
    sys = adijif.system("ad9680", "ad9523_1", "xilinx", 125e6)
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.converter.sample_clock = 1e9
    sys.converter.decimation = 1
    sys.converter.L = 4
    sys.converter.M = 2
    sys.converter.N = 14
    sys.converter.Np = 16
    sys.converter.K = 32
    sys.converter.F = 1
    return sys


def two_step_example() -> dict:
    """Initialize, constrain, then do_solve."""
    sys = _build_daq2_system()

    clocks = sys.initialize()
    print("Inter-component clocks available for constraining:")
    for name in sorted(clocks):
        print(f"  - {name}")

    # Force the FPGA reference clock into a 250-350 MHz window and pick an
    # exact sysref rate.
    clocks.constrain("AD9680_fpga_ref_clk", range=(250e6, 350e6))
    clocks.constrain("AD9680_sysref", equal_to=7.8125e6)

    return sys.do_solve()


def callback_example() -> dict:
    """Pass a constraint callback to solve()."""
    sys = _build_daq2_system()

    def constrain(clocks: ClocksBundle) -> None:
        clocks.constrain("AD9680_fpga_ref_clk", range=(250e6, 350e6))
        clocks.constrain("AD9680_sysref", equal_to=7.8125e6)

    return sys.solve(constrain=constrain)


if __name__ == "__main__":
    print("=== Two-step initialize / constrain / do_solve ===")
    cfg_two_step = two_step_example()
    pprint.pprint(cfg_two_step["clock"]["output_clocks"])

    print("\n=== solve(constrain=callback) ===")
    cfg_callback = callback_example()
    pprint.pprint(cfg_callback["clock"]["output_clocks"])
