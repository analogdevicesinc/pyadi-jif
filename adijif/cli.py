"""JSON command-line interface for local AI agents and automation."""

import contextlib
import io
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import click

from adijif.agent_api import call_operation, describe_operations


def _json_default(value: Any) -> Any:
    """Convert common numeric and path objects at the JSON boundary."""
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _emit(result: Dict[str, Any], pretty: bool) -> None:
    """Write exactly one JSON document and exit nonzero for API errors."""
    click.echo(
        json.dumps(
            result,
            indent=2 if pretty else None,
            sort_keys=True,
            default=_json_default,
        )
    )
    if "error" in result:
        raise click.exceptions.Exit(1)


def _read_json_source(inline: Optional[str], file_path: Optional[str]) -> str:
    """Read JSON from an option, a file, or standard input."""
    if inline is not None and file_path is not None:
        raise ValueError("Use either inline JSON or a JSON file, not both.")
    if file_path == "-":
        return sys.stdin.read()
    if file_path is not None:
        return Path(file_path).read_text(encoding="utf-8")
    return inline if inline is not None else "{}"


def _call_cleanly(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Keep solver chatter off stdout so it remains a JSON-only channel."""
    diagnostics = io.StringIO()
    with contextlib.redirect_stdout(diagnostics):
        result = call_operation(name, arguments)
    output = diagnostics.getvalue()
    if output:
        click.echo(output, err=True, nl=False)
    return result


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--pretty/--compact", default=True, help="Format JSON output.")
@click.pass_context
def main(ctx: click.Context, pretty: bool) -> None:
    """Call pyadi-jif tools locally without an MCP transport."""
    ctx.ensure_object(dict)
    ctx.obj["pretty"] = pretty


@main.command("tools")
@click.pass_context
def tools_command(ctx: click.Context) -> None:
    """List available operations and their argument schemas as JSON."""
    _emit(describe_operations(), ctx.obj["pretty"])


@main.command("call")
@click.argument("operation")
@click.option("--arguments", help="JSON object containing operation arguments.")
@click.option(
    "--arguments-file",
    type=click.Path(dir_okay=False),
    help="JSON argument file, or '-' for standard input.",
)
@click.pass_context
def call_command(
    ctx: click.Context,
    operation: str,
    arguments: Optional[str],
    arguments_file: Optional[str],
) -> None:
    """Call an MCP-equivalent operation using a JSON argument object."""
    try:
        raw = _read_json_source(arguments, arguments_file)
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("arguments must be a JSON object")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        _emit({"error": f"Invalid arguments JSON: {exc}"}, ctx.obj["pretty"])
        return
    _emit(_call_cleanly(operation, parsed), ctx.obj["pretty"])


@main.command("components")
@click.argument("component_type")
@click.pass_context
def components_command(ctx: click.Context, component_type: str) -> None:
    """List components of TYPE (converter, clock, fpga, or pll)."""
    result = _call_cleanly(
        "list_components", {"component_type": component_type}
    )
    _emit(result, ctx.obj["pretty"])


@main.command("info")
@click.argument("component_type")
@click.argument("component_name")
@click.pass_context
def info_command(
    ctx: click.Context, component_type: str, component_name: str
) -> None:
    """Describe one component as JSON."""
    result = _call_cleanly(
        "get_component_info",
        {
            "component_type": component_type,
            "component_name": component_name,
        },
    )
    _emit(result, ctx.obj["pretty"])


@main.command("jesd-modes")
@click.argument("component_name")
@click.option("--params", help="Inline JSON JESD filter parameters.")
@click.option(
    "--params-file",
    type=click.Path(dir_okay=False),
    help="JSON parameter file, or '-' for standard input.",
)
@click.pass_context
def jesd_modes_command(
    ctx: click.Context,
    component_name: str,
    params: Optional[str],
    params_file: Optional[str],
) -> None:
    """Query matching JESD modes for a converter."""
    try:
        raw = _read_json_source(params, params_file)
    except (OSError, UnicodeError, ValueError) as exc:
        _emit({"error": f"Unable to read parameters: {exc}"}, ctx.obj["pretty"])
        return
    result = _call_cleanly(
        "query_jesd_modes",
        {"component_name": component_name, "jesd_params_json": raw},
    )
    _emit(result, ctx.obj["pretty"])


@main.command("solve")
@click.argument("config_file", type=click.Path(dir_okay=False))
@click.pass_context
def solve_command(ctx: click.Context, config_file: str) -> None:
    """Solve a system from CONFIG_FILE, or '-' for standard input."""
    try:
        raw = _read_json_source(None, config_file)
    except (OSError, UnicodeError, ValueError) as exc:
        _emit(
            {"error": f"Unable to read system configuration: {exc}"},
            ctx.obj["pretty"],
        )
        return
    result = _call_cleanly("solve_system", {"system_config_json": raw})
    _emit(result, ctx.obj["pretty"])


if __name__ == "__main__":
    main()
