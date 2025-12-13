import blinker
import pynput
from loguru import logger

import g13lib.keylib as keylib
from g13lib.input_manager import InputManager


class SingleAppManager(InputManager):
    active = False
    app_name: str

    def __init__(self):
        logger.debug("Initializing SingleAppManager for app: {}", self.app_name)
        blinker.signal("app_changed").connect(self.app_changed)
        super().__init__()

    def activate(self):
        self.active = True
        blinker.signal("single_focus").send(self.app_name)
        blinker.signal("g13_status").send(f"{self.app_name}")

    def deactivate(self):
        self.active = False
        blinker.signal("release_focus").send(self.app_name)
        blinker.signal("g13_clear_status").send()

    def app_changed(self, app_name: str):
        logger.info("Switching to app: {}", app_name)
        if app_name == self.app_name:
            self.activate()
        else:
            self.deactivate()


class DavinciInputManager(SingleAppManager):
    app_name = "DaVinci Resolve"
    direct_mapping = {
        "G1": keylib.undo,
        "G2": keylib.redo,
        "G3": keylib.zoom_in,
        "G5": keylib.zoom_out,
        "G8": keylib.copy,
        "G9": keylib.paste,
        "G10": pynput.keyboard.Key.left,
        "G11": pynput.keyboard.Key.space,
        "G12": pynput.keyboard.Key.right,
        "G15": pynput.keyboard.Key.shift,
    }
