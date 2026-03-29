# flake8: noqa
import pytest

import adijif as jif


@pytest.mark.parametrize(
    "conv",
    [
        "ad9680",
        "adrv9009_rx",
        "adrv9009_tx",
        "ad9081_rx",
        "ad9081_tx",
        "ad9144",
        "ad9152",
        "ad9084_rx",
        "ad9088_rx",
        "ad9082_rx",
        "ad9082_tx",
    ],
)
def test_converters(conv):
    c = eval(f"jif.{conv}()")
    # Check static
    c.validate_config()

    required_clocks = c.get_required_clocks()
    required_clock_names = c.get_required_clock_names()

    # Add generic clock sources for solver
    clks = []
    for clock, name in zip(required_clocks, required_clock_names):
        clk = jif.types.arb_source(name)
        c._add_equation(clk(c.model) == clock)
        clks.append(clk)

    # Solve
    solution = c.model.solve(LogVerbosity="Quiet")
    settings = c.get_config(solution)

    # Get clock values
    clock_values = {}
    for clk in clks:
        clock_values.update(clk.get_config(solution))
    settings["clocks"] = clock_values

    print(settings)

    image_data = c.draw(settings["clocks"])
    assert image_data is not None


@pytest.mark.drawing
@pytest.mark.parametrize("clock", ["hmc7044", "ltc6952", "ad9528", "ad9523_1"])
def test_clock_chip_draw(clock):

    import pprint

    vcxo = 125000000

    clk = eval(f"jif.{clock}()")
    # clk = jif.hmc7044()

    output_clocks = [1e9, 500e6, 7.8125e6]
    output_clocks = list(map(int, output_clocks))  # force to be ints
    clock_names = ["ADC", "FPGA", "SYSREF"]

    clk.set_requested_clocks(vcxo, output_clocks, clock_names)

    clk.solve()

    o = clk.get_config()

    pprint.pprint(o)

    clk.draw()


@pytest.mark.drawing
def test_ad9680_draw():
    adc = jif.ad9680()

    # Check static
    adc.validate_config()

    required_clocks = adc.get_required_clocks()
    required_clock_names = adc.get_required_clock_names()

    # Add generic clock sources for solver
    clks = []
    for clock, name in zip(required_clocks, required_clock_names):
        clk = jif.types.arb_source(name)
        adc._add_equation(clk(adc.model) == clock)
        clks.append(clk)

    # Solve
    solution = adc.model.solve(LogVerbosity="Quiet")
    settings = adc.get_config(solution)

    # Get clock values
    clock_values = {}
    for clk in clks:
        clock_values.update(clk.get_config(solution))
    settings["clocks"] = clock_values

    print(settings)

    image_data = adc.draw(settings["clocks"])
    assert image_data is not None

    # with open("ad9680_example.svg", "w") as f:
    #     f.write(image_data)


@pytest.mark.drawing
def test_generic_converter_draw():
    adc = jif.adrv9009_rx()
    adc.sample_clock = 122.88e6
    adc.decimation = 4
    adc.set_quick_configuration_mode("17", "jesd204b")

    # Check static
    adc.validate_config()

    required_clocks = adc.get_required_clocks()
    required_clock_names = adc.get_required_clock_names()

    # Add generic clock sources for solver
    clks = []
    for clock, name in zip(required_clocks, required_clock_names):
        clk = jif.types.arb_source(name)
        adc._add_equation(clk(adc.model) == clock)
        clks.append(clk)

    # Solve
    solution = adc.model.solve(LogVerbosity="Quiet")
    settings = adc.get_config(solution)

    # Get clock values
    clock_values = {}
    for clk in clks:
        clock_values.update(clk.get_config(solution))
    settings["clocks"] = clock_values

    print(settings)

    image_data = adc.draw(settings["clocks"])
    assert image_data is not None


@pytest.mark.drawing
@pytest.mark.parametrize(
    "device_clock_source", ["external", "link_clock", "ref_clock"]
)
def test_xilinx_draw(device_clock_source):
    import adijif as jif
    from adijif.converters.converter import converter

    fpga = jif.xilinx()
    fpga.setup_by_dev_kit_name("vcu118")
    fpga.device_clock_source = device_clock_source

    # class dummy_converter(converter):
    #     name = "dummy"

    # dc = dummy_converter()
    dc = jif.ad9680()

    fpga_ref = jif.types.arb_source("FPGA_REF")
    link_out_ref = jif.types.arb_source("LINK_OUT_REF")

    clocks = fpga.get_required_clocks(
        dc, fpga_ref(fpga.model), link_out_ref(fpga.model)
    )
    # print(clocks)

    solution = fpga.model.solve(LogVerbosity="Quiet")
    # solution.write()

    settings = {}
    # Get clock values
    clock_values = {}
    for clk in [fpga_ref, link_out_ref]:
        clock_values.update(clk.get_config(solution))
    settings["clocks"] = clock_values

    settings["fpga"] = fpga.get_config(
        dc, settings["clocks"]["FPGA_REF"], solution
    )
    print(settings)

    image_data = fpga.draw(settings)

    del fpga

    assert image_data


@pytest.mark.drawing
def test_system_draw():
    import pprint

    import adijif

    vcxo = 125000000

    sys = adijif.system("ad9680", "hmc7044", "xilinx", vcxo)

    # Get Converter clocking requirements
    sys.converter.sample_clock = 1e9
    sys.converter.decimation = 1
    sys.converter.set_quick_configuration_mode(str(0x88))
    sys.converter.K = 32
    sys.Debug_Solver = False

    # Get FPGA clocking requirements
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.fpga.force_qpll = 1

    cfg = sys.solve()

    pprint.pprint(cfg)

    # print("Clock config:")
    # pprint.pprint(cfg["clock"])

    # print("Converter config:")
    # pprint.pprint(cfg["converter"])

    print("FPGA config:")
    pprint.pprint(cfg["fpga_AD9680"])

    # print("JESD config:")
    # pprint.pprint(cfg["jesd_AD9680"])

    data = sys.draw(cfg)

    # with open("daq2_example.svg", "w") as f:
    #     f.write(data)


@pytest.mark.drawing
def test_ad9084_draw():
    """Test AD9084 drawing."""
    conv = jif.ad9084_rx()

    # Check static
    conv.validate_config()

    required_clocks = conv.get_required_clocks()
    required_clock_names = conv.get_required_clock_names()

    # Add generic clock sources for solver
    clks = []
    for clock, name in zip(required_clocks, required_clock_names):
        clk = jif.types.arb_source(name)
        conv._add_equation(clk(conv.model) == clock)
        clks.append(clk)

    # Solve
    solution = conv.model.solve(LogVerbosity="Quiet")
    settings = conv.get_config(solution)

    # Get clock values
    clock_values = {}
    for clk in clks:
        clock_values.update(clk.get_config(solution))
    settings["clocks"] = clock_values

    image_data = conv.draw(settings["clocks"])
    assert image_data is not None


@pytest.mark.drawing
def test_ad9081_rx_draw():
    """Test AD9081 RX drawing with CDDC/FDDC datapath detail."""
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
    assert image_data is not None
    # Verify datapath nodes are present in the D2 output
    assert "CDDC0" in image_data
    assert "FDDC0" in image_data
    assert "JESD204 Framer" in image_data
    assert "ADC0" in image_data


@pytest.mark.drawing
def test_ad9081_tx_draw():
    """Test AD9081 TX drawing with CDUC/FDUC datapath detail."""
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
    assert image_data is not None
    # Verify TX datapath nodes are present
    assert "CDUC0" in image_data
    assert "FDUC0" in image_data
    assert "JESD204 Deframer" in image_data
    assert "DAC0" in image_data


@pytest.mark.drawing
def test_adrv9009_rx_draw():
    """Test ADRV9009 RX drawing with decimation filter detail."""
    conv = jif.adrv9009_rx()

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
    assert image_data is not None
    assert "ADC" in image_data
    assert "Decimation Filter" in image_data
    assert "JESD204 Framer" in image_data


@pytest.mark.drawing
def test_adrv9009_tx_draw():
    """Test ADRV9009 TX drawing with interpolation filter detail."""
    conv = jif.adrv9009_tx()

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
    assert image_data is not None
    assert "DAC" in image_data
    assert "Interpolation Filter" in image_data
    assert "JESD204 Deframer" in image_data


@pytest.mark.drawing
def test_ad9144_draw():
    """Test AD9144 drawing with interpolation and multi-DAC detail."""
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
    assert image_data is not None
    assert "Interpolation" in image_data
    assert "DAC0" in image_data
    assert "JESD204 Deframer" in image_data


@pytest.mark.drawing
def test_ad9082_rx_inherits_draw():
    """Verify AD9082 RX produces detailed diagram via AD9081 RX draw mixin."""
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
    assert image_data is not None
    assert "CDDC0" in image_data
    assert "FDDC0" in image_data


@pytest.mark.drawing
def test_ltc6953_draw():
    """Test LTC6953 drawing with divider detail."""
    clk = jif.ltc6953()
    ref_in = jif.types.range(1000000000, 4500000000, 1000000, "ref_in")
    output_clocks = [1000000000, 500000000, 7812500]
    clock_names = ["ADC", "FPGA", "SYSREF"]
    clk.set_requested_clocks(ref_in, output_clocks, clock_names)
    clk.solve()
    clk.get_config()
    image_data = clk.draw()
    assert image_data is not None
    assert "LTC6953" in image_data
    assert "ADC" in image_data
    assert "FPGA" in image_data
    assert "SYSREF" in image_data


@pytest.mark.drawing
def test_ad9545_draw():
    """Test AD9545 drawing with multi-PLL detail."""
    clk = jif.ad9545()
    input_refs = [(0, 1), (1, 10e6)]
    output_clocks = [(0, 30720000)]
    clk.set_requested_clocks(input_refs, output_clocks)
    clk.solve()
    clk.get_config()
    image_data = clk.draw()
    assert image_data is not None
    assert "AD9545" in image_data
    assert "PLL0" in image_data
    assert "Q0" in image_data
