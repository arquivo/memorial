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


def fix_not_closed_metatags(tag):
    """Fix unclosed meta tags by ensuring proper closing.

    Some archived sites (e.g., gridcomputing.pt) have malformed HTML with
    unclosed meta/link tags. This function ensures they are properly closed
    with self-closing syntax (/>).

    Args:
        tag: BeautifulSoup tag object to fix

    Returns:
        str: Fixed tag string with proper closing
    """
    # Extract tag content before the first '>'
    fix_tag = str(tag).split(">")[0]

    # Ensure self-closing tags end with '/>'
    if not fix_tag.endswith("/"):
        fix_tag += "/>"
    else:
        fix_tag += ">"

    return fix_tag


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
        except Exception:
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

        # Parse HTML content
        html = r.content
        soup = BeautifulSoup(html, "html.parser")

        # Extract common meta tags that describe the page
        valid_meta_names = ["description", "keywords", "author"]
        for name in valid_meta_names:
            for tag in soup.find_all("meta", {"name": name}):
                meta_list.append(fix_not_closed_metatags(tag))

        # Extract link tags for additional resources (favicon, alternate pages, etc.)
        # Only if the page has a <head> section
        head = soup.find("head")
        if head:
            valid_link_rels = ["author", "home", "shortcut icon", "alternate"]
            for rel_value in valid_link_rels:
                for tag in head.find_all("link", attrs={"rel": rel_value}):
                    meta_list.append(fix_not_closed_metatags(tag))

        # Extract page title
        title = soup.find("title")

        return title, meta_list
    except Exception as e:
        # Log error but continue - metadata extraction is best effort
        logger.error(
            f"Failed to extract metadata for {redirect_url_home}: {type(e).__name__}: {str(e) or 'No error message'}",
            exc_info=True,
        )
        return None, meta_list


@app.route("/robots.txt")
async def robots():
    """Serve robots.txt file for web crawlers."""
    return await send_from_directory("static", "robots.txt")


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
    # Get the original host that was requested
    origin_host = request.host

    # Strip port if MEMORIAL_STRIP_PORT is enabled (useful for local development)
    # When enabled, converts "example.com:8080" to "example.com" for config lookup
    if app.config.get("STRIP_PORT", False):
        origin_host = origin_host.split(":")[0]

    host_without_www = origin_host.replace("www.", "")  # Normalize host for config lookup

    # Wayback Machine URLs - can be overridden in config
    wayback_server_url = app.config.get("WAYBACK_SERVER", "https://arquivo.pt/wayback/")
    wayback_noframe_server_url = app.config.get("WAYBACK_NOFRAME_SERVER", "https://arquivo.pt/noFrame/replay/")

    # Default template settings
    template = "redirect_default.html"
    default_language = "pt"
    message_pt = None
    message_en = None
    version = None  # Specific timestamp version of archived site
    button_color = None
    logo = None
    link_pt = None  # Custom links for Portuguese version
    link_en = None  # Custom links for English version
    link_to_noFrame = False  # Whether to use noFrame version
    should_extract_metadata = None  # Whether to extract metadata from archived page
    configured_title = None  # Static title when metadata extraction is disabled
    configured_metadata = None  # Static metadata when metadata extraction is disabled
    status_code = 502  # Default to 502 Bad Gateway if the archived site is not configured
    archived_site_status_code = 200  # HTTP status code (200=OK, 502=Bad Gateway, etc.)

    # Look up custom configuration for this specific host
    # Configuration is defined in config.py ARCHIVE_CONFIG dictionary
    host_config = app.config["ARCHIVE_CONFIG"].get(host_without_www, None)
    if host_config is not None:
        # Override defaults with host-specific settings
        template = host_config.get("template", template)
        default_language = host_config.get("default_language", default_language)
        message_pt = host_config.get("message_pt", message_pt)
        message_en = host_config.get("message_en", message_en)
        version = host_config.get("version", version)  # Timestamp like '20200117175504'
        button_color = host_config.get("button_color", button_color)
        logo = host_config.get("logo", logo)
        link_pt = host_config.get("link_pt", link_pt)
        link_en = host_config.get("link_en", link_en)
        link_to_noFrame = host_config.get("link_to_noFrame", link_to_noFrame)
        should_extract_metadata = host_config.get("extract_metadata", should_extract_metadata)  # Per-host metadata extraction
        configured_title = host_config.get("title", configured_title)  # Static title for this site
        configured_metadata = host_config.get("metadata", configured_metadata)  # Static metadata for this site
        status_code = host_config.get("status_code", archived_site_status_code)  # HTTP status code

    # Construct Wayback Machine URLs
    # If a specific version timestamp is configured, use it; otherwise use latest
    if version:
        # URLs with specific timestamp version (e.g., /20200117175504/example.com)
        redirect_url_wayback = f"{wayback_server_url}{version}/{request.base_url}"
        redirect_url_noFrame = f"{wayback_noframe_server_url}{version}/{request.base_url}"
        redirect_url_home = f"{wayback_noframe_server_url}{version}/{host_without_www}"
    else:
        # URLs without version - Wayback will use the latest archived version
        redirect_url_wayback = f"{wayback_server_url}{request.base_url}"
        redirect_url_noFrame = f"{wayback_noframe_server_url}{request.base_url}"
        redirect_url_home = f"{wayback_noframe_server_url}{host_without_www}"

    # Choose between noFrame (cleaner) or regular Wayback interface
    redirect_url = redirect_url_noFrame if link_to_noFrame else redirect_url_wayback

    # Determine if metadata should be extracted
    # Priority: per-host setting > global setting > default (False)
    if should_extract_metadata is not None:
        extract_metadata_enabled = should_extract_metadata
    else:
        extract_metadata_enabled = app.config.get("EXTRACT_METADATA", False)

    # Render the memorial landing page
    if template == "redirect_default.html":
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
                origin_host=origin_host,  # The domain that was requested
                origin_url=request.url,  # Full original URL
                redirect_url=redirect_url,  # Where to find the archived version
                default_language=default_language,  # UI language (pt/en)
                message_pt=message_pt,  # Custom Portuguese message
                message_en=message_en,  # Custom English message
                button_color=button_color,  # Custom button styling
                logo=logo,  # Custom logo URL
                link_pt=link_pt,  # Additional Portuguese links
                link_en=link_en,  # Additional English links
                args=request.args.items(),  # Query string parameters
            ),
            status_code,  # Return configured HTTP status code
        )
    else:
        # For custom templates, provide minimal context
        return (
            await render_template(template, origin_host=origin_host, origin_url=request.url, redirect_url=redirect_url),
            status_code,
        )


if __name__ == "__main__":
    # Run Quart development server when executed directly
    # For production, use Hypercorn or similar ASGI server
    app.run()
