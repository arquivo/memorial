import sys
import unittest

from bs4 import BeautifulSoup

sys.path.append('.')
from redirect_app import app


class BasicTests(unittest.TestCase):

    ############################
    #### setup and teardown ####
    ############################

    # executed prior to each test
    def setUp(self):
        app.config['WAYBACK_SERVER'] = 'https://arquivo.pt/wayback/'
        app.config['ARCHIVE_VERSIONS'] = {"www.umic.pt": "20190822151328", "cla.fccn.pt": "20180504071206"}
        # app.config['TEMPLATES'] = {"www.umic.pt": "redirect.html"}

        self.app = app.test_client()

    # executed after each test
    def tearDown(self):
        pass

    ###############
    #### tests ####
    ###############

    def test_main_page(self):
        # Fake host so it properly match the template
        response = self.app.get('/', follow_redirects=True, headers={'Host': 'www.umic.pt'})
        self.assertEqual(response.status_code, 200)

        html = str(response.data)
        soup = BeautifulSoup(html, "html.parser")

        title = soup.find('title')
        self.assertEqual(title.text, "Umic - In\\xc3\\xadcio")


if __name__ == "__main__":
    unittest.main()
