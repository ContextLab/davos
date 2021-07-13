from __future__ import annotations

import ast
import html
import json
import re
import time
from collections.abc import Iterable, Iterator
from os import getenv
from pathlib import Path
from typing import (
    Any,
    Literal,
    Optional,
    overload,
    Type,
    TYPE_CHECKING,
    TypedDict,
    TypeVar,
    Union
)

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
# noinspection PyPep8Naming
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

if TYPE_CHECKING:
    import _pytest
    import pluggy
    import py


######################## TYPING-RELATED OBJECTS ########################    # noqa: E266
_ByOpts = Literal[
    'class name',
    'css selector',
    'id',
    'link text',
    'name',
    'partial link text',
    'tag name',
    'xpath'
]
_E = TypeVar('_E', bound=BaseException)
_IpyVersions = Literal['5.5.0', '7.3.0', '7.15', '7.16', 'latest']
_NbTypes = Literal['colab', 'jupyter']
_PyVersions = Literal['3.6', '3.7', '3.8', '3.9']


class _SharedVars(TypedDict):
    GITHUB_USERNAME: str
    GITHUB_REF: str
    NOTEBOOK_TYPE: _NbTypes
    IPYTHON_VERSION: _IpyVersions
    PYTHON_VERSION: _PyVersions


# could type-hint notebook JSON many levels deep, but unnecessary
class _CellJson(TypedDict, total=False):
    cell_type: Literal['code', 'markdown']
    execution_count: int
    metadata: dict[str, Union[Any, dict[str, Any]]]
    outputs: list[dict[str, Union[int, str, dict[str, Any], list[dict[str, Any]]]]]
    source: list[str]


class _DecoratorData(TypedDict):
    name: str
    args: tuple
    kwargs: dict[str, Any]


class _NotebookJson(TypedDict):
    cells: list[_CellJson]
    metadata: dict[str, Union[dict[str, dict[str, Any]]]]
    nbformat: int
    nbformat_minor: int


########################################################################


GITHUB_USERNAME: str = getenv("GITHUB_REPOSITORY").split('/')[0]
GITHUB_REF: str = getenv("HEAD_SHA")
REPO_ROOT: Path = Path(getenv("GITHUB_WORKSPACE")).resolve(strict=True)
# noinspection PyTypeChecker
IPYTHON_VERSION: _IpyVersions = getenv('IPYTHON_VERSION')
# noinspection PyTypeChecker
NOTEBOOK_TYPE: _NbTypes = getenv('NOTEBOOK_TYPE')
# noinspection PyTypeChecker
PYTHON_VERSION: _PyVersions = getenv('PYTHON_VERSION')
SHARED_VARS: _SharedVars = {
    'GITHUB_USERNAME': GITHUB_USERNAME,
    'GITHUB_REF': GITHUB_REF,
    'NOTEBOOK_TYPE': NOTEBOOK_TYPE,
    'IPYTHON_VERSION': IPYTHON_VERSION,
    'PYTHON_VERSION': PYTHON_VERSION
}


# noinspection PyPep8Naming
class element_has_class:
    def __init__(self, locator: tuple[_ByOpts, str], cls_name: str) -> None:
        self.locator = locator
        self.cls_name = cls_name

    def __call__(self, driver: webdriver.Firefox) -> Union[WebElement, Literal[False]]:
        element = driver.find_element(*self.locator)
        if self.cls_name in element.get_attribute('class').split():
            return element
        return False


class NotebookTestFailed(Exception):
    pass


class NotebookTestSkipped(Exception):
    pass


class NotebookDriver:
    def __init__(self, url: str) -> None:
        self.url = url
        options = Options()
        options.headless = False
        self.driver = webdriver.Firefox(
            options=options, executable_path=getenv('DRIVER_PATH')
        )
        self.driver.get(url)

    # noinspection PyCompatibility
    def click(
            self,
            __locator_or_el: Union[str, WebElement],
            /,
            by: _ByOpts = By.CSS_SELECTOR,
            timeout: int = 10,
            poll_frequency: float = 0.5,
            ignored_exceptions: Optional[Union[_E, Iterable[_E]]] = None
    ) -> WebElement:
        if isinstance(__locator_or_el, WebElement):
            if isinstance(ignored_exceptions, BaseException):
                ignored_exceptions: tuple[_E] = (ignored_exceptions,)
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
            element: WebElement = wait.until(element_is_clickable)
            element.click()
            return element

    def get_test_result(self, func_name: str) -> list[str]:
        result_element = self.driver.find_element_by_id(f"{func_name}_result")
        result: list[str] = result_element.text.split(maxsplit=2)[1:]
        if len(result) == 0:
            # managed to read element text in the moment between when it 
            # was created and when it was populated
            time.sleep(3)
            result_element = self.driver.find_element_by_id(f"{func_name}_result")
            result = result_element.text.split(maxsplit=2)[1:]
        return result

    def get_test_runner_cell(self) -> WebElement:
        # TODO: make this more robust --  maybe loop in reverse over 
        #  cells and find the one whose text == "run_cell()"
        return self.driver.find_elements_by_class_name("cell")[-1]

    def quit(self) -> None:
        self.driver.quit()

    def set_max_timeout(self, timeout: float) -> None:
        self.driver.implicitly_wait(timeout)


class ColabDriver(NotebookDriver):
    def __init__(self, notebook_path: Union[Path, str]) -> None:
        url = f"https://colab.research.google.com/github/{GITHUB_USERNAME}/davos/blob/{GITHUB_REF}/{notebook_path}"
        super().__init__(url=url)
        self.sign_in_google()
        self.factory_reset_runtime()

    def clear_all_outputs(self):
        self.driver.execute_script("colab.global.notebook.clearAllOutputs()")

    def factory_reset_runtime(self):
        self.driver.execute_script("colab.global.notebook.kernel.unassignCurrentVm({skipConfirm: 1})")

    def set_template_vars(
            self,
            extra_vars: Optional[dict[str, str]] = None
    ) -> None:
        if extra_vars is None:
            to_replace = SHARED_VARS
        else:
            to_replace = SHARED_VARS | extra_vars
        # assumes variables are set in first code cell
        template_cell = self.driver.find_elements_by_class_name('code')[0]
        cell_contents: str = template_cell.get_property('innerText')
        # replace Latin1 non-breaking spaces with UTF-8 spaces
        cell_contents = cell_contents.replace(u'\xa0', u' ')
        for key, val in to_replace.items():
            template = f"${key}$"
            cell_contents = cell_contents.replace(template, val)
        set_cell_text_js = f"arguments[0].setText(`{cell_contents}`)"
        self.driver.execute_script(set_cell_text_js, template_cell)

    def sign_in_google(self) -> None:
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
            self.click(
                "#view_container > div > div > div.pwWryf.bxPAYd > div > div.WEQkZc > div > form > span > section > div > div > div > ul > li:nth-child(2) > div"
            )
            time.sleep(3)
            recovery_email_input_box = self.driver.find_element_by_id('knowledge-preregistered-email-response')
            recovery_email_input_box.send_keys(getenv('RECOVERY_GMAIL_ADDRESS'))
            self.click("button[jsname='LgbsSe']")
            time.sleep(3)

    def run_all_cells(self, pre_approved: bool = False) -> None:
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

    def wait_for_test_start(self) -> None:
        test_runner_cell = self.get_test_runner_cell()
        test_runner_cell_id: str = test_runner_cell.get_attribute("id")
        # # wait for runtime to connect and queue all cells
        # wait = WebDriverWait(self.driver, 10)
        # is_queued = element_has_class((By.ID, test_runner_cell_id), "pending")
        # wait.until(is_queued)
        # # wait for cell that runs test functions to start execution
        # # needs a longer timeout due to davos installation
        wait = WebDriverWait(self.driver, 60)
        is_running_tests = element_has_class((By.ID, test_runner_cell_id), "code-has-output")
        wait.until(is_running_tests)
        # switch focus to iframe containing cell output
        self.driver.switch_to.frame(test_runner_cell.find_element_by_tag_name("iframe"))


class JupyterDriver(NotebookDriver):
    @staticmethod
    def set_kernel(notebook_path: str) -> None:
        notebook_path: Path = REPO_ROOT.joinpath(notebook_path)
        with notebook_path.open() as nb:
            notebook_json = json.load(nb)
        notebook_json['metadata']['kernelspec'] = {
            'display_name': 'kernel-env',
            'language': 'python',
            'name': 'kernel-env'
        }
        with notebook_path.open('w') as nb:
            json.dump(notebook_json, nb)

    def __init__(
            self,
            notebook_path: Union[Path, str],
            ip: str = '127.0.0.1',
            port: str = '8888'
    ) -> None:
        self.set_kernel(notebook_path)
        # noinspection HttpUrlsUsage
        url = f"http://{ip}:{port}/notebooks/{notebook_path}"
        super().__init__(url=url)
        self.clear_all_outputs()
    
    def clear_all_outputs(self):
        # takes a moment for Jupyter.notebook JS object to be defined
        time.sleep(5)
        self.driver.execute_script("Jupyter.notebook.clear_all_output()")

    def run_all_cells(self) -> None:
        # wait up to 10 seconds for "Cell" menu item to be clickable
        self.click("#menus > div > div > ul > li:nth-child(5) > a")
        self.click("run_all_cells", By.ID)

    def set_template_vars(
            self,
            extra_vars: Optional[dict[str, str]] = None
    ) -> None:
        if extra_vars is None:
            to_replace = SHARED_VARS
        else:
            to_replace = SHARED_VARS | extra_vars
        cell_contents = self.driver.execute_script("return Jupyter.notebook.get_cell(0).get_text()")
        for key, val in to_replace.items():
            template = f"${key}$"
            cell_contents = cell_contents.replace(template, val)
        set_cell_text_js = "Jupyter.notebook.get_cell(0).set_text(arguments[0])"
        self.driver.execute_script(set_cell_text_js, cell_contents)

    def wait_for_test_start(self) -> None:
        wait = WebDriverWait(self.driver, 60)
        locator = (By.CSS_SELECTOR, "#notebook-container > div:last-child .output_area")
        first_test_executed = EC.presence_of_element_located(locator)
        wait.until(first_test_executed)


class NotebookFile(pytest.File):
    test_func_pattern = re.compile(r'(?:^@.+\n)*def test_[^(]+\(.*\):', re.M)

    @staticmethod
    def process_decorators(
            decs_asts: list[Union[ast.Attribute, ast.Call]]
    ) -> list[_pytest.mark.structures.MarkDecorator]:
        pytest_markers = []
        # reverse so multiple decorators are added from inside, out
        for dec in reversed(decs_asts):
            if isinstance(dec, ast.Call):
                # noinspection PyUnresolvedReferences
                # (expects dec.func to be ast.expr, but will always be
                # ast.Attribute here)
                mark_name: str = dec.func.attr
                if mark_name == 'skipif':
                    # ignore mark.skipif decorator so condition is
                    # evaluated in notebook namespace
                    continue
                args = [ast.literal_eval(arg) for arg in dec.args]
                kwargs = {arg.arg: ast.literal_eval(arg.value) for arg in dec.keywords}
            else:
                mark_name = dec.attr
                args = []
                kwargs = {}
            marker = getattr(pytest.mark, mark_name)(*args, **kwargs)
            pytest_markers.append(marker)
        return pytest_markers

    def __init__(
            self,
            fspath: str,
            *,
            driver_cls: Type[Union[ColabDriver, JupyterDriver]],
            parent: Optional[_pytest.nodes.Node] = None,
            config: Optional[_pytest.config.Config] = None,
            session: Optional[_pytest.main.Session] = None,
            nodeid: Optional[str] = None
    ):
        super().__init__(fspath=fspath, parent=parent, config=config,
                         session=session, nodeid=nodeid)
        self.driver_cls = driver_cls
        self.driver: Optional[Union[ColabDriver, JupyterDriver]] = None
        notebook_abspath = Path(self.fspath).resolve(strict=True)
        self.notebook_path = str(notebook_abspath.relative_to(REPO_ROOT))
        self._test_names: list[str] = []

    def collect(self) -> Iterator[NotebookTest]:
        with self.fspath.open() as nb:
            notebook_json: _NotebookJson = json.load(nb)
        for cell in notebook_json['cells']:
            if cell['cell_type'] == 'code':
                cell_contents = ''.join(cell['source'])
                match_groups: list[str] = self.test_func_pattern.findall(cell_contents)
                for match in match_groups:
                    # add body to function signature so it can be parsed
                    valid_funcdef = match + ' pass'
                    # noinspection PyTypeChecker
                    # (expects ast.stmt, will always be ast.FunctionDef)
                    test_ast: ast.FunctionDef = ast.parse(valid_funcdef).body[0]
                    test_name = test_ast.name
                    test_obj: NotebookTest = NotebookTest.from_parent(self, name=test_name)
                    if test_ast.decorator_list:
                        # noinspection PyTypeChecker
                        # (expects list[ast.stmt], will always be
                        # list[Union[ast.Attribute, ast.Call]])
                        pytest_marks = self.process_decorators(test_ast.decorator_list)
                        for mark in pytest_marks:
                            test_obj.add_marker(mark)
                    self._test_names.append(test_name)
                    yield test_obj

    def setup(self) -> None:
        # TODO: refactor this to call self.driver.<setup_func>()?
        super().setup()
        self.driver = self.driver_cls(self.notebook_path)
        self.driver.clear_all_outputs()
        self.driver.set_template_vars()
        # give DOM a moment to update before running & waiting
        time.sleep(3)
        self.driver.run_all_cells()
        self.driver.wait_for_test_start()
        # driver will wait for up to 5 minutes for each test to complete
        # and its result to become readable. Upper limit for *driver* 
        # timeout is intentionally high so individual *tests* can 
        # specify pytest-style timeouts via the @mark.timeout()
        # decorator in the notebook
        self.driver.set_max_timeout(300)

    def teardown(self) -> None:
        if self.driver is not None:
            self.driver.quit()
        return super().teardown()


# noinspection PyUnresolvedReferences
class NotebookTest(pytest.Item):
    parent: NotebookFile

    def reportinfo(self) -> Tuple[Union[py.path.local, str], Optional[int], str]:
        return self.fspath, 0, ""

    def runtest(self) -> None:
        result_info = self.parent.driver.get_test_result(self.name)
        outcome = result_info[0]
        if outcome == 'PASSED':
            return None
        elif outcome == 'SKIPPED':
            # test was skipped due to mark.skipif/mark.xfail conditions
            # evaluating to True within the notebook context.
            # result_info[1] is the "reason" passed to the decorator
            raise NotebookTestSkipped(result_info[1])
        elif outcome == 'FAILED':
            # test failed, result_info[1] is the pre-formatted traceback to
            # be displayed
            raise NotebookTestFailed(result_info[1])
        else:
            raise ValueError(f"received unexpected test outcome: {outcome}")

    @overload
    def repr_failure(
            self,
            excinfo: _pytest._code.code.ExceptionInfo[NotebookTestFailed],
            style: None
    ) -> str:
        ...

    @overload
    def repr_failure(
            self,
            excinfo: _pytest._code.code.ExceptionInfo[BaseException],
            style: Optional[_pytest._code.code._TracebackStyle]
    ) -> _pytest._code.code.TerminalRepr:
        ...

    def repr_failure(
            self,
            excinfo: _pytest._code.code.ExceptionInfo[Union[NotebookTestFailed, BaseException]],
            style: Optional[_pytest._code.code._TracebackStyle] = None
    ) -> Union[str, _pytest._code.code.TerminalRepr]:
        if isinstance(excinfo.value, NotebookTestFailed):
            return html.unescape(excinfo.value.tb_str)
        return super().repr_failure(excinfo=excinfo, style=style)


def pytest_collect_file(
        path: py.path.local,
        parent: pytest.Collector
) -> Optional[NotebookFile]:
    if NOTEBOOK_TYPE == 'colab':
        driver_cls = ColabDriver
    else:
        driver_cls = JupyterDriver

    if path.basename.startswith('test_') and path.ext == ".ipynb":
        return NotebookFile.from_parent(parent, fspath=path, driver_cls=driver_cls)
    return None


def pytest_markeval_namespace(config: _pytest.config.Config):
    return SHARED_VARS


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item: pytest.Item):
    """
    handles @mark.skipif and @mark.xfail decorators whose conditions
    need to be evaluated inside the notebook
    """
    outcome: pluggy.callers._Result = yield
    excinfo = outcome.excinfo
    if excinfo is not None and excinfo[0] is NotebookTestSkipped:
        msg = html.unescape(str(excinfo[1]))
        pytest.skip(msg)


def pytest_runtest_setup(item: pytest.Item):
    missing_reqs = []
    for mark in item.iter_markers():
        if mark.name == 'colab' and NOTEBOOK_TYPE != 'colab':
            missing_reqs.append('Google Colab')
        elif mark.name == 'jupyter' and NOTEBOOK_TYPE != 'jupyter':
            missing_reqs.append('Jupyter notebooks')
        elif (mark.name == 'ipython_pre7' and
                (IPYTHON_VERSION == 'latest' or
                 int(IPYTHON_VERSION.split('.')[0]) >= 7)):
            missing_reqs.append('IPython<7.0.0')
        elif (mark.name == 'ipython_post7' and
              IPYTHON_VERSION != 'latest' and
              int(IPYTHON_VERSION.split('.')[0]) < 7):
            missing_reqs.append('IPython>=7.0.0')

    if missing_reqs:
        pytest.skip(f"Test requires {', '.join(missing_reqs)}")
