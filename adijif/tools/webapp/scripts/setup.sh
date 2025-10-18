#!/bin/bash

# Setup script for PyADI-JIF Tools Explorer Web App

set -e

echo "======================================"
echo "PyADI-JIF Tools Explorer Web App Setup"
echo "======================================"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Check Node.js version
echo "Checking Node.js version..."
node_version=$(node --version 2>&1)
echo "Node.js version: $node_version"
echo ""

# Install Python dependencies
echo "Installing Python dependencies..."
cd "$(dirname "$0")/.."
pip install -e "../../../..[webapp,cplex,draw]"
echo ""

# Install frontend dependencies
echo "Installing frontend dependencies..."
cd frontend
npm install
echo ""

# Copy environment files
echo "Setting up environment files..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created frontend/.env"
fi

cd ../backend
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created backend/.env"
fi
echo ""

echo "======================================"
echo "Setup complete!"
echo "======================================"
echo ""
echo "To start the application:"
echo "  Option 1: Run 'jifwebapp' command"
echo "  Option 2: Run './scripts/start.sh'"
echo ""
echo "To run tests:"
echo "  cd tests && pytest -v"
echo ""
