# FastAPI Application - Auto Author Backend

This project is a FastAPI application designed to provide a robust backend for the Auto Author application. It is structured to facilitate easy development and maintenance.

## Prerequisites

- Python 3.13+
- uv (Python package manager) - Install with: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- MongoDB

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── endpoints/
│   │   │   ├── __init__.py
│   │   │   └── router.py
│   │   └── dependencies.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── security.py
│   ├── db/
│   │   ├── __init__.py
│   │   └── database.py
│   ├── models/
│   │   └── __init__.py
│   └── schemas/
│       └── __init__.py
├── requirements.txt
└── README.md
```

## Installation

To get started with this project, clone the repository and set up the virtual environment:

1. Create and activate virtual environment:
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
uv pip install -r requirements.txt
```

3. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Fill in required values (MongoDB URI, API keys, etc.)

## Usage

To run the FastAPI application, execute the following command:

```bash
uv run uvicorn app.main:app --reload
```

This will start the server at `http://127.0.0.1:8000`. You can access the interactive API documentation at `http://127.0.0.1:8000/docs`.

## Development

### Running Tests
```bash
uv run pytest                          # Run all tests
uv run pytest -v                       # Verbose output
uv run pytest -k "test_name"           # Run specific test
uv run pytest --cov=app               # Run with coverage
uv run pytest tests/test_file.py      # Run specific test file
```

### Code Formatting
```bash
uv run black .                         # Format all Python files
uv run ruff check .                    # Run linting
uv run ruff format .                   # Format with ruff
```

### Package Management

This project uses `uv` as the package manager. Always use `uv` commands within the virtual environment:

- Install new package: `uv pip install package-name`
- Update requirements: `uv pip freeze > requirements.txt`
- Run any command: `uv run command-name`

### Quick Validation Scripts
```bash
uv run python quick_validate.py        # Validate implementation
uv run python test_toc_transactions.py # Test TOC transactions
```

## API Documentation

For detailed API documentation, please refer to:

- [API Authentication Endpoints](../docs/api-auth-endpoints.md) - Authentication API documentation
- [API Profile Endpoints](../docs/api-profile-endpoints.md) - Profile management API documentation
- [API Book Endpoints](../docs/api-book-endpoints.md) - Book management API documentation
- [API Chapter Tabs](../docs/api-chapter-tabs.md) - Chapter tabs API documentation
- [API Question Endpoints](../docs/api-question-endpoints.md) - Question system API documentation

These documents provide comprehensive information about available endpoints, request/response formats, and authentication requirements.

## Key Features

- **Transaction-based TOC Updates**: Atomic operations for Table of Contents modifications
- **Optimistic Locking**: Version control to prevent concurrent modification conflicts
- **Audit Logging**: Comprehensive activity tracking for all operations
- **Chapter Tab Management**: Advanced chapter organization with tab states
- **Question System**: Interview-style question generation and management

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue for any suggestions or improvements.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.