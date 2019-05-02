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
        print("Title: {}".format(title.text))
        self.assertEqual(title.text, "Umic - In\\xc3\\xadcio")

        response = self.app.get('/', follow_redirects=True, headers={'Host': 'www.ligarportugal.pt'})
        self.assertEqual(response.status_code, 200)

        html = str(response.data)
        soup = BeautifulSoup(html, "html.parser")

        title = soup.find('title')
        print("Title: {}".format(title.text))
        self.assertEqual(title.text, "Ligar Portugal")


if __name__ == "__main__":
    unittest.main()
