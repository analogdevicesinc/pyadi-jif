#!/usr/bin/env python3
"""Development server script for PyADI-JIF Tools Explorer Web App.

This script can be run directly without installing the package:
    python run_dev.py
"""

import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Run the web application in development mode."""
    webapp_dir = Path(__file__).parent
    frontend_dir = webapp_dir / "frontend"

    print("=" * 80)
    print("PyADI-JIF Tools Explorer - Web Application (Development Mode)")
    print("=" * 80)
    print()
    print("This will start the FastAPI backend and React frontend.")
    print()
    print("Backend API will be available at: http://localhost:8000")
    print("Frontend UI will be available at: http://localhost:3000")
    print()
    print("=" * 80)
    print()

    # Check if frontend dependencies are installed
    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        print("Frontend dependencies not found. Installing...")
        print()
        try:
            subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)
        except FileNotFoundError:
            print("ERROR: npm not found. Please install Node.js first.")
            sys.exit(1)
        print()

    # Start backend in background
    print("Starting FastAPI backend...")
    backend_process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "adijif.tools.webapp.backend.main:app",
            "--reload",
            "--port",
            "8000",
        ],
    )

    # Start frontend
    print("Starting React frontend...")
    print()
    try:
        subprocess.run(["npm", "run", "dev"], cwd=frontend_dir, check=True)
    except KeyboardInterrupt:
        print("\nShutting down...")
    except FileNotFoundError:
        print("ERROR: npm not found. Please install Node.js first.")
    finally:
        backend_process.terminate()
        backend_process.wait()


if __name__ == "__main__":
    main()
