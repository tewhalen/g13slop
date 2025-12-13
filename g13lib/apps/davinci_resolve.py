import pynput

import g13lib.keylib as keylib
from g13lib.single_app_manager import SingleAppManager


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
