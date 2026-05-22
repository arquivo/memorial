"""
Status Code Message Tests

Tests for status-code-based default messages functionality:
  - Default messages for HTTP 200 (disabled site)
  - Default messages for HTTP 502 (temporarily unavailable)
  - Custom messages override defaults
  - Fallback behavior for unknown status codes
  - Language-specific message rendering
"""

import pytest
from bs4 import BeautifulSoup
from conftest import (
    request_host,
    with_test_config,
)


def get_message_by_lang(response_data, lang):
    """Extract the message for a specific language from the HTML response.

    Args:
        response_data: The HTML content of the response (bytes or string)
        lang: The language code ('pt' or 'en')

    Returns:
        The message text, or None if not found
    """
    # Decode if bytes
    if isinstance(response_data, bytes):
        html = response_data.decode('utf-8')
    else:
        html = str(response_data)

    soup = BeautifulSoup(html, "html.parser")

    # Find the message paragraph section (between "entity message" comments)
    # This is before the form starts
    # Strategy: find all p tags with the matching lang, and get the first one
    # that's not inside a form
    paragraphs = soup.find_all("p", {"lang": lang})

    for p in paragraphs:
        # Check if this paragraph is inside a form
        parent = p.parent
        inside_form = False
        while parent:
            if parent.name == "form":
                inside_form = True
                break
            parent = parent.parent

        # Skip if inside form (that's the Arquivo.pt message)
        if inside_form:
            continue

        # Skip language selector links
        if parent and parent.get("id") == "language-container":
            continue

        text = p.get_text(strip=True)
        # Skip empty text
        if text:
            return text

    return None


@pytest.mark.asyncio
async def test_default_message_status_200(client):
    """
    Test that explicitly configured site with 200 status code shows 'disabled' message.

    When a site is configured with status_code 200, it should show
    "O site foi desactivado." (PT) and "The site has been disabled." (EN).
    """
    with with_test_config({
        "explicit-200-site.example.com": {
            "version": "20200101000000",
            "status_code": 200,
        }
    }):
        response = await request_host(
            client, "/", "explicit-200-site.example.com", expected_status=200
        )

        data = await response.data
        message_pt = get_message_by_lang(data, "pt")
        message_en = get_message_by_lang(data, "en")

        assert message_pt is not None, "Portuguese message should be present"
        assert message_en is not None, "English message should be present"
        assert "desactivado" in message_pt.lower(), f"Expected 'desactivado' in PT message, got: {message_pt}"
        assert "disabled" in message_en.lower(), f"Expected 'disabled' in EN message, got: {message_en}"


@pytest.mark.asyncio
async def test_default_message_status_502(client):
    """
    Test that unconfigured site with 502 status code shows 'temporarily unavailable' message.

    When a site is configured with status_code 502, it should show
    "O site está temporariamente indisponível." (PT) and "The site is temporarily unavailable." (EN).
    """
    with with_test_config({
        "temp-down.example.com": {
            "version": "20200101000000",
            "status_code": 502,
        }
    }):
        response = await request_host(
            client, "/", "temp-down.example.com", expected_status=502
        )

        data = await response.data
        message_pt = get_message_by_lang(data, "pt")
        message_en = get_message_by_lang(data, "en")

        assert message_pt is not None, "Portuguese message should be present"
        assert message_en is not None, "English message should be present"
        assert "temporariamente" in message_pt.lower() or "indisponível" in message_pt.lower(), \
            f"Expected 'temporariamente indisponível' in PT message, got: {message_pt}"
        assert "temporarily" in message_en.lower() or "unavailable" in message_en.lower(), \
            f"Expected 'temporarily unavailable' in EN message, got: {message_en}"


@pytest.mark.asyncio
async def test_custom_message_overrides_default_200(client):
    """
    Test that custom configured messages override the default 200 message.

    When a site has custom message_pt and message_en in configuration,
    these should be used instead of the default status code messages.
    """
    custom_pt = "Site customizado para status 200"
    custom_en = "Custom site for status 200"

    with with_test_config({
        "custom-site.example.com": {
            "version": "20200101000000",
            "message_pt": custom_pt,
            "message_en": custom_en,
            # No explicit status_code, defaults to 200
        }
    }):
        response = await request_host(
            client, "/", "custom-site.example.com", expected_status=200
        )

        data = await response.data
        message_pt = get_message_by_lang(data, "pt")
        message_en = get_message_by_lang(data, "en")

        assert message_pt == custom_pt, f"Expected '{custom_pt}', got: {message_pt}"
        assert message_en == custom_en, f"Expected '{custom_en}', got: {message_en}"


@pytest.mark.asyncio
async def test_custom_message_overrides_default_502(client):
    """
    Test that custom messages override the default 502 message.

    When a site has both custom messages and status_code 502,
    the custom messages should take precedence.
    """
    custom_pt = "Site temporariamente em manutenção"
    custom_en = "Site under maintenance"

    with with_test_config({
        "maintenance-site.example.com": {
            "version": "20200101000000",
            "status_code": 502,
            "message_pt": custom_pt,
            "message_en": custom_en,
        }
    }):
        response = await request_host(
            client, "/", "maintenance-site.example.com", expected_status=502
        )

        data = await response.data
        message_pt = get_message_by_lang(data, "pt")
        message_en = get_message_by_lang(data, "en")

        assert message_pt == custom_pt, f"Expected '{custom_pt}', got: {message_pt}"
        assert message_en == custom_en, f"Expected '{custom_en}', got: {message_en}"


@pytest.mark.asyncio
async def test_partial_custom_message_pt_only(client):
    """
    Test that when only message_pt is configured, message_en uses default.

    When only Portuguese custom message is set, the English message
    should use the default for the status code.
    """
    custom_pt = "Apenas português customizado"

    with with_test_config({
        "partial-site.example.com": {
            "version": "20200101000000",
            "status_code": 502,
            "message_pt": custom_pt,
            # message_en is not set, should use default for 502
        }
    }):
        response = await request_host(
            client, "/", "partial-site.example.com", expected_status=502
        )

        data = await response.data
        message_pt = get_message_by_lang(data, "pt")
        message_en = get_message_by_lang(data, "en")

        assert message_pt == custom_pt, f"Expected custom PT message, got: {message_pt}"
        assert "temporarily" in message_en.lower() or "unavailable" in message_en.lower(), \
            f"Expected default 502 EN message, got: {message_en}"


@pytest.mark.asyncio
async def test_partial_custom_message_en_only(client):
    """
    Test that when only message_en is configured, message_pt uses default.

    When only English custom message is set, the Portuguese message
    should use the default for the status code.
    """
    custom_en = "Only English customized"

    with with_test_config({
        "partial-en-site.example.com": {
            "version": "20200101000000",
            "status_code": 502,
            "message_en": custom_en,
            # message_pt is not set, should use default for 502
        }
    }):
        response = await request_host(
            client, "/", "partial-en-site.example.com", expected_status=502
        )

        data = await response.data
        message_pt = get_message_by_lang(data, "pt")
        message_en = get_message_by_lang(data, "en")

        assert "temporariamente" in message_pt.lower() or "indisponível" in message_pt.lower(), \
            f"Expected default 502 PT message, got: {message_pt}"
        assert message_en == custom_en, f"Expected custom EN message, got: {message_en}"


@pytest.mark.asyncio
async def test_http_status_code_response(client):
    """
    Test that the HTTP status code is correctly returned in the response.

    Verify that sites with status_code 502 return 502 status code,
    while unconfigured sites return 200.
    """
    with with_test_config({
        "status-200-site.example.com": {
            "version": "20200101000000",
            # Defaults to status_code 200
        },
        "status-502-site.example.com": {
            "version": "20200101000000",
            "status_code": 502,
        }
    }):
        # Test 200 status code
        response_200 = await request_host(
            client, "/", "status-200-site.example.com", expected_status=200
        )
        assert response_200.status_code == 200

        # Test 502 status code
        response_502 = await request_host(
            client, "/", "status-502-site.example.com", expected_status=502
        )
        assert response_502.status_code == 502
