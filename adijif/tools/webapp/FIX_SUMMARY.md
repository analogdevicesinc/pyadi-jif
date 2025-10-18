# Import Error Fix Summary

## Problem

When running `jifwebapp`, you encountered this error:
```
ImportError: attempted relative import with no known parent package
```

This occurred in `/workspaces/pyadi-jif/adijif/tools/webapp/backend/main.py` at line 10:
```python
from .api import clock_router, converter_router, system_router
```

## Root Cause

The issue was caused by **relative imports** in the backend code. When uvicorn tried to load the module with `main:app`, it imported `main.py` as a standalone module rather than as part of a package, causing relative imports (those starting with `.`) to fail.

## Solution

Changed all relative imports to **absolute imports** using the full module path:

### Files Modified

1. **[backend/main.py](backend/main.py:10)**
   ```python
   # Before:
   from .api import clock_router, converter_router, system_router

   # After:
   from adijif.tools.webapp.backend.api import clock_router, converter_router, system_router
   ```

2. **[backend/api/__init__.py](backend/api/__init__.py:3-5)**
   ```python
   # Before:
   from .clocks import router as clock_router
   from .converters import router as converter_router
   from .systems import router as system_router

   # After:
   from adijif.tools.webapp.backend.api.clocks import router as clock_router
   from adijif.tools.webapp.backend.api.converters import router as converter_router
   from adijif.tools.webapp.backend.api.systems import router as system_router
   ```

3. **[backend/api/converters.py](backend/api/converters.py:15-18)**
   ```python
   # Before:
   from ..services.diagram_service import draw_adc_diagram, draw_dac_diagram

   # After:
   from adijif.tools.webapp.backend.services.diagram_service import (
       draw_adc_diagram,
       draw_dac_diagram,
   )
   ```

4. **[backend/services/__init__.py](backend/services/__init__.py:3-6)**
   ```python
   # Before:
   from .diagram_service import draw_adc_diagram, draw_dac_diagram

   # After:
   from adijif.tools.webapp.backend.services.diagram_service import (
       draw_adc_diagram,
       draw_dac_diagram,
   )
   ```

5. **[cli.py](cli.py:37-46)** - Updated to use full module path:
   ```python
   # Before:
   [sys.executable, "-m", "uvicorn", "main:app", "--reload", "--port", "8000"]

   # After:
   [sys.executable, "-m", "uvicorn", "adijif.tools.webapp.backend.main:app", "--reload", "--port", "8000"]
   ```

6. **[scripts/start.sh](scripts/start.sh:29)** - Updated to use full module path:
   ```bash
   # Before:
   python3 -m uvicorn main:app --reload --port 8000

   # After:
   python3 -m uvicorn adijif.tools.webapp.backend.main:app --reload --port 8000
   ```

## New Features Added

### 1. Development Script ([run_dev.py](run_dev.py))

Created a standalone script that can be run without package installation:

```bash
cd adijif/tools/webapp
python run_dev.py
```

This is now the **recommended way** to run the application during development.

### 2. Updated Documentation

- **[README.md](README.md)** - Added troubleshooting section with import error fix
- **[QUICKSTART.md](QUICKSTART.md)** - New quick start guide with 4 different ways to run the app

## How to Run the Application Now

### Option 1: Development Script (Recommended)
```bash
cd adijif/tools/webapp
python run_dev.py
```

### Option 2: Installed CLI Command
```bash
pip install -e ".[webapp]"
jifwebapp
```

### Option 3: Helper Scripts
```bash
cd adijif/tools/webapp
./scripts/start.sh
```

### Option 4: Manual
```bash
# Terminal 1 - Backend
python -m uvicorn adijif.tools.webapp.backend.main:app --reload --port 8000

# Terminal 2 - Frontend
cd adijif/tools/webapp/frontend
npm run dev
```

## Testing the Fix

You can verify the fix works by running:

```bash
# From the repository root
cd adijif/tools/webapp
python run_dev.py
```

This should start both the backend and frontend without any import errors.

## Why This Approach?

**Absolute imports** have several advantages:
1. ✅ Work regardless of how the module is imported
2. ✅ More explicit and easier to understand
3. ✅ Compatible with all Python tools (uvicorn, pytest, etc.)
4. ✅ No ambiguity about where imports come from

**Relative imports** are convenient but:
1. ❌ Require the module to be imported as part of a package
2. ❌ Can fail when running scripts directly
3. ❌ May not work with all development tools

## Additional Notes

- The original Streamlit app (`jiftools`) still works unchanged
- All functionality from the Streamlit app has been preserved
- Selenium tests are ready to run once the app is started
- Docker support is also available via `docker-compose up`

## Need Help?

See:
- [QUICKSTART.md](QUICKSTART.md) - Getting started in 5 minutes
- [README.md](README.md) - Full documentation
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development guide
- [MIGRATION.md](MIGRATION.md) - Differences from Streamlit version
