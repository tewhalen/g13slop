import time
import typing

import blinker
import pynput
from loguru import logger

from g13lib.async_help import PeriodicComponent, run_periodic


def split_joystick_code(code: str) -> tuple[str, str, str]:
    _, j_axis, j_direction, j_value = code.split("_")
    return j_axis, j_direction, j_value


class EndProgram(Exception):
    pass


class InputManager(PeriodicComponent):
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
    _previous_joystick_positions: list[str]

    JOY_REPEAT_DELAY = 500
    JOY_REPEAT_INTERVAL = 100

    joystick_repeat_ticks: int = 0

    def __init__(self):
        self.keyboard = pynput.keyboard.Controller()
        self.mouse = pynput.mouse.Controller()
        self._previous_joystick_positions = ["JOY_X_ZERO_0", "JOY_Y_ZERO_0"]

        # Connect synchronous signals
        blinker.signal("app_changed").connect(self.app_changed)

        # connect asynchronous signal handlers
        blinker.signal("g13_key").connect(self.handle_keystroke)
        blinker.signal("g13_joy").connect(self.handle_joystick)

        # set up task for joystick repeat handling
        self._tasks_to_start = [
            run_periodic(
                self.joystick_repeat, self.JOY_REPEAT_INTERVAL, initial_delay_ms=1000
            )
        ]

    def activate(self, msg):
        """Make this manager active and responsive to events and input."""
        self.active = True

    def deactivate(self, msg):
        """Make this manager inactive and unresponsive to events and input."""
        self.active = False

    def joystick_held(self):
        """returns true when the joystick is outside of the center position."""
        return any(x[-1] != "0" for x in self._previous_joystick_positions)

    async def joystick_repeat(self):
        """Called every JOY_REPEAT_INTERVAL to handle joystick repeat events."""

        if not self.active:
            return

        if self.joystick_held():
            self.joystick_repeat_ticks += 1
            if (
                self.joystick_repeat_ticks
                > self.JOY_REPEAT_DELAY // self.JOY_REPEAT_INTERVAL
            ):
                # Start repeating after initial delay
                self.emit_repeat_scroll()
        else:
            self.joystick_repeat_ticks = 0

    async def handle_keystroke(self, code: str):
        """Take in a G13 keystroke code and handle it accordingly."""

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
            # as a debugging aid for now, show unhandled codes on the g13 console
            blinker.signal("g13_print").send(code)

    def send_output(
        self,
        output_key: list | tuple | str | pynput.keyboard.Key | int | typing.Callable,
        action: str,
    ):
        """Send output to the keyboard based on the action and key code.

        output_key: the key or keys to send. Supports:
            - str or Key: single key
            - tuple: chord (hold all, release in reverse) - only on PRESSED
            - list: sequence of keys/chords/delays to execute in order
            - int: delay in milliseconds (only processed in lists)
            - Callable: a function to be called and passed (self, action), and its return value
              processed as output_key recursively.
        action: "PRESSED" or "RELEASED"

        Examples:
            send_output("a", "PRESSED")  # press 'a'
            send_output((Key.cmd, "c"), "PRESSED")  # cmd+c chord
            send_output(["a", "b", 5, "c"], "PRESSED")  # type a, b, wait 5ms, type c
            send_output(["a", (Key.shift, "b"), 10], "PRESSED")  # type a, then Shift+b, wait 10ms
        """
        if type(output_key) is list:
            if action == "PRESSED":
                # Process list as a sequence of actions
                for item in output_key:
                    if isinstance(item, int):
                        # Integer = delay in milliseconds
                        time.sleep(item / 1000.0)
                    else:
                        # Recursively process each item (handles nested tuples/keys)
                        self.send_output(item, "PRESSED")
        elif type(output_key) is tuple:
            if action == "PRESSED":
                # multi-code events are only executed on press
                # hold each in turn
                for key in output_key:
                    self.keyboard.press(key)
                # release each in reverse order
                for key in reversed(output_key):
                    self.keyboard.release(key)
        elif type(output_key) is str or isinstance(output_key, pynput.keyboard.Key):
            if action == "PRESSED":
                self.keyboard.press(output_key)
            elif action == "RELEASED":
                self.keyboard.release(output_key)
        elif callable(output_key):
            result = output_key(self, action)
            if result is not None:
                self.send_output(result, action)

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

            # moved from center-ish to 2 (or somehow swapped direction!)
            return True

        return False

    async def handle_joystick(self, code: str):
        """Take in a joystick code and handle it accordingly.

        Joystick codes are of the form JOY_X_{direction}_{value} where direction is
        'NEG' or 'POS' or 'ZERO' and value is an integer.
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
                self.mouse.scroll(-6, 0)
            elif j_direction == "POS":
                self.mouse.scroll(6, 0)
        elif j_axis == "Y":
            # generate vertical scroll
            if j_direction == "NEG":
                self.mouse.scroll(0, -6)
            elif j_direction == "POS":
                self.mouse.scroll(0, 6)

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
                self.emit_scroll(j_axis, j_direction)
        return

    def app_changed(self, app_name: str):
        # in the future this will change profiles
        # for now just print the name of the app
        blinker.signal("g13_print").send(app_name)
