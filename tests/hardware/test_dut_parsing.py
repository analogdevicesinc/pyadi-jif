"""Unit tests for the DUT status parsers (no hardware required)."""

from __future__ import annotations

from .dut import JesdLinkStatus, parse_jesd_status, parse_neigh_for_mac

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


# `ip neigh` output captured from the bq exporter host: the board's stable
# Xilinx GEM MAC maps to its live DHCP IP, while the stale configured .23 has no
# lladdr (FAILED). The IPv6 line must be ignored.
_NEIGH = """\
10.0.0.128 dev enp2s0 lladdr 00:0a:35:00:01:22 STALE
10.0.0.23 dev enp2s0 FAILED
10.0.0.41 dev enp2s0 lladdr 52:54:00:aa:bb:cc REACHABLE
fe80::20a:35ff:fe00:122 dev enp2s0 lladdr 00:0a:35:00:01:22 router STALE
"""


def test_neigh_finds_ipv4_for_mac():
    assert parse_neigh_for_mac(_NEIGH, "00:0a:35:00:01:22") == "10.0.0.128"


def test_neigh_is_case_insensitive():
    assert parse_neigh_for_mac(_NEIGH, "00:0A:35:00:01:22") == "10.0.0.128"


def test_neigh_unknown_mac_returns_none():
    assert parse_neigh_for_mac(_NEIGH, "aa:bb:cc:dd:ee:ff") is None


def test_neigh_failed_entry_has_no_mac():
    # The stale configured address (.23) is FAILED -> never returned.
    assert parse_neigh_for_mac(_NEIGH, "00:0a:35:00:01:22") != "10.0.0.23"


def test_neigh_empty():
    assert parse_neigh_for_mac("", "00:0a:35:00:01:22") is None
