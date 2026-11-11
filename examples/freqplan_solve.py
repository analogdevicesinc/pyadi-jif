"""Solve receive frequency placement using IBM CP Optimizer.

Run with ``python examples/freqplan_solve.py``. The ADC inputs, enabled
channels, and routing stay fixed. Fine NCOs compensate for the physical
32-bit coarse NCO's tuning resolution, and the solver selects decimations
that minimize JESD payload throughput. The returned plans are independent
copies, suitable for JSON export or further manual editing.
"""

from adijif.freqplan import (
    Signal,
    SignalTarget,
    SolveRequest,
    default_rx_plan,
    default_tx_plan,
    dumps,
    solve_plan,
)


def main() -> None:
    """Solve the standard AD9084 multiband receive plan."""
    rx = default_rx_plan("AD9084")
    targets = [
        SignalTarget("rx", names[0], path, frequency_hz=0)
        for path, names in rx.targets.items()
    ]
    automatic = {
        f"rx.fddc.{i}.{setting}"
        for i, enabled in enumerate(rx.datapath.fddc_enabled)
        if enabled
        for setting in ("nco", "decimation")
    }
    result = solve_plan(
        SolveRequest(rx=rx, targets=targets, automatic=automatic)
    )
    print(result.status, result.message)
    if result.rx is not None:
        print(f"Payload: {result.objective_bps / 1e9:.3f} Gbit/s")
        print(dumps(result.rx, None))

    # Tx inputs remain baseband signals; targets are desired RF outputs.
    tx = default_tx_plan("AD9081")
    tx.signals = [Signal("A", 0, 20e6, 0), Signal("B", 0, 20e6, 2)]
    result = solve_plan(
        SolveRequest(
            tx=tx,
            targets=[
                SignalTarget("tx", "A", "dac0", 1.6e9),
                SignalTarget("tx", "B", "dac1", 2.3e9),
            ],
            automatic={"tx.cduc.0.nco", "tx.cduc.1.nco"},
        )
    )
    print("Tx RF placement:", result.status, result.achieved)

    # One LO is shared by both receive channels. The filters and sample
    # rate stay fixed here; both signals need the same translation.
    rx = default_rx_plan("ADRV9009")
    for signal in rx.signals:
        signal.center_hz = 2.45e9
    result = solve_plan(
        SolveRequest(
            rx=rx,
            targets=[
                SignalTarget("rx", signal.name, f"ddc{signal.source}")
                for signal in rx.signals
            ],
            automatic={"rx.lo"},
        )
    )
    print("Transceiver LO:", result.status, result.settings.get("rx.lo"))


if __name__ == "__main__":
    main()
