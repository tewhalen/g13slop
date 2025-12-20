import errno

import usb.core
import usb.util
from loguru import logger
from PIL import Image

from g13lib.render_fb import ImageToLPBM
from g13lib.security import drop_root_privs


class G13USBError(Exception):
    pass


class G13USBDevice:
    product_id = "0xc21c"
    vendor_id = "0x046d"

    usb_device: usb.core.Device

    # setting this number lower than 100
    # seems to cause lots of USB errors
    # at least on my system with my device
    READ_TIMEOUT_MS = 100

    def __init__(self):
        self.start_usb_device()

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
        # where we should drop root privileges
        drop_root_privs()

        # honestly not sure what this does or whether it's necessary
        # but it seems to be a good practice
        cfg = usb.util.find_descriptor(self.usb_device)
        self.usb_device.set_configuration(cfg)
        logger.success("G13 USB device initialized")

    def read_data(self) -> list[int] | None | G13USBError:
        """Read 8 bytes from the USB device. If the read times out, return None."""

        d = None
        try:
            d = self.usb_device.read(0x81, 8, self.READ_TIMEOUT_MS)
        except usb.core.USBError as e:
            if e.errno == errno.ETIMEDOUT:  # Timeout error
                pass
            elif e.errno in (errno.EPIPE, errno.EIO):  # pipe error?
                logger.error("USB Error: {}, resetting", e)
                self.usb_device.reset()
                return G13USBError(str(e))
            else:
                # re-raise the unhandled exception...
                # maybe handle them in the future?
                logger.error("Unhandled USB Error: {} ({})", e, e.errno)
                raise
        return d

    def update_leds(self, led_status: list[int]):
        # use the led status to make a binary bitmask
        mask = 0
        for i, status in enumerate(led_status):
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

    async def setLCD(self, fb_image: Image.Image):
        header = [0] * 32
        header[0] = 0x03
        image_buffer = ImageToLPBM(fb_image)
        self.usb_device.write(
            usb.util.CTRL_OUT | 2,  # Endpoint 2 for LCD
            bytes(header) + bytes(image_buffer),
        )

    def close(self):

        self.usb_device.reset()
        usb.util.dispose_resources(self.usb_device)
