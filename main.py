import errno
from typing import Sequence

import usb.core
import usb.util

from g13lib.render_fb import ImageToLPBM
from g13lib.terminal import LogEmulator

product_id = "0xc21c"
vendor_id = "0x046d"


# keycode: byte, bit
keycodes = {
    "G1": (3, 0),
    "G2": (3, 1),
    "G3": (3, 2),
    "G4": (3, 3),
    "G5": (3, 4),
    "G6": (3, 5),
    "G7": (3, 6),
    "G8": (3, 7),
    "G9": (4, 0),
    "G10": (4, 1),
    "G11": (4, 2),
    "G12": (4, 3),
    "G13": (4, 4),
    "G14": (4, 5),
    "G15": (4, 6),
    "G16": (4, 7),
    "G17": (5, 0),
    "G18": (5, 1),
    "G19": (5, 2),
    "G20": (5, 3),
    "G21": (5, 4),
    "G22": (5, 5),
    "BD": (6, 0),
    "L1": (6, 1),
    "L2": (6, 2),
    "L3": (6, 3),
    "L4": (6, 4),
    "M1": (6, 5),
    "M2": (6, 6),
    "M3": (6, 7),
    "MR": (7, 0),
    "THUMB_LEFT": (7, 1),
    "THUMB_RIGHT": (7, 2),
    "THUMB_STICK": (7, 3),
}


class G13Manager:

    held_keys: set
    led_status = [0, 0, 0, 0]
    console: LogEmulator

    def determine_keycode(self, bytes: Sequence[int]):
        # for each keycode in the keycodes dict
        for key, (byte, bit_position) in keycodes.items():
            # if the bits set in the keycode are present in bytes
            mask = 1 << (bit_position)
            if bytes[byte] & mask:

                yield key

    def key_events(self, bytes: Sequence[int]):
        seen_keys = set()
        for key in self.determine_keycode(bytes):
            seen_keys.add(key)
        # release held but unseen keys
        for released_key in self.held_keys.difference(seen_keys):
            yield f"{released_key}_RELEASED"

        for key in seen_keys.difference(self.held_keys):
            yield f"{key}_PRESSED"
        self.held_keys = seen_keys

    def __init__(self):
        self.console = LogEmulator()
        self.held_keys = set()

    def print(self, message: str):
        self.console.output(message)
        image = self.console.draw_buffer()
        image.save("default_font_output.png")
        self.setLCD(ImageToLPBM(image))

    def start(self):
        # HID device for key input
        # self.start_hid_device()
        self.start_usb_device()

    def start_usb_device(self):
        # USB device for control transfers (LCD, LEDs, backlight)
        self.usb_device = usb.core.find(idVendor=0x046D, idProduct=0xC21C)
        if self.usb_device is None:
            raise ValueError("G13 device not found")

        if self.usb_device.is_kernel_driver_active(0):
            self.usb_device.detach_kernel_driver(0)
        cfg = usb.util.find_descriptor(self.usb_device)
        self.usb_device.set_configuration(cfg)

    def read_data(self):
        while True:
            d = None
            try:
                d = self.usb_device.read(0x81, 8, 100)
            except usb.core.USBError as e:
                if e.errno == errno.ETIMEDOUT:  # Timeout error
                    pass
                else:
                    raise
            if d:
                res = list(self.key_events(d))
                if res:
                    self.print(repr(res))
                else:
                    print_as_decoded_bytes(d)

    def toggle_led(self, led_no: int):
        self.led_status[led_no] = 1 - self.led_status[led_no]
        self.update_leds()

    def update_leds(self):
        # use the led status to make a binary bitmask
        mask = 0
        for i, status in enumerate(self.led_status):
            if status:
                mask |= 1 << i

        # and the mask with 0x0F
        # mask = mask & 0x0F
        data = [5, mask, 0, 0, 0]

        self.usb_device.ctrl_transfer(
            usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE,
            bRequest=9,
            wValue=0x305,
            wIndex=0,
            data_or_wLength=data,
        )

    def set_backlight(self, r: int, g: int, b: int):
        data = [7, int(r), int(g), int(b), 0]
        self.usb_device.ctrl_transfer(
            usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE,
            bRequest=9,
            wValue=0x307,
            wIndex=0,
            data_or_wLength=data,
        )

    def setLCD(self, image_buffer: list[int]):
        header = [0] * 32
        header[0] = 0x03

        self.usb_device.write(
            usb.util.CTRL_OUT | 2,  # Endpoint 2 for LCD
            bytes(header) + bytes(image_buffer),
        )

    def close(self):
        self.usb_device.reset()
        usb.util.dispose_resources(self.usb_device)


def print_as_decoded_bytes(data):
    print("Decoded bytes: ", end="")
    for byte in data[:3]:
        print(f"{byte:02x} ", end="")
    for byte in data[3:]:
        # print as binary
        print(f"{byte:08b} ", end="")

    print()


if __name__ == "__main__":
    m = G13Manager()
    m.start()

    try:

        m.read_data()
    finally:
        m.close()
