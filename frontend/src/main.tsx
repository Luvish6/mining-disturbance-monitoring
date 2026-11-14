import {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {ChevronDown, CircleHelp, ClipboardCheck, FileText, Grid2X2, Layers, MapPin, Menu, Minus, Plus, Route, Search, ShieldCheck} from 'lucide-react';
import '@fontsource/inter/400.css';
import '@fontsource/inter/500.css';
import '@fontsource/inter/600.css';
import './style.css';

type Tile = {id: string; valid: number; total: number};
type Data = {area: number; seasons: Record<string, Record<string, number>>; tiles: Tile[]; stations: number};
const nav = [
  ['Overview', Grid2X2], ['Explorer', Layers], ['Rivers', Route],
  ['Review', ClipboardCheck], ['Quality', ShieldCheck], ['Reports', FileText],
] as const;
const districts = ['East Jaintia Hills', 'West Jaintia Hills'] as const;
const format = (value?: number) => value?.toLocaleString('en-IN') ?? '—';
const local = import.meta.env.BASE_URL + 'local/';
const region = (tile: Tile) => tile.id.startsWith('east-') ? districts[0] : districts[1];

function Metric({value, label, note}: {value?: number; label: string; note: string}) {
  return <div className="metric"><strong>{format(value)}</strong><div>{label}<small>{note}</small></div></div>;
}

function App() {
  const [data, setData] = useState<Data>();
  const [district, setDistrict] = useState('All districts');
  const [season, setSeason] = useState('2023-24');
  const [query, setQuery] = useState('');
  const [zoom, setZoom] = useState(1);
  const [image, setImage] = useState(true);
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
    <header className="global"><div className="brand"><b>MEGHALAYA</b><small>Mining &amp; River Intelligence Portal</small></div>
      <label className="control"><MapPin size={16}/><select aria-label="Study area" value={district} onChange={e => setDistrict(e.target.value)}>
        <option value="All districts">Jaintia Hills, Meghalaya</option>{districts.map(name => <option key={name}>{name}</option>)}
      </select></label>
      <label className="control search"><Search size={17}/><input aria-label="Filter district or tile" placeholder="Find a district or tile" value={query} onChange={e => setQuery(e.target.value)}/></label>
      <span className="workspace">Research workspace</span><span className="source">{data ? 'Sources indexed' : 'Local receipts unavailable'}</span>
      <a className="method" href="#methodology"><CircleHelp size={16}/> Methodology</a><span className="badge neutral">Research preview</span>
    </header>
    <nav className={'rail'+(drawer ? ' expanded' : '')} aria-label="Workspace">
      {nav.map(([name, Icon], index) => index === 0 ?
        <a key={name} href="#overview" aria-current="page"><Icon size={20}/><span>{name}</span></a> :
        <button key={name} disabled title={name+' is outside Stage A'}><Icon size={20}/><span>{name}</span></button>)}
      <button className="nav-menu" onClick={() => setDrawer(!drawer)} aria-label="Toggle navigation" aria-expanded={drawer}><Menu size={19}/></button>
    </nav>
    <main id="overview">
      <div className="toolbar"><Grid2X2 size={18}/><b>Overview</b><span>/</span><span>Regional monitoring</span>
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
          <section id="methodology"><h2>Research readiness</h2><ul><li>Acquisition checks complete</li><li>Exploratory change analysis available</li><li>Independent reference admission pending</li></ul>
            <div className="notice">Verified field observations<small>No admitted reference labels.</small></div></section>
          <small>{format(data?.area)} km² · GAUL 2025 study area · {format(data?.stations)} river stations</small>
        </aside>
        <div className="content">
          <section className="map" aria-label="Illustrative study-area context">
            {image && <div className="map-art" style={{transform:'scale('+zoom+')'}}>
              <img className="landscape" src={local+'figma-landscape.png'} onError={()=>setImage(false)} alt=""/>
              {['StudyEnvelope','DistrictBoundary','RiverCorridor','Tributary'].map(name =>
                <img key={name} className={name} src={local+name+'.svg'} alt=""
                     onError={event => {event.currentTarget.hidden = true;}}/>)}
            </div>}
            <div className="map-tabs"><span>Study boundary</span><span>Regional context</span></div><span className="badge map-label">Illustrative context</span>
            {image && <div className="map-names"><span>WEST JAINTIA HILLS</span><span>EAST JAINTIA HILLS</span></div>}
            {!image && <p className="map-empty">Local Figma background unavailable.</p>}
            <div className="zoom"><button aria-label="Zoom in" disabled={!image||zoom>=1.6} onClick={()=>setZoom(Math.min(1.6,zoom+.2))}><Plus size={18}/></button>
              <button aria-label="Zoom out" disabled={!image||zoom<=1} onClick={()=>setZoom(Math.max(1,zoom-.2))}><Minus size={18}/></button></div>
            <div className="map-note">Illustrative study envelope and river corridors · Figma design</div>
          </section>
          <section className="triage"><div className="section-bar"><h2>Tile coverage</h2><span className="badge neutral">{tiles?.length ?? '—'} verified tiles</span></div>
            <p>Saved feature coverage. Independent reference review is pending.</p>
            <div className="table-scroll"><table><thead><tr><th>Area / reference</th><th>District</th><th>Signal</th><th>Common support</th><th>Review status</th></tr></thead>
            <tbody>{tiles?.map(tile=><tr key={tile.id}><td>{tile.id}</td><td>{region(tile)}</td><td>SAR + optical</td><td>{format(tile.valid)} / {format(tile.total)}</td><td>Reference evidence pending</td></tr>)}
            {!tiles?.length && <tr><td colSpan={5}>{data ? 'No matching tiles.' : 'Run the local overview data adapter to load metrics.'}</td></tr>}</tbody></table></div>
          </section>
        </div>
      </div>
    </main>
    <footer><span>RESEARCH PREVIEW / Exploratory observations</span><span>Jaintia Hills, Meghalaya</span><span>Sentinel-1 / Sentinel-2</span></footer>
  </div>;
}
createRoot(document.getElementById('root')!).render(<App/>);
