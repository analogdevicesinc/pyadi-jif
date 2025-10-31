"""CLI entry point for PyADI-JIF Tools Explorer."""

import os
import sys
from typing import Optional

from streamlit.web import cli as stcli


def run_streamlit(args: Optional[list[str]] = None) -> None:
    """Run the Streamlit tools explorer app."""
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
    ] + args

    # Run streamlit
    sys.exit(stcli.main())


if __name__ == "__main__":
    args = sys.argv[1:]
    run_streamlit(args)
