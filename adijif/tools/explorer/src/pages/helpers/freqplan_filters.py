"""Project Rx filter regions and composite capture windows onto input spectra."""

from adijif.freqplan import (
    RxPlan,
    RxResult,
    Span,
    StageOutput,
    rf_to_nco,
    wrap_frequency,
    wrap_spans,
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


def _filter_limit(
    source: StageOutput, child: StageOutput, transition: bool
) -> float:
    """Return the filter edge, or the whole input band for a bypass."""
    if child.rate_hz == source.rate_hz:
        return source.rate_hz / 2
    return (
        child.rate_hz - child.passband_hz if transition else child.passband_hz
    )


def _adc_capture_bands(
    adc: StageOutput,
    coarse: StageOutput,
    fine: StageOutput,
    coarse_nco: float,
    zone: int,
    fine_nco: float,
    transition: bool,
) -> list[tuple[float, float]]:
    """Back-project one FDDC filter through the coarse mixer and filter.

    Unwrap the CDDC output only inside its own filter, then undo its NCO.
    The neighboring periods also cover transition bands that fold at the
    CDDC output Nyquist edge. Fold the result onto the real ADC display.
    """
    fine_limit = _filter_limit(coarse, fine, transition)
    coarse_limit = _filter_limit(adc, coarse, transition)
    inputs = wrap_spans(
        [Span(fine_nco - fine_limit, fine_nco + fine_limit, "")],
        coarse.rate_hz,
    )
    mixed = []
    for span in inputs:
        lo, hi = (span.lo, span.hi) if zone % 2 else (-span.hi, -span.lo)
        for period in (-coarse.rate_hz, 0.0, coarse.rate_hz):
            left = max(lo + period, -coarse_limit)
            right = min(hi + period, coarse_limit)
            if left < right:
                mixed.append(Span(left + coarse_nco, right + coarse_nco, ""))
    bands = []
    for span in wrap_spans(mixed, adc.rate_hz):
        lo = 0.0 if span.lo <= 0 <= span.hi else min(abs(span.lo), abs(span.hi))
        bands.append((lo, max(abs(span.lo), abs(span.hi))))
    return bands


def _merge_bands(bands: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Union overlapping or touching intervals without counting them twice."""
    merged: list[tuple[float, float]] = []
    for lo, hi in sorted(bands):
        if lo >= hi:
            continue
        if merged and lo <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(hi, merged[-1][1]))
        else:
            merged.append((lo, hi))
    return merged


def rx_capture_regions(plan: RxPlan, result: RxResult) -> list[dict]:
    """Combine all enabled FDDC capture windows separately for each ADC.

    Args:
        plan: Rx routing, NCO and decimation settings.
        result: Computed stages, used to exclude disabled or invalid paths.

    Returns:
        ADC-colored chart rows in MHz partitioning each ADC's first Nyquist
        zone into Captured, Transition and Blocked regions. Captured means
        at least one FDDC path passes that frequency without attenuation;
        Transition means only attenuated paths survive. The calculation
        does not depend on the configured input signals or target names.
    """
    rows = []
    for adc in result.stages.values():
        if adc.kind != "adc" or adc.error or adc.rate_hz <= 0:
            continue
        captured, surviving, outputs = [], [], []
        for fine in result.stages.values():
            if fine.kind != "fddc" or fine.error or fine.rate_hz <= 0:
                continue
            coarse = result.stages.get(fine.parent)
            if (
                coarse is None
                or coarse.error
                or coarse.kind != "cddc"
                or coarse.parent != adc.channel
                or coarse.rate_hz <= 0
            ):
                continue
            index = int(coarse.channel.removeprefix("cddc"))
            nco, zone = rf_to_nco(plan.cddc_rf_hz[index], adc.rate_hz)
            index = int(fine.channel.removeprefix("fddc"))
            fine_nco = plan.datapath.fddc_nco_frequencies[index]
            outputs.append(fine.channel.upper())
            for bands, transition in ((captured, False), (surviving, True)):
                bands.extend(
                    _adc_capture_bands(
                        adc, coarse, fine, nco, zone, fine_nco, transition
                    )
                )
        captured, surviving = _merge_bands(captured), _merge_bands(surviving)
        edges = sorted(
            {
                0.0,
                adc.rate_hz / 2,
                *(e for band in captured + surviving for e in band),
            }
        )
        channel_rows = []
        for lo, hi in zip(edges[:-1], edges[1:], strict=True):
            mid = (lo + hi) / 2
            region = "Blocked"
            if any(left <= mid <= right for left, right in captured):
                region = "Captured"
            elif any(left <= mid <= right for left, right in surviving):
                region = "Transition"
            if channel_rows and channel_rows[-1]["region"] == region:
                channel_rows[-1]["hi_mhz"] = hi / 1e6
            else:
                channel_rows.append(
                    {
                        "stage": adc.channel.upper(),
                        "lo_mhz": lo / 1e6,
                        "hi_mhz": hi / 1e6,
                        "region": region,
                        "fddcs": ", ".join(outputs) or "None",
                        "captured_mhz": sum(
                            right - left for left, right in captured
                        )
                        / 1e6,
                    }
                )
        rows.extend(channel_rows)
    return rows
