import blinker
from loguru import logger

from g13lib.input_manager import InputManager
from g13lib.lcd.terminal import LogEmulator
from g13lib.render_fb import LCDCompositor


class SingleAppManager(InputManager):
    """An InputManager for a single application.

    Listens for the active application and activates or deactivates itself accordingly.

    The default compositor shows a terminal log emulator.
    """

    active = False
    app_name: str

    def __init__(self):
        logger.debug("Initializing SingleAppManager for app: {}", self.app_name)
        blinker.signal("app_changed").connect(self.app_changed)
        self._terminal = LogEmulator()
        super().__init__()

    def compositor(self):
        return LCDCompositor(
            self._terminal,
        )

    def activate(self):
        logger.info("Activating SingleAppManager for app: {}", self.app_name)
        self.active = True
        blinker.signal("set_compositor").send(self.compositor())
        blinker.signal("single_focus").send(self.app_name)

    def deactivate(self):
        self.active = False
        blinker.signal("release_focus").send(self.app_name)

    def app_changed(self, app_name: str):
        if app_name == self.app_name:
            self.activate()
        elif self.active:
            self.deactivate()
