# flake8: noqa
"""MCP transport for the shared pyadi-jif agent operations."""

from typing import Any, Dict

import click
from fastmcp import FastMCP

from adijif.agent_api import (
    _apply_config_recursively,
    _parse_vcxo,
    export_xgt_wizard as _export_xgt_wizard,
    get_component_info as _get_component_info,
    list_components as _list_components,
    query_jesd_modes as _query_jesd_modes,
    solve_system as _solve_system,
)


def create_mcp_server() -> FastMCP:
    """Create the MCP server backed by the transport-neutral agent API."""
    mcp_instance = FastMCP(name="pyadi-jif MCP Server")

    @mcp_instance.tool
    def list_components(component_type: str) -> Dict[str, Any]:
        """List registered converter, clock, FPGA, or PLL components.

        Args:
            component_type: One of ``converter``, ``clock``, ``fpga``, or
                ``pll``.

        Returns:
            A dictionary with a ``components`` list, or an ``error`` string.
        """
        return _list_components(component_type)

    @mcp_instance.tool
    def query_jesd_modes(
        component_name: str, jesd_params_json: str = "{}"
    ) -> Dict[str, Any]:
        """Find converter JESD modes matching JSON parameters.

        Args:
            component_name: Registered converter name, such as ``AD9081_RX``.
            jesd_params_json: JSON object encoded as a string. Keys can include
                JESD parameters such as ``M``, ``L``, ``K``, ``F``, and ``S``.

        Returns:
            Matching ``jesd_modes`` and normalized ``query_params``, or an
            ``error`` string.
        """
        return _query_jesd_modes(component_name, jesd_params_json)

    @mcp_instance.tool
    def get_component_info(
        component_type: str, component_name: str
    ) -> Dict[str, Any]:
        """Describe a component's constructor and public API.

        Args:
            component_type: One of ``converter``, ``clock``, ``fpga``, or
                ``pll``.
            component_name: Name returned by ``list_components``.

        Returns:
            Class name, docstring, constructor signature, and public
            properties/methods, or an ``error`` string.
        """
        return _get_component_info(component_type, component_name)

    @mcp_instance.tool
    def solve_system(system_config_json: str) -> Dict[str, Any]:
        """Solve a converter, clock, and FPGA system from JSON.

        The encoded object requires ``conv``, ``clk``, and ``fpga``. Optional
        fields are ``vcxo``, ``solver``, ``converter_properties``,
        ``clock_properties``, ``fpga_properties``, ``pll_configurations``,
        ``constraints``, and ``export_format``. A VCXO can be fixed, a range,
        or an arbitrary source. Inline PLLs are wired from the system clock to
        the converter; sysref PLLs drive converter/FPGA SYSREF. Set
        ``export_format`` to ``adi.jif-dt`` to include a versioned contract.

        Args:
            system_config_json: System configuration object encoded as JSON.

        Returns:
            ``status``, ``config``, and ``solution`` on success, optionally a
            ``contract``; otherwise an ``error`` string.
        """
        return _solve_system(system_config_json)

    @mcp_instance.tool
    def export_xgt_wizard(
        system_config_json: str, hdl_project: str = ""
    ) -> Dict[str, Any]:
        """Solve a system and export HDL repo xgt_wizard build parameters.

        Maps the solved transceiver configuration onto the ADI HDL repo's
        ``adi_xcvr_project`` contract (``LANE_RATE``, ``REF_CLK``,
        ``PLL_TYPE``, ``JESD_MODE``, and ``XCVR_RX_*`` overrides).

        Args:
            system_config_json: Same JSON configuration as ``solve_system``.
            hdl_project: Optional HDL project path relative to
                ``projects/`` (e.g. ``ad9081_fmca_ebz/zcu102``) to include
                a full ``make_command``.

        Returns:
            ``status``, ``config``, ``make_args``, ``tcl``, and optionally
            ``make_command`` on success; otherwise an ``error`` string.
        """
        return _export_xgt_wizard(system_config_json, hdl_project)

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
def main(transport: str, port: int) -> None:
    """Start the pyadi-jif MCP server."""
    click.echo(f"Starting pyadi-jif MCP server with transport: {transport}")
    mcp = create_mcp_server()
    if transport == "http":
        click.echo(f"Listening on port: {port}")
        mcp.run(transport=transport, port=port)
    else:
        mcp.run(transport=transport)


if __name__ == "__main__":
    main()
