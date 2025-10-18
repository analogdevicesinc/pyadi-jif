# Dropdown Troubleshooting Guide

## Issue: Dropdowns Not Working

If dropdowns in the PyADI-JIF web app aren't opening or selecting items, follow this guide to diagnose and fix the issue.

## Quick Diagnosis

### Step 1: Test with Static Data

Navigate to the **Dropdown Test** page (added to the sidebar) to verify Material-UI Select components work with static data.

**If dropdowns work on the test page but not on other pages**, the issue is with **API data loading**, not the dropdown components themselves.

## Common Causes & Fixes

### 1. Backend API Not Running

**Symptoms:**
- Dropdowns appear but are empty
- No converter/clock options visible
- Console shows network errors

**Check:**
```bash
# Verify backend is running
curl http://localhost:8000/health

# Should return: {"status":"healthy"}
```

**Fix:**
```bash
# Start the backend
python adijif/tools/webapp/run_dev.py

# OR manually
python -m uvicorn adijif.tools.webapp.backend.main:app --reload --port 8000
```

### 2. CORS Issues

**Symptoms:**
- Console shows CORS errors
- API requests fail with "Access-Control-Allow-Origin" errors

**Check:**
Open browser Developer Tools (F12) → Console tab, look for CORS errors.

**Fix:**
Edit `backend/main.py` and ensure your frontend origin is allowed:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",  # Vite dev server
        # Add your origin here if different
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. API Base URL Misconfigured

**Symptoms:**
- Network requests go to wrong URL
- 404 errors in console

**Check:**
Frontend `.env` file:
```bash
cat adijif/tools/webapp/frontend/.env
```

**Fix:**
Ensure `.env` contains:
```
VITE_API_BASE_URL=http://localhost:8000/api
```

Restart the frontend after changing `.env`:
```bash
cd adijif/tools/webapp/frontend
npm run dev
```

### 4. TanStack Query Not Fetching Data

**Symptoms:**
- No network errors
- Dropdowns empty but no console errors

**Check:**
Open React DevTools → Components → find the page component → check the `useQuery` hooks.

**Debug:**
Add console logging to see if data is fetched:

Edit `frontend/src/pages/JESDModeSelector.tsx`:
```typescript
const { data: supportedParts } = useQuery({
  queryKey: ['supportedConverters'],
  queryFn: async () => {
    const response = await converterApi.getSupportedConverters()
    console.log('Fetched converters:', response.data)  // Add this
    return response.data
  },
})
```

### 5. PyADI-JIF Not Installed

**Symptoms:**
- Backend starts but API endpoints return errors
- 500 Internal Server Error responses

**Check:**
```bash
python -c "import adijif; print(adijif.__version__)"
```

**Fix:**
```bash
pip install -e ".[cplex,draw]"
# OR
pip install pyadi-jif[cplex,draw]
```

## Testing Checklist

Use this checklist to systematically diagnose the issue:

- [ ] **Backend is running** - `curl http://localhost:8000/health` returns `{"status":"healthy"}`
- [ ] **Frontend is running** - Can access http://localhost:3000
- [ ] **API endpoint works** - `curl http://localhost:8000/api/converters/supported` returns JSON array
- [ ] **No CORS errors** - Check browser console (F12)
- [ ] **Dropdown Test page works** - Go to http://localhost:3000/dropdown-test
- [ ] **React DevTools installed** - Helpful for debugging React state

## Detailed Debugging Steps

### 1. Check API Response

```bash
# Test converter endpoint
curl -v http://localhost:8000/api/converters/supported

# Expected response:
# ["ad9680", "ad9144", "ad9081", ...]
```

### 2. Check Browser Network Tab

1. Open Developer Tools (F12)
2. Go to Network tab
3. Reload the JESD Mode Selector page
4. Look for request to `/api/converters/supported`
5. Check:
   - Status code (should be 200)
   - Response data (should be array of converter names)
   - Response headers (should include CORS headers)

### 3. Check React Query State

Using React DevTools:

1. Install React DevTools browser extension
2. Open DevTools → Components tab
3. Find `JESDModeSelector` component
4. Look at hooks → `useQuery`
5. Check:
   - `data`: Should contain array of converters
   - `isLoading`: Should be `false` after load
   - `error`: Should be `null`

### 4. Test Material-UI Select Directly

Create a minimal test:

```typescript
// In any page component
const [test, setTest] = useState('')

return (
  <FormControl>
    <InputLabel>Test</InputLabel>
    <Select value={test} onChange={(e) => setTest(e.target.value)}>
      <MenuItem value="a">Option A</MenuItem>
      <MenuItem value="b">Option B</MenuItem>
    </Select>
  </FormControl>
)
```

If this works, the issue is definitely with data loading, not MUI components.

## Still Not Working?

### Enable Debug Mode

Add this to `frontend/src/api/client.ts`:

```typescript
// Add request interceptor for debugging
apiClient.interceptors.request.use((config) => {
  console.log('API Request:', config.method?.toUpperCase(), config.url)
  return config
})

// Add response interceptor for debugging
apiClient.interceptors.response.use(
  (response) => {
    console.log('API Response:', response.status, response.data)
    return response
  },
  (error) => {
    console.error('API Error:', error.response?.status, error.message)
    return Promise.reject(error)
  }
)
```

### Check for JavaScript Errors

1. Open DevTools Console
2. Look for any red errors
3. Common issues:
   - `Cannot read property 'map' of undefined` - Data not loaded yet
   - `Network Error` - Backend not accessible
   - `CORS policy` - CORS not configured

### Verify Package Versions

```bash
# Frontend
cd adijif/tools/webapp/frontend
npm list react @mui/material @tanstack/react-query

# Should see compatible versions
# React: 18.x
# MUI: 5.x
# TanStack Query: 5.x
```

## Working Example

Here's a confirmed working Select component from the Dropdown Test page:

```typescript
const [selectedPart, setSelectedPart] = useState('')
const testConverters = ['ad9680', 'ad9144', 'ad9081']

<FormControl fullWidth>
  <InputLabel>Select a Part</InputLabel>
  <Select
    value={selectedPart}
    label="Select a Part"
    onChange={(e) => setSelectedPart(e.target.value)}
  >
    {testConverters.map((part) => (
      <MenuItem key={part} value={part}>
        {part.toUpperCase()}
      </MenuItem>
    ))}
  </Select>
</FormControl>
```

## Next Steps

If you've gone through all these steps and dropdowns still don't work:

1. Check the browser console for errors
2. Share the console output when reporting the issue
3. Share the network tab showing the API request/response
4. Note which page/dropdown specifically isn't working

## Quick Fixes Summary

| Issue | Quick Fix |
|-------|-----------|
| Backend not running | `python run_dev.py` |
| CORS errors | Update `backend/main.py` allowed origins |
| API URL wrong | Check `frontend/.env` file |
| PyADI-JIF not installed | `pip install -e ".[cplex,draw]"` |
| Empty dropdowns | Check API returns data: `curl http://localhost:8000/api/converters/supported` |

## Selenium Test

Run the automated test to verify dropdowns:

```bash
cd adijif/tools/webapp/tests
pytest test_dropdown_functionality.py -v
```

This will test:
- Dropdown opens when clicked
- Options are visible
- Selections work
- No JavaScript errors occur
