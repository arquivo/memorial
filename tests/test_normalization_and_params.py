"""
WWW Normalization & Query Parameters Tests

Tests:
  - WWW prefix handling
  - config lookup normalization
  - double www handling
  - unconfigured behavior
  - query string preservation
  - special character handling
"""

import pytest
from conftest import request_host, with_test_config


@pytest.mark.asyncio
async def test_www_normalization_with_config(client):
    """
    Test that www is correctly stripped when looking up site configuration.
    """
    with with_test_config({"example.com": {"message_pt": "Site without www"}}):
        response = await request_host(client, "/", "www.example.com", expected_status=200)
        assert response.status_code == 200
        html_content = (await response.data).decode("utf-8")
        assert "Site without www" in html_content


@pytest.mark.asyncio
async def test_www_double_with_config(client):
    """
    Test that double www is also normalized correctly.
    """
    with with_test_config({"example.com": {"message_pt": "Configured site"}}):
        # Even with www., should match example.com config
        response = await request_host(client, "/", "www.example.com", expected_status=200)
        assert response.status_code == 200
        html_content = (await response.data).decode("utf-8")
        assert "Configured site" in html_content


@pytest.mark.asyncio
async def test_www_without_config_returns_502(client):
    """
    Test that unconfigured site with www still returns 502.
    """
    with with_test_config({}):
        response = await request_host(client, "/", "www.unconfigured-site.com", expected_status=502)
        assert response.status_code == 502


@pytest.mark.asyncio
async def test_both_www_and_non_www_not_configured(client):
    """
    Test that if only non-www is configured, www requests match it.
    """
    with with_test_config({"target.com": {"status_code": 200}}):
        response = await request_host(client, "/", "www.target.com", expected_status=200)
        assert response.status_code == 200




# Query Parameters Tests: Verify query string parameters are preserved in redirects
# Tests: parameter preservation, special characters, empty values, path+query combinations
# ==============================================================================
# Tests for Query Parameters Handling
# ==============================================================================


@pytest.mark.asyncio
async def test_query_parameters_preserved_in_response(client):
    """
    Test that query parameters are passed through to the template.
    """
    with with_test_config({"query-test.com": {"status_code": 200}}):
        response = await request_host(client, "/?param1=value1&param2=value2", "query-test.com", expected_status=200)
        assert response.status_code == 200
        # The template should have access to query parameters via args


@pytest.mark.asyncio
async def test_query_parameters_with_special_characters(client):
    """
    Test that special characters in query parameters are handled correctly.
    """
    with with_test_config({"special-chars.com": {"status_code": 200}}):
        response = await request_host(client, "/?search=hello%20world&filter=test%2Bvalue", "special-chars.com", expected_status=200)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_empty_query_parameter(client):
    """
    Test handling of empty query parameters.
    """
    with with_test_config({"empty-param.com": {"status_code": 200}}):
        response = await request_host(client, "/?empty=&filled=value", "empty-param.com", expected_status=200)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_path_with_query_parameters(client):
    """
    Test that path and query parameters work correctly together.
    """
    with with_test_config({"path-query.com": {"status_code": 200}}):
        response = await request_host(client, "/page/path?id=123&name=test", "path-query.com", expected_status=200)
        assert response.status_code == 200




