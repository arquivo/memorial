"""
Maintenance Template Tests

Tests for the maintenance page template selection feature:
  - Template lookup by hostname
  - Fallback chain for subdomains
  - 502 status code handling
  - Custom maintenance templates per domain
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from conftest import request_host, with_test_config

from memorial import app, get_maintenance_template


@pytest.fixture
def maintenance_folder():
    """Fixture providing a clean maintenance folder for tests."""
    templates_folder = Path(__file__).parent.parent / "templates" / "maintenance"
    templates_folder.mkdir(parents=True, exist_ok=True)
    
    # Track which files existed before the test
    existing_files = set(templates_folder.glob("*.html"))
    
    yield templates_folder
    
    # Cleanup: remove only html files created during the test, not pre-existing ones
    current_files = set(templates_folder.glob("*.html"))
    for html_file in current_files - existing_files:
        html_file.unlink()


class TestMaintenanceTemplateLookup:
    """Tests for the get_maintenance_template function."""

    @staticmethod
    def create_template(folder, filename, content="<html>Test</html>"):
        """Helper to create a template file."""
        os.makedirs(folder, exist_ok=True)
        file_path = os.path.join(folder, filename)
        with open(file_path, "w") as f:
            f.write(content)
        return file_path

    def test_exact_match_template(self, maintenance_folder):
        """Test finding exact match template for a domain."""
        templates_folder_str = str(maintenance_folder.absolute())
        self.create_template(templates_folder_str, "example_com.html")

        with patch.dict(app.config, {"MAINTENANCE_FOLDER": "maintenance"}):
            result = get_maintenance_template("example.com")
            assert result == "maintenance/example_com.html"

    def test_subdomain_fallback_to_second_level(self, maintenance_folder):
        """Test that subdomain falls back to second-level domain template."""
        templates_folder_str = str(maintenance_folder.absolute())
        self.create_template(templates_folder_str, "example_com.html")

        with patch.dict(app.config, {"MAINTENANCE_FOLDER": "maintenance"}):
            result = get_maintenance_template("sub.example.com")
            assert result == "maintenance/example_com.html"

    def test_subdomain_exact_match_preferred(self, maintenance_folder):
        """Test that subdomain exact match is preferred over fallback."""
        templates_folder_str = str(maintenance_folder.absolute())
        self.create_template(templates_folder_str, "sub_example_com.html")
        self.create_template(templates_folder_str, "example_com.html")

        with patch.dict(app.config, {"MAINTENANCE_FOLDER": "maintenance"}):
            result = get_maintenance_template("sub.example.com")
            assert result == "maintenance/sub_example_com.html"

    def test_fallback_to_default(self):
        """Test fallback to redirect_default.html when no maintenance template exists."""
        with patch.dict(app.config, {"MAINTENANCE_FOLDER": "maintenance"}):
            result = get_maintenance_template("unknown.example.com")
            assert result == "redirect_default.html"

    def test_three_level_subdomain_fallback(self, maintenance_folder):
        """Test three-level subdomain falls back through the hierarchy."""
        templates_folder_str = str(maintenance_folder.absolute())
        self.create_template(templates_folder_str, "example_com.html")

        with patch.dict(app.config, {"MAINTENANCE_FOLDER": "maintenance"}):
            result = get_maintenance_template("a.b.example.com")
            assert result == "maintenance/example_com.html"

    def test_nonexistent_folder(self):
        """Test graceful handling when maintenance folder doesn't exist."""
        with patch.dict(app.config, {"MAINTENANCE_FOLDER": "/nonexistent/path"}):
            result = get_maintenance_template("example.com")
            assert result == "redirect_default.html"

    def test_port_stripping(self, maintenance_folder):
        """Test that port numbers are stripped from host before template lookup."""
        templates_folder_str = str(maintenance_folder.absolute())
        self.create_template(templates_folder_str, "example_com.html")

        with patch.dict(app.config, {"MAINTENANCE_FOLDER": "maintenance"}):
            # Host with port should still find the template
            result = get_maintenance_template("example.com:5000")
            assert result == "maintenance/example_com.html"

    def test_subdomain_with_port(self, maintenance_folder):
        """Test that subdomain with port number is handled correctly."""
        templates_folder_str = str(maintenance_folder.absolute())
        self.create_template(templates_folder_str, "sub_example_com.html")

        with patch.dict(app.config, {"MAINTENANCE_FOLDER": "maintenance"}):
            # Host with port and subdomain should find the subdomain template
            result = get_maintenance_template("sub.example.com:8080")
            assert result == "maintenance/sub_example_com.html"


class TestMaintenancePageRendering:
    """Tests for rendering maintenance pages in responses."""

    @pytest.mark.asyncio
    async def test_502_status_code_returned(self, client):
        """Test that 502 status code is returned correctly."""
        with with_test_config(
            {
                "maint-test502.example.com": {
                    "status_code": 502,
                    "extract_metadata": False,
                }
            }
        ):
            response = await request_host(
                client, "/", "maint-test502.example.com", expected_status=502
            )
            assert response.status_code == 502

    @pytest.mark.asyncio
    async def test_200_status_code_returned(self, client):
        """Test that 200 status code is returned correctly."""
        with with_test_config(
            {
                "maint-test200.example.com": {
                    "status_code": 200,
                    "extract_metadata": False,
                }
            }
        ):
            response = await request_host(
                client, "/", "maint-test200.example.com", expected_status=200
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_502_defaults_to_default_template(self, client):
        """Test that 502 uses redirect_default.html when no maintenance template exists."""
        with with_test_config(
            {
                "maint-notemplate.example.com": {
                    "status_code": 502,
                    "extract_metadata": False,
                }
            }
        ):
            response = await request_host(
                client, "/", "maint-notemplate.example.com", expected_status=502
            )
            html = await response.data
            # Should still render successfully with default template
            assert b"Arquivo.pt Memorial" in html or b"Arquivo" in html

    @pytest.mark.asyncio
    async def test_503_service_unavailable_status_code(self, client):
        """Test that 503 status code is returned correctly."""
        with with_test_config(
            {
                "maint-test503.example.com": {
                    "status_code": 503,
                    "extract_metadata": False,
                }
            }
        ):
            response = await request_host(
                client, "/", "maint-test503.example.com", expected_status=503
            )
            assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_504_gateway_timeout_status_code(self, client):
        """Test that 504 status code is returned correctly."""
        with with_test_config(
            {
                "maint-test504.example.com": {
                    "status_code": 504,
                    "extract_metadata": False,
                }
            }
        ):
            response = await request_host(
                client, "/", "maint-test504.example.com", expected_status=504
            )
            assert response.status_code == 504

    @pytest.mark.asyncio
    async def test_custom_message_in_502_response(self, client):
        """Test that custom messages are rendered in 502 responses."""
        custom_msg = "This site is temporarily unavailable due to maintenance"
        with with_test_config(
            {
                "maint-custom.example.com": {
                    "status_code": 502,
                    "message_pt": custom_msg,
                    "extract_metadata": False,
                }
            }
        ):
            response = await request_host(
                client, "/", "maint-custom.example.com", expected_status=502
            )
            html = await response.data
            assert custom_msg.encode() in html

    @pytest.mark.asyncio
    async def test_default_messages_in_502_response(self, client):
        """Test that default 502 messages are used when custom messages not provided."""
        with with_test_config(
            {
                "maint-default-msg.example.com": {
                    "status_code": 502,
                    "extract_metadata": False,
                }
            }
        ):
            response = await request_host(
                client, "/", "maint-default-msg.example.com", expected_status=502
            )
            html = await response.data
            # Should contain the default 502 message
            assert (
                b"temporariamente indispon\xc3\xadvel" in html
                or b"temporarily unavailable" in html
            )

    @pytest.mark.asyncio
    async def test_200_status_different_message(self, client):
        """Test that 200 status code uses different default message than 502."""
        with with_test_config(
            {
                "maint-code200.example.com": {
                    "status_code": 200,
                    "extract_metadata": False,
                }
            }
        ):
            response = await request_host(
                client, "/", "maint-code200.example.com", expected_status=200
            )
            html = await response.data
            # Should contain the default 200 message (site has been disabled, not temporarily unavailable)
            assert b"desactivado" in html or b"disabled" in html

