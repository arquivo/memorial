"""
Shared pytest configuration and fixtures for Memorial test suite.

This module provides:
- Mock setup for httpx.AsyncClient
- Pytest fixtures (client fixture)
- Helper functions (request_host, get_title, get_metadata, with_test_config)
- Test configuration utilities
"""

from contextlib import contextmanager
from unittest.mock import AsyncMock, Mock, patch

import pytest
from bs4 import BeautifulSoup

# Import memorial first
from memorial import app

# Then patch memorial.httpx.AsyncClient to intercept calls from within memorial
mock_patcher = patch("memorial.httpx.AsyncClient")
mock_client_class = mock_patcher.start()

# Create mock response that works for all tests
mock_response = Mock()
mock_response.status_code = 200
mock_response.headers = {"content-type": "text/html"}
mock_response.content = b"""
<html>
<head>
    <title>Test Page</title>
    <meta name="description" content="Test description">
    <meta name="keywords" content="test, keywords">
</head>
<body>Test content</body>
</html>
"""

# Configure the mock async client instance
mock_client_instance = Mock()
mock_client_instance.head = AsyncMock(return_value=mock_response)
mock_client_instance.get = AsyncMock(return_value=mock_response)
mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
mock_client_instance.__aexit__ = AsyncMock(return_value=None)
mock_client_class.return_value = mock_client_instance


@pytest.fixture
def client():
    """Create a test client for the Quart app."""
    return app.test_client()


@contextmanager
def with_test_config(archive_config):
    """Context manager to temporarily set test configuration."""
    # Save original state
    if "ARCHIVE_CONFIG" in app.config:
        original_archive_config = dict(app.config["ARCHIVE_CONFIG"])
    else:
        original_archive_config = {}

    # Set test config
    app.config["ARCHIVE_CONFIG"] = dict(archive_config)

    # Ensure wayback URLs are set
    if "WAYBACK_SERVER" not in app.config:
        app.config["WAYBACK_SERVER"] = "https://arquivo.pt/wayback/"
    if "WAYBACK_NOFRAME_SERVER" not in app.config:
        app.config["WAYBACK_NOFRAME_SERVER"] = "https://arquivo.pt/noFrame/replay/"

    try:
        yield
    finally:
        app.config["ARCHIVE_CONFIG"] = original_archive_config


async def request_host(client, path, host, expected_status=200):
    """Helper method to make a request with a specific Host header.

    Args:
        client: The test client
        path: The path to request
        host: The Host header value
        expected_status: Expected HTTP status code (default: 200)

    Returns:
        The response object
    """
    response = await client.get(path, headers={"Host": host})
    assert response.status_code == expected_status
    return response


def get_title(response_data):
    """Extract the title from the HTML content of the response."""
    html = str(response_data)
    soup = BeautifulSoup(html, "html.parser")
    title = soup.find("title")
    if title:
        print(f"Title: {title.text}")
        return title.text
    print("Title: None (not found)")
    return None


def get_metadata(response_data, meta_tag):
    """Extract the content of a specific meta tag from the HTML content.

    Args:
        response_data: The HTML content of the response
        meta_tag: The name of the meta tag to extract

    Returns:
        The content of the meta tag, or None if not found
    """
    html = str(response_data)
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", {"name": meta_tag})
    if meta and "content" in meta.attrs:
        print(f"{meta_tag}: {meta['content']}")
        return meta["content"]
    print(f"{meta_tag}: None (not found)")
    return None
