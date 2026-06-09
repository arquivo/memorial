"""Memorial - Arquivo.pt Memorial Service.

A Quart web application that serves as a redirection service for preserved websites.
Provides a user-friendly landing page with metadata extraction from archived pages,
helping users access content preserved by Arquivo.pt (Portuguese Web Archive).
"""

import logging
import os

import httpx
from bs4 import BeautifulSoup
from quart import Quart, render_template, request, send_from_directory
from quart import redirect as quart_redirect

from data_extractor import (
    extract_metadata_from_html,
)

try:
    import setproctitle

    setproctitle.setproctitle("memorial-worker")
except ImportError:
    pass  # setproctitle is optional

# Initialize Quart application
app = Quart(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration from config.py module
app.config.from_object("config")

# Allow overriding configuration via environment variable
# Usage: export MEMORIAL_CONFIGURATION=/path/to/custom_config.py
if "MEMORIAL_CONFIGURATION" in os.environ:
    app.config.from_envvar("MEMORIAL_CONFIGURATION")

# Configure port stripping for local development
# When enabled, strips port numbers from hostnames before config lookup
# This allows local development on non-standard ports (e.g., :8080)
# while using production config files without port specifications
if os.environ.get("MEMORIAL_STRIP_PORT", "").lower() in ("true", "1", "yes"):
    app.config["STRIP_PORT"] = True

# Default messages based on HTTP status code
# These are used when a site is not configured with custom messages
# Each status code has three message types:
# - message: Primary message displayed to the user
# - message_before_button: Message displayed before the redirect button
# - button_message: Text for the redirect button
DEFAULT_MESSAGES = {
    200: {
        "pt": {
            "message": "O site foi desactivado.",
            "message_before_button": 'O <a href="https://arquivo.pt/memorial" target="_blank">Memorial do Arquivo.pt</a> preservou o seu conteúdo.',
            "button_message": "Ver no Arquivo.pt",
        },
        "en": {
            "message": "The site has been disabled.",
            "message_before_button": '<a href="https://arquivo.pt/memorialen" target="_blank">Arquivo.pt Memorial</a> preserved its content.',
            "button_message": "Browse in Arquivo.pt",
        },
    },
    502: {
        "pt": {
            "message": "O site está temporariamente indisponível.",
            "message_before_button": 'O <a href="https://arquivo.pt/memorial" target="_blank">Memorial do Arquivo.pt</a> preservou o seu conteúdo.',
            "button_message": "Ver no Arquivo.pt",
        },
        "en": {
            "message": "The site is temporarily unavailable.",
            "message_before_button": '<a href="https://arquivo.pt/memorialen" target="_blank">Arquivo.pt Memorial</a> preserved its content.',
            "button_message": "Browse in Arquivo.pt",
        },
    },
}


async def fetch_redirect_url_content(redirect_url_home, redirect_url_path):
    """Fetch the content from the redirect URL asynchronously.

    Attempts to fetch the requested path from the Wayback Machine. If the path
    is not HTML content or fails, falls back to fetching the home page instead.

    Uses async HTTP requests for better performance and non-blocking I/O.

    Args:
        redirect_url_home: URL to the archived home page
        redirect_url_path: URL to the specific archived path requested

    Returns:
        httpx.Response: The HTTP response from the Wayback Machine

    Raises:
        httpx.TimeoutException: If the request times out
    """
    wayback_timeout = app.config.get("WAYBACK_REQUEST_TIMEOUT", 3)

    # Create async HTTP client with timeout configuration
    async with httpx.AsyncClient(follow_redirects=True, timeout=wayback_timeout) as client:
        try:
            # First, check if the specific path exists and is HTML
            # Use HEAD request to avoid downloading large files
            redirect_url_path_head = await client.head(redirect_url_path)

            # If path exists and is HTML content, fetch it
            if (
                redirect_url_path_head.status_code < 400
                and "content-type" in redirect_url_path_head.headers
                and redirect_url_path_head.headers["content-type"].startswith("text/html")
            ):
                return await client.get(redirect_url_path)
            else:
                # Non-HTML content (images, PDFs, etc.) - fall back to home page metadata
                return await client.get(redirect_url_home)
        except httpx.TimeoutException:
            # Re-raise timeout errors to be handled by caller
            raise
        except Exception:  # pylint: disable=broad-except
            # For any other error, fall back to home page
            return await client.get(redirect_url_home)


async def extract_metadata(redirect_url_home, redirect_url_path):
    """Extract metadata from the preserved page asynchronously.

    Fetches the archived page and extracts useful metadata including:
    - Page title
    - Meta tags (description, keywords, author)
    - Link tags (author, home, favicon, alternate)

    This metadata is used to populate the memorial landing page with
    information about the preserved site.

    Args:
        redirect_url_home: URL to the archived home page
        redirect_url_path: URL to the specific archived path

    Returns:
        tuple: (title, meta_list) where title is BeautifulSoup tag or None,
               and meta_list is a list of fixed metadata tag strings
    """
    meta_list = []
    try:
        # Fetch the archived page content asynchronously
        r = await fetch_redirect_url_content(redirect_url_home, redirect_url_path)

        # Parse HTML content and extract metadata using the shared utility
        meta_list = extract_metadata_from_html(r.content)

        # Extract page title
        soup = BeautifulSoup(r.content, "html.parser")
        title = soup.find("title")

        return title, meta_list
    except Exception as e:  # pylint: disable=broad-except
        # Log error but continue - metadata extraction is best effort
        logger.error(
            "Failed to extract metadata for %s: %s: %s",
            redirect_url_home,
            type(e).__name__,
            str(e) or "No error message",
            exc_info=True,
        )
        return None, meta_list


@app.route("/robots.txt")
async def robots():
    """Serve robots.txt file for web crawlers."""
    return await send_from_directory("static", "robots.txt")


def get_host_configuration(host: str) -> tuple[str, dict | None]:
    """Helper function to get site-specific configuration for a given host.

    This function normalizes the host by stripping "www." and optionally
    removing port numbers (if STRIP_PORT is enabled) before looking up the
    configuration in the ARCHIVE_CONFIG dictionary.

    Args:
        host: The original host from the request (e.g., "www.example.com:8080")

    Returns:
        tuple: (host, config) where host is the normalized host string,
               and config is the configuration dictionary for the host, or None if not found
    """
    # Optionally strip port number if STRIP_PORT is enabled
    if app.config.get("STRIP_PORT", False):
        host = host.split(":")[0]

    # Normalize host by stripping "www." only from the beginning
    if host.startswith("www."):
        host = host[4:]  # Remove first 4 characters ("www.")

    # Look up configuration for the normalized host
    return host, app.config["ARCHIVE_CONFIG"].get(host, None)


def get_wayback_noframe_server_url():
    """Helper function to get the Wayback noFrame server URL from configuration.

    This function retrieves the WAYBACK_NOFRAME_SERVER URL from the application
    configuration and ensures it ends with a slash (/) for consistent URL construction.

    Returns:
        str: The Wayback noFrame server URL, guaranteed to end with a slash
    """
    wayback_noframe_server_url = app.config.get("WAYBACK_NOFRAME_SERVER", "https://arquivo.pt/noFrame/replay/")
    if not wayback_noframe_server_url.endswith("/"):
        wayback_noframe_server_url += "/"
    return wayback_noframe_server_url


def get_maintenance_template(host: str) -> str:
    """Find the appropriate maintenance template for a given host.

    When status_code is 502 (Bad Gateway), this function attempts to find
    a custom maintenance page template specific to the domain. It follows
    a hierarchical search strategy:

    For example, for "some.example.com":
    1. Try some_example_com.html
    2. Try example_com.html
    3. Try to find the domain (e.g., com.html for multi-part domains)
    4. Fall back to redirect_default.html

    The host should already be normalized (www. prefix removed).

    Args:
        host: The normalized host name (e.g., "example.com" or "sub.example.com")

    Returns:
        str: The template filename to use (e.g., "maintenance/example_com.html" or "redirect_default.html")
    """
    maintenance_folder = app.config.get("MAINTENANCE_FOLDER", "maintenance")

    # Strip port number if present (e.g., "example.com:5000" -> "example.com")
    # Always strip port numbers for maintenance template lookup
    if ":" in host:
        host = host.split(":")[0]

    # Normalize host by stripping "www." only from the beginning
    if host.startswith("www."):
        host = host[4:]  # Remove first 4 characters ("www.")

    # Convert host to normalized form by replacing dots with underscores
    # e.g., "example.com" -> "example_com", "some.example.com" -> "some_example_com"
    host_normalized = host.replace(".", "_")

    # Try to find the template following the hierarchy
    templates_to_try = []

    # 1. Try the full host name (e.g., some_example_com.html)
    templates_to_try.append(f"{host_normalized}.html")

    # 2. For subdomains, try the second-level domain and above
    # e.g., for "some.example.com" -> try "example_com.html"
    parts = host.split(".")
    if len(parts) > 2:
        # Remove the first part and try again
        domain_without_subdomain = ".".join(parts[1:])
        templates_to_try.append(f"{domain_without_subdomain.replace('.', '_')}.html")

    # 3. For multi-level TLDs, try progressively shorter domain names
    # e.g., for "example.co.uk" -> try "example_co.html"
    if len(parts) > 2:
        for i in range(1, len(parts) - 1):
            partial_domain = ".".join(parts[i:])
            templates_to_try.append(f"{partial_domain.replace('.', '_')}.html")

    # Try each template in order
    try:
        if os.path.isdir(f"templates/{maintenance_folder}"):
            existing_files = os.listdir(f"templates/{maintenance_folder}")
            for template_candidate in templates_to_try:
                if template_candidate in existing_files:
                    # Return path with folder prefix for Jinja2 to locate
                    # e.g., "maintenance/example_com.html" will look for templates/maintenance/example_com.html
                    template_path = f"{maintenance_folder}/{template_candidate}"
                    logger.info("Found maintenance template: %s for host: %s", template_path, host)
                    return template_path
    except Exception as e:  # pylint: disable=broad-except
        logger.error("Error checking maintenance folder: %s", str(e))

    # Fall back to default template
    logger.info("No maintenance template found for host: %s, using default", host)
    return "redirect_default.html"


# favicon.ico redirect to archived version
# to http://arquivo.pt/noFrame/replay/<host>/favicon.ico
@app.route("/favicon.ico")
async def favicon():
    """Redirect requests for favicon.ico to the archived version."""
    host, host_config = get_host_configuration(request.host)

    version = None
    favicon_url = None
    if host_config:
        version = host_config.get("version", None)
        favicon_url = host_config.get("favicon", None)

    wayback_noframe_server_url = get_wayback_noframe_server_url()
    favicon_url = wayback_noframe_server_url
    if version:
        favicon_url += f"{version}/"
    favicon_url += f"{host}/favicon.ico"

    return quart_redirect(favicon_url, code=302)


@app.route("/memorial-site-image")
async def site_image():
    """Serves an image for the site"""
    host, host_config = get_host_configuration(request.host)

    # Image files follow a naming convention where domain names
    # have dots (.) replaced with underscores (_)
    # Without www and with . replaced by _ (e.g., example_com.png for example.com)
    host_image_normalized = host.replace(".", "_")

    # read the 'IMAGES_FOLDER' configuration variable to get the path to the images folder
    images_folder = app.config.get("IMAGES_FOLDER", "/static/img")

    logo = None
    if host_config:
        logo = host_config.get("logo", None)

    # if logo is an URL send a redirect to it
    if logo and (logo.startswith("http://") or logo.startswith("https://") or logo.startswith("//")):
        return await quart_redirect(logo, code=302)

    # Try to find any file that matches the host name with any extension
    image_filename = None
    try:
        if os.path.isdir(images_folder):
            for fname in os.listdir(images_folder):
                name_no_ext, _ext = os.path.splitext(fname)
                if name_no_ext.lower() == host_image_normalized.lower():
                    image_filename = fname
                    break
    except Exception:  # pylint: disable=broad-except
        logger.info("No image file found for %s", host_image_normalized)

    if not image_filename:
        image_filename = app.config.get("DEFAULT_LOGO", "arquivo_pt_2024-preto.png")

    logger.info("Serving image folder: %s file: %s", images_folder, image_filename)
    return await send_from_directory(images_folder, image_filename)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
async def redirect(path):
    """Main handler for all routes - generates memorial landing page.

    Creates a landing page that informs visitors the site is archived and
    provides a link to view it in the Arquivo.pt Wayback Machine. The page
    can be customized per-domain with specific messages, logos, and versions.

    This is an async route handler that uses non-blocking HTTP requests
    for better performance when fetching metadata from the Wayback Machine.

    Args:
        path: The requested path (captured from URL)

    Returns:
        Rendered HTML template with metadata and redirect information
    """
    host, host_config = get_host_configuration(request.host)

    # Wayback Machine URLs - can be overridden in config
    wayback_server_url = app.config.get("WAYBACK_SERVER", "https://arquivo.pt/wayback/")
    wayback_noframe_server_url = get_wayback_noframe_server_url()

    template = None  # Template to use for this host (default is redirect_default.html)
    default_language = "pt"
    message_pt = None
    message_en = None
    message_before_button_pt = None
    message_before_button_en = None
    button_message_pt = None
    button_message_en = None
    version = None  # Specific timestamp version of archived site
    button_color = None
    logo = None
    link_pt = None  # Custom links for Portuguese version
    link_en = None  # Custom links for English version
    link_to_noFrame = False  # Whether to use noFrame version
    should_extract_metadata = None  # Whether to extract metadata from archived page
    configured_title = None  # Static title when metadata extraction is disabled
    configured_metadata = None  # Static metadata when metadata extraction is disabled
    status_code = 502  # HTTP status code (200=OK, 502=Bad Gateway, etc.)
    archived_site_status_code = 200  # HTTP status code (200=OK, 502=Bad Gateway, etc.)

    # Look up custom configuration for this specific host
    # Configuration is defined in config.py ARCHIVE_CONFIG dictionary
    host_config = app.config["ARCHIVE_CONFIG"].get(host, None)
    if host_config is not None:
        # Override defaults with host-specific settings
        template = host_config.get("template", None)  # Optional custom template for this host
        default_language = host_config.get("default_language", default_language)
        message_pt = host_config.get("message_pt", message_pt)  # Only message is configurable per-host
        message_en = host_config.get("message_en", message_en)  # Only message is configurable per-host
        version = host_config.get("version", version)  # Timestamp like '20200117175504'
        button_color = host_config.get("button_color", button_color)
        logo = host_config.get("logo", logo)
        link_pt = host_config.get("link_pt", link_pt)
        link_en = host_config.get("link_en", link_en)
        link_to_noFrame = host_config.get("link_to_noFrame", link_to_noFrame)
        should_extract_metadata = host_config.get(
            "extract_metadata", should_extract_metadata
        )  # Per-host metadata extraction
        configured_title = host_config.get("title", configured_title)  # Static title for this site
        configured_metadata = host_config.get("metadata", configured_metadata)  # Static metadata for this site
        status_code = host_config.get("status_code", archived_site_status_code)  # HTTP status code

    # Default template settings
    # For 502 status codes, check for maintenance-specific templates
    if not template and status_code in (502, 503, 504):  # Server error status codes
        template = get_maintenance_template(host)
    else:
        template = "redirect_default.html"

    # Apply status-code-based default messages if no custom message is configured
    # This allows different messages for different HTTP status codes (e.g., 200 vs 502)
    # while still allowing per-host overrides via config.py
    # Note: Only the primary message can be overridden per-host
    # message_before_button and button_message always come from DEFAULT_MESSAGES
    default_messages_for_status = DEFAULT_MESSAGES.get(status_code, DEFAULT_MESSAGES[200])

    if message_pt is None:
        message_pt = default_messages_for_status["pt"]["message"]
    if message_en is None:
        message_en = default_messages_for_status["en"]["message"]

    # message_before_button and button_message are always from DEFAULT_MESSAGES
    message_before_button_pt = default_messages_for_status["pt"]["message_before_button"]
    message_before_button_en = default_messages_for_status["en"]["message_before_button"]
    button_message_pt = default_messages_for_status["pt"]["button_message"]
    button_message_en = default_messages_for_status["en"]["button_message"]

    # Construct Wayback Machine URLs
    # If a specific version timestamp is configured, use it; otherwise use latest
    # URLs with specific timestamp version (e.g., /20200117175504/example.com)
    # Or latest version without timestamp (e.g., /example.com) - Wayback will serve the latest archived version
    _version = f"{version}/" if version else ""

    redirect_url_wayback = f"{wayback_server_url}{_version}{request.base_url}"
    redirect_url_noFrame = f"{wayback_noframe_server_url}{_version}{request.base_url}"
    redirect_url_home = f"{wayback_noframe_server_url}{_version}{host}"

    # Choose between noFrame (cleaner) or regular Wayback interface
    redirect_url = redirect_url_noFrame if link_to_noFrame else redirect_url_wayback

    # Determine if metadata should be extracted
    # Priority: per-host setting > global setting > default (False)
    if should_extract_metadata is not None:
        extract_metadata_enabled = should_extract_metadata
    else:
        extract_metadata_enabled = app.config.get("EXTRACT_METADATA", False)

    # For the default template, optionally extract metadata from the archived page
    # This provides context about what the preserved site contained
    if extract_metadata_enabled:
        # Extract dynamic metadata from archived page (ignores configured title/metadata)
        title, metadata = await extract_metadata(redirect_url_home, redirect_url_noFrame)
    else:
        # Use configured static metadata if available
        title = f"<title>{configured_title}</title>" if configured_title is not None else None
        metadata = configured_metadata if configured_metadata is not None else []

    return (
        await render_template(
            template,
            title=title,  # Original page title
            metatags=metadata,  # Meta tags from original page
            redirect_url=redirect_url,  # Where to find the archived version
            default_language=default_language,  # UI language (pt/en)
            message_pt=message_pt,  # Custom Portuguese message (only configurable message)
            message_en=message_en,  # Custom English message (only configurable message)
            message_before_button_pt=message_before_button_pt,  # Message before button (from DEFAULT_MESSAGES)
            message_before_button_en=message_before_button_en,  # Message before button (from DEFAULT_MESSAGES)
            button_message_pt=button_message_pt,  # Button text (from DEFAULT_MESSAGES)
            button_message_en=button_message_en,  # Button text (from DEFAULT_MESSAGES)
            button_color=button_color,  # Custom button styling
            logo=logo,  # Custom logo URL
            link_pt=link_pt,  # Additional Portuguese links
            link_en=link_en,  # Additional English links
            args=request.args.items(),  # Query string parameters
        ),
        status_code,  # Return configured HTTP status code
    )


if __name__ == "__main__":
    # Run Quart development server when executed directly
    # For production, use Hypercorn or similar ASGI server
    app.run()
