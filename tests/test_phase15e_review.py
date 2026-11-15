import pytest
from shapely.geometry import box, mapping, shape

from scripts.phase15e_review import windows


def test_only_neutral_search_window_reaches_reviewers():
    candidate = dict(id="internal-hash", geometry=mapping(box(82.59, 22.32, 82.591, 22.321)),
                     properties=dict(region_id="gevra", status="REVIEW_REQUIRED", evidence_status="UNKNOWN",
                                     data_kind="exploratory", eligible_observation_count=0, mean_score=.8))
    public, crosswalk = windows([candidate])
    assert crosswalk == {"G01": "internal-hash"}
    [window] = public["features"]
    assert window["properties"] == {"review_id": "G01"}
    assert shape(window["geometry"]).contains(shape(candidate["geometry"]))
    candidate["properties"]["eligible_observation_count"] = 1
    with pytest.raises(ValueError, match="review-only"):
        windows([candidate])
