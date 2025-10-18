#!/bin/bash

# Start script for PyADI-JIF Tools Explorer Web App

set -e

echo "======================================"
echo "Starting PyADI-JIF Tools Explorer Web App"
echo "======================================"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEBAPP_DIR="$(dirname "$SCRIPT_DIR")"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend
echo "Starting FastAPI backend on http://localhost:8000..."
python3 -m uvicorn adijif.tools.webapp.backend.main:app --reload --port 8000 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait for backend to start
sleep 3

# Start frontend
echo "Starting React frontend on http://localhost:3000..."
cd "$WEBAPP_DIR/frontend"
npm run dev &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

echo ""
echo "======================================"
echo "Application started!"
echo "======================================"
echo ""
echo "Backend API: http://localhost:8000"
echo "API Docs:    http://localhost:8000/docs"
echo "Frontend UI: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Wait for processes
wait
