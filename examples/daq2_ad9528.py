# Determine clocking for DAQ2

import adijif

vcxo = 125000000

sys = adijif.system("ad9680", "ad9528", "xilinx", vcxo)

# Get Converter clocking requirements
sys.converter.sample_clock = 1e9
sys.converter.datapath_decimation = 1
sys.converter.L = 4
sys.converter.M = 2
sys.converter.N = 14
sys.converter.Np = 16
sys.converter.K = 32
sys.converter.F = 1

cnv_clocks = sys.converter.get_required_clocks()

# Get FPGA clocking requirements
sys.fpga.setup_by_dev_kit_name("zc706")
fpga_dev_clock = sys.fpga.get_required_clocks(sys.converter)

# Collect all requirements
sys.clock.set_requested_clocks(vcxo, [fpga_dev_clock] + cnv_clocks)

print("Starting Solver")
sys.model.options.SOLVER = 1  # APOPT solver
sys.model.solve(disp=False)
sys.model.solver_options = [
    "minlp_maximum_iterations 1000",  # minlp iterations with integer solution
    "minlp_max_iter_with_int_sol 100",  # treat minlp as nlp
    "minlp_as_nlp 0",  # nlp sub-problem max iterations
    "nlp_maximum_iterations 5000",  # 1 = depth first, 2 = breadth first
    "minlp_branch_method 1",  # maximum deviation from whole number
    "minlp_integer_tol 0.05",  # covergence tolerance
    "minlp_gap_tol 0.01",
]

for c in sys.clock.config:
    vs = sys.clock.config[c]
    for v in vs:
        if len(vs) > 1:
            print(c, v[0])
        else:
            print(c, v)

print("sysref: " + str(sys.converter.config["sysref"].value[0]))
print("fpga_ref: ", sys.fpga.config["fpga_ref"].value[0])
