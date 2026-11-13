"""Controls for ACE-approved ADRV9042 external clock and link settings."""

import streamlit as st

from adijif.converters.adrv9042 import _adrv9042_link, adrv9042


def select_link(link: _adrv9042_link, key: str) -> _adrv9042_link:
    """Select a hardware link instance before building its transport controls."""
    count = 3 if link.converter_type == "adc" else 2
    index = st.selectbox(
        "Hardware framer" if count == 3 else "Hardware deframer",
        range(count),
        index=link.link_index,
        key=f"{key}_link_index",
    )
    return type(link)(model=link.model, solver=link.solver, link_index=index)


def configure_reference(device: object, key: str) -> None:
    """Enter DEVCLK from the ACE-approved configuration."""
    st.caption(
        "Enter DEVCLK and interface sample rates from an ACE-approved configuration. Transport candidates do not generate or qualify a complete firmware profile."
    )
    device.reference_clock = st.number_input(
        "DEVCLK reference (Hz)",
        min_value=61_440_000,
        max_value=491_520_000,
        value=245_760_000,
        step=1,
        key=f"{key}_reference_clock",
    )


def configure_link(
    link: _adrv9042_link, key: str, *, reference: bool = True
) -> None:
    """Configure transport framing and optional standalone DEVCLK."""
    if reference:
        configure_reference(link, key)
    standard = st.selectbox(
        "JESD standard",
        link.available_jesd_modes,
        index=1,
        key=f"{key}_standard",
    )
    modes = link.quick_configuration_modes[standard]
    selected = st.selectbox(
        "Transport candidate",
        list(modes),
        index=list(modes).index("M4L2Np16S1"),
        key=f"{key}_mode",
    )
    link.set_quick_configuration_mode(selected, standard)
    link.sample_clock = st.number_input(
        "Interface sample rate (Hz)",
        min_value=1,
        max_value=491_520_000,
        value=122_880_000,
        key=f"{key}_sample_clock",
    )
    link.cddc_cduc_bypassed = st.toggle(
        "CDDC/CDUC bypassed", key=f"{key}_bypassed"
    )
    configure_framing(link, key)


def configure_framing(link: _adrv9042_link, key: str) -> None:
    """Allow ACE framing overrides after selecting a transport candidate."""
    standard = link.jesd_class
    selected = f"M{int(link.M)}L{int(link.L)}Np{int(link.Np)}S{int(link.S)}"
    # Include the mode in framing widget keys so selecting a new candidate
    # starts from that candidate's valid canonical K/E rather than old state.
    framing_key = f"{key}_{standard}_{selected}"
    cols = st.columns(4)
    with cols[0]:
        link.K = st.number_input(
            "K",
            min_value=1,
            max_value=32 if standard == "jesd204b" else 256,
            value=int(link.K),
            key=f"{framing_key}_k",
        )
    with cols[1]:
        if standard == "jesd204c":
            link.E = st.selectbox(
                "E",
                link.E_available,
                index=link.E_available.index(link.E),
                key=f"{framing_key}_e",
            )
    with cols[2]:
        link.N = st.number_input(
            "N",
            min_value=1,
            max_value=int(link.Np),
            value=int(link.N),
            key=f"{framing_key}_n",
        )
    with cols[3]:
        link.CS = st.selectbox("CS", link.CS_available, key=f"{framing_key}_cs")
    link.HD = st.selectbox(
        "HD", [0, 1], index=int(link.HD), key=f"{framing_key}_hd"
    )


def configure_device(device: adrv9042) -> None:
    """Expose enablement, physical lane ownership, and all five transports."""
    configure_reference(device, "adrv9042")
    for name in device._link_names:
        link = getattr(device, name)
        link.enabled = st.checkbox(
            name.capitalize(),
            value=link.enabled,
            key=f"adrv9042_{name}_enabled",
        )
        if not link.enabled:
            continue
        with st.expander(f"{name.capitalize()} settings", expanded=True):
            key = f"adrv9042_{name}"
            configure_link(link, key, reference=False)
            start = {
                "framer0": 0,
                "framer1": 2,
                "framer2": 4,
                "deframer0": 0,
                "deframer1": 2,
            }[name]
            link.lane_mapping = st.multiselect(
                "Physical lanes (logical lane order)",
                range(8),
                default=list(range(start, start + link.L))
                if start + link.L <= 8
                else list(range(link.L)),
                key=f"{key}_lanes",
            )
    try:
        device.validate_config()
    except ValueError as exc:
        st.error(str(exc))


def render_system(system: object) -> None:
    """Configure and solve an ADRV9042 multi-link system in Explorer."""
    configure_device(system.converter)
    if st.button("Solve ADRV9042 clock tree", key="adrv9042_solve"):
        try:
            result = system.solve()
        except Exception as exc:
            st.error(f"Error solving ADRV9042: {exc}")
            return
        st.subheader("Clock configuration")
        st.json(result["clock"])
        st.subheader("Active link configurations")
        st.json({key: value for key, value in result.items() if key != "clock"})
