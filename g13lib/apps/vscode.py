"""
An example of the sort of thing that can be done with this framework.

Pressing the G1 key will trigger running all tests in VSCode. If you have
pytest (or whatever your framework is) configured to output junitxml
formatted test results to /tmp/test_results.xml, the results will be
monitored and printed to the G13 terminal when they change.

For pytest, this configuration can be done by adding the following to your
project's pyproject.toml file:

        [tool.pytest]
        addopts = ["--junitxml=/tmp/test_results.xml"]


"""

import time
from pathlib import Path

import blinker
from PIL import Image

import g13lib.keylib as keylib
from g13lib.async_help import PeriodicComponent, run_periodic
from g13lib.single_app_manager import SingleAppManager


class PytestOutputMonitor:
    _last_check_time: float = 0.0
    file_updates: dict[Path, float]
    _tasks_to_start: list

    def __init__(self, vs_code_monitor, log_files: list[Path]):
        self.test_output = ""
        self.vs_code_monitor = vs_code_monitor
        self.file_updates = {log_file: 0.0 for log_file in log_files}
        self._tasks_to_start = [
            run_periodic(self.check_output, 1000, initial_delay_ms=500)
        ]

    async def check_output(self, *msg):

        # look for test output in designated spaces and
        # if updated, load it in and print results to the
        # g13 terminal.

        # only look if the vs code app is active
        if not self.vs_code_monitor.active:
            return

        for file_path, last_mtime in self.file_updates.items():
            try:
                mtime = file_path.stat().st_mtime
                if mtime > last_mtime:
                    with open(file_path, "r") as f:
                        new_content = f.read()
                        self.process_logfile(new_content)
                    self.file_updates[file_path] = mtime
            except FileNotFoundError:
                continue

    def process_logfile(self, content: str):
        # process the content of the logfile and send to g13 terminal
        # it's a pytest junitoutput log in xml format
        # for simplicity, just extract the test results summary
        # from the <testsuite name="pytest"> tag

        import xml.etree.ElementTree as ET

        root = ET.fromstring(content)
        # find the testsuite with name="pytest"
        pytest_suite = None
        for testsuite in root.findall("testsuite"):
            if testsuite.attrib.get("name") == "pytest":
                pytest_suite = testsuite
                break
        if pytest_suite is None:
            return  # no pytest results found
        tests = int(pytest_suite.attrib.get("tests", "0"))
        failures = int(pytest_suite.attrib.get("failures", "0"))
        errors = int(pytest_suite.attrib.get("errors", "0"))
        skipped = int(pytest_suite.attrib.get("skipped", "0"))
        if failures:
            blinker.signal("g13_print").send(f"{failures}/{tests} FAILED\n")
        else:
            blinker.signal("g13_print").send(f"{tests}/{tests} PASSED\n")
        blinker.signal("g13_print").send(f"Errors: {errors}, Skipped: {skipped}\n")


class VSCodeInputManager(SingleAppManager, PeriodicComponent):
    """
    This manager is designed to work with VSCode. Pressing G1 will
    trigger running all tests (cmd+; then 'a'). The results will be
    monitored from /tmp/test_results.xml and printed to the G13 terminal
    when they change.
    """

    app_name = "Code"

    def __init__(self):
        super().__init__()
        self._pytest_monitor = PytestOutputMonitor(
            self, [Path("/tmp/test_results.xml")]
        )
        self._tasks_to_start = self._pytest_monitor._tasks_to_start

    def run_all_tests(self, action, key_code):
        # send a cmd+; and then an 'a'

        if action == "PRESSED":
            self.send_output((keylib.cmd, ";"), action="PRESSED")
            self.send_output("a", action="PRESSED")

    direct_mapping = {
        "G1": run_all_tests,
    }
