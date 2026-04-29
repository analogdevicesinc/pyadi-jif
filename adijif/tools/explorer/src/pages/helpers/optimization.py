"""Helper functions for the System Configurator's optimization controls."""

from typing import Any

import streamlit as st

from adijif.sys.clocks_bundle import ClocksBundle

_UNIT_MULT = {"Hz": 1.0, "kHz": 1e3, "MHz": 1e6, "GHz": 1e9}
_KIND_LABELS = {
    "equal_to": "equal to",
    "range": "range",
    "min": "min",
    "max": "max",
}


def _next_id(state_key: str) -> int:
    """Return a fresh monotonic id for a row in ``state_key`` rows."""
    counter_key = f"{state_key}_next_id"
    rid = st.session_state.get(counter_key, 1)
    st.session_state[counter_key] = rid + 1
    return rid


def gen_clock_constraints(clocks: ClocksBundle) -> None:
    """Render the clock-constraint editor and apply each row to ``clocks``.

    Rows persist in ``st.session_state["sys_constraints"]``. Each constraint
    row is rendered with a stable ``id`` so Streamlit widget state survives
    additions and removals.

    Args:
        clocks: ClocksBundle from ``system.initialize()``. Constraints are
            applied via :meth:`ClocksBundle.constrain`.
    """
    state_key = "sys_constraints"
    st.session_state.setdefault(state_key, [])
    rows = st.session_state[state_key]

    clock_names = sorted(clocks.keys())
    if not clock_names:
        st.info("No inter-component clocks available for this configuration.")
        return

    st.markdown("**Clock Constraints**")
    st.caption(
        "Narrow which clock rates are valid (e.g. force the FPGA reference "
        "clock into a range). Bad rows are skipped with a warning."
    )

    units = st.selectbox(
        "Units (applied to all constraint values)",
        options=list(_UNIT_MULT.keys()),
        index=2,
        key="sys_constraints_units",
    )
    mult = _UNIT_MULT[units]

    to_remove = []
    for idx, row in enumerate(rows):
        rid = row["id"]
        cols = st.columns([3, 2, 2, 2, 1])
        with cols[0]:
            default_clock = (
                row["clock"] if row["clock"] in clock_names else clock_names[0]
            )
            st.selectbox(
                "Clock",
                options=clock_names,
                index=clock_names.index(default_clock),
                key=f"sys_c_clock_{rid}",
            )
        with cols[1]:
            kind_keys = list(_KIND_LABELS.keys())
            st.selectbox(
                "Type",
                options=kind_keys,
                index=kind_keys.index(row["kind"]),
                format_func=lambda k: _KIND_LABELS[k],
                key=f"sys_c_kind_{rid}",
            )
        kind = st.session_state[f"sys_c_kind_{rid}"]
        with cols[2]:
            st.number_input(
                f"Value ({units})" if kind != "range" else f"Min ({units})",
                value=float(row["v1"]),
                format="%g",
                key=f"sys_c_v1_{rid}",
            )
        with cols[3]:
            if kind == "range":
                st.number_input(
                    f"Max ({units})",
                    value=float(row["v2"]),
                    format="%g",
                    key=f"sys_c_v2_{rid}",
                )
            else:
                st.write("")
        with cols[4]:
            st.write("")
            if st.button("✕", key=f"sys_c_rm_{rid}", help="Remove row"):
                to_remove.append(idx)

    if st.button("Add Constraint", key="sys_c_add"):
        rows.append(
            {
                "id": _next_id(state_key),
                "clock": clock_names[0],
                "kind": "range",
                "v1": 100.0,
                "v2": 200.0,
            }
        )
        st.rerun()

    if to_remove:
        for i in reversed(to_remove):
            rows.pop(i)
        st.rerun()

    for row in rows:
        rid = row["id"]
        clock_name = st.session_state.get(f"sys_c_clock_{rid}", row["clock"])
        kind = st.session_state.get(f"sys_c_kind_{rid}", row["kind"])
        v1 = st.session_state.get(f"sys_c_v1_{rid}", row["v1"])
        v2 = st.session_state.get(f"sys_c_v2_{rid}", row["v2"])
        row["clock"] = clock_name
        row["kind"] = kind
        row["v1"] = v1
        row["v2"] = v2
        try:
            if kind == "range":
                clocks.constrain(clock_name, range=(v1 * mult, v2 * mult))
            else:
                clocks.constrain(clock_name, **{kind: v1 * mult})
        except Exception as e:  # noqa: BLE001
            st.warning(f"Skipping constraint on {clock_name!r}: {e}")


def gen_clock_objectives(sys: Any, clocks: ClocksBundle) -> None:
    """Render the clock-objective editor and register each row with ``sys``.

    Rows persist in ``st.session_state["sys_objectives"]``. Each row is
    applied via :meth:`adijif.system.system.add_objective`.

    Args:
        sys: The ``adijif.system`` instance to register objectives on.
        clocks: ClocksBundle whose entries are used as objective expressions.
    """
    state_key = "sys_objectives"
    st.session_state.setdefault(state_key, [])
    rows = st.session_state[state_key]

    clock_names = sorted(clocks.keys())
    if not clock_names:
        return

    st.markdown("**Clock Objectives**")
    st.caption(
        "Rank valid configurations by minimizing or maximizing a clock. "
        "Lower tier = higher priority; tier 1 only breaks ties left by "
        "tier 0."
    )

    to_remove = []
    for idx, row in enumerate(rows):
        rid = row["id"]
        cols = st.columns([3, 1, 1, 1, 2, 1])
        with cols[0]:
            default_clock = (
                row["clock"] if row["clock"] in clock_names else clock_names[0]
            )
            st.selectbox(
                "Clock",
                options=clock_names,
                index=clock_names.index(default_clock),
                key=f"sys_o_clock_{rid}",
            )
        with cols[1]:
            st.selectbox(
                "Sense",
                options=["min", "max"],
                index=["min", "max"].index(row["sense"]),
                key=f"sys_o_sense_{rid}",
            )
        with cols[2]:
            st.number_input(
                "Tier",
                value=int(row["tier"]),
                min_value=0,
                step=1,
                key=f"sys_o_tier_{rid}",
            )
        with cols[3]:
            st.number_input(
                "Weight",
                value=float(row["weight"]),
                format="%g",
                key=f"sys_o_weight_{rid}",
            )
        with cols[4]:
            st.text_input(
                "Name (optional)",
                value=row["name"],
                key=f"sys_o_name_{rid}",
            )
        with cols[5]:
            st.write("")
            if st.button("✕", key=f"sys_o_rm_{rid}", help="Remove row"):
                to_remove.append(idx)

    if st.button("Add Objective", key="sys_o_add"):
        rows.append(
            {
                "id": _next_id(state_key),
                "clock": clock_names[0],
                "sense": "min",
                "tier": 0,
                "weight": 1.0,
                "name": "",
            }
        )
        st.rerun()

    if to_remove:
        for i in reversed(to_remove):
            rows.pop(i)
        st.rerun()

    for row in rows:
        rid = row["id"]
        clock_name = st.session_state.get(f"sys_o_clock_{rid}", row["clock"])
        sense = st.session_state.get(f"sys_o_sense_{rid}", row["sense"])
        tier = st.session_state.get(f"sys_o_tier_{rid}", row["tier"])
        weight = st.session_state.get(f"sys_o_weight_{rid}", row["weight"])
        name = st.session_state.get(f"sys_o_name_{rid}", row["name"])
        row["clock"] = clock_name
        row["sense"] = sense
        row["tier"] = tier
        row["weight"] = weight
        row["name"] = name
        try:
            sys.add_objective(
                clocks[clock_name],
                sense=sense,
                tier=int(tier),
                weight=float(weight),
                name=name or None,
            )
        except Exception as e:  # noqa: BLE001
            st.warning(f"Skipping objective on {clock_name!r}: {e}")
