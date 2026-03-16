# Track Specification: Add AD9152 DAC model

## 1. Goal
The objective of this track is to implement a comprehensive Python model for the AD9152 High-Speed DAC. This includes clocking logic, JESD204B interface configuration, datapath features, and integration with the existing validation and UI frameworks. The AD9152 is primarily intended for use with the FMCDAQ3 board.

## 2. Requirements
- **Generic DAC and AD9152-specific clocking constraints:** Implement the `ad9152` class, inheriting from `dac` and `converter`.
- **JESD204B Only Support:** Focus on JESD204B modes as required for the AD9152.
- **Datapath Features:** Support for interpolation and other AD9152-specific datapath configurations.
- **Validation Support:** Add validation rules for the AD9152 within the existing JESD204 validation suite.
- **System Integration:** Enable integration with the FMCDAQ3 system configurations.
- **UI Integration:** Add the AD9152 to the JIF Tools Explorer (Streamlit).

## 3. Core Components
- **`ad9152` class:** The primary hardware model for the DAC.
- **`ad9152_dp` class:** The datapath model (interpolation, etc.).
- **`AD9152Rules`:** Validation rules for the converter.

## 4. Acceptance Criteria
- [ ] AD9152 model can correctly solve for valid clocking configurations.
- [ ] JESD204B modes (L, M, F, S, K, etc.) are correctly defined for the part.
- [ ] Unit tests for the AD9152 model cover >90% of the code.
- [ ] Validation rules for AD9152 are implemented and tested.
- [ ] AD9152 is selectable and functional in the Streamlit UI.
- [ ] AD9152 is integrated into an example/system-test for FMCDAQ3.
