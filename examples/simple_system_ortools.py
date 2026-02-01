"""Simple system configuration using OR-Tools solver.

This example demonstrates how to compose a simple system using the
pysym framework with OR-Tools solver.

While the legacy adijif.system class works well for many use cases,
the pysym framework provides a more flexible foundation for:
  - Custom constraint programming problems
  - Education and learning (explicit constraint definition)
  - Integration with OR-Tools and other solvers
  - Fine-grained control over problem structure

This example shows:
  - Creating a pysym Model with OR-Tools
  - Defining a converter's JESD clock requirements
  - Defining a clock generator configuration
  - Composing constraints across components
  - Optimizing system-level objectives

This is an educational example that simplifies the actual converter
and clock models for clarity.

NOTE: This example requires OR-Tools. Install with:
    pip install 'pyadi-jif[ortools]'
"""

from adijif.pysym.model import Model
from adijif.pysym.variables import IntegerVar
import pprint

# ============================================================================
# Problem Description
# ============================================================================
#
# We have a simple system with:
#   - A converter (ADC/DAC) that needs JESD clock synchronization
#   - A clock generator (like HMC7044) providing the JESD clock
#   - An FPGA that processes data
#
# Constraints:
#   - Converter sample rate: configurable via PLL dividers
#   - JESD clock must be derived from converter sample clock
#   - Clock generator has limited divider ranges
#   - System must satisfy timing relationships
#
# Goal: Find configuration that minimizes power (lower divider ratios)

# ============================================================================
# System Configuration
# ============================================================================

# Reference frequency (common in high-speed systems)
REFERENCE_FREQ = 100_000_000  # 100 MHz

# Converter sample rate targets
# Typical AD9081: 1 - 6 GHz sample rate
MIN_SAMPLE_RATE = 500_000_000  # 500 MHz
MAX_SAMPLE_RATE = 4_000_000_000  # 4 GHz

# FPGA clock requirement
TARGET_FPGA_CLOCK = 200_000_000  # 200 MHz

# ============================================================================
# pysym Model - Define the System
# ============================================================================

model = Model(solver="ortools")

print("=" * 70)
print("Simple System Configuration with OR-Tools")
print("=" * 70)
print(f"\nReference Frequency: {REFERENCE_FREQ / 1e6:.1f} MHz")
print(f"Target FPGA Clock:   {TARGET_FPGA_CLOCK / 1e6:.1f} MHz")
print(f"Converter Sample Rate Range: {MIN_SAMPLE_RATE / 1e9:.1f} - {MAX_SAMPLE_RATE / 1e9:.1f} GHz")

# ============================================================================
# Converter: Sample Rate Configuration
# ============================================================================
#
# Simplified model: converter sample rate is determined by dividing
# a PLL VCO frequency.
#
# sample_rate = vco_freq / pll_divider

# PLL divider (typically 1-256)
pll_divider = IntegerVar(domain=range(1, 257), name="converter_pll_div")
model.add_variable(pll_divider)

# Assumed VCO frequency (simplified model - normally there's more complexity)
vco_freq = 2_000_000_000  # 2 GHz (typical PLL VCO)

# Constraint: sample rate must be in valid range
# sample_rate = vco_freq / pll_divider
# MIN <= vco_freq / pll_divider <= MAX
# vco_freq/MAX <= pll_divider <= vco_freq/MIN
min_div = vco_freq // MAX_SAMPLE_RATE
max_div = vco_freq // MIN_SAMPLE_RATE

model.add_constraint(pll_divider >= min_div)
model.add_constraint(pll_divider <= max_div)

# ============================================================================
# Clock Generator: FPGA Clock Configuration
# ============================================================================
#
# The clock generator derives the FPGA clock from a VCO, with an output divider.
#
# fpga_clock = vco_freq / fpga_output_div

# FPGA output divider (typically 1-4095 for HMC7044)
fpga_output_div = IntegerVar(domain=range(1, 4096), name="fpga_output_div")
model.add_variable(fpga_output_div)

# Constraint: FPGA clock should be close to target
# fpga_clock = 2000 MHz / fpga_output_div
# We want fpga_clock ≈ 200 MHz
# fpga_output_div ≈ 2000 / 200 = 10

expected_fpga_div = vco_freq // TARGET_FPGA_CLOCK
tolerance = max(1, expected_fpga_div // 10)  # ±10% tolerance

model.add_constraint(fpga_output_div >= expected_fpga_div - tolerance)
model.add_constraint(fpga_output_div <= expected_fpga_div + tolerance)

# ============================================================================
# System-Level Constraints
# ============================================================================
#
# In a real system, there are often relationships between components.
# For this simple example, we ensure the FPGA clock is reasonable:
# FPGA clock must be lower than sample rate / 4 (power of two relationship)

# sample_rate / 4 >= fpga_clock
# (vco_freq / pll_divider) / 4 >= (vco_freq / fpga_output_div)
# Simplified: (1 / pll_divider) / 4 >= (1 / fpga_output_div)
# 1 / (4 * pll_divider) >= 1 / fpga_output_div
# fpga_output_div >= 4 * pll_divider (approximately)

# This is a reasonable constraint to avoid overly fast FPGA clocks
model.add_constraint(fpga_output_div >= 2 * pll_divider)

# ============================================================================
# Objective
# ============================================================================
#
# Minimize total divider ratio for lower power consumption
# Lower dividers generally mean lower power in PLL systems

total_divider = pll_divider + fpga_output_div
model.add_objective(total_divider, minimize=True)

# ============================================================================
# Solve
# ============================================================================

print("\n" + "=" * 70)
print("Solving with OR-Tools...")
print("=" * 70)

solution = model.solve()

if solution.is_feasible:
    print("\n✓ Feasible solution found!")

    pll_div_val = solution.get_value(pll_divider)
    fpga_div_val = solution.get_value(fpga_output_div)

    # Calculate actual frequencies
    sample_rate = vco_freq / pll_div_val
    fpga_clock = vco_freq / fpga_div_val

    print("\n" + "=" * 70)
    print("System Configuration")
    print("=" * 70)

    print("\nConverter:")
    print(f"  PLL Divider:      {pll_div_val}")
    print(f"  VCO Frequency:    {vco_freq / 1e9:.1f} GHz")
    print(f"  Sample Rate:      {sample_rate / 1e9:.3f} GHz")

    print("\nClock Generator:")
    print(f"  Output Divider:   {fpga_div_val}")
    print(f"  FPGA Clock:       {fpga_clock / 1e6:.1f} MHz")
    print(f"  Target:           {TARGET_FPGA_CLOCK / 1e6:.1f} MHz")
    clock_error = abs(fpga_clock - TARGET_FPGA_CLOCK) / TARGET_FPGA_CLOCK * 100
    print(f"  Error:            {clock_error:.2f}%")

    print("\nSystem Summary:")
    print(f"  Total Divider Ratio: {pll_div_val + fpga_div_val}")

    config = {
        "REFERENCE": f"{REFERENCE_FREQ / 1e6:.1f} MHz",
        "CONVERTER": {
            "PLL_DIVIDER": pll_div_val,
            "VCO": f"{vco_freq / 1e9:.1f} GHz",
            "SAMPLE_RATE": f"{sample_rate / 1e9:.3f} GHz",
        },
        "CLOCK_GEN": {
            "OUTPUT_DIVIDER": fpga_div_val,
            "FPGA_CLOCK": f"{fpga_clock / 1e6:.1f} MHz",
            "TARGET": f"{TARGET_FPGA_CLOCK / 1e6:.1f} MHz",
        },
        "SYSTEM": {
            "TOTAL_DIVIDER_RATIO": pll_div_val + fpga_div_val,
        },
    }

    print("\n" + "=" * 70)
    print("Configuration Details")
    print("=" * 70)
    pprint.pprint(config)

    print("\nSystem Design complete!")
    print("Constraints satisfied:")
    print(f"  ✓ Sample rate in range: {MIN_SAMPLE_RATE / 1e9:.1f} - {MAX_SAMPLE_RATE / 1e9:.1f} GHz")
    print(f"  ✓ FPGA clock near target: {TARGET_FPGA_CLOCK / 1e6:.1f} MHz")
    print(f"  ✓ System timing relationships satisfied")

else:
    print("\n✗ No feasible solution found")
    print(f"Solver: {solution.solver_name}")
    print("\nThis may indicate:")
    print("  - Conflicting requirements")
    print("  - Insufficient divider ranges")
    print("  - Infeasible target frequencies")
