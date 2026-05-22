"""Data extraction utilities for archived sites on Arquivo.pt.

This module provides functions to extract metadata from specific versions of archived
sites stored on the Arquivo.pt Wayback Machine. Metadata includes titles, meta tags,
and link tags extracted from the archived pages.

Usage:
    Extract metadata for a single site:
        metadata = extract_site_metadata("example.com", "20200117175504")
        print(metadata)  # List of meta tag strings

    Extract metadata for all configured sites:
        from config import ARCHIVE_CONFIG
        results = extract_metadata_for_configured_sites(ARCHIVE_CONFIG)
        export_to_tsv(results, "metadata.tsv")
"""

import logging
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def fix_not_closed_metatags(tag) -> str:
    """Fix unclosed meta tags by ensuring proper closing.

    Some archived sites have malformed HTML with unclosed meta/link tags.
    This function ensures they are properly closed with self-closing syntax (/>).

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


def get_archived_page_content(
    wayback_url: str, timeout: int = 10
) -> Optional[bytes]:
    """Fetch content from an archived page on Arquivo.pt.

    Attempts to fetch the requested URL from the Wayback Machine using a synchronous
    HTTP request. Handles redirects and timeouts gracefully.

    Args:
        wayback_url: The full URL to the archived page on Arquivo.pt
                    (e.g., https://arquivo.pt/noFrame/replay/20200117175504/example.com)
        timeout: Request timeout in seconds (default: 10)

    Returns:
        bytes: The HTML content of the archived page, or None if retrieval fails
    """
    try:
        response = httpx.get(wayback_url, follow_redirects=True, timeout=timeout)
        if response.status_code == 200:
            return response.content
        else:
            logger.warning(
                "Failed to fetch %s: HTTP %s", wayback_url, response.status_code
            )
            return None
    except httpx.TimeoutException:
        logger.error("Timeout fetching %s after %s seconds", wayback_url, timeout)
        return None
    except Exception as e:  # pylint: disable=broad-except
        logger.error("Error fetching %s: %s", wayback_url, str(e))
        return None


def extract_metadata_from_html(html_content: bytes) -> tuple[str, list[str]]:
    """Extract page title and metadata tags from HTML content.

    Parses HTML and extracts:
    - Page title from <title> tag
    - Meta tags (description, keywords, author)
    - Link tags (author, home, favicon, alternate)

    Args:
        html_content: The HTML content to parse (bytes)

    Returns:
        tuple: (title, metadata_list) where title is a string and metadata_list is a list of tag strings
    """
    meta_list = []
    title = ""

    try:
        soup = BeautifulSoup(html_content, "html.parser")

        # Extract page title
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)

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

    except Exception as e:  # pylint: disable=broad-except
        logger.error("Error parsing HTML: %s", str(e))

    return title, meta_list


def extract_site_metadata(
    site: str,
    version: str,
    wayback_noframe_server: str = "https://arquivo.pt/noFrame/replay/",
    timeout: int = 10,
) -> tuple[str, list[str]]:
    """Extract title and metadata for a specific archived site and version.

    Constructs the Arquivo.pt Wayback Machine URL for the given site and version,
    fetches the archived page, and extracts the page title and metadata tags from it.

    Args:
        site: The domain name of the archived site (e.g., "example.com")
        version: The version timestamp (e.g., "20200117175504")
        wayback_noframe_server: Base URL for Arquivo.pt noFrame replay (default: https://arquivo.pt/noFrame/replay/)
        timeout: Request timeout in seconds (default: 10)

    Returns:
        tuple: (title, metadata_list) where title is a string and metadata_list is a list of tag strings.
               Returns ("", []) if extraction fails.

    Example:
        >>> title, metadata = extract_site_metadata("senior3045.ipportalegre.pt", "20200117175504")
        >>> print(title)
        'Example Site Title'
        >>> print(metadata)
        ['<meta name="description" content="Example description"/>']
    """
    # Ensure wayback URL ends with slash
    if not wayback_noframe_server.endswith("/"):
        wayback_noframe_server += "/"

    # Construct the full URL to the archived site
    wayback_url = f"{wayback_noframe_server}{version}/{site}"

    logger.info("Extracting data from %s", wayback_url)

    # Fetch the archived page content
    html_content = get_archived_page_content(wayback_url, timeout)

    if html_content is None:
        logger.warning("Could not extract data for %s version %s", site, version)
        return "", []

    # Extract title and metadata from the HTML
    return extract_metadata_from_html(html_content)


def extract_metadata_for_configured_sites(
    archive_config: dict,
    wayback_noframe_server: str = "https://arquivo.pt/noFrame/replay/",
    timeout: int = 10,
) -> dict[str, tuple[str, list[str]]]:
    """Extract title and metadata for all configured sites in ARCHIVE_CONFIG.

    Iterates through all sites configured in ARCHIVE_CONFIG and extracts title
    and metadata for each one. Only processes sites that have a "version" defined.

    Args:
        archive_config: The ARCHIVE_CONFIG dictionary from config.py
        wayback_noframe_server: Base URL for Arquivo.pt noFrame replay
        timeout: Request timeout in seconds per site (default: 10)

    Returns:
        dict: A dictionary mapping site hostnames to their (title, metadata_list) tuples.
              Format: {"site.com": ("Site Title", ['<meta name="description" content="..."/>'], ...}

    Example:
        >>> from config import ARCHIVE_CONFIG
        >>> results = extract_metadata_for_configured_sites(ARCHIVE_CONFIG)
        >>> for site, (title, metadata) in results.items():
        ...     print(f"{site}: {title} ({len(metadata)} tags)")
    """
    results = {}

    for site, site_config in archive_config.items():
        # Only process sites with a defined version
        if not isinstance(site_config, dict) or "version" not in site_config:
            logger.info("Skipping %s: no version defined", site)
            continue

        version = site_config["version"]
        logger.info("Processing %s (version: %s)", site, version)

        title, metadata = extract_site_metadata(
            site, version, wayback_noframe_server, timeout
        )
        results[site] = (title, metadata)

    return results


def format_metadata_as_string(metadata_list: list[str]) -> str:
    """
    Format metadata list as a single string for TSV export.

    The export needs to be compatible with both TSV format and Python because 
    the metadata is to be read back into Python for further processing.

    Joins metadata tags using the specified separator and escapes special characters for TSV.

    Args:
        metadata_list: List of metadata tag strings

    Returns:
        str: Formatted string suitable for TSV column

    Example:
        >>> metadata = ['<meta name="description" content="My 'special' example"/>', '<meta name="keywords" content="test"/>']
        >>> print(format_metadata_as_string(metadata))
        [ '''<meta name="description" content="My 'special' example"/>''', '''<meta name="keywords" content="test"/>''']
    """
    metadata_list = [f"'''{tag}'''" for tag in metadata_list]
    return f"[ {', '.join(metadata_list)} ]"


def export_site_to_tsv(
    site: str, title: str, metadata_list: list[str], output_file: str
) -> None:
    """Export a single site's data to TSV file (append mode).

    Appends a single site's extracted data to a TSV file. Does not write headers.
    Suitable for streaming/incremental exports when processing many sites.

    Args:
        site: The domain name of the site
        title: The page title
        metadata_list: List of extracted metadata tags
        output_file: Path to the output TSV file (will be created if it doesn't exist)

    Example:
        >>> export_site_to_tsv("example.com", "Example Site", ['<meta name="description"/>'], "data.tsv")
    """
    try:
        metadata_str = format_metadata_as_string(metadata_list)

        # Escape tabs and newlines in both title and metadata
        title_escaped = title.replace("\t", "\\t").replace("\n", "\\n")
        metadata_str_escaped = metadata_str.replace("\t", "\\t").replace("\n", "\\n")

        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"{site}\t{title_escaped}\t{metadata_str_escaped}\n")

        logger.debug("Appended data for %s to %s", site, output_file)

    except Exception as e:  # pylint: disable=broad-except
        logger.error("Error appending to TSV file %s: %s", output_file, str(e))
        print(f"Error appending to TSV: {str(e)}")


def export_to_tsv(
    results: dict[str, tuple[str, list[str]]], output_file: str, append: bool = False
) -> None:
    """Export extracted site data to a TSV file.

    Creates a TSV file with three columns (or appends without header):
    - Column 1: Site hostname
    - Column 2: Page title
    - Column 3: Extracted metadata (formatted as a string)

    Args:
        results: Dictionary mapping sites to their (title, metadata_list) tuples
                (output from extract_metadata_for_configured_sites or extract_site_metadata)
        output_file: Path to the output TSV file
        append: If True, append to file without writing header. If False, overwrite file with header.

    Example:
        >>> results = {"example.com": ("Example Site", ['<meta name="description" content="Example"/>'])}
        >>> export_to_tsv(results, "data.tsv")  # Creates new file with header
        >>> export_to_tsv(results, "data.tsv", append=True)  # Appends without header
    """
    try:
        mode = "a" if append else "w"
        with open(output_file, mode, encoding="utf-8") as f:
            # Write TSV header only if not appending
            if not append:
                f.write("Site\tTitle\tMetadata\n")

            # Write data rows
            for site in sorted(results.keys()):
                title, metadata_list = results[site]
                metadata_str = format_metadata_as_string(metadata_list)

                # Escape tabs and newlines in both title and metadata
                title = title.replace("\t", "\\t").replace("\n", "\\n")
                metadata_str = metadata_str.replace("\t", "\\t").replace(
                    "\n", "\\n"
                )

                f.write(f"{site}\t{title}\t{metadata_str}\n")

        action = "appended" if append else "exported"
        logger.info("%s data to %s", action.capitalize(), output_file)
        print(f"Successfully {action} data to {output_file}")

    except Exception as e:  # pylint: disable=broad-except
        logger.error("Error writing TSV file %s: %s", output_file, str(e))
        print(f"Error exporting to TSV: {str(e)}")
