# Track Implementation Plan: Add AD9152 DAC model

## Phase 1: Core AD9152 Model and Datapath [checkpoint: 7f4e6fc]

- [x] Task: Implement AD9152 datapath model (`ad9152_dp`) [3564b46]
    - [x] Write failing tests for AD9152 interpolation and datapath constraints
    - [x] Implement `ad9152_dp` in `adijif/converters/ad9152_dp.py`
    - [x] Verify tests pass
- [x] Task: Implement AD9152 converter model [56fe4f7]
    - [x] Write failing tests for AD9152 clocking and JESD204B mode selection
    - [x] Implement `ad9152` class in `adijif/converters/ad9152.py`
    - [x] Verify tests pass
- [x] Task: Conductor - User Manual Verification 'Phase 1: Core Model' (Protocol in workflow.md)

## Phase 2: Validation and System Integration [checkpoint: 0491f9b]

- [x] Task: Implement AD9152 validation rules [7af495f]
    - [x] Write failing tests for AD9152 specific hardware constraints in validation engine
    - [x] Implement `AD9152Rules` in `adijif/validation/converters.py`
    - [x] Verify tests pass
- [x] Task: Integrate AD9152 into FMCDAQ3 system configurations [fabddd7]
    - [x] Write failing tests for FMCDAQ3 system with AD9152
    - [x] Update system configuration logic to support AD9152 + AD9680
    - [x] Verify tests pass
- [x] Task: Conductor - User Manual Verification 'Phase 2: Validation & System' (Protocol in workflow.md)


## Phase 3: UI Integration and Examples [checkpoint: 4573afd]

- [x] Task: Add AD9152 to JIF Tools Explorer (Streamlit) [56fe4f7]
    - [x] Update Streamlit UI to include AD9152 in the converter selection
    - [x] Manually verify UI functionality
- [x] Task: Create FMCDAQ3 example script with AD9152 [5165e7f]
    - [x] Implement an example script demonstrating AD9152 configuration
    - [x] Verify example runs correctly
- [x] Task: Conductor - User Manual Verification 'Phase 3: UI & Examples' (Protocol in workflow.md)
