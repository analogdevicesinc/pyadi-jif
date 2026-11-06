"""AD9084 frequency plan, scripted with adijif.freqplan.

Starts from the planner's default four-signal Rx plan, then:

* moves S4 into the second Nyquist zone (12.2 GHz at 20 GSPS) and points
  CDDC3 at it, and
* raises FDDC0's decimation so only part of S1 fits its passband.

It prints the verdict for every output, sizes each JESD204 link (M and the
link sample rate) and picks the first mode that fits a VCU118, and writes
the plan and those modes to ``freqplan_ad9084.json`` next to this script; load that file in the
Frequency Planner page (``jiftools``) to see the same plan.
"""

import os

from adijif.freqplan import (
    Signal,
    compute_rx,
    compute_tx,
    default_rx_plan,
    default_tx_plan,
    dumps,
    evaluate_dac,
    evaluate_output,
    fpga_from_devkit,
    jesd_to_dict,
    link_summary,
    rx_link,
    solve_link,
    tx_link,
)

rx = default_rx_plan()

# S4 moves to 12.2 GHz: the second Nyquist zone of a 20 GSPS ADC.
rx.signals[3] = Signal("S4", 12.2e9, 200e6, 3)
rx.cddc_rf_hz[3] = 12.2e9  # CDDC NCOs are entered as the RF frequency

# FDDC0 (fed by CDDC0, ÷4) now decimates by 16: 20 GSPS / 64 = 312.5 MSPS,
# so with alpha = 0.8 only ±125 MHz of the 400 MHz S1 is usable.
rx.datapath.fddc_decimations[0] = 16

rx_result = compute_rx(rx)
rx_signals = {s.name: s for s in rx.signals}
print("Rx outputs")
for name, stage in rx_result.stages.items():
    if not stage.is_output:
        continue
    verdict = evaluate_output(stage, rx_signals, rx.targets.get(name, []))
    rate = f"{stage.rate_hz / 1e6:g} MSPS" if not stage.error else "-"
    print(f"  {name:6s} {rate:>12s}  {verdict.status:5s}  "
          + " | ".join(verdict.messages))
for warning in rx_result.warnings:
    print(f"  warning: {warning}")

tx = default_tx_plan()
tx_result = compute_tx(tx)
tx_signals = {s.name: s for s in tx.signals}
print("Tx outputs")
for name, stage in tx_result.stages.items():
    if stage.is_output:
        verdict = evaluate_dac(stage, tx_signals)
        print(f"  {name:6s} {verdict.status:5s}  "
              + " | ".join(verdict.messages))

# JESD204: M is two per complex output; the link runs at the fastest output.
fpga = fpga_from_devkit("vcu118")
chosen = {}
for tab, plan, req in (
    ("rx", rx, rx_link(rx, rx_result)),
    ("tx", tx, tx_link(tx, tx_result)),
):
    sol = solve_link(plan, req, fpga)
    print(f"{tab.upper()} JESD204: {link_summary(sol)}")
    chosen[tab] = sol.fits[0] if sol.fits else None
    if chosen[tab]:
        print(f"  chosen: {chosen[tab].label()}")

out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "freqplan_ad9084.json")
with open(out, "w") as f:
    f.write(dumps(rx, tx, None, jesd_to_dict({"devkit": "vcu118"}, chosen)))
print(f"Wrote {out}")
