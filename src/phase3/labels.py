"""Strict reference polygon import. Unlabeled space is unknown, never class 0."""
import json
from datetime import date
from pathlib import Path
from shapely.geometry import shape


def load_labels(source, max_features=5000):
    """GeoJSON path/dict or explicitly bounded Earth Engine FeatureCollection."""
    if isinstance(source, (str, Path)):
        source = json.loads(Path(source).read_text(encoding='utf-8-sig'))
    elif not isinstance(source, dict):
        n = source.size().getInfo()
        if not 0 < n <= max_features:
            raise ValueError('EE label import exceeds explicit bounded feature limit')
        source = source.getInfo()
    if source.get('type') != 'FeatureCollection' or source.get('crs'):
        raise ValueError('Use RFC 7946 WGS84 GeoJSON without a legacy CRS member')
    features = source.get('features', [])
    if not 0 < len(features) <= max_features:
        raise ValueError('No labels or too many label features')
    seen, result = set(), []
    for f in features:
        p = f.get('properties', {})
        for key in ('label_id', 'source', 'provenance', 'interpretation_date', 'reviewer'):
            if not isinstance(p.get(key), str) or not p[key].strip():
                raise ValueError(f'Missing reference metadata: {key}')
        date.fromisoformat(p['interpretation_date'])
        if p['label_id'] in seen:
            raise ValueError('Duplicate label_id')
        seen.add(p['label_id'])
        if type(p.get('label')) is not int or p['label'] not in (0, 1):
            raise ValueError('Reference label must be integer 0 or 1')
        if p.get('confidence') not in ('high', 'medium') or p.get('reviewed') is not True:
            raise ValueError('Only reviewed high/medium confidence polygons may enter datasets')
        g = shape(f['geometry'])
        if g.geom_type not in ('Polygon', 'MultiPolygon') or g.is_empty or not g.is_valid:
            raise ValueError('Valid Polygon/MultiPolygon required')
        x0, y0, x1, y1 = g.bounds
        if not (-180 <= x0 <= x1 <= 180 and -90 <= y0 <= y1 <= 90):
            raise ValueError('GeoJSON coordinates must be WGS84 longitude/latitude')
        for other, _ in result:
            if g.intersection(other).area > 0:
                raise ValueError('Overlapping reference polygons are ambiguous')
        result.append((g, dict(p)))
    return result


def save_ee_labels(collection, output, max_features=5000):
    """Explicit bounded import after caller initializes Earth Engine."""
    if Path(output).exists():
        raise ValueError('Refusing to replace an existing label file')
    n = collection.size().getInfo()
    if not 0 < n <= max_features:
        raise ValueError('EE label import exceeds explicit bounded feature limit')
    data = collection.getInfo()
    load_labels(data, max_features)
    Path(output).write_text(json.dumps(data, indent=2, allow_nan=False), encoding='utf-8')
