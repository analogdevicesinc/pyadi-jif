"""Transport-neutral operations for MCP and local agent clients."""

import inspect
import json
from typing import Any, Callable, Dict

import adijif.types
from adijif.registry import COMPONENT_REGISTRY, get_component_class
from adijif.system import system as _system
from adijif.utils import get_jesd_mode_from_params

AgentResult = Dict[str, Any]
AgentOperation = Callable[..., AgentResult]
_COMPONENT_KINDS = ("converter", "clock", "fpga", "pll")


def _parse_vcxo(vcxo_config: Dict[str, Any]) -> Any:
    """Parse a JSON VCXO description into a pyadi-jif source."""
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
        return adijif.types.range(start, stop, step, "vcxo")
    if vcxo_type == "arb_source":
        frequency = vcxo_config.get("frequency")
        count = vcxo_config.get("count")
        if frequency is None or count is None:
            raise ValueError(
                "vcxo of type 'arb_source' requires 'frequency' and 'count'."
            )
        return adijif.types.arb_source(str(frequency), count)
    return value


def _apply_config_recursively(obj: Any, config: Dict[str, Any]) -> None:
    """Apply nested configuration dictionaries to a component."""
    for key, value in config.items():
        if not isinstance(key, str) or key.startswith("_"):
            raise ValueError(f"Invalid configuration attribute: {key!r}")
        if not hasattr(obj, key):
            raise ValueError(
                f"Unknown configuration attribute '{key}' for "
                f"{type(obj).__name__}"
            )
        current = getattr(obj, key)
        if isinstance(value, dict):
            if current is None or isinstance(
                current, (str, bytes, int, float, bool, list, tuple, dict)
            ):
                raise ValueError(
                    f"Configuration attribute '{key}' does not accept nested values"
                )
            _apply_config_recursively(getattr(obj, key), value)
        else:
            setattr(obj, key, value)


def _registry_for(component_type: str) -> Dict[str, type]:
    """Return one validated component registry."""
    if not isinstance(component_type, str):
        raise ValueError("component_type must be a string")
    normalized = component_type.lower()
    if normalized not in COMPONENT_REGISTRY:
        raise ValueError(
            f"Invalid component_type '{component_type}'. Must be one of "
            f"{', '.join(_COMPONENT_KINDS)}."
        )
    return COMPONENT_REGISTRY[normalized]  # type: ignore[return-value]


def list_components(component_type: str) -> AgentResult:
    """List supported component names for one component kind."""
    try:
        registry = _registry_for(component_type)
    except ValueError as exc:
        return {"error": str(exc)}
    return {"components": sorted(name.upper() for name in registry)}


def query_jesd_modes(
    component_name: str, jesd_params_json: str = "{}"
) -> AgentResult:
    """Find converter JESD modes matching JSON parameters."""
    if not isinstance(component_name, str):
        return {"error": "component_name must be a string"}
    if not isinstance(jesd_params_json, str):
        return {"error": "jesd_params_json must be a string"}
    try:
        jesd_params = json.loads(jesd_params_json)
    except json.JSONDecodeError as exc:
        return {
            "error": f"Invalid JSON string for jesd_params_json: {exc}",
            "jesd_params_json": jesd_params_json,
        }

    try:
        converter_class = get_component_class("converter", component_name)
    except (TypeError, ValueError):
        available = list_components("converter")["components"]
        return {
            "error": f"Component '{component_name}' not found in registry. "
            f"Available components: {available}"
        }

    try:
        converter_instance = converter_class(model=None, solver="CPLEX")
        found_modes = get_jesd_mode_from_params(converter_instance, **jesd_params)
        return {
            "component": component_name,
            "jesd_modes": found_modes,
            "query_params": jesd_params,
        }
    except Exception as exc:
        return {
            "error": f"Failed to query JESD modes for '{component_name}': {exc}",
            "component": component_name,
            "query_params": jesd_params,
        }


def get_component_info(component_type: str, component_name: str) -> AgentResult:
    """Describe a component's constructor and public API."""
    try:
        registry = _registry_for(component_type)
    except ValueError as exc:
        return {"error": str(exc)}

    if not isinstance(component_name, str):
        return {"error": "component_name must be a string"}
    normalized_name = component_name.lower()
    if normalized_name not in registry:
        available = sorted(name.upper() for name in registry)
        return {
            "error": f"Component '{component_name}' of type '{component_type}' "
            f"not found. Available {component_type}s: {available}"
        }

    component_class = registry[normalized_name]
    info: AgentResult = {
        "name": component_class.__name__,
        "docstring": inspect.getdoc(component_class),
        "constructor_signature": str(inspect.signature(component_class.__init__)),
        "properties": {},
    }
    properties = info["properties"]
    for name in dir(component_class):
        if name.startswith("_"):
            continue
        member = getattr(component_class, name)
        if isinstance(member, property):
            annotations = getattr(member.fget, "__annotations__", {})
            properties[name] = {
                "type": str(annotations.get("return", "Any")),
                "docstring": inspect.getdoc(member),
            }
        elif (
            inspect.isfunction(member)
            and not name.startswith("set_")
            and inspect.getmodule(member) == inspect.getmodule(component_class)
        ):
            properties[name] = {
                "type": "method",
                "signature": str(inspect.signature(member)),
                "docstring": inspect.getdoc(member),
            }
    return info


def solve_system(system_config_json: str) -> AgentResult:
    """Solve a system from the MCP-compatible JSON configuration."""
    if not isinstance(system_config_json, str):
        return {"error": "system_config_json must be a string"}
    try:
        system_config = json.loads(system_config_json)
    except json.JSONDecodeError as exc:
        return {
            "error": f"Invalid JSON string for system_config_json: {exc}",
            "system_config_json": system_config_json,
        }
    if not isinstance(system_config, dict):
        return {
            "error": "Configuration error: system configuration must be an object",
            "system_config_json": system_config_json,
        }

    try:
        conv_name = system_config.get("conv")
        clk_name = system_config.get("clk")
        fpga_name = system_config.get("fpga")
        if not conv_name or not clk_name or not fpga_name:
            raise ValueError(
                "System configuration must specify 'conv', 'clk', and 'fpga'."
            )

        try:
            get_component_class("converter", conv_name)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Converter '{conv_name}' not found in registry."
            ) from exc
        try:
            get_component_class("clock", clk_name)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Clock '{clk_name}' not found in registry.") from exc
        try:
            get_component_class("fpga", fpga_name)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"FPGA '{fpga_name}' not found in registry.") from exc

        vcxo_config = system_config.get(
            "vcxo", {"type": "fixed", "value": 100_000_000}
        )
        solver = system_config.get("solver", "CPLEX")
        sys_instance = _system(
            conv=conv_name,
            clk=clk_name,
            fpga=fpga_name,
            vcxo=_parse_vcxo(vcxo_config),
            solver=solver,
        )

        _apply_config_recursively(
            sys_instance.converter, system_config.get("converter_properties", {})
        )
        _apply_config_recursively(
            sys_instance.clock, system_config.get("clock_properties", {})
        )
        _apply_config_recursively(
            sys_instance.fpga, system_config.get("fpga_properties", {})
        )

        for pll_config in system_config.get("pll_configurations", []):
            if not isinstance(pll_config, dict):
                raise ValueError("Each PLL configuration must be an object")
            pll_type = pll_config.get("type")
            pll_name = pll_config.get("name")
            pll_properties = pll_config.get("pll_properties", {})
            if not isinstance(pll_name, str):
                raise ValueError("PLL configuration requires a string 'name'")
            if not isinstance(pll_properties, dict):
                raise ValueError("PLL 'pll_properties' must be an object")

            if pll_type == "inline":
                target = pll_config.get("target_component", "converter")
                if target != "converter":
                    raise ValueError(
                        f"Invalid target_component for inline PLL: {target}"
                    )
                try:
                    get_component_class("pll", pll_name)
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        f"PLL '{pll_name}' not found in clock registry."
                    ) from exc
                if "vcxo" in pll_config:
                    raise ValueError(
                        "Per-PLL 'vcxo' is not supported; PLL references are "
                        "wired from the system clock"
                    )
                sys_instance.add_pll_inline(
                    pll_name, sys_instance.clock, sys_instance.converter
                )
                _apply_config_recursively(sys_instance.plls[-1], pll_properties)
            elif pll_type == "sysref":
                try:
                    get_component_class("pll", pll_name)
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        f"PLL '{pll_name}' not found in clock registry for sysref."
                    ) from exc
                if "vcxo" in pll_config:
                    raise ValueError(
                        "Per-PLL 'vcxo' is not supported; PLL references are "
                        "wired from the system clock"
                    )
                sys_instance.add_pll_sysref(
                    pll_name,
                    sys_instance.clock,
                    sys_instance.converter,
                    sys_instance.fpga,
                )
                _apply_config_recursively(
                    sys_instance._plls_sysref[-1], pll_properties
                )
            else:
                raise ValueError(
                    f"Unsupported PLL configuration type: {pll_type}"
                )

        solution = sys_instance.solve(
            out_clock_constraints=system_config.get("constraints", {})
        )
        result: AgentResult = {
            "config": system_config,
            "solution": solution,
            "status": "solved",
        }
        contract_format = system_config.get("export_format")
        if contract_format:
            result["contract"] = sys_instance.export_config(
                format=contract_format, solution=solution
            ).to_dict()
        return result
    except (TypeError, ValueError) as exc:
        return {
            "error": f"Configuration error: {exc}",
            "system_config_json": system_config_json,
        }
    except Exception as exc:
        return {
            "error": f"An unexpected error occurred during system solving: {exc}",
            "system_config_json": system_config_json,
        }


AGENT_OPERATIONS: Dict[str, AgentOperation] = {
    "list_components": list_components,
    "query_jesd_modes": query_jesd_modes,
    "get_component_info": get_component_info,
    "solve_system": solve_system,
}


def call_operation(name: str, arguments: Dict[str, Any]) -> AgentResult:
    """Invoke a named operation using JSON-compatible keyword arguments."""
    if not isinstance(name, str):
        return {"error": "operation name must be a string"}
    if not isinstance(arguments, dict):
        return {"error": "operation arguments must be an object"}
    operation = AGENT_OPERATIONS.get(name)
    if operation is None:
        return {
            "error": f"Unknown operation '{name}'. Available operations: "
            f"{sorted(AGENT_OPERATIONS)}"
        }
    try:
        return operation(**arguments)
    except Exception as exc:
        return {"error": f"Invalid arguments for '{name}': {exc}"}


def describe_operations() -> AgentResult:
    """Return local discovery metadata for agent operations."""
    tools = []
    for name, operation in AGENT_OPERATIONS.items():
        signature = inspect.signature(operation)
        properties = {}
        required = []
        for parameter in signature.parameters.values():
            annotation = parameter.annotation
            json_type = {
                str: "string",
                int: "integer",
                float: "number",
                bool: "boolean",
                dict: "object",
            }.get(annotation, "string")
            property_schema = {"type": json_type}
            if parameter.default is inspect.Parameter.empty:
                required.append(parameter.name)
            else:
                property_schema["default"] = parameter.default
            properties[parameter.name] = property_schema
        tools.append(
            {
                "name": name,
                "description": inspect.getdoc(operation),
                "signature": str(signature),
                "input_schema": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                    "additionalProperties": False,
                },
            }
        )
    return {"tools": tools}
