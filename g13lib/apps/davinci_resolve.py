import blinker
import pynput
from PIL import Image

import g13lib.keylib as keylib
from g13lib.lcd.images import DecayingImage
from g13lib.lcd.terminal import LogEmulator
from g13lib.render_fb import LCDCompositor
from g13lib.single_app_manager import SingleAppManager


class DavinciInputManager(SingleAppManager):
    app_name = "DaVinci Resolve"

    playhead_action: str = "normal"

    workspace_page: str = "edit"  # "edit", "fusion", "color"

    # 32x32 icon for DaVinci Resolve
    icon = Image.open("icons/davinci_resolve_icon.png")

    def __init__(self):

        super().__init__()

    def compositor(self):
        return LCDCompositor(
            LogEmulator(),
            DecayingImage(self.icon, (64, 0)),
        )

    def activate(self):
        # activate the compositor first
        blinker.signal("set_compositor").send(self.compositor())

        blinker.signal("g13_set_status").send("edit   fusion  color")
        return super().activate()

    def deactivate(self):
        blinker.signal("g13_clear_status").send()
        return super().deactivate()

    def toggle_blade(self, action, key_code):
        """Cycle through playhead actions: normal -> blade -> trim -> normal"""
        key_mapping = {"normal": "a", "blade": "b", "trim": "t"}
        if action == "RELEASED":
            # lookup current status in key_mapping and release that key
            current_key = key_mapping[self.playhead_action]
            self.keyboard.release(current_key)
        else:
            # advance the status to the next status
            if self.playhead_action == "normal":
                self.playhead_action = "blade"

            elif self.playhead_action == "blade":
                self.playhead_action = "trim"
            else:
                self.playhead_action = "normal"
            current_key = key_mapping[self.playhead_action]
            self.keyboard.press(current_key)

    def switch_to_edit(self, action, key_code):
        if action == "PRESSED":
            self.send_output((keylib.shift, "4"), "PRESSED")  # shift + 4?

            self.workspace_page = "edit"

    def switch_to_fusion(self, action, key_code):
        if action == "PRESSED":
            self.send_output((keylib.shift, "5"), "PRESSED")  # shift + 5?

            self.workspace_page = "fusion"

    def switch_to_color(self, action, key_code):
        if action == "PRESSED":
            self.send_output((keylib.shift, "6"), "PRESSED")  # shift + 6?

            self.workspace_page = "color"

    direct_mapping = {
        "G1": keylib.undo,
        "G2": keylib.redo,
        "G3": keylib.zoom_out,
        "G5": keylib.zoom_in,
        "G7": toggle_blade,
        "G8": keylib.copy,
        "G9": keylib.paste,
        "G10": pynput.keyboard.Key.left,
        "G11": pynput.keyboard.Key.space,
        "G12": pynput.keyboard.Key.right,
        "G15": pynput.keyboard.Key.shift,
        "L1": switch_to_edit,
        "L2": switch_to_fusion,
        "L3": switch_to_color,
    }


if __name__ == "__main__":
    m = DavinciInputManager()

    c = m.compositor()
    m.activate()
    blinker.signal("g13_print").send("HELLOW DAVINCI\n")
    fb = c.render()
    fb.save("davinci_test.png")
