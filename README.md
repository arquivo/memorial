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

### Maintenance Pages (502/503/504 Status Codes)

When a site is configured with a 502, 503, or 504 status code (indicating the site is unavailable), Memorial automatically looks for domain-specific maintenance page templates in the `templates/maintenance/` folder.

#### Template Lookup Strategy

For a request to a domain, Memorial follows this hierarchical lookup:

1. **Subdomain template**: For `sub.example.com`, try `sub_example_com.html`
2. **Second-level domain template**: For `sub.example.com`, try `example_com.html`
3. **Partial domain templates**: For multi-level domains, progressively shorter domain names
4. **Default template**: Fall back to `redirect_default.html` if no specific template found

#### Creating Custom Maintenance Templates

1. Create an HTML template file in `templates/maintenance/` folder
2. Name it according to your domain (dots replaced with underscores), e.g.:
   - `example_com.html` for `example.com`
   - `subdomain_example_com.html` for `subdomain.example.com`
   - `api_example_com.html` for `api.example.com`

3. Your template can use the same variables as regular templates:
   - `{{ message_pt }}` / `{{ message_en }}` - Custom domain-specific messages
   - `{{ redirect_url }}` - URL to the archived version
   - `{{ button_message_pt }}` / `{{ button_message_en }}` - Button text
   - And other standard template variables

#### Example Maintenance Template

```html
<!DOCTYPE html>
<html>
<head>
    <title>Site Maintenance</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
    <div class="maintenance-notice">
        <h2>Site Under Maintenance</h2>
        <p>{{ message_pt if default_language == 'pt' else message_en }}</p>
        <p>{{ message_before_button_pt if default_language == 'pt' else message_before_button_en }}</p>
        <a href="{{ redirect_url }}" class="btn">
            {{ button_message_pt if default_language == 'pt' else button_message_en }}
        </a>
    </div>
</body>
</html>
```

#### Configuration Example

In `config.py`, configure a site with 502 status:

```python
ARCHIVE_CONFIG = {
    "example.com": {
        "status_code": 502,  # Bad Gateway
        "version": "20230101000000",
        "message_pt": "O site está em manutenção",
        "message_en": "The site is under maintenance",
    }
}
```

The application will automatically serve `templates/maintenance/example_com.html` for requests to this domain, with a 502 status code.

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

### Test Pages

To double check if everything is ok you can use this procedure during local development.

Edit your `/etc/hosts` file.

```
127.0.0.1 umic.pt
127.0.0.1 english.umic.pt
127.0.0.1 www.sg.pcm.gov.pt
127.0.0.1 oe2020.gov.pt
127.0.0.1 example.com
127.0.0.1 educast.fccn.pt
127.0.0.1 xpto.fccn.pt
127.0.0.1 www.fccn.pt
```

Start the development mode of this application:
```bash
make run-dev
```

Open your browser on those pages use an incognito window because the browser could have SSL connection cached:

- http://umic.pt:5000
- http://english.umic.pt:5000
- http://www.sg.pcm.gov.pt:5000
- http://oe2020.gov.pt:5000
- http://example.com:5000
- http://educast.fccn.pt:5000
- http://xpto.fccn.pt:5000
- http://www.fccn.pt:5000


## Metadata Extraction

Memorial includes comprehensive utilities to extract and export metadata from archived sites on Arquivo.pt. This is useful for:
- Testing metadata availability before adding a site to config
- Bulk extracting metadata for all configured sites
- Generating metadata exports in TSV format with titles and metadata

### Files

- **`data_extractor.py`** - Core library module with reusable functions
- **`extract_data_for_sites.py`** - Command-line tool to extract and export data for all configured or individual archived sites

### Quick Start

#### Extract for all configured sites and export to TSV:

```bash
python extract_data_for_sites.py
```

This creates a `data.tsv` file with three columns:
- Column 1: Site hostname (e.g., `example.com`)
- Column 2: Page title
- Column 3: Extracted metadata tags (semicolon-separated)

#### Extract for a specific site:

```bash
# Display data on screen
python extract_data_for_sites.py --site example.com --version 20230101120000

# Export to TSV file
python extract_data_for_sites.py --site example.com --version 20230101120000 --output my_site.tsv

# Custom timeout for slow sites
python extract_data_for_sites.py --site example.com --version 20230101120000 --timeout 30
```

#### Extract all configured sites with options:

```bash
# Custom output file
python extract_data_for_sites.py --output my_data.tsv

# Longer timeout for slow sites
python extract_data_for_sites.py --timeout 30 --output results.tsv

# Verbose logging
python extract_data_for_sites.py --verbose

# Custom wayback server
python extract_data_for_sites.py --wayback-server https://web.archive.org/web/
```

### Using as a Python Library

#### Extract data for a single site:

```python
from data_extractor import extract_site_metadata

# Extract title and metadata for a specific site and version
title, metadata = extract_site_metadata(
    site="example.com",
    version="20200117175504"
)

print(f"Title: {title}")
print(f"Metadata tags: {metadata}")
# Output: 
# Title: Example Site
# Metadata tags: ['<meta name="description" content="..."/>', ...]
```

#### Extract and display results programmatically:

```python
from data_extractor import extract_site_metadata

title, metadata = extract_site_metadata("example.com", "20230101120000", timeout=15)

print(f"✓ Site Title: {title}")
if metadata:
    print(f"✓ Found {len(metadata)} metadata tags:")
    for tag in metadata:
        print(f"  - {tag}")
else:
    print("✗ No metadata found")
```

#### Extract for all configured sites:

```python
from config import ARCHIVE_CONFIG
from data_extractor import extract_metadata_for_configured_sites, export_to_tsv

# Extract titles and metadata for all sites in config
results = extract_metadata_for_configured_sites(ARCHIVE_CONFIG)

# Export to TSV
export_to_tsv(results, "data.tsv")

# Or process results programmatically
for site, (title, metadata) in results.items():
    print(f"{site}: '{title}' - {len(metadata)} metadata tags")
```

### API Reference

#### `extract_site_metadata(site, version, wayback_noframe_server, timeout)`

Extract title and metadata for a specific archived site and version.

**Parameters:**
- `site` (str): Domain name (e.g., "example.com")
- `version` (str): Version timestamp (e.g., "20200117175504")
- `wayback_noframe_server` (str): Base Arquivo.pt URL (default: `https://arquivo.pt/noFrame/replay/`)
- `timeout` (int): Request timeout in seconds (default: 30)

**Returns:** `tuple[str, list[str]]` - (title, metadata_list) where metadata_list contains metadata tag strings

**Example:**
```python
title, metadata = extract_site_metadata("senior3045.ipportalegre.pt", "20200117175504")
```

#### `extract_metadata_for_configured_sites(archive_config, wayback_noframe_server, timeout)`

Extract title and metadata for all sites in ARCHIVE_CONFIG.

**Parameters:**
- `archive_config` (dict): The ARCHIVE_CONFIG dictionary from config.py
- `wayback_noframe_server` (str): Base Arquivo.pt URL (default: `https://arquivo.pt/noFrame/replay/`)
- `timeout` (int): Request timeout per site (default: 30)

**Returns:** `dict[str, tuple[str, list[str]]]` - Dict mapping sites to (title, metadata_list) tuples

**Example:**
```python
from config import ARCHIVE_CONFIG
results = extract_metadata_for_configured_sites(ARCHIVE_CONFIG)
```

#### `export_to_tsv(results, output_file)`

Export extracted data to a TSV file with three columns: site, title, metadata.

**Parameters:**
- `results` (dict[str, tuple[str, list[str]]]): Dictionary from `extract_metadata_for_configured_sites()`
- `output_file` (str): Path to output TSV file

**Returns:** `None`

**Example:**
```python
export_to_tsv(results, "data.tsv")
```

#### `extract_metadata_from_html(html_content)`

Extract title and metadata tags from HTML content.

**Parameters:**
- `html_content` (bytes): HTML content to parse

**Returns:** `tuple[str, list[str]]` - (title, metadata_list)

#### `get_archived_page_content(wayback_url, timeout)`

Fetch content from an archived page on Arquivo.pt.

**Parameters:**
- `wayback_url` (str): Full URL to archived page
- `timeout` (int): Request timeout in seconds (default: 30)

**Returns:** `bytes | None` - HTML content or None if retrieval fails

### TSV File Format

The exported TSV file has the following structure:

```
Site	Title	Metadata
example.com	Example Site Title	<meta name="description" content="Example site"/>; <meta name="keywords" content="test"/>
newsite.com	New Site	<meta name="author" content="Author Name"/>
```

Features:
- **Tab-separated** for easy import into spreadsheets
- **Semicolon-separated** metadata tags within each row
- **UTF-8 encoded** for international characters
- Special characters (tabs, newlines) are escaped

### Command-Line Options

```bash
python extract_data_for_sites.py --help

# Key options:
#   --site SITE                 Extract specific site (requires --version)
#   --version VERSION           Timestamp for archived version
#   --output OUTPUT, -o OUTPUT  Output TSV file (default: data.tsv)
#   --timeout TIMEOUT, -t       Request timeout in seconds (default: 30)
#   --wayback-server URL, -w    Custom Arquivo.pt URL
#   --config CONFIG, -c         Custom config.py path
#   --verbose, -vv              Enable verbose logging
```

### Workflow: Adding a New Site

1. **Test metadata extraction** before adding to config:
```bash
python extract_data_for_sites.py --site newsite.com --version 20230101120000
```

2. **Review the extracted title and metadata** - if useful, proceed to step 3

3. **Add site to `config.py`:**
```python
ARCHIVE_CONFIG = {
    # ... existing sites ...
    "newsite.com": {
        "version": "20230101120000",
        "message_pt": "Custom Portuguese message",
    }
}
```

4. **Extract data for all sites:**
```bash
python extract_data_for_sites.py --output data_updated.tsv
```

### Error Handling

The utilities handle various error conditions gracefully:

- **Network errors**: Logs warning and returns empty metadata list
- **Timeout**: Falls back gracefully, customizable with `--timeout`
- **Invalid HTML**: BeautifulSoup handles malformed HTML
- **Malformed tags**: Unclosed tags are automatically corrected

### Logging

Enable verbose logging to see what's happening:

```bash
python extract_data_for_sites.py --verbose
```

Or in Python code:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Considerations

- Default timeout is 30 seconds per site
- For large numbers of sites, extraction can take time
- Adjust `--timeout` based on your network conditions
- Arquivo.pt may rate-limit requests - adjust accordingly

### Troubleshooting

**No metadata extracted for a site:**
1. Check if the site's version is correct in config.py
2. Verify the site exists on Arquivo.pt: `https://arquivo.pt/noFrame/replay/VERSION/site.com`
3. Run with `--verbose` flag to see detailed logs
4. Increase `--timeout` if the site is slow to respond

**TSV file not created:**
1. Check file permissions in the output directory
2. Ensure the output path is valid
3. Check logs for specific error message

### Integration with the Web App

The Memorial web application (memorial.py) can use metadata extracted by this module:

1. Use `extract_metadata_for_configured_sites()` during deployment to pre-compute data
2. Store results in cache for faster page loads
3. Update metadata periodically using the CLI tool in a cron job

### Project Structure

```
memorial/
├── memorial.py           # Main Quart async application
├── config.py            # Site configuration
├── data_extractor.py # Data extraction utility library
├── extract_data_for_sites.py  # CLI tool for metadata extraction
├── example_metadata_extraction.py # Examples demonstrating metadata utilities
├── pyproject.toml       # Project metadata and dependencies
├── setup.py             # Backwards compatibility setup file
├── Makefile             # Development automation tasks
├── hypercorn.toml       # Hypercorn ASGI server configuration
├── Dockerfile           # Docker container definition
├── README.md            # This file
├── METADATA_EXTRACTION.md # Detailed metadata extraction documentation
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

