"""CLI entry point for PyADI-JIF Tools Explorer Web App."""

import os
import subprocess
import sys
from pathlib import Path


def run_webapp() -> None:
    """Run the web application (backend and frontend)."""
    webapp_dir = Path(__file__).parent

    print("=" * 80)
    print("PyADI-JIF Tools Explorer - Web Application")
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
    frontend_dir = webapp_dir / "frontend"
    node_modules = frontend_dir / "node_modules"

    if not node_modules.exists():
        print("Frontend dependencies not found. Installing...")
        print()
        subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)
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
    finally:
        backend_process.terminate()
        backend_process.wait()


if __name__ == "__main__":
    run_webapp()
