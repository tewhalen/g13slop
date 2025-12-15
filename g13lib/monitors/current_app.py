import time

import blinker
from AppKit import NSWorkspace


class AppMonitor:
    current_app: str | None
    last_poll: float

    def __init__(self):
        self.current_app = self.detect_current_application()

        blinker.signal("tick").connect(self.notify)

    def detect_current_application(self) -> str:
        active_app = NSWorkspace.sharedWorkspace().activeApplication()

        self.last_poll = time.time()
        return active_app["NSApplicationName"]

    def notify(self, msg) -> bool:
        # if it's been at least a 1/10th second
        if time.time() - self.last_poll < 0.1:
            return False
        active_app = self.detect_current_application()
        if active_app != self.current_app:
            self.current_app = active_app
            # Add your notification logic here
            blinker.signal("app_changed").send(active_app)
            return True
        return False
