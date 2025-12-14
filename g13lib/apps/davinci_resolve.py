import pynput

import g13lib.keylib as keylib
from g13lib.single_app_manager import SingleAppManager


class DavinciInputManager(SingleAppManager):
    app_name = "DaVinci Resolve"

    playhead_action: str = "normal"

    def toggle_blade(self, action, key_code):
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
    }
