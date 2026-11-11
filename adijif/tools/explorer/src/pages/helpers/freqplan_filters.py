"""Project a selected Rx path's next DDC filter onto its input spectrum."""

from adijif.freqplan import (
    RxPlan,
    RxResult,
    StageOutput,
    rf_to_nco,
    wrap_frequency,
)


def downstream_filter_regions(
    source: StageOutput, downstream: StageOutput, nco_hz: float
) -> list[dict]:
    """Find transition and rejected intervals in the source's coordinates.

    The ideal DDC passes up to ``p = alpha * R / 2`` and rejects at
    ``s = R - p``, where R is its output rate. Classify exact intervals
    between these boundaries after projecting them through the periodic
    mixer. For a real ADC plot a frequency passes if either conjugate
    component passes. Equal input/output rates bypass the filter.

    Args:
        source: Spectrum feeding the filter.
        downstream: Next CDDC or FDDC on the selected path.
        nco_hz: Mixer frequency in the source's coordinates (folded for ADCs).

    Returns:
        Chart rows in MHz, labelled by the downstream filter and region.
        Passbands are unshaded; bypassed or unavailable filters return no rows.
    """
    if (
        source.error
        or downstream.error
        or source.kind not in ("adc", "cddc")
        or downstream.kind not in ("cddc", "fddc")
        or downstream.parent != source.channel
        or not 0 < downstream.rate_hz < source.rate_hz
    ):
        return []
    fs = source.rate_hz
    lo = 0.0 if source.kind == "adc" else -fs / 2
    hi = fs / 2
    p = downstream.passband_hz
    stop = downstream.rate_hz - p
    center = wrap_frequency(nco_hz, fs)
    centers = {center, -center} if source.kind == "adc" else {center}
    boundaries = {lo, hi}
    for center in centers:
        for edge in (-stop, -p, p, stop):
            for period in (-fs, 0.0, fs):
                boundary = center + edge + period
                if lo < boundary < hi:
                    boundaries.add(boundary)

    edges = sorted(boundaries)
    rows: list[dict] = []
    for left, right in zip(edges[:-1], edges[1:], strict=True):
        mid = (left + right) / 2
        distance = min(abs(wrap_frequency(mid - c, fs)) for c in centers)
        if distance <= p:
            continue
        region = "Rejected" if distance >= stop else "Transition"
        if (
            rows
            and rows[-1]["region"] == region
            and rows[-1]["hi_mhz"] == left / 1e6
        ):
            rows[-1]["hi_mhz"] = right / 1e6
        else:
            rows.append(
                {
                    "lo_mhz": left / 1e6,
                    "hi_mhz": right / 1e6,
                    "filter": downstream.channel.upper(),
                    "region": region,
                }
            )
    return rows


def rx_filter_overlays(
    plan: RxPlan, result: RxResult, path: tuple[str, ...]
) -> dict[str, list[dict]]:
    """Build a next-stage mask for each upstream plot of one selected Rx path.

    Args:
        plan: Rx settings, including RF and fine NCO frequencies.
        result: Spectra computed from that plan.
        path: Stage IDs in input-to-output order.

    Returns:
        Upstream stage IDs mapped to filter-region chart rows. The final
        stage, disabled stages, and bypassed filters have no overlay.
    """
    overlays = {}
    for source_id, downstream_id in zip(path[:-1], path[1:], strict=True):
        source = result.stages.get(source_id)
        downstream = result.stages.get(downstream_id)
        if (
            source is None
            or downstream is None
            or source.error
            or downstream.error
        ):
            continue
        if downstream.kind == "cddc":
            index = int(downstream.channel.removeprefix("cddc"))
            nco, _ = rf_to_nco(plan.cddc_rf_hz[index], source.rate_hz)
        elif downstream.kind == "fddc":
            index = int(downstream.channel.removeprefix("fddc"))
            nco = plan.datapath.fddc_nco_frequencies[index]
        else:
            continue
        regions = downstream_filter_regions(source, downstream, nco)
        if regions:
            overlays[source_id] = regions
    return overlays
