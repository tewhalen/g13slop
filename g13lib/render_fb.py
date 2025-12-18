from loguru import logger
from PIL import Image

LCD_WIDTH = 160
LCD_HEIGHT = 48


class Layer:

    def render(self) -> tuple[Image.Image | None, tuple[int, int]]:
        """Render the layer to an image."""
        raise NotImplementedError("Subclasses must implement render method.")


class LCDCompositor:
    scene: list

    lcd_dims = (LCD_WIDTH, LCD_HEIGHT)

    def __init__(self, *layers):
        self.scene = list(layers)

    def render(self) -> Image.Image:
        """Render the current scene to an image."""
        framebuffer = Image.new(
            "1", self.lcd_dims, color=1
        )  # start with white background

        for z, layer in enumerate(self.scene):
            layer_image, position = layer.render()
            if layer_image:
                # if there's an alpha channel, use it as a mask
                if layer_image.mode in ("RGBA", "LA") or (
                    layer_image.mode == "P" and "transparency" in layer_image.info
                ):
                    framebuffer.paste(layer_image, position, layer_image)
                else:
                    framebuffer.paste(layer_image, position)
                layer_image.save(f"davinci_layer_{z}.png")

        return framebuffer


def ImageToLPBM(image: Image.Image):
    """Simple function to convert a PIL Image into LPBM format.

    LPBM is a bitmap, with each byte representing 8 vertical pixels.
    """
    monochrome_dithered_img = image.convert("1")
    i = monochrome_dithered_img.load()

    output = [[int(0)] * LCD_WIDTH for _ in range(LCD_HEIGHT // 8)]

    for im_col in range(LCD_WIDTH):
        for im_row in range(LCD_HEIGHT):
            out_col = im_col
            out_row = im_row // 8
            # Convert pixel to 1 or 0 (PIL mode "1" returns 255 for white, 0 for black)
            pixel_bit = 1 if i[im_col, im_row] else 0
            output[out_row][out_col] |= pixel_bit << (im_row % 8)
            assert output[out_row][out_col] <= 255

    # flatten list and return
    return [byte for row in output for byte in row]
