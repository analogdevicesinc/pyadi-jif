"""Browser regressions for composite frequency-planner capture masks."""

import re

import pytest
from playwright.sync_api import expect

from adijif.freqplan import default_rx_plan, default_tx_plan, dumps


@pytest.mark.e2e
def test_composite_capture_stays_clear_across_selected_adcs(
    page, streamlit_app
):
    """Union overlapping outputs before shading, including legend changes."""
    rx = default_rx_plan()
    rx.signals = []
    rx.targets = {}
    rx.cddc_rf_hz[:2] = [5e9, 5.6e9]
    rx.datapath.cddc_enabled = [True, True, False, False]
    rx.datapath.fddc_enabled = [
        True,
        False,
        True,
        False,
        False,
        False,
        False,
        False,
    ]
    rx.datapath.fddc_decimations[0] = 4
    rx.datapath.fddc_decimations[2] = 4
    config = dumps(
        rx,
        default_tx_plan(),
        {
            "rx": {"path": "all", "show_composite_capture": True},
        },
    )
    page.goto(streamlit_app)
    page.get_by_text("Frequency Planner", exact=True).first.click()
    page.get_by_role("switch", name="Composite ADC capture").wait_for()
    page.locator('input[type="file"]').set_input_files(
        {
            "name": "overlapping-adc-capture.json",
            "mimeType": "application/json",
            "buffer": config.encode(),
        }
    )
    block = (
        page.get_by_text("All ADCs", exact=True)
        .locator("xpath=ancestor::div[@data-testid='stHorizontalBlock']")
        .first
    )
    adc = block.locator("svg.marks").first
    captured = adc.locator('[aria-label*="Composite capture: Captured;"]')
    masks = adc.locator('[aria-label*="Composite capture:"]')

    def assert_clear_window(hi, bandwidth):
        expect(captured).to_have_count(1)
        expect(captured).to_have_attribute(
            "aria-label",
            re.compile(
                rf".*Low \(MHz\): 4500;.*High \(MHz\): {hi};.*"
                rf"Total captured \(MHz\): {bandwidth}(?:;|$)"
            ),
        )
        expect(captured).to_have_attribute("fill-opacity", "0")
        # No other mask may lie underneath the transparent capture window.
        for label in masks.evaluate_all(
            "els => els.map(el => el.getAttribute('aria-label'))"
        ):
            if "Composite capture: Captured;" in label:
                continue
            lo = float(re.search(r"Low \(MHz\): ([^;]+)", label)[1])
            upper = float(re.search(r"High \(MHz\): ([^;]+)", label)[1])
            assert upper <= 4500 or lo >= hi, label

    # ADC0 captures 4500..5500; ADC1 captures 5100..6100. The other ADCs
    # reject everything, but must not shade the union of these two windows.
    assert_clear_window(6100, 1600)
    adc.locator(".role-legend-label").filter(has_text="ADC0").click()
    assert_clear_window(5500, 1000)
    adc.locator(".role-legend-label").filter(has_text="ADC1").click(
        modifiers=["Shift"]
    )
    assert_clear_window(6100, 1600)
    adc.locator(".role-legend-label").filter(has_text="ADC2").click()
    expect(captured).to_have_count(0)
    expect(masks).to_have_count(1)
    expect(masks).to_have_attribute(
        "aria-label", re.compile(".*Composite capture: Blocked;.*")
    )
    adc.dblclick(position={"x": 140, "y": 40})
    assert_clear_window(6100, 1600)
