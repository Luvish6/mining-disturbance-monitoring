from io import BytesIO

import numpy as np
from PIL import Image
import pytest

from scripts import minenetcd256_rf_pilot as pilot


def asset(image, encoding="PNG"):
    buffer = BytesIO()
    image.save(buffer, format=encoding)
    return {"bytes": buffer.getvalue()}


def test_signed_rgb_and_explicit_ambiguity_exclusion():
    mask = Image.new("L", (256, 256))
    mask.putpixel((0, 0), 255)
    mask.putpixel((1, 0), 37)
    row = {"imageA": asset(Image.new("RGB", (256, 256), (255, 4, 12))),
           "imageB": asset(Image.new("RGB", (256, 256), (0, 14, 10))),
           "label": asset(mask)}
    x, y, excluded = pilot.patch_arrays(row)
    assert np.array_equal(x[0], [-255, 10, -2])
    assert x.shape == (65535, 3)
    assert y[0] == 1 and y.sum() == 1 and excluded == 1

    row["label"] = asset(mask, "JPEG")
    with pytest.raises(ValueError, match="lossless"):
        pilot.patch_arrays(row)


def test_range_budget_stops_before_request():
    source = pilot.RangeSource.__new__(pilot.RangeSource)
    source.budget = 4
    source.url = "unused"
    with pytest.raises(ValueError, match="budget"):
        source._range(0, 4)
