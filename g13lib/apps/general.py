import blinker

from g13lib.input_manager import InputManager
from g13lib.lcd.terminal import LogEmulator
from g13lib.render_fb import LCDCompositor


class GeneralManager(InputManager):
    _compositor: LCDCompositor

    def __init__(self):
        super().__init__()
        self._compositor = LCDCompositor(LogEmulator())
        blinker.signal("release_focus").connect(self.activate)
        blinker.signal("single_focus").connect(self.deactivate)

    def compositor(self):
        return self._compositor

    def activate(self, msg):
        blinker.signal("set_compositor").send(self.compositor())
        return super().activate(msg)
