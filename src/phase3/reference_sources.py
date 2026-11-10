"""Download and subset historical public mining references; never training labels."""
import hashlib
import json
from pathlib import Path
import sqlite3
import requests
from shapely import from_wkb
from shapely.geometry import mapping, shape

DOI='https://doi.org/10.1594/PANGAEA.942325'
BASE='https://download.pangaea.de/dataset/942325/files/'
FILES=('global_mining_polygons_v2.gpkg','validation_points_v2.gpkg')


def gpkg_geometry(blob):
    if blob[:2]!=b'GP':
        raise ValueError('Expected GeoPackage geometry header')
    envelope=(blob[3]>>1)&7
    sizes={0:0,1:32,2:48,3:48,4:64}
    if envelope not in sizes:
        raise ValueError('Unsupported GeoPackage envelope')
    return from_wkb(blob[8+sizes[envelope]:])


def subset(gpkg, boundary, output):
    """Retain original geometries intersecting planning AOI; no label assignment."""
    output=Path(output)
    if output.exists(): raise ValueError('Output already exists')
    document=json.loads(Path(boundary).read_text(encoding='utf-8-sig'))
    region=shape(document['geometry'] if document['type']=='Feature' else document)
    if not region.is_valid or region.is_empty: raise ValueError('Invalid planning boundary')
    conn=sqlite3.connect(Path(gpkg).resolve().as_uri()+'?mode=ro',uri=True)
    features=[]
    try:
        table,column,srs=conn.execute('SELECT table_name,column_name,srs_id FROM gpkg_geometry_columns').fetchone()
        if srs!=4326: raise ValueError('Reference inventory must use EPSG:4326')
        quote=lambda x:'"'+x.replace('"','""')+'"'
        cursor=conn.execute('SELECT * FROM '+quote(table))
        names=[d[0] for d in cursor.description]
        for values in cursor:
            row=dict(zip(names,values)); blob=row.pop(column)
            if blob is None: continue
            geometry=gpkg_geometry(blob)
            if geometry.is_empty or not geometry.intersects(region): continue
            features.append(dict(type='Feature',geometry=mapping(geometry),properties=dict(
                reference_role='historical_candidate_not_training_label',source_doi=DOI,
                source_file=Path(gpkg).name,imagery_reference_year=2019,
                temporal_match_2023_2025=False,spatial_accuracy_m=None,
                accuracy_note='10 m source mosaic pixel size is not a measured positional error',
                license='CC-BY-SA-4.0',source_attributes=row,
                boundary_selection='Intersection with 100 m simplified district planning outline')))
    finally: conn.close()
    with output.open('x',encoding='utf-8') as stream:
        json.dump(dict(type='FeatureCollection',features=features),stream,indent=2,allow_nan=False)
    return len(features)


def discover(boundary, output):
    output=Path(output); output.mkdir(parents=True,exist_ok=False)
    raw=output/'raw'; raw.mkdir()
    inventory=[]
    for name in FILES:
        dest=raw/name; h=hashlib.sha256(); size=0
        with requests.get(BASE+name,stream=True,timeout=(15,60)) as response:
            response.raise_for_status()
            with dest.open('xb') as stream:
                for chunk in response.iter_content(1024*1024):
                    size+=len(chunk)
                    if size>32*1024*1024: raise ValueError('Reference download exceeds 32 MiB cap')
                    h.update(chunk); stream.write(chunk)
        count=subset(dest,boundary,output/(Path(name).stem+'_local_candidates.geojson'))
        inventory.append(dict(file=name,bytes=size,sha256=h.hexdigest(),url=BASE+name,
                              local_candidate_count=count,accepted_training_samples=0))
    report=dict(source=DOI,citation='Maus et al. (2022), Global-scale mining polygons (Version 2), PANGAEA.942325',
                license='CC-BY-SA-4.0',reference_year=2019,files=inventory,
                positive_training_samples=0,negative_training_samples=0,
                limitation='Historical mine/no-mine validation is not 2023–2025 disturbance validation')
    with (output/'discovery.json').open('x',encoding='utf-8') as stream: json.dump(report,stream,indent=2)
    return report


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('boundary'); p.add_argument('output')
    a=p.parse_args(); print(json.dumps(discover(a.boundary,a.output),indent=2))
