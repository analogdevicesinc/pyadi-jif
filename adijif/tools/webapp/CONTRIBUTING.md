# Contributing to PyADI-JIF Tools Explorer Web App

Thank you for your interest in contributing! This guide will help you get started.

## Development Setup

### Prerequisites
- Python 3.9+
- Node.js 18+
- Git

### Initial Setup

1. Clone the repository:
```bash
git clone https://github.com/analogdevicesinc/pyadi-jif.git
cd pyadi-jif
```

2. Install Python dependencies:
```bash
pip install -e ".[webapp,webapp-tests,cplex,draw]"
```

3. Install frontend dependencies:
```bash
cd adijif/tools/webapp/frontend
npm install
```

## Development Workflow

### Backend Development

1. Start the FastAPI server:
```bash
cd adijif/tools/webapp/backend
uvicorn main:app --reload --port 8000
```

2. Visit [http://localhost:8000/docs](http://localhost:8000/docs) for API documentation

3. Make changes to API endpoints in `backend/api/`

4. Test API endpoints using the Swagger UI or curl

### Frontend Development

1. Start the development server:
```bash
cd adijif/tools/webapp/frontend
npm run dev
```

2. Visit [http://localhost:3000](http://localhost:3000)

3. Make changes to React components in `frontend/src/`

4. Hot reload will automatically update the browser

## Code Style

### Backend (Python)
- Follow PEP 8
- Use type hints
- Use docstrings for all functions/classes
- Run linter before committing:
```bash
ruff check .
ruff format .
```

### Frontend (TypeScript/React)
- Use TypeScript for all new files
- Follow React best practices
- Use functional components with hooks
- Run linter before committing:
```bash
npm run lint
```

## Testing

### Adding Backend Tests
Create API tests in `backend/tests/`:
```python
def test_new_endpoint(client):
    response = client.get("/api/new-endpoint")
    assert response.status_code == 200
```

### Adding Frontend Tests
Add component tests in `frontend/src/`:
```typescript
import { render, screen } from '@testing-library/react';
import MyComponent from './MyComponent';

test('renders correctly', () => {
  render(<MyComponent />);
  expect(screen.getByText('Hello')).toBeInTheDocument();
});
```

### Adding Selenium Tests
Add E2E tests in `tests/`:
```python
def test_new_feature(driver, base_url):
    driver.get(f"{base_url}/page")
    element = driver.find_element(By.ID, "my-element")
    assert element.text == "Expected Text"
```

Run all tests:
```bash
cd tests
pytest -v
```

## Adding New Features

### Adding a New API Endpoint

1. Define the endpoint in `backend/api/`:
```python
@router.get("/new-endpoint")
async def get_new_data() -> dict:
    return {"data": "value"}
```

2. Add the API client method in `frontend/src/api/client.ts`:
```typescript
export const api = {
  getNewData: () => apiClient.get('/new-endpoint'),
}
```

3. Use in React component:
```typescript
const { data } = useQuery({
  queryKey: ['newData'],
  queryFn: api.getNewData,
})
```

### Adding a New Page

1. Create component in `frontend/src/pages/`:
```typescript
export default function NewPage() {
  return <div>New Page</div>
}
```

2. Add route in `App.tsx`:
```typescript
const pages = [
  { name: 'New Page', path: '/new-page', component: NewPage },
  // ...
]
```

3. Add Selenium tests in `tests/test_new_page.py`

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `pytest -v`
5. Commit with descriptive messages
6. Push to your fork
7. Create a pull request

### PR Checklist
- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] All tests pass
- [ ] No TypeScript/ESLint errors
- [ ] Tested locally

## Common Tasks

### Adding a New Converter
Backend is already set up to discover converters automatically from `adijif`.

### Adding a New Clock
Backend is already set up to discover clocks automatically from `adijif`.

### Updating Material-UI Theme
Edit `frontend/src/theme.ts`:
```typescript
const theme = createTheme({
  palette: {
    primary: {
      main: '#your-color',
    },
  },
})
```

### Adding Environment Variables

Backend (`.env`):
```
NEW_VARIABLE=value
```

Frontend (`.env`):
```
VITE_NEW_VARIABLE=value
```

Access in code:
```typescript
const value = import.meta.env.VITE_NEW_VARIABLE
```

## Debugging

### Backend Debugging
Use FastAPI's built-in debugging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Frontend Debugging
Use React DevTools browser extension and console.log:
```typescript
console.log('Debug:', data)
```

### Network Debugging
Use browser DevTools Network tab to inspect API calls

## Getting Help

- Check existing issues
- Read the documentation
- Ask in discussions
- Contact maintainers

## Code of Conduct

Be respectful and constructive in all interactions.
