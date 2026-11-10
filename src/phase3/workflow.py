"""Readiness tools for human reference labeling and bounded raster preparation."""
import argparse
import json
from pathlib import Path
import numpy as np
import rasterio
from pyproj import Transformer
from shapely import transform
from shapely.geometry import box, mapping, shape
from .data import BANDS, digest, save_json
from .labels import load_labels, save_ee_labels
from .spatial import block_for, partition


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)


def init_labels(output):
    """Empty collection only: no invented examples enter the data directory."""
    write_new(output, dict(type='FeatureCollection', features=[]))


def check_labels(labels, output, seed=42, block_m=5000, buffer_m=120):
    summary = dict(status='blocked', training_ready=False, issues=[], polygons=[],
                   counts={s: [0, 0] for s in ('train','validation','test')},
                   independent_blocks={s: [] for s in ('train','validation','test')},
                   note='Polygon counts are not pixel counts; run dataset preparation for final readiness.')
    try:
        references = load_labels(labels)
    except (ValueError, KeyError, TypeError) as exc:
        summary['issues'].append(str(exc))
        write_new(output, summary)
        return summary
    project = Transformer.from_crs(4326, 32646, always_xy=True).transform
    kinds = set()
    for geometry, properties in references:
        kinds.add(bool(properties.get('synthetic', False)))
        metric = transform(geometry, project, interleaved=False)
        block = block_for(metric.bounds, block_m, buffer_m)
        split = partition(block, seed) if block is not None else None
        row = dict(label_id=properties['label_id'], label=properties['label'],
                   area_m2=metric.area, block=block, split=split,
                   retained=block is not None)
        summary['polygons'].append(row)
        if block is None:
            summary['issues'].append(f"{properties['label_id']}: crosses a block core or buffer; redraw conservative interiors")
        else:
            summary['counts'][split][properties['label']] += 1
            summary['independent_blocks'][split].append(block)
    for split, blocks in summary['independent_blocks'].items():
        summary['independent_blocks'][split] = sorted(set(blocks))
        if not blocks:
            summary['issues'].append(f'No retained {split} reference blocks')
        elif 0 in summary['counts'][split]:
            summary['issues'].append(f'{split}: a reference class is missing')
    if len(kinds) != 1:
        summary['issues'].append('Mixed synthetic and real references')
    summary['data_kind'] = 'synthetic' if kinds == {True} else 'real'
    summary['status'] = 'needs_correction' if summary['issues'] else 'label_checks_passed'
    summary['label_sha256'] = digest(labels)
    write_new(output, summary)
    return summary


def block_grid(aoi, output, seed=42, block_m=5000, buffer_m=120):
    """Unlabeled reference-planning grid, clipped to an explicit user AOI."""
    document = json.loads(Path(aoi).read_text(encoding='utf-8-sig'))
    if document.get('crs'):
        raise ValueError('Use RFC 7946 WGS84 GeoJSON')
    if document.get('type') == 'Feature':
        geometry = shape(document['geometry'])
    else:
        geometry = shape(document)
    if geometry.is_empty or not geometry.is_valid or geometry.geom_type not in ('Polygon','MultiPolygon'):
        raise ValueError('Supply one valid AOI Polygon/MultiPolygon or Feature')
    if not (-180 <= geometry.bounds[0] <= geometry.bounds[2] <= 180 and -90 <= geometry.bounds[1] <= geometry.bounds[3] <= 90):
        raise ValueError('AOI coordinates must be WGS84 longitude/latitude')
    forward = Transformer.from_crs(4326,32646,always_xy=True).transform
    inverse = Transformer.from_crs(32646,4326,always_xy=True).transform
    metric = transform(geometry,forward,interleaved=False)
    block_for(metric.bounds,block_m,buffer_m)  # validate settings
    lo = np.floor(np.array(metric.bounds[:2])/block_m).astype(int)
    hi = np.floor(np.array(metric.bounds[2:])/block_m).astype(int)
    if int(np.prod(hi-lo+1)) > 10000:
        raise ValueError('AOI is too large for a bounded labeling grid')
    features = []
    for x in range(lo[0],hi[0]+1):
        for y in range(lo[1],hi[1]+1):
            core = box(x*block_m+buffer_m,y*block_m+buffer_m,
                       (x+1)*block_m-buffer_m,(y+1)*block_m-buffer_m).intersection(metric)
            if core.is_empty or core.area == 0:
                continue
            block = f'{x}:{y}'
            features.append(dict(type='Feature',geometry=mapping(transform(core,inverse,interleaved=False)),
                properties=dict(block=block,split=partition(block,seed),block_m=block_m,
                                buffer_m=buffer_m,seed=seed,purpose='unlabeled planning core')))
    write_new(output,dict(type='FeatureCollection',features=features))
    return len(features)


def audit_raster(raster, output, max_pixels=4_000_000):
    """Read-only windowed inspection. No zeros are inferred to be missing data."""
    with rasterio.open(raster) as ds:
        if ds.width*ds.height > max_pixels or ds.count != len(BANDS):
            raise ValueError('Expected a bounded 14-band tile')
        a = ds.transform
        issues = []
        if ds.crs is None or ds.crs.to_epsg()!=32646:
            issues.append('Expected EPSG:32646')
        if a.b or a.d or a.a<=0 or a.e>=0 or abs(a.a+a.e)>1e-6:
            issues.append('Expected north-up square pixels')
        if tuple(ds.descriptions)!=BANDS:
            issues.append('Band descriptions/order do not match the ingestion contract')
        if ds.tags().get('data_kind') not in ('real','synthetic'):
            issues.append('Missing real/synthetic provenance tag')
        valid_counts = np.zeros(ds.count,dtype='int64')
        sums = np.zeros(ds.count); minima=np.full(ds.count,np.inf); maxima=np.full(ds.count,-np.inf)
        common, total = 0, ds.width*ds.height
        for _, window in ds.block_windows(1):
            values = ds.read(window=window)
            valid = (ds.read_masks(window=window)>0)&np.isfinite(values)
            common += int(valid.all(axis=0).sum())
            for c in range(ds.count):
                v = values[c][valid[c]].astype('float64')
                valid_counts[c]+=v.size; sums[c]+=v.sum()
                if v.size:
                    minima[c]=min(minima[c],v.min()); maxima[c]=max(maxima[c],v.max())
        if common==0:
            issues.append('No common valid pixels')
        summary=dict(status='needs_correction' if issues else 'raster_checks_passed',issues=issues,
                     raster_sha256=digest(raster),crs=str(ds.crs),transform=list(a)[:6],
                     width=ds.width,height=ds.height,nodata=ds.nodata if ds.nodata is None or np.isfinite(ds.nodata) else str(ds.nodata),
                     data_kind=ds.tags().get('data_kind'),common_valid_pixels=common,
                     common_valid_fraction=common/total,
                     bands=[dict(name=ds.descriptions[c],valid_pixels=int(n),valid_fraction=int(n)/total,
                                 min=float(minima[c]) if n else None,max=float(maxima[c]) if n else None,
                                 mean=float(sums[c]/n) if n else None) for c,n in enumerate(valid_counts)])
    write_new(output,summary)
    return summary


def register_raster(raster, metadata, output, coverage_report=None):
    """Copy a source export with explicit provenance; never alter the original."""
    meta=json.loads(Path(metadata).read_text(encoding='utf-8-sig'))
    for key in ('source','export_id','operator','retrieved_date'):
        if not isinstance(meta.get(key),str) or not meta[key].strip():
            raise ValueError(f'Missing raster provenance: {key}')
    from datetime import date
    date.fromisoformat(meta['retrieved_date'])
    if meta.get('data_kind') not in ('real','synthetic') or meta.get('band_order')!=list(BANDS):
        raise ValueError('Explicit data_kind and exact source band order required')
    if meta.get('raster_sha256')!=digest(raster):
        raise ValueError('Source raster checksum does not match provenance')
    from config.settings import BEFORE, AFTER
    seasons=[[BEFORE.start,BEFORE.end],[AFTER.start,AFTER.end]]
    if meta.get('seasons')!=seasons:
        raise ValueError('Provenance seasons differ from the project comparison')
    if meta['data_kind']=='real':
        if coverage_report is None:
            raise ValueError('Real input requires a saved successful coverage report')
        report=json.loads(Path(coverage_report).read_text(encoding='utf-8'))
        if (report.get('status')!='district_coverage_passed'
                or not report.get('district_coverage_checked')
                or not report.get('district_coverage',{}).get('coverage_gate_passed')
                or meta.get('coverage_report_sha256')!=digest(coverage_report)
                or meta.get('relative_orbit')!=report.get('metadata',{}).get('selected_relative_orbit')
                or meta.get('orbit_pass')!=report.get('config',{}).get('orbit_pass')
                or report.get('seasons')!=[vars(BEFORE),vars(AFTER)]):
            raise ValueError('Raster provenance does not match successful seasonal coverage report')
    output=Path(output)
    if output.exists():
        raise ValueError('Choose a new registered raster output')
    with rasterio.open(raster) as src:
        existing=src.tags().get('data_kind')
        if existing and existing!=meta['data_kind']:
            raise ValueError('Refusing to change real/synthetic identity')
        a=src.transform
        if (src.count!=14 or src.width*src.height>4_000_000 or src.crs is None
                or src.crs.to_epsg()!=32646 or a.a!=30 or a.e!=-30 or a.b or a.d):
            raise ValueError('Registration requires a bounded 14-band, north-up 30 m EPSG:32646 source')
        if any(src.descriptions) and tuple(src.descriptions)!=BANDS:
            raise ValueError('Existing band descriptions conflict with declared order')
        if src.nodata is None:
            raise ValueError('Explicit source nodata required; never infer missing zeros')
        output.parent.mkdir(parents=True,exist_ok=True)
        profile=src.profile.copy()
        profile.update(driver='GTiff')
        try:
            with rasterio.open(output,'w',**profile) as dst:
                for _,window in src.block_windows(1):
                    dst.write(src.read(window=window),window=window)
                    # Preserve any dataset-wide validity mask in addition to nodata.
                    if any(rasterio.enums.MaskFlags.per_dataset in flags for flags in src.mask_flag_enums):
                        dst.write_mask(src.dataset_mask(window=window),window=window)
                dst.descriptions=BANDS
                dst.update_tags(**src.tags())
                dst.update_tags(data_kind=meta['data_kind'],provenance=json.dumps(meta,allow_nan=False))
        except Exception:
            if output.exists():
                output.unlink()
            raise
    return str(output)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('init-labels'); p.add_argument('output')
    p=sub.add_parser('check-labels'); p.add_argument('labels'); p.add_argument('output')
    g=sub.add_parser('block-grid'); g.add_argument('aoi'); g.add_argument('output')
    for p in (p,g):
        p.add_argument('--seed',type=int,default=42); p.add_argument('--block-m',type=float,default=5000)
        p.add_argument('--buffer-m',type=float,default=120)
    p=sub.add_parser('audit-raster'); p.add_argument('raster'); p.add_argument('output')
    p=sub.add_parser('register-raster'); p.add_argument('raster'); p.add_argument('metadata'); p.add_argument('output')
    p.add_argument('--coverage-report')
    p=sub.add_parser('import-ee-labels'); p.add_argument('asset'); p.add_argument('output')
    args=vars(parser.parse_args()); command=args.pop('command')
    if command=='import-ee-labels':
        import ee
        from src.gee_setup import initialize
        initialize(); save_ee_labels(ee.FeatureCollection(args['asset']),args['output'])
        return
    result={'init-labels':init_labels,'check-labels':check_labels,
            'block-grid':block_grid,'audit-raster':audit_raster,'register-raster':register_raster}[command](**args)
    if isinstance(result,dict):
        print(result['status'])
        if result.get('issues'):
            for issue in result['issues']:
                print(f'- {issue}')
            raise SystemExit(2)


if __name__=='__main__':
    main()
