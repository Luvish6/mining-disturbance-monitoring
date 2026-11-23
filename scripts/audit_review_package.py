"""Offline, fail-closed audit of the existing Sentinel-only Phase 23I reviewer ZIP."""
import hashlib
import json
import re
import zipfile
from pathlib import Path

S2_ID = re.compile(r"^20[0-9]{6}T[0-9]{6}_20[0-9]{6}T[0-9]{6}_T[0-9]{2}[A-Z]{3}$")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def validate_archive(archive, trusted_chips, ids):
    """Allow only expected blinded files; compare every PNG with the verified render."""
    ids = list(ids)
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r"R[0-9A-F]{8}", i) for i in ids):
        raise ValueError("Invalid review identities")
    expected = {f"chips10/{i}.png" for i in ids} | {"README.txt", "review_B.html", "review_sheet_B.csv"}
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or set(names) != expected or z.testzip():
            raise ValueError("Unapproved, duplicate, missing or corrupt package member")
        hashes = {}
        for i in ids:
            data = z.read(f"chips10/{i}.png")
            if data != (trusted_chips / f"{i}.png").read_bytes():
                raise ValueError("Unverified reviewer PNG: " + i)
            hashes[i] = sha(data)
        page = z.read("review_B.html").decode("utf-8")
        # Offline reviewer package must not connect to the private Planet viewer or remote imagery.
        if re.search(r"https?://|__planet_review__|<iframe|<script[^>]+src=", page, re.I):
            raise ValueError("External/private viewer dependency in review page")
    return hashes


def validate_s2_metadata(metadata, ids):
    if set(metadata) != set(ids):
        raise ValueError("Metadata/reviewer identity mismatch")
    for record in metadata.values():
        if set(record) != {"before", "after", "follow"}:
            raise ValueError("Unexpected seasons")
        for season in record.values():
            if not season.get("ids") or any(not S2_ID.fullmatch(i) for i in season["ids"]):
                raise ValueError("Non-Sentinel or missing source identity")


def main():
    root = Path("outputs/phase23i_review")
    ids = [r["review_id"] for r in json.loads((root / "crosswalk.json").read_bytes())]
    if len(ids) != 30:
        raise ValueError("Expected the frozen 30 items")
    validate_s2_metadata(json.loads((root / "s2_10m/metadata.json").read_bytes()), ids)
    hashes = validate_archive(root / "share_reviewer_B.zip", root / "chips10", ids)
    print(json.dumps(dict(items=len(hashes), source="Sentinel-2 only", planet_assets=0,
                          zip_sha256=sha((root / "share_reviewer_B.zip").read_bytes())), sort_keys=True))


if __name__ == "__main__":
    main()
