"""
Multi-Part Message Tests

Tests for the three-part message system (message, message_before_button, button_message):
  - Primary message (configurable per-host)
  - Message before button (from DEFAULT_MESSAGES)
  - Button message text (from DEFAULT_MESSAGES)
  - Language-specific message rendering
  - Status code based message selection
  - Proper HTML handling and escaping
"""

import pytest
from bs4 import BeautifulSoup
from conftest import (
    request_host,
    with_test_config,
)


def extract_message_parts(response_data, lang):
    """Extract all three message parts for a specific language from the HTML response.

    Args:
        response_data: The HTML content of the response (bytes or string)
        lang: The language code ('pt' or 'en')

    Returns:
        dict: {
            'primary_message': str or None,
            'message_before_button': str or None,
            'button_message': str or None,
        }
    """
    # Decode if bytes
    if isinstance(response_data, bytes):
        html = response_data.decode('utf-8')
    else:
        html = str(response_data)

    soup = BeautifulSoup(html, "html.parser")
    
    result = {
        'primary_message': None,
        'message_before_button': None,
        'button_message': None,
    }

    # Extract primary message (first p tag with lang, not in form)
    paragraphs = soup.find_all("p", {"lang": lang})
    for p in paragraphs:
        parent = p.parent
        inside_form = False
        while parent:
            if parent.name == "form":
                inside_form = True
                break
            parent = parent.parent

        if not inside_form:
            text = p.get_text(strip=True)
            if text:
                result['primary_message'] = text
                break

    # Extract message_before_button (p tag with lang inside form)
    form = soup.find("form")
    if form:
        form_paragraphs = form.find_all("p", {"lang": lang})
        if form_paragraphs:
            # First p tag in form is the message_before_button
            result['message_before_button'] = form_paragraphs[0].get_text(strip=True)
        
        # Extract button message
        buttons = form.find_all("button", {"lang": lang})
        if buttons:
            result['button_message'] = buttons[0].get_text(strip=True)

    return result


@pytest.mark.asyncio
async def test_default_messages_status_200_all_parts(client):
    """
    Test that all three message parts are present for status 200.

    Verifies that primary message, message_before_button, and button_message
    are all present and contain expected content for Portuguese and English.
    """
    with with_test_config({
        "test-200.example.com": {
            "version": "20200101000000",
            "status_code": 200,
        }
    }):
        response = await request_host(
            client, "/", "test-200.example.com", expected_status=200
        )

        data = await response.data
        
        # Check Portuguese messages
        messages_pt = extract_message_parts(data, "pt")
        assert messages_pt['primary_message'] is not None, "PT primary message should exist"
        assert "desactivado" in messages_pt['primary_message'].lower(), \
            f"PT primary message should contain 'desactivado', got: {messages_pt['primary_message']}"
        assert messages_pt['message_before_button'] is not None, "PT message_before_button should exist"
        assert "memorial" in messages_pt['message_before_button'].lower(), \
            f"PT message_before_button should contain 'memorial', got: {messages_pt['message_before_button']}"
        assert "preservou" in messages_pt['message_before_button'].lower(), \
            f"PT message_before_button should contain 'preservou', got: {messages_pt['message_before_button']}"
        assert messages_pt['button_message'] is not None, "PT button_message should exist"
        assert "arquivo" in messages_pt['button_message'].lower(), \
            f"PT button_message should contain 'arquivo', got: {messages_pt['button_message']}"
        
        # Check English messages
        messages_en = extract_message_parts(data, "en")
        assert messages_en['primary_message'] is not None, "EN primary message should exist"
        assert "disabled" in messages_en['primary_message'].lower(), \
            f"EN primary message should contain 'disabled', got: {messages_en['primary_message']}"
        assert messages_en['message_before_button'] is not None, "EN message_before_button should exist"
        assert "preserved" in messages_en['message_before_button'].lower(), \
            f"EN message_before_button should contain 'preserved', got: {messages_en['message_before_button']}"
        assert messages_en['button_message'] is not None, "EN button_message should exist"
        assert "browse" in messages_en['button_message'].lower(), \
            f"EN button_message should contain 'browse', got: {messages_en['button_message']}"


@pytest.mark.asyncio
async def test_default_messages_status_502_all_parts(client):
    """
    Test that all three message parts are present for status 502.

    Verifies that primary message, message_before_button, and button_message
    are all present with 502-specific content.
    """
    with with_test_config({
        "test-502.example.com": {
            "version": "20200101000000",
            "status_code": 502,
        }
    }):
        response = await request_host(
            client, "/", "test-502.example.com", expected_status=502
        )

        data = await response.data
        
        # Check Portuguese messages
        messages_pt = extract_message_parts(data, "pt")
        assert messages_pt['primary_message'] is not None, "PT primary message should exist"
        assert ("temporariamente" in messages_pt['primary_message'].lower() or 
                "indisponível" in messages_pt['primary_message'].lower()), \
            f"PT primary message should indicate unavailability, got: {messages_pt['primary_message']}"
        # message_before_button should be the same for both 200 and 502
        assert messages_pt['message_before_button'] is not None, "PT message_before_button should exist"
        assert "memorial" in messages_pt['message_before_button'].lower()
        
        # Check English messages
        messages_en = extract_message_parts(data, "en")
        assert messages_en['primary_message'] is not None, "EN primary message should exist"
        assert ("temporarily" in messages_en['primary_message'].lower() or 
                "unavailable" in messages_en['primary_message'].lower()), \
            f"EN primary message should indicate unavailability, got: {messages_en['primary_message']}"
        assert messages_en['message_before_button'] is not None, "EN message_before_button should exist"


@pytest.mark.asyncio
async def test_custom_primary_message_with_default_button_messages(client):
    """
    Test that custom primary message is used while button messages stay default.

    When a site has a custom message_pt and message_en, only the primary message
    should change. The message_before_button and button_message should remain
    from DEFAULT_MESSAGES based on status code.
    """
    custom_pt = "Conteúdo preservado com versão customizada"
    custom_en = "Content preserved with custom version"

    with with_test_config({
        "custom-primary.example.com": {
            "version": "20200101000000",
            "status_code": 200,
            "message_pt": custom_pt,
            "message_en": custom_en,
        }
    }):
        response = await request_host(
            client, "/", "custom-primary.example.com", expected_status=200
        )

        data = await response.data
        
        # Check Portuguese messages
        messages_pt = extract_message_parts(data, "pt")
        assert messages_pt['primary_message'] == custom_pt, \
            f"Expected custom PT message '{custom_pt}', got: {messages_pt['primary_message']}"
        # Button messages should still be default
        assert "ver no arquivo" in messages_pt['button_message'].lower(), \
            f"Button message should be default, got: {messages_pt['button_message']}"
        
        # Check English messages
        messages_en = extract_message_parts(data, "en")
        assert messages_en['primary_message'] == custom_en, \
            f"Expected custom EN message '{custom_en}', got: {messages_en['primary_message']}"
        assert "browse" in messages_en['button_message'].lower(), \
            f"Button message should be default, got: {messages_en['button_message']}"


@pytest.mark.asyncio
async def test_button_message_contains_valid_text(client):
    """
    Test that button messages contain valid, non-empty text.

    Button messages should always be present and contain meaningful text,
    never None or empty strings.
    """
    with with_test_config({
        "button-test.example.com": {
            "version": "20200101000000",
        }
    }):
        response = await request_host(
            client, "/", "button-test.example.com", expected_status=200
        )

        data = await response.data
        
        # Check Portuguese button
        messages_pt = extract_message_parts(data, "pt")
        assert messages_pt['button_message'] is not None, "PT button_message should not be None"
        assert len(messages_pt['button_message'].strip()) > 0, \
            "PT button_message should not be empty"
        
        # Check English button
        messages_en = extract_message_parts(data, "en")
        assert messages_en['button_message'] is not None, "EN button_message should not be None"
        assert len(messages_en['button_message'].strip()) > 0, \
            "EN button_message should not be empty"


@pytest.mark.asyncio
async def test_message_before_button_contains_link(client):
    """
    Test that message_before_button contains proper HTML link tags.

    The message_before_button should contain an href to Arquivo.pt Memorial
    and be properly formatted with HTML tags.
    """
    with with_test_config({
        "link-test.example.com": {
            "version": "20200101000000",
        }
    }):
        response = await request_host(
            client, "/", "link-test.example.com", expected_status=200
        )

        data = await response.data
        
        # Check Portuguese link
        if isinstance(data, bytes):
            html = data.decode('utf-8')
        else:
            html = str(data)
        
        soup = BeautifulSoup(html, "html.parser")
        form = soup.find("form")
        assert form is not None, "Form should exist"
        
        # Find message_before_button paragraph in form (first p tag with lang="pt")
        pt_paragraphs = form.find_all("p", {"lang": "pt"})
        assert len(pt_paragraphs) > 0, "Should have Portuguese paragraph in form"
        
        # First paragraph should contain a link to arquivo.pt/memorial
        first_p = pt_paragraphs[0]
        link = first_p.find("a")
        assert link is not None, "Message should contain an anchor tag"
        assert "href" in link.attrs, "Link should have href attribute"
        assert "arquivo.pt/memorial" in link.attrs["href"], \
            f"Link should point to arquivo.pt/memorial, got: {link.attrs['href']}"


@pytest.mark.asyncio
async def test_message_structure_consistency_across_status_codes(client):
    """
    Test that message structure is consistent across different status codes.

    Both 200 and 502 status codes should have the same structure for
    message_before_button and button_message, only differing in primary_message.
    """
    with with_test_config({
        "status-200.example.com": {
            "version": "20200101000000",
            "status_code": 200,
        },
        "status-502.example.com": {
            "version": "20200101000000",
            "status_code": 502,
        },
    }):
        # Get 200 response
        response_200 = await request_host(
            client, "/", "status-200.example.com", expected_status=200
        )
        data_200 = await response_200.data
        messages_200_pt = extract_message_parts(data_200, "pt")
        
        # Get 502 response
        response_502 = await request_host(
            client, "/", "status-502.example.com", expected_status=502
        )
        data_502 = await response_502.data
        messages_502_pt = extract_message_parts(data_502, "pt")
        
        # Primary messages should differ
        assert messages_200_pt['primary_message'] != messages_502_pt['primary_message'], \
            "Primary messages should differ between status codes"
        
        # Button messages should be the same (same default messages)
        assert messages_200_pt['button_message'] == messages_502_pt['button_message'], \
            "Button messages should be identical across status codes"
        
        # message_before_button should be the same (same default messages)
        assert messages_200_pt['message_before_button'] == messages_502_pt['message_before_button'], \
            "message_before_button should be identical across status codes"


@pytest.mark.asyncio
async def test_message_before_button_with_partial_custom_message(client):
    """
    Test that message_before_button stays default when only message_pt is custom.

    When only message_pt is customized, message_en should get its default for
    the status code, and button messages should always come from defaults.
    """
    custom_pt = "Apenas mensagem portuguesa customizada"

    with with_test_config({
        "partial-custom.example.com": {
            "version": "20200101000000",
            "status_code": 502,
            "message_pt": custom_pt,
            # message_en is NOT set, should use default
        }
    }):
        response = await request_host(
            client, "/", "partial-custom.example.com", expected_status=502
        )

        data = await response.data
        
        # Check Portuguese messages
        messages_pt = extract_message_parts(data, "pt")
        assert messages_pt['primary_message'] == custom_pt, \
            "PT primary message should be custom"
        assert messages_pt['message_before_button'] is not None, \
            "PT message_before_button should use default"
        assert "memorial" in messages_pt['message_before_button'].lower(), \
            "PT message_before_button should contain 'memorial'"
        
        # Check English messages
        messages_en = extract_message_parts(data, "en")
        assert "temporarily" in messages_en['primary_message'].lower() or \
               "unavailable" in messages_en['primary_message'].lower(), \
            "EN primary message should use 502 default"
        assert messages_en['message_before_button'] is not None, \
            "EN message_before_button should use default"
        assert messages_en['button_message'] is not None, \
            "EN button_message should use default"
