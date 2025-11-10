# JIF Tools Quick Start Guide

Get started with the JIF Tools Explorer in minutes!

## Installation and Launch

1. **Install pyadi-jif:**
   ```bash
   pip install 'pyadi-jif[cplex,tools]'
   ```

2. **Launch the tools:**
   ```bash
   jiftools
   ```

3. **Access the web interface:**
   The application will open automatically in your browser at `http://localhost:8501`

---

## Quick Example 1: Find JESD Modes for AD9680

**Goal:** Find a 4-lane JESD204B mode for the AD9680 running at 1 GSPS

**Steps:**

1. **Select Tool:** Click "JESD204 Mode Selector" in the sidebar

2. **Select Part:** Choose "ad9680" from the dropdown

3. **Configure Datapath:**
   - Decimation: 1
   - Units: GHz
   - Converter Rate: 1.0

4. **Filter Modes:**
   - In Configuration section, select L → [4]
   - In Configuration section, select jesd_class → ["jesd204b"]

5. **View Results:**
   - Check the JESD204 Modes table
   - Note the lane rate (e.g., 10 Gbps)
   - Export to CSV if needed

**Result:** You'll see valid modes with 4 lanes operating at 1 GSPS, showing parameters like M=2, L=4, F=1, S=1, K=32.

---

## Quick Example 2: Configure HMC7044 for AD9680

**Goal:** Generate clocks for AD9680 and FPGA reference

**Steps:**

1. **Select Tool:** Click "Clock Configurator" in the sidebar

2. **Select Part:** Choose "hmc7044" from the dropdown

3. **Set Reference Clock:**
   - Reference Clock: 125000000 (125 MHz)

4. **Configure Outputs:**
   - Number of Clock Outputs: 2
   - Output Clock 1: 1000000000 (1 GHz for ADC)
   - Output Clock 1 Name: "ADC_CLK"
   - Output Clock 2: 250000000 (250 MHz for FPGA)
   - Output Clock 2 Name: "FPGA_REF"

5. **View Results:**
   - Configuration appears if valid solution found
   - Clock tree diagram shows signal routing
   - Device tree fragment available for Linux

**Result:** Valid HMC7044 configuration with VCO and divider settings.

---

## Quick Example 3: Complete System Configuration

**Goal:** Configure complete AD9680 + HMC7044 + Xilinx ZCU102 system

**Steps:**

1. **Select Tool:** Click "System Configurator" in the sidebar

2. **The tool will automatically:**
   - Set up AD9680 converter
   - Configure HMC7044 clock chip
   - Set Xilinx FPGA parameters
   - Use 125 MHz VCXO reference

3. **Configure Settings:**
   - Converter sample clock: 1e9 (1 GSPS)
   - Decimation: 1
   - Quick config mode: "0x88"
   - K: 32

4. **FPGA Setup:**
   - Dev kit: "zc706"
   - Force QPLL: 1

5. **Solve:**
   - Click solve button
   - View complete system configuration
   - Check system block diagram

**Result:** Complete validated configuration for converter, clock chip, and FPGA transceivers.

---

## Common Tasks

### Export JESD Mode Table
1. Configure filters in JESD Mode Selector
2. View results table
3. Click data editor
4. Use browser to copy/export data

### Save Clock Configuration
1. Generate configuration in Clock Configurator
2. Copy device tree fragment from output
3. Save to file for use with Linux drivers

### Compare Different Parts
1. Select first part and note results
2. Use browser back button or refresh
3. Select different part
4. Compare specifications

---

## Tips for Success

### Start Simple
- Begin with default settings
- Add one filter/constraint at a time
- Verify each step works before proceeding

### Understand Your Requirements
- Know your sample rate target
- Understand FPGA lane rate limits
- Consider available reference clocks

### Use Visual Feedback
- Check derived settings after each change
- Review diagrams to understand signal flow
- Toggle valid/invalid modes to see constraints

### Iterate
- Start with broad filters, then narrow down
- Try multiple configurations
- Compare trade-offs (lanes vs rate)

---

## Troubleshooting Quick Fixes

### "No modes found"
- **Check:** Sample rate within device limits?
- **Try:** Remove some filters
- **Verify:** Decimation/interpolation correct?

### "No valid configuration found" (Clock)
- **Check:** Are output frequencies achievable from reference?
- **Try:** Different reference frequency
- **Verify:** Internal VCO ranges compatible?

### System solve fails
- **Check:** All components compatible?
- **Try:** Different JESD mode or lane count
- **Verify:** FPGA supports required lane rate?

### Application won't start
- **Check:** Python version (3.9+)
- **Try:** Reinstall with `pip install --force-reinstall 'pyadi-jif[cplex]'`
- **Verify:** No other Streamlit apps on port 8501

---

## Next Steps

After completing the quick start:

1. **Read Full Documentation:** [JIF Tools Explorer Guide](tools.md)
2. **Explore Python API:** [Converter API](converters.md)
3. **Learn About JESD204:** [Flow Documentation](flow.md)
4. **Advanced Features:** [Drawing Tools](draw.md)

---

## Getting Help

- **Documentation:** https://analogdevicesinc.github.io/pyadi-jif/
- **GitHub Issues:** https://github.com/analogdevicesinc/pyadi-jif/issues
- **ADI Support:** https://ez.analog.com/
- **Examples:** Check `examples/` directory in repository

---

## Quick Reference

### Supported Converters
- ADCs: AD9680, AD9625, AD9208, etc.
- DACs: AD9144, AD9136, AD9172, etc.
- MxFEs: AD9081, AD9082, AD9084, etc.
- Transceivers: ADRV9009, ADRV9002, etc.

### Supported Clock Chips
- HMC7044 - High-performance jitter attenuator
- AD9545 - Multi-input clock generator
- AD9523-1 - Low jitter clock distribution

### Supported FPGAs
- **Xilinx:** 7-series, UltraScale, UltraScale+
- **Intel (Altera):** Arria, Stratix

### Common Development Kits
- ZC706, ZCU102 (Xilinx)
- Various ADI evaluation boards

---

**Ready to get started? Launch the tools with `jiftools` and try Example 1!**
