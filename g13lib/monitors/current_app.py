import time

import blinker
from AppKit import NSWorkspace
from loguru import logger


class AppMonitor:
    current_app: str | None
    last_poll: float

    def __init__(self):
        self.current_app = self.detect_current_application()
        self.last_poll = time.time()

        blinker.signal("tick").connect(self.handle_tick)

    def detect_current_application(self) -> str:
        active_app = NSWorkspace.sharedWorkspace().activeApplication()

        return active_app["NSApplicationName"]

    def handle_tick(self, msg) -> bool:
        # if it's been at least a 1/10th second
        if time.time() - self.last_poll < 0.1:
            return False
        return self.notify()

    def notify(self) -> bool:

        try:
            self.last_poll = time.time()
            active_app = self.detect_current_application()
        except Exception as e:
            logger.error("Error detecting current application: {}", e)
            return False
        if active_app != self.current_app:
            self.current_app = active_app
            # Add your notification logic here
            blinker.signal("app_changed").send(active_app)
            return True
        return False
