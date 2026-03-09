import unittest
from unittest.mock import Mock, patch

from bs4 import BeautifulSoup

from memorial import app


class BasicTests(unittest.TestCase):

    # setup and teardown
    # executed prior to each test
    def setUp(self):
        self.app = app.test_client()
        # Mock the requests to arquivo.pt to avoid network dependency
        self.patcher = patch("memorial.requests.Session")
        self.mock_session = self.patcher.start()

        # Create mock response objects
        mock_response = Mock()
        mock_response.ok = True
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

        # Configure the mock session
        mock_session_instance = Mock()
        mock_session_instance.head.return_value = mock_response
        mock_session_instance.get.return_value = mock_response
        self.mock_session.return_value = mock_session_instance

    # executed after each test
    def tearDown(self):
        self.patcher.stop()

    def request_host(self, path, host):
        # Fake host so it properly match the template
        response = self.app.get(path, follow_redirects=True, headers={"Host": host})
        self.assertEqual(response.status_code, 200)
        return response

    def get_title(self, response_data):
        html = str(response_data)
        soup = BeautifulSoup(html, "html.parser")
        title = soup.find("title")
        if title:
            print(f"Title: {title.text}")
            return title.text
        print("Title: None (not found)")
        return None

    def get_metadata(self, response_data, meta_tag):
        html = str(response_data)
        soup = BeautifulSoup(html, "html.parser")
        meta = soup.find("meta", {"name": meta_tag})
        if meta and "content" in meta.attrs:
            print(f"{meta_tag}: {meta['content']}")
            return meta["content"]
        print(f"{meta_tag}: None (not found)")
        return None

    def test_nonexistent_page(self):
        response_nonexistent = self.request_host("/example-nonexistent", "www.antonioguterres.gov.pt")
        response_home = self.request_host("/", "www.antonioguterres.gov.pt")
        title_home = self.get_title(response_home.data)
        title_nonexistent = self.get_title(response_nonexistent.data)
        # Both should have the same title from the archived page
        self.assertEqual(title_home, title_nonexistent)

        desc_home = self.get_metadata(response_home.data, "description")
        desc_nonexistent = self.get_metadata(response_nonexistent.data, "description")
        self.assertEqual(desc_home, desc_nonexistent)

    def test_inner_page(self):
        response_home = self.request_host("/", "www.antonioguterres.gov.pt")
        response_inner = self.request_host(
            "/wp-content/uploads/2016/06/Antonio-Guterres-Portugal-Informal-dialogue-for-the-position-of-the-next-UN-Secretary-General.mp4",
            "www.antonioguterres.gov.pt",
        )
        # Non-HTML content should fall back to home page metadata
        self.assertEqual(self.get_title(response_home.data), self.get_title(response_inner.data))
        self.assertEqual(
            self.get_metadata(response_home.data, "description"), self.get_metadata(response_inner.data, "description")
        )

        response_inner = self.request_host("/antonio-guterres-biography/", "www.antonioguterres.gov.pt")
        # With mocked responses, we get consistent test data
        title = self.get_title(response_inner.data)
        self.assertIsNotNone(title)
        desc = self.get_metadata(response_inner.data, "description")
        self.assertIsNotNone(desc)

        response_home = self.request_host("/", "www.portugalin.gov.pt")
        response_inner = self.request_host(
            "/wp-content/plugins/so-widgets-bundle/icons/fontawesome/webfonts/fa-solid-900.woff2",
            "www.portugalin.gov.pt",
        )
        self.assertEqual(self.get_title(response_home.data), self.get_title(response_inner.data))
        self.assertEqual(
            self.get_metadata(response_home.data, "description"), self.get_metadata(response_inner.data, "description")
        )

    def test_main_page(self):
        response = self.request_host("/", "www.umic.pt")
        title = self.get_title(response.data)
        # With mocked responses, we should get our test title
        self.assertIsNotNone(title)
        desc = self.get_metadata(response.data, "description")
        self.assertIsNotNone(desc)

        response = self.request_host("/", "www.ligarportugal.pt")
        title = self.get_title(response.data)
        self.assertIsNotNone(title)

    def test_robotstxt(self):
        # Fake host so it properly match the template
        response = self.request_host("/robots.txt", "www.umic.pt")
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
