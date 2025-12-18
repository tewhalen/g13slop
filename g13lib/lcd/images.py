from PIL import Image

from g13lib.render_fb import Layer


class SimpleImageLayer(Layer):
    image: Image.Image
    position: tuple[int, int]

    def __init__(self, image: Image.Image, position: tuple[int, int] = (0, 0)):
        self.image = image
        self.position = position

    def render(self) -> tuple[Image.Image | None, tuple[int, int]]:
        return self.image, self.position


class DecayingImage(SimpleImageLayer):
    """An image that decays after a set number of renderings (10ms apart)"""

    decay_ticks: int = 30
    current_ticks: int = 0

    def __init__(self, image: Image.Image, position: tuple[int, int] = (0, 0)):
        # convert to RGBA to support transparency
        self.image = image.convert("RGBA")
        self.position = position

    def faded_image(self) -> Image.Image | None:
        """Return the faded image based on current ticks."""
        if self.current_ticks < self.decay_ticks:
            faded_image = self.image.copy()
            alpha = int(255 * (1 - self.current_ticks / self.decay_ticks))
            faded_image.putalpha(alpha)
            # composite with white background
            background = Image.new("RGBA", faded_image.size, (0, 0, 0, 255))
            background.paste(faded_image, (0, 0), faded_image)
            return background.convert("1")  # convert to 1-bit image with dithering
        else:
            return None

    def render(self) -> tuple[Image.Image | None, tuple[int, int]]:
        self.current_ticks += 1
        faded_image = self.faded_image()
        return faded_image, self.position
