import base64
import io
from PIL import Image


def process_and_convert_image_to_base64(img, maxHeight):
    try:
        img = Image.open(io.BytesIO(base64.b64decode(img)))
        img = img.convert("RGB")
        oldWidth, oldHeight = img.size

        if oldHeight > maxHeight:
            ratio = maxHeight / oldHeight
            img.thumbnail((oldWidth * ratio, oldHeight * ratio))

        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", optimize=True, quality=50)
        img = base64.b64encode(buffered.getvalue())
        return img
    except Exception as e:
        raise e