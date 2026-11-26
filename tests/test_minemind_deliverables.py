import copy,csv,io,json
from pathlib import Path
import pytest
from scripts.minemind_deliverables import collect,build,RUNS,sha
from scripts.phase25_minemind_portal import snapshot_sources,RUN


def test_saved_export_preserves_cohorts_and_undefined_values(tmp_path):
    metric=dict(spearman=.5,top5_jaccard=.25,candidate_jaccard=None,polygons=[0,0],candidate_area_m2=[0,0],same_season_exceedance=[0,.1])
    for cohort,path in RUNS.items():
        folder=tmp_path/path;folder.mkdir(parents=True)
        site=dict(eligible_cells=10,methods={'phase15c':dict(metrics=metric,threshold=.4)})
        data={'holdouts' if cohort=='geographic_development_holdouts' else 'sites':{'synthetic':site}}
        (folder/'metrics.json').write_text(json.dumps(data));(folder/'integrity.json').write_text(json.dumps({'metrics.json':sha(folder/'metrics.json')}))
    rows,sources=collect(tmp_path)
    assert len(rows)==3 and len(sources)==3 and all(r['candidate_jaccard'] is None for r in rows)
    assert rows[0]['cutoff_basis']=='fixed Phase15C 2.5/6'
    (tmp_path/next(iter(RUNS.values()))/'metrics.json').write_text('{}')
    with pytest.raises(ValueError):collect(tmp_path)


def test_output_bundle_never_overwrites_existing(tmp_path):
    with pytest.raises(ValueError):build(tmp_path,tmp_path)


@pytest.fixture
def source_fixture(tmp_path,monkeypatch):
    import scripts.phase25_minemind_portal as module
    def put(path,raw):
        p=tmp_path/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);return sha(p)
    metrics_sha=put(RUN/'metrics.json',b'synthetic metrics')
    cache_sha=put(Path('outputs/indian_ssl_observation_cache/verified_cache.json'),b'synthetic receipt')
    river=dict(summary={'matched_pairs':16});river_sha=put(Path('outputs/phase12d_brahmani/comparison.csv'),b'synthetic river')
    put(Path('frontend/public/local/river.json'),json.dumps(dict(pilot=dict(common_pixels=12,reportable=False))).encode())
    monkeypatch.setattr(module,'brahmani_snapshot',lambda _:river)
    d=dict(source_metrics_sha256=metrics_sha,cache_sha256=cache_sha,sites={},river=river,river_sha256=river_sha,leshka=dict(common_cells=12,minimum_cells=25,status='INSUFFICIENT_DATA'))
    files={'minemind/river.csv':('text/csv',b'synthetic river')}
    for site,parent in [('gevra','indian_ssl_observation_cache'),('bhubaneswari','indian_ssl_bhubaneswari_retry')]:
        folder=Path('outputs')/parent/f'{site}-r1';hashes={n:put(folder/n,('synthetic '+site+n).encode()) for n in ['features.tif','diagnostics.tif']}
        scenes=[dict(s1=['synthetic_before']),dict(s1=['synthetic_after'])];put(folder/'receipt.json',json.dumps(dict(hashes=hashes,scenes=scenes)).encode())
        stem=f'minemind/{site}/ssl_both/r1';assets={k:stem+'_'+k+'.png' for k in ['before','after','score','candidates']}
        for path in assets.values():files[path]=('image/png',b'synthetic not rendered')
        r=dict(id=1,geojson=stem+'.geojson',assets=assets,candidates=[],source_sha256=put(RUN/site/'ssl_both/r1.tif',b'synthetic scores'))
        g=dict(features=[],provenance=dict(model_validation='NOT_VALIDATED',operational_alerts=0,method='ssl_both',threshold=.5,frozen_experiment_sha256=metrics_sha,bounds=[0,0,30,30],crs='EPSG:32646',source_hashes=hashes,scene_groups=scenes))
        files[r['geojson']]=('application/geo+json',json.dumps(g).encode());d['sites'][site]=dict(bounds=[0,0,30,30],crs='EPSG:32646',methods=dict(ssl_both=dict(threshold=.5,replicas=[r])))
    return tmp_path,d,files


def test_verified_sources_match_snapshot_without_raster_decoding(source_fixture):snapshot_sources(*source_fixture)


@pytest.mark.parametrize('change',['pixels','scores','missing','dates','swap','export','river','validated'])
def test_stale_sources_and_swapped_or_divergent_exports_fail_closed(source_fixture,change):
    root,d,files=source_fixture;r=d['sites']['gevra']['methods']['ssl_both']['replicas'][0]
    folder=root/'outputs/indian_ssl_observation_cache/gevra-r1'
    if change=='pixels':
        path=folder/'features.tif';payload=path.read_bytes();path.write_bytes(payload[:-1]+bytes([payload[-1]^1]))
    elif change=='scores':(root/RUN/'gevra/ssl_both/r1.tif').write_bytes(b'altered scores')
    elif change=='missing':(folder/'diagnostics.tif').unlink()
    elif change=='dates':
        receipt=json.loads((folder/'receipt.json').read_bytes());receipt['scenes'].reverse();(folder/'receipt.json').write_text(json.dumps(receipt))
    elif change=='swap':r['assets']['before']=r['assets']['after']
    elif change=='export':
        geo=json.loads(files[r['geojson']][1]);geo['features']=[{'synthetic':'different'}];files[r['geojson']]=('application/geo+json',json.dumps(geo).encode())
    elif change=='river':(root/'outputs/phase12d_brahmani/comparison.csv').write_bytes(b'changed river')
    elif change=='validated':
        geo=json.loads(files[r['geojson']][1]);geo['provenance']['model_validation']='VALIDATED';files[r['geojson']]=('application/geo+json',json.dumps(geo).encode())
    with pytest.raises((ValueError,OSError)):snapshot_sources(root,d,files)
