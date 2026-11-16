import csv

import pytest

from scripts.phase13_data import candidates, comparison


def table(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_candidates_require_unknown(tmp_path):
    row = dict(id="example", state="Odisha", district="Angul", longitude=85, latitude=21,
               status="UNKNOWN", common=25, median_delta="{'dVV': -1.0}", source="example")
    path = tmp_path / "candidate.csv"
    assert candidates(table(path, [row]))[0]["changes"] == {"dVV": -1.0}
    with pytest.raises(ValueError, match="UNKNOWN"):
        candidates(table(path, [dict(row, status="confirmed")]))


def test_comparison_rejects_under_supported_dated_results(tmp_path):
    row = dict(row_type="summary", status="DESCRIPTIVE ONLY", upstream_cells=24,
               downstream_cells=75, matched_months=2, matched_pairs=0)
    path = tmp_path / "comparison.csv"
    with pytest.raises(ValueError, match="coverage gate"):
        comparison(table(path, [row]))
    assert comparison(table(path, [dict(row, status="INSUFFICIENT DATA")]))["dates"] == []


def test_comparison_checks_matched_dates_and_provenance(tmp_path):
    path = tmp_path / "river.csv"
    summary = dict(row_type="summary", status="DESCRIPTIVE ONLY", upstream_cells=25,
                   downstream_cells=75, matched_months=2, matched_pairs=2,
                   pair="", season="", date="", source_collections="S2",
                   rainfall_geometry="station cell", mine_connectivity="UNKNOWN")
    hashes = ("source_receipt_sha256", "station_table_sha256",
              "upstream_mask_sha256", "downstream_mask_sha256")
    summary.update(dict.fromkeys(hashes, "a" * 64))
    rows = [dict(row_type="date", status="DESCRIPTIVE ONLY", pair=i, season=s, date=stamp)
            for i, s, stamp in ((1, "before", "2023-11-01"), (1, "after", "2024-11-02"),
                                (2, "before", "2023-12-01"), (2, "after", "2024-12-02"))]
    assert len(comparison(table(path, [summary, *rows]))["dates"]) == 4
    with pytest.raises(ValueError, match="provenance"):
        comparison(table(path, [dict(summary, upstream_mask_sha256=""), *rows]))
    rows[-1]["date"] = "2024-11-03"
    with pytest.raises(ValueError, match="mismatched date pairs"):
        comparison(table(path, [summary, *rows]))


def test_rejected_snapshot_is_removed(tmp_path, monkeypatch):
    from scripts import phase13_data

    monkeypatch.chdir(tmp_path)
    local = tmp_path / "frontend/public/local"
    local.mkdir(parents=True)
    snapshot = local / "brahmani.json"
    snapshot.write_text("old")
    source = tmp_path / "outputs/phase12d_brahmani/comparison.csv"
    source.parent.mkdir(parents=True)
    table(source, [dict(row_type="summary", status="UNRECOGNIZED")])
    with pytest.raises(ValueError, match="Unexpected"):
        phase13_data.main()
    assert not snapshot.exists()
