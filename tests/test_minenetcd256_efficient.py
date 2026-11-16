import json

import pytest

from scripts import minenetcd256_efficient as efficient
from scripts import minenetcd256_planner as base


def test_diverse_plan_all_shards_and_cap():
    roster = {"train": {}, "val": {}}
    calls = []

    def scan(shard, budget):
        calls.append(shard)
        split = "train" if shard in base.SOURCES["train"] else "val"
        index = base.SOURCES[split].index(shard)
        chunk = {"domain": [(0, 10)], "imageA": [(10, 30)],
                 "imageB": [(30, 50)], "label": [(50, 60)]}
        names = list(roster[split])[index::len(base.SOURCES[split])]
        return [[site] * 16 for site in names], [chunk] * len(names), {
            "metadata_bytes": 5, "acquisition_header_footer_bytes": 6,
        }

    roster["train"] = {f"Region{i % 8}_{i}": 16 for i in range(24)}
    roster["val"] = {f"Other_{i}": 16 for i in range(10)}
    result = efficient.plans(roster, scan, cap=1900)
    assert calls == [*base.SOURCES["train"], *base.SOURCES["val"]]
    assert efficient.plans(roster, scan, cap=1900) == result
    for manifest in result.values():
        assert manifest["targets"] == {"train": 20, "val": 10}
        assert manifest["total_bytes"] == 1844
        train = {r["site"] for r in manifest["patches"]["train"]}
        assert len({site.split("_")[0] for site in train}) == 8
        assert train.isdisjoint(r["site"] for r in manifest["patches"]["val"])
    reduced = efficient.plans(roster, scan, cap=1784)
    assert reduced["primary"]["targets"] == {"train": 19, "val": 10}
    roster["val"][next(iter(roster["train"]))] = 16
    with pytest.raises(ValueError, match="overlap"):
        efficient.plans(roster, scan, cap=1900)


def test_resume_verifies_cached_ranges_without_recharging(tmp_path, monkeypatch):
    requests = []

    def remote(self, start, end):
        requests.append((start, end))
        return b"PAR1", 100

    monkeypatch.setattr(base.GuardedSource, "_range", remote)
    manifest = {"sha256": "selection", "metadata_bytes": 10}
    url = "https://example.invalid/pinned/train"
    first = efficient.RangeJournal(tmp_path, manifest)
    with first.source(url, 100):
        pass
    resumed = efficient.RangeJournal(tmp_path, manifest)
    with resumed.source(url, 100):
        pass
    assert requests == [(0, 3)]
    assert json.loads(resumed.path.read_bytes())["charged"] == 4
    next(tmp_path.glob("*.range")).write_bytes(b"BROK")
    with pytest.raises(ValueError, match="Corrupt"):
        resumed.source(url, 100)
    assert requests == [(0, 3)]


def test_journal_checks_cap_before_request(tmp_path, monkeypatch):
    monkeypatch.setattr(base.GuardedSource, "_range", lambda *args: pytest.fail("network read"))
    journal = efficient.RangeJournal(tmp_path, {"sha256": "selection", "metadata_bytes": base.CAP - 3})
    with pytest.raises(ValueError, match="cap exhausted"):
        journal.source("https://example.invalid/pinned/train", 100)
