"""Bounded seasonal context and manual polygon editor; never verifies labels."""
from dataclasses import asdict
from datetime import datetime,timezone
import html
import math
import json
from pathlib import Path
import folium
from folium.plugins import Draw,SideBySideLayers
from branca.element import MacroElement,Template,Element
from shapely.geometry import Point,shape,mapping,box
from pyproj import Transformer
from shapely import transform
from .annotation import latest,candidates,boundary_geometry,write_new,sha,read
from .spatial import partition


def core_features(boundary,region=None):
    forward=Transformer.from_crs(4326,32646,always_xy=True).transform
    inverse=Transformer.from_crs(32646,4326,always_xy=True).transform
    area=transform(shape(region) if region else boundary_geometry(boundary),forward,interleaved=False)
    x0,y0,x1,y1=area.bounds;features=[]
    for x in range(math.floor(x0/5000),math.floor(x1/5000)+1):
        for y in range(math.floor(y0/5000),math.floor(y1/5000)+1):
            core=box(x*5000+120,y*5000+120,(x+1)*5000-120,(y+1)*5000-120).intersection(area)
            if core.is_empty or core.area==0: continue
            identity=f'{x}:{y}'
            features.append(dict(type='Feature',geometry=mapping(transform(core,inverse,interleaved=False)),
                properties=dict(block=identity,partition=partition(identity,42))))
    return dict(type='FeatureCollection',features=features)


def bounded_region(boundary,point,radius_m):
    if point is None or len(point)!=2 or not 100<=radius_m<=500: raise ValueError('Choose an actual point and radius 100–500 m')
    lon,lat=point
    if not (-180<=lon<=180 and -90<=lat<=90): raise ValueError('Invalid WGS84 coordinates')
    p=Point(lon,lat);region=boundary_geometry(boundary)
    if not region.covers(p): raise ValueError('Review point is outside the original districts')
    forward=Transformer.from_crs(4326,32646,always_xy=True).transform
    inverse=Transformer.from_crs(32646,4326,always_xy=True).transform
    return mapping(transform(transform(p,forward,interleaved=False).buffer(radius_m).intersection(transform(region,forward,interleaved=False)),inverse,interleaved=False))


def rgb_context(img,cfg):
    import ee
    from src import optical_preprocessing as optical
    valid=ee.Image(optical.prepare(img,cfg)).mask().reduce(ee.Reducer.min())
    return img.select(['B4','B3','B2']).divide(10000).updateMask(valid)


def seasonal_layers(region):
    import ee
    from config.settings import BEFORE,AFTER
    from config.phase2_settings import Phase2Config
    from src import optical_preprocessing as optical
    from src.gee_setup import initialize
    initialize();ee.data.setDeadline(60000);cfg=Phase2Config(relative_orbit=77)
    ee_region=ee.Geometry(region);layers=[];records=[]
    for season in (BEFORE,AFTER):
        raw,joined=optical.collections(ee_region,season,cfg)
        dates=joined.aggregate_array('system:time_start').getInfo()
        if not dates or len(dates)>500: raise ValueError('No optical scenes or unbounded review collection')
        composite=joined.map(lambda img:rgb_context(img,cfg)).median()
        _,count=optical.seasonal(joined,ee_region,cfg)
        composite=composite.updateMask(count.gte(cfg.min_observations)).clip(ee_region)
        layer=composite.getMapId({'min':0,'max':.3,'bands':['B4','B3','B2']})['tile_fetcher'].url_format
        valid=count.gte(cfg.min_observations).rename('optical_valid')
        coverage=valid.unmask(0,sameFootprint=False).reduceRegion(ee.Reducer.mean(),ee_region,30,
            crs='EPSG:32646',maxPixels=10000,tileScale=2).getInfo()
        count_url=count.getMapId({'min':0,'max':50,'palette':['black','orange','green']})['tile_fetcher'].url_format
        layers.append((layer,count_url))
        records.append(dict(season=asdict(season),scene_count=len(dates),
            acquisition_dates_utc=sorted({datetime.fromtimestamp(t/1000,timezone.utc).date().isoformat() for t in dates}),
            optical_valid_fraction=coverage.get('optical_valid'),composite='seasonal median RGB',
            independent_reference=False,role='Sentinel-2 classifier-source context; not independent truth',
            license='Copernicus Sentinel data terms',cloud_probability=cfg.cloud_probability,
            min_observations=cfg.min_observations))
    return layers,records


PANEL='''<div style="position:fixed;right:10px;top:10px;width:365px;max-height:85vh;overflow:auto;z-index:1000;background:white;padding:14px;border:1px solid #aaa;font:13px Arial">
<b>Reference annotation — drafts only</b><p>Draw a polygon or click one to edit its evidence. Use the layer switcher or swipe control to compare seasonal context. Rendering does not verify a site.</p>
<input id="session-file" type="file" accept=".json,.geojson"><button id="save-drafts">Download drafts</button>
<p id="annotation-status">No polygon selected.</p><label>Candidate <select id="candidate-id"></select></label>
<p>Evidence metadata (JSON). Unknown fields stay null. No reviewer, date or positional error is inferred.</p>
<textarea id="evidence-properties" rows="23" style="width:100%;font:12px monospace"></textarea>
<button id="apply-metadata">Save selected polygon metadata</button><p>Review and acceptance happen through the project commands. Importing edited drafts invalidates earlier reviews.</p>
<details open><summary>Candidate locations and source evidence — not labels</summary><div id="candidate-leads"></div></details>
<details><summary>Imagery acquisition and coverage record</summary><pre style="white-space:pre-wrap" id="imagery-record"></pre></details>
<p>Independent dated evidence: record actual URLs, dates, access/license and interpretation in the metadata. This map does not redistribute external high-resolution imagery.</p></div>'''


def review_map(root,output,point=None,radius_m=300,live=False):
    document,boundary=latest(root);output=Path(output)
    if output.exists(): raise ValueError('Choose a new imagery review directory')
    rows=candidates(root);region=bounded_region(boundary,point,radius_m) if point is not None else None
    if live and region is None: raise ValueError('Live imagery requires a bounded --point')
    layers,record=seasonal_layers(region) if live else ([],[])
    map_=folium.Map(location=[25.4,92.3],zoom_start=10,tiles=None)
    # No third-party basemap imagery is downloaded or silently added.
    folium.GeoJson(boundary,name='Original GAUL districts',style_function=lambda f:dict(color='#486581',fillOpacity=0,weight=1)).add_to(map_)
    cores=core_features(boundary,region)
    if cores['features']:
        folium.GeoJson(cores,name='5 km buffered cores, fixed seed 42',
            style_function=lambda f:dict(color={'train':'#1277a4','validation':'#bb8600','test':'#ab2673'}[f['properties']['partition']],fillOpacity=.03,weight=2),
            tooltip=folium.GeoJsonTooltip(fields=['block','partition'])).add_to(map_)
    geometries=[dict(type='Feature',geometry=r['geometry'],properties=dict(candidate_id=r['candidate_id'],
        site_name=r.get('site_name',r['candidate_id']),source_url=r['source_url'],
        geometry_role=r.get('geometry_role','Candidate geometry; not a reference label'))) for r in rows if r.get('geometry')]
    if geometries: folium.GeoJson(dict(type='FeatureCollection',features=geometries),name='Candidate source geometries — not disturbance labels',
        tooltip=folium.GeoJsonTooltip(fields=['site_name','candidate_id','source_url','geometry_role'])).add_to(map_)
    if region:
        folium.GeoJson(region,name='Bounded review area',style_function=lambda f:dict(color='orange',fillOpacity=0)).add_to(map_)
        west,south,east,north=shape(region).bounds;map_.fit_bounds([[south,west],[north,east]])
    else:
        west,south,east,north=boundary_geometry(boundary).bounds;map_.fit_bounds([[south,west],[north,east]])
    rgb=[]
    for i,(url,counts) in enumerate(layers):
        title=('Before 2023–24' if i==0 else 'After 2024–25')+' seasonal RGB — input context'
        tile=folium.TileLayer(url,attr='Copernicus Sentinel / Google Earth Engine',name=title,overlay=True,control=True)
        tile.add_to(map_);rgb.append(tile)
        folium.TileLayer(counts,attr='Copernicus Sentinel / Google Earth Engine',name=title+' valid observation count',overlay=True,show=False).add_to(map_)
    if len(rgb)==2: SideBySideLayers(rgb[0],rgb[1]).add_to(map_)
    group=folium.FeatureGroup(name='Editable draft polygons').add_to(map_)
    Draw(feature_group=group,show_geometry_on_click=False,draw_options=dict(polyline=False,circle=False,circlemarker=False,marker=False,rectangle=False,polygon={'allowIntersection':False}),edit_options={'edit':True,'remove':True}).add_to(map_)
    folium.LayerControl(position='bottomleft',collapsed=False).add_to(map_)
    map_.get_root().html.add_child(Element(PANEL))
    script=(Path(__file__).with_name('annotation_editor.js')).read_text(encoding='utf-8')
    safe=lambda value:json.dumps(value,allow_nan=False).replace('</','<\\/')
    script=script.replace('__MAP__',map_.get_name()).replace('__GROUP__',group.get_name())
    script=script.replace('__CANDIDATES__',safe(rows)).replace('__FEATURES__',safe(document['features'])).replace('__IMAGERY__',safe(record))
    macro=MacroElement();macro.code=script;macro._template=Template('{% macro script(this, kwargs) %}{{ this.code }}{% endmacro %}');macro.add_to(map_)
    output.mkdir(parents=True);map_.save(str(output/'review.html'))
    write_new(output/'imagery_record.json',dict(live=live,region=region,seasons=record,
        note='Seasonal composites are not single-date or independent observations. Tiles expire; regenerate into a new directory.',
        independent_imagery_available=False,annotation_verification=False))
    return output/'review.html'


def paired_export_plan(root,coverage,output,point,radius_m=300):
    """Prepare and validate an unsubmitted EE task; no start() is called."""
    import ee
    from config.phase2_settings import Phase2Config
    from config.settings import BEFORE,AFTER
    from src.gee_setup import initialize
    from .ee_inputs import export_task,paired_graph
    from .data import BANDS,digest
    _,boundary=latest(root);geometry=bounded_region(boundary,point,radius_m);report=read(coverage)
    cfg=Phase2Config(**report['config']);orbit=report['metadata']['selected_relative_orbit']
    from dataclasses import replace
    cfg=replace(cfg,relative_orbit=orbit)
    if report.get('seasons')!=[asdict(BEFORE),asdict(AFTER)]: raise ValueError('Coverage seasons differ from project')
    initialize();task=export_task(ee.Geometry(geometry),cfg,report,'phase3a_small_paired_tile')
    output=Path(output)
    if output.exists(): raise ValueError('Choose a new export plan directory')
    output.mkdir(parents=True)
    plan=dict(status='prepared_not_submitted',region=geometry,project='maj-project-513220',
        crs='EPSG:32646',crs_transform=[30,0,0,0,-30,0],band_order=list(BANDS),nodata=-9999,
        seasons=[[BEFORE.start,BEFORE.end],[AFTER.start,AFTER.end]],config=asdict(cfg),
        relative_orbit=orbit,orbit_pass=cfg.orbit_pass,coverage_report_sha256=digest(coverage),
        data_kind='real',source='Existing Sentinel-1/Sentinel-2/SRTM paired graph',
        export_id=None,raster_sha256=None,operator=None,retrieved_date=None,
        note='Export ID, completion and file hash must come from actual subsequent execution. No imagery export was started.')
    write_new(output/'export_plan.json',plan)
    (output/'paired_graph.json').write_text(paired_graph(ee.Geometry(geometry),cfg).serialize(),encoding='utf-8')
    return output/'export_plan.json'
