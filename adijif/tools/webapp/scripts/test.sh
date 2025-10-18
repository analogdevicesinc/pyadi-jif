#!/bin/bash

# Test script for PyADI-JIF Tools Explorer Web App

set -e

echo "======================================"
echo "Running Tests"
echo "======================================"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEBAPP_DIR="$(dirname "$SCRIPT_DIR")"

# Check if backend and frontend are running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "Error: Backend is not running. Please start the application first."
    echo "Run: ./scripts/start.sh"
    exit 1
fi

if ! curl -s http://localhost:3000 > /dev/null; then
    echo "Error: Frontend is not running. Please start the application first."
    echo "Run: ./scripts/start.sh"
    exit 1
fi

echo "Starting Selenium tests..."
echo ""

cd "$WEBAPP_DIR/tests"
pytest -v --tb=short

echo ""
echo "======================================"
echo "Tests complete!"
echo "======================================"
