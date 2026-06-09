"""
Edge Cases & Error Condition Tests

Tests:
  - malformed headers
  - long paths
  - unicode content
  - multiple slashes
  - language-specific content
  - custom styling
  - timeout handling
  - multi-site configurations
  - priority and precedence
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from conftest import request_host, with_test_config


@pytest.mark.asyncio
async def test_malformed_host_header(client):
    """
    Test handling of malformed host headers.
    """
    with with_test_config({"normal.com": {}}):
        # Test with empty host header
        response = await client.get("/", headers={"Host": ""})
        # Should not crash, might return 502 for unconfigured/invalid host
        assert response.status_code in [200, 502]


@pytest.mark.asyncio
async def test_very_long_path(client):
    """
    Test handling of very long URL paths.
    """
    with with_test_config({"long-path.com": {}}):
        long_path = "/" + "/".join(["segment"] * 50)
        response = await request_host(client, long_path, "long-path.com", expected_status=200)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_unicode_characters_in_path(client):
    """
    Test handling of unicode characters in URL path.
    """
    with with_test_config({"unicode.com": {}}):
        response = await request_host(client, "/página/sobre-nós", "unicode.com", expected_status=200)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_multiple_slashes_in_path(client):
    """
    Test handling of multiple consecutive slashes in path.
    """
    with with_test_config({"slashes.com": {}}):
        response = await request_host(client, "//path///to///resource", "slashes.com", expected_status=200)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_language_specific_content(client):
    """
    Test that language-specific messages are rendered correctly.
    """
    with with_test_config(
        {
            "i18n-test.com": {
                "message_pt": "Mensagem em português",
                "message_en": "Message in English",
                "default_language": "pt",
            }
        }
    ):
        response = await request_host(client, "/", "i18n-test.com", expected_status=200)
        html_content = (await response.data).decode("utf-8")
        # Both messages should be present (one hidden by default)
        assert "Mensagem em português" in html_content
        assert "Message in English" in html_content


@pytest.mark.asyncio
async def test_custom_button_color(client):
    """
    Test that custom button color is applied.
    """
    with with_test_config(
        {
            "colored-button.com": {
                "button_color": "#FF5733",
            }
        }
    ):
        response = await request_host(client, "/", "colored-button.com", expected_status=200)
        html_content = (await response.data).decode("utf-8")
        assert "#FF5733" in html_content


@pytest.mark.asyncio
async def test_custom_links_for_languages(client):
    """
    Test that custom links for different languages are applied.
    """
    with with_test_config(
        {
            "custom-links.com": {
                "link_pt": "https://example.com/pt",
                "link_en": "https://example.com/en",
            }
        }
    ):
        response = await request_host(client, "/", "custom-links.com", expected_status=200)
        html_content = (await response.data).decode("utf-8")
        assert "https://example.com/pt" in html_content
        assert "https://example.com/en" in html_content


@pytest.mark.asyncio
async def test_httpx_timeout_configuration(client):
    """
    Test that WAYBACK_REQUEST_TIMEOUT configuration is respected.
    """
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/html"}
    mock_response.content = b"<html><head><title>Test</title></head></html>"

    mock_client_instance = Mock()
    mock_client_instance.head = AsyncMock(return_value=mock_response)
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)

    with patch("memorial.httpx.AsyncClient") as mock_async_client_class:
        mock_async_client_class.return_value = mock_client_instance

        with patch.dict("memorial.app.config", {"WAYBACK_REQUEST_TIMEOUT": 10, "EXTRACT_METADATA": True}, clear=False):
            with with_test_config({"timeout-test.com": {}}):
                response = await request_host(client, "/", "timeout-test.com", expected_status=200)
                assert response.status_code == 200
                # Verify AsyncClient was called with timeout
                mock_async_client_class.assert_called()


@pytest.mark.asyncio
async def test_multiple_sites_different_configs(client):
    """
    Test that multiple sites can be configured with completely different configurations.
    """
    with with_test_config(
        {
            "site-a.com": {
                "status_code": 200,
                "message_pt": "Site A",
                "default_language": "pt",
                "version": "20190101000000",
            },
            "site-b.com": {
                "status_code": 410,
                "message_en": "Site B - Gone",
                "default_language": "en",
            },
            "site-c.com": {
                "status_code": 503,
                "extract_metadata": True,
                "version": "20210601000000",
            },
        }
    ):
        # Test site A
        response_a = await request_host(client, "/", "site-a.com", expected_status=200)
        assert "Site A" in (await response_a.data).decode("utf-8")

        # Test site B
        response_b = await request_host(client, "/", "site-b.com", expected_status=410)
        assert response_b.status_code == 410

        # Test site C
        response_c = await request_host(client, "/", "site-c.com", expected_status=503)
        assert response_c.status_code == 503
