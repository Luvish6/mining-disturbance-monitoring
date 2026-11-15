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
