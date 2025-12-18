import blinker
from loguru import logger
from PIL import Image

from g13lib.input_manager import InputManager
from g13lib.lcd.images import DecayingImage
from g13lib.lcd.terminal import LogEmulator
from g13lib.render_fb import LCDCompositor


class GeneralManager(InputManager):
    """
    The is the default InputManager that provides a general-purpose
    terminal emulator on the LCD.

    Currently it just logs keypresses to the LCD and sends joystick
    events as mouse scrolls.

    """

    _compositor: LCDCompositor

    def __init__(self):
        super().__init__()
        self._log_emulator = LogEmulator()
        self._icon_image = None

        blinker.signal("release_focus").connect(self.activate)
        blinker.signal("single_focus").connect(self.deactivate)
        blinker.signal("current_app_icon").connect(self.update_icon)

    def compositor(self):

        return LCDCompositor(
            self._log_emulator,
            self._icon_image,
        )

    def update_icon(self, icon: Image.Image):

        self._icon_image = DecayingImage(
            image=icon,
            position=(64, 0),
        )
        blinker.signal("set_compositor").send(self.compositor())

    def activate(self, msg):
        blinker.signal("set_compositor").send(self.compositor())
        return super().activate(msg)
