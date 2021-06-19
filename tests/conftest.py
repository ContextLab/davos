import json
import re
import time
from os import getenv
from pathlib import Path

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
            
    def get_test_result(self, func_name):
        # TODO: implement me
        return True


class JupyterDriver(NotebookDriver):
    def __init__(self, notebook_path, ip='127.0.0.1', port='8888', browser='firefox'):
        url = f"http://{ip}:{port}/notebooks/{notebook_path}"
        super().__init__(url=url, browser=browser)
        self.set_kernel('kernel-env')
        
    def run_all_cells(self):
        self.driver.find_element_by_id("run_all_cells").click()
        
    def get_test_result(self, func_name):
        # TODO: implement me
        return True
        
    def set_kernel(self, kernel_name):
        self.driver.find_element_by_id(f"kernel-submenu-{kernel_name} > a").click()
        # allow time for kernel to change
        time.sleep(5)


class NotebookFile(pytest.File):
    test_func_pattern = re.compile('(?<=def )test_[^(]+', re.MULTILINE)

    def __init__(self, fspath, *, driver_cls, parent=None, config=None, session=None, nodeid=None):
        super().__init__(fspath=fspath, parent=parent, config=config, session=session, nodeid=nodeid)
        self.driver_cls = driver_cls
        self.driver = None
        repo_root = Path(getenv("GITHUB_WORKSPACE")).resolve(strict=True)
        notebook_abspath = Path(self.fspath).resolve(strict=True)
        self.notebook_path = str(notebook_abspath.relative_to(repo_root))
        
    def collect(self):
        with self.fspath.open() as nb:
            notebook_json = json.load(nb)
        for cell in notebook_json['cells']:
            if cell['cell_type'] == 'code':
                cell_contents = ''.join(cell['source'])
                # noinspection PyCompatibility
                # TODO: make sure tests_require is being enforced
                if match := self.test_func_pattern.search(cell_contents):
                    yield NotebookTest.from_parent(self, name=match.group())
    
    def setup(self):
        super().setup()
        self.driver = self.driver_cls(self.notebook_path)
        self.driver.run_all_cells()
    
    def teardown(self):
        self.driver.quit()
        return super().teardown()
        

class NotebookTest(pytest.Item):
    def runtest(self): 
        test_result = self.parent.driver.get_test_result(self.name)
        return test_result
    
    def repr_failure(self, execinfo):
        # TODO: write me
        ...
    
    def reportinfo(self):
        # TODO: write me
        return self.fspath, None, ""
        

def pytest_collect_file(path, parent):
    notebook_type = getenv("NOTEBOOK_TYPE")
    if notebook_type == 'colab':
        driver_cls = ColabDriver
    else:
        driver_cls = JupyterDriver
    if path.basename.startswith('test') and path.ext == ".ipynb":
        if any(key in path.basename for key in (notebook_type, 'shared', 'common')):
            return NotebookFile.from_parent(parent, fspath=path, driver_cls=driver_cls)
