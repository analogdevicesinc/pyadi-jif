"""Automatic-planning controls and per-session background job management."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable

import pandas as pd
import streamlit as st

from adijif.freqplan import compute_rx, get_adapter, plan_to_dict


@dataclass
class SolveJob:
    """A job belongs to one session and one immutable request fingerprint."""

    fingerprint: str
    future: Future

    def applicable(self, current: str) -> bool:
        """Only a finished, successful, current result may be applied."""
        if current != self.fingerprint or not self.future.done():
            return False
        if self.future.cancelled() or self.future.exception() is not None:
            return False
        result = self.future.result()
        return result.status in ("optimal", "feasible", "timeout") and (
            result.rx is not None or result.tx is not None
        )


def fingerprint(rx: Any, tx: Any, options: dict) -> str:
    """Hash plans and every input that could change the solve result."""
    config = plan_to_dict(rx, tx) if rx is not None or tx is not None else {}
    encoded = json.dumps([config, options], sort_keys=True, allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def target_rows(rx: Any, tx: Any) -> pd.DataFrame:
    """Default targets on the selected physical routes, independent of capture."""
    rows = []
    if rx is not None:
        adapter = get_adapter(rx.part)
        dp = rx.datapath
        result = compute_rx(rx)
        for sig in rx.signals:
            if getattr(adapter, "topology", "mxfe") == "mxfe":
                explicit = [
                    p for p, names in rx.targets.items() if sig.name in names
                ]
                paths = explicit or [
                    name
                    for name, stage in result.stages.items()
                    if stage.is_output
                    and (
                        rx.adc_to_cddc[dp.fddc_source[int(name[4:])] - 1]
                        if name.startswith("fddc")
                        else rx.adc_to_cddc[int(name[4:])]
                    )
                    == sig.source
                ]
            else:
                paths = [f"ddc{sig.source}"]
            for path in paths:
                rows.append(
                    {
                        "direction": "rx",
                        "signal": sig.name,
                        "path": path,
                        "target_mhz": 0.0,
                    }
                )
    if tx is not None:
        adapter = get_adapter(tx.part)
        dp = tx.datapath
        for sig in tx.signals:
            if getattr(adapter, "topology", "mxfe") == "mxfe":
                i = sig.source
                if not 0 <= i < len(dp.fduc_source):
                    continue
                c = dp.fduc_source[i] - 1
                center = (
                    sig.center_hz
                    + dp.fduc_nco_frequencies[i]
                    + tx.cduc_dac_hz[c]
                )
                paths = [
                    f"dac{j}"
                    for j, srcs in enumerate(dp.cduc_sources)
                    if c + 1 in srcs
                ]
            else:
                center = sig.center_hz + dp.lo_hz
                if dp.nco_hz:
                    center += dp.nco_hz[sig.source]
                paths = [f"dac{sig.source}"]
            for path in paths:
                rows.append(
                    {
                        "direction": "tx",
                        "signal": sig.name,
                        "path": path,
                        "target_mhz": float(center / 1e6),
                    }
                )
    return pd.DataFrame(
        rows, columns=["direction", "signal", "path", "target_mhz"]
    )


def _label(key: str) -> str:
    return " · ".join(
        {"nco": "NCO", "lo": "LO"}.get(word, word) for word in key.split(".")
    )


def validated_options(raw: Any, part: str | None = None) -> dict:
    """Validate persisted widget inputs before a transactional config import."""
    if not isinstance(raw, dict):
        raise ValueError("view.solver.options must be an object")
    if raw.get("scope", "Rx") not in ("Rx", "Tx", "Rx and Tx"):
        raise ValueError("Invalid solve direction")
    for field in ("pinned_modes", "jesd_modes"):
        pinned = raw.get(field, {})
        if not isinstance(pinned, dict):
            raise ValueError(f"{field} must be an object")
        for direction, mode in pinned.items():
            if (
                direction not in ("rx", "tx")
                or not isinstance(mode, (list, tuple))
                or len(mode) != 2
                or any(not isinstance(value, str) for value in mode)
            ):
                raise ValueError(
                    "Pinned JESD modes need a direction and [class, mode] pair"
                )
            if part is not None:
                converter = getattr(get_adapter(part), f"{direction}_converter")
                if converter is None or mode[
                    1
                ] not in converter.quick_configuration_modes.get(mode[0], {}):
                    raise ValueError(
                        f"Unknown pinned JESD mode for {part} {direction.upper()}: {mode}"
                    )
    automatic = raw.get("automatic", [])
    if not isinstance(automatic, list) or any(
        not isinstance(k, str) for k in automatic
    ):
        raise ValueError("Automatic settings must be a list of setting names")
    targets = raw.get("targets", [])
    if not isinstance(targets, list):
        raise ValueError("Solve targets must be a list")
    for target in targets:
        if not isinstance(target, dict) or target.get("direction") not in (
            "rx",
            "tx",
        ):
            raise ValueError("Invalid solve target direction")
        if any(not isinstance(target.get(k), str) for k in ("signal", "path")):
            raise ValueError("Solve targets need a signal and path")
        if not math.isfinite(float(target.get("target_mhz", float("nan")))):
            raise ValueError("Solve target frequency must be finite")
    for name, minimum, maximum in (
        ("timeout_s", 1, 600),
        ("tolerance_hz", 0, float("inf")),
    ):
        value = float(raw.get(name, 30 if name == "timeout_s" else 1))
        if not math.isfinite(value) or not minimum <= value <= maximum:
            raise ValueError(f"Invalid {name}")
    domains = raw.get("rate_domains", {})
    if not isinstance(domains, dict):
        raise ValueError("Rate domains must be an object")
    for direction, domain in domains.items():
        if direction not in ("rx", "tx") or not isinstance(domain, dict):
            raise ValueError("Invalid rate domain")
        if domain.get("mode") == "Allowed list":
            if not isinstance(domain.get("values"), str):
                raise ValueError(
                    "Allowed rates must be comma-separated MHz values"
                )
            values = [float(v.strip()) for v in domain["values"].split(",")]
        elif domain.get("mode") == "Range":
            values = [
                float(domain[name]) for name in ("minimum", "maximum", "step")
            ]
            if values[0] > values[1]:
                raise ValueError("Rate minimum exceeds maximum")
        else:
            raise ValueError("Invalid rate domain mode")
        if any(not math.isfinite(v) or v < 0.000001 for v in values):
            raise ValueError(
                "Rate domain values must be finite, positive MHz values"
            )
    return copy.deepcopy(raw)


def _start(request: Any, signature: str) -> SolveJob:
    from adijif.freqplan.solver import solve_plan

    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="freqplan")
    future = executor.submit(solve_plan, copy.deepcopy(request))
    executor.shutdown(wait=False)
    return SolveJob(signature, future)


@st.fragment(run_every=1)
def _running_status() -> None:
    """Refresh only job status while the backend works off the UI thread."""
    job = st.session_state.get("fp_solve_job")
    if job is not None and job.future.done():
        st.rerun()
    st.info(
        "Solving in the background. You can keep editing; changed inputs "
        "invalidate this result."
    )
    st.button("Refresh solve status", key="fp_solve_refresh")


def solver_panel(
    rx: Any,
    tx: Any,
    fpga: Any,
    fpga_choice: dict | None,
    apply_solution: Callable[[Any, Any], None],
    selected_modes: dict | None = None,
) -> None:
    """Render request controls, a nonblocking worker, and a reviewed apply step."""
    from adijif.freqplan.solver import (
        RateDomain,
        SignalTarget,
        SolveRequest,
        available_settings,
    )

    ss = st.session_state
    gen = ss.get("fp_editor_gen", 0)
    saved = ss.get("fp_solver_options", {})
    with st.expander("Automatic planning", expanded=False):
        st.caption(
            "Keep the selected paths. Unlock the settings to choose automatically; all other settings stay fixed."
        )
        scopes = (["Rx"] if rx is not None else []) + (
            ["Tx"] if tx is not None else []
        )
        if len(scopes) == 2:
            scopes.append("Rx and Tx")
        if not scopes:
            st.info("Correct the plan inputs to enable automatic planning.")
            return
        chosen = saved.get("scope", scopes[0])
        scope = st.radio(
            "Solve directions",
            scopes,
            index=scopes.index(chosen) if chosen in scopes else 0,
            horizontal=True,
            key=f"fp_solve_scope_{gen}",
        )
        st.caption(
            "Choose Rx and Tx to validate shared converter clock relationships. A single-direction solve does not validate the other direction."
        )
        sr = rx if scope != "Tx" else None
        stx = tx if scope != "Rx" else None
        settings = {}
        for direction, plan in (("rx", sr), ("tx", stx)):
            if plan is not None:
                settings.update(available_settings(plan, direction))
        automatic = st.multiselect(
            "Automatically choose",
            list(settings),
            default=[k for k in saved.get("automatic", []) if k in settings],
            format_func=_label,
            key=f"fp_solve_auto_{gen}",
        )
        pin_modes = st.checkbox(
            "Constrain to selected JESD modes",
            value=bool(saved.get("pin_modes", False)),
            key=f"fp_solve_pin_modes_{gen}",
            help="Pin the current Mode for export selections. Pins stay fixed when the plan changes; use Update pinned JESD modes to replace them.",
        )
        pinned_modes = {
            direction: tuple(mode)
            for direction, mode in saved.get(
                "pinned_modes", saved.get("jesd_modes", {})
            ).items()
        }
        update_pins = False
        if pin_modes:
            update_pins = st.button(
                "Update pinned JESD modes",
                key="fp_solve_update_pins",
                help="Replace the pins with the current Mode for export selections. Directions with no selected mode are cleared.",
            )
            if not saved.get("pin_modes", False) or update_pins:
                pinned_modes = {
                    direction: tuple(mode)
                    for direction, mode in (selected_modes or {}).items()
                    if mode is not None
                }
            if pinned_modes:
                st.caption(
                    "Pinned JESD modes: "
                    + "; ".join(
                        f"{direction.upper()} {mode[0]} mode {mode[1]}"
                        for direction, mode in pinned_modes.items()
                    )
                )
        jesd_constraints = {
            direction: mode
            for direction, mode in pinned_modes.items()
            if pin_modes
            and (
                (direction == "rx" and sr is not None)
                or (direction == "tx" and stx is not None)
            )
        }
        if pin_modes and not jesd_constraints:
            st.caption(
                "Select a JESD mode in a direction's JESD204 modes panel, then choose Update pinned JESD modes."
            )
        defaults = target_rows(sr, stx)
        routes = defaults[["direction", "signal", "path"]].to_json()
        target_key = f"fp_solve_targets_{gen}_{hashlib.sha256(routes.encode()).hexdigest()[:8]}"
        seed_key = target_key + "_seed"
        if seed_key not in ss:
            previous = {
                (r["direction"], r["signal"], r["path"]): r["target_mhz"]
                for r in saved.get("targets", [])
            }
            defaults["target_mhz"] = [
                previous.get((r.direction, r.signal, r.path), r.target_mhz)
                for r in defaults.itertuples()
            ]
            ss[seed_key] = defaults
        targets_frame = st.data_editor(
            ss[seed_key],
            key=target_key,
            hide_index=True,
            disabled=["direction", "signal", "path"],
            column_config={
                "target_mhz": st.column_config.NumberColumn(
                    "Desired center (MHz)",
                    required=True,
                    help="Rx: desired output offset. Tx: desired RF output center; baseband signal offsets are retained.",
                )
            },
        )
        domains = {}
        domain_options = {}
        error = None
        for direction, plan in (("rx", sr), ("tx", stx)):
            if plan is None or f"{direction}.rate" not in automatic:
                continue
            adapter = get_adapter(plan.part)
            rate = plan.adc_rate_hz if direction == "rx" else plan.dac_rate_hz
            bounds = getattr(
                adapter, f"{direction}_rate_bounds_hz", (rate, rate)
            )
            old = saved.get("rate_domains", {}).get(direction, {})
            with st.container(border=True):
                st.markdown(
                    f"**{direction.upper()} converter sample-rate choices**"
                )
                rate_domain_modes = ["Range", "Allowed list"]
                mode = st.radio(
                    "Rate domain",
                    rate_domain_modes,
                    index=rate_domain_modes.index(old.get("mode", "Range")),
                    horizontal=True,
                    key=f"fp_solve_{direction}_domain_{gen}",
                )
                if mode == "Allowed list":
                    values = st.text_input(
                        "Allowed rates (MHz, comma-separated)",
                        value=old.get("values", f"{rate / 1e6:g}"),
                        key=f"fp_solve_{direction}_values_{gen}",
                    )
                    domain_options[direction] = {"mode": mode, "values": values}
                    try:
                        parsed = tuple(
                            float(v.strip()) * 1e6 for v in values.split(",")
                        )
                        if not parsed or any(v <= 0 for v in parsed):
                            raise ValueError
                        domains[direction] = RateDomain(values_hz=parsed)
                    except ValueError:
                        error = "Allowed rates must be a comma-separated list of positive MHz values."
                else:
                    cols = st.columns(3)
                    vals = []
                    for col, label, name, default in zip(
                        cols,
                        ("Minimum (MHz)", "Maximum (MHz)", "Step (MHz)"),
                        ("minimum", "maximum", "step"),
                        (bounds[0] / 1e6, bounds[1] / 1e6, 1.0),
                        strict=False,
                    ):
                        with col:
                            vals.append(
                                st.number_input(
                                    label,
                                    min_value=0.000001,
                                    value=float(old.get(name, default)),
                                    format="%.6f",
                                    key=f"fp_solve_{direction}_{name}_{gen}",
                                )
                            )
                    domain_options[direction] = {
                        "mode": mode,
                        "minimum": vals[0],
                        "maximum": vals[1],
                        "step": vals[2],
                    }
                    if vals[0] > vals[1]:
                        error = (
                            "The minimum rate must not exceed the maximum rate."
                        )
                    else:
                        domains[direction] = RateDomain(
                            minimum_hz=vals[0] * 1e6,
                            maximum_hz=vals[1] * 1e6,
                            step_hz=vals[2] * 1e6,
                        )
        c1, c2 = st.columns(2)
        with c1:
            timeout = st.number_input(
                "Solve time limit (seconds)",
                min_value=1.0,
                max_value=600.0,
                value=float(saved.get("timeout_s", 30)),
                key=f"fp_solve_timeout_{gen}",
            )
        with c2:
            tolerance = st.number_input(
                "Frequency tolerance (Hz)",
                min_value=0.0,
                value=float(saved.get("tolerance_hz", 1)),
                key=f"fp_solve_tolerance_{gen}",
                help="Hardware NCO tuning words have finite resolution. For example, a 32-bit coarse NCO at 20 GSPS has about 4.66 Hz steps. Unlock fine NCOs or choose a wider tolerance (such as 5 Hz) if an otherwise valid plan cannot meet 1 Hz.",
            )
        options = {
            "scope": scope,
            "automatic": automatic,
            "targets": targets_frame.to_dict("records"),
            "rate_domains": domain_options,
            "timeout_s": timeout,
            "tolerance_hz": tolerance,
            "fpga": fpga_choice,
            "pin_modes": pin_modes,
            "pinned_modes": pinned_modes,
            "jesd_modes": jesd_constraints,
        }
        ss["fp_solver_options"] = options
        try:
            signature = fingerprint(rx, tx, options)
            targets = [
                SignalTarget(
                    direction=r.direction,
                    signal=r.signal,
                    path=r.path,
                    frequency_hz=float(r.target_mhz) * 1e6,
                )
                for r in targets_frame.itertuples()
            ]
        except (TypeError, ValueError) as exc:
            error = f"Invalid solve inputs: {exc}"
            signature = "invalid"
            targets = []
        ss["fp_solver_current_signature"] = signature
        job = ss.get("fp_solve_job")
        running = job is not None and not job.future.done()
        if error:
            st.error(error)
        if st.button(
            "Solve settings",
            disabled=running or error is not None,
            key="fp_solve_start",
        ):
            request = SolveRequest(
                rx=sr,
                tx=stx,
                targets=targets,
                automatic=set(automatic),
                rate_domains=domains,
                fpga=fpga,
                timeout_s=timeout,
                tolerance_hz=tolerance,
                jesd_modes=jesd_constraints,
            )
            ss["fp_solve_job"] = _start(request, signature)
            job = ss["fp_solve_job"]
            running = True
        if job is None:
            return
        if running:
            _running_status()
            return
        try:
            result = job.future.result()
        except Exception as exc:
            st.error(f"Solver failed: {exc}")
            return
        stale = signature != job.fingerprint
        if stale:
            st.warning(
                "Inputs changed since this solve. Run Solve settings again before applying a result."
            )
            ss.pop("fp_solver_result", None)
        message = f"{result.status.capitalize()}: {result.message}"
        if result.status in ("unavailable", "invalid", "infeasible"):
            st.warning(message)
        else:
            st.info(message)
        if result.rx is None and result.tx is None:
            return
        if not stale:
            ss["fp_solver_result"] = {
                "status": result.status,
                "message": result.message,
                "objective_bps": result.objective_bps,
                "achieved": result.achieved,
                "settings": result.settings,
                "elapsed_s": result.elapsed_s,
            }
        if result.objective_bps is not None:
            st.metric(
                "Transported data rate",
                f"{result.objective_bps / 1e9:.6g} Gbit/s",
            )
        if result.settings:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Setting": key,
                            "Current": settings.get(key),
                            "Proposed": value,
                        }
                        for key, value in result.settings.items()
                    ]
                ),
                hide_index=True,
            )
        if result.achieved:
            st.dataframe(pd.DataFrame(result.achieved), hide_index=True)
        if getattr(result, "modes", None):
            st.caption(
                "JESD modes: "
                + "; ".join(
                    f"{direction.upper()} {mode[0]} mode {mode[1]}"
                    for direction, mode in result.modes.items()
                )
            )
        st.button(
            "Apply solution",
            disabled=not job.applicable(signature),
            key="fp_solve_apply",
            on_click=apply_solution,
            args=(result.rx, result.tx),
        )
