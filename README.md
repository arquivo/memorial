# Memorial

> Arquivo.pt Memorial service to serve preserved web pages

Memorial is a Quart-based async web application that serves as a redirection service for preserved websites. It provides a user-friendly landing page with metadata extraction from archived pages, helping users access content preserved by [Arquivo.pt](https://arquivo.pt) (Portuguese Web Archive).

## Features

- 🚀 **Async/ASGI** - Built on Quart for true async concurrency
- 🌐 Automatic redirection to preserved versions of websites
- 📝 Metadata extraction from archived pages (titles, descriptions, keywords)
- 🎨 Customizable templates per domain
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
- `template`: Custom template name
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
pytest tests/test_basic.py

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
└── tests/               # Test suite
    └── test_basic.py    # Async test suite with pytest
```

## Docker Deployment

### Build and Run

```bash
# Build the Docker image
docker build -t memorial .

# Run the container
docker run -p 127.0.0.1:8080:8080 memorial

# Run with custom configuration
docker run -p 8080:8080 -v /path/to/config.py:/app/config.py memorial
```

### Docker Compose (Optional)

Create a `docker-compose.yml`:
```yaml
version: '3.8'
services:
  memorial:
    build: .
    ports:
      - "8080:8080"
    environment:
      - MEMORIAL_CONFIGURATION=/app/custom_config.py
    volumes:
      - ./custom_config.py:/app/custom_config.py
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## About Arquivo.pt

[Arquivo.pt](https://arquivo.pt) is the Portuguese web archive, preserving information published on the web since the mid-1990s. It provides full-text search over historical websites and supports research and access to web heritage.

## Support

For issues and questions:
- 🐛 [Issue Tracker](https://github.com/arquivo/memorial/issues)
- 📧 Email: arquivo@fccn.pt
- 🌐 Website: [arquivo.pt](https://arquivo.pt)

