import blinker
import pynput
from loguru import logger


def split_joystick_code(code: str) -> tuple[str, str, str]:
    _, j_axis, j_direction, j_value = code.split("_")
    return j_axis, j_direction, j_value


class EndProgram(Exception):
    pass


class InputManager:
    """Receives codes from the device and outputs keyboard and mouse events."""

    direct_mapping: dict[
        str, str | pynput.keyboard.Key | tuple[pynput.keyboard.Key | str, ...]
    ] = {
        "G1": (pynput.keyboard.Key.cmd, "z"),
        "G2": (pynput.keyboard.Key.shift, pynput.keyboard.Key.cmd, "z"),
        "G3": (pynput.keyboard.Key.cmd, "="),
        "G5": (pynput.keyboard.Key.cmd, "-"),
        "G8": (pynput.keyboard.Key.cmd, "c"),
        "G9": (pynput.keyboard.Key.cmd, "v"),
        "G10": pynput.keyboard.Key.left,
        "G11": pynput.keyboard.Key.space,
        "G12": pynput.keyboard.Key.right,
        "G15": pynput.keyboard.Key.shift,
    }
    keyboard: pynput.keyboard.Controller
    mouse: pynput.mouse.Controller
    previous_joystick_positions: tuple[str | None, str | None] = (
        "JOY_X_ZERO_0",
        "JOY_Y_ZERO_0",
    )
    active: bool = True

    def __init__(self):
        self.keyboard = pynput.keyboard.Controller()
        self.mouse = pynput.mouse.Controller()

        blinker.signal("app_changed").connect(self.app_changed)
        blinker.signal("g13_key").connect(self.handle_keystroke)
        blinker.signal("g13_joy").connect(self.handle_joystick)

    def activate(self, msg):
        self.active = True

    def deactivate(self, msg):
        self.active = False

    def handle_input(self, code: str):

        if code.startswith("JOY"):
            self.handle_joystick(code)
        else:
            self.handle_keystroke(code)

    def handle_keystroke(self, code: str):
        # code will end in either '_PRESSED' or '_RELEASED'
        # split and handle accordingly
        if not self.active:
            return
        action = code.split("_")[-1]
        key_code = "_".join(code.split("_")[:-1])
        output_key = self.direct_mapping.get(key_code)
        if type(output_key) is tuple:
            if action == "PRESSED":
                # multi-code events are only executed on press
                # hold each in turn
                for key in output_key:
                    self.keyboard.press(key)
                for key in reversed(output_key):
                    self.keyboard.release(key)
        elif output_key:
            if action == "PRESSED":
                self.keyboard.press(output_key)
            elif action == "RELEASED":
                self.keyboard.release(output_key)
        elif key_code == "BD":

            raise EndProgram()

        elif key_code == "M1":
            blinker.signal("g13_status").send("Well now")
        elif key_code == "M2":
            blinker.signal("g13_clear_status").send()
        else:
            blinker.signal("g13_print").send(code)

    def handle_joystick(self, code: str):
        """Take in a joystick code and handle it accordingly."""
        if not self.active:
            return
        # let's start simple.... generate a mouse scroll event
        # if the JOY code moves from 0 or 1 to 2
        j_axis, j_direction, j_value = split_joystick_code(code)
        if j_axis == "X":
            p_code = self.previous_joystick_positions[0]
        else:
            p_code = self.previous_joystick_positions[1]
        if p_code:
            _, p_direction, p_value = split_joystick_code(p_code)
        else:
            p_direction, p_value = "ZERO", "0"

        if j_value == "2":
            if p_value in ("0", "1") or p_direction != j_direction:
                logger.info("Scrolling...")
                # moved from center-ish to 2 (or somehow swapped direction!)
                if j_axis == "X":
                    # generate horizontal scroll
                    if j_direction == "NEG":
                        self.mouse.scroll(-12, 0)
                    elif j_direction == "POS":
                        self.mouse.scroll(12, 0)
                elif j_axis == "Y":
                    # generate vertical scroll
                    if j_direction == "NEG":
                        self.mouse.scroll(0, -12)
                    elif j_direction == "POS":
                        self.mouse.scroll(0, 12)
        if j_axis == "X":
            self.previous_joystick_positions = (
                code,
                self.previous_joystick_positions[1],
            )
        else:
            self.previous_joystick_positions = (
                self.previous_joystick_positions[0],
                code,
            )

    def app_changed(self, app_name: str):
        # in the future this will change profiles
        # for now just print the name of the app
        blinker.signal("g13_print").send(app_name)


class GeneralManager(InputManager):
    def __init__(self):
        super().__init__()
        blinker.signal("release_focus").connect(self.activate)
        blinker.signal("single_focus").connect(self.deactivate)
