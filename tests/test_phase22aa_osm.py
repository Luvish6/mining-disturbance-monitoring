from shapely.geometry import LineString, box

from scripts.phase22aa_osm import censored_distance, envelope_wgs84, query


def test_censored_distance_caps_and_handles_empty():
    cell = box(0, 0, 30, 30)
    assert censored_distance(cell, [LineString([(90, 0), (90, 30)])]) == 60
    assert censored_distance(cell, [LineString([(5000, 0), (5000, 1)])]) == 500
    assert censored_distance(cell, []) == 500


def test_query_and_envelope_are_bounded():
    s, w, n, e = envelope_wgs84([441540, 2791540, 443460, 2793460])
    assert s < n and w < e and 25.0 < s < 25.4 and 92.3 < w < 92.5
    q = query([(s, w, n, e)])
    assert q.count('way["highway"]') == 1 and q.count('way["building"]') == 1 and "out geom" in q
