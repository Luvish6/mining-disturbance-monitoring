from copy import deepcopy
from io import BytesIO

from PIL import Image
import pytest

from scripts import minenetcd256_adapter as adapter


def test_roster_fails_closed_on_shared_site(monkeypatch):
    monkeypatch.setattr(adapter, "SPLITS", {"train": (1, 2), "test": (1, 2)})

    def record(site):
        return dict(partial=False, num_examples=2, statistics=[dict(column_name="domain",
                    column_statistics=dict(frequencies={site: 2}, nan_count=0, no_label_count=0, n_unique=1))])

    metadata = {"train": record("Mine_01"), "test": record("Mine_02")}
    assert adapter.verify_roster(metadata)["train"] == {"Mine_01": 2}
    with pytest.raises(ValueError, match="assignments"):
        adapter.verify_roster(dict(metadata, test=record("Mine_01")))


def test_patch_validates_alignment_and_keeps_ambiguous_values(monkeypatch):
    def encode(image):
        output = BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()

    mask = Image.new("L", (256, 256))
    mask.putpixel((0, 0), 255)
    mask.putpixel((1, 0), 127)
    rgb = encode(Image.new("RGB", (256, 256)))
    monkeypatch.setattr(adapter, "fetch", lambda url, limit: encode(mask) if "/label/" in url else rgb)
    row = dict(domain="Mine_01", **{field: dict(width=256, height=256,
        src=f"https://{adapter.HOST}/cached-assets/{adapter.DATASET}/--/{adapter.REVISION}/--/default/train/0/{field}/image.png")
        for field in adapter.FIELDS})
    record = dict(row_idx=0, row=row, truncated_cells=[])
    roster = {"train": {"Mine_01": 1}}
    assert adapter.inspect_patch("train", record, roster)["label_counts"] == {
        "unchanged": 65534, "changed": 1, "ambiguous": 1}
    bad = deepcopy(record)
    bad["row"]["imageB"]["width"] = 255
    with pytest.raises(ValueError, match="dimensions"):
        adapter.inspect_patch("train", bad, roster)
