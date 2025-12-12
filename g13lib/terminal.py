import itertools

from PIL import Image, ImageChops, ImageDraw, ImageFont

spleen_font = ImageFont.load("font/spleen-5x8.pil")


class LogEmulator:
    width = 34
    height = 5
    buffer: list
    autowrap: bool = True
    status: str = ""

    def __init__(self):
        self.buffer = [" " * self.width for _ in range(self.height)]
        self.status = ""

    def split_input(self, raw_line: str):
        lines = []
        for line in raw_line.splitlines():
            if self.autowrap:
                for sub_line in itertools.batched(line, self.width):
                    sub_line = "".join(sub_line)
                    # print(sub_line)
                    lines.append(sub_line.ljust(self.width)[: self.width])
            else:
                lines.append(line.ljust(self.width)[: self.width])
        return lines

    def output(self, raw_line: str):
        for line in self.split_input(raw_line):
            self.buffer.append(line)
        self.buffer = self.buffer[-self.height :]

    def set_status(self, status: str):
        self.status = status

    def clear_status(self):
        self.status = ""

    def content(self):
        return ["".join(row) for row in self.buffer]

    def draw_buffer(self):
        image = Image.new(
            "1", (160, 48), 1
        )  # Mode "1" for 1-bit pixels, white background
        draw = ImageDraw.Draw(image)

        # if the status line is set, skip the first row of the buffer
        content = self.content()
        if self.status:
            content = content[1:]

        for i, row_content in enumerate(content):
            draw.text((0, i * 9), row_content, font=spleen_font, fill=0)

        # if there's a status line, draw a black box on the final row
        # and then the status line on top in white
        if self.status:
            draw.rectangle((0, (self.height - 1) * 9, 160, 48), fill=0)
            draw.text((0, (self.height - 1) * 9), self.status, font=spleen_font, fill=1)
        image = image.convert("L")
        return ImageChops.invert(image).convert("1")  # white on black


if __name__ == "__main__":
    t = LogEmulator()

    t.output("This is a test of the terminal and the lines are too long")

    image = t.draw_buffer()
    image.save("default_font_output.png")
