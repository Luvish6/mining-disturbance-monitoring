"""Export exact saved MineMind research tables/figure; no inference, fitting or HTTP."""
import argparse,csv,hashlib,io,json,shutil
from pathlib import Path

RUNS={
 'replica_baselines':'outputs/phase25/experiments/minemind-cached-v1',
 'learning_recovery':'outputs/phase25/experiments/minemind-learning-v1',
 'geographic_development_holdouts':'outputs/phase25/experiments/minemind-geographic-comparison-v1',
}
FIELDS=['cohort','site','method','eligible_cells','spearman','top5_jaccard','candidate_jaccard','polygons_r1','polygons_r2','area_r1_m2','area_r2_m2','same_season_before','same_season_after','threshold','cutoff_basis','source_metrics_sha256']


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verified(root,relative):
    folder=Path(root)/relative
    for name,digest in json.loads((folder/'integrity.json').read_bytes()).items():
        p=(folder/name).resolve()
        if not p.is_relative_to(folder.resolve()) or sha(p)!=digest:raise ValueError('Saved research artifact integrity mismatch')
    return json.loads((folder/'metrics.json').read_bytes()),sha(folder/'metrics.json')


def collect(root):
    records=[];sources={}
    for cohort,relative in RUNS.items():
        saved,digest=verified(root,relative);sources[relative+'/metrics.json']=digest
        sites=saved['holdouts'] if cohort=='geographic_development_holdouts' else saved['sites']
        for site_id,site in sites.items():
            for method,run in site['methods'].items():
                m=run['metrics'];p=m['polygons'];a=m['candidate_area_m2'];s=m['same_season_exceedance']
                records.append(dict(cohort=cohort,site=site.get('state',site_id),method=method,eligible_cells=site['eligible_cells'],spearman=m['spearman'],top5_jaccard=m['top5_jaccard'],candidate_jaccard=m['candidate_jaccard'],polygons_r1=p[0],polygons_r2=p[1],area_r1_m2=a[0],area_r2_m2=a[1],same_season_before=s[0],same_season_after=s[1],threshold=run['threshold'],cutoff_basis=('fixed Phase15C 2.5/6' if method=='phase15c' else 'original calibration81cell quota') if cohort=='replica_baselines' else 'TRAIN99.5percentile' if cohort=='learning_recovery' else 'TRAIN41cell quota',source_metrics_sha256=digest))
    return records,sources


def markdown(records):
    text=['\n<!-- MINEMIND_FINAL_RESULTS_V1 -->','## Final MineMind methods and saved-result comparison','',
      'The canonical 30 m stack retains registered before/after VV, VH, NDVI and NDTI, their signed differences, elevation and slope. SAR smoothing is performed in linear power before dB compositing. Cloud-probability <40, accepted SCL classes, at least two observations and the existing <=25-degree slope support are retained for comparison; this slope restriction is not a mining-location assumption. Seasons are [2023-11-01,2024-04-01) and [2024-11-01,2025-04-01).',
      '', 'The frozen pointwise 8D encoder learned cross-sensor masked Huber reconstruction using four BEFORE-season TRAIN blocks, with TRAIN median/MAD normalization. Four separate blocks supplied original calibration cutoffs. Sensor-only variants and reliability weighting use the same observed cells. Adaptive weights combine modality availability, count saturation and TRAIN cross-reconstruction/latent-scale statistics; they are not calibrated sensor-quality probabilities. The temporal auxiliary reconstruction attempt retained the original encoder architecture and used TRAIN seasonal pairs only. No follow-up, human review or independent mining labels entered these SSL fits.',
      '', 'One six-state expansion supplied four new reliability-fit regions and two geographic development holdouts, inside previously frozen TRAIN geography. These holdouts were not moved from official TEST. Encoder weights and normalization stayed frozen. A single 0.00723-second reliability fit used 8,191 balanced BEFORE cells across eight TRAIN blocks. All geographic methods selected 41 cells from the same TRAIN sample; historical cutoffs/results were preserved. The original 5 km/120 m design and inherited 2,050 m Maus opposing-group guard remain unchanged.',
      '', 'The table below reports saved values to six decimals; the [machine-readable CSV](minemind-comparison.csv) preserves unrounded values, cutoffs, areas and counts; blank CSV ratios mean undefined, never zero. Comparisons are within cohorts on identical support. Cutoff-dependent areas from different calibration policies are not matched comparisons. No pixel-level significance or mining accuracy is inferred.',
      '', '| Cohort | Site | Method | Cells | Spearman | Top-5% Jaccard | Candidate Jaccard |',
      '|---|---|---|---:|---:|---:|---:|']
    for r in records:
        if r['cohort']=='replica_baselines':continue  # Original replica table above remains unchanged.
        f=lambda v:'undefined' if v is None else f'{v:.6f}'
        text.append('| '+' | '.join([r['cohort'],r['site'],r['method'],str(r['eligible_cells']),f(r['spearman']),f(r['top5_jaccard']),f(r['candidate_jaccard'])])+' |')
    text += ['', '**Negative findings and decision.** Temporal recovery reduced pretext loss (0.386740 to 0.358242) without consistent repeatability gains. Expanded adaptive ranking improved modestly over prior adaptive on the two new holdouts, but top-5% overlap did not improve; Haryana after-season same-season exceedance increased from 12.890625% to 14.648438%. This proxy is NOT a true false-positive rate. Optical-only was more repeatable than fusion in the Madhya Pradesh window. Missing-sensor rankings remain sensor-dependent. Stop optimization; retain Phase15C as primary and SSL/adaptive variants as ablations. No model was promoted to operational use.',
      '', '**Geographic/evidence limits.** Both geographic holdouts have historical cropland context. Six acquired AOIs do not provide balanced agriculture/built-up/forest/disturbance coverage: built-up support is limited. WorldCover2021 is historical context, not current reference truth. The source mining-study sampling frame is biased, and only four Meghalaya blocks trained the encoder. Controlled sensor withholding does not validate natural missingness. Reconstruction disagreement may suppress real discordant change. Competing-explanation separation is undefined without independently reviewed class evidence; candidate polygons remain UNKNOWN/REVIEW_REQUIRED. No national generalization, mining legality or causal river attribution is established.',
      '', '**Other frozen experiments remain separate.** The later preregistered [RGB RF test](phase17g-rf-heldout-results.md) used 60 patches/15 official TEST mines, 3,932,160 pixels/421,918 changed pixels, cutoff0.65: precision0.2374, recall0.2554, F1 0.2461, IoU0.1403, FPR0.0986; confusion [[3164101,346141],[314144,107774]]. The [RGB U-Net recovery](phase17e-unet-recovery.md) was not promoted. These reports are reused, not rescored. RGB benchmark performance cannot validate Indian Sentinel inference. The [2019 static weak-label experiment](phase22h-expanded-training.md) reported U-Net weak-label VAL F1 0.7131+/-0.0848, IoU0.5585+/-0.0989 and FPR0.0838+/-0.0468 across seeds; all VAL groups were in Odisha and model selection reused those weak labels. Static footprint agreement, temporal pseudo-label agreement and unsupervised repeatability are different outcomes; they must not be pooled or ranked as equivalent accuracy.',
      '', '**River result.** The separate [Brahmani matched-date comparison](downstream-river-consolidation.md) retains16 pairs/five months,93 upstream/75 downstream common cells and seasonal downstream-minus-upstream contrast change -0.08062309711104701 dimensionless NDTI. Leshka12<25 cells remains insufficient. NDTI is not NTU, acidity or contamination; mining-to-reach attribution remains unverified. No river recomputation is needed for this consolidation.',
      '', '**Reproduction and artifacts.** See [README offline launch](../../README.md#current-offline-minemind-run) and [commands](../REPRODUCIBILITY.md#current-minemind-application-and-saved-result-export). `scripts.minemind_deliverables` verifies saved artifact hashes and exports tables plus a copy of the existing numeric-only geographic comparison figure. The PNG remains private in the output bundle; no satellite pixels or restricted imagery enter the committed CSV/provenance. The [provenance manifest](minemind-comparison-provenance.json) records exact source metric hashes. Models, imagery, scene receipts, full figures and review materials remain local. No new training, acquisition, TEST payload access or experimental tuning was performed for this deliverable.', '']
    return '\n'.join(text)


def build(root,out):
    root=Path(root);out=Path(out)
    if out.exists():raise ValueError('Choose a new output bundle; historical artifacts are immutable')
    records,sources=collect(root)
    figure=root/'outputs/phase25/qa/minemind-geography-v1/comparison.png'
    fp=json.loads((figure.parent/'figure-provenance.json').read_bytes())
    geo=RUNS['geographic_development_holdouts']+'/metrics.json'
    if fp['metrics_sha256']!=sources[geo] or fp['figure_sha256']!=sha(figure):raise ValueError('Existing figure provenance mismatch')
    b=io.StringIO(newline='');writer=csv.DictWriter(b,fieldnames=FIELDS);writer.writeheader();writer.writerows(records)
    out.mkdir(parents=True);(out/'minemind-comparison.csv').write_text(b.getvalue(),encoding='utf-8',newline='')
    (out/'methods-results.md').write_text(markdown(records),encoding='utf-8');shutil.copyfile(figure,out/'geographic-comparison.png')
    provenance=dict(schema='minemind-saved-results/1',source_metrics_sha256=sources,rows=len(records),figure_source_metrics_sha256=fp['metrics_sha256'],figure_sha256=fp['figure_sha256'],metric_kind='Unsupervised repeatability, not mining accuracy',new_training=False,new_acquisition=False,test_payload_access=False,operational_alerts=0)
    (out/'minemind-comparison-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8')
    print(f'Exported {len(records)} saved-result rows and one existing numeric-only figure; no model execution.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();build(Path.cwd(),a.output)
