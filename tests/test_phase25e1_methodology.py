import ast
from pathlib import Path
import numpy as np
import pytest
from src.phase25.dataset import BANDS,COUNTS
from src.phase25.methodology import score_cached,build_graph_bundle
from src.phase3.spatial import partition
import json

RULES=json.loads(Path('config/phase25b_v1.json').read_bytes())['rules']


def fixture():
    x=np.zeros((len(BANDS),32,32),dtype='float32')
    for s in ['before','after']:x[BANDS.index(s+'_NDWI')]=-.5
    for n,v in [('dNDVI',-.4),('dBSI',.2),('dVV',-1),('dVH',-1)]:x[BANDS.index(n)]=v
    return dict(features=x,counts=np.full((len(COUNTS),32,32),2.),validity=np.isfinite(x),pseudo_states=np.full((32,32),255))


def test_frozen_rule_count_and_missing_signal_no_fabrication():
    r=fixture();a=score_cached(r,RULES);assert np.all(a['score']==3)
    r['features'][BANDS.index('dVH')]=1
    assert np.all(score_cached(r,RULES)['score']==2)
    r['features'][BANDS.index('before_NDWI')]=.1
    assert np.isnan(score_cached(r,RULES)['score']).all()
    r=fixture();r['counts'][COUNTS.index('after_sar_count')]=np.nan
    assert np.isnan(score_cached(r,RULES)['score']).all()


def test_context_never_changes_score_or_makes_mining_labels():
    r=fixture();a=score_cached(r,RULES)
    for name in ['land_cover','rainfall','surface_water','roads','geology','mining_context','fire_history']:
        r['features'][BANDS.index(name)]=np.nan
    r['features'][BANDS.index('slope')]=65
    r['validity']=np.isfinite(r['features']);b=score_cached(r,RULES)
    assert np.array_equal(a['score'],b['score']) and b['contexts']['roads']['status']=='MISSING'
    assert b['alternatives']['steep_terrain_context_cells']==1024
    r['pseudo_states'][:]=1
    assert np.array_equal(b['score'],score_cached(r,RULES)['score'])
    assert 'reference_label' not in b


def test_invalid_masks_rejected():
    r=fixture();r['validity'][:]=False
    with pytest.raises(ValueError,match='masks'):score_cached(r,RULES)


def test_graph_test_partition_rejected_before_any_ee_use():
    key=next(f'{n}:557' for n in range(100) if partition(f'{n}:557')=='test')
    with pytest.raises(ValueError,match='TRAIN only'):build_graph_bundle(None,key,dict(split='test'),None,None)


def test_graph_composes_existing_builders_without_evaluation(monkeypatch):
    from types import SimpleNamespace
    import scripts.phase25b_cached as cached
    import scripts.phase25b1_recover as context
    import scripts.phase22l_temporal as optical
    import src.sar_preprocessing as sar
    key=next(f'{n}:557' for n in range(100) if partition(f'{n}:557')=='train')
    calls=[]
    monkeypatch.setattr(cached,'guarded',lambda *a:calls.append('guard'))
    class Image:
        def select(self,n):return ('selected',n)
    monkeypatch.setattr(context,'graphs',lambda *a:(Image(),{'source_ids':'lazy metadata'}))
    monkeypatch.setattr(optical,'seasonal_graph',lambda region,season,cfg:('optical','count',None,None))
    monkeypatch.setattr(sar,'collection',lambda *a:'collection')
    monkeypatch.setattr(sar,'seasonal',lambda col,orbit,region,cfg:('sar','count') if orbit==77 else pytest.fail('Orbit changed'))
    ee=SimpleNamespace(Geometry=SimpleNamespace(Rectangle=lambda *a:'region'),Terrain=SimpleNamespace(slope=lambda im:'slope'))
    out,info=build_graph_bundle(ee,key,dict(split='train',bounds=[0,0,1920,1920]),None,None)
    assert calls==['guard'] and set(out)=={'context','slope','before','after'}
    assert out['before']['sar']=='sar' and info['source_ids']=='lazy metadata'
    tree=ast.parse(Path('src/phase25/methodology.py').read_text())
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in {'getInfo','Initialize','getDownloadURL','start'} for n in ast.walk(tree))
