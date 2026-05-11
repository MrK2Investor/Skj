from __future__ import annotations

from io import BytesIO
from typing import Any

import numpy as np
from PIL import Image


class ImageProcessingError(ValueError):
    pass


def _ensure_rgb(img: Image.Image) -> Image.Image:
    if img.mode not in ("RGB", "RGBA"):
        return img.convert("RGB")
    if img.mode == "RGBA":
        return img.convert("RGB")
    return img


def load_image_to_array(image_bytes: bytes) -> np.ndarray:
    with Image.open(BytesIO(image_bytes)) as img:
        img = _ensure_rgb(img)
        return np.array(img)


def array_to_png_bytes(array: np.ndarray) -> bytes:
    output = BytesIO()
    Image.fromarray(array.astype(np.uint8)).save(output, format="PNG")
    return output.getvalue()


def invert(img_array: np.ndarray, params: dict[str, Any] | None = None) -> np.ndarray:
    return (255 - img_array).astype(np.uint8)


def mirror(img_array: np.ndarray, params: dict[str, Any] | None = None) -> np.ndarray:
    return img_array[:, ::-1, :].astype(np.uint8)


def crop(img_array: np.ndarray, params: dict[str, Any] | None = None) -> np.ndarray:
    params = params or {}

    height, width = img_array.shape[:2]

    # buď zadáš x/y/w/h, nebo fallback odstraní 100 px okraje
    x = int(params.get("x", 100))
    y = int(params.get("y", 100))
    w = int(params.get("width", width - 200))
    h = int(params.get("height", height - 200))

    if x < 0 or y < 0 or w <= 0 or h <= 0:
        raise ImageProcessingError("Crop parameters must be positive")

    if x + w > width or y + h > height:
        raise ImageProcessingError(
            f"Crop is outside image dimensions. Image size is {width}x{height}, "
            f"crop is x={x}, y={y}, width={w}, height={h}"
        )

    return img_array[y:y + h, x:x + w, :].astype(np.uint8)


def brightness(img_array: np.ndarray, params: dict[str, Any] | None = None) -> np.ndarray:
    params = params or {}
    value = int(params.get("value", 50))

    tmp = img_array.astype(np.int16)
    tmp = tmp + value
    tmp = np.clip(tmp, 0, 255)

    return tmp.astype(np.uint8)


def grayscale(img_array: np.ndarray, params: dict[str, Any] | None = None) -> np.ndarray:
    rgb = img_array.astype(np.float32)

    gray = (
        0.299 * rgb[:, :, 0]
        + 0.587 * rgb[:, :, 1]
        + 0.114 * rgb[:, :, 2]
    )

    gray = np.clip(gray, 0, 255).astype(np.uint8)

    # vrátíme RGB obrázek, aby šel stejně uložit a zobrazit jako barevný PNG
    return np.stack([gray, gray, gray], axis=2)


OPERATIONS = {
    "invert": invert,
    "negative": invert,
    "mirror": mirror,
    "flip_horizontal": mirror,
    "crop": crop,
    "brightness": brightness,
    "grayscale": grayscale,
}


def process_image_bytes(
    image_bytes: bytes,
    operation: str,
    params: dict[str, Any] | None = None,
) -> bytes:
    if operation not in OPERATIONS:
        raise ImageProcessingError(f"Unsupported image operation: {operation}")

    img_array = load_image_to_array(image_bytes)
    new_array = OPERATIONS[operation](img_array, params)

    return array_to_png_bytes(new_array)
