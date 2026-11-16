import io
from collections import Counter
from zipfile import ZipFile

import numpy as np
import pytest

from scripts import eurominenet_acquire as acquire
from scripts.eurominenet_validate import support


class Response:
    url = acquire.URL

    def __init__(self, status, headers, data):
        self.status_code = status
        self.headers = headers
        self.raw = io.BytesIO(data)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def test_exact_range_and_resumable_hash(tmp_path):
    calls = []

    def request(url, **kwargs):
        calls.append(kwargs["headers"]["Range"])
        return Response(206, {"Content-Range": f"bytes 0-3/{acquire.LENGTH}"}, b"test")

    with acquire.Archive(tmp_path, request) as source:
        assert source.fetch(0, 4) == b"test"
    with acquire.Archive(tmp_path, request) as resumed:
        assert resumed.fetch(0, 4) == b"test"
        (tmp_path / "ranges/0-3").write_bytes(b"bad!")
        with pytest.raises(ValueError, match="hash mismatch"):
            resumed.fetch(0, 4)
    assert calls == ["bytes=0-3"]


def test_ignored_range_and_budget_fail_closed(tmp_path, monkeypatch):
    response = Response(200, {}, b"unapproved")
    with acquire.Archive(tmp_path, lambda *args, **kwargs: response) as source:
        with pytest.raises(ValueError, match="exact pinned range"):
            source.fetch(0, 4)
        assert response.raw.tell() == 0
        monkeypatch.setattr(acquire, "CAP", acquire.PRIOR + acquire.TEST_RESERVE)
        with pytest.raises(ValueError, match="TEST bytes reserved"):
            source.fetch(8, 12)


def test_zip_directory_does_not_extract_members(monkeypatch):
    packet = io.BytesIO()
    roster = {"train": ("X_1",), "val": ("Y_1",), "test": ("Z_1",)}
    with ZipFile(packet, "w") as buffer:
        for sites in roster.values():
            for kind in ("image", "label"):
                for year in (2023, 2024):
                    buffer.writestr(f"EuroMineNet/{sites[0]}/{kind}/Year{year}.tif", b"sample")
    monkeypatch.setattr(acquire, "SITES", roster)
    monkeypatch.setattr(acquire, "COSTS", dict.fromkeys(roster, 24))
    packet.seek(0)
    with ZipFile(packet) as buffer:
        monkeypatch.setattr(buffer, "read", lambda *args: pytest.fail("Member opened"))
        members = acquire.index(buffer)
    assert Counter(r["site"] for r in members["test"]) == {"Z_1": 4}
    assert all(r["header_offset"] > 0 for r in members["test"])


def test_windows_and_transition_support():
    origins = acquire.windows("fixture", (500, 400))
    assert len(origins) == 9 and origins == acquire.windows("fixture", (500, 400))
    assert all(r % 128 == c % 128 == 0 for r,c in origins)
    good = np.ones((128,128), bool)
    before, after = np.zeros_like(good), np.zeros_like(good)
    before[0, 0] = True
    after[0, 1:3] = True
    good[0, 2] = False
    assert support([(0,0)], good, [before,after])[0] == {
        "row": 0, "col": 0, "signal_cells": 16383, "expansion": 1, "contraction": 1, "unchanged": 16381,
    }
