import typing

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
        str,
        str
        | pynput.keyboard.Key
        | tuple[pynput.keyboard.Key | str, ...]
        | typing.Callable,
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

    active: bool = True

    # Joystick repeat tracking
    _previous_joystick_positions: list[str, str]

    REPEAT_START_TICKS = 10  # ~500ms at 50ms/tick
    REPEAT_INTERVAL_TICKS = 2  # Repeat every ~100ms
    joystick_repeat_ticks: int = 0

    def __init__(self):
        self.keyboard = pynput.keyboard.Controller()
        self.mouse = pynput.mouse.Controller()
        self._previous_joystick_positions = ["JOY_X_ZERO_0", "JOY_Y_ZERO_0"]

        blinker.signal("app_changed").connect(self.app_changed)
        blinker.signal("g13_key").connect(self.handle_keystroke)
        blinker.signal("g13_joy").connect(self.handle_joystick)
        blinker.signal("tick").connect(self.on_tick)

    def activate(self, msg):
        self.active = True

    def deactivate(self, msg):
        self.active = False

    def joystick_held(self):
        """returns true when the joystick is outside of the center position."""
        return any(x[-1] != "0" for x in self._previous_joystick_positions)

    def on_tick(self, msg):
        """Called on each main loop tick to handle joystick repeat events."""
        if not self.active:
            return

        if self.joystick_held():
            self.joystick_repeat_ticks += 1
            if self.joystick_repeat_ticks == self.REPEAT_START_TICKS:
                # Start repeating after initial delay
                self.emit_repeat_scroll()
            elif self.joystick_repeat_ticks > self.REPEAT_START_TICKS:
                # Continue repeating at interval

                self.emit_repeat_scroll()
        else:
            self.joystick_repeat_ticks = 0

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
        if isinstance(output_key, typing.Callable):
            output_key(self, action, key_code)

        elif output_key:
            self.send_output(output_key, action)
        elif key_code == "BD":

            raise EndProgram()

        elif key_code == "M1":
            blinker.signal("g13_set_status").send("Well now")
        elif key_code == "M2":
            blinker.signal("g13_clear_status").send()
        else:
            blinker.signal("g13_print").send(code)

    def send_output(self, output_key: tuple | str | pynput.keyboard.Key, action: str):
        """Send output to the keyboard based on the action and key code."""
        if type(output_key) is tuple:
            if action == "PRESSED":
                # multi-code events are only executed on press
                # hold each in turn
                for key in output_key:
                    self.keyboard.press(key)
                for key in reversed(output_key):
                    self.keyboard.release(key)
        else:
            if action == "PRESSED":
                self.keyboard.press(output_key)
            elif action == "RELEASED":
                self.keyboard.release(output_key)

    def previous_joystick_position(self, j_axis: str) -> tuple[str, str]:
        """Returns direction, value of previous position for relevant axis."""
        if j_axis == "X":
            p_code = self._previous_joystick_positions[0]
        else:
            p_code = self._previous_joystick_positions[1]
        _, p_direction, p_value = split_joystick_code(p_code)

        return p_direction, p_value

    def joystick_scroll_triggered(
        self, j_axis: str, j_direction: str, j_value: str
    ) -> bool:
        """Returns true if the joystick has moved a lower to a higher value."""
        if j_value == "0":
            # moved to center
            return False
        p_direction, p_value = self.previous_joystick_position(j_axis)
        if int(j_value) > int(p_value) or p_direction != j_direction:

            logger.info("Scrolling...")
            # moved from center-ish to 2 (or somehow swapped direction!)
            return True

        return False

    def handle_joystick(self, code: str):
        """Take in a joystick code and handle it accordingly.

        Joystick codes are of the form JOY_X_{direction}_{value} where direction is
        'NEG' or 'POS' or 'ZERO' and value is a number.
        """

        if not self.active:
            return

        j_axis, j_direction, j_value = split_joystick_code(code)

        if self.joystick_scroll_triggered(j_axis, j_direction, j_value):
            self.emit_scroll(j_axis, j_direction)

        if j_axis == "X":
            self._previous_joystick_positions[0] = code
        else:
            self._previous_joystick_positions[1] = code

    def emit_scroll(self, j_axis: str, j_direction: str):
        """Emit a scroll event for the given axis and direction."""
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

    def is_scroll_tick(self, j_value: str) -> bool:
        """Return true if the current tick count is right for the given joystick position."""
        tick_mod = [None, 4, 2, 1][int(j_value)]

        if tick_mod and self.joystick_repeat_ticks % tick_mod == 0:

            return True

        return False

    def emit_repeat_scroll(self):
        """Emit a repeat scroll based on the currently held joystick position."""
        for code in self._previous_joystick_positions:

            j_axis, j_direction, j_value = split_joystick_code(code)
            if self.is_scroll_tick(j_value):
                if j_value != "0":
                    logger.info(f"Repeating scroll {code}")
                    self.emit_scroll(j_axis, j_direction)
        return

    def app_changed(self, app_name: str):
        # in the future this will change profiles
        # for now just print the name of the app
        blinker.signal("g13_print").send(app_name)


class GeneralManager(InputManager):
    def __init__(self):
        super().__init__()
        blinker.signal("release_focus").connect(self.activate)
        blinker.signal("single_focus").connect(self.deactivate)
