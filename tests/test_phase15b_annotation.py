import sqlite3

from shapely.geometry import box, mapping

from scripts.phase15b_annotation import LAYERS, preflight, schema
from src.phase3.annotation import sha
from src.phase3.admission import TARGET


def test_templates_are_empty_typed_wgs84_layers(tmp_path):
    path = tmp_path/"draft.gpkg"
    schema(path)
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA application_id").fetchone()[0] == 0x47504B47
        assert set(db.execute("SELECT table_name,geometry_type_name,srs_id FROM gpkg_geometry_columns")) == {
            (name, "POLYGON", 4326) for name in LAYERS}
        for name in LAYERS:
            assert db.execute(f"SELECT count(*) FROM {name}").fetchone()[0] == 0


def test_checker_rejects_circular_evidence_inadequate_rights_and_no_regional_design():
    footprint = mapping(box(85, 20, 86, 21))
    fields = dict(crs="EPSG:4326", valid_footprint=footprint, coverage_verified=True,
                  reuse_permitted=True, rights_reference="fixture", independence_verified=True)
    document = dict(geometry=mapping(box(85.1, 20.1, 85.2, 20.2)), crs="EPSG:4326",
                    decision=LAYERS[0], before=dict(fields, id="cached-model-input", date="2024-03-01"),
                    after=dict(fields, id="independent", date="2025-03-01", reuse_permitted=False),
                    reference_properties=dict(synthetic=False, independent_reference=True, target_definition=TARGET,
                        spatial_accuracy_m=20, evidence_urls=["https://example.org/evidence"],
                        positional_evidence_reference="fixture", evidence_group_id="fixture"))
    packet_hash = sha({key: document[key] for key in ("geometry", "before", "after", "decision", "reference_properties")})
    document["reviews"] = [dict(reviewer=reviewer, attests_independent=True,
                                decision=LAYERS[0], packet_sha256=packet_hash) for reviewer in ("one", "two")]
    result = preflight(document, {"cached-model-input"})
    assert result["status"] == "UNKNOWN"
    assert any("shared model-input" in issue for issue in result["issues"])
    assert any("rights" in issue for issue in result["issues"])
    assert any("spatial-block" in issue for issue in result["issues"])
    assert not any("reviewers" in issue for issue in result["issues"])
    document["reviews"][1]["packet_sha256"] = "different"
    assert any("reviewers" in issue for issue in preflight(document, set())["issues"])
