import {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {BarChart3, ChevronDown, CircleHelp, ClipboardCheck, FileText, Grid2X2, Layers, MapPin, Menu, Route, Search} from 'lucide-react';
import '@fontsource/inter/400.css';
import '@fontsource/inter/500.css';
import '@fontsource/inter/600.css';
import './style.css';
import {Explorer} from './explorer';
import {River} from './river';
import {PlanetReview} from './planet';
import {Analytics, Evidence, ResearchKPIs, RiverExposure} from './research';
import {GeoMap} from './geomap';
import {IndiaDiscovery, ScopeSwitch} from './india';

type Tile = {id: string; valid: number; total: number};
type Data = {area: number; seasons: Record<string, Record<string, number>>; tiles: Tile[]; stations: number};
const nav = [
  ['Overview', Grid2X2], ['Explorer', Layers], ['Rivers', Route],
  ['Review', ClipboardCheck], ['Analytics', BarChart3], ['Evidence', FileText],
] as const;
const districts = ['East Jaintia Hills', 'West Jaintia Hills'] as const;
const format = (value?: number) => value?.toLocaleString('en-IN') ?? '—';
const local = import.meta.env.BASE_URL + 'local/';
const region = (tile: Tile) => tile.id.startsWith('east-') ? districts[0] : districts[1];

function Metric({value, label, note}: {value?: number; label: string; note: string}) {
  return <div className="metric"><strong>{format(value)}</strong><div>{label}<small>{note}</small></div></div>;
}

function App() {
  const [hash, setHash] = useState(location.hash);
  const explorer = hash.startsWith('#explorer');
  const rivers = hash.startsWith('#river');
  const review = hash === '#review';
  const analytics = hash.startsWith('#analytics');
  const evidence = hash.startsWith('#evidence');
  const exposure = hash === '#rivers-exposure';
  const meghalaya = hash === '#meghalaya';
  const page = review?3:analytics?4:evidence?5:rivers?2:explorer?1:0;
  useEffect(() => {
    const route = () => setHash(location.hash);
    addEventListener('hashchange', route);
    return () => removeEventListener('hashchange', route);
  }, []);
  const [data, setData] = useState<Data>();
  const [district, setDistrict] = useState('All districts');
  const [season, setSeason] = useState('2023-24');
  const [query, setQuery] = useState('');
  const [drawer, setDrawer] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    fetch(local + 'overview.json', {signal: controller.signal})
      .then(response => { if (!response.ok) throw Error('Unavailable'); return response.json(); })
      .then(setData).catch(() => {});
    return () => controller.abort();
  }, []);
  const tiles = data?.tiles.filter(tile =>
    (district === 'All districts' || region(tile) === district) &&
    (tile.id + ' ' + region(tile)).toLowerCase().includes(query.trim().toLowerCase()));
  const inventory = data?.seasons[season];
  return <div className="app">
    <header className="global"><div className="brand"><b>{page===0 && !meghalaya ? 'INDIA' : 'MEGHALAYA'}</b><small>Mining &amp; River Intelligence Portal</small></div>
      {page===0 && meghalaya && <><label className="control"><MapPin size={16}/><select aria-label="Study area" value={district} onChange={e => setDistrict(e.target.value)}>
        <option value="All districts">Jaintia Hills, Meghalaya</option>{districts.map(name => <option key={name}>{name}</option>)}
      </select></label>
      <label className="control search"><Search size={17}/><input aria-label="Filter district or tile" placeholder="Find a district or tile" value={query} onChange={e => setQuery(e.target.value)}/></label></>}
      <span className="workspace">Research workspace</span><span className="source">{data ? 'Sources indexed' : 'Local receipts unavailable'}</span>
      <a className="method" onClick={event=>{if(analytics||evidence||exposure)return;if(rivers||review){event.preventDefault();const details=document.querySelector<HTMLDetailsElement>(review?"#review-methodology":"#river-methodology");if(details){details.open=true;details.scrollIntoView();details.querySelector("summary")?.focus();}}}} href={analytics||evidence||exposure?"#evidence":explorer?"#explorer-methodology":rivers?"#river-methodology":review?"#review-methodology":"#methodology"}><CircleHelp size={16}/> Methodology</a><span className="badge neutral">Research preview</span>
    </header>
    <nav className={'rail'+(drawer ? ' expanded' : '')} aria-label="Workspace">
      {nav.map(([name, Icon], index) =>
        <a key={name} href={["#overview","#explorer","#rivers","#review","#analytics","#evidence"][index]} aria-current={index===page?"page":undefined} title={name}><Icon size={20}/><span>{name}</span></a>)}
      <button className="nav-menu" onClick={() => setDrawer(!drawer)} aria-label="Toggle navigation" aria-expanded={drawer}><Menu size={19}/></button>
    </nav>
    <main id={["overview","explorer","rivers","review","analytics","evidence"][page]}>{analytics ? <Analytics/> : evidence ? <Evidence/> : exposure ? <RiverExposure/> : explorer ? <Explorer key={hash} hash={hash}/> : rivers ? <River key={hash} pilotView={hash==="#rivers-leshka"} brahmaniView={hash==="#rivers-brahmani"}/> : review ? <PlanetReview/> : !meghalaya ? <IndiaDiscovery/> : <>
      <div className="toolbar"><Grid2X2 size={18}/><b>Overview</b><ScopeSwitch scope="meghalaya"/>
        <label className="season"><select aria-label="Inventory window" value={season} onChange={e => setSeason(e.target.value)}>
          <option value="2023-24">Nov 2023 — Mar 2024</option><option value="2024-25">Nov 2024 — Mar 2025</option>
        </select><ChevronDown size={13}/></label><span className="badge neutral">Read only</span></div>
      <div className="overview">
        <aside className="summary">
          <small>REGIONAL MONITORING</small><h1>Jaintia Hills</h1><p>East &amp; West Jaintia Hills, Meghalaya</p><span className="badge">RESEARCH PREVIEW</span>
          <section><h2>Observation summary</h2><p>District archive inventory · {season}</p>
            <Metric value={inventory?.['Sentinel-1 GRD']} label="SAR scenes" note="Sentinel-1 GRD archive count"/>
            <Metric value={inventory?.['Sentinel-2 SR Harmonized']} label="Optical scenes" note="Sentinel-2 harmonized SR archive count"/>
            <Metric value={data?.tiles.length} label="Feature tiles" note="Phase 6B verified footprints"/>
          </section>
          <section><h2>District focus</h2>{districts.map(name => <button className="district" key={name} aria-pressed={district===name}
            onClick={() => setDistrict(district===name?'All districts':name)}>{name}<span>{format(data?.tiles.filter(tile=>region(tile)===name).length)}</span></button>)}</section>
          <ResearchKPIs district={district}/>
          <section id="methodology"><h2>Research readiness</h2><ul><li>Acquisition checks complete</li><li>Exploratory change analysis available</li><li>Independent reference admission pending</li></ul>
            <div className="notice">Verified field observations<small>No admitted reference labels.</small></div></section>
          <small>{format(data?.area)} km² · GAUL 2025 study area · {format(data?.stations)} river stations</small>
        </aside>
        <div className="content">
          <section className="map" aria-label="Interactive study-area map">
            <GeoMap district={district}/>
            <span className="badge map-label">Real geography · offline vectors</span>
          </section>
          <section className="triage"><div className="section-bar"><h2>Tile coverage</h2><span className="badge neutral">{tiles?.length ?? '—'} verified tiles</span></div>
            <p>Saved feature coverage. Independent reference review is pending.</p>
            <div className="table-scroll"><table><thead><tr><th>Area / reference</th><th>District</th><th>Signal</th><th>Common support</th><th>Review status</th></tr></thead>
            <tbody>{tiles?.map(tile=><tr key={tile.id}><td>{tile.id}</td><td>{region(tile)}</td><td>SAR + optical</td><td>{format(tile.valid)} / {format(tile.total)}</td><td>Reference evidence pending</td></tr>)}
            {!tiles?.length && <tr><td colSpan={5}>{data ? 'No matching tiles.' : 'Run the local overview data adapter to load metrics.'}</td></tr>}</tbody></table></div>
          </section>
        </div>
      </div>
    </>}</main>
    <footer><span>RESEARCH PREVIEW / Frozen results — not real-time monitoring · Mining attribution UNKNOWN</span><span>Jaintia Hills, Meghalaya</span><span>Sentinel-1 / Sentinel-2</span></footer>
  </div>;
}
createRoot(document.getElementById('root')!).render(<App/>);
