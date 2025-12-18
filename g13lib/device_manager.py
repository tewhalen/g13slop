import bisect
import errno
import time
from typing import Sequence

import blinker
import PIL.Image
import usb.core
import usb.util
from loguru import logger

import g13lib.data
from g13lib.render_fb import ImageToLPBM, LCDCompositor
from g13lib.security import drop_root_privs

product_id = "0xc21c"
vendor_id = "0x046d"


class G13USBError(Exception):
    pass


class G13Manager:

    held_keys: set[str]
    led_status: list[int]

    compositor: LCDCompositor
    _lcd_tick_timer: float = 0.0
    _lcd_framebuffer: PIL.Image.Image

    usb_device: usb.core.Device
    _joy_x_zero: bool = True
    _joy_y_zero: bool = True

    def __init__(self):

        # initialize the USB device and drop root privs
        self.start_usb_device()

        self.held_keys = set()
        self.led_status = [0, 0, 0, 0]
        self._joystick_codes = set()

        self.compositor = LCDCompositor()
        self._lcd_framebuffer = PIL.Image.new("RGB", (160, 43))

        blinker.signal("tick").connect(self.get_codes)
        blinker.signal("tick").connect(self.lcd_tick)

        blinker.signal("set_compositor").connect(self.set_compositor)
        blinker.signal("g13_led_toggle").connect(self.toggle_led)
        blinker.signal("g13_led_on").connect(self.led_on)
        blinker.signal("g13_led_off").connect(self.led_off)

    def joystick_position(self, bytes: Sequence[int]):
        """If the joystick has moved significantly, yield corresponding codes."""
        joy_x, joy_y = bytes[1], bytes[2]

        for code in self.joy_position_to_codes(joy_x, joy_y):

            yield code

    def joy_position_to_codes(self, joy_x: int, joy_y: int):
        # joystick positions are betwen 0x00 and 0xFF

        codes = ["NEG_3", "NEG_2", "NEG_1", "ZERO_0", "POS_1", "POS_2", "POS_3"]
        thresholds = [0x25, 0x50, 0x60, 0x80, 0xA0, 0xC0]
        # the y axis is reversed

        # look up x value in x_thresholds and yield corresponding keycode
        x_index = bisect.bisect_left(thresholds, joy_x)
        y_index = bisect.bisect_left(thresholds, joy_y)
        if x_index < len(codes):
            code = codes[x_index]
            if code:

                if code.startswith("ZERO"):
                    if not self._joy_x_zero:
                        yield f"JOY_X_{code}"
                        self._joy_x_zero = True
                else:
                    self._joy_x_zero = False
                    yield f"JOY_X_{code}"
        if y_index < len(codes):
            code = list(reversed(codes))[y_index]
            if code:
                if code.startswith("ZERO"):
                    if not self._joy_y_zero:
                        yield f"JOY_Y_{code}"
                        self._joy_y_zero = True
                else:
                    self._joy_y_zero = False
                    yield f"JOY_Y_{code}"

    def determine_held_keycodes(self, bytes: Sequence[int]):
        """Given a bitmask of held keys, yield the corresponding keycodes."""
        # for each keycode in the keycodes dict
        for key, (byte, bit_position) in g13lib.data.keycodes.items():
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

    def set_compositor(self, compositor: LCDCompositor):

        self.compositor = compositor

    def lcd_tick(self, *msg):
        """Refresh the LCD with the current console framebuffer if it's changed."""
        # refresh at 30 Hz max
        current_time = time.time()
        if current_time - self._lcd_tick_timer < 0.033:
            return
        self._lcd_tick_timer = current_time
        fb_image = self.compositor.render()
        if fb_image != self._lcd_framebuffer:

            self._lcd_framebuffer = fb_image
            self.setLCD(ImageToLPBM(fb_image))

    def start_usb_device(self):
        # USB device for control transfers (LCD, LEDs, backlight)
        usb_device = usb.core.find(idVendor=0x046D, idProduct=0xC21C)
        if usb_device is None:
            raise ValueError("G13 device not found")
        elif type(usb_device) is not usb.core.Device:
            raise ValueError("Invalid USB device")
        # okay, great
        self.usb_device = usb_device

        if self.usb_device.is_kernel_driver_active(0):
            self.usb_device.detach_kernel_driver(0)

        # at this point, we're initialized to the point
        # where we can drop root privileges
        drop_root_privs()

        # honestly not sure what this does or whether it's necessary
        # but it seems to be a good practice
        cfg = usb.util.find_descriptor(self.usb_device)
        self.usb_device.set_configuration(cfg)

    def get_codes(self, msg=None):
        """Poll the USB device for key events and joystick positions."""
        try:
            read_result = self.read_data()
        except usb.core.USBError as e:
            if e.errno in (errno.EPIPE, errno.EIO):  # pipe error?
                logger.error("USB Error: {}, resetting", e)
                self.usb_device.reset()
                return G13USBError(str(e))

            # re-raise the unhandled exception...
            # maybe handle them in the future?
            logger.error("Unhandled USB Error: {} ({})", e, e.errno)
            raise
        if read_result:
            events = list(self.key_events(read_result))
            for event in events:
                blinker.signal("g13_key").send(event)

            joy_events = list(self.joystick_position(read_result))
            for event in joy_events:
                blinker.signal("g13_joy").send(event)

    def read_data(self) -> list[int]:
        """Read 8 bytes from the USB device."""

        d = None
        try:
            d = self.usb_device.read(0x81, 8, 100)
        except usb.core.USBError as e:
            if e.errno == errno.ETIMEDOUT:  # Timeout error
                pass

            else:
                raise
        return d

    def toggle_led(self, led_no: int):
        self.led_status[led_no] = 1 - self.led_status[led_no]
        self.update_leds()

    def led_on(self, led_no: int):
        self.led_status[led_no] = 1
        self.update_leds()

    def led_off(self, led_no: int):
        self.led_status[led_no] = 0
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
