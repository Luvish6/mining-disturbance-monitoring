"""Acquire the preregistered EuroMineNet development subset without opening TEST."""
import argparse
from hashlib import sha256
import io
import json
from pathlib import Path
import re
from urllib.parse import urlparse
from zipfile import ZipFile

import requests

URL = "https://rodare.hzdr.de/record/4656/files/EuroMineNet.zip"
LENGTH = 18_378_458_649
CAP = 512 * 1024**2
PRIOR = 4_259_372
BLOCK = 4 * 1024**2
HEADERS = 16 * 1024
SITES = {
    "train": ("Sweden_9", "Czechia_3", "Spain_15", "Slovakia_2", "Romania_8", "Finland_4",
              "Portuga_3", "Poland_9", "Hungary_1", "Austria_1", "Germany_14", "Italy_1"),
    "val": ("Sweden_2", "Czechia_2", "Romania_4", "Finland_7"),
    "test": ("Sweden_1", "Czechia_4", "Slovakia_1", "Romania_10"),
}
COSTS = {"train": 187_217_870, "val": 116_956_397, "test": 166_496_150}
TEST_RESERVE = COSTS["test"] + 3 * 1024**2


def digest(data):
    return sha256(data).hexdigest()


def save(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


class Archive(io.RawIOBase):
    """Strict, journaled random reader for a pinned public ZIP."""

    def __init__(self, root, request=requests.get):
        self.root, self.request = root, request
        self.position = 0
        self.enabled = None
        self.journal = root / "transfer.json"
        self.state = (json.loads(self.journal.read_bytes()) if self.journal.exists()
                      else dict(url=URL, length=LENGTH, prior=PRIOR, attempts=[], ranges={}))
        if (self.state["url"], self.state["length"], self.state["prior"]) != (URL, LENGTH, PRIOR):
            raise ValueError("Transfer journal archive identity differs")
        (root / "ranges").mkdir(exist_ok=True)

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        position = {0: 0, 1: self.position, 2: LENGTH}[whence] + offset
        if position < 0:
            raise OSError("Negative archive seek")
        self.position = position
        return position

    def read(self, size=-1):
        size = LENGTH - self.position if size < 0 else min(size, LENGTH - self.position)
        if size <= 0:
            return b""
        start, stop = self.position, self.position + size
        # Before the directory has been parsed, confine reads to ZIP tail metadata.
        lo, hi = self.enabled or (LENGTH - 1024**2, LENGTH)
        if not lo <= start < stop <= hi:
            raise ValueError("Unapproved ZIP byte range")
        value = b"".join(self.fetch(k, min(k + BLOCK, stop)) for k in range(start, stop, BLOCK))
        self.position = stop
        return value

    def fetch(self, start, stop):
        key = f"{start}-{stop-1}"
        path = self.root / "ranges" / key
        size = stop - start
        if key in self.state["ranges"]:
            content = path.read_bytes()
            if len(content) != size or digest(content) != self.state["ranges"][key]:
                raise ValueError("Cached archive range hash mismatch")
            return content
        for attempt in range(2):
            charged = size + HEADERS
            used = PRIOR + sum(r["charged"] for r in self.state["attempts"])
            if used + charged + TEST_RESERVE > CAP:
                raise ValueError("Aggregate cap reached with TEST bytes reserved")
            row = dict(range=key, charged=charged, received=0, complete=False)
            self.state["attempts"].append(row)
            save(self.journal, self.state)
            try:
                with self.request(URL, headers={"Range": f"bytes={key}", "Accept-Encoding": "identity"},
                                  stream=True, timeout=(15, 60), allow_redirects=False) as response:
                    row["status"] = response.status_code
                    if (response.status_code != 206
                            or response.headers.get("Content-Range") != f"bytes {key}/{LENGTH}"
                            or response.headers.get("Content-Encoding", "identity") != "identity"
                            or int(response.headers.get("Content-Length", size)) != size
                            or urlparse(response.url).hostname != "rodare.hzdr.de"):
                        raise ValueError("Archive response did not honor the exact pinned range")
                    content = response.raw.read(size)
                    row["received"] = len(content)
                    if len(content) != size:
                        raise OSError("Short archive range")
            except (requests.RequestException, OSError) as error:
                row["error"] = type(error).__name__
                if attempt == 1:
                    raise
            else:
                path.write_bytes(content)
                self.state["ranges"][key] = digest(content)
                row["complete"] = True
                return content
            finally:
                save(self.journal, self.state)
        raise AssertionError("Unreachable")


def index(archive):
    groups = {s: [] for s in SITES}
    for split, sites in SITES.items():
        for site in sites:
            for kind in ("image", "label"):
                for year in (2023, 2024):
                    name = f"EuroMineNet/{site}/{kind}/Year{year}.tif"
                    item = archive.getinfo(name)
                    groups[split].append(dict(name=name, site=site, kind=kind, year=year,
                                              header_offset=item.header_offset, compressed=item.compress_size,
                                              bytes=item.file_size, crc32=f"{item.CRC:08x}"))
        if sum(item["compressed"] for item in groups[split]) != COSTS[split]:
            raise ValueError("Archive compressed sizes disagree with preregistration")
    return groups


def acquire(root):
    root.mkdir(parents=True, exist_ok=True)
    with Archive(root) as source, ZipFile(source) as archive:
        groups = index(archive)
        roster = root / "frozen_members.json"
        plan = dict(url=URL, length=LENGTH, cap=CAP, test_reserve=TEST_RESERVE, members=groups)
        if roster.exists() and json.loads(roster.read_bytes()) != plan:
            raise ValueError("Frozen directory metadata changed")
        if not roster.exists():
            save(roster, plan)
        # A header may include the local ZIP64 extra field. Bound each member by
        # the next entry's offset, including entries outside our frozen roster.
        offsets = sorted({i.header_offset for i in archive.infolist()} | {archive.start_dir})
        next_offset = dict(zip(offsets, offsets[1:]))
        for split in ("train", "val"):
            for item in groups[split]:
                path = root / item["name"]
                receipt = path.with_suffix(".json")
                if receipt.exists():
                    original = json.loads(receipt.read_bytes())
                    if (any(original[k] != v for k, v in item.items())
                            or original["sha256"] != digest(path.read_bytes())):
                        raise ValueError("Extracted member hash disagrees with receipt")
                    continue
                start = item["header_offset"]
                source.enabled = (start, next_offset[start])
                payload = archive.read(item["name"])  # zipfile verifies member CRC.
                if len(payload) != item["bytes"]:
                    raise ValueError("Member length differs from directory")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(payload)
                save(receipt, dict(item, sha256=digest(payload)))
                print(split, item["name"], flush=True)


def windows(site, shape):
    rows, cols = shape
    candidates = [(r, c) for r in range(0, rows-127, 128) for c in range(0, cols-127, 128)]
    return sorted(candidates, key=lambda rc: digest(f"42:{site}:{rc[0]}:{rc[1]}".encode()))[:16]


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output", type=Path)
    args = cli.parse_args()
    acquire(args.output)


if __name__ == "__main__":
    main()
