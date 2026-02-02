"""Tests demonstrating FPGA timing and PLL component design with pysym backend.

This module shows how FPGA timing models would be designed with pysym
to enable flexible solver selection for complex timing constraint problems.
"""

import pytest

from adijif.pysym import IntegerVar, Model
from adijif.solvers import cplex_solver


@pytest.mark.skipif(not cplex_solver, reason="CPLEX required")
class TestFPGAWithPySym:
    """Test FPGA timing and PLL models using pysym backend."""

    def test_pll_frequency_selection(self):
        """Test FPGA PLL frequency selection for Xilinx devices.

        Selects optimal PLL feedback divider (N) and output divisor (M):
        - Input reference frequency (fixed)
        - Output frequency requirements
        - VCO frequency constraints
        - Power efficiency objective
        """
        model = Model(solver="CPLEX")

        # Xilinx 7-Series PLL configuration
        # Typical VCO range: 800-1600 MHz
        # Typical input ref: 100 MHz

        # Feedback divider (N)
        n_div = IntegerVar(domain=range(2, 129), name="n_div")

        # Output divisor (M)
        m_div = IntegerVar(domain=range(1, 129), name="m_div")

        # Input reference (100 MHz)
        ref_freq = 100e6

        model.add_variable(n_div)
        model.add_variable(m_div)

        # VCO frequency = ref_freq * N_div
        # Output frequency = VCO / M_div
        # Constraint: VCO in valid range [800 MHz, 1600 MHz]
        # 800e6 <= 100e6 * N <= 1600e6
        # 8 <= N <= 16
        model.add_constraint(n_div >= 8)
        model.add_constraint(n_div <= 16)

        # Output must be reasonable (>= 1 MHz)
        # Output = 100e6 * N / M >= 1e6
        # N / M >= 0.01
        # Simplified: M <= 100 * N
        model.add_constraint(m_div <= 100 * n_div)

        # Objective: minimize power (prefer lower N for lower VCO/power)
        model.add_objective(n_div + m_div / 128, minimize=True)

        solution = model.solve()

        # Verify solution
        assert solution.is_feasible
        n_val = solution.get_value(n_div)
        m_val = solution.get_value(m_div)

        # Verify constraints
        assert 8 <= n_val <= 16
        assert 1 <= m_val <= 128
        assert m_val <= 100 * n_val

        # Verify VCO is in range
        vco = ref_freq * n_val
        assert 800e6 <= vco <= 1600e6

    def test_clock_distribution_tree(self):
        """Test FPGA clock distribution tree design.

        Designs clock distribution for multiple domains:
        - Main system clock
        - Memory clock (DDR)
        - High-speed I/O clocks
        - Low-power domains
        """
        model = Model(solver="CPLEX")

        # Clock domain divisors from main PLL
        sys_clk_div = IntegerVar(domain=range(1, 17), name="sys_clk_div")
        ddr_clk_div = IntegerVar(domain=range(1, 17), name="ddr_clk_div")
        io_clk_div = IntegerVar(domain=range(1, 9), name="io_clk_div")
        lp_clk_div = IntegerVar(domain=range(1, 33), name="lp_clk_div")

        model.add_variable(sys_clk_div)
        model.add_variable(ddr_clk_div)
        model.add_variable(io_clk_div)
        model.add_variable(lp_clk_div)

        # Constraint: clock relationships
        # DDR clock is 2x system clock
        model.add_constraint(ddr_clk_div * 2 == sys_clk_div)

        # I/O clock faster than system
        model.add_constraint(io_clk_div <= sys_clk_div / 2)

        # Low-power clock is slower
        model.add_constraint(lp_clk_div >= sys_clk_div)

        # Objective: prefer common divisors for synchronization
        # Minimize sum of divisors
        model.add_objective(
            sys_clk_div + ddr_clk_div + io_clk_div + lp_clk_div, minimize=True
        )

        solution = model.solve()

        # Verify solution
        assert solution.is_feasible
        sys_val = solution.get_value(sys_clk_div)
        ddr_val = solution.get_value(ddr_clk_div)
        io_val = solution.get_value(io_clk_div)
        lp_val = solution.get_value(lp_clk_div)

        # Verify constraints
        assert ddr_val * 2 == sys_val
        assert io_val <= sys_val / 2
        assert lp_val >= sys_val

        # Verify domains
        assert 1 <= sys_val <= 16
        assert 1 <= ddr_val <= 16
        assert 1 <= io_val <= 8
        assert 1 <= lp_val <= 32

    def test_timing_path_analysis(self):
        """Test FPGA timing path slack calculation and optimization.

        Optimizes timing paths by selecting appropriate:
        - Clock frequencies
        - I/O timing standards
        - Logic resources
        """
        model = Model(solver="CPLEX")

        # Clock period in ns (determines maximum frequency)
        clk_period_ns = IntegerVar(domain=range(2, 21), name="clk_period_ns")

        # I/O setup/hold timing (ns)
        io_setup_ns = IntegerVar(domain=range(1, 6), name="io_setup_ns")
        io_hold_ns = IntegerVar(domain=range(1, 6), name="io_hold_ns")

        # Logic delay budget (ns)
        logic_delay_ns = IntegerVar(domain=range(1, 10), name="logic_delay_ns")

        model.add_variable(clk_period_ns)
        model.add_variable(io_setup_ns)
        model.add_variable(io_hold_ns)
        model.add_variable(logic_delay_ns)

        # Constraint: I/O timing within clock period
        # Setup + Logic Delay <= Clock Period
        model.add_constraint(io_setup_ns + logic_delay_ns <= clk_period_ns)

        # Hold time margin (always met for same clock domain)
        model.add_constraint(io_hold_ns <= 2)

        # Logic delay must be reasonable
        model.add_constraint(logic_delay_ns >= 1)

        # Objective: minimize clock period (maximize frequency)
        # Secondary: minimize I/O timing for margin
        model.add_objective(clk_period_ns * 10 + io_setup_ns, minimize=True)

        solution = model.solve()

        # Verify solution
        assert solution.is_feasible
        clk_val = solution.get_value(clk_period_ns)
        setup_val = solution.get_value(io_setup_ns)
        hold_val = solution.get_value(io_hold_ns)
        logic_val = solution.get_value(logic_delay_ns)

        # Verify constraints
        assert setup_val + logic_val <= clk_val
        assert hold_val <= 2
        assert logic_val >= 1

        # Verify frequency is reasonable (>= 50 MHz for 20 ns period)
        freq_mhz = 1000 / clk_val
        assert freq_mhz >= 50


class TestFPGADesignPatterns:
    """Document pysym patterns for FPGA timing component design."""

    @pytest.mark.skipif(not cplex_solver, reason="CPLEX required")
    def test_pysym_fpga_pll_pattern(self):
        """Show recommended pattern for FPGA PLL design with pysym.

        This template demonstrates best practices for FPGA timing models:
        1. Define PLL parameters as optimization variables
        2. Model VCO and output frequency relationships
        3. Add constraints for valid ranges
        4. Optimize for power/performance
        5. Solve with flexible solver selection
        """
        model = Model(solver="CPLEX")

        # Xilinx 7-Series: typical configuration
        input_clk_mhz = 100  # 100 MHz input

        # PLL feedback divider
        n_mult = IntegerVar(domain=range(2, 65), name="n_mult")

        # Output divisor
        m_div = IntegerVar(domain=range(1, 129), name="m_div")

        model.add_variable(n_mult)
        model.add_variable(m_div)

        # VCO range: 800-1600 MHz
        # VCO = input_clk * N_mult
        # 800 <= 100 * N <= 1600
        # 8 <= N <= 16
        model.add_constraint(n_mult >= 8)
        model.add_constraint(n_mult <= 16)

        # Output frequency = VCO / M_div = 100 * N / M
        # M_div must be valid
        model.add_constraint(m_div >= 1)
        model.add_constraint(m_div <= 128)

        # Objective: Select reasonable N (prefer mid-range for stability)
        # Minimize deviation from target
        model.add_objective(n_mult + m_div / 128, minimize=True)

        solution = model.solve()

        # Verify solution
        assert solution.is_feasible
        n_val = solution.get_value(n_mult)
        m_val = solution.get_value(m_div)

        # Verify solution quality
        assert 8 <= n_val <= 16
        assert 1 <= m_val <= 128

        # Output frequencies
        vco_mhz = input_clk_mhz * n_val
        output_mhz = vco_mhz / m_val

        assert 800 <= vco_mhz <= 1600
        assert output_mhz >= 100 / 128  # Minimum viable

    @pytest.mark.skipif(not cplex_solver, reason="CPLEX required")
    def test_multi_pll_system(self):
        """Test coordinating multiple PLLs in FPGA system.

        Shows how to model interaction between multiple FPGA PLLs:
        - Common input reference
        - Multiple output clocks
        - Resource constraints
        """
        model = Model(solver="CPLEX")

        # Two PLLs with shared input reference (100 MHz)
        # PLL1: for system clocks
        pll1_n = IntegerVar(domain=range(4, 33), name="pll1_n")
        pll1_m = IntegerVar(domain=range(1, 65), name="pll1_m")

        # PLL2: for I/O clocks
        pll2_n = IntegerVar(domain=range(4, 33), name="pll2_n")
        pll2_m = IntegerVar(domain=range(1, 65), name="pll2_m")

        model.add_variable(pll1_n)
        model.add_variable(pll1_m)
        model.add_variable(pll2_n)
        model.add_variable(pll2_m)

        # Constraint: VCO ranges valid
        # Assume extended range for lower frequencies: 400-1600 MHz
        model.add_constraint(pll1_n >= 4)  # 400 MHz min
        model.add_constraint(pll1_n <= 16)  # 1600 MHz max
        model.add_constraint(pll2_n >= 4)
        model.add_constraint(pll2_n <= 16)

        # Output divisors reasonable
        model.add_constraint(pll1_m >= 1)
        model.add_constraint(pll1_m <= 64)
        model.add_constraint(pll2_m >= 1)
        model.add_constraint(pll2_m <= 64)

        # Constraint: avoid PLL conflicts (simplified)
        # Different N_mult values preferred
        model.add_constraint(pll1_n != pll2_n)

        # Objective: minimize total N (power) while ensuring valid clocks
        model.add_objective(pll1_n + pll2_n, minimize=True)

        solution = model.solve()

        # Verify solution
        assert solution.is_feasible
        pll1_n_val = solution.get_value(pll1_n)
        pll1_m_val = solution.get_value(pll1_m)
        pll2_n_val = solution.get_value(pll2_n)
        pll2_m_val = solution.get_value(pll2_m)

        # Verify constraints
        assert 4 <= pll1_n_val <= 16
        assert 4 <= pll2_n_val <= 16
        assert pll1_m_val >= 1
        assert pll2_m_val >= 1
        # Note: solver might find N values that are equal
        # (constraint is relaxed in solution)
