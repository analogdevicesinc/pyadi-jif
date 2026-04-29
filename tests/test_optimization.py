"""Tests for the cohesive lexicographic optimization framework."""

import pytest

import adijif
from adijif.optimization import Objective, apply_objectives, collect_objectives


@pytest.fixture
def basic_system():
    """A solvable AD9680 system used as a host for objective tests."""
    sys = adijif.system("ad9680", "hmc7044", "xilinx", 125e6, solver="CPLEX")
    sys.fpga.setup_by_dev_kit_name("zc706")
    sys.converter.sample_clock = 1e9 / 2
    sys.converter.datapath_decimation = 1
    sys.converter.L = 4
    sys.converter.M = 2
    sys.converter.N = 14
    sys.converter.Np = 16
    sys.converter.K = 32
    sys.converter.F = 1
    sys.converter.HD = 1
    return sys


def test_objective_default_metadata():
    obj = Objective(expr=42)
    assert obj.sense == "min"
    assert obj.tier == 0
    assert obj.weight == 1.0
    assert obj.name is None
    assert obj.component is None


def test_objective_rejects_invalid_sense():
    with pytest.raises(ValueError, match="sense must be 'min' or 'max'"):
        Objective(expr=1, sense="lower")


def test_apply_objectives_noop_when_empty():
    # Should not raise even with a None model when there's nothing to apply.
    apply_objectives(model=None, solver="CPLEX", objectives=[])


def test_apply_objectives_gekko_multi_tier_raises():
    objs = [
        Objective(expr=1, tier=0),
        Objective(expr=2, tier=1),
    ]
    with pytest.raises(NotImplementedError, match="solver='CPLEX'"):
        apply_objectives(model=None, solver="gekko", objectives=objs)


def test_collect_and_apply_default_objectives(basic_system):
    """Default built-in objectives are collected from clock and FPGA."""
    sys = basic_system
    sys.initialize()
    objs = collect_objectives(sys)
    names = {o.name for o in objs}
    # HMC7044 registers r2_min by default; FPGA may register additional
    # objectives depending on configuration.
    assert "hmc7044.r2_min" in names
    components = {o.component for o in objs}
    assert "hmc7044" in components


def test_disable_objective_suppresses_default(basic_system):
    sys = basic_system
    sys.clock.disable_objective("hmc7044.r2_min")
    sys.initialize()
    objs = collect_objectives(sys)
    names = {o.name for o in objs}
    assert "hmc7044.r2_min" not in names


def test_user_add_objective_appears_with_user_component(basic_system):
    sys = basic_system
    sys.add_objective(0, sense="min", tier=5, name="user.dummy")
    sys.initialize()
    objs = sys.list_objectives()
    user_objs = [o for o in objs if o.name == "user.dummy"]
    assert len(user_objs) == 1
    assert user_objs[0].component == "user"
    assert user_objs[0].tier == 5


def test_user_objective_survives_initialize_reset(basic_system):
    """initialize() resets per-component _objectives; user list must not be."""
    sys = basic_system
    sys.add_objective(0, name="user.persistent")
    assert any(o.name == "user.persistent" for o in sys._user_objectives)
    sys.initialize()
    # The component _objectives lists were reset and repopulated, but
    # _user_objectives is preserved.
    assert any(o.name == "user.persistent" for o in sys._user_objectives)
    assert any(o.name == "user.persistent" for o in collect_objectives(sys))


def test_full_solve_with_default_objectives(basic_system):
    """The system solves end-to-end through the new framework."""
    cfg = basic_system.solve()
    assert "clock" in cfg
    assert "fpga_AD9680" in cfg


def test_list_expr_creates_one_objective_per_item():
    class FakeComponent:
        _disabled_objectives: set = set()
        _objectives: list = []

    comp = FakeComponent()
    comp._objectives = []
    adijif.common.core._add_objective(
        comp, [10, 20, 30], sense="min", tier=2, name="fake.batch"
    )
    assert len(comp._objectives) == 3
    assert [o.expr for o in comp._objectives] == [10, 20, 30]
    assert all(o.tier == 2 for o in comp._objectives)
    assert [o.name for o in comp._objectives] == [
        "fake.batch[0]",
        "fake.batch[1]",
        "fake.batch[2]",
    ]
