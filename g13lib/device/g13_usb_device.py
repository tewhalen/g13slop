import errno
import queue
import threading

import usb.core
import usb.util
from loguru import logger
from PIL import Image

from g13lib.render_fb import ImageToLPBM
from g13lib.security import drop_root_privs


class G13USBError(Exception):
    pass


class G13USBDevice:
    """
    Interface for communicating with the Logitech G13 USB device.
    Manages USB I/O in a separate thread to avoid blocking the main application.
    """

    product_id = 0xC21C
    vendor_id = 0x046D

    usb_device: usb.core.Device

    read_queue: queue.Queue
    write_queue: queue.Queue

    _thread: threading.Thread
    running: bool = False

    # setting this number too low
    # seems to cause lots of USB errors
    # at least on my system with my device
    READ_TIMEOUT_MS = 10

    def __init__(self):
        self.read_queue = queue.Queue()
        self.write_queue = queue.Queue()

        self._thread = threading.Thread(target=self._usb_thread_main)
        self.running = True
        self._thread.start()

    def _usb_thread_main(self):

        self.start_usb_device()
        while self.running:
            # outgoing commands
            try:
                cmd = self.write_queue.get_nowait()
                if cmd["type"] == "set_backlight":
                    r, g, b = cmd["r"], cmd["g"], cmd["b"]
                    self._set_backlight(r, g, b)
                elif cmd["type"] == "set_lcd":
                    self._setLCD(cmd["fb_image"])
                elif cmd["type"] == "set_leds":
                    self._update_leds(cmd["led_status"])
                elif cmd["type"] == "stop":
                    self._close()
                    self.running = False
                    continue
            except queue.Empty:
                pass

            # incoming data
            try:
                data = self._read_data()
                if data is not None:
                    self.read_queue.put(("input", data))
            except Exception as e:
                self.read_queue.put(("error", G13USBError(str(e))))

    def start_usb_device(self):
        """Initialize the USB device. Drops root privileges after initialization.

        Runs within the USB thread."""
        # USB device for control transfers (LCD, LEDs, backlight)
        usb_device = usb.core.find(idVendor=self.vendor_id, idProduct=self.product_id)
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
        """Read data from the USB input queue if available. Non-blocking."""

        try:
            msg_type, data = self.read_queue.get_nowait()
            if msg_type == "input":
                return data
            elif msg_type == "error":
                return data
        except queue.Empty:
            return None

    def _read_data(self) -> list[int] | None | G13USBError:
        """Read 8 bytes from the USB device. If the read times out, return None.

        Runs within the USB thread."""

        d = None
        try:
            d = self.usb_device.read(0x81, 8, self.READ_TIMEOUT_MS)
        except usb.core.USBError as e:
            if e.errno == errno.ETIMEDOUT:  # Timeout error
                pass
            elif e.errno in (errno.EPIPE, errno.EIO):  # pipe error?
                logger.error("USB Error: {}, resetting", e)
                self.usb_device.reset()
                raise
                # return G13USBError(str(e))
            else:
                # re-raise the unhandled exception...
                # maybe handle them in the future?
                logger.error("Unhandled USB Error: {} ({})", e, e.errno)
                raise
        return d

    def update_leds(self, led_status: list[int]):
        self.write_queue.put({"type": "set_leds", "led_status": led_status})

    def _update_leds(self, led_status: list[int]):
        """Update the LED status on the G13 device.

        Runs within the USB thread."""
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
        self.write_queue.put({"type": "set_backlight", "r": r, "g": g, "b": b})

    def _set_backlight(self, r: int, g: int, b: int):
        """Set the backlight color on the G13 device.

        Runs within the USB thread."""
        data = [7, int(r), int(g), int(b), 0]
        self.usb_device.ctrl_transfer(
            usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE,
            bRequest=9,
            wValue=0x307,
            wIndex=0,
            data_or_wLength=data,
        )

    def setLCD(self, fb_image: Image.Image):
        """Convert the framebuffer image and queue it for sending to the G13 device."""

        # rather than convert the image inside the USB thread,
        # do it here and just send the converted data to the USB thread
        # we don't want to do any "heavy" processing inside the USB thread
        converted_image = ImageToLPBM(fb_image)
        self.write_queue.put({"type": "set_lcd", "fb_image": converted_image})

    def _setLCD(self, lpbm_image: list[int]):
        """Send the converted framebuffer image to the G13 device.

        Runs within the USB thread."""
        header = [0] * 32
        header[0] = 0x03

        self.usb_device.write(
            usb.util.CTRL_OUT | 2,  # Endpoint 2 for LCD
            bytes(header) + bytes(lpbm_image),
        )

    def close(self):
        """Close the USB device and stop the USB thread."""
        self.write_queue.put({"type": "stop"})
        self._thread.join()

    def _close(self):
        """Close the USB device and cleanup resources.

        Runs within the USB thread."""
        self.usb_device.reset()
        usb.util.dispose_resources(self.usb_device)
