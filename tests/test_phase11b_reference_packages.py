from shapely.geometry import shape
import pytest

from scripts.phase11b_reference_packages import FORM, candidate


def test_training_search_polygon_is_not_a_reference():
    point = [92.2211387789683, 25.69239909504793]
    packet = candidate(point, "84:568", "train")
    assert packet["status"] == "UNKNOWN"
    assert packet["geometry_kind"] == "300 m imagery search area"
    assert shape(packet["geometry"]).is_valid
    assert packet["windows"][0]["start"] == "2023-11-01"
    with pytest.raises(ValueError, match="frozen"):
        candidate(point, "84:568", "test")


def test_worksheet_requires_independent_review_slots():
    assert "First reviewer" in FORM and "Independent second reviewer" in FORM
    assert FORM.count("Decision (pending") == 2
