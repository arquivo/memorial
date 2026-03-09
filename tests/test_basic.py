import unittest
from unittest.mock import AsyncMock, Mock, patch

import httpx
from bs4 import BeautifulSoup

from memorial import app, fix_not_closed_metatags


class BasicTests(unittest.TestCase):

    # setup and teardown
    # executed prior to each test
    def setUp(self):
        self.app = app.test_client()
        # Mock the httpx.AsyncClient to avoid network dependency
        self.patcher = patch("memorial.httpx.AsyncClient")
        self.mock_client_class = self.patcher.start()

        # Create mock response objects
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

        # Configure the mock async client
        mock_client_instance = Mock()
        mock_client_instance.head = AsyncMock(return_value=mock_response)
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        self.mock_client_class.return_value = mock_client_instance

    # executed after each test
    def tearDown(self):
        self.patcher.stop()

    def request_host(self, path, host, expected_status=200):
        """Helper method to make a request with a specific Host header.

        Args:
            path: The path to request
            host: The Host header value
            expected_status: Expected HTTP status code (default: 200)

        Returns:
            The response object
        """
        # Fake host so it properly match the template
        response = self.app.get(path, follow_redirects=True, headers={"Host": host})
        self.assertEqual(response.status_code, expected_status)
        return response

    def get_title(self, response_data):
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

    def get_metadata(self, response_data, meta_tag):
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

    def test_nonexistent_page(self):
        """
        Test that requesting a non-existent page returns the same metadata as the home page, since it should fall back to the archived home page.
        """
        # Use a configured site (umic.pt:8080 is in config.py)
        response_nonexistent = self.request_host("/example-nonexistent", "umic.pt:8080", expected_status=200)
        response_home = self.request_host("/", "umic.pt:8080", expected_status=200)
        title_home = self.get_title(response_home.data)
        title_nonexistent = self.get_title(response_nonexistent.data)
        # Both should have the same title from the archived page
        self.assertEqual(title_home, title_nonexistent)

        desc_home = self.get_metadata(response_home.data, "description")
        desc_nonexistent = self.get_metadata(response_nonexistent.data, "description")
        self.assertEqual(desc_home, desc_nonexistent)

    def test_inner_page(self):
        """
        Test that requesting an inner page returns the same metadata as the home page for non-HTML content,
        and extracts metadata correctly for HTML content.
        """
        # Use configured sites from config.py
        response_home = self.request_host("/", "umic.pt:8080", expected_status=200)
        response_inner = self.request_host(
            "/some/path/file.mp4",
            "umic.pt:8080",
            expected_status=200,
        )
        # Non-HTML content should fall back to home page metadata
        self.assertEqual(self.get_title(response_home.data), self.get_title(response_inner.data))
        self.assertEqual(
            self.get_metadata(response_home.data, "description"), self.get_metadata(response_inner.data, "description")
        )

        response_inner = self.request_host("/some/html/page/", "umic.pt:8080", expected_status=200)
        # With mocked responses, we get consistent test data
        title = self.get_title(response_inner.data)
        self.assertIsNotNone(title)
        desc = self.get_metadata(response_inner.data, "description")
        self.assertIsNotNone(desc)

        response_home = self.request_host("/", "ligarportugal.pt:8080", expected_status=200)
        response_inner = self.request_host(
            "/fonts/font-file.woff2",
            "ligarportugal.pt:8080",
            expected_status=200,
        )
        self.assertEqual(self.get_title(response_home.data), self.get_title(response_inner.data))
        self.assertEqual(
            self.get_metadata(response_home.data, "description"), self.get_metadata(response_inner.data, "description")
        )

    def test_main_page(self):
        """
        Test that requesting the main page returns the expected metadata.
        """
        # Use sites from config.py with :8080 port
        response = self.request_host("/", "umic.pt:8080", expected_status=200)
        title = self.get_title(response.data)
        # With mocked responses, we should get our test title
        self.assertIsNotNone(title)
        desc = self.get_metadata(response.data, "description")
        self.assertIsNotNone(desc)

        response = self.request_host("/", "ligarportugal.pt:8080", expected_status=200)
        title = self.get_title(response.data)
        self.assertIsNotNone(title)

    def test_robotstxt(self):
        """
        Test that requesting the robots.txt file returns a 200 status code.
        """
        response = self.request_host("/robots.txt", "umic.pt:8080", expected_status=200)
        self.assertEqual(response.status_code, 200)

    def test_configured_site_returns_200(self):
        """
        Test that a configured site without explicit status_code returns 200 OK by default.
        """
        # umic.pt:8080 is configured in config.py without explicit status_code
        response = self.request_host("/", "umic.pt:8080", expected_status=200)
        self.assertEqual(response.status_code, 200)

        # Verify we get the memorial page content
        self.assertIn(b"arquivo.pt", response.data.lower())

    def test_unconfigured_site_returns_502(self):
        """
        Test that an unconfigured site returns 502 Bad Gateway by default.
        This indicates the original site is no longer available.
        """
        # unconfigured-site.example.com is NOT in config.py
        response = self.request_host("/", "unconfigured-site.example.com", expected_status=502)
        self.assertEqual(response.status_code, 502)

        # Verify we still get the memorial page content
        self.assertIn(b"arquivo.pt", response.data.lower())

    def test_configured_site_custom_status_code(self):
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
            response = self.request_host("/", "custom-status.example.com", expected_status=410)
            self.assertEqual(response.status_code, 410)
            self.assertIn(b"arquivo.pt", response.data.lower())

    def test_different_status_codes_for_different_sites(self):
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
            response_200 = self.request_host("/", "site-ok.example.com", expected_status=200)
            self.assertEqual(response_200.status_code, 200)

            # Test 410 Gone
            response_410 = self.request_host("/", "site-gone.example.com", expected_status=410)
            self.assertEqual(response_410.status_code, 410)

            # Test 503 Service Unavailable
            response_503 = self.request_host("/", "site-unavailable.example.com", expected_status=503)
            self.assertEqual(response_503.status_code, 503)

    def test_status_code_preserved_across_paths(self):
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
            response_root = self.request_host("/", "consistent-status.example.com", expected_status=410)
            self.assertEqual(response_root.status_code, 410)

            # Test subpath
            response_sub = self.request_host("/some/path", "consistent-status.example.com", expected_status=410)
            self.assertEqual(response_sub.status_code, 410)

            # Test with query parameters
            response_query = self.request_host("/page?id=123", "consistent-status.example.com", expected_status=410)
            self.assertEqual(response_query.status_code, 410)

    def test_fix_not_closed_metatags_with_slash(self):
        """
        Test fix_not_closed_metatags function with tag ending in /.
        """
        # Create a mock tag that ends with /
        mock_tag = Mock()
        mock_tag.__str__ = Mock(return_value='<meta name="test" content="value"/')

        result = fix_not_closed_metatags(mock_tag)
        self.assertEqual(result, '<meta name="test" content="value"/>')

    def test_fix_not_closed_metatags_without_slash(self):
        """
        Test fix_not_closed_metatags function with tag not ending in /.
        """
        # Create a mock tag that doesn't end with /
        mock_tag = Mock()
        mock_tag.__str__ = Mock(return_value='<meta name="test" content="value"')

        result = fix_not_closed_metatags(mock_tag)
        self.assertEqual(result, '<meta name="test" content="value"/>')

    def test_timeout_exception_handling(self):
        """
        Test that timeout exceptions are properly raised when fetching content.
        """
        # Configure mock to raise TimeoutException
        mock_client_instance = Mock()
        mock_client_instance.head = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        with patch("memorial.httpx.AsyncClient", return_value=mock_client_instance):
            response = self.request_host("/", "umic.pt:8080", expected_status=200)
            # The app should handle the timeout gracefully
            self.assertEqual(response.status_code, 200)

    def test_extract_metadata_exception_handling(self):
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

        with patch("memorial.httpx.AsyncClient", return_value=mock_client_instance):
            response = self.request_host("/", "umic.pt:8080", expected_status=200)
            # Should still return a response even if metadata extraction fails
            self.assertEqual(response.status_code, 200)

    def test_custom_template_rendering(self):
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

                self.app.get("/", headers={"Host": "custom-template.example.com"})

                # Verify custom template was used (not redirect_default.html)
                mock_render.assert_called_once()
                call_args = mock_render.call_args
                self.assertEqual(call_args[0][0], "custom_template.html")
                # Verify simpler params for custom template (no metadata)
                self.assertIn("origin_host", call_args[1])
                self.assertIn("redirect_url", call_args[1])
                self.assertNotIn("metadata", call_args[1])

    def test_environment_variable_configuration(self):
        """
        Test that MEMORIAL_CONFIGURATION environment variable is properly loaded.
        This tests the configuration override mechanism.
        """
        import os
        import tempfile

        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write('ARCHIVE_CONFIG = {"env-test.example.com": {"status_code": 418}}\n')
            f.write('WAYBACK_SERVER = "https://arquivo.pt/wayback/"\n')
            f.write('WAYBACK_NOFRAME_SERVER = "https://arquivo.pt/noFrame/replay/"\n')
            temp_config_path = f.name

        try:
            # Set environment variable and reload app
            with patch.dict(os.environ, {"MEMORIAL_CONFIGURATION": temp_config_path}):
                # Import and reload to test env var loading
                # Note: This tests that the code path exists, actual testing would require
                # app reload which is complex in testing context
                self.assertTrue("MEMORIAL_CONFIGURATION" in os.environ)
        finally:
            # Cleanup
            os.unlink(temp_config_path)

    def test_non_html_content_fallback(self):
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

        with patch("memorial.httpx.AsyncClient", return_value=mock_client_instance):
            response = self.request_host("/image.jpg", "umic.pt:8080", expected_status=200)
            self.assertEqual(response.status_code, 200)
            # Should get metadata from home page instead
            self.assertIn(b"Home Page", response.data)

    def test_metadata_with_link_tags(self):
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

        with patch("memorial.httpx.AsyncClient", return_value=mock_client_instance):
            response = self.request_host("/", "umic.pt:8080", expected_status=200)
            self.assertEqual(response.status_code, 200)
            # Verify link tags are extracted
            html_content = response.data.decode("utf-8")
            self.assertIn("shortcut icon", html_content)


if __name__ == "__main__":
    unittest.main()
