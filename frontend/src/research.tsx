import {useEffect, useMemo, useState} from 'react';
import {AlertTriangle, BarChart3, Download, FileText, Route} from 'lucide-react';
import './research.css';
import {localSnapshot} from './research-data';

type CI = [number, number];
type Source = {file: string; sha256: string};
type Aoi = {aoi: string; district: string; split: string; candidate_cells: number; clusters: number; candidate_ha: number; density: number; dvh_db: number | null; status: string};
type Share = {share: number; ci95: CI; clusters: number};
type Arm = {features: string[]; precision: number; recall: number; f1: number; iou: number; fpr: number; f1_ci95: CI; iou_ci95: CI};
type Reach = Record<string, string | number>;
export type Research = {
  mining_attribution: string; earth_engine_requests: number;
  landscape: {source: Source; aois: number; clusters_tested: number;
    density: {overall: {mean: number; ci95: CI; aois: number; aois_with_candidates: number}; by_district: Record<string, {mean: number; ci95: CI; aois: number; aois_with_candidates: number}>; unit: string};
    sar_dvh: {mean_db: number; aois_negative: number[]; null: {null_median: number; p_two_sided: number}}; sar_dvv: {mean_db: number};
    gfc_recent_loss: {clusters: number[]; fraction: number; wilson95: CI; null_median: number};
    hard_commodities: {mean_probability: number; null_median: number}; per_aoi: Aoi[]};
  persistence: {source: Source; clusters: number; shares: Record<string, Share>; by_district: Record<string, Record<string, number>>; lumshnong: Record<string, number>; slope_by_class: Record<string, number>; follow_up_season: string};
  ablation: {source: Source; context: string; cohort: Record<string, number | string[]>; cutoff: number; arms: Record<string, Arm>;
    paired: Record<string, {f1_diff_ci95: CI; f1_diff_median: number; share_resamples_positive: number}>};
  exposure: {source: Source; rules: Record<string, unknown>; reaches: Reach[]; separate_official: {note: string; stations: string[]}};
  official_water_quality: {source: Source; portal: string; note: string; stations: {code: string; name: string; ph_2023_24: CI; ph_2024_25: CI; months: string}[]};
  review: {source: Source; status: string; reviews_returned: number; total_items: number; seed: string; strata: Record<string, {frame_size: number; sampled: number}>; note: string};
};

const pct = (v: number) => (v * 100).toFixed(1) + '%';
const f = (v: number | null | undefined, d = 2) => v == null ? '—' : v.toFixed(d);
const ARM_LABEL: Record<string, string> = {A_sar: 'SAR only (VV, VH)', B_optical: 'Optical only (B3, B4, B8)', C_fusion: 'SAR + optical',
  D_fusion_terrain: 'SAR + optical + terrain', 'R_rule_ndvi_lt_0.10': 'Rule baseline (NDVI < 0.10)'};

export function useResearch() {
  const [data, setData] = useState<Research>();
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading');
  useEffect(() => {
    const c = new AbortController();
    fetch(localSnapshot + 'research.json', {signal: c.signal})
      .then(r => { if (!r.ok) throw Error('Unavailable'); return r.json(); })
      .then(d => { setData(d); setState('ready'); })
      .catch(() => { if (!c.signal.aborted) setState('error'); });
    return () => c.abort();
  }, []);
  return {data, state};
}

export function DataState({state}: {state: 'loading' | 'error'}) {
  return state === 'loading'
    ? <p className="state" role="status">Loading research results…</p>
    : <div className="state error" role="alert"><AlertTriangle size={16}/> Research snapshot unavailable. Run
      <code>python -B -m scripts.phase23_dashboard_data</code> from the repository root, then reload.</div>;
}

/** Horizontal interval chart: point estimate with 95% CI whiskers. Values only from research.json. */
export function IntervalChart({rows, max, unit = '', label}: {rows: {name: string; value: number; ci?: CI; tone?: string}[]; max: number; unit?: string; label: string}) {
  const w = 420, row = 30, left = 168, scale = (v: number) => left + (Math.max(0, Math.min(v, max)) / max) * (w - left - 44);
  return <svg className="interval" viewBox={`0 0 ${w} ${rows.length * row + 22}`} role="img" aria-label={label}>
    {rows.map((r, i) => {
      const y = i * row + 16;
      return <g key={r.name}>
        <text x={0} y={y + 4} className="lab">{r.name}</text>
        <line x1={left} x2={w - 44} y1={y} y2={y} className="track"/>
        <rect x={left} y={y - 6} width={Math.max(1, scale(r.value) - left)} height={12} className={'bar ' + (r.tone ?? '')}/>
        {r.ci && <><line x1={scale(r.ci[0])} x2={scale(r.ci[1])} y1={y} y2={y} className="ci"/>
          <line x1={scale(r.ci[0])} x2={scale(r.ci[0])} y1={y - 5} y2={y + 5} className="ci"/>
          <line x1={scale(r.ci[1])} x2={scale(r.ci[1])} y1={y - 5} y2={y + 5} className="ci"/></>}
        <text x={w - 40} y={y + 4} className="val">{r.value.toFixed(unit === '%' ? 1 : 2)}{unit}</text>
      </g>;
    })}
    <text x={left} y={rows.length * row + 18} className="axis">0</text>
    <text x={w - 44} y={rows.length * row + 18} className="axis" textAnchor="end">{max}{unit}</text>
  </svg>;
}

export function ResearchKPIs({district}: {district: string}) {
  const {data, state} = useResearch();
  if (state !== 'ready' || !data) return <section><h2>Landscape screening</h2><DataState state={state === 'ready' ? 'error' : state}/></section>;
  const L = data.landscape;
  const d = district !== 'All districts' ? L.density.by_district[district] : L.density.overall;
  return <section className="kpis"><h2>Landscape screening · Phase 22X</h2><p>{d.aois} systematically sampled 1.92 km AOIs{district !== 'All districts' ? ' · ' + district : ''}</p>
    <div className="metric"><strong>{f(d.mean)}</strong><div>ha / 100 ha<small>Candidate density · 95% CI {f(d.ci95[0])}–{f(d.ci95[1])}</small></div></div>
    <div className="metric"><strong>{L.sar_dvh.aois_negative[0]}/{L.sar_dvh.aois_negative[1]}</strong><div>AOIs with S1 VH decrease<small>Cluster mean {f(L.sar_dvh.mean_db)} dB vs background</small></div></div>
    <div className="metric"><strong>{pct(L.gfc_recent_loss.fraction)}</strong><div>overlap GFC 2024/25 loss<small>{L.gfc_recent_loss.clusters[0]}/{L.gfc_recent_loss.clusters[1]} clusters · chance ≈ {pct(L.gfc_recent_loss.null_median)}</small></div></div>
    <div className="notice">Mining attribution: {data.mining_attribution}<small>Candidates are satellite-observed land disturbance, not verified mining.</small></div>
  </section>;
}

function Panel({title, badge, children}: {title: string; badge?: string; children: React.ReactNode}) {
  return <section className="panel"><div className="section-bar"><h2>{title}</h2>{badge && <span className="badge neutral">{badge}</span>}</div>{children}</section>;
}

export function Analytics() {
  const {data, state} = useResearch();
  const [district, setDistrict] = useState('All');
  if (state !== 'ready' || !data) return <div className="page"><DataState state={state === 'ready' ? 'error' : state}/></div>;
  const L = data.landscape, P = data.persistence, A = data.ablation;
  const aois = L.per_aoi.filter(a => district === 'All' || a.district === district);
  const maxDensity = Math.ceil(Math.max(...Object.values(L.density.by_district).map(v => v.ci95[1]), L.density.overall.ci95[1]));
  return <div className="page">
    <div className="toolbar"><BarChart3 size={18}/><b>Analytics</b><span>/</span><span>Frozen research results (read only)</span><span className="badge neutral">No live monitoring</span></div>
    <div className="grid2">
      <Panel title="Candidate density by district" badge="Meghalaya · Phase 22X">
        <IntervalChart label="Candidate density with AOI-bootstrap 95% CI" unit="" max={maxDensity}
          rows={[{name: 'Both districts', value: L.density.overall.mean, ci: L.density.overall.ci95},
            ...Object.entries(L.density.by_district).map(([k, v]) => ({name: k, value: v.mean, ci: v.ci95, tone: 'alt'}))]}/>
        <p className="legend">{L.density.unit}. Bars: mean over AOIs; whiskers: AOI-bootstrap 95% CI. Overlapping intervals — no detectable district difference.</p>
      </Panel>
      <Panel title="Persistence after one further season" badge="Meghalaya · Phase 22Y">
        <IntervalChart label="Persistence class shares with AOI-bootstrap CI" unit="%" max={100}
          rows={['PERSISTENT', 'PARTIAL', 'RECOVERING'].map(c => ({name: c[0] + c.slice(1).toLowerCase() + ` (${P.shares[c].clusters})`,
            value: P.shares[c].share * 100, ci: [P.shares[c].ci95[0] * 100, P.shares[c].ci95[1] * 100] as CI, tone: c === 'PERSISTENT' ? 'warn' : c === 'RECOVERING' ? 'alt' : ''}))}/>
        <p className="legend">{P.clusters} clusters, follow-up {P.follow_up_season}. Mean slope: persistent {f(P.slope_by_class.PERSISTENT, 1)}°, recovering {f(P.slope_by_class.RECOVERING, 1)}°.
          Lumshnong blocks: {P.lumshnong.PERSISTENT} of {Object.values(P.lumshnong).reduce((a, b) => a + b, 0)} persistent. Persistent = mining-compatible review priority, not a label.</p>
      </Panel>
    </div>
    <Panel title="Independent corroboration of candidates" badge="Meghalaya · Phases 22X/22R">
      <div className="facts">
        <div><b>{f(L.sar_dvh.mean_db)} dB</b><span>Sentinel-1 VH change vs background (null ≈ {f(L.sar_dvh.null.null_median)} dB)</span></div>
        <div><b>{f(L.sar_dvv.mean_db)} dB</b><span>Sentinel-1 VV change vs background</span></div>
        <div><b>{pct(L.gfc_recent_loss.fraction)}</b><span>clusters overlapping Hansen GFC 2024/25 loss · Wilson CI {pct(L.gfc_recent_loss.wilson95[0])}–{pct(L.gfc_recent_loss.wilson95[1])}</span></div>
        <div><b>{f(L.hard_commodities.mean_probability, 3)}</b><span>mean hard-commodities driver probability (null {f(L.hard_commodities.null_median, 3)}; 1 km, 2001–2024)</span></div>
      </div>
      <p className="legend">p-values are descriptive (spatially dependent cells). Agreement supports real land disturbance; it does not establish mining.</p>
    </Panel>
    <Panel title="Sampled AOIs" badge={`${aois.length} of ${L.aois}`}>
      <label className="filter">District <select value={district} onChange={e => setDistrict(e.target.value)}>
        <option>All</option>{Object.keys(L.density.by_district).map(k => <option key={k}>{k}</option>)}</select></label>
      <div className="table-scroll"><table><thead><tr><th>AOI block</th><th>District</th><th>Split</th><th>Candidate cells</th><th>Clusters</th><th>Density</th><th>dVH vs bg (dB)</th></tr></thead>
        <tbody>{aois.map(a => <tr key={a.aoi}><td>{a.aoi}</td><td>{a.district}</td><td>{a.split.toUpperCase()}</td><td>{a.candidate_cells}</td><td>{a.clusters}</td><td>{f(a.density)}</td><td>{a.dvh_db == null ? <span className="muted">{a.status === 'ZERO_CANDIDATES' ? 'no candidates' : 'not tested'}</span> : f(a.dvh_db)}</td></tr>)}
        {!aois.length && <tr><td colSpan={7}>No AOIs for this filter.</td></tr>}</tbody></table></div>
    </Panel>
    <Panel title="Sensor ablation (external benchmark)" badge="NOT Meghalaya · Phase 22W">
      <div className="notice">{A.context}<small>Fixed cutoff {A.cutoff}; {String(A.cohort.train_patches)} TRAIN / {String(A.cohort.validation_patches)} VAL patches; Goa excluded (no Sentinel-1).</small></div>
      <IntervalChart label="F1 against weak labels with group-bootstrap 95% CI" max={1}
        rows={Object.entries(A.arms).map(([k, v]) => ({name: ARM_LABEL[k] ?? k, value: v.f1, ci: v.f1_ci95, tone: k.startsWith('R_') ? 'alt' : k === 'A_sar' ? 'warn' : ''}))}/>
      <div className="table-scroll"><table><thead><tr><th>Comparison (F1)</th><th>Median Δ</th><th>95% CI</th><th>P(Δ&gt;0)</th></tr></thead>
        <tbody>{['C_fusion-minus-B_optical', 'B_optical-minus-A_sar', 'D_fusion_terrain-minus-C_fusion'].map(k => { const d = A.paired[k]; return d && <tr key={k}><td>{k.replace(/-minus-/, ' − ').replace(/_/g, ' ')}</td><td>{f(d.f1_diff_median, 3)}</td><td>{f(d.f1_diff_ci95[0], 3)} to {f(d.f1_diff_ci95[1], 3)}</td><td>{f(d.share_resamples_positive)}</td></tr>; })}</tbody></table></div>
      <p className="legend">Fusion adds no detectable F1 over optical (CI spans 0); terrain lowers it. Static footprint agreement only — not change detection.</p>
    </Panel>
  </div>;
}

const CAT: Record<string, [string, string]> = {
  LINKED_CANDIDATE: ['Linked candidate', 'Upstream disturbance and a measured river shift'],
  LAND_DISTURBANCE_ONLY: ['Land disturbance only', 'Adequately observed river, no detectable shift'],
  RIVER_SHIFT_ONLY: ['River shift only', 'Measured shift without linked disturbance'],
  RIVER_UNOBSERVABLE: ['River unobservable', 'Insufficient valid river observations — not "unchanged"'],
  UNKNOWN: ['Unknown', 'Evidence ambiguous; no category forced'],
};

export function RiverExposure() {
  const {data, state} = useResearch();
  if (state !== 'ready' || !data) return <div className="page"><DataState state={state === 'ready' ? 'error' : state}/></div>;
  const E = data.exposure, W = data.official_water_quality;
  const name = (s: string) => s.split('-').slice(0, 2).join(' · ');
  return <div className="page">
    <div className="toolbar"><Route size={18}/><b>River exposure</b><span>/</span><span>Phase 23H reach table</span><span className="badge neutral">Monitoring priority, not pollution</span></div>
    <Panel title="Modelled drainage connectivity" badge="D8 routing · Phase 23A">
      <div className="flow">{[['Lukha-Khaddum-4315', 'Lukha-Sunapur-3376'], ['Myntdu-Mihmyntdu-4316', 'Myntdu-Leshka-3379']].map(pair =>
        <div key={pair[0]} className="chain">{pair.map((s, i) => { const r = E.reaches.find(x => x.station === s)!; return <span key={s} className="node-wrap">
          {i > 0 && <span className="arrow" aria-hidden>→</span>}<span className={'node p-' + String(r.inspection_priority).toLowerCase()}>
          <b>{name(s)}</b><small>{r.upstream_clusters} upstream · {r.upstream_persistent} persistent</small></span></span>; })}</div>)}</div>
      <p className="legend">Counts are cumulative down the main stem (90 m HydroSHEDS D8 routing of 174 clusters). Exposure geometry only — karst, culverts and roads are not resolved.</p>
    </Panel>
    <Panel title="Reach evidence and inspection priority" badge="4 CPCB station reaches">
      <div className="table-scroll"><table><thead><tr><th>Reach</th><th>Upstream clusters (P/Pa/R)</th><th>NDTI dates B/A</th><th>River observation</th><th>Shift</th><th>Category</th><th>Priority</th></tr></thead>
        <tbody>{E.reaches.map(r => <tr key={String(r.station)}><td>{name(String(r.station))}</td>
          <td>{r.upstream_clusters} ({r.upstream_persistent}/{r.upstream_partial}/{r.upstream_recovering})</td>
          <td>{r.ndti_dates_before}/{r.ndti_dates_after}</td><td title={String(r.observation_reason)}>{r.river_observation}<small className="block">{r.observation_reason}</small></td>
          <td>{r.shift_detected === 'NOT_ASSESSED' ? <span className="muted">not assessed</span> : r.shift_detected}</td>
          <td><span className={'cat c-' + String(r.evidence_category).toLowerCase()}>{CAT[String(r.evidence_category)]?.[0] ?? r.evidence_category}</span></td>
          <td><span className={'prio p-' + String(r.inspection_priority).toLowerCase()}>{r.inspection_priority}</span></td></tr>)}</tbody></table></div>
      <dl className="cats">{Object.entries(CAT).map(([k, [t, d]]) => <div key={k}><dt><span className={'cat c-' + k.toLowerCase()}>{t}</span></dt><dd>{d}</dd></div>)}</dl>
      <p className="legend">Sunapur is HIGH priority for future monitoring because of modelled upstream exposure and missing usable NDTI — not because pollution has been demonstrated. No official measurements are verified at these four stations.</p>
    </Panel>
    <Panel title="Official water-quality records — kept separate" badge="Not linked to any reach">
      <div className="notice">{W.portal}<small>{W.note}</small></div>
      <div className="table-scroll"><table><thead><tr><th>Station</th><th>pH Nov–Mar 2023–24</th><th>pH Nov–Mar 2024–25</th><th>Months</th></tr></thead>
        <tbody>{W.stations.map(s => <tr key={s.code}><td>{s.code} · {s.name}</td><td>{s.ph_2023_24[0]}–{s.ph_2023_24[1]}</td><td>{s.ph_2024_25[0]}–{s.ph_2024_25[1]}</td><td>{s.months}</td></tr>)}</tbody></table></div>
    </Panel>
  </div>;
}

function download(name: string, text: string, type: string) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text], {type}));
  a.download = name; a.click(); URL.revokeObjectURL(a.href);
}

export function toCSV(rows: Record<string, unknown>[]) {
  if (!rows.length) return '';
  const cols = Object.keys(rows[0]);
  const esc = (v: unknown) => { const s = Array.isArray(v) ? v.join(' ') : String(v ?? ''); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
  return [cols.join(','), ...rows.map(r => cols.map(c => esc(r[c])).join(','))].join('\n');
}

export function Evidence() {
  const {data, state} = useResearch();
  const sources = useMemo(() => data ? (['landscape', 'persistence', 'ablation', 'exposure', 'official_water_quality', 'review'] as const)
    .map(k => [k, data[k].source] as const) : [], [data]);
  if (state !== 'ready' || !data) return <div className="page"><DataState state={state === 'ready' ? 'error' : state}/></div>;
  const R = data.review;
  return <div className="page">
    <div className="toolbar"><FileText size={18}/><b>Evidence</b><span>/</span><span>Methodology, sources and exports</span><span className="badge neutral">{data.earth_engine_requests} live requests</span></div>
    <div className="grid2">
      <Panel title="Methodology (summary)">
        <ul className="plain">
          <li>Seasonal Sentinel-2 composites, Nov–Mar 2023–24 vs 2024–25; candidate rule NDVI drop ≤ −0.30 and BSI rise &gt; +0.10 (Phase 22L, unchanged).</li>
          <li>Preregistered, TEST-guarded systematic sample of 20 AOIs (5 km seed-42 spatial blocks).</li>
          <li>Corroboration with Sentinel-1 VV/VH, Hansen GFC v1.13 and WRI/GDM forest-loss drivers; persistence checked with 2025–26.</li>
          <li>Drainage exposure by 90 m HydroSHEDS D8 routing; relative NDTI = (B4 − B3)/(B4 + B3) only where interior water is verified.</li>
        </ul>
      </Panel>
      <Panel title="Limitations">
        <ul className="plain warn">
          <li>No independently verified mining labels: mining attribution UNKNOWN; no accuracy is reported for Meghalaya.</li>
          <li>Narrow rivers: no flowing reach has usable 10 m interior water; official station records unverified.</li>
          <li>Seasonal composites at 30 m; jhum, logging, roads and construction produce similar signals.</li>
          <li>Static snapshot of frozen results — not real-time monitoring.</li>
        </ul>
      </Panel>
    </div>
    <Panel title="Independent human review" badge={R.status}>
      <div className="notice">{R.note}<small>{R.reviews_returned} of 2 independent reviews returned · {R.total_items} blinded items · seed {R.seed}</small></div>
      <div className="table-scroll"><table><thead><tr><th>Stratum</th><th>Frame</th><th>Sampled</th></tr></thead>
        <tbody>{Object.entries(R.strata).map(([k, v]) => <tr key={k}><td>{k}</td><td>{v.frame_size.toLocaleString('en-IN')}</td><td>{v.sampled}</td></tr>)}</tbody></table></div>
    </Panel>
    <Panel title="Exports (aggregate results only)">
      <div className="exports">
        <button onClick={() => download('research-summary.json', JSON.stringify(data, null, 1), 'application/json')}><Download size={15}/> Full summary (JSON)</button>
        <button onClick={() => download('sampled-aois.csv', toCSV(data.landscape.per_aoi), 'text/csv')}><Download size={15}/> Sampled AOIs (CSV)</button>
        <button onClick={() => download('reach-priority.csv', toCSV(data.exposure.reaches), 'text/csv')}><Download size={15}/> Reach priority (CSV)</button>
        <button onClick={() => download('sensor-ablation.csv', toCSV(Object.entries(data.ablation.arms).map(([k, v]) => ({arm: k, ...v}))), 'text/csv')}><Download size={15}/> Sensor ablation (CSV)</button>
      </div>
      <p className="legend">No imagery, coordinates, reviewer answers or blinded-review keys are included.</p>
    </Panel>
    <Panel title="Data provenance">
      <div className="table-scroll"><table><thead><tr><th>Block</th><th>Source</th><th>SHA-256</th></tr></thead>
        <tbody>{sources.map(([k, s]) => <tr key={k}><td>{k}</td><td>{s.file}</td><td><code>{s.sha256.slice(0, 16)}…</code></td></tr>)}</tbody></table></div>
    </Panel>
  </div>;
}
