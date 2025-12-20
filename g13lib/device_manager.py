import bisect
from typing import Sequence

import blinker
from loguru import logger

import g13lib.device.keycodes
from g13lib.device.g13_usb_device import G13USBDevice


class G13Manager:

    g13_usb_device: G13USBDevice

    held_keys: set[str]

    _joy_x_zero: bool = True
    _joy_y_zero: bool = True

    def __init__(self, g13_usb_device: G13USBDevice):
        super().__init__()

        self.g13_usb_device = g13_usb_device

        self.held_keys = set()

    def joystick_position(self, bytes: Sequence[int]):
        """If the joystick has moved significantly, yield corresponding codes.

        When the joystick is centered (or returns to center), only yields
        the ZERO_0 codes once.
        """
        joy_x, joy_y = bytes[1], bytes[2]

        for code in self.joy_position_to_codes(joy_x, joy_y):
            if code == "JOY_X_ZERO_0" and not self._joy_x_zero:
                self._joy_x_zero = True
                yield code
            elif code == "JOY_Y_ZERO_0" and not self._joy_y_zero:
                self._joy_y_zero = True
                yield code
            elif code.startswith("JOY_X"):
                self._joy_x_zero = False
                yield code
            elif code.startswith("JOY_Y"):
                self._joy_y_zero = False
                yield code
            else:
                # ????
                yield code

    def joy_position_to_codes(self, joy_x: int, joy_y: int):
        """Given joystick x and y positions bytes (0x00-0xFF), yield corresponding codes."""

        codes = ["NEG_3", "NEG_2", "NEG_1", "ZERO_0", "POS_1", "POS_2", "POS_3"]
        thresholds = [0x25, 0x50, 0x60, 0x80, 0xA0, 0xC0]
        # the y axis is reversed

        # look up x value in x_thresholds and yield corresponding keycode
        x_index = bisect.bisect_left(thresholds, joy_x)
        y_index = bisect.bisect_left(thresholds, joy_y)
        if x_index < len(codes):
            code = codes[x_index]
            if code:
                yield f"JOY_X_{code}"

        if y_index < len(codes):
            code = list(reversed(codes))[y_index]
            if code:
                yield f"JOY_Y_{code}"

    def determine_held_keycodes(self, bytes: Sequence[int]):
        """Given a bitmask of held keys, yield the corresponding keycodes."""
        # for each keycode in the keycodes dict
        for key, (byte, bit_position) in g13lib.device.keycodes.keycodes.items():
            # if the bits set in the keycode are present in bytes
            mask = 1 << (bit_position)
            if bytes[byte] & mask:

                yield key

    def key_events(self, bytes: Sequence[int]):
        """Given a bitmask of held keys, yield the corresponding pressed and released events."""
        seen_keys = set()
        for key in self.determine_held_keycodes(bytes):
            seen_keys.add(key)

        # release held but now unseen keys
        for released_key in self.held_keys.difference(seen_keys):
            yield f"{released_key}_RELEASED"
        # press unheld but now seen keys
        for key in seen_keys.difference(self.held_keys):
            yield f"{key}_PRESSED"
        self.held_keys = seen_keys

    async def get_codes(self, msg=None):
        """Poll the USB device for key events and joystick positions."""

        read_result = self.g13_usb_device.read_data()

        if isinstance(read_result, Sequence):
            for i, event in enumerate(self.key_events(read_result)):

                await blinker.signal("g13_key").send_async(event)

            for event in self.joystick_position(read_result):
                await blinker.signal("g13_joy").send_async(event)
        return read_result

    def close(self):
        self.g13_usb_device.close()


def print_as_decoded_bytes(data):
    print("Decoded bytes: ", end="")
    for byte in data[:3]:
        print(f"{byte:02x} ", end="")
    for byte in data[3:]:
        # print as binary
        print(f"{byte:08b} ", end="")

    print()
