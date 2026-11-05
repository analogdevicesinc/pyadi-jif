# JIF Tools Explorer

The JIF Tools Explorer is an interactive web-based application built with Streamlit that provides a graphical interface for configuring and exploring JESD204 based systems with Analog Devices converters and clock chips.

```{admonition} New to JIF Tools?
:class: tip
Check out the [Quick Start Guide](tools_quickstart.md) for step-by-step examples to get up and running in minutes!
```

## Installation

The JIF Tools Explorer is included with the pyadi-jif package. Install it with:

```bash
pip install 'pyadi-jif[cplex]'
```

For development or to include Streamlit dependencies:

```bash
pip install 'pyadi-jif[cplex,tools,draw]'
```

## Launching the Application

Once installed, you can launch the JIF Tools Explorer from the command line:

```bash
jiftools
```

This will start a local web server and automatically open the application in your default web browser. The application typically runs at `http://localhost:8501`.

## Application Overview

The JIF Tools Explorer provides six tools accessible from the sidebar:

1. **JESD204 Mode Selector** - Explore and filter JESD204 modes for ADI converters
2. **Clock Configurator** - Configure clock distribution chips for your system
3. **System Configurator** - Complete end-to-end system configuration (FPGA + Converter + Clock)
4. **ADF4030 System Designer** - Plan an Aion (ADF4030) clock-distribution
   system: pick the cascade / tree / hybrid / hybrid2 architecture and the
   per-Unit-Board sizing, then view the partition summary and a topology
   diagram. See [Clocking → ADF4030 Architectures](clocking/adf4030_architecture.md)
   for the underlying Python API.
5. **Basic JESD204 Calculator** - Calculate lane rate, sample rate, and core
   clock directly from a small set of JESD204 link parameters
6. **Frequency Planner** - Place signals through a converter's DDC/DUC chains
   and check what each output captures

---

## JESD204 Mode Selector

The JESD204 Mode Selector helps you find suitable JESD204 modes for your ADI converter based on your application requirements.

### Features

- **Part Selection**: Choose from a wide range of ADI converters (ADCs, DACs, MxFEs, Transceivers)
- **Datapath Configuration**: Configure decimation/interpolation settings
- **Sample Rate Control**: Set converter sample rates with flexible units (Hz, kHz, MHz, GHz)
- **Mode Filtering**: Filter JESD204 modes by parameters (M, L, N, Np, F, S, K, HD, CS)
- **Validation**: Automatically validates modes against device constraints
- **Visual Diagrams**: View clock tree diagrams for ADC converters
- **Export**: Export mode tables to CSV

```{figure} _static/imgs/jesdmodeselector.png
:alt: JESD204 Mode Selector showing the AD9680 datapath diagram and configuration controls
:width: 100%

The Mode Selector pairs the selected converter's datapath diagram with the
controls that determine its sample rate and JESD204 operating mode.
```

### Usage

#### 1. Select a Converter

From the "Select a part" dropdown, choose your converter. The list includes:
- ADCs: AD9680, AD9625, etc.
- DACs: AD9144, AD9136, etc.
- MxFEs: AD9081, AD9082, etc.
- Transceivers: adrv9009, etc.

#### 2. Configure Datapath

In the "Datapath Configuration" section:

**For ADCs:**
- Set decimation values (CDDC, FDDC if available)
- Configure converter sample rate

**For DACs:**
- Set interpolation values (CDUC, FDUC if available)
- Configure converter sample rate

#### 3. Set Converter Rate

1. Select units (Hz, kHz, MHz, or GHz)
2. Enter the desired converter rate
3. The derived sample rate will be calculated automatically

#### 4. Filter JESD Modes

Use the multiselect controls in the "Configuration" section to filter modes by JESD204 parameters:

- **M**: Number of converters
- **L**: Number of lanes
- **N**: Converter resolution
- **Np**: Number of bits per sample
- **F**: Octets per frame
- **S**: Samples per converter per frame cycle
- **K**: Frames per multiframe
- **HD**: High density mode
- **CS**: Control bits per sample

#### 5. View Results

The "JESD204 Modes" section displays:
- Valid modes matching your criteria
- Lane rates and sample rates for each mode
- Toggle to show/hide invalid modes

```{figure} _static/imgs/jesdmodeselector_modes.png
:alt: JESD204 Mode Selector filters and valid mode table shown side by side
:width: 100%

Filters and matching modes stay side by side, making it easy to compare lane
counts, rates, and framing parameters while narrowing the result set.
```

### Example Workflow

```python
# Example: Configure AD9680 for 1 GSPS operation

1. Select part: "AD9680"
2. Set decimation: 1 (no decimation)
3. Set units: GHz
4. Set converter rate: 1.0 GHz
5. Filter by L=4 (4 lanes)
6. Review valid modes in the table
7. Note lane rates for FPGA configuration
```

---

## Clock Configurator

The Clock Configurator helps you configure ADI clock distribution chips (e.g., HMC7044, AD9545) to generate the required clocks for your system.

### Features

- **Multi-Clock Output**: Configure multiple output clocks with different frequencies
- **Reference Clock**: Set input reference clock frequency
- **Internal Configuration**: Control internal clock chip parameters (VCO, dividers, etc.)
- **Visual Diagrams**: View generated clock tree diagrams
- **Device Tree Export**: Export configuration as device tree fragments (for supported chips)

```{figure} _static/imgs/clockconfigurator.png
:alt: Clock Configurator showing HMC7044 reference and output clock inputs
:width: 100%

The Clock Configurator collects the reference, requested outputs, and optional
internal-divider constraints on one page.
```

### Usage

#### 1. Select a Clock Chip

Choose from supported clock chips:
- HMC7044 - High-performance clock distribution
- AD9545 - Quad/Octal Clock Generator & Synchronizer
- And more...

#### 2. Configure Clocks

**Reference Clock:**
- Set the input reference clock frequency

**Output Clocks:**
1. Specify number of clock outputs needed
2. For each output:
   - Set the desired frequency
   - Assign a descriptive name (e.g., "ADC_CLK", "FPGA_REF")

#### 3. Internal Configuration

Adjust internal parameters if needed:
- VCO frequency ranges
- Divider values
- Distribution settings

The tool will automatically calculate valid configurations.

#### 4. View Results

If a valid configuration is found:
- Configuration parameters are displayed
- Clock tree diagram shows the signal flow
- Device tree fragment (if supported) for Linux driver integration

```{figure} _static/imgs/clockconfigurator_diagram.png
:alt: Solved HMC7044 clock configuration and generated clock tree diagram
:width: 100%

The solved divider values are followed by a generated clock tree, so the
numeric configuration and signal path can be reviewed together.
```

### Example Workflow

```python
# Example: HMC7044 configuration for AD9680 + FPGA

1. Select part: "hmc7044"
2. Set reference clock: 125 MHz
3. Configure outputs:
   - Output 1: 1000 MHz (name: "ADC_SAMPLE_CLK")
   - Output 2: 250 MHz (name: "FPGA_REF_CLK")
4. Review generated configuration
5. View clock tree diagram
6. Export device tree fragment
```

---

## System Configurator

The System Configurator provides end-to-end configuration of a complete JESD204 system including FPGA, converter, and clock chip.

### Features

- **Complete System**: Configure all components together
- **FPGA Integration**: Set up FPGA transceiver parameters (Xilinx, Intel)
- **Development Kit Presets**: Quick setup for common evaluation boards
- **Automatic Solving**: Automatically finds valid configurations across all components
- **System Diagram**: Visualize the complete system architecture

```{figure} _static/imgs/systemconfigurator.png
:alt: System Configurator showing AD9680, HMC7044, ZCU102, converter, and FPGA controls
:width: 100%

System-level choices appear first, followed by converter and FPGA controls in
parallel columns for an at-a-glance view of the complete setup.
```

### Usage

#### 1. Select Components

Choose:
- **Converter**: Your ADI converter (ADC/DAC/MxFE)
- **Clock Chip**: Clock distribution chip
- **FPGA**: Target FPGA vendor (Xilinx, Intel)

#### 2. Configure Converter

Set converter parameters:
- Sample clock frequency
- Decimation/interpolation
- JESD204 mode

#### 3. Configure FPGA

Select FPGA settings:
- Development kit (optional)
- Transceiver type (QPLL/CPLL for Xilinx)
- Reference clock frequency

#### 4. Set VCXO/Reference

Specify the system reference clock (VCXO) frequency.

#### 5. Solve and View

Click solve to:
- Calculate complete system configuration
- Validate all constraints are met
- Generate system diagram
- Show configuration for all components

```{figure} _static/imgs/systemconfigurator_diagram.png
:alt: Solved AD9680 HMC7044 ZCU102 system configuration and complete system diagram
:width: 100%

The solved JESD204 parameters sit directly above the complete converter,
clock, and FPGA signal-flow diagram. This example uses AD9680 quick mode 136
(`0x88`) with four lanes at 10 Gbps.
```

### Example Workflow

```python
# Example: AD9680 + HMC7044 + Xilinx ZCU102

1. Create system:
   - Converter: "AD9680"
   - Clock: "hmc7044"
   - FPGA: "xilinx"
   - VCXO: 125 MHz

2. Configure converter:
   - Sample rate: 1 GSPS
   - Decimation: 1
   - Mode: 0x88
   - K: 32

3. Configure FPGA:
   - Dev kit: "zcu102"
   - Force QPLL: Yes

4. Solve system

5. View results:
   - Clock configuration
   - Converter settings
   - FPGA transceiver config
   - JESD204 link parameters
   - System block diagram
```

---

(adf4030-system-designer)=
## ADF4030 System Designer

The ADF4030 System Designer helps you plan how Aion (ADF4030) chips
chain together to produce SYSREF for large multi-converter systems.
Pick an architecture, set the per-Unit-Board sizing, and the page
renders the partition summary plus a topology diagram of one Unit
Board (or the full system).

### Features

- **Four architectures**: cascade, tree, hybrid (cascade-of-trees),
  hybrid2 (tree-of-cascades)
- **Partition summary**: per-FPGA / per-Aion / per-Apollo counts,
  plus the number of Unit Boards required for the total Apollo count
- **Topology diagram**: rendered SVG of the Aion / Apollo / FPGA
  hierarchy with the architecture-appropriate intra-FPGA connections
- **Scope selector**: per-Unit-Board (fast) or full system (slower at
  large `N`)

```{figure} _static/imgs/adf4030systemdesigner.png
:alt: ADF4030 System Designer inputs and partition summary
:width: 100%

Architecture and board-sizing controls update the partition summary and
topology in the same view.
```

### Usage

#### 1. Sizing inputs

- **Total Apollo devices (N)**: how many Apollo data converters in the system.
- **Apollos per Unit Board**: how many Apollos a single board hosts.
- **FPGAs per Unit Board**: how many FPGAs partition the Aions on a board.

#### 2. Architecture and branch count

Pick an architecture. For `tree`, `hybrid`, and `hybrid2`, a
**Branches (`N_branch`)** input appears — that is how many sub-branches
the tree fans into.

#### 3. Diagram scope

Toggle between **`ub`** (one Unit Board) and **`system`** (the full
multi-board layout).

#### 4. Review the partition

The "Partition summary" block lists the same fields that the Python
`Adf4030Architecture.summary` property emits, plus the calculated
`N_UB`. The topology diagram below it visualises the selected scope.

```{figure} _static/imgs/adf4030systemdesigner_topology.png
:alt: ADF4030 Unit Board topology with FPGA, Aion, and Apollo hierarchy
:width: 100%

The focused topology view makes the Unit Board, FPGA, Aion, and Apollo
hierarchy—and the clock-distribution connections between them—visible without
leaving the sizing workflow.
```

### Example Workflow

```python
# Example: 32 Apollo devices, 8 per board, 1 FPGA per board, tree topology
#
# Inputs in the page:
#   N = 32
#   N_Apollo = 8
#   N_FPGA = 1
#   Architecture = tree
#   N_branch = 2
#   Diagram scope = ub
#
# Result:
#   N_Aion_UB = 2 (each board needs 2 Aions: 1 root + 1 leaf)
#   N_UB = 4 (4 boards needed for 32 Apollos)
#   ...plus the topology SVG below the summary.
```

---

## Basic JESD204 Calculator

The Basic JESD204 Calculator provides a quick link-budget check without loading
a converter model or running the constraint solver. Enter the lane count (`L`),
converter count (`M`), bits per sample (`Np`), and JESD204 class, then calculate
from either a sample rate or a lane rate.

### Features

- **Bidirectional rate calculation**: derive lane rate from sample rate, or
  sample rate from lane rate
- **JESD204B/C overhead**: applies the appropriate 8b/10b or 64b/66b encoding
  factor
- **Core clock estimate**: reports the link-layer core clock alongside the
  derived rate
- **No solver required**: useful for fast feasibility checks and transceiver
  budgeting

```{figure} _static/imgs/jesdbasiccalculator.png
:alt: Basic JESD204 Calculator showing link inputs and derived lane and core clock rates
:width: 100%

Inputs and derived parameters share one compact view, making the calculator a
quick companion to the Mode Selector and System Configurator.
```

### Example Workflow

1. Set `L=4`, `M=4`, and `Np=16`.
2. Select **JESD204B** and **Sample Rate** as the reference source.
3. Enter the converter sample rate.
4. Read the resulting lane rate and core clock from **Derived parameters**.

---

(frequency-planner)=
## Frequency Planner

The Frequency Planner shows what each stage of a converter's digital
down-conversion (Rx) or up-conversion (Tx) chain does to your signals. Place
signals by RF centre frequency and bandwidth, set the NCOs and decimation or
interpolation, and the page draws the spectrum after every stage with a quick
verdict under each output. Today it supports the **AD9084**; parts are handled
through an adapter layer, so AD9081 and AD9088 can be added later without
changing the maths. The calculation lives in the `adijif.freqplan` package and
uses no solver.

### Features

- **Rx and Tx tabs**: Rx runs ADC, CDDC, then FDDC. Tx runs FDUC, CDUC, then
  DAC.
- **Per-stage spectrum charts**: one chart per stage and channel, with each
  signal in its own colour and images and aliases marked.
- **Verdict per output**: how much of each target signal is captured, what
  unwanted energy lands in band, and how much of the output bandwidth is used.
- **Tx DAC routing table**: lists which CDUCs feed each DAC.
- **Export, Load, and Reset**: save the plan and view as JSON, restore it
  later, or return to the defaults.

### The brick-wall model

The planner uses an ideal filter at every decimating or interpolating stage.
One global value, **alpha** (default 0.8, adjustable from 0.5 to 0.95), is the
usable fraction of a Nyquist band. Which band depends on the direction:

- **DDC (decimation) stages** use the output rate `fs_out`: the passband edge
  is `p = alpha * fs_out / 2` and the stopband starts at `s = fs_out - p`.
- **DUC (interpolation) stages** use the input rate `fs_in`: the passband edge
  is `p = alpha * fs_in / 2` and the stopband starts at `s = fs_in - p`.
  Images beyond `s` are rejected.

In both cases the stage passes frequencies from `-p` to `+p`. Anything between
`p` and `s` is in the transition band: its energy is drawn attenuated (faded)
and counts as only a partial problem in the verdict. Anything beyond the
stopband is removed. The DAC row shows the plain range `[0, fs/2]` and does
not use alpha.

The same alpha applies to Rx and Tx.

### Usage

#### 1. Pick the part and alpha

Choose the part and set the alpha slider at the top of the page.

#### 2. Enter the signals

On each tab, set the converter rate in MHz and add one row per signal in the
signals table with a name, centre frequency (MHz), bandwidth (MHz), and a
source. On Rx the source is the 0-indexed ADC the signal arrives on. On Tx the
signal centre is a baseband offset at the FDUC input, and the source is the
0-indexed FDUC that carries it. A bandwidth of 0 describes a CW tone.

#### 3. Set the stage tables

NCO frequencies are entered in MHz. The conventions differ by stage:

- **CDDC (Rx)**: enter the *absolute RF frequency* to bring to DC. The page
  folds it into the first Nyquist zone `[0, fs/2]` and records the Nyquist
  zone when you export. RF frequencies must be zero or greater.
- **FDDC (Rx)**: enter the NCO *relative to its CDDC output*, so 0 means the
  centre of the CDDC output. The FDDC source column is the 1-indexed CDDC
  number that feeds it.
- **FDUC (Tx)**: the NCO moves DC to `+f`. It is applied after FDUC
  interpolation, so it offsets the signal at the CDUC input rate. The
  source column is the 1-indexed CDUC number it feeds.
- **CDUC (Tx)**: the NCO is entered in *DAC output terms*, the frequency at
  the DAC that the CDUC input's DC maps to. It moves DC to `+f`.
- **Targets**: a comma-separated list of the signal names an output should
  capture. Leave it empty to use every signal that lands there.

The CDDC table also sets the ADC feeding each CDDC. The **DAC routing** table
lists, for each DAC, the 1-indexed CDUC numbers that are summed into it.
Entries that are not numbers, or are outside the valid CDUC range, are
ignored with a note.

#### 4. Read the spectra and verdicts

The right-hand side shows the stages from top to bottom. Use these controls to
declutter the view:

- **Stages** and **Channels** pills hide or show stage kinds and individual
  channels.
- **Passband edges** toggles the passband markers.
- **Guard bands** toggles the shaded transition and guard regions.

Each output has a one-line verdict:

- ✓ **ok**: every target is fully captured and there is no unwanted energy in
  band.
- ⚠ **warn**: a target is only partly captured, or the only interference is
  attenuated (in a transition band).
- ✗ **error**: an unattenuated interferer or image sits in the usable band, or
  the stage itself reported an error.

When an output uses half or less of its bandwidth, the message adds **could
decimate further**: a lower output rate would still hold your targets. On the
Tx side, the DAC output is checked for collisions between different signals and
images within `[0, fs/2]`.

#### 5. Export, load, and reset

**Export config** downloads `freqplan.json` containing the plan and the current
view. **Load config** accepts such a file and rebuilds both tabs from it; a file
with the wrong version, an unsupported part, wrong list lengths, or values
outside the widget limits is rejected with an error and the current plan is
left alone. **Reset to defaults** restores the starting plan.

### Config file format

The file is plain JSON. All frequencies are in Hz. The sketch below shows the
structure; the `rx` and `tx` sections are each optional (a file may hold only
one), and lists are shown shortened.

```json
{
  "version": 1,
  "part": "AD9084",
  "alpha": 0.8,
  "rx": {
    "adc_rate_hz": 20000000000.0,
    "signals": [
      {"name": "A", "center_hz": 2400000000.0,
       "bandwidth_hz": 100000000.0, "source": 0}
    ],
    "adc_to_cddc": [0, 1, 2, 3],
    "cddc_rf_hz": [2400000000.0, 0.0, 0.0, 0.0],
    "targets": {"cddc0": ["A"]},
    "datapath": {
      "cddc": {
        "enabled": [true, true, true, true],
        "decimations": [4, 1, 1, 1],
        "nco_frequencies": [2400000000.0, 0, 0, 0],
        "nyquist_zones": [1, 1, 1, 1],
        "nco_phases": [0, 0, 0, 0]
      },
      "fddc": {
        "enabled": [false, "..."],
        "decimations": [1, "..."],
        "nco_frequencies": [0, "..."],
        "nco_phases": [0, "..."],
        "source": [1, 1, 2, 2, 3, 3, 4, 4]
      }
    }
  },
  "tx": {
    "dac_rate_hz": 20000000000.0,
    "signals": [
      {"name": "A", "center_hz": 0.0,
       "bandwidth_hz": 100000000.0, "source": 0}
    ],
    "cduc_dac_hz": [3000000000.0, 0.0, 6000000000.0, 0.0],
    "datapath": {
      "cduc": {
        "enabled": [true, true, true, true],
        "interpolation": 1,
        "nco_frequencies": [3000000000.0, 0, 6000000000.0, 0],
        "nco_phases": [0, 0, 0, 0],
        "sources": [[1], [1], [3], [3]]
      },
      "fduc": {
        "enabled": [false, "..."],
        "interpolation": 1,
        "nco_frequencies": [0, "..."],
        "nco_phases": [0, "..."],
        "sources": [1, 1, 2, 2, 3, 3, 4, 4]
      }
    }
  },
  "view": {
    "rx": {"hidden_kinds": [], "hidden_channels": [],
           "show_passband": true, "show_alias": true},
    "tx": {"hidden_kinds": [], "hidden_channels": [],
           "show_passband": true, "show_alias": true}
  }
}
```

Notes on the fields:

- `version` must equal `1`; any other value is rejected on load.
- `alpha` defaults to 0.8 if missing. `part` must be a supported part.
- `rx.cddc_rf_hz` holds the absolute RF centre of each CDDC. The matching
  `datapath.cddc.nco_frequencies` are those values folded into `[0, fs/2]`, and
  `datapath.cddc.nyquist_zones` records the zone each came from. On load the
  RF values are the source of truth.
- `rx.targets` maps a stage name (`cddc0`, `fddc1`, and so on) to the signal
  names it should capture.
- `tx.cduc_dac_hz` holds the DAC-side CDUC NCOs as entered, and
  `datapath.cduc.nco_frequencies` the same values wrapped into the DAC's
  Nyquist range.
- `datapath.cduc.sources` is the DAC routing (one list of 1-indexed CDUC
  numbers per DAC). `datapath.fduc.sources` gives the 1-indexed CDUC each FDUC
  feeds.
- Every per-stage list must have exactly the length the part expects
  (for AD9084: 4 CDDCs, 8 FDDCs, 4 CDUCs, 8 FDUCs); a mismatch is an error.
- `view` stores the UI toggles per tab and may be empty.

### Example Workflow

1. Select **AD9084** and leave alpha at 0.8.
2. On the **Rx** tab, set the ADC rate and add a signal, for example `A` at
   2400 MHz with 100 MHz bandwidth on ADC 0.
3. In the CDDC table, set the RF NCO of `cddc0` to 2400 MHz, choose a
   decimation, and set its targets to `A`.
4. Read the verdict under the `cddc0` output. If it reports a partial capture,
   lower the decimation; if it says **could decimate further**, raise it.
5. Enable an FDDC fed by `cddc0` to split off a narrower channel, with its NCO
   relative to the CDDC output.
6. Switch to the **Tx** tab and set the CDUC DAC-side NCO and the DAC routing
   to place the signal in the output spectrum, checking that no signals or
   images collide.
7. Click **Export config** to save the plan, and **Load config** to restore it
   later.

### Out of Scope

The planner is a quick sanity check, not a signal-integrity simulator. It does
not model:

- real filter shapes, ripple, or rejection (filters are ideal brick walls);
- NCO or ADC spurs, harmonics, or noise;
- the DAC sinc roll-off.

It also does not generate pyadi-iio scripts (planned for later) or JESD
profiles and device-tree fragments.

---

## Tips and Best Practices

### Performance Optimization

1. **Start Simple**: Begin with basic configurations before adding complexity
2. **Use Filters**: Narrow down modes early to reduce computation
3. **Valid Modes Toggle**: Hide invalid modes to focus on viable options

### Common Workflows

#### Finding Compatible Modes

1. Set your sample rate requirement
2. Filter by available lane count
3. Review lane rates against FPGA capabilities
4. Select mode with margin for PVT variation

#### Clock System Design

1. Identify all required clocks (ADC, FPGA ref, SYSREF, etc.)
2. Start with reference clock you have available
3. Configure outputs in priority order
4. Verify clock quality (jitter, phase noise)

#### System Integration

1. Use System Configurator for initial feasibility
2. Switch to individual tools for fine-tuning
3. Validate with hardware using exported configurations

### Troubleshooting

**No valid modes found:**
- Relax filter constraints
- Check sample rate is within device limits
- Verify decimation/interpolation settings

**Clock configuration fails:**
- Check if output frequencies are achievable with selected reference
- Verify VCO frequency ranges
- Try different internal divider settings

**System solve fails:**
- Ensure all components are compatible
- Check FPGA transceiver supports required lane rates
- Verify reference clock is appropriate for FPGA

---

## API Access

While the JIF Tools Explorer provides a graphical interface, all functionality is also available through the pyadi-jif Python API for scripting and automation:

```python
import adijif

# Example: Programmatic JESD mode search
converter = adijif.AD9680()
converter.sample_clock = 1e9
converter.decimation = 1

# Get valid modes
modes = converter.quick_configuration_modes

# Or use the mode selector
from adijif.utils import get_jesd_mode_from_params
found_modes = get_jesd_mode_from_params(
    converter,
    L=4,
    M=2,
    jesd_class="jesd204b"
)
```

For more details on the Python API, see the [API Documentation](converters.md).

## Technical Details

### Architecture

The JIF Tools Explorer is built using:
- **Streamlit**: Web application framework
- **pyadi-jif**: Core JESD204 configuration library
- **docplex**: Constraint solver (CPLEX)
- **D2**: Diagram generation

### State Management

The application uses Streamlit's session state to maintain:
- Part selections across tool switches
- Configuration values
- Generated diagrams (cached for performance)

### Performance Considerations

- Diagram generation is cached per part
- Mode searching is optimized with early filtering
- Solver constraints are pre-validated

---

## Contributing

To contribute to JIF Tools Explorer:

1. See [Developer Documentation](developers.md)
2. Test changes with: `streamlit run adijif/tools/explorer/main.py`
3. Add tests in `tests/tools/`
4. Update documentation as needed

## Support

For issues or questions:
- GitHub Issues: https://github.com/analogdevicesinc/pyadi-jif/issues
- Documentation: https://analogdevicesinc.github.io/pyadi-jif/
- ADI Support: https://ez.analog.com/

---

## See Also

- [Installation Guide](install.md)
- [Converter Documentation](converters.md)
- [Clocking Documentation](clocking/index.md)
- [FPGA Integration](fpgas/index)
- [Drawing Utilities](draw.md)
