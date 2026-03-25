# flake8: noqa
"""MCP server exposing pyadi-jif component configuration and system solving tools."""

import importlib
import inspect
import json
import os
from pathlib import Path
from typing import Any, Dict, Type

import click
from fastmcp import FastMCP

import adijif.clocks
import adijif.converters
import adijif.fpgas
import adijif.plls
import adijif.types
from adijif.board_references import get_common_vcxo_references
from adijif.clocks.clock import clock as BaseClock
from adijif.converters.converter import converter as BaseConverter
from adijif.fpgas.fpga import fpga as BaseFPGA
from adijif.plls.pll import BasePLL
from adijif.system import system as _system
from adijif.utils import get_jesd_mode_from_params

_converter_registry: Dict[str, Type[BaseConverter]] = {}
_clock_registry: Dict[str, Type[BaseClock]] = {}
_fpga_registry: Dict[str, Type[BaseFPGA]] = {}
_pll_registry: Dict[str, Type[BasePLL]] = {}
_all_registries_populated = False
_PROFILE_QUICK_KEYS = {"F", "HD", "K", "L", "M", "N", "Np", "S", "CS"}
_PROFILE_META_KEYS = {"bypass_version_check", "jesd_class", "mode", "path", "target"}


def _populate_registry(registry: Dict, base_class: Type, package: Any):
    """Dynamically populate a component registry."""
    package_path = Path(package.__file__).parent
    for file_path in package_path.glob("**/*.py"):
        relative_path = file_path.relative_to(package_path)

        if file_path.name == "__init__.py":
            # Include subpackage __init__.py (e.g. fpgas/xilinx/__init__.py)
            # but skip the top-level package __init__.py itself.
            parent_parts = relative_path.parent.parts
            if not parent_parts:
                continue
            module_name = ".".join(parent_parts)
        elif file_path.name.startswith("__"):
            continue
        else:
            module_name = ".".join(relative_path.with_suffix("").parts)

        module_path_str = f"{package.__name__}.{module_name}"

        try:
            module = importlib.import_module(module_path_str)
            for name, obj in inspect.getmembers(module):
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, base_class)
                    and obj is not base_class
                    and not inspect.isabstract(obj)
                ):
                    # Use the uppercase class name as the key
                    registry[obj.__name__.upper()] = obj
        except (ImportError, TypeError, AttributeError, ValueError):
            # Silently ignore errors, as some files might not be importable
            # or contain abstract base classes that fail on instantiation.
            pass


def _populate_all_registries():
    """Populate all component registries if not already populated."""
    global _all_registries_populated
    if _all_registries_populated:
        return

    _populate_registry(_converter_registry, BaseConverter, adijif.converters)
    _populate_registry(_clock_registry, BaseClock, adijif.clocks)
    _populate_registry(_fpga_registry, BaseFPGA, adijif.fpgas)
    _populate_registry(_pll_registry, BasePLL, adijif.plls)

    _all_registries_populated = True


def _parse_vcxo(vcxo_config: Dict[str, Any]) -> Any:
    """Helper to parse vcxo configuration from JSON into adijif.types objects."""
    vcxo_type = vcxo_config.get("type")
    value = vcxo_config.get("value")

    if vcxo_type == "range":
        start = vcxo_config.get("start")
        stop = vcxo_config.get("stop")
        step = vcxo_config.get("step")
        if start is None or stop is None or step is None:
            raise ValueError(
                "vcxo of type 'range' requires 'start', 'stop', and 'step'."
            )
        return adijif.types.range(start, stop, step)
    elif vcxo_type == "arb_source":
        # arb_source takes frequency and count as args
        frequency = vcxo_config.get("frequency")
        count = vcxo_config.get("count")
        if frequency is None or count is None:
            raise ValueError(
                "vcxo of type 'arb_source' requires 'frequency' and 'count'."
            )
        return adijif.types.arb_source(frequency, count)
    else:
        # Default to raw value (int/float)
        return value


def _apply_config_recursively(obj: Any, config: Dict[str, Any]):
    """Recursively apply configuration to an object's attributes."""
    for key, value in config.items():
        if isinstance(value, dict):
            # If the attribute exists and is an object, recurse
            if hasattr(obj, key) and isinstance(getattr(obj, key), object):
                _apply_config_recursively(getattr(obj, key), value)
            else:
                # If it's a dict but not an object, set directly (e.g., config for a property)
                setattr(obj, key, value)
        else:
            setattr(obj, key, value)


def _load_profile_file(profile_path: str) -> Dict[str, Any]:
    """Load a converter profile payload from disk.

    Args:
        profile_path: Path to the profile JSON file.

    Returns:
        Dict containing JSON payload.
    """
    path = Path(profile_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Profile file does not exist: {profile_path}")

    with open(path, "r", encoding="utf-8") as profile_file:
        payload = json.load(profile_file)

    if not isinstance(payload, dict):
        raise ValueError(f"Profile file '{profile_path}' must contain a JSON object.")
    return payload


def _apply_profile_entries(
    converter: BaseConverter,
    profile: Any,
) -> None:
    """Apply a profile definition to an instantiated converter."""
    if isinstance(profile, str):
        profile_data: Dict[str, Any] = {"path": profile}
    elif isinstance(profile, dict):
        profile_data = dict(profile)
    else:
        raise ValueError(f"Profile payload must be a path string or JSON object.")

    profile_path = profile_data.pop("path", None)
    bypass_version_check = bool(profile_data.pop("bypass_version_check", False))

    if profile_path:
        if hasattr(converter, "apply_profile_settings"):
            converter.apply_profile_settings(  # type: ignore[attr-defined]
                profile_path, bypass_version_check
            )
            if not profile_data:
                return
        else:
            file_payload = _load_profile_file(profile_path)
            profile_data = {**file_payload, **profile_data}

    if "mode" in profile_data:
        converter.set_quick_configuration_mode(
            profile_data.pop("mode"), profile_data.pop("jesd_class", "jesd204b")
        )
    elif any(key in _PROFILE_QUICK_KEYS for key in profile_data):
        jesd_class = profile_data.pop("jesd_class", "jesd204b")
        mode_kwargs = {
            key: profile_data[key] for key in _PROFILE_QUICK_KEYS if key in profile_data
        }
        mode_candidates = get_jesd_mode_from_params(
            converter,
            jesd_class=jesd_class,
            **mode_kwargs,
        )
        if not mode_candidates:
            raise ValueError(
                f"Unable to infer JESD mode from profile for {converter.name}"
            )
        converter.set_quick_configuration_mode(
            mode_candidates[0]["mode"], mode_candidates[0]["jesd_class"]
        )

        for key in mode_kwargs:
            profile_data.pop(key, None)

    for key in _PROFILE_META_KEYS:
        profile_data.pop(key, None)

    if profile_data:
        _apply_config_recursively(converter, profile_data)


def _apply_converter_profile(converter: BaseConverter, converter_profile: Any) -> None:
    """Apply profile configuration to converter(s), including nested converters."""
    if converter_profile is None:
        return

    if getattr(converter, "_nested", None) and isinstance(converter_profile, dict):
        nested_applied = False
        for side in ["adc", "dac"]:
            if side in converter_profile:
                side_payload = converter_profile[side]
                _apply_profile_entries(getattr(converter, side), side_payload)
                nested_applied = True

        if nested_applied:
            return

        _apply_profile_entries(converter.adc, converter_profile)
        _apply_profile_entries(converter.dac, converter_profile)
        return

    if getattr(converter, "_nested", None) and not isinstance(converter_profile, dict):
        if isinstance(converter_profile, str):
            converter_profile = _load_profile_file(converter_profile)
        _apply_profile_entries(converter.adc, converter_profile)
        _apply_profile_entries(converter.dac, converter_profile)
        return

    _apply_profile_entries(converter, converter_profile)


def create_mcp_server() -> FastMCP:
    """Creates and configures the FastMCP server instance with all tools."""
    mcp_instance = FastMCP(name="pyadi-jif MCP Server")

    @mcp_instance.tool
    def list_components(
        component_type: str,
    ) -> Dict[str, Any]:
        """
        Lists all available components of a given type.

        Args:
            component_type: The type of component ('converter', 'clock', 'pll', or 'fpga').

        Returns:
            A dictionary containing a list of available component names.
        """
        _populate_all_registries()

        registry = None
        if component_type.lower() == "converter":
            registry = _converter_registry
        elif component_type.lower() == "clock":
            registry = _clock_registry
        elif component_type.lower() == "pll":
            registry = _pll_registry
        elif component_type.lower() == "fpga":
            registry = _fpga_registry
        else:
            return {
                "error": f"Invalid component_type '{component_type}'. "
                "Must be 'converter', 'clock', 'pll', or 'fpga'."
            }

        return {"components": list(registry.keys())}

    @mcp_instance.tool
    def get_vcxo_references(
        converter: str = "",
        clock_chip: str = "",
        board: str = "",
        pll: str = "",
    ) -> Dict[str, Any]:
        """
        Return common VCXO reference presets for known converter/clock board combinations.

        Args:
            converter: Optional converter name (e.g. "ad9084_rx").
            clock_chip: Optional clock chip name (e.g. "ltc6952").
            board: Optional board/platform name (e.g. "Triton (Quad-Apollo)").
            pll: Optional PLL name (e.g. "adf4382").

        Returns:
            Matching list of VCXO reference presets.
        """
        refs = get_common_vcxo_references(
            converter=converter or None,
            clock_chip=clock_chip or None,
            board=board or None,
            pll=pll or None,
        )

        return {"vcxo_references": refs}

    @mcp_instance.tool
    def query_jesd_modes(
        component_name: str,
        jesd_params_json: str = "{}",
    ) -> Dict[str, Any]:
        """
        Queries the available JESD modes for a given component based on provided parameters.

        Args:
            component_name: The name of the component (e.g., 'AD9081_RX', 'ADRV9009_TX').
            jesd_params_json: A JSON string representing keyword arguments for JESD parameters
                              (e.g., '{"M": 4, "L": 8, "K": 32}').

        Returns:
            A dictionary containing information about the available JESD modes.
        """
        _populate_all_registries()

        if component_name.upper() not in _converter_registry:
            return {
                "error": f"Component '{component_name}' not found in registry. "
                f"Available components: {list(_converter_registry.keys())}"
            }

        ConverterClass = _converter_registry[component_name.upper()]

        try:
            jesd_params = json.loads(jesd_params_json)
            converter_instance = ConverterClass(model=None, solver="CPLEX")

            found_modes = get_jesd_mode_from_params(converter_instance, **jesd_params)

            return {
                "component": component_name,
                "jesd_modes": found_modes,
                "query_params": jesd_params,
            }
        except json.JSONDecodeError as e:
            return {
                "error": f"Invalid JSON string for jesd_params_json: {str(e)}",
                "jesd_params_json": jesd_params_json,
            }
        except Exception as e:
            return {
                "error": f"Failed to query JESD modes for '{component_name}': {str(e)}",
                "component": component_name,
                "query_params": jesd_params,
            }

    @mcp_instance.tool
    def get_component_info(
        component_type: str,
        component_name: str,
    ) -> Dict[str, Any]:
        """
        Retrieves detailed information about a specific component (converter, clock, PLL, or FPGA).

        Args:
            component_type: The type of component ('converter', 'clock', 'pll', or 'fpga').
            component_name: The name of the component (e.g., 'AD9081_RX', 'HMC7044', 'XILINX').

        Returns:
            A dictionary containing information about the component, including its docstring,
            constructor signature, and public properties.
        """
        _populate_all_registries()

        registry = None
        if component_type.lower() == "converter":
            registry = _converter_registry
        elif component_type.lower() == "clock":
            registry = _clock_registry
        elif component_type.lower() == "fpga":
            registry = _fpga_registry
        elif component_type.lower() == "pll":
            registry = _pll_registry
        else:
            return {
                "error": f"Invalid component_type '{component_type}'. "
                "Must be 'converter', 'clock', 'pll', or 'fpga'."
            }

        if component_name.upper() not in registry:
            return {
                "error": f"Component '{component_name}' of type '{component_type}' not found. "
                f"Available {component_type}s: {list(registry.keys())}"
            }

        ComponentClass = registry[component_name.upper()]

        info = {
            "name": ComponentClass.__name__,
            "docstring": inspect.getdoc(ComponentClass),
            "constructor_signature": str(inspect.signature(ComponentClass.__init__)),
            "properties": {},
        }

        # Inspect public properties and methods
        for name in dir(ComponentClass):
            if not name.startswith("_"):  # Exclude private/protected members
                member = getattr(ComponentClass, name)
                if isinstance(member, property):
                    info["properties"][name] = {
                        "type": str(member.fget.__annotations__.get("return", "Any")),
                        "docstring": inspect.getdoc(member),
                    }
                elif inspect.isfunction(member) and not name.startswith(
                    "set_"
                ):  # Exclude setters
                    if (
                        inspect.getmodule(member) == ComponentClass.__module__
                    ):  # Only own methods
                        info["properties"][name] = {
                            "type": "method",
                            "signature": str(inspect.signature(member)),
                            "docstring": inspect.getdoc(member),
                        }
        return info

    @mcp_instance.tool
    def solve_system(
        system_config_json: str,
    ) -> Dict[str, Any]:
        """
        Performs system-level solving based on the provided JSON configuration.

        The system_config_json should be a JSON string with the following structure:
        {
            "conv": "AD9084_RX",          // Converter name (use list_components to see options)
            "clk": "HMC7044",             // Clock chip name
            "fpga": "XILINX",             // FPGA name
            "vcxo": {                      // VCXO configuration
                "type": "fixed",           //   "fixed", "range", or "arb_source"
                "value": 125000000         //   frequency in Hz
            },
            "solver": "CPLEX",             // "CPLEX" (default) or "gekko"
            "converter_profile": "/path/to/profile.json",  // Profile file path (sets JESD mode, clocking)
            "converter_properties": {      // Additional converter settings
                "clocking_option": "direct"  // "direct", "integrated_pll", or "external"
            },
            "clock_properties": {},        // Additional clock chip settings
            "fpga_properties": {           // FPGA settings — IMPORTANT: ref_clock bounds required
                "dev_kit": "vcu118",       //   Auto-configure for known board (zc706, zcu102, vcu118, vck190, etc.)
                "ref_clock_min": 60000000, //   OR set manually: min ref clock in Hz
                "ref_clock_max": 820000000,//   max ref clock in Hz
                "out_clk_select": "XCVR_REFCLK"
            },
            "pll_configurations": [        // External PLLs
                {
                    "type": "inline",      //   "inline" (between clock and converter) or "sysref"
                    "name": "ADF4382",     //   PLL name (use list_components to see options)
                    "vcxo": { "type": "fixed", "value": 125000000 },
                    "target_component": "converter",  // "converter", "clock", or "fpga"
                    "pll_properties": {}
                }
            ],
            "constraints": {}
        }

        IMPORTANT NOTES:
        - fpga_properties MUST include either "dev_kit" (e.g. "vcu118") or both
          "ref_clock_min" and "ref_clock_max", otherwise the solver will fail.
        - When using a converter_profile file, it sets sample_clock and JESD parameters
          automatically. Do NOT also set sample_clock in converter_properties.
        - AD9084 converters only support clocking_option="direct" and require an inline PLL
          (e.g. ADF4382) targeting the converter.
        - For "vcxo", "type" can be "fixed" (value: int/float), "range" (start, stop, step),
          or "arb_source" (frequency, count).

        Args:
            system_config_json: A JSON string containing the system configuration.

        Returns:
            A dictionary with keys "config", "solution", "status" on success,
            or "error" on failure. Save the full result under the "jif_output"
            key in pipeline_config.json.
        """
        _populate_all_registries()
        import os

        log_folder = Path("/tmp/mcp_logs")
        if os.path.exists(log_folder):
            os.system(f"rm -rf {log_folder}")
        log_folder.mkdir(parents=True, exist_ok=True)
        json_file_count = len(
            [f for f in os.listdir(log_folder) if f.endswith(".json")]
        )

        log_filename = log_folder / f"solve_system_{json_file_count + 1}.json"
        with open(log_filename, "wb") as f:
            # Write dict with indentation for readability
            f.write(
                json.dumps({"input_config": system_config_json}, indent=4).encode(
                    "utf-8"
                )
            )

        try:
            system_config = json.loads(system_config_json)

            conv_name = system_config.get("conv")
            clk_name = system_config.get("clk")
            fpga_name = system_config.get("fpga")
            vcxo_config = system_config.get(
                "vcxo", {"type": "fixed", "value": 100000000}
            )  # Default to 100MHz fixed
            solver = system_config.get("solver", "CPLEX")
            pll_configurations = system_config.get("pll_configurations", [])
            constraints = system_config.get("constraints", {})
            converter_profile = system_config.get("converter_profile")

            if not conv_name or not clk_name or not fpga_name:
                raise ValueError(
                    "System configuration must specify 'conv', 'clk', and 'fpga'."
                )

            # Resolve component classes from registries
            # Use the simple component names (e.g., "AD9081_RX") which adijif.system.system expects as top-level aliases
            if conv_name.upper() not in _converter_registry:
                raise ValueError(f"Converter '{conv_name}' not found in registry.")
            if clk_name.upper() not in _clock_registry:
                raise ValueError(f"Clock '{clk_name}' not found in registry.")
            if fpga_name.upper() not in _fpga_registry:
                raise ValueError(f"FPGA '{fpga_name}' not found in registry.")

            # Instantiate system using simple component names (top-level aliases)
            vcxo_parsed = _parse_vcxo(vcxo_config)
            sys_instance = _system(
                conv=conv_name,  # Pass the simple name, which is now a top-level alias
                clk=clk_name,  # Pass the simple name
                fpga=fpga_name,  # Pass the simple name
                vcxo=vcxo_parsed,
                solver=solver,
            )

            if converter_profile is not None:
                _apply_converter_profile(sys_instance.converter, converter_profile)

            # Apply properties to components
            converter_properties = system_config.get("converter_properties", {})
            _apply_config_recursively(sys_instance.converter, converter_properties)

            clock_properties = system_config.get("clock_properties", {})
            _apply_config_recursively(sys_instance.clock, clock_properties)

            fpga_properties = dict(system_config.get("fpga_properties", {}))

            # Support "dev_kit" shorthand to auto-configure FPGA board settings
            # (ref_clock_min/max, transceiver_type, speed_grade, etc.)
            dev_kit = fpga_properties.pop("dev_kit", None)
            if dev_kit and hasattr(sys_instance.fpga, "setup_by_dev_kit_name"):
                sys_instance.fpga.setup_by_dev_kit_name(dev_kit)

            _apply_config_recursively(sys_instance.fpga, fpga_properties)

            # Pre-flight: check that FPGA ref clock bounds are configured
            fpga = sys_instance.fpga
            if hasattr(fpga, "ref_clock_min") and hasattr(fpga, "ref_clock_max"):
                if fpga.ref_clock_min == -1 or fpga.ref_clock_max == -1:
                    raise ValueError(
                        "FPGA ref_clock_min and ref_clock_max are not set. "
                        "Either include 'dev_kit' (e.g. 'vcu118') in fpga_properties "
                        "to auto-configure, or set 'ref_clock_min' and 'ref_clock_max' "
                        "explicitly in fpga_properties."
                    )

            # Handle PLL configurations
            for pll_cfg in pll_configurations:
                pll_type = pll_cfg.get("type")
                pll_name = pll_cfg.get("name")
                pll_vcxo_config = pll_cfg.get("vcxo")
                pll_vcxo_parsed = _parse_vcxo(pll_vcxo_config)
                pll_properties = pll_cfg.get("pll_properties", {})
                target_component_str = pll_cfg.get("target_component")

                if pll_type == "inline":
                    if pll_name.upper() not in _pll_registry:
                        raise ValueError(f"PLL '{pll_name}' not found in pll registry.")

                    target_component = None
                    if target_component_str == "converter":
                        target_component = sys_instance.converter
                    elif target_component_str == "clock":
                        target_component = sys_instance.clock
                    elif target_component_str == "fpga":
                        target_component = sys_instance.fpga
                    else:
                        raise ValueError(
                            f"Invalid target_component for inline PLL: {target_component_str}"
                        )

                    # Add inline PLL
                    sys_instance.add_pll_inline(
                        pll_name, pll_vcxo_parsed, target_component
                    )  # Pass simple name
                    # Apply properties to the newly added PLL
                    _apply_config_recursively(sys_instance.plls[-1], pll_properties)

                elif pll_type == "sysref":
                    if pll_name.upper() not in _pll_registry:
                        raise ValueError(
                            f"PLL '{pll_name}' not found in pll registry for sysref."
                        )

                    sys_instance.add_pll_sysref(
                        pll_name, pll_vcxo_parsed, sys_instance.clock
                    )  # Pass simple name
                    # Apply properties to the newly added PLL
                    _apply_config_recursively(sys_instance.plls[-1], pll_properties)
                else:
                    raise ValueError(f"Unsupported PLL configuration type: {pll_type}")

            # Solve the system
            solution = sys_instance.solve(out_clock_constraints=constraints)

            return {
                "config": system_config,
                "solution": solution,
                "status": "solved",
            }

        except json.JSONDecodeError as e:
            return {
                "error": f"Invalid JSON string for system_config_json: {str(e)}",
                "system_config_json": system_config_json,
            }
        except ValueError as e:
            return {
                "error": f"Configuration error: {str(e)}",
                "system_config_json": system_config_json,
            }
        except Exception as e:
            # Catch any other unexpected errors during solving
            return {
                "error": f"An unexpected error occurred during system solving: {str(e)}",
                "system_config_json": system_config_json,
            }

    return mcp_instance


@click.command()
@click.option(
    "--transport",
    default="stdio",
    help="The transport to use for the MCP server (e.g., 'stdio', 'http').",
)
@click.option(
    "--port",
    type=int,
    default=5000,
    help="The port to use if the transport is 'http'.",
)
def main(transport: str, port: int):
    """
    Starts the pyadi-jif MCP server.
    """
    click.echo(f"Starting pyadi-jif MCP server with transport: {transport}")
    mcp = create_mcp_server()
    if transport == "http":
        click.echo(f"Listening on port: {port}")
        mcp.run(transport=transport, port=port)
    else:
        mcp.run(transport=transport)


if __name__ == "__main__":
    main()
