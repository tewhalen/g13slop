from PIL import Image

LCD_WIDTH = 160
LCD_HEIGHT = 48


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
