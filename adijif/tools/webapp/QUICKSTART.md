# Quick Start Guide

Get the PyADI-JIF Tools Explorer web application running in 5 minutes!

## Prerequisites

Make sure you have:
- Python 3.9+ installed
- Node.js 18+ installed
- PyADI-JIF installed (if not: `pip install pyadi-jif[cplex,draw]`)

## Option 1: Using the Development Script (Easiest)

From the repository root:

```bash
cd adijif/tools/webapp
python run_dev.py
```

That's it! The script will:
1. Install frontend dependencies (if needed)
2. Start the backend on http://localhost:8000
3. Start the frontend on http://localhost:3000

Press Ctrl+C to stop both servers.

## Option 2: Using the CLI Command

If you've installed the package in development mode:

```bash
# One-time setup
pip install -e ".[webapp]"

# Run the application
jifwebapp
```

## Option 3: Using Helper Scripts

From the `webapp` directory:

```bash
# Setup (first time only)
./scripts/setup.sh

# Start the application
./scripts/start.sh

# Run tests (in another terminal after starting)
./scripts/test.sh
```

## Option 4: Manual Setup

### Terminal 1 - Backend
```bash
python -m uvicorn adijif.tools.webapp.backend.main:app --reload --port 8000
```

### Terminal 2 - Frontend
```bash
cd adijif/tools/webapp/frontend
npm install  # First time only
npm run dev
```

## Accessing the Application

Once running:
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **API**: http://localhost:8000/api

## What to Expect

The application has 3 main pages:

1. **JESD204 Mode Selector** - Configure JESD modes for ADI converters
2. **Clock Configurator** - Design clock distribution systems
3. **System Configurator** - Configure complete systems

## Common Issues

### "ImportError: attempted relative import"
Use `python run_dev.py` or install the package with `pip install -e ".[webapp]"`

### "Port already in use"
Another application is using port 8000 or 3000. Either:
- Stop the other application
- Change the port in the startup command

### "npm: command not found"
Install Node.js from https://nodejs.org/

### "Module 'adijif' not found"
Install PyADI-JIF:
```bash
pip install pyadi-jif[cplex,draw]
# or from source:
pip install -e ".[cplex,draw]"
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [CONTRIBUTING.md](CONTRIBUTING.md) to learn how to add features
- See [MIGRATION.md](MIGRATION.md) for differences from the Streamlit version

## Need Help?

- Check the API documentation at http://localhost:8000/docs
- Review the troubleshooting section in README.md
- Open an issue on GitHub
