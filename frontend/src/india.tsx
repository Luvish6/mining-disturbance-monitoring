import {useEffect, useState} from 'react';
import {Globe2, MapPin, Route} from 'lucide-react';
import './india.css';
import {localSnapshot, useSnapshot} from './research-data';
import {ANALYSED_REGION, INDIA_FRAME, RIVER_STUDY, TIERS, type Lead, type Screening, byState, inFrame, plot, siteFor, statesOf, summarise, tierOf} from './india-data';

/** Label placement only: points stay at their true coordinates; labels of points closer than 18 px are stacked. */
export function placeLabels(leads: Lead[], W: number, H: number) {
  const out: {l: Lead; x: number; y: number; dy: number}[] = [];
  for (const l of leads) {
    const [x, y] = plot(l.longitude, l.latitude, W, H);
    const near = out.filter(o => Math.hypot(o.x - x, o.y - y) < 18).length;
    out.push({l, x, y, dy: near * 16});
  }
  return out;
}

export function ScopeSwitch({scope}: {scope: 'india' | 'meghalaya'}) {
  return <nav className="scope-switch" aria-label="Overview scope">
    <a href="#overview" aria-current={scope === 'india' ? 'page' : undefined}>India — Discovery</a>
    <a href="#meghalaya" aria-current={scope === 'meghalaya' ? 'page' : undefined}>Meghalaya — Detailed Study</a>
  </nav>;
}

export function IndiaDiscovery() {
  const {result, failed} = useSnapshot<Lead[]>('india-candidates');
  const [study, setStudy] = useState<number[]>();
  const [sel, setSel] = useState('');
  const [state, setState] = useState('');
  const screening = useSnapshot<Screening>('india-screening').result?.data;
  useEffect(() => {  // verified Meghalaya study bounds from the existing geo layer (optional)
    const c = new AbortController();
    fetch(localSnapshot + 'geo.json', {signal: c.signal}).then(r => r.ok ? r.json() : undefined).then(g => g && setStudy(g.view_bounds)).catch(() => {});
    return () => c.abort();
  }, []);
  const all = (result?.data ?? []).filter(l => inFrame(l.longitude, l.latitude));
  const leads = byState(all, state);
  const s = summarise(all);
  const lead = leads.find(l => l.id === sel) ?? leads[0];
  const site = lead && siteFor(screening, lead.id);
  const W = 600, H = 620;
  return <>
    <div className="toolbar"><Globe2 size={18}/><b>Overview</b><ScopeSwitch scope="india"/><span className="badge neutral">Discovery leads · not detections</span></div>
    <div className="india">
      <aside className="summary">
        <small>INDIA-WIDE DISCOVERY</small><h1>India</h1><p>Mining-related disturbance leads (Phase 11C)</p><span className="badge">RESEARCH PREVIEW</span>
        <section><h2>Lead counts</h2>
          <div className="metric"><strong>{result ? s.leads : '—'}</strong><div>Candidate leads<small>{s.states} states · all status UNKNOWN</small></div></div>
          <div className="metric"><strong>{result ? s.tiers.SCREENED_SITE : '—'}</strong><div>Screened sites<small>Saved S1/S2 site observations</small></div></div>
          <div className="metric"><strong>0</strong><div>Verified detections<small>No independent reference anywhere in India</small></div></div>
        </section>
        <section><h2>Evidence tiers</h2>
          {(Object.keys(TIERS) as (keyof typeof TIERS)[]).map(t => <div key={t} className={'tier t-' + t.toLowerCase()}>
            <span className="dot" aria-hidden/><div><b>{TIERS[t].label} ({result ? s.tiers[t] : '—'})</b><small>{TIERS[t].text}</small></div></div>)}
          <div className="tier t-analysed"><span className="dot" aria-hidden/><div><b>{ANALYSED_REGION.label} (1)</b><small>{ANALYSED_REGION.text}</small></div></div>
          <div className="notice">Rest of India: no analysis<small>Unmarked areas were not screened. Absence of a point is not absence of mining.</small></div>
        </section>
        <section><h2>State</h2>
          <label className="state-filter">Filter leads by state<select value={state} onChange={e => { setState(e.target.value); setSel(''); }}>
            <option value="">All states ({statesOf(all).length})</option>
            {statesOf(all).map(x => <option key={x} value={x}>{x}</option>)}</select></label>
          {screening && <p className="legend">Phase 24B screened {screening.coverage.aois_screened} tiles · {screening.coverage.screened_km2} km² in total · national coverage: no</p>}
        </section>
        <section><h2>Studies</h2>
          <a className="nav-card" href="#meghalaya"><MapPin size={15}/> Meghalaya detailed study<small>20 sampled AOIs, persistence, river exposure</small></a>
          <a className="nav-card" href="#explorer-india"><Globe2 size={15}/> India leads in Explorer<small>Per-lead screening values and site layers</small></a>
          <a className="nav-card" href="#rivers"><Route size={15}/> River studies<small>Lukha/Myntdu stations · <span>Brahmani via its lead</span></small></a>
        </section>
      </aside>
      <div className="content">
        <section className="india-map" aria-label="India discovery leads on a longitude/latitude graticule">
          {failed && <p className="geomap-state" role="alert">Lead snapshot unavailable. Run <code>python -B -m scripts.phase13_data</code> and reload.</p>}
          {!result && !failed && <p className="geomap-state" role="status">Loading leads…</p>}
          <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${s.leads} leads plotted by longitude and latitude; no basemap or boundaries`}>
            {Array.from({length: 7}, (_, i) => INDIA_FRAME.west + i * 5).map(lon => { const [x] = plot(lon, INDIA_FRAME.south, W, H); const [, y0] = plot(lon, INDIA_FRAME.north, W, H); const [, y1] = plot(lon, INDIA_FRAME.south, W, H);
              return <g key={'x' + lon}><line x1={x} x2={x} y1={y0} y2={y1} className="grat"/><text x={x} y={y1 + 16} className="gl" textAnchor="middle">{lon}°E</text></g>; })}
            {Array.from({length: 7}, (_, i) => INDIA_FRAME.south + i * 5).filter(l => l <= INDIA_FRAME.north).map(lat => { const [x0, y] = plot(INDIA_FRAME.west, lat, W, H); const [x1] = plot(INDIA_FRAME.east, lat, W, H);
              return <g key={'y' + lat}><line x1={x0} x2={x1} y1={y} y2={y} className="grat"/><text x={x0 - 6} y={y + 3} className="gl" textAnchor="end">{lat}°N</text></g>; })}
            {study && (() => { const [a, b] = plot(study[0], study[3], W, H), [c, d] = plot(study[2], study[1], W, H);
              return <a href="#meghalaya" aria-label="Open the Meghalaya detailed study"><rect x={a} y={b} width={Math.max(4, c - a)} height={Math.max(4, d - b)} className="study"/>
                <text x={(a + c) / 2} y={d + 16} className="gl study-l" textAnchor="middle">Meghalaya study area</text></a>; })()}
            {placeLabels([...leads].sort((a, b) => Number(tierOf(a) === 'SCREENED_SITE') - Number(tierOf(b) === 'SCREENED_SITE')), W, H).map(({l, x, y, dy}) => { const t = tierOf(l);
              return <g key={l.id} transform={`translate(${x} ${y})`} className={'lead t-' + t.toLowerCase() + (lead?.id === l.id ? ' on' : '')}
                role="button" tabIndex={0} aria-label={`${l.id}, ${l.state}, ${TIERS[t].label}, status ${l.status}`} aria-pressed={lead?.id === l.id}
                onClick={() => setSel(l.id)} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSel(l.id); } }}>
                {t === 'SCREENED_SITE' ? <rect x={-6} y={-6} width={12} height={12}/> : <circle r={6}/>}
                {dy !== 0 && <line x1={8} y1={0} x2={10} y2={dy} className="leader"/>}
                <text x={12} y={dy + 4}>{l.id}</text></g>; })}
          </svg>
          <div className="geonote">Plain lon/lat graticule · no basemap or boundaries (not downloaded) · WGS84 · Phase 11C locations from public clearance documents</div>
        </section>
        {lead && <section className="triage lead-detail"><div className="section-bar"><h2>{lead.id}</h2><span className="badge neutral">{TIERS[tierOf(lead)].label} · {lead.status}</span></div>
          <p>{lead.state}{lead.district ? ' · ' + lead.district : ''} · {lead.latitude.toFixed(4)}° N, {lead.longitude.toFixed(4)}° E · {lead.common.toLocaleString('en-IN')} common-valid 30 m cells</p>
          <p className="legend">Seasonal screening medians (after − before): {Object.entries(lead.changes).map(([k, v]) => `${k} ${v.toFixed(3)}${k === 'dVV' || k === 'dVH' ? ' dB' : ''}`).join(' · ')}. Exploratory only; not mining evidence.</p>
          <div className="lead-links">
            <a href={'#explorer-india/' + lead.id}>Open in Explorer</a>
            {tierOf(lead) === 'SCREENED_SITE' && <a href={'#explorer-india/' + lead.id + '/site'}>Saved site observations</a>}
            {RIVER_STUDY[lead.id] && <a href={RIVER_STUDY[lead.id]}>Brahmani river study</a>}
            {tierOf(lead) === 'MEGHALAYA_LEAD' && <a href="#meghalaya">Meghalaya detailed study</a>}
          </div>
          {site ? <div className="screen-detail">
            <h3>Phase 24B screening summary <span className="badge neutral">{site.status} · attribution {site.attribution}</span></h3>
            <table><thead><tr><th>Change (after − before)</th><th>p10</th><th>median</th><th>p90</th></tr></thead>
              <tbody>{Object.entries(site.tile.changes).map(([k, q]) => <tr key={k}><td>{k}{k === 'dVV' || k === 'dVH' ? ' (dB)' : ''}</td><td>{q.p10.toFixed(3)}</td><td>{q.median.toFixed(3)}</td><td>{q.p90.toFixed(3)}</td></tr>)}</tbody></table>
            <p className="legend">{site.tile.common_cells}/{site.tile.grid_cells} common-valid cells ({site.tile.screened_km2} km²) · NDVI drop ≤ −0.30 in {(100 * site.tile.ndvi_loss_fraction).toFixed(1)}% of cells (with VH decrease {(100 * site.tile.ndvi_loss_and_vh_drop_fraction).toFixed(1)}%)
              {site.terrain && <> · median slope {site.terrain.slope_deg.median.toFixed(1)}°, &gt;25° in {(100 * site.terrain.slope_over_25_fraction).toFixed(1)}%</>}
              {site.screening && <> · 15C {site.screening.method}: {site.screening.candidate_polygons} review-only anomaly polygons</>}</p>
            <details><summary>Provenance and uncertainty</summary>
              <p className="legend">Tile SHA-256 {site.provenance.tile_sha256.slice(0, 12)}… · config {screening?.config_version} ({site.provenance.config_sha256.slice(0, 12)}…){site.provenance.location_document ? ' · location: ' + site.provenance.location_document : ''}</p>
              <p className="legend">{site.uncertainty}. Descriptive statistics only: no detections, accuracy or mining attribution.</p></details>
          </div> : lead && <p className="legend">No Phase 24B summary loaded. Run <code>python -B -m scripts.phase24b_india_screening --summarise</code>.</p>}
        </section>}
      </div>
    </div>
  </>;
}
