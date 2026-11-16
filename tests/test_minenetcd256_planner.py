from collections import Counter

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from scripts import minenetcd256_planner as planner


def fixture():
    sites = {"train": [f"Region{i % 4}_{i:02}" for i in range(20)],
             "val": [f"Other_{i:02}" for i in range(10)]}
    shards = {}
    for split, names in sites.items():
        for idx, shard in enumerate(planner.SOURCES[split]):
            subset = names[idx::len(planner.SOURCES[split])]
            shards[shard] = [[site] for site in subset for _ in range(16)]

    calls = []

    def scan(shard, budget):
        calls.append(shard)
        groups = shards[shard]
        ranges = [{key: [(0, 4)] for key in (*planner.ASSETS, "domain")} for _ in groups]
        return groups, ranges, dict(metadata_bytes=5, acquisition_header_footer_bytes=6)

    roster = {key: dict.fromkeys(values, 16) for key, values in sites.items()}
    return roster, scan, calls


def test_all_shards_and_deterministic_selection():
    roster, scan, calls = fixture()
    plans, decision = planner.build(roster, scan)
    assert calls == [*planner.SOURCES["train"], *planner.SOURCES["val"]]
    assert decision == "primary"
    reordered = {split: dict(reversed(list(sites.items()))) for split, sites in roster.items()}
    assert planner.build(reordered, scan)[0] == plans
    for key, counts in (("primary", (12, 8)), ("fallback", (6, 4))):
        for (split, rows), count in zip(plans[key]["patches"].items(), counts, strict=True):
            assert Counter(r["site"] for r in rows) == dict.fromkeys(roster[split], count)
            assert len({r["patch_id"] for r in rows}) == len(rows)
    rows = plans["primary"]["patches"]["train"][:12]
    assert [r["group"] % 16 + r["row"] for r in rows] == [i * 15 // 11 for i in range(12)]


def test_cap_and_manifest_integrity():
    roster, scan, _ = fixture()
    plans, _ = planner.build(roster, scan)
    fallback = plans["fallback"]["total_bytes"]
    fallback_plans, decision = planner.build(roster, scan, fallback)
    assert decision == "fallback"
    planner.verify(fallback_plans["fallback"])
    with pytest.raises(ValueError, match="over-cap"):
        planner.verify(fallback_plans["primary"])
    assert planner.build(roster, scan, fallback - 1)[1] == "blocked"
    fallback_plans["fallback"]["patches"]["train"][0]["row"] += 1
    with pytest.raises(ValueError, match="altered"):
        planner.verify(fallback_plans["fallback"])


def test_roster_split_mismatch():
    roster, scan, _ = fixture()
    roster["val"][next(iter(roster["train"]))] = roster["val"].pop(next(iter(roster["val"])))
    with pytest.raises(ValueError, match="official roster"):
        planner.build(roster, scan)


def test_metadata_only_ranges():
    blob = pa.BufferOutputStream()
    image = [{"bytes": b"do not fetch", "path": "asset.png"}] * 4
    pq.write_table(pa.table(dict(imageA=image, imageB=image, label=image,
                                 domain=["A_01", "A_01", "B_01", "B_01"])), blob, row_group_size=2)
    payload = blob.getvalue().to_pybytes()
    requested = []

    class MemorySource(planner.GuardedSource):
        def _range(self, start, end):
            requested.append((start, end + 1))
            self.budget -= end - start + 1
            return payload[start:end + 1], len(payload)

    groups, chunks, receipt = planner.scan("unused", 100_000, MemorySource)
    assert groups == [["A_01", "A_01"], ["B_01", "B_01"]]
    assert receipt["metadata_bytes"] == sum(b - a for a, b in requested)
    assert requested[3:] == [group["domain"][0] for group in chunks]
    for start, end in requested:
        assert not any(start < b and end > a for group in chunks
                       for name in planner.ASSETS for a, b in group[name])
    with MemorySource("unused") as source:
        metadata, _, _ = planner.footer(source)
        parquet = pq.ParquetFile(source, metadata=metadata, pre_buffer=False)
        for idx, group in enumerate(chunks):
            source.allowed = [r for ranges in group.values() for r in ranges]
            first = len(requested)
            parquet.read_row_group(idx, use_threads=False)
            assert sorted(requested[first:]) == sorted(source.allowed)
