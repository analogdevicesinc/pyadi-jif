"""CLI entry point for PyADI-JIF Tools Explorer."""

import os
import sys

from streamlit.web import cli as stcli


def run_streamlit() -> None:
    """Run the Streamlit tools explorer app."""
    # Get the directory where this file is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    main_file = os.path.join(current_dir, "main.py")

    # Set up sys.argv for streamlit
    sys.argv = ["streamlit", "run", main_file]

    # Run streamlit
    sys.exit(stcli.main())


if __name__ == "__main__":
    run_streamlit()
