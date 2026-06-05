"""Unit tests for the DUT status parsers (no hardware required)."""

from __future__ import annotations

from .dut import JesdLinkStatus, parse_jesd_status

_STATUS_UP = """Link is enabled
Measured Link Clock: 122.880 MHz
Reported Link Clock: 122.880 MHz
Lane rate: 4915.200 MHz
Lane rate / 40: 122.880 MHz
LMFC rate: 3.840 MHz
Link status: DATA
SYSREF captured: Yes
SYSREF alignment error: No
"""

_STATUS_DOWN = """Link is disabled
"""


def test_parse_status_up():
    st = parse_jesd_status(_STATUS_UP)
    assert isinstance(st, JesdLinkStatus)
    assert st.enabled is True
    assert st.data is True
    assert st.up is True
    assert st.lane_rate_hz == 4.9152e9
    assert st.link_clock_hz == 122.88e6
    assert st.lmfc_rate_hz == 3.84e6
    assert st.sysref_captured is True


def test_parse_status_down():
    st = parse_jesd_status(_STATUS_DOWN)
    assert st.enabled is False
    assert st.up is False
    assert st.lane_rate_hz is None


def test_parse_status_ghz_units():
    st = parse_jesd_status("Link is enabled\nLane rate: 4.915200 GHz\n")
    assert st.lane_rate_hz == 4.9152e9
    # No 'Link status' line -> data unknown, but enabled -> treat as up.
    assert st.data is None
    assert st.up is True


def test_parse_status_empty():
    st = parse_jesd_status("")
    assert st.enabled is None
    assert st.up is False
