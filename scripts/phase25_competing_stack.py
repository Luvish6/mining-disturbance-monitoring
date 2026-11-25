"""Acquire paired observed stacks for selected TRAIN windows; append, never recreate V2."""
import json
from pathlib import Path
import numpy as np
from affine import Affine
from rasterio.io import MemoryFile
from scripts.phase25b_cached import digest,tif
from scripts.phase25b1_recover import save_verified,cached_json,graphs as context_layers,NAMES as CONTEXT_NAMES
from scripts.phase25_multiclass_acquire import graph as dw_graph,NAMES as DW_NAMES
from src.phase25.features import Grid
from src.phase25.competing_classes import competing_evidence
from scripts.phase25_competing_recover import OUT,PARENT

EXTRA=[s+'_'+p+'_'+n for s in ['before','after'] for p in ['early','late'] for n in ['NDVI','BSI','count']]+['follow_built','follow_crops','follow_dw_count']


def stack(row,cfg):
    import ee
    from config.phase2_settings import Phase2Config
    from config.settings import Season
    from scripts.phase22l_temporal import seasonal_graph
    from src import sar_preprocessing as sar
    region=ee.Geometry.Rectangle(row['bounds'],'EPSG:32646',False);pcfg=Phase2Config(relative_orbit=77)
    values={};info={};periods=dict(cfg['seasons'],follow=['2025-11-01','2026-04-01'])
    for s,dates in periods.items():
        image,count,raw,joined=seasonal_graph(region,Season(s,*dates),pcfg)
        for b in ['B2','B3','B4','NDVI','BSI','NDWI']:values[s+'_'+b]=image.select(b)
        values[s+('_count' if s=='follow' else '_optical_count')]=count
        info[s]=dict(s2_ids=joined.aggregate_array('system:index'),s2_dates_ms=joined.aggregate_array('system:time_start'),window=dates)
        if s!='follow':
            col=sar.collection(region,Season(s,*dates),pcfg).filter(ee.Filter.eq('relativeOrbitNumber_start',77));db,sc=sar.seasonal(col,77,region,pcfg)
            for b in ['VV','VH']:values[s+'_'+b]=db.select(b)
            values[s+'_sar_count']=sc;info[s].update(s1_ids=col.aggregate_array('system:index'),s1_dates_ms=col.aggregate_array('system:time_start'),relative_orbit=77,direction=pcfg.orbit_pass,units='dB; spatial smoothing in linear power')
            mid=str(int(dates[0][:4])+1)+'-01-01'
            for part,period in [('early',[dates[0],mid]),('late',[mid,dates[1]])]:
                sub,n,_,joined_sub=seasonal_graph(region,Season(s+'_'+part,*period),pcfg)
                for b in ['NDVI','BSI']:values[s+'_'+part+'_'+b]=sub.select(b)
                values[s+'_'+part+'_count']=n;info[s+'_'+part]=dict(s2_ids=joined_sub.aggregate_array('system:index'),s2_dates_ms=joined_sub.aggregate_array('system:time_start'),window=period)
    context,context_info=context_layers(ee,row['aoi'],row);info['context']=context_info
    for name,source in [('elevation','elevation'),('land_cover','land_cover'),('surface_water','water_occurrence')]:values[name]=context.select(source)
    values['slope']=ee.Terrain.slope(ee.Image('USGS/SRTMGL1_003').select('elevation'))
    values['rainfall']=context.select('rain_after_mm').subtract(context.select('rain_before_mm'))
    dw,dw_info=dw_graph(ee,row,cfg);info['dynamic_world_fire']=dw_info
    for n in DW_NAMES:values[n]=dw.select(n)
    follow=ee.ImageCollection(cfg['sources']['dynamic_world']).filterBounds(region).filterDate(*periods['follow']);n=follow.select('built').count().unmask(0)
    values['follow_dw_count']=n
    for b in ['built','crops']:values['follow_'+b]=follow.select(b).median().updateMask(n.gte(2))
    info['follow_dynamic_world']=dict(ids=follow.aggregate_array('system:index'),dates_ms=follow.aggregate_array('system:time_start'))
    for b in ['VV','VH','NDVI','BSI']:values['d'+b]=values['after_'+b].subtract(values['before_'+b])
    blank=ee.Image.constant(0).updateMask(ee.Image.constant(0))
    m=json.loads((PARENT/'manifest.json').read_bytes());names=[n for n in m['bands'] if n!='temporal_persistence']+EXTRA
    image=ee.Image.cat([values.get(n,blank).rename(n) for n in names]).clip(region)
    return image,info,names


def check(raw,row,names):
    with MemoryFile(raw) as memory,memory.open() as ds:
        expected=Affine(30,0,row['bounds'][0],0,-30,row['bounds'][3])
        if ds.shape!=(32,32) or ds.count!=len(names) or ds.crs.to_string()!='EPSG:32646' or ds.transform!=expected or (any(ds.descriptions) and list(ds.descriptions)!=names):raise ValueError('Shape/band/grid mismatch: '+str((ds.shape,ds.count,ds.crs.to_string(),list(ds.transform)[:6],ds.descriptions[:3])))
        a=ds.read().astype('float32');a[a==-9999]=np.nan
    if np.isinf(a).any():raise ValueError('Nonfinite acquired values')
    for i,n in enumerate(names):
        if n.endswith('count'):
            v=a[i][np.isfinite(a[i])]
            if np.any(v<0) or np.any(v!=np.floor(v)):raise ValueError('Observation counts invalid')
    return a


def acquire_and_build(plan,selected,meter,cfg):
    rows=[];counts={str(k):0 for k in [0,1,2,3,4,255]};m=json.loads((PARENT/'manifest.json').read_bytes());thresholds=cfg['thresholds']
    # Empty selection is an honest measured outcome, not an invitation to relocate.
    for row in selected:
        pid='mci_supp_'+row['aoi'].replace(':','_');folder=OUT/'patches'/pid;folder.mkdir(parents=True,exist_ok=True);source=folder/'source_stack.tif'
        image,info,names=stack(row,cfg);meta=folder/'source_receipt.json'
        if not meta.exists():
            import ee
            values=ee.Dictionary(info).getInfo();save_verified(meta,dict(source_metadata=values,graph_sha256=__import__('hashlib').sha256(image.serialize().encode()).hexdigest(),plan_sha256=digest(OUT/'frozen_plan.json'),bands=names,selection=row))
        else:
            receipt=cached_json(meta)
            if receipt['bands']!=names or receipt['plan_sha256']!=digest(OUT/'frozen_plan.json'):raise ValueError('Cached plan/source mismatch')
        band_receipt=folder/'export_band_order.json'
        if not band_receipt.exists():
            actual=image.bandNames().getInfo()
            if actual!=names:raise ValueError('Server-side band order mismatch')
            save_verified(band_receipt,dict(bands=actual,graph_sha256=__import__('hashlib').sha256(image.serialize().encode()).hexdigest(),explanation='GeoTIFF descriptions may be absent; explicit server-side ordered bands verified before export'))
        elif cached_json(band_receipt)['bands']!=names:raise ValueError('Band order receipt mismatch')
        if source.exists():
            if not (folder/'source.sha256').exists() or (folder/'source.sha256').read_text().strip()!=digest(source):raise ValueError('Unverified cached raster')
            a=check(source.read_bytes(),row,names)
        else:
            url=image.toFloat().unmask(-9999,False).getDownloadURL(dict(format='GEO_TIFF',crs='EPSG:32646',crs_transform=[30,0,row['bounds'][0],0,-30,row['bounds'][3]],dimensions=[32,32]))
            response,raw=meter.request(url)
            if response.status!=200:raise ValueError('GEE export failed')
            diagnostic=folder/('response_attempt_'+str(len(meter.rows))+'.tif')
            diagnostic.write_bytes(raw)
            a=check(raw,row,names)
            with source.open('xb') as f:f.write(raw)
            (folder/'source.sha256').write_text(digest(source)+'\n',encoding='utf-8')
        v=dict(zip(names,a));result=competing_evidence(v,thresholds);grid=Grid('EPSG:32646',(30,0,row['bounds'][0],0,-30,row['bounds'][3]),(32,32))
        if (folder/'weak_classes.tif').exists():raise ValueError('Never overwrite completed patch')
        tif(folder/'weak_classes.tif',result['labels'],grid,['WEAK_COMPETING_CLASS_NOT_REFERENCE'],dtype='uint8',nodata=255)
        tif(folder/'validity.tif',np.isfinite(a).astype('uint8'),grid,names,dtype='uint8',nodata=255)
        # Preserve parent model inputs; all new temporal diagnostics/follow-up stay annotation-only.
        inputs=m['model_input_bands'];features=a[[names.index(n) for n in inputs]]
        np.savez_compressed(folder/'model_ready.npz',features=features,validity=np.isfinite(features),weak_labels=result['labels'],label_valid=result['labels']!=255)
        count={str(k):int((result['labels']==k).sum()) for k in [0,1,2,3,4,255]}
        for k,c in count.items():counts[k]+=c
        rows.append(dict(patch_id=pid,group_id=row['aoi'],split='train',bounds=row['bounds'],crs='EPSG:32646',affine=list(grid.affine),shape=[32,32],classes=count,folder=folder.relative_to(OUT).as_posix(),source_sha256=digest(source),source_receipt_sha256=digest(meta),mining_attribution='UNKNOWN',reference_labels=None))
        print(json.dumps(dict(patch=pid,classes=count,traffic=meter.summary())),flush=True)
    manifest=dict(schema='mci-multiclass-extension/1',parent_path='../minechange-india-multiclass-v2',parent_integrity_sha256=plan['parent_inventory_sha256'],parent_patches=80,new_train_patches=rows,unchanged_val_patches=12,test_sealed=True,classes=plan['classes'],model_input_bands=m['model_input_bands'],annotation_only_bands=m['annotation_only_bands']+EXTRA,quality_only_bands=m['quality_only_bands'],label_semantics='WEAK_ALGORITHMIC_HYPOTHESES_NOT_REFERENCE',reference_labels=None,operational_alerts=0)
    save_verified(OUT/'extension_manifest.json',manifest);save_verified(OUT/'summary.json',dict(supplemental_patches=len(rows),combined_patches=80+len(rows),new_class_counts=counts,class_group_support={k:len({r['group_id'] for r in rows if r['classes'][k]}) for k in counts},traffic=meter.summary(),official_nrsc_numeric_layers_acquired=0,verified_labels=0,rights='NRSC catalogs/failed service probes are context only; no numeric NRSC legend accepted. Copernicus,CC-BY4WorldCover/DW,CHIRPS,JRC,SRTM,MODIS attribution applies; external release unauthorized.'))
