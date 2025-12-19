import time
from pathlib import Path

import blinker
from PIL import Image

import g13lib.keylib as keylib
from g13lib.single_app_manager import SingleAppManager


class PytestOutputMonitor:
    _last_check_time: float = 0.0

    def __init__(self, log_files: list[Path]):
        self.test_output = ""
        self.file_updates = {log_file: 0 for log_file in log_files}
        blinker.signal("tick").connect(self.check_output)

    def check_output(self, msg):
        # every ms is too often, so only check every second
        current_time = time.time()

        if current_time - self._last_check_time < 1.0:
            return
        self._last_check_time = current_time
        # look for test output in designated spaces and
        # if updated, load it in and print results to the
        # g13 terminal.
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
            blinker.signal("g13_print").send("FAILED\n")
        else:
            blinker.signal("g13_print").send("PASSED\n")
        blinker.signal("g13_print").send(
            f"{tests}, Failures: {failures}, Errors: {errors}, Skipped: {skipped}\n"
        )


class VSCodeInputManager(SingleAppManager):
    app_name = "Code"

    def __init__(self):
        super().__init__()
        self._pytest_monitor = PytestOutputMonitor([Path("/tmp/test_results.xml")])

    def run_all_tests(self, action, key_code):
        # send a cmd+; and then an 'a'

        if action == "PRESSED":
            self.send_output((keylib.cmd, ";"), action="PRESSED")
            self.send_output("a", action="PRESSED")

    direct_mapping = {
        "G1": run_all_tests,
    }
