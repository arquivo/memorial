"""
Helper Functions & URL Construction Tests

Tests:
  - get_host_configuration() function
  - get_wayback_noframe_server_url() function
  - URL construction with/without versions
  - noFrame preference
  - default URL selection
  - port stripping
"""

from unittest.mock import patch

import pytest
from conftest import request_host, with_test_config


@pytest.mark.asyncio
async def test_get_wayback_noframe_server_url_with_slash(client):
    """
    Test that get_wayback_noframe_server_url ensures trailing slash.
    """
    with patch.dict("memorial.app.config", {"WAYBACK_NOFRAME_SERVER": "https://arquivo.pt/noFrame/replay"}, clear=False):
        from memorial import get_wayback_noframe_server_url
        url = get_wayback_noframe_server_url()
        assert url.endswith("/")
        assert "arquivo.pt" in url


@pytest.mark.asyncio
async def test_get_wayback_noframe_server_url_custom(client):
    """
    Test that custom WAYBACK_NOFRAME_SERVER is used correctly.
    """
    custom_url = "https://custom.archive.org/replay/"
    with patch.dict("memorial.app.config", {"WAYBACK_NOFRAME_SERVER": custom_url}, clear=False):
        from memorial import get_wayback_noframe_server_url
        url = get_wayback_noframe_server_url()
        assert url == custom_url


@pytest.mark.asyncio
async def test_get_host_configuration_strips_www(client):
    """
    Test that get_host_configuration correctly normalizes hosts by removing www.
    """
    from memorial import get_host_configuration

    with patch.dict("memorial.app.config", {
        "ARCHIVE_CONFIG": {"example.com": {"message_pt": "Test"}},
        "STRIP_PORT": False
    }, clear=False):
        # Test with www
        normalized_host, config = get_host_configuration("www.example.com")
        assert normalized_host == "example.com"
        assert config is not None


@pytest.mark.asyncio
async def test_get_host_configuration_no_config(client):
    """
    Test that get_host_configuration returns None when site not configured.
    """
    from memorial import get_host_configuration

    with patch.dict("memorial.app.config", {
        "ARCHIVE_CONFIG": {},
        "STRIP_PORT": False
    }, clear=False):
        normalized_host, config = get_host_configuration("unknown.com")
        assert config is None


@pytest.mark.asyncio
async def test_get_host_configuration_with_port_stripping(client):
    """
    Test that get_host_configuration strips port when STRIP_PORT is enabled.
    """
    from memorial import get_host_configuration

    with patch.dict("memorial.app.config", {
        "ARCHIVE_CONFIG": {"example.com": {"message_pt": "Test"}},
        "STRIP_PORT": True
    }, clear=False):
        # Test with port
        normalized_host, config = get_host_configuration("example.com:8080")
        assert normalized_host == "example.com"
        assert config is not None




# URL Construction Tests: Verify correct Wayback Machine URLs are constructed
# Tests: URLs with/without version timestamps, noFrame preference, default URL selection
# ==============================================================================
# Tests for URL Construction
# ==============================================================================


@pytest.mark.asyncio
async def test_wayback_url_with_version(client):
    """
    Test that Wayback URLs are correctly constructed with version timestamps.
    """
    with with_test_config({
        "versioned.com": {
            "version": "20200101120000",
        }
    }):
        response = await request_host(client, "/", "versioned.com", expected_status=200)
        html_content = (await response.data).decode("utf-8")
        # URL should contain the version timestamp
        assert "20200101120000" in html_content


@pytest.mark.asyncio
async def test_wayback_url_without_version(client):
    """
    Test that Wayback URLs are constructed without version when not specified.
    """
    with with_test_config({"no-version.com": {}}):
        response = await request_host(client, "/", "no-version.com", expected_status=200)
        html_content = (await response.data).decode("utf-8")
        # URL should reference the domain without version prefix
        assert "arquivo.pt" in html_content


@pytest.mark.asyncio
async def test_noframe_url_preference(client):
    """
    Test that noFrame URL is used when link_to_noFrame is True.
    """
    with with_test_config({
        "noframe-pref.com": {
            "link_to_noFrame": True,
        }
    }):
        response = await request_host(client, "/", "noframe-pref.com", expected_status=200)
        html_content = (await response.data).decode("utf-8")
        # Should use noFrame URL
        assert "noFrame/replay" in html_content


@pytest.mark.asyncio
async def test_regular_wayback_url_used_by_default(client):
    """
    Test that regular Wayback URL is used when link_to_noFrame is False or not set.
    """
    with with_test_config({
        "regular-wayback.com": {
            "link_to_noFrame": False,
        }
    }):
        response = await request_host(client, "/", "regular-wayback.com", expected_status=200)
        html_content = (await response.data).decode("utf-8")
        # Should use regular wayback URL
        assert "wayback" in html_content




# Edge Cases & Error Conditions: Verify robustness with malformed input and edge cases
# Tests: malformed headers, long paths, unicode, multiple slashes, language content,
#        custom styling, timeouts, multi-site configurations
# ==============================================================================
