from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from image_processor import ImageProcessingError, load_image_to_array, process_image_bytes


def make_test_png() -> bytes:
    arr = np.array(
        [
            [[255, 0, 0], [0, 255, 0]],
            [[0, 0, 255], [255, 255, 255]],
        ],
        dtype=np.uint8,
    )

    output = BytesIO()
    Image.fromarray(arr).save(output, format="PNG")
    return output.getvalue()


def test_invert():
    result = process_image_bytes(make_test_png(), "invert")
    arr = load_image_to_array(result)

    assert arr[0, 0].tolist() == [0, 255, 255]


def test_mirror():
    result = process_image_bytes(make_test_png(), "mirror")
    arr = load_image_to_array(result)

    assert arr[0, 0].tolist() == [0, 255, 0]


def test_brightness_saturates():
    result = process_image_bytes(make_test_png(), "brightness", {"value": 50})
    arr = load_image_to_array(result)

    assert arr[0, 0].tolist() == [255, 50, 50]


def test_grayscale():
    result = process_image_bytes(make_test_png(), "grayscale")
    arr = load_image_to_array(result)

    assert arr[0, 0, 0] == arr[0, 0, 1] == arr[0, 0, 2]


def test_crop_invalid_dimensions():
    with pytest.raises(ImageProcessingError):
        process_image_bytes(
            make_test_png(),
            "crop",
            {"x": 0, "y": 0, "width": 999, "height": 999},
        )


def test_invalid_operation_does_not_pass():
    with pytest.raises(ImageProcessingError):
        process_image_bytes(make_test_png(), "exploit-op")
