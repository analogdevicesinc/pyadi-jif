# PyADI-JIF Tools Explorer - Web Application

A modern web application for configuring JESD204 converters, clocks, and complete systems. Built with React, Material-UI, and FastAPI.

## Features

- **JESD204 Mode Selector**: Select and configure JESD204 modes for ADI converters
- **Clock Configurator**: Configure clock distribution chips
- **System Configurator**: Configure complete systems with converters, clocks, and FPGAs
- Modern Material-UI interface
- Real-time configuration validation
- Interactive diagrams
- Comprehensive Selenium test suite

## Project Structure

```
webapp/
├── backend/           # FastAPI backend
│   ├── api/          # API endpoints
│   ├── services/     # Business logic
│   └── main.py       # FastAPI application
├── frontend/          # React frontend
│   ├── src/
│   │   ├── api/      # API client
│   │   ├── pages/    # Page components
│   │   ├── App.tsx   # Main app component
│   │   └── main.tsx  # Entry point
│   └── public/       # Static assets
└── tests/            # Selenium E2E tests
```

## Prerequisites

- Python 3.9+
- Node.js 18+
- npm or yarn

## Installation

### Backend Setup

1. Install Python dependencies:

```bash
cd backend
pip install -r requirements.txt
```

2. Install PyADI-JIF with required extras:

```bash
pip install "pyadi-jif[cplex,draw]"
```

### Frontend Setup

1. Install Node dependencies:

```bash
cd frontend
npm install
```

## Running the Application

### Quick Start (Recommended)

The easiest way to run the application:

```bash
cd adijif/tools/webapp
python run_dev.py
```

This will automatically:
- Install frontend dependencies if needed
- Start the FastAPI backend on port 8000
- Start the React frontend on port 3000
- Open your browser to [http://localhost:3000](http://localhost:3000)

### Using the CLI Command (After Package Installation)

If you've installed the package with `pip install -e ".[webapp]"`:

```bash
jifwebapp
```

### Manual Development Mode

1. Start the FastAPI backend:

```bash
python -m uvicorn adijif.tools.webapp.backend.main:app --reload --port 8000
```

2. In a new terminal, start the React frontend:

```bash
cd adijif/tools/webapp/frontend
npm run dev
```

3. Open your browser to [http://localhost:3000](http://localhost:3000)

### Production Mode

1. Build the frontend:

```bash
cd frontend
npm run build
```

2. Serve with a production server or integrate with FastAPI static file serving.

## Running Tests

### Selenium Tests

1. Ensure both backend and frontend are running

2. Install test dependencies:

```bash
cd tests
pip install -r requirements.txt
```

3. Run tests:

```bash
pytest -v
```

### Frontend Unit Tests

```bash
cd frontend
npm test
```

## API Documentation

Once the backend is running, visit:
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## API Endpoints

### Converters
- `GET /api/converters/supported` - List supported converters
- `GET /api/converters/{part}/info` - Get converter information
- `POST /api/converters/{part}/valid-modes` - Get valid JESD modes

### Clocks
- `GET /api/clocks/supported` - List supported clocks
- `POST /api/clocks/{part}/solve` - Solve clock configuration

### Systems
- `GET /api/systems/fpga-dev-kits` - List FPGA dev kits
- `POST /api/systems/solve` - Solve system configuration

## Docker Support

Build and run with Docker:

```bash
# Build
docker-compose build

# Run
docker-compose up
```

## Technology Stack

### Frontend
- React 18
- TypeScript
- Material-UI 5
- Vite
- TanStack Query (React Query)
- Axios

### Backend
- FastAPI
- Pydantic
- Uvicorn
- PyADI-JIF

### Testing
- Selenium WebDriver
- Pytest
- Chrome WebDriver

## Development

### Code Style

Frontend:
```bash
npm run lint
```

Backend:
```bash
ruff check .
```

### Adding New Features

1. Add API endpoint in `backend/api/`
2. Create corresponding API client method in `frontend/src/api/client.ts`
3. Implement UI in React components
4. Add Selenium tests in `tests/`

## Troubleshooting

### ImportError: attempted relative import with no known parent package

If you see this error, it means the Python module isn't being imported correctly. Solutions:

1. **Use the run_dev.py script (Recommended)**:
   ```bash
   python adijif/tools/webapp/run_dev.py
   ```

2. **Install the package in development mode**:
   ```bash
   pip install -e ".[webapp]"
   jifwebapp
   ```

3. **Use the full module path with uvicorn**:
   ```bash
   python -m uvicorn adijif.tools.webapp.backend.main:app --reload --port 8000
   ```

### Port Already in Use

If port 8000 or 3000 is already in use:

Backend:
```bash
python -m uvicorn adijif.tools.webapp.backend.main:app --reload --port 8001
```

Frontend: Edit `vite.config.ts` to change the port.

### CORS Issues

CORS is configured in `backend/main.py`. Ensure your frontend origin is in the allowed origins list.

### Frontend Dependencies Not Installing

Make sure you have Node.js 18+ and npm installed:
```bash
node --version  # Should be 18+
npm --version
```

## License

Same as PyADI-JIF (EPL-2.0)
