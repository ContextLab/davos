import html
import json
import re
import time
from os import getenv
from pathlib import Path

import pytest
from selenium import webdriver
from selenium.common.exceptions import (
    ElementNotInteractableException, 
    TimeoutException,
    WebDriverException
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class element_has_class:
    def __init__(self, locator, cls_name):
        self.locator = locator
        self.cls_name = cls_name
        
    def __call__(self, driver):
        element = driver.find_element(*self.locator)
        if self.cls_name in element.get_attribute('class').split():
            return element
        return False
    

class NotebookTestFailed(Exception):
    def __init__(self, tb_str):
        self.tb_str = tb_str
        super().__init__()


class NotebookDriver:
    def __init__(self, url, browser='firefox'):
        self.url = url
        if browser.lower() != 'firefox':
            raise NotImplementedError("Test only implemented for Firefox")
        options = Options()
        options.headless = True
        self.driver = webdriver.Firefox(options=options, 
                                        executable_path=getenv('DRIVER_PATH'))
        self.driver.get(url)
        
    def click(
            self, 
            __locator_or_el, 
            /,
            by=By.CSS_SELECTOR, 
            timeout=10, 
            poll_frequency=0.5, 
            ignored_exceptions=None
    ):
        if isinstance(__locator_or_el, WebElement):
            start_time = time.time()
            while True:
                try:
                    __locator_or_el.click()
                except (ElementNotInteractableException, *ignored_exceptions) as e:
                    if time.time() - start_time >= timeout:
                        raise TimeoutException(
                            f"{__locator_or_el} was not clickable after "
                            f"{timeout} seconds"
                        ) from e
                    else:
                        pass
                else:
                    return __locator_or_el
        else:
            wait = WebDriverWait(self.driver, timeout=timeout, 
                                 poll_frequency=poll_frequency, 
                                 ignored_exceptions=ignored_exceptions)
            locator = (by, __locator_or_el)
            element_is_visible = EC.visibility_of_element_located(locator)
            element_is_clickable = EC.element_to_be_clickable(locator)
            wait.until(element_is_visible)
            element = wait.until(element_is_clickable)
            element.click()
            return element
    
    def get_test_runner_cell(self):
        # TODO: make this more robust --  maybe loop in reverse over 
        #  cells and find the one whose text == "run_cell()"
        return self.driver.find_elements_by_class_name("cell")[-1]

    def quit(self):
        self.driver.quit()
        
    def set_max_timeout(self, timeout):
        self.driver.implicitly_wait(timeout)


class ColabDriver(NotebookDriver):
    def __init__(self, notebook_path, browser='firefox'):
        username = getenv("GITHUB_ACTOR")
        ref = getenv("GITHUB_SHA")
        url = f"https://colab.research.google.com/github/{username}/davos/blob/{ref}/{notebook_path}"
        super().__init__(url=url, browser=browser)
        self.sign_in_google()
        self.set_template_vars({'$GITHUB_USERNAME': username, '$GITHUB_REF': ref})
        
    def set_template_vars(self, to_replace):
        # assumes variables are set in first code cell
        template_var_cell = self.driver.find_elements_by_class_name('code')[0]
        cell_contents = template_var_cell.get_property('innerText')
        # replace Latin1 non-breaking spaces with UTF-8 spaces
        cell_contents = cell_contents.replace(u'\xa0', u' ')
        for template, val in to_replace.items():
            cell_contents = cell_contents.replace(template, val)
        set_cell_text_js = f"arguments[0].setText(`{cell_contents}`)"
        print(set_cell_text_js)
        self.driver.execute_script(set_cell_text_js, template_var_cell)

    def sign_in_google(self):
        # click "Sign in" button
        self.click("#gb > div > div.gb_Se > a")
        # enter email
        email_input_box = self.driver.find_element_by_id("identifierId")
        email_input_box.send_keys(getenv("GMAIL_ADDRESS"))
        self.click("identifierNext", By.ID)
        # screen takes a moment to progress
        time.sleep(3)
        # enter password
        pwd_input_box = self.driver.find_element_by_name("password")
        pwd_input_box.send_keys(getenv("GMAIL_PASSWORD"))
        self.click("passwordNext", By.ID)
        time.sleep(3)
        if self.driver.current_url != self.url:
            # handle additional "verify it's you" page
            self.click("#view_container > div > div > div.pwWryf.bxPAYd > div > div.WEQkZc > div > form > span > section > div > div > div > ul > li:nth-child(2) > div")
            time.sleep(3)
            recovery_email_input_box = self.driver.find_element_by_id('knowledge-preregistered-email-response')
            recovery_email_input_box.send_keys(getenv('RECOVERY_GMAIL_ADDRESS'))
            self.click("button[jsname='LgbsSe']")
            time.sleep(3)

    def run_all_cells(self, pre_approved=False):
        keyboard_shortcut = ActionChains(self.driver) \
            .key_down(Keys.META).send_keys() \
            .send_keys(Keys.F9) \
            .key_up(Keys.META)
        keyboard_shortcut.perform()
        if not pre_approved:
            # approve notebook not authored by Google
            # (button takes a second to become clickable, seems to be 
            # obscured by other element, raises 
            # ElementClickInterceptedException)
            time.sleep(3)
            try:
                self.driver.find_element_by_id("ok").click()
            except WebDriverException as e:
                # write source of current page to file
                page_src_path = Path('page_at_error.html').resolve()
                page_src_path.write_text(self.driver.page_source)
                # export path to file as environment variable
                with open(getenv('GITHUB_ENV'), 'a') as f:
                    f.write(f"\nERROR_PAGE_SOURCE={page_src_path}")
                # raise exception and show URL
                raise WebDriverException(
                    f"Error on page: {self.driver.current_url}. Page source "
                    f"in {page_src_path} will be uploaded as build artifact"
                ) from e

    def get_test_result(self, func_name):
        result_element = self.driver.find_element_by_id(f"{func_name}_result")
        result = result_element.text.split(maxsplit=2)[1:]
        if result[0] == 'FAILED':
            return result[1]
        return None
    
    def wait_for_test_start(self):
        test_runner_cell = self.get_test_runner_cell()
        test_runner_cell_id = test_runner_cell.get_attribute("id")
        # wait for runtime to connect and queue all cells
        wait = WebDriverWait(self.driver, 10)
        is_queued = element_has_class((By.ID, test_runner_cell_id), "pending")
        wait.until(is_queued)
        # wait for cell that runs test functions to start execution
        # needs a longer timeout due to davos installation
        wait = WebDriverWait(self.driver, 60)
        is_running_tests = element_has_class((By.ID, test_runner_cell_id), "code-has-output")
        wait.until(is_running_tests)
        # switch focus to iframe containing cell output
        self.driver.switch_to.frame(test_runner_cell.find_element_by_tag_name("iframe"))


class JupyterDriver(NotebookDriver):
    def __init__(self, notebook_path, ip='127.0.0.1', port='8888', browser='firefox'):
        self.set_kernel(notebook_path)
        url = f"http://{ip}:{port}/notebooks/{notebook_path}"
        super().__init__(url=url, browser=browser)
        
    def run_all_cells(self):
        # wait up to 10 seconds for "Cell" menu item to be clickable
        self.click("#menus > div > div > ul > li:nth-child(5) > a")
        self.click("run_all_cells", By.ID)
        
    def get_test_result(self, func_name):
        # TODO: implement me
        return None
        
    def set_kernel(self, notebook_path):
        repo_root = Path(getenv("GITHUB_WORKSPACE")).resolve(strict=True)
        notebook_path = repo_root.joinpath(notebook_path)
        with notebook_path.open() as nb:
            notebook_json = json.load(nb)
        notebook_json['metadata']['kernelspec'] = {
            'display_name': 'kernel-env',
            'language': 'python',
            'name': 'kernel-env'
        }
        with notebook_path.open('w') as nb:
            json.dump(notebook_json, nb)
    
    def wait_for_test_start(self):
        test_runner_cell = self.get_test_runner_cell()
        wait = WebDriverWait(self.driver, 60)
        locator = (By.CLASS_NAME, 'output_area')
        first_test_executed = EC.presence_of_element_located(locator)
        wait.until(first_test_executed)
        

class NotebookFile(pytest.File):
    test_func_pattern = re.compile('(?<=def )test_[^(]+', re.MULTILINE)

    def __init__(
            self, 
            fspath, 
            *, 
            driver_cls, 
            parent=None, 
            config=None, 
            session=None, 
            nodeid=None
    ):
        super().__init__(fspath=fspath, parent=parent, config=config, 
                         session=session, nodeid=nodeid)
        self.driver_cls = driver_cls
        self.driver = None
        repo_root = Path(getenv("GITHUB_WORKSPACE")).resolve(strict=True)
        notebook_abspath = Path(self.fspath).resolve(strict=True)
        self.notebook_path = str(notebook_abspath.relative_to(repo_root))
        self._test_names = []
        
    def collect(self):
        with self.fspath.open() as nb:
            notebook_json = json.load(nb)
        for cell in notebook_json['cells']:
            if cell['cell_type'] == 'code':
                cell_contents = ''.join(cell['source'])
                # noinspection PyCompatibility
                # TODO: make sure tests_require is being enforced
                if match := self.test_func_pattern.search(cell_contents):
                    test_name = match.group()
                    self._test_names.append(test_name)
                    yield NotebookTest.from_parent(self, name=test_name)
    
    def setup(self):
        # TODO: refactor this to call self.driver.<setup_func>()
        super().setup()
        self.driver = self.driver_cls(self.notebook_path)
        self.driver.run_all_cells()
        self.driver.wait_for_test_start()
        # driver will wait for up to 5 minutes for each test to complete
        # and its result to become readable. Upper limit for *driver* 
        # timeout is intentionally high so individual *tests* can 
        # specify pytest-style timeouts via the @mark_timeout() 
        # decorator in the notebook
        self.driver.set_max_timeout(300)
    
    def teardown(self):
        if self.driver is not None:
            self.driver.quit()
        return super().teardown()
        

class NotebookTest(pytest.Item):
    def runtest(self): 
        traceback_ = self.parent.driver.get_test_result(self.name)
        if traceback_ is not None:
            # test failed, traceback_ is the pre-formatted traceback to 
            # be displayed
            raise NotebookTestFailed(traceback_)
        return None

    def repr_failure(self, excinfo, style=None):
        if isinstance(excinfo.value, NotebookTestFailed):
            return html.unescape(excinfo.value.tb_str)
        return super().repr_failure(excinfo=excinfo, style=style)

def pytest_collect_file(path, parent):
    notebook_type = getenv("NOTEBOOK_TYPE")
    test_file_patterns = (notebook_type, 'shared', 'common')
    if notebook_type == 'colab':
        driver_cls = ColabDriver
    else:
        driver_cls = JupyterDriver
    
    if (
            path.basename.startswith('test') and 
            path.ext == ".ipynb" and
            any(pat in path.basename for pat in test_file_patterns)
    ):
        return NotebookFile.from_parent(parent, fspath=path, driver_cls=driver_cls)
    return None