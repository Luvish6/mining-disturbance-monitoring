import {useEffect, useRef, useState} from 'react';
import {Crosshair, Layers, Minus, PanelLeft, Plus} from 'lucide-react';
import './explorer.css';
import {ExperimentalPredictions} from './experimental';
import {MineMind} from './minemind';
import {localSnapshot, useSnapshot} from './research-data';

const bands = ['dVV', 'dVH', 'dNDVI', 'dNDTI'] as const;
const levels = ['low', 'middle', 'high'] as const;
type Level = typeof levels[number];
type Tile = {
  id: string; district: string; split: string; bounds: number[]; shape: number[]; common: number;
  layers: Record<typeof bands[number], (number | null)[]>;
  counts: Record<string, number[] | null>;
  overlaps: Record<Level, Record<string, number | null>>;
  overlays: Partial<Record<Level, number[]>>;
  sourceHashes: Record<string, string>;
};
type Data = {tiles: Tile[]; periods: string[][]; crs: string; spacing: number; overlapSha256: string};
const colors = [[45,57,69], [255,179,80], [100,212,221], [207,129,225]];
const overlapNames = ['Neither', 'SAR only', 'Optical only', 'Both'];
const overlapFields = ['neither', 'radar_only', 'optical_only', 'joint'];
const rgb = (color: number[]) => 'rgb('+color.join(',')+')';

type Candidate = {
  id: string; state: string; district: string; longitude: number; latitude: number;
  status: 'UNKNOWN'; common: number; changes: Record<string, number>; source: string;
};
type ReviewPolygon = {
  id: string; rings: number[][][]; longitude: number; latitude: number;
  area: number; score: number; status: 'REVIEW_REQUIRED'; evidence: 'UNKNOWN';
};
type Site = {
  crs: string; bounds: number[]; shape: number[]; windows: string[][];
  scenes: Record<string, Record<string, {id: string; acquired_utc: string}[]>>;
  observation_counts: {eligible_cells: number; grid_cells: number; seasonal_count_ranges: Record<string, number[]>};
  settings: {min_robust_z: number; minimum_area_m2: number};
  candidates: ReviewPolygon[]; operational_alerts: number; uncertainty: string; source_sha256: string;
};
const siteModes = {optical:'Sentinel-2 false colour', VV:'Sentinel-1 VV', VH:'Sentinel-1 VH', anomaly:'Cross-sensor anomaly score'};
const legends = {optical:'B8 / B4 / B3 · reflectance stretch 0–0.35', VV:'Greyscale · −25 to 0 dB',
  VH:'Greyscale · −32 to −5 dB', anomaly:'Dark to light · 0 to 1 · unitless tile-relative score'};
function SiteMap({site}: {site: string}) {
  const {result, failed} = useSnapshot<Site>('india-sites/'+site);
  const [mode, setMode] = useState<keyof typeof siteModes>('optical');
  const [season, setSeason] = useState('before');
  const [candidate, setCandidate] = useState('');
  const [showPolygons, setShowPolygons] = useState(true);
  if (!result) return <p role="status">{failed?'Local site imagery and screening results unavailable.':'Loading saved site observations…'}</p>;
  const d = result.data;
  const chosen = d.candidates.find(row=>row.id===candidate);
  const [height,width] = d.shape;
  const layer = mode==='anomaly' ? mode : mode+'_'+season;
  return <>
    <div className="explorer-map" role="region" aria-label="Georeferenced site imagery and review polygons">
      <div className="explorer-map-head"><span>{site} · {siteModes[mode]}</span><span>{d.crs} · North ↑</span></div>
      <svg width="70%" style={{maxHeight:'68%'}} viewBox={'0 0 '+width+' '+height} aria-label="Native 30 m raster and candidate outlines">
        <image href={localSnapshot+'india-sites/'+site+'/'+layer+'.png'} width={width} height={height} style={{imageRendering:'pixelated'}}/>
        {showPolygons && d.candidates.map(row=><path key={row.id} aria-label="Review candidate outline"
          d={row.rings.map(ring=>'M'+ring.map(([x,y])=>x.toFixed(3)+','+y.toFixed(3)).join(' L')+' Z').join(' ')}
          fill="none" stroke={row.id===candidate?'#fff':'#ffc16e'} strokeWidth={0.16}/>)}
      </svg>
      <div className="explorer-legend"><span>{legends[mode]}</span><span>Amber outlines · REVIEW_REQUIRED</span></div>
      <div className="explorer-coords">Bounds (m) · {d.bounds.join(' / ')}</div>
    </div>
    <div className="explorer-periods"><div>
      <label>Display layer <select value={mode} onChange={e=>setMode(e.target.value as keyof typeof siteModes)}>
        {Object.entries(siteModes).map(([key,title])=><option key={key} value={key}>{title}</option>)}</select></label>
      <label>Observation window <select value={season} disabled={mode==='anomaly'} onChange={e=>setSeason(e.target.value)}>
        {d.windows.map(([start,end],i)=><option key={start} value={i===0?'before':'after'}>{start} → {end} (exclusive)</option>)}</select></label>
      <label><input type="checkbox" checked={showPolygons} onChange={e=>setShowPolygons(e.target.checked)}/> Review outlines</label>
    </div></div>
    <div className="explorer-periods"><div>
      <strong>{d.candidates.length} retained screening candidates · {d.operational_alerts} operational alerts</strong>
      {d.candidates.length===0 && <p>No polygons met the screen in this window. Mining activity remains unknown.</p>}
      {d.candidates.length>0 && <label>Review candidate <select value={candidate} onChange={e=>setCandidate(e.target.value)}>
        <option value="">Choose a candidate</option>{d.candidates.map((r,i)=><option key={r.id} value={r.id}>Candidate {i+1}</option>)}</select></label>}
      {chosen && <p>{chosen.status} · {chosen.evidence} · {chosen.longitude.toFixed(6)}° E, {chosen.latitude.toFixed(6)}° N · {chosen.area.toLocaleString()} m² · mean anomaly {chosen.score.toFixed(3)}</p>}
      <p>{d.observation_counts.eligible_cells} / {d.observation_counts.grid_cells} eligible 30 m cells. Minimum departure {d.settings.min_robust_z} robust units in each sensor; connected area ≥ {d.settings.minimum_area_m2.toLocaleString()} m².</p>
      <details id="explorer-methodology"><summary>Observation dates, source and uncertainty</summary>
        <p>{d.uncertainty}. Dates below identify source scenes for seasonal composites.</p>
        <p style={{overflowWrap:'anywhere'}}>Source TIFF SHA-256 {d.source_sha256}. Anomaly TIFF SHA-256 {result.sha256}.</p>
        <ul>{Object.entries(d.observation_counts.seasonal_count_ranges).map(([key,counts])=><li key={key}>{key.replaceAll('_',' ')}: {counts.join('–')}</li>)}</ul>
        {Object.entries(d.scenes).map(([when,sensors])=><details key={when}><summary>{when} scene inventory</summary>
          <ul>{Object.values(sensors).flat().map(row=><li key={row.id} style={{overflowWrap:'anywhere'}}>{row.acquired_utc} · {row.id}</li>)}</ul>
        </details>)}
      </details>
    </div></div>
  </>;
}

function CandidateExplorer({toggle, initial, site}: {toggle: () => void; initial?: string; site?: boolean}) {
  const {result, failed} = useSnapshot<Candidate[]>('india-candidates');
  const [state, setState] = useState('');
  const [id, setId] = useState(initial ?? '');
  const candidates = result?.data ?? [];
  const activeState = state || candidates.find(c => c.id === id)?.state || candidates[0]?.state || '';
  const [showSite, setShowSite] = useState(!!site && ['gevra','bhubaneswari'].includes(initial ?? ''));
  const selected = candidates.find(c=>c.state===activeState && c.id===id) ?? candidates.find(c=>c.state===activeState);
  return <>
    <div className="toolbar"><Layers size={18}/><b>Satellite Explorer</b><button onClick={toggle}>Meghalaya tiles</button><a href="#explorer-experimental">Experimental U-Net</a><a href="#explorer-minemind">MineMind SSL</a><span className="badge neutral">Indian discovery leads</span></div>
    <div className="explorer">
      <aside className="explorer-analysis">
        <label>State<select value={activeState} onChange={e=>{setState(e.target.value);setShowSite(false);}}>
          {[...new Set(candidates.map(c=>c.state))].map(name=><option key={name}>{name}</option>)}
        </select></label>
        <label>Candidate<select value={selected?.id ?? ''} onChange={e=>{setId(e.target.value);setShowSite(false);}}>
          {candidates.filter(c=>c.state===activeState).map(c=><option key={c.id}>{c.id}</option>)}
        </select></label>
        {selected && ['gevra','bhubaneswari'].includes(selected.id) && <button onClick={()=>setShowSite(!showSite)}>{showSite?'Show candidate locations':'Inspect saved site observations'}</button>}
        {result && <p><a href={localSnapshot+'india-candidates.csv'} download>Download candidate CSV</a></p>}
      </aside>
      <section className="explorer-main">
        {showSite && selected ? <SiteMap key={selected.id} site={selected.id}/> : <div className="explorer-map" role="region" aria-label="Candidate locations">
          <div className="explorer-map-head"><span>Phase 11C candidate locations</span><span>WGS84 · North ↑</span></div>
          {selected ? <svg width="90%" viewBox="0 0 240 160" aria-label="Candidate points on longitude and latitude axes">
            <path d="M20 15V140H225" fill="none" stroke="currentColor"/>
            <text x="17" y="153" fill="currentColor" fontSize="9">80° E</text>
            <text x="199" y="153" fill="currentColor" fontSize="9">95° E</text>
            <text x="22" y="22" fill="currentColor" fontSize="9">28° N</text>
            <text x="22" y="136" fill="currentColor" fontSize="9">18° N</text>
            {candidates.map(c=><circle key={c.id} cx={20+(c.longitude-80)*205/15} cy={15+(28-c.latitude)*12.5}
              fill={c.id===selected.id?'#ffc16e':'#72d7d7'} r={c.id===selected.id?4:2.5}
              role="button" tabIndex={0} aria-label={c.id} aria-pressed={c.id===selected.id}
              onClick={()=>{setState(c.state);setId(c.id);}}
              onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();setState(c.state);setId(c.id);}}}><title>{c.id}</title></circle>)}
          </svg> : <p role="status">{failed?'Candidate snapshot unavailable. Run python -B -m scripts.phase13_data.':'Loading candidate snapshot…'}</p>}
        </div>}
      </section>
      <aside className="explorer-details">
        <h2>Evidence status</h2><p>Indian supervised training: <strong>NO-GO</strong>. Model performance: <strong>NOT VALIDATED</strong>.</p>
        {selected && <><h3>{selected.id}</h3><p>{selected.state}{selected.district && ' · '+selected.district} · <strong>{selected.status}</strong></p>
          <p>{selected.latitude.toFixed(6)}° N · {selected.longitude.toFixed(6)}° E</p>
          <p>{selected.common.toLocaleString()} common-valid 30 m cells. Screening medians, after minus before.</p>
          <dl>{Object.entries(selected.changes).map(([band,value])=><div key={band}><dt>{band}</dt><dd>{value.toFixed(4)} {band==='dVV'||band==='dVH'?'dB':'unitless'}</dd></div>)}</dl>
          <details><summary>Source and provenance</summary>
            {selected.source.startsWith('https://') ? <p><a href={selected.source} target="_blank" rel="noreferrer">Site location document</a></p> : <p>Local source: {selected.source}</p>}
            <p>Phase 11C candidate CSV SHA-256</p><code style={{overflowWrap:'anywhere'}}>{result?.sha256}</code>
          </details></>}
        <p className="notice">Exploratory screening. Independent reference admission pending.</p>
        <p><a href="#rivers-brahmani">Open Brahmani river indicators</a></p>
      </aside>
    </div>
  </>;
}

export function Explorer({hash = ''}: {hash?: string}) {
  const deep = hash.startsWith('#explorer-india') ? hash.split('/') : undefined;
  const [india, setIndia] = useState(!!deep);
  const [data, setData] = useState<Data>();
  const [failed, setFailed] = useState(false);
  const [district, setDistrict] = useState('');
  const [id, setId] = useState('');
  const [band, setBand] = useState<typeof bands[number]>('dVV');
  const [level, setLevel] = useState<Level>('middle');
  const [overlay, setOverlay] = useState(false);
  const [visible, setVisible] = useState(true);
  const [opacity, setOpacity] = useState(1);
  const [collapsed, setCollapsed] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState([0,0]);
  const [sample, setSample] = useState('');
  const drag = useRef<{x: number; y: number; pan: number[]} | undefined>(undefined);
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const controller = new AbortController();
    fetch(import.meta.env.BASE_URL+'local/explorer.json', {signal: controller.signal})
      .then(response => { if (!response.ok) throw Error('Unavailable'); return response.json(); })
      .then(value => { if (!value.tiles?.length || value.tiles.some((t: {split?: string}) => t.split === 'test')) throw Error('Invalid roster'); setData(value); })
      .catch(() => { if (!controller.signal.aborted) setFailed(true); });
    return () => controller.abort();
  }, []);
  const districts = [...new Set(data?.tiles.map(item => item.district))];
  const activeDistrict = district || districts[0];
  const tiles = data?.tiles.filter(item => item.district === activeDistrict);
  const tile = tiles?.find(item => item.id === id) ?? tiles?.[0];
  const unit = band === 'dVV' || band === 'dVH' ? 'dB' : 'unitless';
  const limit = unit === 'dB' ? 5 : 0.3;
  const categories = overlay ? tile?.overlays[level] : undefined;
  const layer = tile?.layers[band];
  const stats = tile?.overlaps[level];
  const total = tile ? tile.shape[0]*tile.shape[1] : 0;
  const reset = () => {setZoom(1); setPan([0,0]); setSample('');};
  useEffect(() => {
    const ctx = canvas.current?.getContext('2d');
    if (!ctx || !tile || !layer) return;
    const frame = ctx.createImageData(tile.shape[1], tile.shape[0]);
    layer.forEach((value, index) => {
      if (value === null) return;
      const offset = index*4;
      if (categories) {
        frame.data.set(colors[categories[index]], offset);
      } else {
        const fraction = Math.min(Math.abs(value)/limit, 1);
        const edge = value < 0 ? [64,160,232] : [247,157,72];
        frame.data.set(edge.map(target => 235+(target-235)*fraction), offset);
      }
      frame.data[offset+3] = 255;
    });
    ctx.putImageData(frame, 0, 0);
  }, [tile, layer, limit, categories, india]);
  if (hash.startsWith('#explorer-minemind')) return <MineMind/>;
  if (hash.startsWith('#explorer-experimental')) return <ExperimentalPredictions/>;
  if (india) return <CandidateExplorer toggle={()=>setIndia(false)} initial={deep?.[1]} site={deep?.[2] === 'site'}/>;
  return <>
    <div className="toolbar"><Layers size={18}/><b>Satellite Explorer</b><button onClick={()=>setIndia(true)}>Indian candidates</button><a href="#explorer-experimental">Experimental U-Net</a><a href="#explorer-minemind">MineMind SSL</a><span>/</span><span>Regional monitoring</span><span className="badge neutral">Exploratory</span></div>
    <div className={'explorer'+(collapsed?' analysis-closed':'')}>
      <aside className="explorer-analysis">
        <button className="explorer-toggle" aria-expanded={!collapsed} aria-label="Toggle analysis" onClick={()=>setCollapsed(!collapsed)}><PanelLeft size={17}/>{!collapsed && 'Analysis'}</button>
        {!collapsed && <>
          <label>District<select value={activeDistrict ?? ''} onChange={e=>{setDistrict(e.target.value); reset();}}>{districts.map(name=><option key={name}>{name}</option>)}</select></label>
          <label>Tile<select value={tile?.id ?? ''} onChange={e=>{setId(e.target.value); reset();}}>{tiles?.map(item=><option key={item.id}>{item.id}</option>)}</select></label>
          <fieldset><legend>Signed changes</legend><div className="explorer-options">{bands.map(item=><button key={item} aria-pressed={item===band && !overlay} onClick={()=>{setBand(item);setOverlay(false);setSample('');}}>{item}</button>)}</div></fieldset>
          <fieldset><legend>Threshold sensitivity</legend><div className="explorer-options">{levels.map(item=><button key={item} aria-pressed={item===level} onClick={()=>{setLevel(item);setSample('');}}>{item}</button>)}</div>
            <p>{level === 'low' ? '1 dB / 0.03' : level === 'middle' ? '2 dB / 0.06' : '3 dB / 0.09'}</p>
          </fieldset>
          <label className="explorer-check"><input type="checkbox" checked={overlay} onChange={e=>{setOverlay(e.target.checked);setSample('');}}/> Show SAR–optical overlap</label>
          <label className="explorer-check"><input type="checkbox" checked={visible} onChange={e=>setVisible(e.target.checked)}/> Layer visible</label>
          <label>Opacity · {Math.round(opacity*100)}%<input type="range" min="0" max="1" step=".05" value={opacity} onChange={e=>setOpacity(+e.target.value)}/></label>
        </>}
      </aside>
      <section className="explorer-main">
        <div className="explorer-map" role="region" aria-label="Georeferenced change map" tabIndex={0}
          onKeyDown={e=>{
            const steps: Record<string, number[]> = {ArrowLeft:[-30,0],ArrowRight:[30,0],ArrowUp:[0,-30],ArrowDown:[0,30]};
            const step = steps[e.key];
            if (step) {e.preventDefault(); setPan(([x,y])=>[x+step[0],y+step[1]]);}
          }}
          onPointerDown={e=>{
            if (e.button!==0 || (e.target as HTMLElement).closest('button')) return;
            drag.current={x:e.clientX,y:e.clientY,pan};
            e.currentTarget.setPointerCapture(e.pointerId);
          }}
          onPointerUp={()=>{drag.current=undefined;}}
          onPointerCancel={()=>{drag.current=undefined;}}
          onPointerMove={e=>{
            const start=drag.current;
            if (start) {setPan([start.pan[0]+e.clientX-start.x,start.pan[1]+e.clientY-start.y]);return;}
            if (!tile || !layer || !canvas.current || (overlay && !categories) || !visible || !opacity) {setSample('');return;}
            const rect=canvas.current.getBoundingClientRect();
            const x=Math.floor((e.clientX-rect.left)/rect.width*tile.shape[1]);
            const y=Math.floor((e.clientY-rect.top)/rect.height*tile.shape[0]);
            if (x<0 || y<0 || x>=tile.shape[1] || y>=tile.shape[0]) {setSample('');return;}
            const index=y*tile.shape[1]+x;
            const value=layer[index];
            const east=tile.bounds[0]+(x+.5)*30, north=tile.bounds[3]-(y+.5)*30;
            setSample(east+' E · '+north+' N · '+(value===null?'NoData':categories?overlapNames[categories[index]]:value.toFixed(4)+' '+unit));
          }} onPointerLeave={()=>setSample('')}>
          <div className="explorer-map-head"><span>{tile?.id ?? 'Tile map'}</span><span>{data?.crs} · North ↑</span></div>
          {tile && <canvas ref={canvas} width={tile.shape[1]} height={tile.shape[0]} aria-label="Native change raster"
            style={{opacity:visible && (!overlay || categories)?opacity:0,transform:'translate('+pan[0]+'px,'+pan[1]+'px) scale('+zoom+')'}}/>}
          {(!tile || (overlay && !categories)) && <div className="explorer-empty">{failed ? <>Local tile data unavailable. Run <code>python -m scripts.phase8_explorer_data</code> from the project root.</> : tile ? 'Middle threshold has statistics only. Select low or high for a spatial overlay.' : 'Loading local tile data…'}</div>}
          <div className="explorer-legend">
            {overlay ? categories && overlapNames.map((name,i)=><span key={name}><i style={{background:rgb(colors[i])}}/>{name}</span>) :
              <><b>{band} · {unit}</b><div className="explorer-gradient"/><div className="explorer-ticks"><span>−{limit}</span><span>0</span><span>+{limit}</span></div></>}
            {tile && <small>Checked cells · NoData</small>}
          </div>
          <div className="explorer-zoom">
            <button aria-label="Zoom in" onClick={()=>setZoom(Math.min(8,zoom*1.4))}><Plus size={17}/></button>
            <button aria-label="Zoom out" onClick={()=>setZoom(Math.max(.5,zoom/1.4))}><Minus size={17}/></button>
            <button aria-label="Reset map view" onClick={reset}><Crosshair size={17}/></button>
          </div>
          <div className="explorer-coords">{sample || (tile ? 'Projected bounds (m) · '+tile.bounds.join(' / ') : '')}</div>
        </div>
        <div className="explorer-periods">{data?.periods.map(([start,end],i)=><div key={start}><small>{i===0?'BEFORE':'AFTER'}</small><strong>{start} → {end}</strong></div>)}</div>
      </section>
      <aside className="explorer-details">
        <h2>Cross-sensor overlap</h2><p>{level} threshold · Directional unions</p>
        {stats && <>
          <div className="explorer-bar" aria-label="SAR–optical overlap distribution">{overlapFields.map((key,i)=>
            <span key={key} style={{flexGrow:stats[key]??0,background:rgb(colors[i])}}/>)}</div>
          <dl>{overlapFields.map((key,i)=><div key={key}><dt>{overlapNames[i]}</dt><dd>{stats[key]?.toLocaleString()??'—'}</dd></div>)}
            <div><dt>Jaccard</dt><dd>{stats.jaccard?.toFixed(3)??'—'}</dd></div></dl>
        </>}
        <h2>Observation quality</h2>
        {tile && <><p>{tile.common.toLocaleString()} / {total.toLocaleString()} common-valid pixels ({(100*tile.common/total).toFixed(1)}%)</p>
          <dl>{Object.entries(tile.counts).map(([key, range])=><div key={key}><dt>{key.replaceAll('_',' ')}</dt><dd>{range?.join('–')??'—'}</dd></div>)}</dl></>}
        <details id="explorer-methodology"><summary>Methodology and provenance</summary>
          <p>After minus before on the native 30 m projected grid. Display colours clip at legend endpoints. Directional radar and optical unions use the saved Phase 7 Day 2 thresholds and the common-valid denominator. Date windows use an exclusive end.</p>
          <p>Sentinel-1 GRD and Sentinel-2 SR Harmonized. Frozen split: {tile?.split ?? '—'}. KORPET reference status: UNKNOWN.</p>
          {tile && <dl className="explorer-hashes">{Object.entries({...tile.sourceHashes,overlap:data?.overlapSha256}).map(([name,hash])=><div key={name}><dt>{name}</dt><dd>{hash}</dd></div>)}</dl>}
        </details>
        <p className="notice">Exploratory satellite change. Mining attribution remains unverified.</p>
      </aside>
    </div>
  </>;
}
