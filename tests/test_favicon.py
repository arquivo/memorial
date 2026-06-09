"""
Favicon Endpoint Tests: Verify /favicon.ico redirects to Arquivo.pt archived version

Tests:
  - version handling
  - latest version fallback
  - www compatibility
  - unconfigured sites
"""

import pytest
from conftest import with_test_config


@pytest.mark.asyncio
async def test_favicon_redirect_with_version(client):
    """
    Test that favicon requests redirect to Arquivo.pt with the correct version.
    """
    with with_test_config(
        {
            "favicon-test.com": {
                "version": "20200117175504",
            }
        }
    ):
        response = await client.get("/favicon.ico", headers={"Host": "favicon-test.com"})
        assert response.status_code == 302  # Redirect status
        location = response.headers.get("Location", "")
        assert "arquivo.pt" in location
        assert "20200117175504" in location
        assert "favicon.ico" in location


@pytest.mark.asyncio
async def test_favicon_redirect_without_version(client):
    """
    Test that favicon requests redirect to latest version when no version specified.
    """
    with with_test_config({"favicon-noversion.com": {}}):
        response = await client.get("/favicon.ico", headers={"Host": "favicon-noversion.com"})
        assert response.status_code == 302
        location = response.headers.get("Location", "")
        assert "arquivo.pt" in location
        assert "favicon-noversion.com" in location
        assert "favicon.ico" in location


@pytest.mark.asyncio
async def test_favicon_with_www(client):
    """
    Test that favicon requests work correctly with www subdomain.
    """
    with with_test_config({"test-www.com": {"version": "20210101000000"}}):
        response = await client.get("/favicon.ico", headers={"Host": "www.test-www.com"})
        assert response.status_code == 302
        location = response.headers.get("Location", "")
        # Should normalize host to remove www
        assert "test-www.com" in location


@pytest.mark.asyncio
async def test_favicon_unconfigured_site(client):
    """
    Test favicon redirect for unconfigured site.
    """
    response = await client.get("/favicon.ico", headers={"Host": "unconfigured-favicon.com"})
    assert response.status_code == 302
    location = response.headers.get("Location", "")
    assert "arquivo.pt" in location
