"""Tests demonstrating ADC/DAC converter component design with pysym backend.

This module shows how converter components would be designed with pysym
to enable solver abstraction and multi-solver support.
"""

import pytest

from adijif.pysym import BinaryVar, IntegerVar, Model
from adijif.solvers import cplex_solver


@pytest.mark.skipif(
    not cplex_solver,
    reason="CPLEX required"
)
class TestConverterWithPySym:
    """Test converter-like models using pysym backend."""

    def test_jesd_mode_selection(self):
        """Test JESD204 mode selection for ADC/DAC.

        Selects optimal JESD parameters for a converter:
        - M: number of ADC/DAC channels
        - L: number of JESD lanes
        - F: octets per frame
        - S: samples per frame
        - K: frames per multiframe

        Constraint: bitrate = (M * Np * Cs * 10/8) / (L * F)
        """
        model = Model(solver="CPLEX")

        # JESD parameters (typical ranges from standards)
        M = IntegerVar(domain=range(1, 9), name="M")  # Channels: 1-8
        L = IntegerVar(domain=[1, 2, 4, 8], name="L")  # Lanes: 1,2,4,8
        F = IntegerVar(domain=range(1, 256), name="F")  # Octets: 1-255
        K = IntegerVar(domain=[16, 32, 64], name="K")  # Multiframes

        model.add_variable(M)
        model.add_variable(L)
        model.add_variable(F)
        model.add_variable(K)

        # Sample rate (fixed for this example)

        # Constraint: Frame clock <= lane clock (simplified)
        # Frame clock = Cs / (M * F)
        # Lane clock = bitrate / 10
        # Assume bitrate ~ 6.144 Gbps, lane clock ~ 614.4 MHz
        # Frame clock <= lane clock => F >= M * Cs / lane_clock
        # For simplicity: F >= M (ensure valid timing)
        model.add_constraint(F >= M)

        # Constraint: K (multiframe size) must be valid
        model.add_constraint(K >= 16)

        # Objective: minimize total bandwidth (M * L * bitrate)
        # Simplified: minimize M * L to reduce complexity
        model.add_objective(M * L + K / 64, minimize=True)

        solution = model.solve()

        # Verify solution
        assert solution.is_feasible
        m_val = solution.get_value(M)
        l_val = solution.get_value(L)
        f_val = solution.get_value(F)
        k_val = solution.get_value(K)

        # Verify constraints
        assert f_val >= m_val

        # Verify domains
        assert 1 <= m_val <= 8
        assert l_val in [1, 2, 4, 8]
        assert 1 <= f_val <= 255
        assert k_val in [16, 32, 64]

    def test_adc_interpolation_filter(self):
        """Test ADC data path interpolation filter selection.

        Simulates selecting interpolation filter for ADC:
        - CIC filter decimation ratio
        - Final low-pass filter
        - Output sample rate matching system requirements
        """
        model = Model(solver="CPLEX")

        # Input sample rate (ADC sampling)

        # Filter decimation ratios (available options)
        cic_decimation = IntegerVar(
            domain=[1, 2, 4, 8, 16], name="cic_decimation"
        )
        fir_decimation = IntegerVar(
            domain=[1, 2, 3, 4, 5], name="fir_decimation"
        )

        model.add_variable(cic_decimation)
        model.add_variable(fir_decimation)

        # Output sample rate (required values in Hz)
        # Options: 30.72MHz, 61.44MHz, 122.88MHz, 245.76MHz
        output_rate = IntegerVar(domain=[30720000, 61440000, 122880000], name="output_rate")
        model.add_variable(output_rate)

        # Constraint: output_rate = f_adc / (cic_decimation * fir_decimation)
        # Simplified: ensure output rate is compatible with decimation
        # For each valid output, calculate required total decimation
        # This example uses simpler constraint: total decimation in valid range
        model.add_constraint(cic_decimation * fir_decimation >= 2)
        model.add_constraint(cic_decimation * fir_decimation <= 16)

        # Constraint: output rate must be within valid set
        model.add_constraint(output_rate >= 30720000)

        # Objective: minimize filter complexity (decimation ratio) + prefer lower output rate
        model.add_objective(cic_decimation * fir_decimation, minimize=True)

        solution = model.solve()

        # Verify solution
        assert solution.is_feasible
        cic_val = solution.get_value(cic_decimation)
        fir_val = solution.get_value(fir_decimation)
        out_val = solution.get_value(output_rate)

        # Verify constraints
        total_dec = cic_val * fir_val
        assert 2 <= total_dec <= 16

        # Verify domains
        assert cic_val in [1, 2, 4, 8, 16]
        assert 1 <= fir_val <= 5
        assert out_val in [30720000, 61440000, 122880000]

    def test_converter_feature_selection(self):
        """Test feature selection for converter configuration.

        Simulates selecting converter features based on system needs:
        - NCO (Numerically Controlled Oscillator) enabled
        - Gain settings
        - Filter options
        """
        model = Model(solver="CPLEX")

        # Feature flags
        use_nco = BinaryVar(name="use_nco")
        use_complex = BinaryVar(name="use_complex")

        # Gain setting (fixed-point values)
        gain = IntegerVar(domain=range(0, 32), name="gain")

        # Filter bandwidth selection
        bw = IntegerVar(domain=[1, 2, 4, 8, 16], name="bandwidth_mhz")

        model.add_variable(use_nco)
        model.add_variable(use_complex)
        model.add_variable(gain)
        model.add_variable(bw)

        # Constraint: complex mode requires NCO
        # If use_complex = 1, then use_nco = 1
        model.add_constraint(use_complex <= use_nco)

        # Constraint: gain >= 0
        model.add_constraint(gain >= 0)

        # Constraint: bandwidth selection
        # If NCO disabled, limit bandwidth
        # Simplified: always enable full bandwidth capability
        model.add_constraint(bw >= 1)

        # Objective: prefer simpler configuration (minimize enabled features)
        model.add_objective(use_nco + use_complex + (gain / 32) + (bw / 16), minimize=True)

        solution = model.solve()

        # Verify solution
        assert solution.is_feasible
        nco_val = solution.get_value(use_nco)
        cplx_val = solution.get_value(use_complex)
        gain_val = solution.get_value(gain)
        bw_val = solution.get_value(bw)

        # Verify constraints
        assert cplx_val <= nco_val  # Complex requires NCO
        assert 0 <= gain_val < 32
        assert bw_val >= 1

        # Verify domains
        assert nco_val in [0, 1]
        assert cplx_val in [0, 1]
        assert bw_val in [1, 2, 4, 8, 16]


class TestConverterDesignPatterns:
    """Document pysym patterns for converter component design."""

    def test_pysym_converter_pattern(self):
        """Show recommended pattern for converter design with pysym.

        This template demonstrates best practices for converter models:
        1. Define JESD/data path parameters as variables
        2. Add constraints relating parameters
        3. Define optimization objectives
        4. Solve with any supported solver
        """
        model = Model(solver="CPLEX")

        # Converter parameters
        m_channels = IntegerVar(domain=range(1, 5), name="m_channels")
        l_lanes = IntegerVar(domain=[1, 2, 4], name="l_lanes")
        n_bits = IntegerVar(domain=[12, 14, 16], name="n_bits")

        model.add_variable(m_channels)
        model.add_variable(l_lanes)
        model.add_variable(n_bits)

        # Constraint: ensure JESD link rate is valid
        # Simplified: N_bits * M <= 64 * L (fits in JESD lane)
        model.add_constraint(n_bits * m_channels <= 64 * l_lanes)

        # Objective: minimize lanes needed
        model.add_objective(l_lanes, minimize=True)

        solution = model.solve()

        # Verify solution
        assert solution.is_feasible
        m_val = solution.get_value(m_channels)
        l_val = solution.get_value(l_lanes)
        n_val = solution.get_value(n_bits)

        # Check constraint
        assert n_val * m_val <= 64 * l_val

        # Verify domains
        assert 1 <= m_val <= 4
        assert l_val in [1, 2, 4]
        assert n_val in [12, 14, 16]

    @pytest.mark.skipif(
        not cplex_solver,
        reason="CPLEX required"
    )
    def test_multi_converter_coordination(self):
        """Test coordinating multiple converters in a system.

        Shows how to model interactions between multiple ADCs/DACs:
        - Shared clock domains
        - Synchronization requirements
        - Data path constraints
        """
        model = Model(solver="CPLEX")

        # Two ADCs with independent JESD configurations
        adc1_M = IntegerVar(domain=[1, 2, 4], name="adc1_M")
        adc1_L = IntegerVar(domain=[1, 2, 4], name="adc1_L")

        adc2_M = IntegerVar(domain=[1, 2, 4], name="adc2_M")
        adc2_L = IntegerVar(domain=[1, 2, 4], name="adc2_L")

        model.add_variable(adc1_M)
        model.add_variable(adc1_L)
        model.add_variable(adc2_M)
        model.add_variable(adc2_L)

        # Constraint: total lanes <= 8 (FPGA limitation)
        model.add_constraint(adc1_L + adc2_L <= 8)

        # Constraint: if ADC1 has more channels, needs more lanes
        model.add_constraint(adc1_M <= adc1_L * 4)  # Max 4 channels per lane
        model.add_constraint(adc2_M <= adc2_L * 4)

        # Objective: minimize total lanes
        model.add_objective(adc1_L + adc2_L, minimize=True)

        solution = model.solve()

        # Verify solution
        assert solution.is_feasible
        adc1_m = solution.get_value(adc1_M)
        adc1_l = solution.get_value(adc1_L)
        adc2_m = solution.get_value(adc2_M)
        adc2_l = solution.get_value(adc2_L)

        # Check constraints
        assert adc1_l + adc2_l <= 8
        assert adc1_m <= adc1_l * 4
        assert adc2_m <= adc2_l * 4
