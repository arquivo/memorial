"""
Memorial View Tests: Verify the /memorial/<site>/view preview on Arquivo.pt domains

Tests:
  - the preview shows the same page and status code as the memorial site
  - unconfigured sites show the default page
  - the site image and favicon routes of the preview
  - on memorial sites, the preview paths are regular paths
  - MEMORIAL_VIEW_HOSTS configuration
"""

from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup
from conftest import get_title, request_host, with_test_config

from memorial import app

SITE_CONFIG = {
    "example.pt": {
        "version": "20200117175504",
        "message_pt": "Mensagem do example.pt",
        "message_en": "Message of example.pt",
        "title": "Example",
        "metadata": [],
    },
    "nau.edu.pt": {
        "version": "20240101000000",
        "status_code": 502,
        "title": "NAU",
        "metadata": [],
    },
}


async def get_page(client, site_path, host):
    """Request a path and return the response and its parsed HTML."""
    response = await client.get(site_path, headers={"Host": host})
    soup = BeautifulSoup(await response.get_data(as_text=True), "html.parser")
    return response, soup


@pytest.mark.asyncio
async def test_view_matches_memorial_site(client):
    """The preview shows the same messages, archive link and status code as the site home page."""
    with with_test_config(SITE_CONFIG):
        site_response, site_soup = await get_page(client, "/", "example.pt")
        view_response, view_soup = await get_page(client, "/memorial/example.pt/view", "arquivo.pt")

        assert view_response.status_code == site_response.status_code == 200
        assert "Mensagem do example.pt" in str(view_soup)
        assert view_soup.find("form")["action"] == site_soup.find("form")["action"]
        assert view_soup.find("form")["action"] == "https://arquivo.pt/wayback/20200117175504/http://example.pt/"
        assert get_title(view_soup) == "Example"


@pytest.mark.asyncio
async def test_view_keeps_maintenance_template_and_status_code(client):
    """A site configured with a 502 status code previews its maintenance page with the same status code."""
    with with_test_config(SITE_CONFIG):
        site_response, _ = await get_page(client, "/", "nau.edu.pt")
        view_response, view_soup = await get_page(client, "/memorial/nau.edu.pt/view", "arquivo.pt")

        assert view_response.status_code == site_response.status_code == 502
        assert get_title(view_soup) == "NAU: Em manutenção"


@pytest.mark.asyncio
async def test_view_unconfigured_site_shows_default_page(client):
    """A site without configuration previews the same default page as an unconfigured host."""
    with with_test_config(SITE_CONFIG):
        site_response, site_soup = await get_page(client, "/", "unknown.pt")
        view_response, view_soup = await get_page(client, "/memorial/unknown.pt/view", "arquivo.pt")

        assert view_response.status_code == site_response.status_code
        assert view_soup.find("form")["action"] == "https://arquivo.pt/wayback/http://unknown.pt/"
        assert view_soup.find("form")["action"] == site_soup.find("form")["action"]


@pytest.mark.asyncio
async def test_view_with_www_site(client):
    """A www. site previews the configuration of the site without www., like the memorial site."""
    with with_test_config(SITE_CONFIG):
        _, view_soup = await get_page(client, "/memorial/www.example.pt/view", "arquivo.pt")

        assert "Mensagem do example.pt" in str(view_soup)
        assert view_soup.find("form")["action"] == "https://arquivo.pt/wayback/20200117175504/http://www.example.pt/"


@pytest.mark.asyncio
async def test_view_site_is_case_insensitive(client):
    """The site of the preview is normalized to lower case, like host names."""
    with with_test_config(SITE_CONFIG):
        _, view_soup = await get_page(client, "/memorial/Example.PT/view", "arquivo.pt")

        assert "Mensagem do example.pt" in str(view_soup)


@pytest.mark.asyncio
@pytest.mark.parametrize("site", ["exa mple.pt", "example.pt%3Cscript%3E", "example.pt:port"])
async def test_view_rejects_invalid_site(client, site):
    """A site that is not a host name returns 404."""
    with with_test_config(SITE_CONFIG):
        await request_host(client, f"/memorial/{site}/view", "arquivo.pt", expected_status=404)


@pytest.mark.asyncio
async def test_view_links_to_preview_image_and_favicon(client):
    """The preview page loads the site image and favicon from the preview routes."""
    with with_test_config(SITE_CONFIG):
        _, view_soup = await get_page(client, "/memorial/example.pt/view", "arquivo.pt")
        _, site_soup = await get_page(client, "/", "example.pt")

        assert view_soup.find("img")["src"] == "/memorial/example.pt/memorial-site-image"
        assert view_soup.find("link", rel="icon")["href"] == "/memorial/example.pt/favicon.ico"
        assert site_soup.find("img")["src"] == "/memorial-site-image"
        assert site_soup.find("link", rel="icon")["href"] == "/favicon.ico"


@pytest.mark.asyncio
async def test_view_favicon_redirects_to_archived_favicon(client):
    """The preview favicon redirects to the same archived favicon as the memorial site."""
    with with_test_config(SITE_CONFIG):
        site_response = await request_host(client, "/favicon.ico", "example.pt", expected_status=302)
        view_response = await request_host(
            client, "/memorial/example.pt/favicon.ico", "arquivo.pt", expected_status=302
        )

        assert view_response.headers["Location"] == site_response.headers["Location"]
        assert view_response.headers["Location"].endswith("/20200117175504/example.pt/favicon.ico")


@pytest.mark.asyncio
async def test_view_site_image_serves_site_image(client):
    """The preview site image looks up the image of the site."""
    with with_test_config(SITE_CONFIG):
        with patch("memorial.serve_site_image") as mock_serve_site_image:
            mock_serve_site_image.return_value = "image"
            await request_host(client, "/memorial/example.pt/memorial-site-image", "arquivo.pt")

            mock_serve_site_image.assert_called_once_with("example.pt")


@pytest.mark.asyncio
@pytest.mark.parametrize("host", ["arquivo.pt", "www.arquivo.pt", "preprod.arquivo.pt", "dev.arquivo.pt:443"])
async def test_view_on_default_hosts(client, host):
    """The preview is available on the Arquivo.pt domains by default."""
    with with_test_config(SITE_CONFIG):
        _, view_soup = await get_page(client, "/memorial/example.pt/view", host)

        assert "Mensagem do example.pt" in str(view_soup)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "site_path",
    ["/memorial/example.pt/view", "/memorial/example.pt/memorial-site-image", "/memorial/example.pt/favicon.ico"],
)
async def test_preview_paths_on_memorial_site_show_memorial_page(client, site_path):
    """On a memorial site, the preview paths show the landing page of that site."""
    with with_test_config(SITE_CONFIG):
        response, soup = await get_page(client, site_path, "nau.edu.pt")

        assert response.status_code == 502
        assert get_title(soup) == "NAU: Em manutenção"


@pytest.mark.asyncio
async def test_view_hosts_configuration(client):
    """MEMORIAL_VIEW_HOSTS replaces the default Arquivo.pt domains."""
    with with_test_config(SITE_CONFIG):
        with patch.dict(app.config, {"MEMORIAL_VIEW_HOSTS": ["localhost"]}):
            _, local_soup = await get_page(client, "/memorial/example.pt/view", "localhost:5000")
            _, arquivo_soup = await get_page(client, "/memorial/example.pt/view", "arquivo.pt")

            assert "Mensagem do example.pt" in str(local_soup)
            assert "Mensagem do example.pt" not in str(arquivo_soup)
