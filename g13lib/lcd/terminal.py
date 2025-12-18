"""
A 'terminal emulator' for the G13's LCD screen.

Maintains a buffer of text lines, and renders them to a full-screen image that can be
sent to the G13.

Monitors a signal for new text to print, and updates the image accordingly.
Also supports a bottom status line that can appear at the bottom of the screen. (Ideal for labeling
the L1-L4 keys, for example.)

Currently this sends out the framebuffer Image when updated,
but also listens for a signal and returns the image when requested.

This might alllow better control over what's drawn when. (E.g. we could swap from
an image to the terminal view on demand, or composite multiple images together,
animate transitions, etc.)

"""

import itertools

import blinker
from PIL import Image, ImageChops, ImageDraw, ImageFont

from g13lib.render_fb import Layer

spleen_font = ImageFont.load("font/spleen-5x8.pil")


class LogEmulator(Layer):
    # G13 LCD is 160x48 pixels
    lcd_dims = (160, 48)
    # G13 LCD dimensions in character cells using 5x8 font
    row_chars: int = 32
    term_rows: int = 5

    row_height: int = 9  # pixels per text row

    # NOTE: 8 pixel font + 1 pixel spacing
    # total rows = 48 / 9 = 5.33, so we can fit 5 full rows
    # we're wasting 3 rows of pixels?
    # or maybe the display is not exactly 48 pixels high?

    buffer: list[str]
    autowrap: bool = True
    status: str = ""

    dirty: bool = True
    _image_cache: Image.Image | None = None

    def __init__(self):
        # initialize the buffer with empty lines
        self.buffer = [" " * self.row_chars for _ in range(self.term_rows)]
        self.status = ""
        blinker.signal("g13_print").connect(self.output)
        blinker.signal("g13_set_status").connect(self.set_status)
        blinker.signal("g13_clear_status").connect(self.clear_status)
        blinker.signal("term_framebuffer_request").connect(self.framebuffer)
        blinker.signal("term_updated_framebuffer_request").connect(
            self.updated_framebuffer
        )

    def _invalidate(self, msg=None):
        self.dirty = True
        self._image_cache = None

    def split_input(self, raw_line: str):
        lines = []
        for line in raw_line.splitlines():
            if self.autowrap:
                for sub_line in itertools.batched(line, self.row_chars):
                    sub_line = "".join(sub_line)
                    # print(sub_line)
                    lines.append(sub_line.ljust(self.row_chars)[: self.row_chars])
            else:
                lines.append(line.ljust(self.row_chars)[: self.row_chars])
        return lines

    def output(self, raw_line: str):
        for line in self.split_input(raw_line):
            self.buffer.append(line)
        self.buffer = self.buffer[-self.term_rows :]
        self._invalidate()
        blinker.signal("g13_framebuffer").send(self.framebuffer())

    def set_status(self, status: str):
        self.status = status
        self._invalidate()
        blinker.signal("g13_framebuffer").send(self.framebuffer())

    def clear_status(self, *msg):
        self.status = ""
        self._invalidate()
        blinker.signal("g13_framebuffer").send(self.framebuffer())

    def content(self) -> list[str]:
        return ["".join(row) for row in self.buffer]

    def framebuffer(self, msg=None) -> Image.Image:
        if not self.dirty and self._image_cache:
            return self._image_cache

        self._image_cache = self._render_buffer_to_image()
        self.dirty = False
        return self._image_cache

    def updated_framebuffer(self, msg=None) -> Image.Image | None:
        """Returns the framebuffer image, only if dirty."""
        if self.dirty or not self._image_cache:
            return self.framebuffer()
        else:
            # not updated
            return None

    def _render_buffer_to_image(self):
        image = Image.new(
            "1", self.lcd_dims, 1
        )  # Mode "1" for 1-bit pixels, white background
        draw = ImageDraw.Draw(image)

        # if the status line is set, skip the first row of the buffer
        content = self.content()
        if self.status:
            content = content[1:]

        for i, row_content in enumerate(content):
            draw.text((0, i * self.row_height), row_content, font=spleen_font, fill=0)

        # if there's a status line, draw a black box on the final row
        # and then the status line on top in white
        if self.status:
            draw.rectangle(
                (
                    0,
                    (self.term_rows - 1) * self.row_height,
                    self.lcd_dims[0],
                    self.lcd_dims[1],
                ),
                fill=0,
            )
            draw.text(
                (0, (self.term_rows - 1) * self.row_height),
                self.status,
                font=spleen_font,
                fill=1,
            )
        image = image.convert("L")
        final = ImageChops.invert(image).convert("1")  # white on black
        return final

    def render(self) -> tuple[Image.Image, tuple[int, int]]:
        """Returns the current buffer image and its position."""
        return self.framebuffer(), (0, 0)


if __name__ == "__main__":
    t = LogEmulator()

    t.output("This is a test of the terminal and the lines are too long")

    image = t.framebuffer()
    image.save("default_font_output.png")
