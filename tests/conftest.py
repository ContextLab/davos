import time
from os import getenv

import pytest
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


class NotebookDriver:
    def __init__(self, url, browser='firefox'):
        self.url = url
        if browser.lower() != 'firefox':
            raise NotImplementedError("Test only implemented for Firefox")
        self.driver = webdriver.Firefox(executable_path=getenv('DRIVER_PATH'))
        self.driver.get(url)


class ColabDriver(NotebookDriver):
    def __init__(self, notebook_path, browser='firefox'):
        username = getenv("GITHUB_ACTOR")
        ref = getenv("GITHUB_SHA")
        url = f"https://colab.research.google.com/github/{username}/davos/blob/{ref}/{notebook_path}"
        super().__init__(url=url, browser=browser)
        self.sign_in_google()

    def sign_in_google(self):
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
        
    def run_all_cells(self, pre_approved=False):
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


class JupyterDriver(NotebookDriver):
    def __init__(self, notebook_path, ip='127.0.0.1', port='8888', browser='firefox'):
        url = f"http://{ip}:{port}/notebooks/{notebook_path}"
        super().__init__(url=url, browser=browser)
        
    def run_all_cells(self):
        self.driver.find_element_by_id("run_all_cells").click()
        
    def set_kernel(self, kernel_name):
        self.driver.find_element_by_id(f"kernel-submenu-{kernel_name} > a").click()
        # allow time for kernel to change
        time.sleep(5)
