import {useEffect, useState} from 'react';
import {MapPin, Route} from 'lucide-react';
import './river.css';

type Season = 'before' | 'after';
type Row = Record<string, string | number>;
type Window = {scenes: Row[]; preview?: string} & Record<string, unknown>;
type Station = {
  coordinates: number[]; projected: number[]; extent: number[]; station_to_reach_m: number;
  corridor_pixels: number; reach_properties: {GOID: number}; seasons: Record<Season, Window>;
};
type Pilot = {
  common_pixels: number; strict_pixels: number; wider_pixels: number; historical_pixels: number;
  preview?: string; matched_pairs: string[][]; reportable: boolean; rainfall_geometry: string;
  native_support: Record<string, {SCL: number; B11: number}>;
  analysis_rules: {minimum_common_pixels: number; minimum_matched_months: number; maximum_day_of_month_gap: number};
};
type Data = {
  periods: Record<Season, string[]>; river: {stations: Record<string, Station>; projection: string; grid_m: number; sources: string[]};
  pilot: Pilot; observations: Row[]; days: Row[]; provenance: Record<string, string>;
};
const local = import.meta.env.BASE_URL+'local/';
const screens = [['unique_joined_dates','Joined'],['valid_dates','Valid corridor'],['water_dates','Screened water'],
  ['core_dates','Interior · 20 m clearance'],['wider_core_dates','Interior · 30 m clearance']];
const granules = [['acquired_utc','Acquired UTC'],['id','Granule'],['existing_valid','Valid cells'],['water','Water cells'],
  ['core_10m','Interior cells'],['cloud','Cloud cells'],['shadow','Shadow cells']];
const rainfall = [['rain_1d_mm','Prior 1 day (mm)'],['rain_3d_mm','Prior 3 days (mm)'],['rain_7d_mm','Prior 7 days (mm)']];
const name = (id: string) => id.split('-')[1];
const display = (value: unknown) => value === '' || value == null ? 'Unavailable' : String(value);

function EvidenceTable({rows, fields}: {rows: Row[]; fields: string[][]}) {
  if (!rows.length) return <p>No observations for this selection.</p>;
  return <div className="table-scroll river-table" tabIndex={0} aria-label="Scrollable observation table">
    <table><thead><tr>{fields.map(([key,label])=><th key={key}>{label}</th>)}</tr></thead>
    <tbody>{rows.map((row,i)=><tr key={i}>{fields.map(([key])=><td key={key}>{display(row[key])}</td>)}</tr>)}</tbody></table>
  </div>;
}

function StationMap({stations, selected, select}: {stations: Data['river']['stations']; selected: string; select: (id: string)=>void}) {
  const entries = Object.entries(stations);
  const originX = Math.min(...entries.map(([,s])=>s.extent[0]))-3000;
  const originY = Math.max(...entries.map(([,s])=>s.extent[3]))+3000;
  const scale = 9000/24;
  return <div className="river-map">
    <svg viewBox="0 0 140 122" role="group" aria-label="Map of projected station locations">
      <text x="123" y="12">N ↑</text>
      <line x1="8" y1="106" x2={8+5000/scale} y2="106" stroke="currentColor" strokeWidth=".5"/>
      <text x="8" y="114">5 km</text>
      {entries.map(([id,s])=>{
        const [x,y] = [(s.projected[0]-originX)/scale,(originY-s.projected[1])/scale];
        return <g key={id} transform={'translate('+x+' '+y+')'} role="button" tabIndex={0}
          aria-label={'Map station '+name(id)} aria-pressed={id===selected} onClick={()=>select(id)}
          onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select(id);}}}>
          <rect x={(s.extent[0]-s.projected[0])/scale} y={(s.projected[1]-s.extent[3])/scale}
            width={(s.extent[2]-s.extent[0])/scale} height={(s.extent[3]-s.extent[1])/scale}/>
          <circle r="1.5"/><text x="4" y="1.5">{name(id)}</text>
        </g>;
      })}
    </svg>
    <p>CPCB points · Amber selected · Squares show 720 m windows · EPSG:32646</p>
  </div>;
}

function Preview({file, label}: {file?: string; label: string}) {
  const [failed, setFailed] = useState(false);
  return file && !failed ? <figure><img src={local+file} alt={label} onError={()=>setFailed(true)}/><figcaption>{label}</figcaption></figure>
    : <p>No saved preview is available for this selection.</p>;
}

export function River({pilotView}: {pilotView: boolean}) {
  const [data, setData] = useState<Data>();
  const [failed, setFailed] = useState(false);
  const [id, setId] = useState('Lukha-Khaddum-4315');
  const [season, setSeason] = useState<Season>('before');
  useEffect(()=>{
    const controller = new AbortController();
    fetch(local+'river.json',{signal:controller.signal})
      .then(response=>{if(!response.ok) throw Error('Unavailable'); return response.json();})
      .then(payload=>{
        if(Object.keys(payload.river?.stations ?? {}).length!==4 || !payload.pilot || !Array.isArray(payload.days)) throw Error('Invalid river snapshot');
        setData(payload);
      })
      .catch(()=>{if(!controller.signal.aborted) setFailed(true);});
    return ()=>controller.abort();
  },[]);
  const station = data?.river.stations[id];
  const record = station?.seasons[season];
  const pilot = data?.pilot;
  const days = data?.days.filter(row=>row.season===season) ?? [];
  const measured = data?.observations.filter(row=>row.season===season && row.common_ratio !== '') ?? [];
  const diagnostics = data?.observations.filter(row=>row.season===season) ?? [];
  return <>
    <div className="toolbar"><Route size={18}/><b>{pilotView?'Leshka Feasibility':'River Intelligence'}</b><span>/</span><span>Regional monitoring</span><span className="badge neutral">Feasibility</span></div>
    <div className="river-workspace">
      <aside className="river-catalog">
        <h1>River monitoring</h1><p>Sentinel-2 observation support in the Lukha and Myntdu study windows.</p>
        <a href="#rivers" aria-current={!pilotView?'page':undefined}>Station monitoring</a>
        <a href="#rivers-leshka" aria-current={pilotView?'page':undefined}>Leshka Feasibility</a>
        {data && !pilotView && <>
          <h2>Monitoring stations</h2>
          {Object.keys(data.river.stations).map(key=><button key={key} aria-pressed={key===id} onClick={()=>setId(key)}>
            <strong>{name(key)}</strong><small>{key.split('-')[0]} · CPCB {key.split('-')[2]}</small>
          </button>)}
        </>}
        <label>Season<select value={season} onChange={e=>setSeason(e.target.value as Season)}>
          <option value="before">Before · 2023–24</option><option value="after">After · 2024–25</option>
        </select></label>
        {data && <small>{data.periods[season].join(' → ')} UTC · end exclusive</small>}
        <p className="notice">Satellite screening only. Water chemistry and mining-related impacts remain unverified.</p>
      </aside>
      {!data ? <section className="river-center" role="status"><p>{failed?<>Local Phase 4 results unavailable. Run <code>python -B -m scripts.phase8_river_data</code> from the project root using the saved outputs.</>:'Loading saved Phase 4 results…'}</p></section> :
        pilotView && pilot ? <section className="river-center">
          <h2>Fixed-footprint assessment</h2>
          <p className="notice">{pilot.reportable ? 'See the Phase 4B report for the admitted analysis.' : 'Seasonal spectral comparison withheld. The common support fell below the pilot minimum.'}</p>
          <div className="river-metrics">
            <div><strong>{pilot.common_pixels}</strong>Common 10 m cells</div>
            <div><strong>{pilot.analysis_rules.minimum_common_pixels}</strong>Minimum common cells</div>
            <div><strong>{pilot.matched_pairs.length}</strong>Matched date pairs</div>
          </div>
          <Preview file={pilot.preview} label="Phase 4B fixed-water support · yellow outlines the common footprint"/>
          <h2>Observation availability</h2>
          <p>{days.filter(r=>Number(r.interior_granules)>0).length} distinct UTC dates with screened interior support in this window.</p>
          <details open><summary>Matched date pairs</summary><EvidenceTable
            rows={pilot.matched_pairs.map(([before,after])=>({before,after}))} fields={[['before','Before UTC'],['after','After UTC']]}/></details>
          <details><summary>Dated spectral diagnostics · diagnostic use only</summary>
            <p>B4 red and B3 green are unitless L2A reflectance after scaling. The normalized red–green difference is unitless. Values are diagnostic observations on the fixed footprint.</p>
            <EvidenceTable rows={measured} fields={[[ 'acquired_utc','Acquired UTC'],['fixed_pixels','10 m cells'],
              ['common_red','B4 red'],['common_green','B3 green'],['common_ratio','(B4 − B3) / (B4 + B3)'],...rainfall]}/></details>
          <details><summary>Granule exclusions and rainfall</summary><EvidenceTable rows={diagnostics}
            fields={[[ 'acquired_utc','Acquired UTC'],['status','Status'],['core_10m','Interior cells'],...rainfall]}/></details>
          <details><summary>Daily coverage ledger</summary><EvidenceTable rows={days}
            fields={[[ 'date','UTC date'],['status','Status'],['joined_granules','Joined granules'],['interior_granules','Interior granules'],...rainfall]}/></details>
        </section> : station && record ? <section className="river-center">
          <StationMap stations={data.river.stations} selected={id} select={setId}/>
          <h2>Seasonal observation screening</h2><p>Counts are distinct UTC dates. Open the dated observations to see individual granules.</p>
          <ul className="river-bars" aria-label="Distinct UTC dates by screen">
            {screens.map(([field,label])=><li key={field}><span>{label}</span><div aria-hidden="true"><i style={{width:100*Number(record[field])/Math.max(1,Number(record.unique_joined_dates))+'%'}}/></div><strong>{display(record[field])}</strong></li>)}
          </ul>
          <details><summary>Dated observations and quality flags</summary><EvidenceTable rows={record.scenes} fields={granules}/></details>
          <details><summary>Saved dated reach preview</summary><Preview key={id+season} file={record.preview} label="Phase 4A dated example · blue screened water · gold screened interior"/></details>
        </section> : <section className="river-center"><p>Station observations are unavailable.</p></section>}
      {data && station && pilot && <aside className="river-assessment">
        <h2>{pilotView?'Comparison assessment':'Reach assessment'}</h2>
        {pilotView ? <>
          <h3>Myntdu · Leshka</h3><p>The sampled waterbody may be a reservoir or backwater influenced by hydropower operations. Independent boundary, stage and release records were unavailable.</p>
          <details open><summary>Footprint sensitivity</summary><dl>
            <dt>Stricter NDWI</dt><dd>{pilot.strict_pixels} cells</dd>
            <dt>30 m clearance</dt><dd>{pilot.wider_pixels} cells</dd>
            <dt>Historical occurrence</dt><dd>{pilot.historical_pixels} cells</dd>
            <dt>Whole 20 m SCL / B11 cells</dt><dd>{Math.min(...Object.values(pilot.native_support).map(s=>s.SCL))} / {Math.min(...Object.values(pilot.native_support).map(s=>s.B11))}</dd>
          </dl></details>
          <p>{pilot.rainfall_geometry}. CHIRPS describes the coarse station cell. Empty totals indicate missing input days.</p>
        </> : <>
          <h3><MapPin size={16}/> {id.split('-')[0]} · {name(id)}</h3>
          <p>{station.coordinates[1]}° N · {station.coordinates[0]}° E</p>
          <dl><dt>HydroSHEDS reach GOID</dt><dd>{station.reach_properties.GOID}</dd>
            <dt>Station-to-line offset</dt><dd>{station.station_to_reach_m} m</dd>
            <dt>Corridor grid cells</dt><dd>{station.corridor_pixels}</dd></dl>
          <p>{id.endsWith('3379')?'Leshka advanced to the fixed-footprint pilot. The seasonal contrast remains withheld.':
            'This station lacks screened interior water in both windows. The screen cannot establish river flow or bank-to-bank width.'}</p>
          <p>The saved reach is a corridor guide. The pilots did not delineate upstream catchments or verify flow direction.</p>
        </>}
        <details id="river-methodology"><summary>Screening rules and provenance</summary>
          <p>Water requires SCL 6 and positive green–NIR NDWI after cloud, edge and validity screening. Interior requires 20 m centre-to-failing-cell clearance on the 10 m grid. SCL and B11 are native 20 m. Cloud and shadow flags can overlap.</p>
          {pilotView && <p>Matching pairs nonreused dates in the same calendar month within {pilot.analysis_rules.maximum_day_of_month_gap} days by day of month. The minimum is {pilot.analysis_rules.minimum_matched_months} matched months.</p>}
          <ul>{data.river.sources.map(item=><li key={item}>{item}</li>)}</ul>
          <dl className="river-receipts">{Object.entries(data.provenance).map(([path,hash])=><div key={path}><dt>{path}</dt><dd>{hash}</dd></div>)}</dl>
        </details>
      </aside>}
    </div>
  </>;
}
