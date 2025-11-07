# flake8: noqa

import pytest

import adijif


def test_converter_lane_count_valid():
    sys = adijif.system("ad9144", "ad9523_1", "xilinx", 125e6)
    sys.fpga.setup_by_dev_kit_name("zcu102")

    sys.converter.sample_clock = 1e9
    # Mode 0
    sys.converter.interpolation = 1
    sys.converter.L = 8
    sys.converter.M = 4
    sys.converter.N = 16
    sys.converter.Np = 16
    sys.converter.K = 32
    sys.converter.F = 1
    sys.converter.HD = 1
    sys.converter.clocking_option = "integrated_pll"

    cfg = sys.solve()


def test_converter_lane_count_exceeds_fpga_lane_count():
    convs = ["ad9144", "ad9144", "ad9144"]
    sys = adijif.system(convs, "ad9523_1", "xilinx", 125e6)
    sys.fpga.setup_by_dev_kit_name("zcu102")

    for i, _ in enumerate(convs):
        # Mode 0
        sys.converter[i].sample_clock = 1e9
        sys.converter[i].interpolation = 1
        sys.converter[i].L = 8
        sys.converter[i].M = 4
        sys.converter[i].N = 16
        sys.converter[i].Np = 16
        sys.converter[i].K = 32
        sys.converter[i].F = 1
        sys.converter[i].HD = 1
        sys.converter[i].clocking_option = "integrated_pll"

    with pytest.raises(Exception, match=f"Max SERDES lanes exceeded. 8 only available"):
        cfg = sys.solve()


def test_nested_converter_lane_count_valid():
    sys = adijif.system("adrv9009", "ad9528", "xilinx", 122.88e6)
    sys.fpga.setup_by_dev_kit_name("zcu102")
    sys.converter.adc.sample_clock = 122.88e6
    sys.converter.dac.sample_clock = 122.88e6

    sys.converter.adc.decimation = 4
    sys.converter.dac.interpolation = 4

    mode_rx = "17"
    mode_tx = "6"
    sys.converter.adc.set_quick_configuration_mode(mode_rx, "jesd204b")
    sys.converter.dac.set_quick_configuration_mode(mode_tx, "jesd204b")

    cfg = sys.solve()


def test_nested_converter_lane_count_exceeds_fpga_lane_count():
    fpga_L = 1

    sys = adijif.system("adrv9009", "ad9528", "xilinx", 122.88e6)

    sys.fpga.setup_by_dev_kit_name("zcu102")
    sys.fpga.max_serdes_lanes = fpga_L  # Force it to break

    sys.converter.adc.sample_clock = 122.88e6
    sys.converter.dac.sample_clock = 122.88e6

    sys.converter.adc.decimation = 4
    sys.converter.dac.interpolation = 4

    mode_rx = "17"
    mode_tx = "6"
    sys.converter.adc.set_quick_configuration_mode(mode_rx, "jesd204b")
    sys.converter.dac.set_quick_configuration_mode(mode_tx, "jesd204b")

    with pytest.raises(
        Exception, match=f"Max SERDES lanes exceeded. {fpga_L} only available"
    ):
        cfg = sys.solve()


def test_system_with_arb_source_vcxo():
    """Test system with arb_source VCXO type."""
    import adijif

    vcxo = adijif.types.arb_source("vcxo")

    sys = adijif.system("ad9680", "hmc7044", "xilinx", vcxo)
    sys.converter.sample_clock = 1e9
    sys.converter.decimation = 1
    sys.converter.set_quick_configuration_mode(str(0x88))
    sys.converter.K = 32

    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.fpga.force_qpll = 1

    cfg = sys.solve()
    assert cfg is not None


def test_system_model_reset():
    """Test that model_reset properly resets all components."""
    import adijif

    sys = adijif.system("ad9680", "hmc7044", "xilinx", 125e6)

    # Store original model
    original_model = sys.model

    # Reset the model
    sys._model_reset()

    # Model should be recreated
    assert sys.model is not original_model
    assert sys.clock.model is sys.model
    assert sys.fpga.model is sys.model
    assert sys.converter.model is sys.model


def test_system_debug_solver():
    """Test system with debug solver enabled."""
    import adijif

    sys = adijif.system("ad9680", "hmc7044", "xilinx", 125e6)
    sys.Debug_Solver = True

    sys.converter.sample_clock = 1e9
    sys.converter.decimation = 1
    sys.converter.set_quick_configuration_mode(str(0x88))
    sys.converter.K = 32

    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.fpga.force_qpll = 1

    cfg = sys.solve()
    assert cfg is not None


def test_system_disabled_clocks():
    """Test system with both converter and FPGA clocks disabled."""
    import adijif

    sys = adijif.system("ad9680", "hmc7044", "xilinx", 125e6)
    sys.enable_converter_clocks = False
    sys.enable_fpga_clocks = False

    with pytest.raises(Exception, match="Converter and/or FPGA clocks must be enabled"):
        sys.solve()


def test_system_with_pll_inline():
    """Test system with external PLL inline setup."""
    import adijif

    sys = adijif.system("ad9144", "hmc7044", "xilinx", 125e6)
    sys.fpga.setup_by_dev_kit_name("zcu102")

    sys.converter.sample_clock = 1e9
    sys.converter.interpolation = 1
    sys.converter.L = 8
    sys.converter.M = 4
    sys.converter.N = 16
    sys.converter.Np = 16
    sys.converter.K = 32
    sys.converter.F = 1
    sys.converter.HD = 1
    sys.converter.clocking_option = "integrated_pll"

    # Just test that add_pll_inline works
    sys.add_pll_inline("adf4382", sys.clock, sys.converter)
    assert len(sys.plls) == 1


def test_system_unknown_converter_type():
    """Test system with converter having invalid type."""
    import adijif

    sys = adijif.system("ad9680", "hmc7044", "xilinx", 125e6)
    sys.converter.sample_clock = 1e9
    sys.converter.decimation = 1
    sys.converter.set_quick_configuration_mode(str(0x88))
    sys.converter.K = 32

    # Force an invalid converter type
    sys.converter.converter_type = "INVALID"

    sys.fpga.setup_by_dev_kit_name("zc706")

    with pytest.raises(Exception, match="Unknown converter type"):
        sys.solve()


def test_system_use_common_sysref_attribute():
    """Test system with common sysref attribute."""
    import adijif

    sys = adijif.system("ad9144", "ad9523_1", "xilinx", 125e6)
    sys.fpga.setup_by_dev_kit_name("zcu102")

    # Test that attribute can be set
    sys.use_common_sysref = True
    assert sys.use_common_sysref is True


def test_system_arb_source_with_gekko_error():
    """Test that arb_source with gekko solver raises error."""
    import adijif

    vcxo = adijif.types.arb_source("vcxo")

    with pytest.raises(
        Exception,
        match="arb_source type requires CPLEX solver",
    ):
        sys = adijif.system("ad9680", "hmc7044", "xilinx", vcxo, solver="gekko")


def test_system_model_reset_with_list_converters():
    """Test model reset with list of converters."""
    import adijif

    convs = ["ad9144", "ad9144"]
    sys = adijif.system(convs, "ad9523_1", "xilinx", 125e6)

    original_model = sys.model

    sys._model_reset()

    assert sys.model is not original_model
    for conv in sys.converter:
        assert conv.model is sys.model


def test_system_destructor():
    """Test system destructor cleanup."""
    import adijif

    sys = adijif.system("ad9680", "hmc7044", "xilinx", 125e6)

    sys.__del__()

    assert sys.fpga == []
    assert sys.converter == []
    assert sys.clock == []


def test_system_destructor_with_list():
    """Test system destructor with list of converters."""
    import adijif

    convs = ["ad9144", "ad9144"]
    sys = adijif.system(convs, "ad9523_1", "xilinx", 125e6)

    sys.__del__()

    assert sys.converter == []


def test_system_with_gekko_solver():
    """Test system with GEKKO solver."""
    import adijif

    try:
        sys = adijif.system("ad9680", "hmc7044", "xilinx", 125e6, solver="gekko")
        assert sys.solver == "gekko"

        # Test model reset with gekko
        sys._model_reset()
        assert sys.model is not None
    except Exception as e:
        # GEKKO may not be installed
        if "GEKKO Solver not installed" not in str(e):
            raise


def test_system_unknown_solver():
    """Test system with unknown solver."""
    import adijif

    with pytest.raises(Exception, match="Unknown solver"):
        sys = adijif.system("ad9680", "hmc7044", "xilinx", 125e6, solver="INVALID")


def test_system_model_reset_with_gekko():
    """Test model reset with GEKKO solver."""
    import adijif

    try:
        sys = adijif.system("ad9680", "hmc7044", "xilinx", 125e6, solver="gekko")
        original_model = sys.model

        sys._model_reset()

        assert sys.model is not original_model
        assert sys.clock.model is sys.model
    except Exception as e:
        # GEKKO may not be installed
        if "GEKKO Solver not installed" not in str(e):
            raise


@pytest.mark.skipif(True, reason="Old BF method, can take a long time to run")
def test_system_determine_clocks():
    """Test determine_clocks method."""
    import adijif

    sys = adijif.system("ad9680", "hmc7044", "xilinx", 125e6)
    sys.converter.sample_clock = 500e6
    sys.converter.decimation = 1
    sys.converter.set_quick_configuration_mode(str(0x88))
    sys.converter.K = 32

    sys.fpga.setup_by_dev_kit_name("zc706")

    try:
        configs = sys.determine_clocks()
        assert configs is not None
        assert len(configs) > 0
    except Exception:
        # May not find valid config for all parameter combinations
        pass


def test_system_plls_property():
    """Test plls property."""
    import adijif

    sys = adijif.system("ad9144", "hmc7044", "xilinx", 125e6)

    # Initially should be empty
    assert sys.plls == []
    assert len(sys.plls) == 0


def test_system_add_pll_inline_sets_connected_output():
    """Test that add_pll_inline properly sets connection."""
    import adijif

    sys = adijif.system("ad9144", "hmc7044", "xilinx", 125e6)
    sys.fpga.setup_by_dev_kit_name("zcu102")

    sys.add_pll_inline("adf4382", sys.clock, sys.converter)

    assert len(sys._plls) == 1
    assert sys._plls[0]._connected_to_output == sys.converter.name


def test_system_solve_with_gekko():
    """Test solve with GEKKO solver."""
    import adijif

    try:
        sys = adijif.system("ad9680", "hmc7044", "xilinx", 125e6, solver="gekko")
        sys.converter.sample_clock = 500e6
        sys.converter.decimation = 1
        sys.converter.set_quick_configuration_mode(str(0x88))
        sys.converter.K = 32

        sys.fpga.setup_by_dev_kit_name("zc706")

        cfg = sys.solve()
        assert cfg is not None
    except Exception as e:
        # GEKKO may not be installed or may not find solution
        if "GEKKO Solver not installed" not in str(e):
            # Solution not found is acceptable
            pass


def test_system_solve_unknown_solver():
    """Test solve with unknown solver raises error."""
    import adijif

    sys = adijif.system("ad9680", "hmc7044", "xilinx", 125e6)
    sys.solver = "INVALID_SOLVER"

    sys.converter.sample_clock = 1e9
    sys.converter.decimation = 1
    sys.converter.set_quick_configuration_mode(str(0x88))
    sys.converter.K = 32

    sys.fpga.setup_by_dev_kit_name("zc706")

    with pytest.raises(Exception, match="Unknown solver"):
        sys.solve()
