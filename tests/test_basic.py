import unittest

from bs4 import BeautifulSoup
from memorial import app


class BasicTests(unittest.TestCase):

    # setup and teardown
    # executed prior to each test
    def setUp(self):
        self.app = app.test_client()

    # executed after each test
    def tearDown(self):
        pass

    def request_host(self, path, host):
        # Fake host so it properly match the template
        response = self.app.get(path, follow_redirects=True, headers={'Host': host})
        self.assertEqual(response.status_code, 200)
        return response

    def get_title(self, response_data):
        html = str(response_data)
        soup = BeautifulSoup(html, "html.parser")
        title = soup.find('title')
        print("Title: {}".format(title.text))
        return title.text

    def get_metadata(self, response_data, meta_tag):
        html = str(response_data)
        soup = BeautifulSoup(html, "html.parser")
        meta = soup.find('meta', {'name': meta_tag})
        print(meta_tag + ": {}".format(meta['content']))
        return meta['content']

    def test_nonexistent_page(self):
        response_nonexistent = self.request_host("/example-nonexistent", "www.antonioguterres.gov.pt")
        response_home = self.request_host("/", "www.antonioguterres.gov.pt")
        self.assertEqual(self.get_title(response_home.data), self.get_title(response_nonexistent.data))
        self.assertEqual(self.get_metadata(response_home.data, "description"), self.get_metadata(response_nonexistent.data, "description"))

    def test_inner_page(self):
        response_home = self.request_host("/", "www.antonioguterres.gov.pt")
        response_inner = self.request_host("/wp-content/uploads/2016/06/Antonio-Guterres-Portugal-Informal-dialogue-for-the-position-of-the-next-UN-Secretary-General.mp4", "www.antonioguterres.gov.pt")
        self.assertEqual(self.get_title(response_home.data), self.get_title(response_inner.data))
        self.assertEqual(self.get_metadata(response_home.data, "description"), self.get_metadata(response_inner.data, "description"))

        response_inner = self.request_host("/antonio-guterres-biography/", "www.antonioguterres.gov.pt")
        self.assertEqual(self.get_title(response_inner.data), "Ant\\xc3\\xb3nio Guterres, a lifetime dedicated to public service")
        self.assertEqual(self.get_metadata(response_inner.data, "description") ,"Ant\\xc3\\xb3nio Guterres served as United Nations High Commissioner for Refugees and he is a Candidate for the position of Secretary-General of the United Nations.")

        response_home = self.request_host("/", "www.portugalin.gov.pt")
        response_inner = self.request_host("/wp-content/plugins/so-widgets-bundle/icons/fontawesome/webfonts/fa-solid-900.woff2", "www.portugalin.gov.pt")
        self.assertEqual(self.get_title(response_home.data), self.get_title(response_inner.data))
        self.assertEqual(self.get_metadata(response_home.data, "description"), self.get_metadata(response_inner.data, "description"))

    def test_main_page(self):
        response = self.request_host("/", "www.umic.pt")
        self.assertEqual(self.get_title(response.data), "Umic - In\\xc3\\xadcio")
        self.assertEqual(self.get_metadata(response.data, "description"), 'UMIC - Ag\\xc3\\xaancia para a Sociedade do Conhecimento IP')

        response = self.request_host("/", "www.ligarportugal.pt")
        self.assertEqual(self.get_title(response.data), "Ligar Portugal")

    def test_robotstxt(self):
        # Fake host so it properly match the template
        response = self.request_host('/robots.txt', 'www.umic.pt')
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()