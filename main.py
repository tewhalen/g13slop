import time

import blinker
from AppKit import NSWorkspace
from loguru import logger

from g13lib.device_manager import G13Manager, G13USBError
from g13lib.input_manager import EndProgram, InputManager


class AppMonitor:
    current_app: str | None
    last_poll: float

    def __init__(self):
        self.current_app = self.detect_current_application()

    def detect_current_application(self) -> str:
        active_app = NSWorkspace.sharedWorkspace().activeApplication()

        self.last_poll = time.time()
        return active_app["NSApplicationName"]

    def notify(self) -> bool:
        # if it's been at least a second
        if time.time() - self.last_poll < 1:
            return False
        active_app = self.detect_current_application()

        if active_app != self.current_app:
            self.current_app = active_app
            # Add your notification logic here
            blinker.signal("app_changed").send(active_app)
            return True
        return False


def read_data_loop(
    device_manager: G13Manager, input_manager: InputManager, app_monitor: AppMonitor
):
    """Currently this is a loop that reads data from the USB device."""
    # probably we should be using an interrupt?
    error_count = 0
    while True:
        if error_count > 5:
            # give up
            break
        time.sleep(0.001)
        app_monitor.notify()

        for result in device_manager.get_codes():
            if isinstance(result, G13USBError):
                error_count += 1
                logger.error("USB Error: %s", result)


if __name__ == "__main__":
    m = G13Manager()
    processor = InputManager(m)
    a = AppMonitor()
    m.start()

    try:

        read_data_loop(m, processor, a)
    except EndProgram:
        blinker.signal("g13_print").send("That's all!")
        logger.success("Exiting...")
    finally:
        m.close()
