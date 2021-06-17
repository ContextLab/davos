import time

from seleniumbase import BaseCase


class MyTestClass(BaseCase):
    def test_basics(self):
        url = "https://colab.research.google.com/github/paxtonfitzpatrick/davos/blob/main/tests/test_davos_colab.ipynb"
        self.open(url)
        # sign in with Google account
        self.click("#gb > div > div.gb_Se > a")
        self.type("#identifierId", '<EMAIL HERE>')
        self.click("#identifierNext > div > button")
        time.sleep(3)
        self.type("#password > div.aCsJod.oJeWuf > div > div.Xb9hP > input", "<PASSWORD HERE>")
        self.click("#passwordNext > div > button")
        # run all cells
        self.click("#runtime-menu-button > div > div > div.goog-inline-block.goog-menu-button-caption")
        self.click("#\\:1s")
        # approve notebook not authored by Google (button takes a second 
        # to become clickable)
        time.sleep(3)
        self.click("#ok")
        time.sleep(3)
