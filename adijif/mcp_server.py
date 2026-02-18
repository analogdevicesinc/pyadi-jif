import json
import click
from fastmcp import FastMCP
from typing import Dict, Any, Type, List
import inspect
import importlib

from adijif.utils import get_jesd_mode_from_params
from adijif.converters.converter import converter as BaseConverter
import adijif.converters

import adijif.system
import adijif.types
from pathlib import Path

from adijif.clocks.clock import clock as BaseClock
import adijif.clocks
from adijif.fpgas.fpga import fpga as BaseFPGA
import adijif.fpgas


_converter_registry: Dict[str, Type[BaseConverter]] = {}
_clock_registry: Dict[str, Type[BaseClock]] = {}
_fpga_registry: Dict[str, Type[BaseFPGA]] = {}
_all_registries_populated = False

def _populate_registry(registry: Dict, base_class: Type, package: Any):
    """Dynamically populate a component registry."""
    package_path = Path(package.__file__).parent
    for file_path in package_path.glob("**/*.py"):
        if file_path.name.startswith("__"):
            continue

        # Construct module path
        relative_path = file_path.relative_to(package_path)
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
        except (ImportError, TypeError, AttributeError, ValueError) as e:
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
            raise ValueError("vcxo of type 'range' requires 'start', 'stop', and 'step'.")
        return adijif.types.range(start, stop, step)
    elif vcxo_type == "arb_source":
        # arb_source takes frequency and count as args
        frequency = vcxo_config.get("frequency")
        count = vcxo_config.get("count")
        if frequency is None or count is None:
            raise ValueError("vcxo of type 'arb_source' requires 'frequency' and 'count'.")
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
            component_type: The type of component ('converter', 'clock', or 'fpga').

        Returns:
            A dictionary containing a list of available component names.
        """
        _populate_all_registries()

        registry = None
        if component_type.lower() == "converter":
            registry = _converter_registry
        elif component_type.lower() == "clock":
            registry = _clock_registry
        elif component_type.lower() == "fpga":
            registry = _fpga_registry
        else:
            return {
                "error": f"Invalid component_type '{component_type}'. "
                         "Must be 'converter', 'clock', or 'fpga'."
            }

        return {"components": list(registry.keys())}

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
        Retrieves detailed information about a specific component (converter, clock, or FPGA).

        Args:
            component_type: The type of component ('converter', 'clock', or 'fpga').
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
        else:
            return {
                "error": f"Invalid component_type '{component_type}'. "
                         "Must be 'converter', 'clock', or 'fpga'."
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
            if not name.startswith("_"): # Exclude private/protected members
                member = getattr(ComponentClass, name)
                if isinstance(member, property):
                    info["properties"][name] = {
                        "type": str(member.fget.__annotations__.get('return', 'Any')),
                        "docstring": inspect.getdoc(member),
                    }
                elif inspect.isfunction(member) and not name.startswith("set_"): # Exclude setters
                    if inspect.getmodule(member) == ComponentClass.__module__: # Only own methods
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
            "conv": "AD9081_RX",
            "clk": "HMC7044",
            "fpga": "XILINX",
            "vcxo": {
                "type": "fixed",
                "value": 100000000
            },
            "solver": "CPLEX",
            "converter_properties": {
                "sample_clock": 1000000000,
                "jesd_class": "jesd204c",
                "M": 4,
                "L": 8,
                "F": 1
            },
            "clock_properties": {
                "jesd_class": "jesd204c"
            },
            "fpga_properties": {},
            "pll_configurations": [
                {
                    "type": "inline",
                    "name": "ADF4371",
                    "vcxo": { "type": "fixed", "value": 122880000 },
                    "target_component": "converter",
                    "pll_properties": {
                        "r_divider": 1,
                        "n_divider": 20
                    }
                }
            ],
            "constraints": {}
        }
        For "vcxo", "type" can be "fixed" (value: int/float), "range" (start: int, stop: int, step: int),
        or "arb_source" (frequency: int, count: int).

        Args:
            system_config_json: A JSON string containing the system configuration.

        Returns:
            A dictionary containing the solving results or an error message.
        """
        _populate_all_registries()

        try:
            system_config = json.loads(system_config_json)

            conv_name = system_config.get("conv")
            clk_name = system_config.get("clk")
            fpga_name = system_config.get("fpga")
            vcxo_config = system_config.get("vcxo", {"type": "fixed", "value": 100000000}) # Default to 100MHz fixed
            solver = system_config.get("solver", "CPLEX")
            pll_configurations = system_config.get("pll_configurations", [])
            constraints = system_config.get("constraints", {})

            if not conv_name or not clk_name or not fpga_name:
                raise ValueError("System configuration must specify 'conv', 'clk', and 'fpga'.")

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
            sys_instance = adijif.system.system(
                conv=conv_name, # Pass the simple name, which is now a top-level alias
                clk=clk_name,   # Pass the simple name
                fpga=fpga_name, # Pass the simple name
                vcxo=vcxo_parsed,
                solver=solver
            )

            # Apply properties to components
            converter_properties = system_config.get("converter_properties", {})
            _apply_config_recursively(sys_instance.converter, converter_properties)

            clock_properties = system_config.get("clock_properties", {})
            _apply_config_recursively(sys_instance.clock, clock_properties)

            fpga_properties = system_config.get("fpga_properties", {})
            _apply_config_recursively(sys_instance.fpga, fpga_properties)

            # Handle PLL configurations
            for pll_cfg in pll_configurations:
                pll_type = pll_cfg.get("type")
                pll_name = pll_cfg.get("name")
                pll_vcxo_config = pll_cfg.get("vcxo")
                pll_vcxo_parsed = _parse_vcxo(pll_vcxo_config)
                pll_properties = pll_cfg.get("pll_properties", {})
                target_component_str = pll_cfg.get("target_component")
                
                if pll_type == "inline":
                    if pll_name.upper() not in _clock_registry:
                        raise ValueError(f"PLL '{pll_name}' not found in clock registry.")
                    
                    target_component = None
                    if target_component_str == "converter":
                        target_component = sys_instance.converter
                    elif target_component_str == "clock":
                        target_component = sys_instance.clock
                    elif target_component_str == "fpga":
                        target_component = sys_instance.fpga
                    else:
                        raise ValueError(f"Invalid target_component for inline PLL: {target_component_str}")
                    
                    # Add inline PLL
                    sys_instance.add_pll_inline(pll_name, pll_vcxo_parsed, target_component) # Pass simple name
                    # Apply properties to the newly added PLL
                    _apply_config_recursively(sys_instance.plls[-1], pll_properties)

                elif pll_type == "sysref":
                    if pll_name.upper() not in _clock_registry:
                        raise ValueError(f"PLL '{pll_name}' not found in clock registry for sysref.")
                    
                    sys_instance.add_pll_sysref(pll_name, pll_vcxo_parsed, sys_instance.clock) # Pass simple name
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
