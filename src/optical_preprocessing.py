"""Fail-closed cloud join, SCL shadows, edge masks and seasonal index medians."""
import ee


def collections(region, season, cfg):
    sr = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(region)
          .filterDate(season.start, season.end)
          .filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE', cfg.scene_cloud_percent)))
    clouds = (ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY')
              .filterBounds(region).filterDate(season.start, season.end))
    joined = ee.ImageCollection(ee.Join.saveFirst('clouds').apply(
        primary=sr, secondary=clouds,
        condition=ee.Filter.equals(leftField='system:index', rightField='system:index')))
    return sr, joined.filter(ee.Filter.notNull(['clouds']))


def prepare(img, cfg):
    probability = ee.Image(img.get('clouds')).select('probability')
    scl = img.select('SCL')
    valid = probability.lt(cfg.cloud_probability)
    # 0 no data, 1 saturated, 2 dark/topographic shadow, 3 cloud shadow,
    # 7 unclassified, 8/9 cloud, 10 cirrus, 11 snow. Retain 4/5/6 only.
    valid = valid.And(scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6)))
    valid = (valid.And(img.select('B8A').mask()).And(img.select('B9').mask())
             .And(img.select(['B3', 'B4', 'B8']).mask().reduce(ee.Reducer.min())))
    reflectance = img.select(['B3', 'B4', 'B8']).divide(10000).updateMask(valid)

    def ratio(a, b, name):
        x, y = reflectance.select(a), reflectance.select(b)
        denominator = x.add(y)
        # Explicit expression avoids normalizedDifference's negative-input mask.
        return x.subtract(y).divide(denominator).updateMask(denominator.neq(0)).rename(name)

    indices = ratio('B8', 'B4', 'NDVI').addBands(ratio('B4', 'B3', 'NDTI'))
    joint_mask = indices.mask().reduce(ee.Reducer.min())
    return indices.updateMask(joint_mask).copyProperties(img, ['system:time_start'])


def seasonal(joined, region, cfg):
    indices = joined.map(lambda img: prepare(img, cfg))
    count = indices.select('NDVI').count().unmask(0).rename('optical_count').clip(region)
    return (indices.median().updateMask(count.gte(cfg.min_observations)).clip(region), count)
