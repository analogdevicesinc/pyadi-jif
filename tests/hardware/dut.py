"""Read JESD + clock facts from a booted ADI Linux DUT.

This module is intentionally free of any pyadi-jif imports so it can be reused
and unit-tested on its own. It provides:

* :func:`coordinator_place_address` -- resolve the ``NetworkService`` IP a
  labgrid coordinator advertises for a place.
* :class:`DUT` -- a thin SSH wrapper (paramiko) that reads the authoritative
  ``axi-jesd204`` link status and IIO sample rates from the running board.
* :func:`parse_jesd_status` -- parse the kernel ``axi-jesd204-*`` ``status``
  text into a :class:`JesdLinkStatus` (kept separate so it is testable without
  hardware).
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class JesdLinkStatus:
    """Normalized view of one ``axi-jesd204-{rx,tx}`` link.

    Rates are stored in hertz. ``enabled``/``data`` capture link state.
    """

    enabled: Optional[bool] = None
    data: Optional[bool] = None  # link reached DATA phase
    lane_rate_hz: Optional[float] = None
    link_clock_hz: Optional[float] = None
    lmfc_rate_hz: Optional[float] = None
    sysref_captured: Optional[bool] = None
    raw: str = ""

    @property
    def up(self) -> bool:
        """True when the link is enabled and (if reported) in the DATA phase."""
        if not self.enabled:
            return False
        # Some driver versions don't print a link status line; treat missing
        # DATA as "don't know" rather than failure.
        return self.data is not False


_UNIT_HZ = {"hz": 1.0, "khz": 1e3, "mhz": 1e6, "ghz": 1e9}


def _to_hz(value: str, unit: str) -> float:
    return float(value) * _UNIT_HZ[unit.strip().lower()]


def parse_jesd_status(text: str) -> JesdLinkStatus:
    """Parse ``axi-jesd204-{rx,tx}`` ``status`` sysfs text.

    The ADI ``axi-jesd204`` driver prints a human-readable block such as::

        Link is enabled
        Measured Link Clock: 122.880 MHz
        Reported Link Clock: 122.880 MHz
        Lane rate: 4915.200 MHz
        Lane rate / 40: 122.880 MHz
        LMFC rate: 3.840 MHz
        Link status: DATA
        SYSREF captured: Yes

    Args:
        text: Raw contents of the ``status`` node.

    Returns:
        JesdLinkStatus: Parsed status (fields left ``None`` when not present).
    """
    st = JesdLinkStatus(raw=text)

    if re.search(r"Link is enabled", text, re.IGNORECASE):
        st.enabled = True
    elif re.search(r"Link is disabled", text, re.IGNORECASE):
        st.enabled = False

    m = re.search(r"Link status:\s*(\w+)", text, re.IGNORECASE)
    if m:
        st.data = m.group(1).upper() == "DATA"

    m = re.search(r"Lane rate:\s*([\d.]+)\s*([kKmMgG]?Hz)", text)
    if m:
        st.lane_rate_hz = _to_hz(m.group(1), m.group(2))

    m = re.search(
        r"(?:Measured|Reported) Link Clock:\s*([\d.]+)\s*([kKmMgG]?Hz)", text
    )
    if m:
        st.link_clock_hz = _to_hz(m.group(1), m.group(2))

    m = re.search(r"LMFC rate:\s*([\d.]+)\s*([kKmMgG]?Hz)", text)
    if m:
        st.lmfc_rate_hz = _to_hz(m.group(1), m.group(2))

    m = re.search(r"SYSREF captured:\s*(Yes|No)", text, re.IGNORECASE)
    if m:
        st.sysref_captured = m.group(1).lower() == "yes"

    return st


def coordinator_place_address(
    place: str, coordinator: str = "10.0.0.41:20408"
) -> Optional[str]:
    """Resolve the ``NetworkService`` address a coordinator advertises for a place.

    Uses the ``labgrid-client`` CLI (already installed alongside the
    coordinator) rather than the labgrid Python API so that resolution works
    even when the board is not acquired.

    Args:
        place: Coordinator place name (e.g. ``"nemo"``).
        coordinator: ``host:port`` of the labgrid coordinator.

    Returns:
        The advertised IP address as a string, or ``None`` if it cannot be
        resolved (place unknown, coordinator unreachable, no NetworkService).
    """
    try:
        out = subprocess.run(
            ["labgrid-client", "-x", coordinator, "-p", place, "show"],
            capture_output=True,
            text=True,
            timeout=20,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None

    in_ns = False
    for line in out.splitlines():
        if "NetworkService" in line:
            in_ns = True
        if in_ns:
            m = re.search(r"'address':\s*'([^']+)'", line)
            if m:
                return m.group(1)
    return None


@dataclass
class DUT:
    """SSH handle to a booted ADI Linux board for reading JESD/clock facts."""

    address: str
    username: str = "root"
    password: str = "analog"
    _client: object = field(default=None, repr=False)

    def connect(self, timeout: float = 10.0) -> "DUT":
        """Open the SSH connection. Raises on failure (caller decides to skip)."""
        import paramiko

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            self.address,
            username=self.username,
            password=self.password,
            timeout=timeout,
            allow_agent=False,
            look_for_keys=False,
        )
        self._client = client
        return self

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def cmd(self, command: str, timeout: float = 20.0) -> str:
        """Run a shell command on the DUT and return stdout (stderr appended)."""
        assert self._client is not None, "DUT not connected"
        _in, out, err = self._client.exec_command(command, timeout=timeout)
        stdout = out.read().decode(errors="replace")
        stderr = err.read().decode(errors="replace")
        return (stdout + stderr).strip()

    # -- JESD / clock readers -------------------------------------------------

    def jesd_status(self) -> Dict[str, JesdLinkStatus]:
        """Read every ``axi-jesd204-*`` link's ``status`` node.

        Returns:
            Mapping of device name (e.g. ``"axi-jesd204-rx"``) to parsed status.
        """
        # Enumerate the jesd device dirs, then cat each status node tagged with
        # its name so the output is unambiguous.
        script = (
            "for d in /sys/bus/platform/devices/*axi-jesd204-*; do "
            '[ -e "$d/status" ] || continue; '
            'echo "===$(basename $d)==="; cat "$d/status"; '
            "done"
        )
        out = self.cmd(script)
        result: Dict[str, JesdLinkStatus] = {}
        if not out:
            return result
        # re.split with a capturing group yields [pre, name1, body1, name2, ...]
        parts = re.split(r"===([^=]+)===", out)
        for i in range(1, len(parts), 2):
            name = parts[i].strip()
            body = parts[i + 1] if i + 1 < len(parts) else ""
            # Strip a trailing 'axi-XXXX.' prefix down to the role suffix.
            short = re.sub(r"^[0-9a-fx]+\.", "", name)
            result[short] = parse_jesd_status(body)
        return result

    def sampling_frequencies(self) -> Dict[str, float]:
        """Read IIO sampling frequencies (Hz) keyed by device name.

        Returns the first ``*sampling_frequency`` attribute found per device.
        """
        script = (
            "for dev in /sys/bus/iio/devices/iio:device*; do "
            'name=$(cat "$dev/name" 2>/dev/null); '
            'f=$(cat "$dev"/*sampling_frequency 2>/dev/null | head -n1); '
            '[ -n "$f" ] && echo "$name $f"; '
            "done"
        )
        out = self.cmd(script)
        freqs: Dict[str, float] = {}
        for line in out.splitlines():
            bits = line.split()
            if len(bits) >= 2:
                try:
                    freqs[bits[0]] = float(bits[-1])
                except ValueError:
                    continue
        return freqs

    def clock_summary(self) -> Dict[str, float]:
        """Parse ``/sys/kernel/debug/clk/clk_summary`` into name -> rate (Hz)."""
        out = self.cmd("cat /sys/kernel/debug/clk/clk_summary 2>/dev/null")
        rates: Dict[str, float] = {}
        for line in out.splitlines():
            cols = line.split()
            # Columns: clk_name flags enable_cnt prepare_cnt protect_cnt rate ...
            if len(cols) >= 6 and cols[5].lstrip("-").isdigit():
                rates[cols[0].lstrip()] = float(cols[5])
        return rates

    def iio_device_names(self) -> List[str]:
        """List IIO device names present on the DUT."""
        out = self.cmd(
            "for dev in /sys/bus/iio/devices/iio:device*; do "
            'cat "$dev/name" 2>/dev/null; done'
        )
        return [n for n in out.splitlines() if n.strip()]

    def jesd_framing(self) -> Dict[str, Dict[str, object]]:
        """Read per-link JESD framing from the booted device tree.

        The ``axi-jesd204`` driver's ``status`` node reports lane *rate* but not
        the converter framing, and a lane rate alone does not pin M and L
        independently (only the ratio). The device tree the board booted with
        carries the authoritative framing, so this reads the ``adi,*`` framing
        cells directly from ``/proc/device-tree``.

        Returns:
            Mapping of jesd node name -> dict with any of ``role`` ('rx'/'tx'),
            ``F`` (octets-per-frame), ``K`` (frames-per-multiframe), ``M``
            (converters-per-device), ``Np`` (bits-per-sample), ``N``
            (converter-resolution). Keys are present only when the node carries
            them (e.g. M/Np/N are typically only on the Tx framer node).
        """
        # For each device-tree node whose `compatible` mentions axi-jesd204,
        # emit the node basename, its compatible, and each framing property as
        # hex bytes (decoded big-endian below). Kept to one round trip.
        prop_map = {
            "adi,octets-per-frame": "F",
            "adi,frames-per-multiframe": "K",
            "adi,converters-per-device": "M",
            "adi,bits-per-sample": "Np",
            "adi,converter-resolution": "N",
        }
        script = (
            "for c in $(grep -rl axi-jesd204 /proc/device-tree 2>/dev/null "
            "| grep compatible); do "
            'node=$(dirname "$c"); '
            'echo "===$(basename $node)==="; '
            'echo "compatible=$(tr -d "\\000" < "$c")"; '
            "for p in " + " ".join(prop_map) + "; do "
            '[ -e "$node/$p" ] && echo "$p=$(od -An -tx1 "$node/$p" '
            '| tr -d " \\n")"; '
            "done; "
            "done"
        )
        out = self.cmd(script)
        result: Dict[str, Dict[str, object]] = {}
        cur: Optional[Dict[str, object]] = None
        for line in out.splitlines():
            m = re.match(r"===(.+)===", line)
            if m:
                cur = {}
                result[m.group(1).strip()] = cur
                continue
            if cur is None or "=" not in line:
                continue
            key, _, val = line.partition("=")
            if key == "compatible":
                cur["role"] = (
                    "tx"
                    if "jesd204-tx" in val
                    else ("rx" if "jesd204-rx" in val else "?")
                )
                continue
            if key in prop_map and val:
                try:
                    cur[prop_map[key]] = int(
                        val[:8], 16
                    )  # first u32, big-endian
                except ValueError:
                    continue
        return result
