# Migration from Streamlit to React + FastAPI

This document describes the migration from the Streamlit-based explorer to the new React + FastAPI web application.

## Overview

The new web application provides the same functionality as the Streamlit app but with:
- Modern React frontend with Material-UI
- FastAPI backend with proper API architecture
- Better performance and scalability
- Comprehensive test coverage with Selenium
- Docker support for easy deployment

## Feature Parity

### JESD Mode Selector
**Streamlit**: Uses `streamlit` widgets for part selection, datapath configuration, and mode filtering.
**React + FastAPI**:
- React components with Material-UI `Select`, `TextField`, etc.
- FastAPI endpoints for fetching parts, modes, and configurations
- Real-time mode validation

### Clock Configurator
**Streamlit**: Interactive widgets for clock inputs/outputs and internal configuration.
**React + FastAPI**:
- Dynamic output clock management with add/remove functionality
- Range sliders for large option sets
- API-based solver with diagram generation

### System Configurator
**Streamlit**: Combined converter, clock, and FPGA configuration.
**React + FastAPI**:
- Separate configuration panels for each component
- Real-time validation of configuration completeness
- Solve button enabled only when all required fields are filled

## Architecture Changes

### Backend
**Before (Streamlit)**:
- Monolithic application with page-based structure
- Session state management
- Direct library calls in UI code

**After (FastAPI)**:
- RESTful API with clear endpoint structure
- Stateless API design
- Separation of concerns (API, services, models)
- OpenAPI documentation

### Frontend
**Before (Streamlit)**:
- Python-based UI with `streamlit` widgets
- Server-side rendering
- Built-in state management

**After (React)**:
- TypeScript-based UI with Material-UI components
- Client-side rendering
- TanStack Query for state management
- Modern build tools (Vite)

## API Mapping

### Converters
```python
# Streamlit
converter = eval(f"adijif.{part}()")
modes = converter.quick_configuration_modes

# React + FastAPI
GET /api/converters/supported
GET /api/converters/{part}/quick-modes
POST /api/converters/{part}/valid-modes
```

### Clocks
```python
# Streamlit
clk_chip = eval(f"adijif.{part}()")
clk_chip.solve()

# React + FastAPI
GET /api/clocks/supported
POST /api/clocks/{part}/solve
POST /api/clocks/{part}/diagram
```

### Systems
```python
# Streamlit
sys = adijif.system(converter, clock, fpga, vcxo)
cfg = sys.solve()

# React + FastAPI
POST /api/systems/solve
POST /api/systems/diagram
```

## Running Both Applications

The Streamlit app is still available and can be run alongside the new webapp:

```bash
# Streamlit (legacy)
jiftools

# React + FastAPI (new)
jifwebapp
```

## Testing

### Streamlit
Limited testing capabilities, mainly manual testing.

### React + FastAPI
Comprehensive test suite:
- Unit tests for frontend components (planned)
- API integration tests
- End-to-end Selenium tests
- Coverage reporting

Run tests:
```bash
cd adijif/tools/webapp/tests
pytest -v
```

## Deployment

### Streamlit
```bash
streamlit run main.py
```

### React + FastAPI

Development:
```bash
# Terminal 1: Backend
cd backend
uvicorn main:app --reload

# Terminal 2: Frontend
cd frontend
npm run dev
```

Production:
```bash
# Build frontend
cd frontend
npm run build

# Serve with production server
docker-compose up
```

## Customization

### Streamlit
- Custom CSS via `st.html()` or `st.markdown()`
- Limited theming options
- Page-based navigation

### React + FastAPI
- Material-UI theme customization in `theme.ts`
- Component-level styling with emotion/styled
- Route-based navigation with React Router
- Full control over UI/UX

## Performance

### Streamlit
- Server-side rendering
- Full page reloads on state changes
- Session state overhead

### React + FastAPI
- Client-side rendering
- Selective component updates
- Stateless API calls
- Caching with TanStack Query

## Migration Checklist

- [x] Set up FastAPI backend structure
- [x] Implement converter API endpoints
- [x] Implement clock API endpoints
- [x] Implement system API endpoints
- [x] Create React frontend with Material-UI
- [x] Implement JESD Mode Selector page
- [x] Implement Clock Configurator page
- [x] Implement System Configurator page
- [x] Set up Selenium test infrastructure
- [x] Create Docker support
- [x] Update package configuration
- [ ] Deprecate Streamlit app (future)
- [ ] Update main documentation

## Future Enhancements

Possible improvements for the new webapp:
- User authentication and saved configurations
- Configuration history and comparison
- Export to various formats (JSON, YAML, etc.)
- Real-time collaboration
- Advanced visualization options
- Mobile-responsive improvements
- Progressive Web App (PWA) support
