"""Automatic frequency-planning API and real CP Optimizer regression tests."""

import copy

import pytest

from adijif.freqplan import default_rx_plan, default_tx_plan, plan_to_dict


def _api():
    from adijif.freqplan.solver import (
        RateDomain,
        SignalTarget,
        SolveRequest,
        available_settings,
        solve_plan,
    )

    return (
        RateDomain,
        SignalTarget,
        SolveRequest,
        available_settings,
        solve_plan,
    )


def test_solver_api_exists():
    """The solver has a public API independent of the Streamlit page."""
    import importlib.util

    assert importlib.util.find_spec("adijif.freqplan.solver") is not None


def test_locked_default_rx_is_valid_and_unchanged():
    _, Target, Request, _, solve = _api()
    rx = default_rx_plan()
    before = plan_to_dict(rx, None)
    targets = [
        Target("rx", names[0], path, 0) for path, names in rx.targets.items()
    ]
    result = solve(Request(rx=rx, targets=targets, timeout_s=5, tolerance_hz=5))
    assert result.status == "optimal", result.message
    assert result.rx is not rx
    assert result.objective_bps > 0
    assert all(abs(a["error_hz"]) <= 5 for a in result.achieved)
    assert plan_to_dict(rx, None) == before


def test_solve_nco_moves_rx_to_requested_offset():
    _, Target, Request, _, solve = _api()
    rx = default_rx_plan()
    targets = [
        Target("rx", names[0], path, 10e6) for path, names in rx.targets.items()
    ]
    result = solve(
        Request(
            rx=rx,
            targets=targets,
            automatic={f"rx.fddc.{i}.nco" for i in (0, 2, 4, 6)},
            timeout_s=5,
        )
    )
    assert result.status in ("optimal", "feasible"), result.message
    assert result.rx.datapath.fddc_nco_frequencies[0] == pytest.approx(
        -10e6, abs=3
    )


def test_conflicting_locked_target_is_infeasible():
    _, Target, Request, _, solve = _api()
    rx = default_rx_plan()
    targets = [
        Target("rx", names[0], path, 0) for path, names in rx.targets.items()
    ]
    targets[0] = Target("rx", "S1", "fddc0", 100e6)
    result = solve(Request(rx=rx, targets=targets, timeout_s=5))
    assert result.status == "infeasible", result.message
    assert result.rx is None


def test_unknown_setting_and_missing_target_are_invalid():
    _, _, Request, _, solve = _api()
    result = solve(Request(rx=default_rx_plan(), automatic={"rx.gibberish"}))
    assert result.status == "invalid"
    assert "setting" in result.message.lower()
    result = solve(Request(rx=default_rx_plan()))
    assert result.status == "invalid"
    assert "target" in result.message.lower()


def test_rate_domain_validates_ranges_without_expanding_them():
    Domain, *_ = _api()
    domain = Domain(minimum_hz=8e9, maximum_hz=20e9, step_hz=1)
    assert domain.maximum_hz == 20e9
    with pytest.raises(ValueError):
        Domain(minimum_hz=2, maximum_hz=1)
    with pytest.raises(ValueError):
        Domain(values_hz=(1, float("nan")))


def test_fixed_tx_with_rf_targets():
    _, Target, Request, _, solve = _api()
    tx = default_tx_plan()
    result = solve(
        Request(
            tx=tx,
            targets=[
                Target("tx", "S1", "dac0", 3e9),
                Target("tx", "S2", "dac2", 6e9),
            ],
            timeout_s=5,
            tolerance_hz=5,
        )
    )
    assert result.status == "optimal", result.message
    assert result.tx is not tx


@pytest.mark.parametrize("domain_kind", ["list", "grid"])
def test_rate_optimization_matches_small_exhaustive_domain(domain_kind):
    Domain, Target, Request, _, solve = _api()
    rx = default_rx_plan()
    targets = [
        Target("rx", names[0], path, 0) for path, names in rx.targets.items()
    ]
    domain = (
        Domain(values_hz=(16e9, 18e9, 20e9))
        if domain_kind == "list"
        else Domain(minimum_hz=16e9, maximum_hz=20e9, step_hz=2e9)
    )
    results = []
    for rate in (16e9, 18e9, 20e9):
        fixed = copy.deepcopy(rx)
        fixed.adc_rate_hz = rate
        results.append(
            solve(
                Request(rx=fixed, targets=targets, timeout_s=3, tolerance_hz=5)
            )
        )
    expected = min(r.objective_bps for r in results if r.status == "optimal")
    result = solve(
        Request(
            rx=rx,
            targets=targets,
            automatic={"rx.rate"},
            rate_domains={"rx": domain},
            timeout_s=5,
            tolerance_hz=5,
        )
    )
    assert result.status == "optimal", result.message
    assert result.objective_bps == pytest.approx(expected)
    assert result.rx.adc_rate_hz == 16e9


def test_real_adc_nco_solved_as_tuning_word():
    _, Target, Request, _, solve = _api()
    rx = default_rx_plan("AD9680")
    rx.signals = rx.signals[:1]
    rx.datapath.enabled[1] = False
    rx.datapath.factor = 4
    rx.signals[0].center_hz = rx.adc_rate_hz / 8
    result = solve(
        Request(
            rx=rx,
            targets=[Target("rx", rx.signals[0].name, "ddc0", 0)],
            automatic={"rx.nco.0"},
            timeout_s=5,
        )
    )
    assert result.status == "optimal", result.message
    assert result.rx.datapath.nco_hz[0] == pytest.approx(rx.adc_rate_hz / 8)


def test_transceiver_lo_and_factor_solve():
    _, Target, Request, _, solve = _api()
    rx = default_rx_plan("AD9371")
    rx.signals[0].center_hz = 2.4e9
    rx.signals[1].center_hz = 2.4e9
    result = solve(
        Request(
            rx=rx,
            targets=[
                Target("rx", s.name, f"ddc{s.source}", 0) for s in rx.signals
            ],
            automatic={"rx.lo", "rx.factor"},
            timeout_s=5,
        )
    )
    assert result.status == "optimal", result.message
    assert result.rx.datapath.lo_hz == pytest.approx(2.4e9)
    assert result.rx.datapath.factor == 40


def test_missing_backend_returns_unavailable(monkeypatch):
    _, Target, Request, _, solve = _api()
    from docplex.cp.model import CpoModel

    def missing(*args, **kwargs):
        raise RuntimeError("cpoptimizer executable not found")

    monkeypatch.setattr(CpoModel, "solve", missing)
    rx = default_rx_plan()
    result = solve(
        Request(
            rx=rx,
            targets=[Target("rx", n[0], p) for p, n in rx.targets.items()],
        )
    )
    assert result.status == "unavailable"
    assert result.rx is None


def test_tiny_time_limit_is_not_infeasible():
    _, Target, Request, _, solve = _api()
    rx = default_rx_plan()
    result = solve(
        Request(
            rx=rx,
            targets=[Target("rx", n[0], p) for p, n in rx.targets.items()],
            timeout_s=1e-12,
        )
    )
    assert result.status == "timeout"


@pytest.mark.parametrize(
    "part,direction",
    [
        ("AD9081", "rx"),
        ("AD9081", "tx"),
        ("AD9082", "rx"),
        ("AD9082", "tx"),
        ("AD9088", "rx"),
        ("AD9088", "tx"),
        ("AD9680", "rx"),
        ("AD9144", "tx"),
        ("AD9152", "tx"),
        ("AD9371", "rx"),
        ("AD9371", "tx"),
        ("AD9371_OBS", "rx"),
        ("ADRV9371", "rx"),
        ("ADRV9371", "tx"),
        ("ADRV9009", "rx"),
        ("ADRV9009", "tx"),
    ],
)
def test_all_added_parts_solve_their_fixed_default(part, direction):
    from adijif.freqplan import compute_rx, compute_tx

    _, Target, Request, _, solve = _api()
    plan = default_rx_plan(part) if direction == "rx" else default_tx_plan(part)
    computed = compute_rx(plan) if direction == "rx" else compute_tx(plan)
    targets = []
    for signal in plan.signals:
        for name, stage in computed.stages.items():
            spans = [
                s
                for s in stage.spans
                if s.signal == signal.name and not s.image and not s.attenuated
            ]
            if stage.is_output and spans:
                center = (spans[0].lo + spans[0].hi) / 2
                targets.append(Target(direction, signal.name, name, center))
                break
    result = solve(
        Request(
            **{direction: plan}, targets=targets, timeout_s=3, tolerance_hz=5
        )
    )
    assert result.status == "optimal", result.message


def test_locked_rate_outside_supplied_domain_is_infeasible():
    Domain, Target, Request, _, solve = _api()
    rx = default_rx_plan()
    result = solve(
        Request(
            rx=rx,
            targets=[Target("rx", n[0], p) for p, n in rx.targets.items()],
            rate_domains={"rx": Domain(values_hz=(16e9,))},
        )
    )
    assert result.status == "infeasible"


def test_negative_dac_mixing_can_target_the_real_mirror():
    _, Target, Request, _, solve = _api()
    tx = default_tx_plan()
    tx.cduc_dac_hz[0] = -3e9
    result = solve(
        Request(
            tx=tx,
            targets=[
                Target("tx", "S1", "dac0", 3e9),
                Target("tx", "S2", "dac2", 6e9),
            ],
            tolerance_hz=5,
            timeout_s=3,
        )
    )
    assert result.status == "optimal", result.message


def test_profile_lock_is_not_overridden_by_automatic_factor():
    _, Target, Request, _, solve = _api()
    rx = default_rx_plan("AD9371")
    rx.datapath.profile_constraints = {"factor": 20, "sample_rate_hz": 61.44e6}
    result = solve(
        Request(
            rx=rx,
            targets=[
                Target("rx", s.name, f"ddc{s.source}", 0) for s in rx.signals
            ],
            automatic={"rx.factor"},
            timeout_s=3,
        )
    )
    assert result.status == "optimal", result.message
    assert result.rx.datapath.factor == 20
    assert rx.datapath.factor == 10


def test_combined_transceiver_directions_keep_independent_los():
    _, Target, Request, _, solve = _api()
    rx, tx = default_rx_plan("AD9371"), default_tx_plan("AD9371")
    targets = [Target("rx", s.name, f"ddc{s.source}", 0) for s in rx.signals]
    targets += [
        Target("tx", s.name, f"dac{s.source}", 2.5e9) for s in tx.signals
    ]
    result = solve(
        Request(rx=rx, tx=tx, targets=targets, automatic={"tx.lo"}, timeout_s=3)
    )
    assert result.status == "optimal", result.message
    assert result.rx.datapath.lo_hz == 2.4e9
    assert result.tx.datapath.lo_hz == pytest.approx(2.5e9, abs=1)


def test_overlapping_output_targets_are_proven_infeasible():
    _, Target, Request, _, solve = _api()
    rx = default_rx_plan("AD9371")
    rx.signals[1].source = 0
    result = solve(
        Request(
            rx=rx,
            targets=[Target("rx", s.name, "ddc0", 0) for s in rx.signals],
            automatic={"rx.lo", "rx.factor"},
            timeout_s=3,
        )
    )
    assert result.status == "infeasible", result.message


@pytest.mark.parametrize("direction", ["rx", "tx"])
@pytest.mark.parametrize("bandwidths", [(0, 0), (0, 10e6), (10e6, 0)])
def test_coincident_tones_and_tones_in_bands_are_infeasible(
    direction, bandwidths
):
    from adijif.freqplan import Signal

    _, Target, Request, _, solve = _api()
    plan = (
        default_rx_plan("AD9371")
        if direction == "rx"
        else default_tx_plan("AD9371")
    )
    plan.signals = [
        Signal("a", 2.4e9 if direction == "rx" else 0, bandwidths[0], 0),
        Signal("b", 2.4e9 if direction == "rx" else 0, bandwidths[1], 0),
    ]
    path = "ddc0" if direction == "rx" else "dac0"
    targets = [
        Target(direction, s.name, path, 0 if direction == "rx" else 2.4e9)
        for s in plan.signals
    ]
    result = solve(Request(**{direction: plan}, targets=targets, timeout_s=3))
    assert result.status == "infeasible", result.message


def test_simple_dac_negative_baseband_targets_real_mirror():
    from adijif.freqplan import Signal

    _, Target, Request, _, solve = _api()
    tx = default_tx_plan("AD9152")
    tx.signals = [Signal("tone", -100e6, 10e6, 0)]
    tx.datapath.enabled = [True, False]
    tx.datapath.factor = 1
    tx.dac_rate_hz = 1e9
    result = solve(
        Request(
            tx=tx, targets=[Target("tx", "tone", "dac0", 100e6)], timeout_s=3
        )
    )
    assert result.status == "optimal", result.message


def test_frequency_tolerance_does_not_allow_clipped_bandwidth():
    from adijif.freqplan import Signal

    _, Target, Request, _, solve = _api()
    rx = default_rx_plan("AD9680")
    rx.adc_rate_hz = 1e9
    rx.datapath.factor = 4
    rx.datapath.enabled = [True, False]
    rx.datapath.nco_hz = [125.1e6, 0]
    rx.signals = [Signal("s", 220.1e6, 10e6, 0)]
    result = solve(
        Request(
            rx=rx,
            targets=[Target("rx", "s", "ddc0", 95e6)],
            tolerance_hz=100001,
            timeout_s=3,
        )
    )
    assert result.status == "infeasible", result.message
    assert result.rx is None


@pytest.mark.parametrize(
    "bandwidth,tolerance,target_offset", [(0, 1, 1), (2, 1.1, 1.1)]
)
def test_actual_rx_collision_is_rejected_despite_separate_target_centers(
    bandwidth, tolerance, target_offset
):
    from adijif.freqplan import Signal

    _, Target, Request, _, solve = _api()
    rx = default_rx_plan("AD9371")
    rx.signals = [
        Signal("a", 2.4e9, bandwidth, 0),
        Signal("b", 2.4e9, bandwidth, 0),
    ]
    result = solve(
        Request(
            rx=rx,
            targets=[
                Target("rx", "a", "ddc0", -target_offset),
                Target("rx", "b", "ddc0", target_offset),
            ],
            tolerance_hz=tolerance,
            timeout_s=3,
        )
    )
    assert result.status == "infeasible", result.message


def test_overlapping_target_tolerances_can_cover_separated_actual_rx_bands():
    from adijif.freqplan import Signal

    _, Target, Request, _, solve = _api()
    rx = default_rx_plan("AD9371")
    rx.signals = [Signal("a", 2.38e9, 10e6, 0), Signal("b", 2.42e9, 10e6, 0)]
    result = solve(
        Request(
            rx=rx,
            targets=[
                Target("rx", "a", "ddc0", 0),
                Target("rx", "b", "ddc0", 0),
            ],
            tolerance_hz=25e6,
            timeout_s=3,
        )
    )
    assert result.status == "optimal", result.message
    assert sorted(a["achieved_hz"] for a in result.achieved) == [-20e6, 20e6]


def test_independent_spectrum_validation_rejects_actual_rx_collision():
    from adijif.freqplan import Signal, compute_rx, rx_link, solve_link
    from adijif.freqplan.solver import _validate_candidate

    _, Target, Request, _, _ = _api()
    rx = default_rx_plan("AD9371")
    rx.signals = [Signal("a", 2.4e9, 0, 0), Signal("b", 2.4e9, 0, 0)]
    request = Request(
        rx=rx,
        targets=[Target("rx", "a", "ddc0", -1), Target("rx", "b", "ddc0", 1)],
        tolerance_hz=1,
    )
    computed = compute_rx(rx)
    fit = solve_link(rx, rx_link(rx, computed)).fits[0]
    with pytest.raises(ValueError, match="overlapping"):
        _validate_candidate(
            request, rx, None, {"rx": (fit.jesd_class, fit.mode)}
        )
