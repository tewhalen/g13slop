import blinker
import pynput
from loguru import logger

import g13lib.keylib as keylib
from g13lib.input_manager import InputManager


class SingleAppManager(InputManager):
    """An InputManager for a single application.

    Listens for the active application and activates or deactivates itself accordingly.
    """

    active = False
    app_name: str

    def __init__(self):
        logger.debug("Initializing SingleAppManager for app: {}", self.app_name)
        blinker.signal("app_changed").connect(self.app_changed)
        super().__init__()

    def activate(self):
        self.active = True
        blinker.signal("single_focus").send(self.app_name)
        blinker.signal("g13_set_status").send(f"{self.app_name}")
        blinker.signal("g13_led_on").send(0)

    def deactivate(self):
        self.active = False
        blinker.signal("release_focus").send(self.app_name)
        blinker.signal("g13_clear_status").send()
        blinker.signal("g13_led_off").send(0)

    def app_changed(self, app_name: str):
        logger.info("Switching to app: {}", app_name)
        if app_name == self.app_name:
            self.activate()
        else:
            self.deactivate()
