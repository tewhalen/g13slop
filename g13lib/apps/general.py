import blinker

from g13lib.input_manager import InputManager
from g13lib.render_fb import LCDCompositor
from g13lib.terminal import LogEmulator


class GeneralManager(InputManager):
    def __init__(self):
        super().__init__()

        blinker.signal("release_focus").connect(self.activate)
        blinker.signal("single_focus").connect(self.deactivate)

    def compositor(self):
        return LCDCompositor(LogEmulator())

    def activate(self, msg):
        blinker.signal("set_compositor").send(self.compositor())
        return super().activate(msg)
