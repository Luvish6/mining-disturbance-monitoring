"""Inspect a bounded MineNetCD256 viewer subset and write an external manifest."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
from urllib.parse import urlencode, urlsplit
from urllib.request import urlopen

import numpy as np
from PIL import Image

DATASET = "HZDR-FWGEL/MineNetCD256"
REVISION = "73c771bda9e5c5a1aed755077b1e61596e613161"
HOST = "datasets-server.huggingface.co"
SPLITS = {"train": (60, 47743), "val": (10, 4613), "test": (30, 19355)}
FIELDS = {"imageA": "RGB", "imageB": "RGB", "label": "L"}


def fetch(url, limit):
    with urlopen(url, timeout=30) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Response exceeded the bounded read size")
    return data


def metadata(endpoint, **params):
    query = urlencode(dict(dataset=DATASET, config="default", **params))
    return json.loads(fetch(f"https://{HOST}/{endpoint}?{query}", 262144))


def verify_roster(records):
    roster, seen = {}, set()
    for split, (sites, rows) in SPLITS.items():
        record = records[split]
        domain, = [col["column_statistics"] for col in record["statistics"]
                   if col["column_name"] == "domain"]
        counts = domain["frequencies"]
        if (record["partial"] is not False or record["num_examples"] != rows
                or domain["nan_count"] or domain["no_label_count"]
                or len(counts) != sites or domain["n_unique"] != sites
                or sum(counts.values()) != rows or seen.intersection(counts)
                or any(not re.fullmatch(r"[A-Za-z]+_[0-9]+", site) or count <= 0
                       for site, count in counts.items())):
            raise ValueError("Official split assignments could not be reproduced")
        roster[split] = counts
        seen.update(counts)
    return roster


def inspect_patch(split, item, roster):
    row = item["row"]
    index = item["row_idx"]
    site = row["domain"]
    if site not in roster[split] or set(row) != {*FIELDS, "domain"} or item["truncated_cells"]:
        raise ValueError("Unknown site or unexpected row schema")
    identifier = f"{REVISION}:{split}:{index}"
    assets = {}
    for field, mode in FIELDS.items():
        asset = row[field]
        url = urlsplit(asset["src"])
        prefix = f"/cached-assets/{DATASET}/--/{REVISION}/--/default/{split}/{index}/{field}/"
        if url.scheme != "https" or url.netloc != HOST or not url.path.startswith(prefix):
            raise ValueError("Asset revision or row identity mismatch")
        if (asset["width"], asset["height"]) != (256, 256):
            raise ValueError("Asset metadata dimensions disagree")
        raw = fetch(asset["src"], 262144)
        with Image.open(BytesIO(raw)) as image:
            if image.size != (256, 256) or image.mode != mode:
                raise ValueError("Unexpected image dimensions or channel layout")
            pixels = np.asarray(image)
        assets[field] = dict(id=f"{identifier}:{field}", sha256=sha256(raw).hexdigest())
        if field == "label":
            histogram = np.bincount(pixels.ravel(), minlength=256)
            counts = dict(unchanged=int(histogram[0]), changed=int(histogram[255]),
                          ambiguous=int(histogram[1:255].sum()))
    # The cropped release has row/asset identity but no original scene identifiers.
    return dict(patch_id=identifier, row_index=index, site_id=site, split=split,
                source_scene_ids=None, assets=assets, label_counts=counts)


def build_manifest():
    with ThreadPoolExecutor(max_workers=3) as pool:
        records = dict(zip(SPLITS, pool.map(lambda s: metadata("statistics", split=s), SPLITS), strict=True))
        roster = verify_roster(records)

        def sample(split):
            page = metadata("rows", split=split, offset=0, length=12)
            features = {f["name"]: f["type"]["_type"] for f in page["features"]}
            if (features != {"imageA": "Image", "imageB": "Image", "label": "Image", "domain": "Value"}
                    or page["num_rows_total"] != SPLITS[split][1]
                    or [item["row_idx"] for item in page["rows"]] != list(range(12))):
                raise ValueError("Unexpected official schema or row selection")
            return [inspect_patch(split, row, roster) for row in page["rows"][:5]]

        patches = [patch for batch in pool.map(sample, SPLITS) for patch in batch]
    return dict(dataset=DATASET, revision=REVISION, official_roster=roster,
                mask_policy="Viewer JPEG: 0 unchanged, 255 changed, 1–254 ambiguous; no thresholding",
                split_summary={split: dict(patches=5, sites=sorted({p["site_id"] for p in patches if p["split"] == split}),
                                          **{key: sum(p["label_counts"][key] for p in patches if p["split"] == split)
                                             for key in ("unchanged", "changed", "ambiguous")})
                               for split in SPLITS},
                patches=patches)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_name", help="New JSON basename under outputs/external_minenetcd256")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+\.json", args.output_name):
        parser.error("Use a JSON filename without a directory")
    root = Path(__file__).resolve().parents[1]
    output = root / "outputs/external_minenetcd256" / args.output_name
    if output.exists():
        parser.error("Choose a new manifest filename")
    manifest = build_manifest()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps(manifest["split_summary"], indent=2))


if __name__ == "__main__":
    main()
