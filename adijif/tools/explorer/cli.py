"""CLI entry point for PyADI-JIF Tools Explorer."""

import os
import sys
from typing import Optional


def run_streamlit(args: Optional[list[str]] = None) -> None:
    """Run the Streamlit tools explorer app."""
    # Lazy import: streamlit is an optional dependency (extras: [tools]).
    # Importing at module level causes pipx installation to fail when streamlit
    # is not yet installed, even if the [tools] extra is specified.
    from streamlit.web import cli as stcli  # noqa: PLC0415

    # Get the directory where this file is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    main_file = os.path.join(current_dir, "main.py")

    # Get arguments from sys.argv if not provided
    if args is None:
        args = sys.argv[1:]

    # Set up sys.argv for streamlit
    sys.argv = [
        "streamlit",
        "run",
        main_file,
        "--logger.level=error",
        "--browser.gatherUsageStats=false",
        "--server.showEmailPrompt=false",
        # Shared ADI accent + font across both light and dark modes.
        "--theme.base=light",
        "--theme.primaryColor=#0067B9",
        "--theme.font=sans serif",
        # ADI-tuned light palette.
        "--theme.light.backgroundColor=#FFFFFF",
        "--theme.light.secondaryBackgroundColor=#F5F7FA",
        "--theme.light.textColor=#231F20",
        # ADI-tuned dark palette.
        "--theme.dark.backgroundColor=#0A2540",
        "--theme.dark.secondaryBackgroundColor=#102B4F",
        "--theme.dark.textColor=#FFFFFF",
    ] + args

    # Run streamlit
    sys.exit(stcli.main())


if __name__ == "__main__":
    args = sys.argv[1:]
    run_streamlit(args)
