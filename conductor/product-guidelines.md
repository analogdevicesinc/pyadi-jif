# Product Guidelines

## Prose Style
- **Clarity Above All:** Use clear, unambiguous technical language.
- **Consistency:** Maintain consistent terminology for hardware components (e.g., "Converters," "Clocks," "FPGA") across all documentation.
- **Directness:** Use active voice and avoid overly complex sentence structures.
- **Documentation:** Every public function and class MUST have a clear docstring in Google style.

## Branding and Visuals
- **Official Naming:** The project name is `pyadi-jif`. Always use the lower-case naming for the package.
- **ADI Alignment:** Visuals and documentation should align with Analog Devices, Inc. branding where appropriate.
- **Diagrams:** Use diagrams to explain complex clock trees or JESD204 link configurations.

## User Experience (UX) Principles
- **Interactive Feedback:** Tools like `jiftools` should provide immediate feedback to user inputs.
- **Error Handling:** Provide clear, actionable error messages for invalid configurations.
- **Sensible Defaults:** Provide default configurations for common ADI evaluation boards to lower the entry barrier for new users.
- **Performance:** Interactive tools should remain responsive even when running complex solvers.

## Technical Quality
- **Test-Driven:** Maintain high code coverage (target >90%).
- **Type Safety:** Use Python type hints throughout the codebase.
- **Modular Design:** Keep hardware abstractions separate from the UI/explorer logic.
