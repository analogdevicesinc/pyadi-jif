# Export solved configurations to pyadi-dt

pyadi-jif can export a solved system as the versioned `adi.jif-dt` contract.
The contract contains solved electrical intent—JESD links, semantic clock
requirements, rates, dividers, and FPGA settings—but deliberately excludes
physical clock output channels and device-tree labels.

pyadi-dt owns that physical placement and joins each semantic ID to a board
profile before generating or modifying a device tree. This prevents requested
clock order inside the solver from being mistaken for HMC7044 or AD952x output
channel numbering.

## Solve and export an AD9680 system

The complete runnable example is checked by the normal example test suite:

```{literalinclude} ../../examples/ad9680_jif_dt_contract.py
:language: python
:caption: examples/ad9680_jif_dt_contract.py
```

Run it directly or redirect the portable result to a file:

```bash
python examples/ad9680_jif_dt_contract.py > ad9680.jif-dt.json
```

The important API boundary is:

```python
solution = system.solve()
contract = system.export_config(format="adi.jif-dt", solution=solution)
contract.to_json_file("ad9680.jif-dt.json")
```

Passing the existing `solution` avoids solving twice. If it is omitted,
`export_config()` solves the current system first.

## What the producer emits

For the AD9680 example, the contract contains one `ad9680.rx` link and four
semantic clock requirements:

- `ad9680.device-clock`
- `ad9680.sysref`
- `ad9680.fpga-ref`
- `ad9680.fpga-link`

Each clock has a solved rate and divider, but no `output_index` or `dt_label`.
Those values depend on the carrier and FPGA design, not the solver.

The output begins with:

```json
{
  "clock_requirements": [
    {
      "divider": 3,
      "id": "ad9680.device-clock",
      "rate_hz": 1000000000,
      "role": "converter-device",
      "sink": "AD9680",
      "source": "HMC7044"
    }
  ],
  "producer": {
    "name": "pyadi-jif",
    "version": "0.1.6"
  },
  "schema": "adi.jif-dt",
  "version": "1.0"
}
```

## Consumer-side binding

pyadi-dt loads the JSON with its strict `JifDtContract` projection, then uses a
separate `JifDtBindings` object to map semantic requirements to physical clock
channels and XSA/device-tree labels. See the
[pyadi-dt interface contract documentation](https://developer.analog.com/docs/pyadi-dt/latest/developer/jif_dt_contract/)
for binding examples, validation order, and compatibility rules.

The producer and consumer both enforce contract version 1.0. Unsupported
versions, inconsistent JESD transport/lane rates, duplicate IDs, fractional
hertz, and non-JSON solver objects fail before a device tree can be changed.

## Current topology support

`system.export_config()` initially supports one non-nested ADC or DAC converter.
Nested transceivers and MxFE systems require an explicit follow-up extension so
their multiple links retain stable identities rather than relying on computed
dictionary key parsing.