import pytest

import adijif as jif


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
def test_xilinx_draw():
    import adijif as jif
    from adijif.converters.converter import converter

    fpga = jif.xilinx()
    fpga.setup_by_dev_kit_name("vcu118")

    # class dummy_converter(converter):
    #     name = "dummy"

    # dc = dummy_converter()
    dc = jif.ad9680()

    fpga_ref = jif.types.arb_source("FPGA_REF")
    link_out_ref = jif.types.arb_source("LINK_OUT_REF")

    clocks = fpga.get_required_clocks(
        dc, fpga_ref(fpga.model), link_out_ref(fpga.model)
    )
    print(clocks)

    solution = fpga.model.solve(LogVerbosity="Quiet")
    solution.write()

    settings = {}
    # Get clock values
    clock_values = {}
    for clk in [fpga_ref, link_out_ref]:
        clock_values.update(clk.get_config(solution))
    settings["clocks"] = clock_values

    settings["fpga"] = fpga.get_config(dc, settings["clocks"]["FPGA_REF"], solution)
    print(settings)


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
