# Auto Author Backend Testing

This directory contains tests for the Auto Author backend API.

## Directory Structure

- `conftest.py`: Contains pytest fixtures used across tests
- `test_main.py`: Basic health check and root endpoint tests
- `test_api/`: Tests for API endpoints
  - `test_routes/`: Tests for specific route modules
- `test_models/`: Tests for data models (MongoDB/Beanie)
- `test_services/`: Tests for business logic and services

## Running Tests

Run all tests:
```bash
pytest
```

Run with coverage report:
```bash
pytest --cov=app
```

Run specific test file:
```bash
pytest tests/test_api/test_routes/test_users.py
```

Run tests by marker (e.g., only unit tests):
```bash
pytest -m "unit"
```

## Test Best Practices

1. **Test Independence**: Each test should be able to run independently
2. **Clear Naming**: Test names should clearly describe what they're testing
3. **Fixture Usage**: Use fixtures for test setup and teardown
4. **Mocking External Services**: Always mock external services like Clerk API
5. **Focus on Behavior**: Test what the code does, not implementation details

## Adding New Tests

When adding new endpoints or models, create corresponding test files:

1. For new API routes: `tests/test_api/test_routes/test_[route_name].py`
2. For new models: `tests/test_models/test_[model_name].py`
3. For new services: `tests/test_services/test_[service_name].py`
