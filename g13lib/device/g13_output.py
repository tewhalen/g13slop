import blinker
import PIL.Image

from g13lib.async_help import PeriodicComponent, run_periodic
from g13lib.device.g13_usb_device import G13USBDevice
from g13lib.render_fb import LCDCompositor


class G13DeviceOutputManager(PeriodicComponent):
    """Handles output to the G13 device, including LCD updates and LED status.

    Maintains a task to periodically refresh the LCD display and responds to signals
    for updating the compositor and LED states.
    """

    g13_usb_device: G13USBDevice

    led_status: list[int]

    compositor: LCDCompositor
    _lcd_framebuffer: PIL.Image.Image

    # this seems fine
    LCD_REFRESH_MS = 33  # refresh at ~30 Hz

    def __init__(self, g13_usb_device: G13USBDevice):

        self.g13_usb_device = g13_usb_device

        self.led_status = [0, 0, 0, 0]

        self.compositor = LCDCompositor()
        self._lcd_framebuffer = PIL.Image.new("RGB", (160, 43))

        self._tasks_to_start = [
            run_periodic(self.lcd_tick, self.LCD_REFRESH_MS, initial_delay_ms=100)
        ]

        blinker.signal("set_compositor").connect(self.set_compositor)
        blinker.signal("g13_led_toggle").connect(self.toggle_led)
        blinker.signal("g13_led_on").connect(self.led_on)
        blinker.signal("g13_led_off").connect(self.led_off)

    def set_compositor(self, compositor: LCDCompositor):
        """Replace the current LCD compositor with a new one."""

        self.compositor = compositor

    async def lcd_tick(self, *msg):
        """Refresh the LCD with the current console framebuffer if it's changed."""
        # refresh at 30 Hz max

        fb_image = self.compositor.render()
        if fb_image != self._lcd_framebuffer:

            self._lcd_framebuffer = fb_image
            self.g13_usb_device.setLCD(fb_image)

    def toggle_led(self, *leds: int):
        """Toggle the state of the specified LED on the G13 device."""
        for led_no in leds:
            self.led_status[led_no] = 1 - self.led_status[led_no]
        self.g13_usb_device.update_leds(self.led_status)

    def led_on(self, *leds: int):
        """Turn on the specified LED on the G13 device."""
        for led_no in leds:
            self.led_status[led_no] = 1
        self.g13_usb_device.update_leds(self.led_status)

    def led_off(self, *leds: int):
        """Turn off the specified LED on the G13 device."""
        for led_no in leds:
            self.led_status[led_no] = 0
        self.g13_usb_device.update_leds(self.led_status)
