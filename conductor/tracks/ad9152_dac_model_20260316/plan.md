# Track Implementation Plan: Add AD9152 DAC model

## Phase 1: Core AD9152 Model and Datapath

- [x] Task: Implement AD9152 datapath model (`ad9152_dp`) [3564b46]
    - [x] Write failing tests for AD9152 interpolation and datapath constraints
    - [x] Implement `ad9152_dp` in `adijif/converters/ad9152_dp.py`
    - [x] Verify tests pass
- [~] Task: Implement AD9152 converter model
    - [ ] Write failing tests for AD9152 clocking and JESD204B mode selection
    - [ ] Implement `ad9152` class in `adijif/converters/ad9152.py`
    - [ ] Verify tests pass
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Core Model' (Protocol in workflow.md)

## Phase 2: Validation and System Integration

- [ ] Task: Implement AD9152 validation rules
    - [ ] Write failing tests for AD9152 specific hardware constraints in validation engine
    - [ ] Implement `AD9152Rules` in `adijif/validation/converters.py`
    - [ ] Verify tests pass
- [ ] Task: Integrate AD9152 into FMCDAQ3 system configurations
    - [ ] Write failing tests for FMCDAQ3 system with AD9152
    - [ ] Update system configuration logic to support AD9152 + AD9680
    - [ ] Verify tests pass
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Validation & System' (Protocol in workflow.md)

## Phase 3: UI Integration and Examples

- [ ] Task: Add AD9152 to JIF Tools Explorer (Streamlit)
    - [ ] Update Streamlit UI to include AD9152 in the converter selection
    - [ ] Manually verify UI functionality
- [ ] Task: Create FMCDAQ3 example script with AD9152
    - [ ] Implement an example script demonstrating AD9152 configuration
    - [ ] Verify example runs correctly
- [ ] Task: Conductor - User Manual Verification 'Phase 3: UI & Examples' (Protocol in workflow.md)
