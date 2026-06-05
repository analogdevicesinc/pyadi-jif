# Hardware validation tests for JESD systems via labgrid

Date: 2026-06-05

## Goal

Validate that pyadi-jif's computed JESD link + clock-tree configurations match
what real ADI evaluation systems report when booted, for every JESD-based place
on the labgrid coordinator at `10.0.0.41`.

JESD-based places discovered on the coordinator:

| Place  | Carrier | Daughterboard | JESD parts            | pyadi-jif model |
|--------|---------|---------------|-----------------------|-----------------|
| nemo   | zc706   | adrv9009      | ADRV9009              | exists          |
| nuc    | vcu118  | daq3 (fmcdaq3)| AD9680 + AD9152       | exists          |
| bq     | zc706   | adrv9371      | ADRV9371 (AD9371)     | **must be added** |

`mini2` (ADRV9002, LVDS/CMOS) is intentionally out of scope — it is not a JESD
device.

## Scope

1. Add an **ADRV9371** converter model to pyadi-jif (it does not exist yet),
   modeled by analogy to the existing ADRV9009 model.
2. Build a **hardware test layer** under `tests/hardware/` that uses labgrid +
   `adi_lg_plugins` to acquire/boot a place and read JESD/clock truth from the
   booted DUT over SSH.
3. Per-board **validation tests** that build the equivalent `adijif.system`,
   constrain it with the hardware-measured sample rate + JESD mode, solve, and
   assert pyadi-jif's computed lane rate / reference clock match hardware and
   that the JESD link is up.

## Architecture

### ADRV9371 model — `adijif/converters/adrv9371.py`

- `adrv9371_rx` (adc), `adrv9371_tx` (dac), and combined `adrv9371` classes,
  mirroring the ADRV9009 class hierarchy.
- Clocking equation identical in form to ADRV9009:
  `Lane Rate = sample_clock * M * Np * (10/8) / L`, integrated-PLL clocking.
- AD9371 (Mykonos) specific limits: JESD204B only, max lane rate 6.144 Gbps.
- Quick-configuration mode tables generated the same way as ADRV9009.
- Registered in `adijif/converters/__init__.py` (`supported_parts`) and exported
  from `adijif/__init__.py`.
- Unit tests in `tests/test_adrv9371.py` mirroring `tests/test_adrv9009.py`, so
  the model is covered even without hardware.

### Hardware test layer — `tests/hardware/`

- `conftest.py` — registers `--run-hardware` and `--lg-env` options plus the
  `hardware` marker (matching the labgrid-plugins convention), and a `dut`
  fixture that acquires the labgrid `RemotePlace`, ensures power/boot, waits for
  SSH, and yields a connection handle. Skips cleanly if the board is
  unreachable.
- `dut.py` — SSH helper (`root@<NetworkService address>` / `analog`) that reads
  hardware truth: `sampling_frequency` (IIO sysfs), JESD lane rate + link state
  from the `axi-jesd204-{rx,tx}` `status` node, and device/ref clock from
  `/sys/kernel/debug/clk/clk_summary`. Returns a normalized dataclass.
- `env/{nemo,nuc,bq}.yaml` — `RemotePlace` env yamls pointed at the coordinator.

### Per-board validation tests

- `test_hw_nemo_adrv9009.py`, `test_hw_nuc_fmcdaq3.py`, `test_hw_bq_adrv9371.py`.
- Each: read HW facts -> build `adijif.system(...)` with the board's FPGA dev
  kit -> constrain with HW sample rate + JESD mode -> `solve()` -> assert
  pyadi-jif's `bit_clock` (lane rate) and reference/device clock equal the
  HW-measured values, and assert the JESD link is up.

### Packaging

- New optional extra `hardware = [labgrid, adi-labgrid-plugins, paramiko]`.
- Hardware tests are `@pytest.mark.hardware` and skipped unless `--run-hardware`
  is given, so default CI is unaffected.

## Approach notes / trade-offs

- Hardware truth is read over SSH from sysfs/debugfs rather than via pyadi-iio:
  fewer dependencies, and the `axi-jesd204` status node is the authoritative
  source for lane rate + link state. L/M/F/S readback is best-effort; firm
  assertions are on rates + link state, which the DUT reports reliably.
- Tests live in pyadi-jif (not labgrid-plugins) because they validate pyadi-jif
  models; labgrid-plugins is consumed as a library for boot/acquire plumbing.
- Tests power-cycle their own board via the labgrid strategy and skip gracefully
  when hardware is unavailable, so a run is never blocked by board state.
