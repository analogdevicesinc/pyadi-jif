"""Regression tests for AD9545 request ownership."""

import adijif


def test_ad9545_setup_copies_reference_and_output_lists():
    """Low-level setup must not retain caller-owned topology lists."""
    clock = adijif.ad9545(solver="CPLEX")
    input_refs = [125_000_000, 0, 0, 0]
    out_freqs = [156_250_000] + [0] * 9

    clock.setup_constraints(input_refs, out_freqs)
    input_refs[0] = 1
    out_freqs[0] = 2

    assert clock.input_refs == [125_000_000, 0, 0, 0]
    assert clock.out_freqs == [156_250_000] + [0] * 9


def test_ad9545_requested_clock_pairs_are_caller_independent():
    """The convenience API must derive independent fixed-width topology lists."""
    clock = adijif.ad9545(solver="CPLEX")
    inputs = [[0, 125_000_000]]
    outputs = [[0, 156_250_000]]

    clock.set_requested_clocks(inputs, outputs)
    inputs[0][1] = 1
    outputs[0][1] = 2

    assert clock.input_refs == [125_000_000, 0, 0, 0]
    assert clock.out_freqs == [156_250_000] + [0] * 9
