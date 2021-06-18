import time
from os import getenv

import pytest
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


class ColabNotebookDriver:
    def __init__(self, url, driver_path):
        self.driver = webdriver.Firefox(executable_path=driver_path)
        self.driver.get(url)
        self._sign_in_google()
        self._run_all_cells()

    def _sign_in_google(self):
        # click "Sign in" button
        self.driver.find_element_by_css_selector("#gb > div > div.gb_Se > a").click()
        # enter email
        email_input_box = self.driver.find_element_by_id("identifierId")
        email_input_box.send_keys(getenv("GMAIL_ADDRESS"))
        self.driver.find_element_by_id("identifierNext").click()
        # screen takes a moment to progress
        time.sleep(3)
        # enter password
        pwd_input_box = self.driver.find_element_by_name("password")
        pwd_input_box.send_keys(getenv("GMAIL_PASSWORD"))
        self.driver.find_element_by_id("passwordNext").click()

    def _run_all_cells(self, pre_approved=False):
        keyboard_shortcut = ActionChains(self.driver) \
            .key_down(Keys.META).send_keys() \
            .send_keys(Keys.F9) \
            .key_up(Keys.META)
        keyboard_shortcut.perform()
        if not pre_approved:
            # approve notebook not authored by Google
            # (button takes a second to become clickable)
            time.sleep(3)
            self.driver.find_element_by_id("ok").click()
