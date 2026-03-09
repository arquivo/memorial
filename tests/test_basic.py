from contextlib import contextmanager
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from bs4 import BeautifulSoup

# Import memorial first
from memorial import app, fix_not_closed_metatags

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
    # Fake host so it properly match the template
    response = await client.get(path, headers={"Host": host})
    assert response.status_code == expected_status
    return response


def get_title(response_data):
    """
    Extract the title from the HTML content of the response.
    """
    html = str(response_data)
    soup = BeautifulSoup(html, "html.parser")
    title = soup.find("title")
    if title:
        print(f"Title: {title.text}")
        return title.text
    print("Title: None (not found)")
    return None


def get_metadata(response_data, meta_tag):
    """
    Extract the content of a specific meta tag from the HTML content of the response.

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


@pytest.mark.asyncio
async def test_nonexistent_page(client):
    """
    Test that requesting a non-existent page returns the same metadata as the home page, since it should fall back to the archived home page.
    """
    # Use a test-specific configuration
    with with_test_config({"test-site.example.com": {}}):
        response_nonexistent = await request_host(
            client, "/example-nonexistent", "test-site.example.com", expected_status=200
        )
        response_home = await request_host(client, "/", "test-site.example.com", expected_status=200)
        title_home = get_title(await response_home.data)
        title_nonexistent = get_title(await response_nonexistent.data)
        # Both should have the same title from the archived page
        assert title_home == title_nonexistent

        desc_home = get_metadata(await response_home.data, "description")
        desc_nonexistent = get_metadata(await response_nonexistent.data, "description")
        assert desc_home == desc_nonexistent


@pytest.mark.asyncio
async def test_inner_page(client):
    """
    Test that requesting an inner page returns the same metadata as the home page for non-HTML content,
    and extracts metadata correctly for HTML content.
    """
    # Use test-specific configurations
    with with_test_config(
        {
            "test-site-1.example.com": {},
            "test-site-2.example.com": {},
        }
    ):
        response_home = await request_host(client, "/", "test-site-1.example.com", expected_status=200)
        response_inner = await request_host(
            client,
            "/some/path/file.mp4",
            "test-site-1.example.com",
            expected_status=200,
        )
        # Non-HTML content should fall back to home page metadata
        assert get_title(await response_home.data) == get_title(await response_inner.data)
        assert get_metadata(await response_home.data, "description") == get_metadata(
            await response_inner.data, "description"
        )

        response_inner = await request_host(client, "/some/html/page/", "test-site-1.example.com", expected_status=200)
        # With mocked responses, we get consistent test data
        title = get_title(await response_inner.data)
        assert title is not None
        desc = get_metadata(await response_inner.data, "description")
        assert desc is not None

        response_home = await request_host(client, "/", "test-site-2.example.com", expected_status=200)
        response_inner = await request_host(
            client,
            "/fonts/font-file.woff2",
            "test-site-2.example.com",
            expected_status=200,
        )
        assert get_title(await response_home.data) == get_title(await response_inner.data)
        assert get_metadata(await response_home.data, "description") == get_metadata(
            await response_inner.data, "description"
        )


@pytest.mark.asyncio
async def test_main_page(client):
    """
    Test that requesting the main page returns the expected metadata.
    """
    # Use test-specific configuration
    with with_test_config(
        {
            "test-main-1.example.com": {},
            "test-main-2.example.com": {},
        }
    ):
        response = await request_host(client, "/", "test-main-1.example.com", expected_status=200)
        title = get_title(await response.data)
        # With mocked responses, we should get our test title
        assert title is not None
        desc = get_metadata(await response.data, "description")
        assert desc is not None

        response = await request_host(client, "/", "test-main-2.example.com", expected_status=200)
        title = get_title(await response.data)
        assert title is not None


@pytest.mark.asyncio
async def test_robotstxt(client):
    """
    Test that requesting the robots.txt file returns a 200 status code.
    """
    # robots.txt doesn't depend on configuration, but we still provide it for consistency
    with with_test_config({}):
        response = await request_host(client, "/robots.txt", "test-robots.example.com", expected_status=200)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_configured_site_returns_200(client):
    """
    Test that a configured site without explicit status_code returns 200 OK by default.
    """
    # Use test-specific configuration without explicit status_code
    with with_test_config({"test-configured.example.com": {}}):
        response = await request_host(client, "/", "test-configured.example.com", expected_status=200)
        assert response.status_code == 200

        # Verify we get the memorial page content
        assert b"arquivo.pt" in (await response.data).lower()


@pytest.mark.asyncio
async def test_unconfigured_site_returns_502(client):
    """
    Test that an unconfigured site returns 502 Bad Gateway by default.
    This indicates the original site is no longer available.
    """
    # unconfigured-site.example.com is NOT in config.py
    response = await request_host(client, "/", "unconfigured-site.example.com", expected_status=502)
    assert response.status_code == 502

    # Verify we still get the memorial page content
    assert b"arquivo.pt" in (await response.data).lower()


@pytest.mark.asyncio
async def test_configured_site_custom_status_code(client):
    """
    Test that a site configured with a custom status_code returns that code.
    This requires temporarily patching the config.
    """
    # Patch the ARCHIVE_CONFIG to add a site with custom status_code
    with patch.dict(
        "memorial.app.config",
        {
            "ARCHIVE_CONFIG": {
                "custom-status.example.com": {
                    "status_code": 410,  # 410 Gone
                    "message_pt": "Site permanentemente removido",
                }
            },
            "WAYBACK_SERVER": "https://arquivo.pt/wayback/",
            "WAYBACK_NOFRAME_SERVER": "https://arquivo.pt/noFrame/replay/",
        },
    ):
        response = await request_host(client, "/", "custom-status.example.com", expected_status=410)
        assert response.status_code == 410
        assert b"arquivo.pt" in (await response.data).lower()


@pytest.mark.asyncio
async def test_different_status_codes_for_different_sites(client):
    """
    Test that different sites can have different status codes configured.
    """
    # Patch config with multiple sites with different status codes
    with patch.dict(
        "memorial.app.config",
        {
            "ARCHIVE_CONFIG": {
                "site-ok.example.com": {
                    "status_code": 200,
                    "version": "20200101000000",
                },
                "site-gone.example.com": {
                    "status_code": 410,
                },
                "site-unavailable.example.com": {
                    "status_code": 503,
                },
            },
            "WAYBACK_SERVER": "https://arquivo.pt/wayback/",
            "WAYBACK_NOFRAME_SERVER": "https://arquivo.pt/noFrame/replay/",
        },
    ):
        # Test 200 OK
        response_200 = await request_host(client, "/", "site-ok.example.com", expected_status=200)
        assert response_200.status_code == 200

        # Test 410 Gone
        response_410 = await request_host(client, "/", "site-gone.example.com", expected_status=410)
        assert response_410.status_code == 410

        # Test 503 Service Unavailable
        response_503 = await request_host(client, "/", "site-unavailable.example.com", expected_status=503)
        assert response_503.status_code == 503


@pytest.mark.asyncio
async def test_status_code_preserved_across_paths(client):
    """
    Test that the same status code is returned for all paths on the same host.
    """
    with patch.dict(
        "memorial.app.config",
        {
            "ARCHIVE_CONFIG": {
                "consistent-status.example.com": {
                    "status_code": 410,
                }
            },
            "WAYBACK_SERVER": "https://arquivo.pt/wayback/",
            "WAYBACK_NOFRAME_SERVER": "https://arquivo.pt/noFrame/replay/",
        },
    ):
        # Test root path
        response_root = await request_host(client, "/", "consistent-status.example.com", expected_status=410)
        assert response_root.status_code == 410

        # Test subpath
        response_sub = await request_host(client, "/some/path", "consistent-status.example.com", expected_status=410)
        assert response_sub.status_code == 410

        # Test with query parameters
        response_query = await request_host(
            client, "/page?id=123", "consistent-status.example.com", expected_status=410
        )
        assert response_query.status_code == 410


@pytest.mark.asyncio
async def test_fix_not_closed_metatags_with_slash(client):
    """
    Test fix_not_closed_metatags function with tag ending in /.
    """
    # Create a mock tag that ends with /
    mock_tag = Mock()
    mock_tag.__str__ = Mock(return_value='<meta name="test" content="value"/')

    result = fix_not_closed_metatags(mock_tag)
    assert result == '<meta name="test" content="value"/>'


@pytest.mark.asyncio
async def test_fix_not_closed_metatags_without_slash(client):
    """
    Test fix_not_closed_metatags function with tag not ending in /.
    """
    # Create a mock tag that doesn't end with /
    mock_tag = Mock()
    mock_tag.__str__ = Mock(return_value='<meta name="test" content="value"')

    result = fix_not_closed_metatags(mock_tag)
    assert result == '<meta name="test" content="value"/>'


@pytest.mark.asyncio
async def test_timeout_exception_handling(client):
    """
    Test that timeout exceptions are properly raised when fetching content.
    """
    # Configure mock to raise TimeoutException
    mock_client_instance = Mock()
    mock_client_instance.head = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)

    with with_test_config({"test-timeout.example.com": {}}):
        with patch("memorial.httpx.AsyncClient", return_value=mock_client_instance):
            response = await request_host(client, "/", "test-timeout.example.com", expected_status=200)
            # The app should handle the timeout gracefully
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_extract_metadata_exception_handling(client):
    """
    Test that extract_metadata handles exceptions gracefully.
    """
    # Configure mock to raise an exception during HTML parsing
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/html"}
    mock_response.content = b"invalid html content that will cause parsing errors"

    mock_client_instance = Mock()
    mock_client_instance.head = AsyncMock(side_effect=Exception("Parsing error"))
    mock_client_instance.get = AsyncMock(side_effect=Exception("Parsing error"))
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)

    with with_test_config({"test-exception.example.com": {}}):
        with patch("memorial.httpx.AsyncClient", return_value=mock_client_instance):
            response = await request_host(client, "/", "test-exception.example.com", expected_status=200)
            # Should still return a response even if metadata extraction fails
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_custom_template_rendering(client):
    """
    Test that custom templates are rendered correctly.
    """
    # Patch config with a custom template
    with patch.dict(
        "memorial.app.config",
        {
            "ARCHIVE_CONFIG": {
                "custom-template.example.com": {
                    "template": "custom_template.html",  # Non-default template
                    "status_code": 200,
                }
            },
            "WAYBACK_SERVER": "https://arquivo.pt/wayback/",
            "WAYBACK_NOFRAME_SERVER": "https://arquivo.pt/noFrame/replay/",
        },
    ):
        # Mock the render_template to avoid needing the actual template file
        with patch("memorial.render_template") as mock_render:
            mock_render.return_value = "Custom template content"

            await client.get("/", headers={"Host": "custom-template.example.com"})

            # Verify custom template was used (not redirect_default.html)
            mock_render.assert_called_once()
            call_args = mock_render.call_args
            assert call_args[0][0] == "custom_template.html"
            # Verify simpler params for custom template (no metadata)
            assert "origin_host" in call_args[1]
            assert "redirect_url" in call_args[1]
            assert "metadata" not in call_args[1]


@pytest.mark.asyncio
async def test_environment_variable_configuration(client):
    """
    Test that MEMORIAL_CONFIGURATION environment variable is properly loaded.
    This tests the configuration override mechanism.
    """
    import os
    import tempfile

    # Save original configuration
    original_config = dict(app.config.get("ARCHIVE_CONFIG", {}))

    # Create a temporary config file with unique configuration
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write('ARCHIVE_CONFIG = {"env-test.example.com": {"status_code": 418, "message_pt": "Test config"}}\n')
        f.write('WAYBACK_SERVER = "https://arquivo.pt/wayback/"\n')
        f.write('WAYBACK_NOFRAME_SERVER = "https://arquivo.pt/noFrame/replay/"\n')
        temp_config_path = f.name

    try:
        # Set environment variable and load the config
        with patch.dict(os.environ, {"MEMORIAL_CONFIGURATION": temp_config_path}):
            # Manually load config from environment variable
            app.config.from_envvar("MEMORIAL_CONFIGURATION")

            # Verify the configuration was actually loaded
            assert "env-test.example.com" in app.config["ARCHIVE_CONFIG"]
            assert app.config["ARCHIVE_CONFIG"]["env-test.example.com"]["status_code"] == 418
            assert app.config["ARCHIVE_CONFIG"]["env-test.example.com"]["message_pt"] == "Test config"

            # Test that a request uses the new configuration
            response = await request_host(client, "/", "env-test.example.com", expected_status=418)
            assert response.status_code == 418
    finally:
        # Restore original configuration
        app.config["ARCHIVE_CONFIG"] = original_config
        # Cleanup temp file
        os.unlink(temp_config_path)


@pytest.mark.asyncio
async def test_non_html_content_fallback(client):
    """
    Test that non-HTML content (like images, PDFs) falls back to home page metadata.
    """
    # Configure mock to return non-HTML content type
    mock_head_response = Mock()
    mock_head_response.status_code = 200
    mock_head_response.headers = {"content-type": "image/jpeg"}

    mock_get_response = Mock()
    mock_get_response.status_code = 200
    mock_get_response.headers = {"content-type": "text/html"}
    mock_get_response.content = b"""
    <html>
    <head><title>Home Page</title></head>
    <body>Home content</body>
    </html>
    """

    mock_client_instance = Mock()
    mock_client_instance.head = AsyncMock(return_value=mock_head_response)
    mock_client_instance.get = AsyncMock(return_value=mock_get_response)
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)

    with with_test_config({"test-image.example.com": {}}):
        with patch("memorial.httpx.AsyncClient", return_value=mock_client_instance):
            response = await request_host(client, "/image.jpg", "test-image.example.com", expected_status=200)
            assert response.status_code == 200
            # Should get metadata from home page instead
            assert b"Home Page" in await response.data


@pytest.mark.asyncio
async def test_metadata_with_link_tags(client):
    """
    Test that link tags (favicon, author, etc.) are properly extracted from HTML.
    """
    # Configure mock to return HTML with link tags
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/html"}
    mock_response.content = b"""
    <html>
    <head>
        <title>Test Page with Links</title>
        <link rel="icon" href="/favicon.ico" type="image/x-icon">
        <link rel="shortcut icon" href="/favicon.ico">
        <link rel="author" href="/about">
        <link rel="alternate" hreflang="en" href="/en/">
    </head>
    <body>Test content</body>
    </html>
    """

    mock_client_instance = Mock()
    mock_client_instance.head = AsyncMock(return_value=mock_response)
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)

    with with_test_config({"test-links.example.com": {}}):
        with patch("memorial.httpx.AsyncClient", return_value=mock_client_instance):
            response = await request_host(client, "/", "test-links.example.com", expected_status=200)
            assert response.status_code == 200
            # Verify link tags are extracted
            html_content = (await response.data).decode("utf-8")
            assert "shortcut icon" in html_content
