# Memorial

> Arquivo.pt Memorial service to serve preserved web pages

Memorial is a Quart-based async web application that serves as a redirection service for preserved websites. It provides a user-friendly landing page with metadata extraction from archived pages, helping users access content preserved by [Arquivo.pt](https://arquivo.pt) (Portuguese Web Archive).

## Features

- 🚀 **Async/ASGI** - Built on Quart for true async concurrency
- 🌐 Automatic redirection to preserved versions of websites
- 📝 Metadata extraction from archived pages (titles, descriptions, keywords)
- 🎨 Customizable UI changes per domain
- 🌍 Multi-language support (Portuguese/English)
- 🐳 Docker support for easy deployment
- ✅ Comprehensive test suite with async support

## Requirements

- Python 3.8 or higher
- pip (Python package installer)

## Installation

### Quick Start

1. **Clone the repository**
```bash
git clone https://github.com/arquivo/memorial.git
cd memorial
```

2. **Install dependencies** (venv auto-created)
```bash
# For development (recommended)
make install-dev

# Or for production only
make install
```

3. **Verify installation**
```bash
# Run all CI checks
make ci
```

That's it! The Makefile handles virtual environment creation automatically.

## Usage

### Running Locally

**Using Hypercorn (Production-like):**
```bash
hypercorn memorial:app --bind 0.0.0.0:8080
# or with config file
hypercorn -c hypercorn.toml memorial:app
```

**Using Quart development server:**
```bash
python memorial.py
```

The application will be available at `http://localhost:8080`

### Configuration

Configure archived sites in [`config.py`](config.py). Each domain can have:

- `version`: Specific timestamp for the archived version
- `message_pt`/`message_en`: Custom messages in Portuguese/English
- `logo`: URL or path to custom logo
- `button_color`: Custom button color
- `default_language`: Default language (`pt` or `en`)
- `link_to_noFrame`: Whether to link to noFrame version
- `status_code`: HTTP status code to return (default: `200`, can be `502` for Bad Gateway, etc.)

**Environment Variables:**
- `MEMORIAL_CONFIGURATION`: Path to custom configuration file
- `WAYBACK_SERVER`: Wayback server URL (default: `https://arquivo.pt/wayback/`)
- `WAYBACK_NOFRAME_SERVER`: NoFrame server URL (default: `https://arquivo.pt/noFrame/replay/`)
- `WAYBACK_REQUEST_TIMEOUT`: Request timeout in seconds (default: 3)

## Development

### Setup for Development

The Makefile automatically creates a virtual environment when needed. Just run:

```bash
# Install development dependencies (venv auto-created)
make install-dev
```

This command will:
1. Create `./venv/` if it doesn't exist
2. Install all development tools (pytest, black, ruff, mypy, etc.)

**That's it!** Now you can use all development commands.

### Quick Commands with Makefile

```bash
# First time setup
make install-dev     # Auto-creates venv and installs dev dependencies

# Run all CI checks (format, lint, test)
make ci

# Run tests
make test            # Run tests only
make test-cov        # Tests with coverage report

# Code quality
make format          # Auto-format code with black
make lint            # Check code with ruff
make check           # Run all quality checks

# Run application
make run             # Production-like (uWSGI)
make run-dev         # Development server

# Cleanup
make clean           # Remove build artifacts
make clean-all       # Remove venv and build artifacts

# Help
make help            # Show all available commands
```

**Note:** The virtual environment is created automatically when you run any make target. You don't need to manually create or activate it!

### Running Tests

```bash
# Run all tests
pytest
# or
make test

# Run with coverage report
pytest --cov=. --cov-report=html
# or
make test-cov

# Run specific test file
pytest tests/test_favicon.py                    # Favicon endpoint tests
pytest tests/test_site_image.py                 # Site image endpoint tests
pytest tests/test_normalization_and_params.py   # Normalization & query params
pytest tests/test_url_construction.py           # URL helpers
pytest tests/test_edge_cases.py                 # Edge cases
pytest tests/test_redirect_core.py              # Core redirect logic

# Run tests matching a pattern
pytest -k favicon -v     # Run all tests matching "favicon"

# Note: Tests use pytest with async support (pytest-asyncio)
```

### Code Quality

```bash
# Format code with Black
black .
# or
make format

# Lint code with Ruff
ruff check .
# or
make lint

# Auto-fix linting issues
ruff check --fix .

# Run all quality checks
make check

# Type checking (optional)
mypy memorial.py
```

### Project Structure

```
memorial/
├── memorial.py           # Main Quart async application
├── config.py            # Site configuration
├── pyproject.toml       # Project metadata and dependencies
├── setup.py             # Backwards compatibility setup file
├── Makefile             # Development automation tasks
├── hypercorn.toml       # Hypercorn ASGI server configuration
├── Dockerfile           # Docker container definition
├── static/              # Static assets (CSS, images, robots.txt)
├── templates/           # Jinja2 templates
└── tests/               # Test suite (76 async tests, 98% coverage)
    ├── conftest.py                      # Shared fixtures and helpers
    ├── test_favicon.py                  # Favicon endpoint tests (4 tests)
    ├── test_site_image.py               # Site image endpoint tests (11 tests)
    ├── test_normalization_and_params.py # WWW normalization & query params (8 tests)
    ├── test_url_construction.py         # URL helpers and construction (9 tests)
    ├── test_edge_cases.py               # Edge cases and error conditions (9 tests)
    ├── test_redirect_core.py            # Core redirect functionality (35 tests)
    └── test_basic.py.archive            # Original monolithic test file (archived)
```

### Test Organization

The test suite has been split into focused, manageable files organized by feature:

**Shared Configuration** (`conftest.py`)
- Mock setup for httpx.AsyncClient
- Pytest fixtures (client fixture)
- Helper functions (request_host, get_title, get_metadata, with_test_config)

**Feature-Specific Test Files**
- `test_favicon.py` - /favicon.ico endpoint with version handling and www normalization
- `test_site_image.py` - /memorial-site-image endpoint with custom logos and directory lookups  
- `test_normalization_and_params.py` - WWW prefix handling and query parameter preservation
- `test_url_construction.py` - URL construction helpers and Wayback URL generation
- `test_edge_cases.py` - Error conditions, timeouts, malformed input, multi-site configs
- `test_redirect_core.py` - Core redirect routing, metadata extraction, configuration precedence

## Docker Deployment

### Using Docker Compose (Recommended)

```bash
# Build and start the service
docker compose build && docker compose up

# Or run in background
docker compose up -d

# Stop the service
docker compose stop
```

### Build and Run with Docker

```bash
# Build the Docker image
docker build -t memorial .

# Run the container
docker run -p 127.0.0.1:8080:8080 memorial

# Run with custom configuration
docker run -p 8080:8080 -v /path/to/config.py:/app/config.py memorial
```

### Testing

Test the memorial service with a site configured in `config.py`:

```bash
# Using curl with --resolve to test without DNS
curl -v --resolve senior3045.ipportalegre.pt:80:127.0.0.1 http://senior3045.ipportalegre.pt

# Or test directly with localhost
curl -H "Host: senior3045.ipportalegre.pt" http://127.0.0.1:8080

# Check specific paths
curl -v --resolve senior3045.ipportalegre.pt:80:127.0.0.1 http://senior3045.ipportalegre.pt/about
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## About Arquivo.pt

[Arquivo.pt](https://arquivo.pt) is the Portuguese web archive, preserving information published on the web since the mid-1990s. It provides full-text search over historical websites and supports research and access to web heritage.

## Support

For issues and questions:
- 🐛 [Issue Tracker](https://github.com/arquivo/pwa-technologies/issues/new?template=BLANK_ISSUE&labels=Component-Frontend-Memorial)
- 🌐 Website: [arquivo.pt](https://arquivo.pt)

