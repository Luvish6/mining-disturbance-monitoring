"""Machine checks for real-input evidence; these do not replace human review."""
from datetime import date
import json
import math
from config.settings import BEFORE, AFTER

TARGET='new_mining_related_disturbance_2023_2025'


def validate_references(references):
    if not references: raise ValueError('No independently reviewed references')
    for props in references:
        if props.get('synthetic') is not False or props.get('independent_reference') is not True:
            raise ValueError('Real references require explicit independent evidence and synthetic=false')
        if props.get('target_definition')!=TARGET:
            raise ValueError('Reference target must describe new mining-related disturbance in the comparison')
        for key,season in (('before_evidence_date',BEFORE),('after_evidence_date',AFTER)):
            value=props.get(key,''); date.fromisoformat(value)
            if not season.start<=value<season.end:
                raise ValueError('Reference evidence date falls outside its seasonal window')
        error=props.get('spatial_accuracy_m')
        if isinstance(error,bool) or not isinstance(error,(int,float)) or not math.isfinite(error) or not 0<=error<=30:
            raise ValueError('Document a finite reference positional error <=30 m, not image pixel size')
        if (not isinstance(props.get('second_reviewer'),str) or not props['second_reviewer'].strip()
                or props['second_reviewer']==props.get('reviewer')):
            raise ValueError('Independent second reviewer required')
        urls=props.get('evidence_urls')
        if not isinstance(urls,list) or not urls or any(not isinstance(u,str) or not u.startswith(('https://','http://')) for u in urls):
            raise ValueError('Document independent evidence URLs')


def validate_real_manifest(manifest):
    if manifest.get('resolution_m')!=30 or manifest.get('crs')!='EPSG:32646':
        raise ValueError('Real data requires the agreed 30 m EPSG:32646 grid')
    validate_references(manifest.get('label_provenance',[]))
    try: meta=json.loads(manifest.get('raster_metadata',{}).get('provenance','{}'))
    except (ValueError,TypeError) as exc: raise ValueError('Missing registered real raster provenance') from exc
    if (meta.get('data_kind')!='real' or not meta.get('source') or not meta.get('export_id')
            or meta.get('seasons')!=[[BEFORE.start,BEFORE.end],[AFTER.start,AFTER.end]]
            or not isinstance(meta.get('relative_orbit'),int) or not 1<=meta['relative_orbit']<=175
            or meta.get('orbit_pass') not in ('ASCENDING','DESCENDING')):
        raise ValueError('Registered seasonal raster provenance is incomplete')
    for key in ('raster_sha256','coverage_report_sha256'):
        value=meta.get(key,'')
        if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdefABCDEF' for c in value):
            raise ValueError('Recorded source and coverage hashes are required')
